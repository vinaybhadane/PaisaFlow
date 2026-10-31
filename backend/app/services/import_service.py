"""Service orchestrating statement import lifecycle, previews, and transactional confirmation."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import NotFoundError, ValidationError
from backend.app.ingestion.pipeline import IngestionPipeline
from backend.app.intelligence.categorization.taxonomy import CategoryTaxonomyService
from backend.app.intelligence.corrections.learning_rules import CategorizationRuleService
from backend.app.intelligence.engine import TransactionIntelligenceEngine
from backend.app.models.account import Account
from backend.app.models.import_batch import ImportBatch
from backend.app.models.transaction import Transaction
from backend.app.schemas.import_batch import (
    ImportConfirmRequest,
    ImportConfirmResponse,
    ImportPreviewResponse,
    NormalizedRowSchema,
    RejectedRowSchema,
)


class ImportService:
    """Business logic for statement file processing, preview, and confirmation."""

    def __init__(self) -> None:
        self.pipeline = IngestionPipeline()
        self.intelligence_engine = TransactionIntelligenceEngine()

    async def create_import_job(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        filename: str,
        file_bytes: bytes,
        account_id: Optional[uuid.UUID] = None,
    ) -> ImportBatch:
        """Parse statement, extract candidates, and generate import batch preview."""
        # 1. Fetch user's existing transaction fingerprints for duplicate detection
        stmt = select(Transaction.duplicate_fingerprint).where(
            Transaction.user_id == user_id,
            Transaction.duplicate_fingerprint.is_not(None),
        )
        result = await db.execute(stmt)
        existing_fingerprints: Set[str] = {fp for fp, in result.fetchall() if fp}

        # 2. Run ingestion pipeline
        preview_result, source_type = self.pipeline.process(
            filename=filename,
            file_bytes=file_bytes,
            user_id=user_id,
            account_id=account_id,
            existing_fingerprints=existing_fingerprints,
        )

        # 3. Create persistent ImportBatch entity
        batch = ImportBatch(
            id=uuid.uuid4(),
            user_id=user_id,
            account_id=account_id,
            source_type=source_type,
            original_filename=filename,
            status="preview_ready",
            total_rows=preview_result.total_rows,
            accepted_rows=preview_result.valid_count,
            rejected_rows=preview_result.rejected_count,
            preview_data=preview_result.model_dump(mode="json"),
            created_at=datetime.now(timezone.utc),
        )
        db.add(batch)
        await db.commit()
        await db.refresh(batch)
        return batch

    async def get_import_batch(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        import_id: uuid.UUID,
    ) -> ImportBatch:
        """Retrieve an import batch ensuring user ownership."""
        stmt = select(ImportBatch).where(
            ImportBatch.id == import_id,
            ImportBatch.user_id == user_id,
        )
        result = await db.execute(stmt)
        batch = result.scalar_one_or_none()
        if not batch:
            raise NotFoundError(f"Import batch '{import_id}' not found.")
        return batch

    async def get_import_preview(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        import_id: uuid.UUID,
    ) -> ImportPreviewResponse:
        """Fetch candidate rows, warnings, and normalization summary."""
        batch = await self.get_import_batch(db, user_id, import_id)
        preview_dict: Dict[str, Any] = batch.preview_data or {}

        valid_rows: List[NormalizedRowSchema] = [
            NormalizedRowSchema(**r) for r in preview_dict.get("valid_rows", [])
        ]
        rejected_rows: List[RejectedRowSchema] = [
            RejectedRowSchema(**r) for r in preview_dict.get("rejected_rows", [])
        ]

        return ImportPreviewResponse(
            import_id=batch.id,
            status=batch.status,
            total_rows=preview_dict.get("total_rows", batch.total_rows),
            valid_count=preview_dict.get("valid_count", len(valid_rows)),
            rejected_count=preview_dict.get("rejected_count", len(rejected_rows)),
            duplicate_count=preview_dict.get("duplicate_count", 0),
            warnings=preview_dict.get("warnings", []),
            valid_rows=valid_rows,
            rejected_rows=rejected_rows,
        )

    async def confirm_import(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        import_id: uuid.UUID,
        request: ImportConfirmRequest,
    ) -> ImportConfirmResponse:
        """Commit selected transactions idempotently within an atomic transaction."""
        batch = await self.get_import_batch(db, user_id, import_id)

        # Idempotency check: if already confirmed or completed, return cleanly without duplicating
        if batch.status in ("completed", "confirmed"):
            return ImportConfirmResponse(
                import_id=batch.id,
                status=batch.status,
                total_rows=batch.total_rows,
                accepted_rows=batch.accepted_rows,
                rejected_rows=batch.rejected_rows,
                committed_transactions_count=batch.accepted_rows,
                message="Import batch has already been confirmed.",
            )

        if batch.status != "preview_ready":
            raise ValidationError(
                f"Cannot confirm import batch in '{batch.status}' status. Must be 'preview_ready'."
            )

        # Determine target account
        target_account_id = request.account_id or batch.account_id
        if target_account_id is not None:
            # Verify account ownership
            acc_stmt = select(Account).where(
                Account.id == target_account_id,
                Account.user_id == user_id,
            )
            acc_res = await db.execute(acc_stmt)
            account = acc_res.scalar_one_or_none()
            if not account:
                raise ValidationError("Specified account_id does not belong to the user.")
        else:
            # Query any existing account for this user or create a synthetic default
            acc_stmt = select(Account).where(Account.user_id == user_id).limit(1)
            acc_res = await db.execute(acc_stmt)
            account = acc_res.scalar_one_or_none()
            if not account:
                account = Account(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    display_name="Primary Checking",
                    account_type="checking",
                    currency="INR",
                    is_synthetic=True,
                )
                db.add(account)
                await db.flush()
            target_account_id = account.id

        # Determine which candidate rows to commit
        preview_dict: Dict[str, Any] = batch.preview_data or {}
        candidate_rows: List[Dict[str, Any]] = preview_dict.get("valid_rows", [])

        excluded_ids: Set[str] = set(request.excluded_row_ids or [])
        if request.accepted_row_ids is not None:
            accepted_ids: Set[str] = set(request.accepted_row_ids)
        else:
            # Default: include valid rows that are marked is_included_by_default
            accepted_ids = {
                r["row_id"]
                for r in candidate_rows
                if r.get("is_included_by_default", True)
            }

        final_commit_ids = accepted_ids - excluded_ids

        # Insert Transaction records
        transactions_to_insert: List[Transaction] = []
        for row in candidate_rows:
            if row["row_id"] in final_commit_ids:
                raw_tx_date = row["transaction_date"]
                tx_date = (
                    datetime.strptime(raw_tx_date, "%Y-%m-%d").date()
                    if isinstance(raw_tx_date, str)
                    else raw_tx_date
                )

                tx = Transaction(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    account_id=target_account_id,
                    import_batch_id=batch.id,
                    transaction_date=tx_date,
                    posted_date=tx_date,
                    original_description=row["original_description"],
                    normalized_description=row["normalized_description"],
                    amount=Decimal(str(row["amount"])),
                    currency=row.get("currency", "INR"),
                    direction=row["direction"],
                    transaction_type=row["transaction_type"],
                    is_excluded=row.get("is_excluded", False),
                    duplicate_fingerprint=row.get("duplicate_fingerprint"),
                    review_status="confirmed",
                    categorization_method="statement_import",
                    confidence="high",
                )
                transactions_to_insert.append(tx)

        # Apply transaction intelligence engine (merchant resolution and category assignment)
        cached_cats = await CategoryTaxonomyService.seed_system_categories(db)
        user_rules = await CategorizationRuleService.list_user_rules(db, user_id=user_id, active_only=True)
        for tx in transactions_to_insert:
            await self.intelligence_engine.process_transaction(
                session=db,
                transaction=tx,
                user_rules=user_rules,
                cached_categories=cached_cats,
            )

        db.add_all(transactions_to_insert)

        # Update batch state
        batch.account_id = target_account_id
        batch.status = "completed"
        batch.accepted_rows = len(transactions_to_insert)
        batch.rejected_rows = batch.total_rows - len(transactions_to_insert)
        batch.completed_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(batch)

        return ImportConfirmResponse(
            import_id=batch.id,
            status=batch.status,
            total_rows=batch.total_rows,
            accepted_rows=batch.accepted_rows,
            rejected_rows=batch.rejected_rows,
            committed_transactions_count=len(transactions_to_insert),
            message=f"Successfully committed {len(transactions_to_insert)} transactions.",
        )

