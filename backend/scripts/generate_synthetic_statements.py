"""Deterministic generator for synthetic bank and credit card statement fixtures.

Generates diverse CSV and PDF test statements:
- Standard format with debit/credit columns
- Single signed amount column
- Alternate header aliases
- Duplicate rows
- Malformed rows for error resilience audit
- UTF-8 BOM encoded files
- Clean tabular text PDF
- Multi-page text PDF
- Image-only scanned PDF (for OCR unsupported validation)
"""

from pathlib import Path
import pymupdf as fitz


FIXTURES_DIR = Path(__file__).resolve().parent.parent / "app" / "tests" / "fixtures" / "statements"


def generate_standard_csv(output_path: Path) -> None:
    """Generate standard CSV with separate Debit and Credit columns."""
    content = (
        "Date,Description,Debit,Credit,Balance\n"
        "2026-10-01,SALARY CREDIT - ACME TECH PVT LTD,,85000.00,105000.00\n"
        "2026-10-02,BLINKIT ORDER #89128 BANGALORE,1450.50,,103549.50\n"
        "2026-10-03,UPI-SWIGGY-18293@ICICI,420.00,,103129.50\n"
        "2026-10-05,NETFLIX MUMBAI IN 918239,649.00,,102480.50\n"
        "2026-10-06,TRF TO OWN ACCT 987654,15000.00,,87480.50\n"
        "2026-10-08,REFUND - AMAZON PAY INDIA,,899.00,88379.50\n"
        "2026-10-10,AIRTEL FIBER BROADBAND BILL,1179.00,,87200.50\n"
    )
    output_path.write_text(content, encoding="utf-8")


def generate_signed_amount_csv(output_path: Path) -> None:
    """Generate CSV with a single signed amount column (+ credit, - debit)."""
    content = (
        "Txn Date,Particulars,Amount,Currency\n"
        "01/10/2026,INTEREST CREDIT,+1250.00,INR\n"
        "02/10/2026,UBER INDIA RIDES,-340.00,INR\n"
        "04/10/2026,AMAZON RETAIL INDIA,-2199.00,INR\n"
        "07/10/2026,ZERODHA BROKING LTD,-10000.00,INR\n"
        "12/10/2026,CASHBACK REWARD CREDIT,+250.00,INR\n"
    )
    output_path.write_text(content, encoding="utf-8")


def generate_alternate_headers_csv(output_path: Path) -> None:
    """Generate CSV with alternate column headers and slash dates."""
    content = (
        "Transaction Date,Narrative,Withdrawal,Deposit\n"
        "2026/10/10,ZOMATO RESTAURANTS PVT,580.00,\n"
        "2026/10/12,TATA POWER ELECTRICITY,2340.00,\n"
        "2026/10/15,CLIENT PAYMENT FOR PROJECT,,45000.00\n"
        "2026/10/18,STARBUCKS COFFEE KORAMANGALA,390.00,\n"
    )
    output_path.write_text(content, encoding="utf-8")


def generate_duplicates_csv(output_path: Path) -> None:
    """Generate CSV with duplicate and legitimate repeated rows."""
    content = (
        "Date,Description,Debit,Credit\n"
        "2026-10-03,UPI-SWIGGY-18293@ICICI,420.00,\n"
        "2026-10-03,UPI-SWIGGY-18293@ICICI,420.00,\n"  # Duplicate row
        "2026-10-05,NETFLIX MUMBAI IN 918239,649.00,\n"
        "2026-10-08,UBER RIDE,150.00,\n"
        "2026-10-08,UBER RIDE,150.00,\n"  # Second Uber ride same day
    )
    output_path.write_text(content, encoding="utf-8")


def generate_malformed_csv(output_path: Path) -> None:
    """Generate CSV containing valid rows alongside corrupted lines."""
    content = (
        "Date,Description,Debit,Credit\n"
        "2026-10-01,SALARY CREDIT,,75000.00\n"
        "INVALID-DATE,LOCAL GROCERY,350.00,\n"  # Invalid date
        "2026-10-03,CAFE COFFEE DAY,NOT_A_NUMBER,\n"  # Invalid amount
        "\n"  # Empty row
        "2026-10-04,BOOKSTORE PURCHASE,499.00,\n"
        "2026-10-05,TOO,MANY,COLUMNS,EXTRA,ROW,100.00\n"  # Mismatched columns
    )
    output_path.write_text(content, encoding="utf-8")


def generate_utf8_bom_csv(output_path: Path) -> None:
    """Generate CSV encoded with a UTF-8 Byte Order Mark (BOM)."""
    bom = b"\xef\xbb\xbf"
    text = (
        "Date,Description,Debit,Credit\n"
        "2026-10-01,MICROSOFT 365 SUBSCRIPTION,489.00,\n"
        "2026-10-05,GOOGLE STORAGE ONE 100GB,130.00,\n"
    )
    output_path.write_bytes(bom + text.encode("utf-8"))


