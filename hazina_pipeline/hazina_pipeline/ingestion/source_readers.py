#a reusable csv, xlsx, json, jsonl and parquet reader that:
# Accepts a file path and reader options.
# Reads the configured header row
# Handles encoding
# Normalizes column names by trimming surrounding whitespace
# Returns records as dictionaries
# Rejects missing headers, duplicate headers, and malformed CSV input
# Does not contain any source-specific logic -> will be handled by adapters


import csv
import json
from pathlib import Path
from typing import Any, Iterator

import pandas as pd
from openpyxl import load_workbook


class SourceReaderError(ValueError):
    """Raised when a source file cannot be read safely."""


def _validate_encoding(options: dict[str, Any]) -> str:
    encoding = options.get("encoding", "utf-8-sig")

    if not isinstance(encoding, str) or not encoding.strip():
        raise SourceReaderError(
            "encoding must be a non-empty string."
        )

    return encoding


def _validate_header_row(options: dict[str, Any]) -> int:
    header_row = options.get("header_row", 1)

    if (
        not isinstance(header_row, int)
        or isinstance(header_row, bool)
        or header_row < 1
    ):
        raise SourceReaderError(
            "header_row must be a positive integer."
        )

    return header_row


def _normalize_headers(headers: list[Any]) -> list[str]:
    normalized = [
        str(header).strip().lstrip("\ufeff")
        if header is not None else ""
        for header in headers
    ]

    if any(not header for header in normalized):
        raise SourceReaderError(
            "Source file contains empty column headers."
        )

    if len(normalized) != len(set(normalized)):
        raise SourceReaderError(
            "Source file contains duplicate column headers."
        )

    return normalized


def _validate_file(file_path: str | Path) -> Path:
    path = Path(file_path)

    if not path.is_file():
        raise SourceReaderError(
            f"Source file not found: {path}"
        )

    return path


