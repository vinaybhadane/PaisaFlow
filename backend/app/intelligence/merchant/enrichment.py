"""Database merchant persistence, alias association, and metadata enrichment."""

from typing import Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.merchant import Merchant, MerchantAlias


class MerchantEnrichmentService:
    """Synchronizes merchant resolution outcomes with the database."""

    @classmethod
    async def get_or_create_merchant(
        cls,
        session: AsyncSession,
        canonical_name: str,
        category_id: Optional[uuid.UUID] = None,
        description: Optional[str] = None,
    ) -> Merchant:
        """Find existing merchant or persist new canonical merchant identity."""
        stmt = select(Merchant).where(Merchant.canonical_name == canonical_name.strip())
        res = await session.execute(stmt)
        merchant = res.scalar_one_or_none()

        if not merchant:
            merchant = Merchant(
                id=uuid.uuid4(),
                canonical_name=canonical_name.strip(),
                category_id=category_id,
                description=description or f"Synthetic merchant: {canonical_name.strip()}",
                is_fictional_demo=True,
            )
            session.add(merchant)
            await session.flush()
        elif category_id and not merchant.category_id:
            merchant.category_id = category_id
            await session.flush()

        return merchant

    @classmethod
    async def record_alias(
        cls,
        session: AsyncSession,
        merchant_id: uuid.UUID,
        alias_pattern: str,
        match_type: str = "exact",
    ) -> MerchantAlias:
        """Associate a newly discovered descriptor alias with a merchant."""
        stmt = select(MerchantAlias).where(
            MerchantAlias.merchant_id == merchant_id,
            MerchantAlias.alias_pattern == alias_pattern.strip().upper(),
        )
        res = await session.execute(stmt)
        alias = res.scalar_one_or_none()

        if not alias:
            alias = MerchantAlias(
                id=uuid.uuid4(),
                merchant_id=merchant_id,
                alias_pattern=alias_pattern.strip().upper(),
                match_type=match_type,
                priority=100,
                is_active=True,
            )
            session.add(alias)
            await session.flush()

        return alias

