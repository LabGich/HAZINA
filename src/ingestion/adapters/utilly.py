# This adapter does not perform transaction mapping or validation
# Its sole responsibility is converting the Utilly statement layout
# into clean source records and metadata
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.ingestion.source_readers import CSVReader, SourceReaderError


class SourceAdapterError(ValueError):
    """Raised when source-specific preprocessing fails."""


class UtillyStatementAdapter:
    """Preprocesses Utilly bank statement CSV files."""

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
    def read(
        cls,
        file_path: str | Path,
        reader_options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Extract statement metadata and return transaction records."""

        path = Path(file_path)
        options = reader_options or {}

        encoding = options.get("encoding", "utf-8")

        try:
            with path.open(
                "r",
                encoding=encoding,
                newline="",
            ) as file:
                preamble_reader = csv.reader(file)

                account_line = next(preamble_reader, None)
                period_line = next(preamble_reader, None)

        except (OSError, UnicodeError, csv.Error) as exc:
            raise SourceAdapterError(
                f"Unable to read Utilly statement preamble: {exc}"
            ) from exc

        if not account_line or not period_line:
            raise SourceAdapterError(
                "Utilly statement preamble is incomplete."
            )

        #The first line is a disclaimer. Account details are on line two
        account_text = " ".join(period_line)
        account_match = cls.ACCOUNT_PATTERN.search(account_text)

        if not account_match:
            raise SourceAdapterError(
                "Could not extract account identifier from Utilly statement."
            )

        account_id = account_match.group(0)

        if not period_line:
            raise SourceAdapterError(
                "Utilly statement period information is missing."
            )

        period_text = " ".join(period_line)
        period_match = cls.PERIOD_PATTERN.search(period_text)

        if not period_match:
            raise SourceAdapterError(
                "Could not extract statement period from Utilly statement."
            )

        try:
            period_start = datetime.strptime(
                period_match.group(1),
                "%m/%d/%Y",
            ).date()

            period_end = datetime.strptime(
                period_match.group(2),
                "%m/%d/%Y",
            ).date()

        except ValueError as exc:
            raise SourceAdapterError(
                "Utilly statement contains an invalid statement period."
            ) from exc

        if period_end < period_start:
            raise SourceAdapterError(
                "Utilly statement end date precedes its start date."
            )

        options = {
            **options,
            "header_row": options.get("header_row", 3),
        }

        try:
            records = list(CSVReader.read(path, options))
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
            description = record["Description"].strip().upper()

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
