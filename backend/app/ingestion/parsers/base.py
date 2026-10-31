"""Base classes and data containers for statement parsers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ParsedRow(BaseModel):
    """Raw extracted transaction row before canonical normalization."""

    row_index: int
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    date_str: Optional[str] = None
    description_str: Optional[str] = None
    debit_str: Optional[str] = None
    credit_str: Optional[str] = None
    amount_str: Optional[str] = None
    direction_hint: Optional[str] = None  # 'debit', 'credit', or None
    reference_str: Optional[str] = None
    balance_str: Optional[str] = None
    page_number: Optional[int] = 1
    warnings: List[str] = Field(default_factory=list)
    is_valid: bool = True
    error: Optional[str] = None


class ParseResult(BaseModel):
    """Aggregated result of statement parsing."""

    total_rows: int = 0
    valid_rows: List[ParsedRow] = Field(default_factory=list)
    rejected_rows: List[ParsedRow] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    column_mapping: Dict[str, str] = Field(default_factory=dict)
    source_type: str  # 'csv' or 'pdf_text'


class BaseStatementParser(ABC):
    """Abstract base class for statement parsers."""

    @abstractmethod
    def parse(self, file_bytes: bytes, filename: str = "statement") -> ParseResult:
        """Parse raw file bytes into structured transaction rows."""
        pass

