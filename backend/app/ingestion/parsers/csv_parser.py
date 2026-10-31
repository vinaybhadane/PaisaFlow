"""Robust CSV financial statement parser."""

import csv
import io
import re
from typing import Dict, List, Optional, Tuple

from backend.app.ingestion.parsers.base import BaseStatementParser, ParseResult, ParsedRow


class CSVStatementParser(BaseStatementParser):
    """Parser for diverse bank and financial CSV statement exports."""

    # Candidate header aliases
    HEADER_CANDIDATES = {
        "date": [
            "date", "txn date", "txndate", "transaction date", "value date",
            "posting date", "post date", "trans date", "txn_date", "trans_date"
        ],
        "description": [
            "description", "particulars", "narration", "narrative", "details", "remarks",
            "transaction details", "merchant", "payee", "transaction remarks", "memo",
            "narrative text", "party name", "transaction description"
        ],
        "debit": [
            "debit", "withdrawal", "dr", "dr amount", "debit amount",
            "withdrawal amount", "withdrawals", "paid out", "debit (inr)"
        ],
        "credit": [
            "credit", "deposit", "cr", "cr amount", "credit amount",
            "deposit amount", "deposits", "paid in", "credit (inr)"
        ],
        "amount": [
            "amount", "txn amount", "transaction amount", "net amount", "amt"
        ],
        "direction": [
            "type", "dr/cr", "cr/dr", "indicator", "drcr", "txn type"
        ],
        "reference": [
            "ref no", "reference no", "reference", "utr", "cheque no",
            "chq no", "txn id", "transaction id", "ref", "reference number"
        ],
        "balance": [
            "balance", "closing balance", "available balance", "running balance"
        ],
    }

    def _decode_bytes(self, file_bytes: bytes) -> str:
        """Decode CSV bytes using BOM-aware UTF-8 or Latin-1 fallback."""
        for encoding in ["utf-8-sig", "utf-8", "latin-1"]:
            try:
                return file_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue
        return file_bytes.decode("utf-8", errors="replace")

    def _normalize_header(self, text: str) -> str:
        """Normalize header string for matching."""
        return re.sub(r"[^\w\s]", "", str(text).lower()).strip()

    def _detect_header_row(self, rows: List[List[str]]) -> Tuple[int, Dict[str, int], Dict[str, str]]:
        """Identify header row and map detected columns to roles."""
        best_row_idx = -1
        best_score = 0
        best_mapping: Dict[str, int] = {}
        best_col_names: Dict[str, str] = {}

        for idx, row in enumerate(rows[:15]):  # Check first 15 rows for header
            if not row:
                continue

            current_mapping: Dict[str, int] = {}
            current_col_names: Dict[str, str] = {}
            score = 0

            for col_idx, col_val in enumerate(row):
                norm_col = self._normalize_header(col_val)
                if not norm_col:
                    continue

                for role, aliases in self.HEADER_CANDIDATES.items():
                    if role not in current_mapping:
                        if norm_col in aliases or any(alias in norm_col for alias in aliases):
                            current_mapping[role] = col_idx
                            current_col_names[role] = str(col_val).strip()
                            if role in ["date", "description", "amount", "debit", "credit"]:
                                score += 2
                            else:
                                score += 1
                            break

            # Need at least date and (amount or debit or credit)
            has_date = "date" in current_mapping
            has_money = any(r in current_mapping for r in ["amount", "debit", "credit"])

            if has_date and has_money and score > best_score:
                best_score = score
                best_row_idx = idx
                best_mapping = current_mapping
                best_col_names = current_col_names

        return best_row_idx, best_mapping, best_col_names

    def parse(self, file_bytes: bytes, filename: str = "statement.csv") -> ParseResult:
        """Parse CSV bytes into structured ParseResult."""
        text_content = self._decode_bytes(file_bytes)
        f = io.StringIO(text_content)

        # Detect delimiter
        sample = text_content[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        except Exception:
            dialect = csv.excel

        reader = csv.reader(f, dialect=dialect)
        all_rows = [row for row in reader]

        if not all_rows:
            return ParseResult(
                total_rows=0,
                valid_rows=[],
                rejected_rows=[],
                warnings=["CSV file contains no data rows."],
                column_mapping={},
                source_type="csv",
            )

        header_idx, col_indices, col_names = self._detect_header_row(all_rows)

        if header_idx == -1 or "date" not in col_indices:
            # Cannot identify table structure
            return ParseResult(
                total_rows=len(all_rows),
                valid_rows=[],
                rejected_rows=[
                    ParsedRow(
                        row_index=i + 1,
                        raw_data={"row": row},
                        is_valid=False,
                        error="Cannot detect valid transaction header structure (missing date/amount headers).",
                    )
                    for i, row in enumerate(all_rows[:10])
                ],
                warnings=["Could not automatically detect valid bank statement headers."],
                column_mapping={},
                source_type="csv",
            )

        valid_rows: List[ParsedRow] = []
        rejected_rows: List[ParsedRow] = []
        warnings: List[str] = []

        data_rows = all_rows[header_idx + 1 :]

        for offset, row in enumerate(data_rows):
            actual_row_idx = header_idx + offset + 2

            # Skip empty or whitespace-only rows
            if not row or not any(str(c).strip() for c in row):
                continue

            row_dict = {
                all_rows[header_idx][c_idx]: row[c_idx]
                for c_idx in range(min(len(row), len(all_rows[header_idx])))
            }

            def get_val(role: str) -> Optional[str]:
                if role in col_indices and col_indices[role] < len(row):
                    val = str(row[col_indices[role]]).strip()
                    return val if val else None
                return None

            date_str = get_val("date")
            desc_str = get_val("description") or "Unspecified Description"
            debit_str = get_val("debit")
            credit_str = get_val("credit")
            amount_str = get_val("amount")
            direction_hint = get_val("direction")
            ref_str = get_val("reference")
            bal_str = get_val("balance")

            row_warnings: List[str] = []
            row_errors: List[str] = []

            if not date_str:
                row_errors.append("Missing transaction date in row.")

            # Validate that at least one amount field is present
            has_debit = debit_str is not None and debit_str.strip() != ""
            has_credit = credit_str is not None and credit_str.strip() != ""
            has_amount = amount_str is not None and amount_str.strip() != ""

            if not (has_debit or has_credit or has_amount):
                row_errors.append("No debit, credit, or net amount found in row.")

            parsed_row = ParsedRow(
                row_index=actual_row_idx,
                raw_data=row_dict,
                date_str=date_str,
                description_str=desc_str,
                debit_str=debit_str,
                credit_str=credit_str,
                amount_str=amount_str,
                direction_hint=direction_hint,
                reference_str=ref_str,
                balance_str=bal_str,
                warnings=row_warnings,
                is_valid=len(row_errors) == 0,
                error="; ".join(row_errors) if row_errors else None,
            )

            if parsed_row.is_valid:
                valid_rows.append(parsed_row)
            else:
                rejected_rows.append(parsed_row)

        return ParseResult(
            total_rows=len(data_rows),
            valid_rows=valid_rows,
            rejected_rows=rejected_rows,
            warnings=warnings,
            column_mapping=col_names,
            source_type="csv",
        )
