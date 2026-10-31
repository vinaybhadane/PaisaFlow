"""File upload security and content validation."""

import os
import re
from typing import Tuple

from backend.app.ingestion.exceptions import (
    EmptyFileError,
    FileCorruptionError,
    FileTooLargeError,
    UnsupportedFileFormatError,
)

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".csv", ".pdf"}

# Known binary executable / archive signatures that must never be accepted
DISALLOWED_MAGIC_SIGNATURES = [
    b"MZ",                # Windows Executable / DLL
    b"\x7fELF",           # Linux ELF Binary
    b"\xca\xfe\xba\xbe",  # Java Class / Mach-O fat binary
    b"PK\x03\x04",        # ZIP / JAR (unless explicitly handled, reject to prevent zip bombs)
    b"\x1f\x8b",          # GZIP
    b"Rar!\x1a\x07",      # RAR
    b"7z\xbc\xaf\x27\x1c",# 7-Zip
]


def sanitize_filename(filename: str) -> str:
    """Sanitize uploaded filename to prevent directory traversal and injection."""
    # Take only the basename
    base = os.path.basename(filename)
    # Remove null bytes and control chars
    base = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", base)
    # Replace dangerous characters with underscore
    clean = re.sub(r"[^\w\.\-\(\)\s]", "_", base).strip()
    return clean or "statement_upload"


def validate_file_upload(
    filename: str,
    file_bytes: bytes,
    max_bytes: int = MAX_UPLOAD_SIZE,
) -> Tuple[str, str]:
    """Validate uploaded statement file.

    Returns:
        Tuple of (sanitized_filename, detected_format: 'csv' | 'pdf_text')

    Raises:
        EmptyFileError, FileTooLargeError, UnsupportedFileFormatError, FileCorruptionError
    """
    if not file_bytes:
        raise EmptyFileError("The uploaded file is empty.")

    if len(file_bytes) > max_bytes:
        raise FileTooLargeError(
            f"File size ({len(file_bytes)} bytes) exceeds the maximum allowed limit of {max_bytes} bytes (10 MB)."
        )

    clean_filename = sanitize_filename(filename)
    _, ext = os.path.splitext(clean_filename.lower())

    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileFormatError(
            f"File extension '{ext}' is not supported. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    # Check for disallowed binary headers
    for magic in DISALLOWED_MAGIC_SIGNATURES:
        if file_bytes.startswith(magic):
            raise UnsupportedFileFormatError(
                "Uploaded file contains executable or archive binary signatures which are strictly prohibited."
            )

    # Validate PDF signature
    if ext == ".pdf":
        # Standard PDF files begin with '%PDF-' in first 1024 bytes
        if b"%PDF-" not in file_bytes[:1024]:
            raise FileCorruptionError("Invalid PDF document: missing '%PDF-' signature.")
        return clean_filename, "pdf_text"

    # Validate CSV signature
    if ext == ".csv":
        # CSV must be decodable text with printable characters and delimiters, no null bytes
        if b"\x00" in file_bytes[:4096]:
            raise FileCorruptionError("Invalid CSV document: file contains binary null bytes.")

        # Attempt decoding with UTF-8 (BOM compatible) or Latin-1
        try:
            sample = file_bytes[:4096].decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                sample = file_bytes[:4096].decode("latin-1")
            except Exception as err:
                raise FileCorruptionError(f"Cannot decode CSV text encoding: {err}") from err

        # Must have lines and common delimiters
        lines = [line.strip() for line in sample.splitlines() if line.strip()]
        if not lines:
            raise EmptyFileError("The CSV file does not contain text rows.")

        return clean_filename, "csv"

    raise UnsupportedFileFormatError("Unable to determine file format.")

