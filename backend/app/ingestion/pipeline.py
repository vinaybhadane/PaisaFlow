"""End-to-end statement ingestion and normalization pipeline."""

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid
from pydantic import BaseModel, Field

from backend.app.ingestion.normalization.amount_normalizer import AmountNormalizer
from backend.app.ingestion.normalization.date_normalizer import DateNormalizer
from backend.app.ingestion.normalization.fingerprint import DuplicateFingerprintGenerator
from backend.app.ingestion.normalization.merchant_normalizer import MerchantNormalizer
from backend.app.ingestion.normalization.transaction_classifier import TransactionClassifier
from backend.app.ingestion.parsers.base import BaseStatementParser, ParseResult
from backend.app.ingestion.parsers.csv_parser import CSVStatementParser
from backend.app.ingestion.parsers.pdf_parser import PDFStatementParser
from backend.app.ingestion.validators import validate_file_upload


class NormalizedRowPreview(BaseModel):
    """Normalized, reviewable transaction candidate before confirmation."""

    row_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    row_index: int
    page_number: Optional[int] = 1
    transaction_date: date
    original_description: str
    normalized_description: str
    merchant_name: Optional[str] = None
    amount: Decimal
    currency: str = "INR"
    direction: str  # 'debit' or 'credit'
    transaction_type: str  # 'expense', 'income', 'transfer', 'refund', 'fee'
    is_excluded: bool = False
    duplicate_status: str = "unique"  # 'unique', 'exact_duplicate', 'potential_duplicate'
    duplicate_fingerprint: str
    warnings: List[str] = Field(default_factory=list)
    is_included_by_default: bool = True


class RejectedRowPreview(BaseModel):
    """Row that failed validation or normalization, preserved for user audit."""

    row_index: int
    page_number: Optional[int] = 1
    raw_data: Dict[str, Any]
    error: str
    warnings: List[str] = Field(default_factory=list)


class IngestionPreviewResult(BaseModel):
    """Complete structured preview returned by the ingestion pipeline."""

    total_rows: int
    valid_count: int
    rejected_count: int
    duplicate_count: int
    column_mapping: Dict[str, str] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    valid_rows: List[NormalizedRowPreview] = Field(default_factory=list)
    rejected_rows: List[RejectedRowPreview] = Field(default_factory=list)


class IngestionPipeline:
    """Coordinates parsing, canonical normalization, and duplicate identification."""

    def __init__(self) -> None:
        self.csv_parser = CSVStatementParser()
        self.pdf_parser = PDFStatementParser()

    def process(
        self,
        filename: str,
        file_bytes: bytes,
        user_id: uuid.UUID,
        account_id: Optional[uuid.UUID] = None,
        existing_fingerprints: Optional[Set[str]] = None,
    ) -> Tuple[IngestionPreviewResult, str]:
        """Run the complete ingestion pipeline.

        Returns:
            Tuple of (IngestionPreviewResult, detected_source_type: 'csv' | 'pdf_text')
        """
        clean_name, source_type = validate_file_upload(filename, file_bytes)

        parser: BaseStatementParser = self.csv_parser if source_type == "csv" else self.pdf_parser
        parse_result: ParseResult = parser.parse(file_bytes, clean_name)

        existing_fps = existing_fingerprints or set()
        seen_batch_fps: Set[str] = set()

        valid_rows: List[NormalizedRowPreview] = []
        rejected_rows: List[RejectedRowPreview] = []
        warnings: List[str] = list(parse_result.warnings)

        # Process previously rejected rows from parser
        for rej in parse_result.rejected_rows:
            rejected_rows.append(
                RejectedRowPreview(
                    row_index=rej.row_index,
                    page_number=rej.page_number,
                    raw_data=rej.raw_data,
                    error=rej.error or "Parser error",
                    warnings=rej.warnings,
                )
            )

        for parsed_row in parse_result.valid_rows:
            row_warnings: List[str] = list(parsed_row.warnings)

            # 1. Date normalization
            canon_date, date_err = DateNormalizer.normalize_date(parsed_row.date_str)
            if not canon_date:
                rejected_rows.append(
                    RejectedRowPreview(
                        row_index=parsed_row.row_index,
                        page_number=parsed_row.page_number,
                        raw_data=parsed_row.raw_data,
                        error=date_err or "Invalid transaction date format.",
                        warnings=row_warnings,
                    )
                )
                continue

            # 2. Amount normalization
            debit_amt, debit_neg, debit_err = AmountNormalizer.parse_amount(parsed_row.debit_str)
            credit_amt, credit_neg, credit_err = AmountNormalizer.parse_amount(parsed_row.credit_str)
            net_amt, net_neg, net_err = AmountNormalizer.parse_amount(parsed_row.amount_str)

            final_amount: Optional[Decimal] = None
            debit_present = debit_amt is not None and debit_amt > 0
            credit_present = credit_amt is not None and credit_amt > 0

            if debit_present and not credit_present:
                final_amount = debit_amt
            elif credit_present and not debit_present:
                final_amount = credit_amt
            elif net_amt is not None and net_amt > 0:
                final_amount = net_amt
            elif debit_amt is not None and debit_amt == 0 and credit_amt is not None and credit_amt > 0:
                final_amount = credit_amt
            elif credit_amt is not None and credit_amt == 0 and debit_amt is not None and debit_amt > 0:
                final_amount = debit_amt

            if final_amount is None or final_amount < 0:
                rejected_rows.append(
                    RejectedRowPreview(
                        row_index=parsed_row.row_index,
                        page_number=parsed_row.page_number,
                        raw_data=parsed_row.raw_data,
                        error="Cannot resolve valid non-negative monetary amount.",
                        warnings=row_warnings,
                    )
                )
                continue

            # 3. Merchant Normalization & Resolution
            norm_desc, canon_merchant = MerchantNormalizer.resolve_merchant(
                parsed_row.description_str or "Transaction"
            )

            # 4. Classification
            direction, tx_type, is_excluded = TransactionClassifier.classify(
                description=norm_desc,
                debit_amount_present=debit_present,
                credit_amount_present=credit_present,
                amount_is_negative=net_neg,
                direction_hint=parsed_row.direction_hint,
            )

            # 5. Deterministic Duplicate Fingerprint
            fp = DuplicateFingerprintGenerator.generate_fingerprint(
                user_id=user_id,
                account_id=account_id,
                transaction_date=canon_date,
                amount=final_amount,
                direction=direction,
                normalized_description=norm_desc,
                reference_str=parsed_row.reference_str,
            )

            duplicate_status = "unique"
            is_included = True

            if fp in existing_fps or fp in seen_batch_fps:
                duplicate_status = "exact_duplicate"
                is_included = False
                row_warnings.append(
                    "Exact match already exists in account transaction history."
                    if fp in existing_fps
                    else "Duplicate identical entry detected within this uploaded file."
                )

            seen_batch_fps.add(fp)

            valid_rows.append(
                NormalizedRowPreview(
                    row_index=parsed_row.row_index,
                    page_number=parsed_row.page_number,
                    transaction_date=canon_date,
                    original_description=parsed_row.description_str or "",
                    normalized_description=norm_desc,
                    merchant_name=canon_merchant,
                    amount=final_amount,
                    currency="INR",
                    direction=direction,
                    transaction_type=tx_type,
                    is_excluded=is_excluded,
                    duplicate_status=duplicate_status,
                    duplicate_fingerprint=fp,
                    warnings=row_warnings,
                    is_included_by_default=is_included,
                )
            )

        dup_count = sum(1 for r in valid_rows if r.duplicate_status != "unique")

        result = IngestionPreviewResult(
            total_rows=len(valid_rows) + len(rejected_rows),
            valid_count=len(valid_rows),
            rejected_count=len(rejected_rows),
            duplicate_count=dup_count,
            column_mapping=parse_result.column_mapping,
            warnings=warnings,
            valid_rows=valid_rows,
            rejected_rows=rejected_rows,
        )

        return result, source_type