def generate_clean_text_pdf(output_path: Path) -> None:
    """Generate a clean single-page text PDF statement with tabular layout."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4 size

    # Header title
    page.insert_text(fitz.Point(50, 50), "HDFC BANK LIMITED - ACCOUNT STATEMENT (SYNTHETIC)", fontsize=12)
    page.insert_text(fitz.Point(50, 70), "Account: 5010023456789 | Currency: INR", fontsize=10)
    page.insert_text(fitz.Point(50, 90), "Period: 01-Oct-2026 to 15-Oct-2026", fontsize=10)

    # Table headers
    y = 130
    page.insert_text(fitz.Point(50, y), "Date", fontsize=10)
    page.insert_text(fitz.Point(130, y), "Description", fontsize=10)
    page.insert_text(fitz.Point(380, y), "Debit", fontsize=10)
    page.insert_text(fitz.Point(460, y), "Credit", fontsize=10)

    # Separator line
    page.draw_line(fitz.Point(50, y + 5), fitz.Point(545, y + 5))

    # Transactions
    rows = [
        ("2026-10-01", "SALARY DIRECT DEP ACME CORP", "", "85000.00"),
        ("2026-10-02", "BLINKIT COMMERCE BANGALORE", "1250.00", ""),
        ("2026-10-03", "SWIGGY FOOD DELIVERY", "450.00", ""),
        ("2026-10-04", "NETFLIX ENTERTAINMENT IN", "649.00", ""),
        ("2026-10-06", "TRF TO OWN ACCT 1234", "10000.00", ""),
        ("2026-10-08", "REFUND AMAZON PAY RETAIL", "", "799.00"),
        ("2026-10-10", "AIRTEL FIBER INTERNET", "1179.00", ""),
    ]

    y += 25
    for dt, desc, dr, cr in rows:
        page.insert_text(fitz.Point(50, y), dt, fontsize=9)
        page.insert_text(fitz.Point(130, y), desc, fontsize=9)
        if dr:
            page.insert_text(fitz.Point(380, y), dr, fontsize=9)
        if cr:
            page.insert_text(fitz.Point(460, y), cr, fontsize=9)
        y += 20

    doc.save(str(output_path))
    doc.close()


def generate_multipage_pdf(output_path: Path) -> None:
    """Generate a multi-page statement PDF."""
    doc = fitz.open()

    # Page 1
    page1 = doc.new_page(width=595, height=842)
    page1.insert_text(fitz.Point(50, 50), "ICICI BANK STATEMENT - PAGE 1 OF 2 (SYNTHETIC)", fontsize=12)
    y = 100
    page1.insert_text(fitz.Point(50, y), "Date", fontsize=10)
    page1.insert_text(fitz.Point(130, y), "Description", fontsize=10)
    page1.insert_text(fitz.Point(400, y), "Debit", fontsize=10)
    page1.insert_text(fitz.Point(480, y), "Credit", fontsize=10)

    rows_p1 = [
        ("2026-10-01", "CONSULTING FEE INVOICE 101", "", "45000.00"),
        ("2026-10-03", "AMAZON WEB SERVICES AWS", "3250.00", ""),
        ("2026-10-05", "UBER RIDES MUMBAI", "420.00", ""),
    ]
    y += 25
    for dt, desc, dr, cr in rows_p1:
        page1.insert_text(fitz.Point(50, y), dt, fontsize=9)
        page1.insert_text(fitz.Point(130, y), desc, fontsize=9)
        if dr:
            page1.insert_text(fitz.Point(400, y), dr, fontsize=9)
        if cr:
            page1.insert_text(fitz.Point(480, y), cr, fontsize=9)
        y += 20

    # Page 2
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text(fitz.Point(50, 50), "ICICI BANK STATEMENT - PAGE 2 OF 2 (SYNTHETIC)", fontsize=12)
    y = 100
    page2.insert_text(fitz.Point(50, y), "Date", fontsize=10)
    page2.insert_text(fitz.Point(130, y), "Description", fontsize=10)
    page2.insert_text(fitz.Point(400, y), "Debit", fontsize=10)
    page2.insert_text(fitz.Point(480, y), "Credit", fontsize=10)

    rows_p2 = [
        ("2026-10-15", "GITHUB COPILOT SUBSCRIPTION", "820.00", ""),
        ("2026-10-18", "SPOTIFY PREMIUM FAMILY", "179.00", ""),
        ("2026-10-20", "INTEREST REBATE", "", "150.00"),
    ]
    y += 25
    for dt, desc, dr, cr in rows_p2:
        page2.insert_text(fitz.Point(50, y), dt, fontsize=9)
        page2.insert_text(fitz.Point(130, y), desc, fontsize=9)
        if dr:
            page2.insert_text(fitz.Point(400, y), dr, fontsize=9)
        if cr:
            page2.insert_text(fitz.Point(480, y), cr, fontsize=9)
        y += 20

    doc.save(str(output_path))
    doc.close()


def generate_scanned_image_pdf(output_path: Path) -> None:
    """Generate an image-only PDF with no text layer (scanned statement simulation)."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # Draw geometric shapes/rectangles without text elements
    page.draw_rect(fitz.Rect(50, 50, 545, 80), color=(0.8, 0.8, 0.8), fill=(0.9, 0.9, 0.9))
    page.draw_rect(fitz.Rect(50, 100, 545, 400), color=(0.7, 0.7, 0.7), fill=(0.95, 0.95, 0.95))

    doc.save(str(output_path))
    doc.close()


def generate_all_fixtures() -> None:
    """Create all synthetic test statements in the fixtures directory."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    generate_standard_csv(FIXTURES_DIR / "statement_standard.csv")
    generate_signed_amount_csv(FIXTURES_DIR / "statement_signed_amount.csv")
    generate_alternate_headers_csv(FIXTURES_DIR / "statement_alternate_headers.csv")
    generate_duplicates_csv(FIXTURES_DIR / "statement_duplicates.csv")
    generate_malformed_csv(FIXTURES_DIR / "statement_malformed.csv")
    generate_utf8_bom_csv(FIXTURES_DIR / "statement_utf8_bom.csv")

    generate_clean_text_pdf(FIXTURES_DIR / "statement_clean_text.pdf")
    generate_multipage_pdf(FIXTURES_DIR / "statement_multipage.pdf")
    generate_scanned_image_pdf(FIXTURES_DIR / "statement_scanned_image_only.pdf")

    print(f"Generated 9 synthetic statements in {FIXTURES_DIR}")


if __name__ == "__main__":
    generate_all_fixtures()
