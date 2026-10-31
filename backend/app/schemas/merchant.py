"""Pydantic schemas for merchant records and alias patterns."""

from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict


class MerchantAliasResponse(BaseModel):
    """Merchant alias pattern item."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alias_pattern: str
    match_type: str
    priority: int
    is_active: bool


class MerchantResponse(BaseModel):
    """Canonical merchant identity with associated aliases."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    canonical_name: str
    category_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    is_fictional_demo: bool = True
    created_at: datetime
    aliases: List[MerchantAliasResponse] = []


class MerchantListResponse(BaseModel):
    """List of merchants with summary counts."""

    merchants: List[MerchantResponse]
    total: int
