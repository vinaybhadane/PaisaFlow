"""Text-based PDF financial statement parser."""

import io
import re
from typing import Dict, List, Optional, Tuple
import pdfplumber

from backend.app.ingestion.parsers.base import BaseStatementParser, ParseResult, ParsedRow
from backend.app.ingestion.parsers.csv_parser import CSVStatementParser


class PDFStatementParser(BaseStatementParser):
    """Parser for text-based PDF bank statements extracting tabular transaction data."""

    DATE_PATTERN = re.compile(
        r"^(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}|\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self.csv_helper = CSVStatementParser()

    def _extract_from_tables(
        self,
        pdf: pdfplumber.PDF,
    ) -> Tuple[List[ParsedRow], List[ParsedRow], List[str], Dict[str, str]]:
        """Extract transactions from PDF table structures across all pages."""
        valid_rows: List[ParsedRow] = []
        rejected_rows: List[ParsedRow] = []
        warnings: List[str] = []
        detected_col_names: Dict[str, str] = {}

        global_header_indices: Optional[Dict[str, int]] = None

        row_counter = 0

        for page_idx, page in enumerate(pdf.pages):
            page_num = page_idx + 1
            tables = page.extract_tables()

            for table in tables:
                if not table or len(table) < 2:
                    continue

                cleaned_table = [
                    [str(cell).strip() if cell is not None else "" for cell in row]
                    for row in table
                ]

                # Find header in first page or first table if not already identified
                if global_header_indices is None:
                    _, col_indices, col_names = self.csv_helper._detect_header_row(cleaned_table)
                    if "date" in col_indices and any(r in col_indices for r in ["amount", "debit", "credit"]):
                        global_header_indices = col_indices
                        detected_col_names = col_names

                if global_header_indices is None:
                    continue

                for row in cleaned_table:
                    # Skip empty rows
                    if not any(row):
                        continue

                    # Skip repeated header rows across pages
                    if any("date" in str(c).lower() for c in row) and any("amount" in str(c).lower() or "debit" in str(c).lower() for c in row):
                        continue

                    row_counter += 1

                    def get_cell(role: str) -> Optional[str]:
                        if role in global_header_indices and global_header_indices[role] < len(row):
                            val = row[global_header_indices[role]].strip()
                            return val if val else None
                        return None

                    date_str = get_cell("date")
                    desc_str = get_cell("description") or "Unspecified Description"
                    debit_str = get_cell("debit")
                    credit_str = get_cell("credit")
                    amount_str = get_cell("amount")
                    ref_str = get_cell("reference")
                    bal_str = get_cell("balance")

                    # Check validity
                    row_errors: List[str] = []
                    if not date_str or not self.DATE_PATTERN.search(date_str):
                        row_errors.append("Invalid or missing date cell.")

                    has_money = any(
                        val is not None and val != "" for val in [debit_str, credit_str, amount_str]
                    )
                    if not has_money:
                        row_errors.append("No monetary value identified in row.")

                    parsed_row = ParsedRow(
                        row_index=row_counter,
                        page_number=page_num,
                        raw_data={"row": row, "page": page_num},
                        date_str=date_str,
                        description_str=desc_str,
                        debit_str=debit_str,
                        credit_str=credit_str,
                        amount_str=amount_str,
                        reference_str=ref_str,
                        balance_str=bal_str,
                        is_valid=len(row_errors) == 0,
                        error="; ".join(row_errors) if row_errors else None,
                    )

                    if parsed_row.is_valid:
                        valid_rows.append(parsed_row)
                    else:
                        rejected_rows.append(parsed_row)

        return valid_rows, rejected_rows, warnings, detected_col_names

    def _extract_from_text_lines(
        self,
        pdf: pdfplumber.PDF,
    ) -> Tuple[List[ParsedRow], List[ParsedRow], List[str]]:
        """Fallback line-based extraction when explicit table borders are not present."""
        valid_rows: List[ParsedRow] = []
        rejected_rows: List[ParsedRow] = []
        warnings: List[str] = []

        # Money pattern: e.g. 1,250.00 or 15000.00 or -450.00
        amount_pattern = re.compile(r"[-+]?(?:Rs\.?|INR|₹)?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})|[0-9]+(?:\.[0-9]{2}))")

        row_counter = 0

        for page_idx, page in enumerate(pdf.pages):
            page_num = page_idx + 1
            text = page.extract_text() or ""
            lines = [line_str.strip() for line_str in text.splitlines() if line_str.strip()]

            for line in lines:
                date_match = self.DATE_PATTERN.search(line)
                if not date_match:
                    continue

                amounts = amount_pattern.findall(line)
                if not amounts:
                    continue

                row_counter += 1
                date_str = date_match.group(1).strip()

                # Remainder of line contains description and amounts
                line_rest = line[date_match.end() :].strip()
                # Clean amounts from description text
                desc_str = amount_pattern.sub("", line_rest).strip() or "Transaction"

                # Check if DR or CR indicator is present
                is_debit = bool(re.search(r"\b(DR|DEBIT|WITHDRAWAL)\b", line, re.IGNORECASE))
                is_credit = bool(re.search(r"\b(CR|CREDIT|DEPOSIT)\b", line, re.IGNORECASE))

                parsed_amount = amounts[0].replace(",", "")
                debit_str = parsed_amount if is_debit and not is_credit else None
                credit_str = parsed_amount if is_credit else None
                amt_str = parsed_amount if not debit_str and not credit_str else None

                parsed_row = ParsedRow(
                    row_index=row_counter,
                    page_number=page_num,
                    raw_data={"line": line, "page": page_num},
                    date_str=date_str,
                    description_str=desc_str,
                    debit_str=debit_str,
                    credit_str=credit_str,
                    amount_str=amt_str,
                    direction_hint="debit" if is_debit else ("credit" if is_credit else None),
                    is_valid=True,
                )
                valid_rows.append(parsed_row)

        return valid_rows, rejected_rows, warnings

    def parse(self, file_bytes: bytes, filename: str = "statement.pdf") -> ParseResult:
        """Parse text-based PDF bytes into structured transactions."""
        warnings: List[str] = []

        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                if not pdf.pages:
                    return ParseResult(
                        total_rows=0,
                        valid_rows=[],
                        rejected_rows=[],
                        warnings=["PDF document contains no pages."],
                        column_mapping={},
                        source_type="pdf_text",
                    )

                # Check if PDF contains any extractable text layer
                total_text = "".join((p.extract_text() or "") for p in pdf.pages[:3])
                if not total_text.strip():
                    # Scanned PDF without OCR text
                    return ParseResult(
                        total_rows=0,
                        valid_rows=[],
                        rejected_rows=[],
                        warnings=[
                            "Scanned or image-only PDF detected. This phase supports text-based PDF statements with digital text layers."
                        ],
                        column_mapping={},
                        source_type="pdf_text",
                    )

                # Attempt table extraction first
                valid_rows, rejected_rows, table_warnings, col_mapping = self._extract_from_tables(pdf)
                warnings.extend(table_warnings)

                # If table extraction yielded nothing, fallback to regex line-by-line parsing
                if not valid_rows:
                    valid_rows, rejected_rows, text_warnings = self._extract_from_text_lines(pdf)
                    warnings.extend(text_warnings)

                return ParseResult(
                    total_rows=len(valid_rows) + len(rejected_rows),
                    valid_rows=valid_rows,
                    rejected_rows=rejected_rows,
                    warnings=warnings,
                    column_mapping=col_mapping,
                    source_type="pdf_text",
                )
        except Exception as e:
            return ParseResult(
                total_rows=0,
                valid_rows=[],
                rejected_rows=[],
                warnings=[f"PDF parsing error: {e}"],
                column_mapping={},
                source_type="pdf_text",
            )
