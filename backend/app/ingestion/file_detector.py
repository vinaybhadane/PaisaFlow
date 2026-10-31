"""File format detection and secure temporary file management."""

from contextlib import contextmanager
import os
import tempfile
from typing import Generator
from backend.app.ingestion.validators import validate_file_upload


def detect_file_format(filename: str, file_bytes: bytes) -> str:
    """Detect and return canonical statement format ('csv' | 'pdf_text')."""
    _, detected_format = validate_file_upload(filename, file_bytes)
    return detected_format


@contextmanager
def temporary_upload_file(file_bytes: bytes, suffix: str = ".tmp") -> Generator[str, None, None]:
    """Write bytes to a secure temporary file and ensure cleanup upon exit."""
    fd, temp_path = tempfile.mkstemp(prefix="paisaflow_stmt_", suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(file_bytes)
        yield temp_path
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass

