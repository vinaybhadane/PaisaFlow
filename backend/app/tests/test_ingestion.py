"""Comprehensive unit and integration test suite for statement ingestion pipeline."""

from datetime import date
from decimal import Decimal
from pathlib import Path
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.ingestion.exceptions import (
    EmptyFileError,
    FileTooLargeError,
    UnsupportedFileFormatError,
)
from backend.app.ingestion.normalization.amount_normalizer import AmountNormalizer
from backend.app.ingestion.normalization.date_normalizer import DateNormalizer
from backend.app.ingestion.normalization.fingerprint import DuplicateFingerprintGenerator
from backend.app.ingestion.normalization.merchant_normalizer import MerchantNormalizer
from backend.app.ingestion.normalization.transaction_classifier import TransactionClassifier
from backend.app.ingestion.pipeline import IngestionPipeline
from backend.app.ingestion.validators import sanitize_filename, validate_file_upload
from backend.app.models.transaction import Transaction
from backend.app.models.user import User

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "statements"


# ==============================================================================
# 1. FILE VALIDATION AND SECURITY TESTS
# ==============================================================================


def test_sanitize_filename_prevents_path_traversal() -> None:
    """Verify malicious path traversal attempts are stripped to safe basenames."""
    assert sanitize_filename("../../etc/passwd.csv") == "passwd.csv"
    assert sanitize_filename("..\\..\\Windows\\System32\\statement.csv") == "statement.csv"
    assert sanitize_filename("/var/log/bank.pdf") == "bank.pdf"
    assert sanitize_filename("safe_statement_2026.csv") == "safe_statement_2026.csv"


def test_reject_unsupported_extensions() -> None:
    """Verify non-CSV/PDF extensions are rejected."""
    with pytest.raises(UnsupportedFileFormatError):
        validate_file_upload("script.py", b"print('malicious')")

    with pytest.raises(UnsupportedFileFormatError):
        validate_file_upload("archive.zip", b"PK\x03\x04archive")

    with pytest.raises(UnsupportedFileFormatError):
        validate_file_upload("payload.exe", b"MZ\x90\x00executable")


def test_reject_empty_file() -> None:
    """Verify empty file raises EmptyFileError."""
    with pytest.raises(EmptyFileError):
        validate_file_upload("empty.csv", b"")


def test_reject_oversized_file() -> None:
    """Verify file exceeding 10MB limit raises FileTooLargeError."""
    oversized = b"a" * (10 * 1024 * 1024 + 1)
    with pytest.raises(FileTooLargeError):
        validate_file_upload("large.csv", oversized)


def test_reject_file_signature_spoofing() -> None:
    """Verify binary executable spoofed as .csv or .pdf is rejected by magic byte inspection."""
    exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00This is a Windows executable payload"
    with pytest.raises(UnsupportedFileFormatError):
        validate_file_upload("fake_statement.csv", exe_bytes)

    with pytest.raises(UnsupportedFileFormatError):
        validate_file_upload("fake_statement.pdf", exe_bytes)


# ==============================================================================
# 2. NORMALIZATION UNIT TESTS
# ==============================================================================


def test_date_normalizer() -> None:
    """Verify multiple Indian and international date formats parse correctly."""
    normalizer = DateNormalizer()

    d1, err1 = normalizer.normalize("2026-10-01")
    assert d1 == date(2026, 10, 1)
    assert err1 is None

    d2, err2 = normalizer.normalize("02/10/2026")
    assert d2 == date(2026, 10, 2)
    assert err2 is None

    d3, err3 = normalizer.normalize("2026/10/15")
    assert d3 == date(2026, 10, 15)
    assert err3 is None

    d_bad, err_bad = normalizer.normalize("NOT_A_DATE")
    assert d_bad is None
    assert err_bad is not None


def test_amount_normalizer() -> None:
    """Verify amounts with currency symbols, commas, and signed values are normalized to positive Decimals."""
    normalizer = AmountNormalizer()

    # Debit / Credit explicit
    amt1, dir1, err1 = normalizer.normalize(debit_val="1,450.50", credit_val="")
    assert amt1 == Decimal("1450.50")
    assert dir1 == "debit"
    assert err1 is None

    amt2, dir2, err2 = normalizer.normalize(debit_val="", credit_val="₹85,000.00")
    assert amt2 == Decimal("85000.00")
    assert dir2 == "credit"
    assert err2 is None

    # Single signed amount
    amt3, dir3, err3 = normalizer.normalize(amount_val="-340.50")
    assert amt3 == Decimal("340.50")
    assert dir3 == "debit"
    assert err3 is None

    amt4, dir4, err4 = normalizer.normalize(amount_val="+1,250.00")
    assert amt4 == Decimal("1250.00")
    assert dir4 == "credit"
    assert err4 is None

    # Accounting parentheses (500.00)
    amt5, dir5, err5 = normalizer.normalize(amount_val="(500.00)")
    assert amt5 == Decimal("500.00")
    assert dir5 == "debit"
    assert err5 is None


