"""Exceptions for statement ingestion and parsing."""

from typing import Any, Dict, List, Optional
from fastapi import status
from backend.app.core.exceptions import PaisaFlowException


class IngestionError(PaisaFlowException):
    """Base exception for all statement ingestion errors."""

    def __init__(
        self,
        message: str,
        code: str = "INGESTION_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__(message=message, code=code, status_code=status_code, details=details)


class UnsupportedFileFormatError(IngestionError):
    """Raised when an uploaded file format or signature is unsupported."""

    def __init__(self, message: str = "Unsupported statement format. Supported formats are CSV and text-based PDF."):
        super().__init__(
            message=message,
            code="UNSUPPORTED_FILE_FORMAT",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )


class FileTooLargeError(IngestionError):
    """Raised when an upload exceeds the allowed size limit."""

    def __init__(self, message: str = "File size exceeds the maximum permitted limit of 10 MB."):
        super().__init__(
            message=message,
            code="FILE_TOO_LARGE",
            status_code=413,
        )


class EmptyFileError(IngestionError):
    """Raised when an uploaded file contains zero bytes."""

    def __init__(self, message: str = "The uploaded file is empty."):
        super().__init__(
            message=message,
            code="EMPTY_FILE",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class FileCorruptionError(IngestionError):
    """Raised when a file header is present but structure is unreadable or malformed."""

    def __init__(self, message: str = "File is malformed or corrupted and cannot be read."):
        super().__init__(
            message=message,
            code="FILE_CORRUPTION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class ParserError(IngestionError):
    """Raised when parser fails to extract structural transactions from the document."""

    def __init__(self, message: str = "Failed to parse transactions from statement."):
        super().__init__(
            message=message,
            code="PARSER_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class ImportBatchNotFoundError(IngestionError):
    """Raised when a requested import batch does not exist."""

    def __init__(self, message: str = "Import batch not found."):
        super().__init__(
            message=message,
            code="IMPORT_BATCH_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )
