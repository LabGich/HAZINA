# This adapter does not perform transaction mapping or validation.
# Its sole responsibility is converting the Utilly statement layout
# into clean source records and metadata.

import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from hazina_pipeline.ingestion.source_readers import (
    CSVReader,
    XLSXReader,
    SourceReaderError,
)


class SourceAdapterError(ValueError):
    """Raised when source-specific preprocessing fails."""


class UtillyStatementAdapter:
    """Preprocesses Utilly bank statement CSV and XLSX files."""

    ACCOUNT_PATTERN = re.compile(
        r"\b(?:X{2,}|\*{2,})?\d{4,}\b",
        re.IGNORECASE,
    )

    PERIOD_PATTERN = re.compile(
        r"(\d{2}/\d{2}/\d{4})\s+through\s+"
        r"(\d{2}/\d{2}/\d{4})",
        re.IGNORECASE,
    )

    REQUIRED_COLUMNS = {
        "Date",
        "Description",
        "Debit",
        "Credit",
        "Balance",
    }

    NON_TRANSACTION_DESCRIPTIONS = {
        "BEGINNING BALANCE",
        "TOTALS",
    }

    @classmethod
    def _read_preamble(
        cls,
        path: Path,
        options: dict[str, Any],
    ) -> tuple[str, str]:
        """Read account and statement-period information."""

        suffix = path.suffix.lower()

        try:
            if suffix == ".csv":
                encoding = options.get("encoding", "utf-8-sig")

                with path.open(
                    "r",
                    encoding=encoding,
                    newline="",
                ) as file:
                    reader = csv.reader(file)
                    next(reader, None)
                    period_line = next(reader, None)

                if not period_line:
                    raise SourceAdapterError(
                        "Utilly statement preamble is incomplete."
                    )

                account_text = " ".join(period_line)
                period_text = account_text

            elif suffix == ".xlsx":
                from openpyxl import load_workbook

                workbook = load_workbook(
                    path,
                    read_only=True,
                    data_only=True,
                )

                try:
                    sheet_name = options.get("sheet_name")

                    if sheet_name:
                        if sheet_name not in workbook.sheetnames:
                            raise SourceAdapterError(
                                f"Worksheet not found: {sheet_name}"
                            )
                        worksheet = workbook[sheet_name]
                    else:
                        worksheet = workbook.active

                    first_rows = list(
                        worksheet.iter_rows(
                            min_row=1,
                            max_row=2,
                            values_only=True,
                        )
                    )

                finally:
                    workbook.close()

                if len(first_rows) < 2:
                    raise SourceAdapterError(
                        "Utilly statement preamble is incomplete."
                    )

                period_line = first_rows[1]
                account_text = " ".join(
                    str(value)
                    for value in period_line
                    if value is not None
                )
                period_text = account_text

            else:
                raise SourceAdapterError(
                    f"Unsupported Utilly file format: {suffix}"
                )

        except SourceAdapterError:
            raise
        except (OSError, UnicodeError, csv.Error) as exc:
            raise SourceAdapterError(
                f"Unable to read Utilly statement preamble: {exc}"
            ) from exc

        account_match = cls.ACCOUNT_PATTERN.search(account_text)

        if not account_match:
            raise SourceAdapterError(
                "Could not extract account identifier from Utilly statement."
            )

        period_match = cls.PERIOD_PATTERN.search(period_text)

        if not period_match:
            raise SourceAdapterError(
                "Could not extract statement period from Utilly statement."
            )

        return account_match.group(0), period_match.group(0)

    @classmethod
    def read(
        cls,
        file_path: str | Path,
        reader_options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Extract statement metadata and return transaction records."""

        path = Path(file_path)
        options = reader_options or {}

        account_id, period_text = cls._read_preamble(path, options)

        period_match = cls.PERIOD_PATTERN.fullmatch(period_text)

        try:
            period_start = datetime.strptime(
                period_match.group(1),
                "%m/%d/%Y",
            ).date()

            period_end = datetime.strptime(
                period_match.group(2),
                "%m/%d/%Y",
            ).date()

        except (ValueError, AttributeError) as exc:
            raise SourceAdapterError(
                "Utilly statement contains an invalid statement period."
            ) from exc

        if period_end < period_start:
            raise SourceAdapterError(
                "Utilly statement end date precedes its start date."
            )

        reader_options = {
            **options,
            "header_row": options.get("header_row", 4),
        }

        suffix = path.suffix.lower()

        try:
            if suffix == ".csv":
                records = list(
                    CSVReader.read(path, reader_options)
                )
            elif suffix == ".xlsx":
                records = list(
                    XLSXReader.read(path, reader_options)
                )
            else:
                raise SourceAdapterError(
                    f"Unsupported Utilly file format: {suffix}"
                )

        except SourceReaderError:
            raise

        if not records:
            raise SourceAdapterError(
                "Utilly statement contains no transaction records."
            )

        actual_columns = set(records[0])
        missing_columns = cls.REQUIRED_COLUMNS - actual_columns

        if missing_columns:
            raise SourceAdapterError(
                "Utilly statement is missing required columns: "
                + ", ".join(sorted(missing_columns))
            )

        transactions = []

        for record in records:
            description = str(
                record.get("Description") or ""
            ).strip().upper()

            if description in cls.NON_TRANSACTION_DESCRIPTIONS:
                continue

            if not description:
                continue

            record["account_id"] = account_id
            transactions.append(record)

        if not transactions:
            raise SourceAdapterError(
                "No transaction rows found in Utilly statement."
            )

        return {
            "source_name": "UTILLY",
            "source_account_id": account_id,
            "statement_period_start": period_start.isoformat(),
            "statement_period_end": period_end.isoformat(),
            "records_received": len(records),
            "records_returned": len(transactions),
            "records": transactions,
        }