def test_merchant_normalizer() -> None:
    """Verify prefix removal, channel stripping, and alias resolution."""
    normalizer = MerchantNormalizer()

    m1, clean1 = normalizer.normalize("UPI-SWIGGY-18293@ICICI")
    assert m1 == "Swiggy"
    assert "SWIGGY" in clean1.upper()

    m2, _ = normalizer.normalize("BLINKIT ORDER #89128 BANGALORE")
    assert m2 == "Blinkit"

    m3, _ = normalizer.normalize("NETFLIX MUMBAI IN 918239")
    assert m3 == "Netflix"

    m4, _ = normalizer.normalize("ZOMATO RESTAURANTS PVT")
    assert m4 == "Zomato"


def test_transaction_classifier() -> None:
    """Verify internal transfers and refunds are distinguished from standard income/expenses."""
    classifier = TransactionClassifier()

    # Own account transfer -> must be excluded from income/expense
    tx_type1, is_ex1, warns1 = classifier.classify_for_audit(
        direction="debit",
        description="TRF TO OWN ACCT 987654",
        merchant_name=None,
    )
    assert tx_type1 == "transfer"
    assert is_ex1 is True
    assert any("Excluded own-account" in w for w in warns1)

    # Refund -> must not be counted as salary/ordinary income
    tx_type2, is_ex2, _ = classifier.classify_for_audit(
        direction="credit",
        description="REFUND - AMAZON PAY INDIA",
        merchant_name="Amazon",
    )
    assert tx_type2 == "refund"
    assert is_ex2 is False

    # Salary credit
    tx_type3, is_ex3, _ = classifier.classify_for_audit(
        direction="credit",
        description="SALARY CREDIT - ACME TECH",
        merchant_name=None,
    )
    assert tx_type3 == "income"
    assert is_ex3 is False

    # Regular expense
    tx_type4, is_ex4, _ = classifier.classify_for_audit(
        direction="debit",
        description="BLINKIT ORDER #89128",
        merchant_name="Blinkit",
    )
    assert tx_type4 == "expense"
    assert is_ex4 is False


def test_duplicate_fingerprint_determinism() -> None:
    """Verify fingerprint generator is deterministic and invariant across instances."""
    gen = DuplicateFingerprintGenerator()
    u_id = uuid.uuid4()
    d = date(2026, 10, 5)
    amt = Decimal("649.00")
    desc = "NETFLIX MUMBAI IN"

    fp1 = gen.generate(u_id, None, d, amt, desc)
    fp2 = gen.generate(u_id, None, d, amt, desc)
    assert fp1 == fp2
    assert len(fp1) == 64  # SHA-256


# ==============================================================================
# 3. STATEMENT PARSER TESTS (CSV & PDF FIXTURES)
# ==============================================================================


def test_standard_csv_ingestion() -> None:
    """Verify parsing standard CSV with separate debit and credit columns."""
    csv_bytes = (FIXTURES_DIR / "statement_standard.csv").read_bytes()
    pipeline = IngestionPipeline()
    preview, source_type = pipeline.process("statement_standard.csv", csv_bytes, uuid.uuid4())

    assert source_type == "csv"
    assert preview.total_rows == 7
    assert preview.valid_count == 7
    assert preview.rejected_count == 0

    # Verify classification of refund and transfer
    descriptions = [r.original_description for r in preview.valid_rows]
    assert any("SALARY" in d for d in descriptions)
    assert any("TRF TO OWN ACCT" in d for d in descriptions)
    assert any("REFUND" in d for d in descriptions)

    refund_row = next(r for r in preview.valid_rows if "REFUND" in r.original_description)
    assert refund_row.transaction_type == "refund"
    assert refund_row.direction == "credit"
    assert refund_row.amount == Decimal("899.00")

    transfer_row = next(r for r in preview.valid_rows if "TRF TO OWN ACCT" in r.original_description)
    assert transfer_row.transaction_type == "transfer"
    assert transfer_row.is_excluded is True


