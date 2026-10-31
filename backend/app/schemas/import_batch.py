"""Pydantic schemas for statement ingestion and import batches."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class NormalizedRowSchema(BaseModel):
    """Schema for a valid normalized transaction preview item."""

    row_id: str
    row_index: int
    page_number: Optional[int] = 1
    transaction_date: str
    original_description: str
    normalized_description: str
    merchant_name: Optional[str] = None
    amount: Decimal
    currency: str = "INR"
    direction: str
    transaction_type: str
    is_excluded: bool = False
    duplicate_status: str
    duplicate_fingerprint: str
    warnings: List[str] = Field(default_factory=list)
    is_included_by_default: bool = True


class RejectedRowSchema(BaseModel):
    """Schema for a rejected/malformed row item for audit."""

    row_index: int
    page_number: Optional[int] = 1
    raw_data: Dict[str, Any]
    error: str
    warnings: List[str] = Field(default_factory=list)


class ImportBatchResponse(BaseModel):
    """Import batch summary representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    account_id: Optional[uuid.UUID] = None
    source_type: str
    original_filename: str
    status: str
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ImportPreviewResponse(BaseModel):
    """Structured response for previewing an uploaded statement."""

    import_id: uuid.UUID
    status: str
    total_rows: int
    valid_count: int
    rejected_count: int
    duplicate_count: int
    warnings: List[str] = Field(default_factory=list)
    valid_rows: List[NormalizedRowSchema] = Field(default_factory=list)
    rejected_rows: List[RejectedRowSchema] = Field(default_factory=list)


class ImportConfirmRequest(BaseModel):
    """Payload to confirm or adjust candidate rows before committing."""

    accepted_row_ids: Optional[List[str]] = Field(
        None,
        description="Explicit list of row_ids to commit. If omitted, all default-included valid rows are committed.",
    )
    excluded_row_ids: Optional[List[str]] = Field(
        default_factory=list,
        description="Row IDs to explicitly exclude or skip.",
    )
    account_id: Optional[uuid.UUID] = Field(
        None,
        description="Target account ID if not specified during statement upload.",
    )


class ImportConfirmResponse(BaseModel):
    """Response returned upon completing import commit."""

    import_id: uuid.UUID
    status: str
    total_rows: int
    accepted_rows: int
    rejected_rows: int
    committed_transactions_count: int
    message: str

