"""Pydantic schemas for categories and category taxonomy tree."""

from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict


class CategoryBase(BaseModel):
    """Base category properties."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category_type: str
    parent_id: Optional[uuid.UUID] = None
    is_system: bool = True
    sort_order: int = 0


class CategoryResponse(CategoryBase):
    """Category representation including child subcategories."""

    subcategories: List[CategoryBase] = []


class CategoryListResponse(BaseModel):
    """List of all categories."""

    categories: List[CategoryBase]
    total: int