def test_signed_amount_csv_ingestion() -> None:
    """Verify CSV with single signed amount column (+ for credit, - for debit)."""
    csv_bytes = (FIXTURES_DIR / "statement_signed_amount.csv").read_bytes()
    pipeline = IngestionPipeline()
    preview, _ = pipeline.process("statement_signed_amount.csv", csv_bytes, uuid.uuid4())

    assert preview.total_rows == 5
    assert preview.valid_count == 5

    uber_row = next(r for r in preview.valid_rows if "UBER" in r.original_description)
    assert uber_row.direction == "debit"
    assert uber_row.amount == Decimal("340.00")

    interest_row = next(r for r in preview.valid_rows if "INTEREST" in r.original_description)
    assert interest_row.direction == "credit"
    assert interest_row.amount == Decimal("1250.00")


def test_alternate_headers_csv_ingestion() -> None:
    """Verify CSV with alternate header aliases (Narrative, Withdrawal, Deposit)."""
    csv_bytes = (FIXTURES_DIR / "statement_alternate_headers.csv").read_bytes()
    pipeline = IngestionPipeline()
    preview, _ = pipeline.process("statement_alternate_headers.csv", csv_bytes, uuid.uuid4())

    assert preview.total_rows == 4
    assert preview.valid_count == 4
    assert "Zomato" in [r.merchant_name for r in preview.valid_rows]


def test_utf8_bom_csv_ingestion() -> None:
    """Verify UTF-8 BOM encoding does not corrupt header matching."""
    csv_bytes = (FIXTURES_DIR / "statement_utf8_bom.csv").read_bytes()
    pipeline = IngestionPipeline()
    preview, _ = pipeline.process("statement_utf8_bom.csv", csv_bytes, uuid.uuid4())

    assert preview.valid_count == 2
    assert preview.valid_rows[0].transaction_date == date(2026, 10, 1)


def test_malformed_csv_preserves_valid_and_rejects_bad_rows() -> None:
    """Verify malformed lines are audited into rejected_rows without crashing the pipeline."""
    csv_bytes = (FIXTURES_DIR / "statement_malformed.csv").read_bytes()
    pipeline = IngestionPipeline()
    preview, _ = pipeline.process("statement_malformed.csv", csv_bytes, uuid.uuid4())

    # File has 2 valid rows, 2 invalid data rows, 1 malformed column row, 1 empty row skipped
    assert preview.valid_count >= 2
    assert preview.rejected_count >= 2
    assert len(preview.rejected_rows) >= 2

    # Check error reasons exist
    for rej in preview.rejected_rows:
        assert len(rej.error) > 0


def test_clean_text_pdf_ingestion() -> None:
    """Verify text-based tabular PDF statement extraction."""
    pdf_bytes = (FIXTURES_DIR / "statement_clean_text.pdf").read_bytes()
    pipeline = IngestionPipeline()
    preview, source_type = pipeline.process("statement_clean_text.pdf", pdf_bytes, uuid.uuid4())

    assert source_type == "pdf_text"
    assert preview.valid_count >= 5
    # Should extract salary, swiggy, netflix
    descriptions = [r.original_description for r in preview.valid_rows]
    assert any("SALARY" in d for d in descriptions)
    assert any("NETFLIX" in d for d in descriptions)


def test_multipage_pdf_ingestion() -> None:
    """Verify multi-page PDF extracts records across multiple pages."""
    pdf_bytes = (FIXTURES_DIR / "statement_multipage.pdf").read_bytes()
    pipeline = IngestionPipeline()
    preview, _ = pipeline.process("statement_multipage.pdf", pdf_bytes, uuid.uuid4())

    assert preview.valid_count >= 4
    pages = {r.page_number for r in preview.valid_rows}
    assert len(pages) >= 2, "Rows should be extracted from multiple pages"


def test_scanned_image_only_pdf_rejection() -> None:
    """Verify image-only / scanned PDF without text layer is gracefully flagged."""
    pdf_bytes = (FIXTURES_DIR / "statement_scanned_image_only.pdf").read_bytes()
    pipeline = IngestionPipeline()
    preview, _ = pipeline.process("statement_scanned_image_only.pdf", pdf_bytes, uuid.uuid4())

    # Zero text extracted should produce a clear scanned warning or rejection
    assert preview.valid_count == 0
    assert any("scanned" in w.lower() or "ocr" in w.lower() for w in preview.warnings)


# ==============================================================================
# 4. DUPLICATE DETECTION AND IN-BATCH DUPLICATION
# ==============================================================================