class CSVReader:
    """Generic CSV reader shared by all file-based sources."""

    DEFAULT_ENCODING = "utf-8-sig"
    DEFAULT_HEADER_ROW = 1

    @classmethod
    def read(
        cls,
        file_path: str | Path,
        options: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        options = options or {}

        header_row = _validate_header_row(options)
        encoding = _validate_encoding(options)
        delimiter = options.get("delimiter", ",")

        if not isinstance(delimiter, str) or len(delimiter) != 1:
            raise SourceReaderError(
                "CSV delimiter must be a single character."
            )

        path = _validate_file(file_path)

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

                reader = csv.DictReader(
                    file,
                    delimiter=delimiter,
                )

                if not reader.fieldnames:
                    raise SourceReaderError(
                        "CSV file does not contain a header row."
                    )

                headers = _normalize_headers(reader.fieldnames)
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

        except SourceReaderError:
            raise
        except (OSError, UnicodeError, csv.Error) as exc:
            raise SourceReaderError(
                f"Unable to read CSV file {path}: {exc}"
            ) from exc


class XLSXReader:
    """Generic Excel workbook reader."""

    @classmethod
    def read(
        cls,
        file_path: str | Path,
        options: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        options = options or {}

        header_row = _validate_header_row(options)
        sheet_name = options.get("sheet_name")

        if sheet_name is not None and (
            not isinstance(sheet_name, str) or not sheet_name.strip()
        ):
            raise SourceReaderError(
                "sheet_name must be a non-empty string."
            )

        path = _validate_file(file_path)
        workbook = None

        try:
            workbook = load_workbook(
                path,
                read_only=True,
                data_only=True,
            )

            if sheet_name is not None:
                if sheet_name not in workbook.sheetnames:
                    raise SourceReaderError(
                        f"Worksheet not found: {sheet_name}"
                    )
                worksheet = workbook[sheet_name]
            else:
                worksheet = workbook.active

            header_values = next(
                worksheet.iter_rows(
                    min_row=header_row,
                    max_row=header_row,
                    values_only=True,
                ),
                None,
            )

            if not header_values:
                raise SourceReaderError(
                    "Excel worksheet does not contain a header row."
                )

            headers = _normalize_headers(list(header_values))

            for row_number, values in enumerate(
                worksheet.iter_rows(
                    min_row=header_row + 1,
                    values_only=True,
                ),
                start=header_row + 1,
            ):
                values = list(values)

                if len(values) > len(headers):
                    extra_values = values[len(headers):]

                    if any(value is not None for value in extra_values):
                        raise SourceReaderError(
                            f"Excel row {row_number} contains more values "
                            "than the header."
                        )

                values = values[:len(headers)]
                values.extend([None] * (len(headers) - len(values)))

                if not any(value is not None for value in values):
                    continue

                yield dict(zip(headers, values))

        except SourceReaderError:
            raise
        except Exception as exc:
            raise SourceReaderError(
                f"Unable to read Excel file {path}: {exc}"
            ) from exc
        finally:
            if workbook is not None:
                workbook.close()


def _resolve_record_path(
    data: Any,
    record_path: str,
) -> Any:
    current = data

    for key in record_path.split("."):
        if not isinstance(current, dict) or key not in current:
            raise SourceReaderError(
                f"JSON record_path could not be resolved: {record_path}"
            )

        current = current[key]

    return current


def _normalize_json_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized = {}

    for key, value in record.items():
        if not isinstance(key, str) or not key.strip():
            raise SourceReaderError(
                "JSON records must have non-empty string keys."
            )

        normalized_key = key.strip()

        if normalized_key in normalized:
            raise SourceReaderError(
                f"Duplicate JSON field after normalization: {normalized_key}"
            )

        normalized[normalized_key] = value

    return normalized


class JSONReader:
    """Generic JSON reader for arrays and individual JSON records."""

    @classmethod
    def read(
        cls,
        file_path: str | Path,
        options: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        options = options or {}

        encoding = _validate_encoding(options)
        record_path = options.get("record_path")

        if record_path is not None and (
            not isinstance(record_path, str) or not record_path.strip()
        ):
            raise SourceReaderError(
                "record_path must be a non-empty string."
            )

        path = _validate_file(file_path)

        try:
            with path.open("r", encoding=encoding) as file:
                data = json.load(file)

            if record_path:
                data = _resolve_record_path(data, record_path)

            if isinstance(data, dict):
                records = [data]
            elif isinstance(data, list):
                records = data
            else:
                raise SourceReaderError(
                    "JSON must contain an object or an array of objects."
                )

            if not records:
                raise SourceReaderError(
                    "JSON file contains no records."
                )

            for index, record in enumerate(records, start=1):
                if not isinstance(record, dict):
                    raise SourceReaderError(
                        f"JSON record {index} must be an object."
                    )

                yield _normalize_json_record(record)

        except SourceReaderError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SourceReaderError(
                f"Unable to read JSON file {path}: {exc}"
            ) from exc


class JSONLReader:
    """Generic newline-delimited JSON reader."""

    @classmethod
    def read(
        cls,
        file_path: str | Path,
        options: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        options = options or {}
        encoding = _validate_encoding(options)
        path = _validate_file(file_path)

        try:
            with path.open("r", encoding=encoding) as file:
                record_count = 0

                for line_number, line in enumerate(file, start=1):
                    if not line.strip():
                        continue

                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise SourceReaderError(
                            f"Invalid JSON on line {line_number}: {exc}"
                        ) from exc

                    if not isinstance(record, dict):
                        raise SourceReaderError(
                            f"JSONL line {line_number} must contain an object."
                        )

                    record_count += 1
                    yield _normalize_json_record(record)

                if record_count == 0:
                    raise SourceReaderError(
                        "JSONL file contains no records."
                    )

        except SourceReaderError:
            raise
        except (OSError, UnicodeError) as exc:
            raise SourceReaderError(
                f"Unable to read JSONL file {path}: {exc}"
            ) from exc


class ParquetReader:
    """Generic Parquet reader using pandas and PyArrow."""

    @classmethod
    def read(
        cls,
        file_path: str | Path,
        options: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        options = options or {}
        columns = options.get("columns")

        if columns is not None and (
            not isinstance(columns, list)
            or not columns
            or any(
                not isinstance(column, str) or not column.strip()
                for column in columns
            )
            or len(columns) != len(set(columns))
        ):
            raise SourceReaderError(
                "Parquet columns must be a non-empty list of unique names."
            )

        path = _validate_file(file_path)

        try:
            dataframe = pd.read_parquet(
                path,
                columns=columns,
                engine="pyarrow",
            )

            headers = _normalize_headers(list(dataframe.columns))

            if dataframe.empty:
                raise SourceReaderError(
                    "Parquet file contains no records."
                )

            dataframe.columns = headers

            for record in dataframe.to_dict(orient="records"):
                yield record

        except SourceReaderError:
            raise
        except Exception as exc:
            raise SourceReaderError(
                f"Unable to read Parquet file {path}: {exc}"
            ) from exc


class FormatReaderRegistry:
    """Resolves file formats to their shared reader implementations."""

    _readers = {
        ".csv": CSVReader,
        ".xlsx": XLSXReader,
        ".json": JSONReader,
        ".jsonl": JSONLReader,
        ".parquet": ParquetReader,
    }

    @classmethod
    def get_reader(cls, file_path: str | Path):
        suffix = Path(file_path).suffix.lower()
        reader = cls._readers.get(suffix)

        if reader is None:
            raise SourceReaderError(
                f"Unsupported file format: {suffix or 'unknown'}"
            )

        return reader

    @classmethod
    def read(
        cls,
        file_path: str | Path,
        options: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        reader = cls.get_reader(file_path)
        return reader.read(file_path, options)
