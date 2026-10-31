"""API route handlers for merchant identities and alias catalogue."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.db.dependencies import get_db
from backend.app.models.merchant import Merchant
from backend.app.schemas.common import ApiResponse
from backend.app.schemas.merchant import (
    MerchantAliasResponse,
    MerchantListResponse,
    MerchantResponse,
)

router = APIRouter(prefix="/merchants", tags=["Merchants"])


@router.get(
    "",
    response_model=ApiResponse[MerchantListResponse],
    summary="List canonical merchants and alias patterns",
)
async def list_merchants(
    search: Optional[str] = Query(None, description="Search term for merchant name or alias"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[MerchantListResponse]:
    """Retrieve recognized merchants, descriptions, and linked aliases."""
    stmt = (
        select(Merchant)
        .options(selectinload(Merchant.aliases))
        .order_by(Merchant.canonical_name.asc())
        .limit(limit)
    )

    if search and search.strip():
        term = f"%{search.strip()}%"
        stmt = stmt.where(Merchant.canonical_name.ilike(term))

    res = await db.execute(stmt)
    merchants = res.scalars().all()

    items: List[MerchantResponse] = [
        MerchantResponse(
            id=m.id,
            canonical_name=m.canonical_name,
            category_id=m.category_id,
            description=m.description,
            is_fictional_demo=m.is_fictional_demo,
            created_at=m.created_at,
            aliases=[
                MerchantAliasResponse(
                    id=a.id,
                    alias_pattern=a.alias_pattern,
                    match_type=a.match_type,
                    priority=a.priority,
                    is_active=a.is_active,
                )
                for a in m.aliases
            ],
        )
        for m in merchants
    ]

    return ApiResponse(data=MerchantListResponse(merchants=items, total=len(items)))

