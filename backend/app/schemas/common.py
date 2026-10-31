"""Common API response and error schemas."""

from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, TypeVar
import uuid
from pydantic import BaseModel, Field

T = TypeVar("T")


def get_utc_now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


class ApiMeta(BaseModel):
    """Metadata envelope included with every API response."""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: str = Field(default_factory=get_utc_now_iso)


class ApiResponse(BaseModel, Generic[T]):
    """Standard success response envelope."""

    data: T
    meta: ApiMeta = Field(default_factory=ApiMeta)


class ErrorDetail(BaseModel):
    """Individual error detail for validation or domain issues."""

    field: Optional[str] = None
    message: str
    code: Optional[str] = None


class ApiError(BaseModel):
    """Structured error payload."""

    code: str
    message: str
    details: List[Dict[str, Any]] = Field(default_factory=list)


class ApiErrorResponse(BaseModel):
    """Standard error response envelope."""

    error: ApiError
    meta: ApiMeta = Field(default_factory=ApiMeta)

