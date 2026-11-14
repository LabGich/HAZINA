#a reusable csv reader that:
# Accepts a file path and reader options.
# Reads the configured header row
# Handles encoding
# Normalizes column names by trimming surrounding whitespace
# Returns records as dictionaries
# Rejects missing headers, duplicate headers, and malformed CSV input
# Does not contain any source-specific logic -> will be handled by adapters

import csv
from pathlib import Path
from typing import Any, Iterator

class SourceReaderError(ValueError):
    """Raised when a source file cannot be read safely."""


class CSVReader:
    """Generic CSV reader shared by all file-based sources."""

    DEFAULT_ENCODING = "utf-8"
    DEFAULT_HEADER_ROW = 1

    @classmethod
    def read(
        cls,
        file_path: str | Path,
        options: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, str]]:
        """Read CSV records using validated reader options."""

        options = options or {}

        header_row = options.get(
            "header_row",
            cls.DEFAULT_HEADER_ROW,
        )
        encoding = options.get(
            "encoding",
            cls.DEFAULT_ENCODING,
        )

        if (
            not isinstance(header_row, int)
            or isinstance(header_row, bool)
            or header_row < 1
        ):
            raise SourceReaderError(
                "header_row must be a positive integer."
            )

        if not isinstance(encoding, str) or not encoding.strip():
            raise SourceReaderError(
                "encoding must be a non-empty string."
            )

        path = Path(file_path)

        if not path.is_file():
            raise SourceReaderError(
                f"Source file not found: {path}"
            )

        try:
            with path.open(
                "r",
                encoding=encoding,
                newline="",
            ) as file:
                for _ in range(header_row - 1):
                    if file.readline() == "":
                        raise SourceReaderError(
                            "Configured header row exceeds file length."
                        )

                reader = csv.DictReader(file)

                if not reader.fieldnames:
                    raise SourceReaderError(
                        "CSV file does not contain a header row."
                    )

                headers = [
                    header.strip() if header else ""
                    for header in reader.fieldnames
                ]

                if any(not header for header in headers):
                    raise SourceReaderError(
                        "CSV headers cannot be empty."
                    )

                if len(headers) != len(set(headers)):
                    raise SourceReaderError(
                        "CSV contains duplicate column headers."
                    )

                reader.fieldnames = headers

                for row_number, record in enumerate(
                    reader,
                    start=header_row + 1,
                ):
                    if None in record:
                        raise SourceReaderError(
                            f"CSV row {row_number} contains more values "
                            "than the header."
                        )

                    if not any(
                        value is not None and value.strip()
                        for value in record.values()
                    ):
                        continue

                    yield {
                        key: value.strip() if value is not None else ""
                        for key, value in record.items()
                    }

        except (OSError, UnicodeError, csv.Error) as exc:
            raise SourceReaderError(
                f"Unable to read CSV file {path}: {exc}"
            ) from exc
