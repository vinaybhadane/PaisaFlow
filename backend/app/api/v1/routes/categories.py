"""API route handlers for transaction category taxonomy."""

from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.dependencies import get_db
from backend.app.intelligence.categorization.taxonomy import CategoryTaxonomyService
from backend.app.schemas.category import CategoryBase, CategoryResponse
from backend.app.schemas.common import ApiResponse

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get(
    "",
    response_model=ApiResponse[List[CategoryResponse]],
    summary="List category taxonomy tree with parent and child relationships",
)
async def list_categories(
    tree: bool = Query(True, description="Return hierarchical tree with subcategories"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[List[CategoryResponse]]:
    """Retrieve the canonical financial category taxonomy."""
    # Ensure categories are seeded
    await CategoryTaxonomyService.seed_system_categories(db)

    if tree:
        root_cats = await CategoryTaxonomyService.get_taxonomy_tree(db)
        data = [
            CategoryResponse(
                id=c.id,
                name=c.name,
                category_type=c.category_type,
                parent_id=c.parent_id,
                is_system=c.is_system,
                sort_order=c.sort_order,
                subcategories=[
                    CategoryBase(
                        id=sub.id,
                        name=sub.name,
                        category_type=sub.category_type,
                        parent_id=sub.parent_id,
                        is_system=sub.is_system,
                        sort_order=sub.sort_order,
                    )
                    for sub in sorted(c.subcategories, key=lambda s: s.sort_order)
                ],
            )
            for c in root_cats
        ]
    else:
        all_cats = await CategoryTaxonomyService.get_all_categories(db)
        data = [
            CategoryResponse(
                id=c.id,
                name=c.name,
                category_type=c.category_type,
                parent_id=c.parent_id,
                is_system=c.is_system,
                sort_order=c.sort_order,
                subcategories=[],
            )
            for c in all_cats
        ]

    return ApiResponse(data=data)