def test_in_batch_duplicate_detection() -> None:
    """Verify exact duplicate rows in the same file are flagged."""
    csv_bytes = (FIXTURES_DIR / "statement_duplicates.csv").read_bytes()
    pipeline = IngestionPipeline()
    preview, _ = pipeline.process("statement_duplicates.csv", csv_bytes, uuid.uuid4())

    duplicates = [r for r in preview.valid_rows if r.duplicate_status == "exact_duplicate"]
    assert len(duplicates) >= 1
    # Duplicate rows should not be included by default
    assert duplicates[0].is_included_by_default is False


# ==============================================================================
# 5. END-TO-END IMPORT API LIFECYCLE AND IDEMPOTENCY
# ==============================================================================


@pytest.mark.asyncio
async def test_full_import_api_lifecycle(client_with_db: TestClient, test_db_session: AsyncSession) -> None:
    """Test full upload -> preview -> confirm lifecycle via REST API."""
    # 1. Provision user
    test_user_id = uuid.uuid4()
    user = User(
        id=test_user_id,
        display_name="Test Ingestion User",
        email="ingestion.test@example.com",
        locale="en-IN",
        timezone="Asia/Kolkata",
        default_currency="INR",
    )
    test_db_session.add(user)
    await test_db_session.commit()

    headers = {"X-User-Id": str(test_user_id)}
    csv_path = FIXTURES_DIR / "statement_standard.csv"

    # 2. Upload statement
    with open(csv_path, "rb") as f:
        upload_resp = client_with_db.post(
            "/api/v1/imports",
            files={"file": ("statement_standard.csv", f, "text/csv")},
            headers=headers,
        )

    assert upload_resp.status_code == 201
    upload_data = upload_resp.json()["data"]
    import_id = upload_data["id"]
    assert upload_data["status"] == "preview_ready"
    assert upload_data["total_rows"] == 7

    # 3. Get preview
    preview_resp = client_with_db.get(f"/api/v1/imports/{import_id}/preview", headers=headers)
    assert preview_resp.status_code == 200
    preview_data = preview_resp.json()["data"]
    assert preview_data["valid_count"] == 7
    assert len(preview_data["valid_rows"]) == 7

    # 4. Confirm import
    confirm_resp = client_with_db.post(
        f"/api/v1/imports/{import_id}/confirm",
        json={"accepted_row_ids": None, "excluded_row_ids": []},
        headers=headers,
    )
    assert confirm_resp.status_code == 200
    confirm_data = confirm_resp.json()["data"]
    assert confirm_data["status"] == "completed"
    assert confirm_data["committed_transactions_count"] == 7

    # 5. Verify database transactions were created
    tx_stmt = select(Transaction).where(Transaction.user_id == test_user_id)
    tx_result = await test_db_session.execute(tx_stmt)
    transactions = tx_result.scalars().all()
    assert len(transactions) == 7

    # 6. Idempotency test: confirming a second time returns without duplicate insertion
    confirm_again_resp = client_with_db.post(
        f"/api/v1/imports/{import_id}/confirm",
        json={"accepted_row_ids": None, "excluded_row_ids": []},
        headers=headers,
    )
    assert confirm_again_resp.status_code == 200

    tx_stmt2 = select(Transaction).where(Transaction.user_id == test_user_id)
    tx_result2 = await test_db_session.execute(tx_stmt2)
    transactions2 = tx_result2.scalars().all()
    assert len(transactions2) == 7, "Idempotent confirmation must not insert duplicate transactions"


@pytest.mark.asyncio
async def test_cross_user_isolation(client_with_db: TestClient, test_db_session: AsyncSession) -> None:
    """Verify that User B cannot access or confirm User A's import batch (returns 404)."""
    user_a_id = uuid.uuid4()
    user_b_id = uuid.uuid4()

    # User A uploads a statement
    headers_a = {"X-User-Id": str(user_a_id)}
    csv_path = FIXTURES_DIR / "statement_standard.csv"
    with open(csv_path, "rb") as f:
        upload_resp = client_with_db.post(
            "/api/v1/imports",
            files={"file": ("statement_standard.csv", f, "text/csv")},
            headers=headers_a,
        )
    assert upload_resp.status_code == 201
    import_id = upload_resp.json()["data"]["id"]

    # User B attempts to access User A's import batch
    headers_b = {"X-User-Id": str(user_b_id)}
    get_resp = client_with_db.get(f"/api/v1/imports/{import_id}", headers=headers_b)
    assert get_resp.status_code == 404, "Cross-user batch inspection must return 404"

    # User B attempts to confirm User A's import batch
    confirm_resp = client_with_db.post(
        f"/api/v1/imports/{import_id}/confirm",
        json={},
        headers=headers_b,
    )
    assert confirm_resp.status_code == 404, "Cross-user batch confirmation must return 404"
