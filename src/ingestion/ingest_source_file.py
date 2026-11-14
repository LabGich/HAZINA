# Reuses SourceFileReader and get_database_connection().
# Preserves every original record in raw_payload
# Populates generic raw columns only when matching standardized field names exist
# Associates every raw record with its run_id and source_execution_id
# Commits raw records and execution counters together
# Does not update execution status; orchestration owns status transitions

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from psycopg.types.json import Jsonb

from src.database.connection import get_database_connection
from src.ingestion.source_file_reader import SourceFileReader


class SourceIngestionError(RuntimeError):
    """Raised when a source file cannot be persisted."""


def _json_safe(value: Any) -> Any:
    """Convert common non-JSON Python values into JSON-compatible values."""

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]

    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


def _raw_text(value: Any) -> str | None:
    """Convert an optional source value to its raw text representation."""

    if value is None:
        return None

    return str(value)


def ingest_source_file(
    run_id: int,
    source_execution_id: int,
    source_name: str,
    file_path: str | Path,
    source_file_reader: SourceFileReader | None = None,
) -> dict[str, Any]:
    """
    Read and persist one source file for a V2 source execution.

    Raw records and execution ingestion counters are committed together.
    Execution status transitions are handled by the orchestrator.
    """

    if not isinstance(run_id, int) or run_id <= 0:
        raise SourceIngestionError("run_id must be a positive integer.")

    if (
        not isinstance(source_execution_id, int)
        or source_execution_id <= 0
    ):
        raise SourceIngestionError(
            "source_execution_id must be a positive integer."
        )

    if not isinstance(source_name, str) or not source_name.strip():
        raise SourceIngestionError("source_name must be provided.")

    source_name = source_name.strip().upper()

    reader = source_file_reader or SourceFileReader()

    try:
        result = reader.read(
            source_name=source_name,
            file_path=file_path,
        )
    except Exception as exc:
        raise SourceIngestionError(
            f"Unable to read {source_name} source file: {exc}"
        ) from exc

    records = result["records"]

    if not records:
        raise SourceIngestionError(
            f"No records available for ingestion: {file_path}"
        )

    records_received = result["records_received"]
    records_loaded = len(records)

    metadata = result.get("metadata", {})
    file_name = result["file_name"]

    insert_sql = """
        INSERT INTO raw.transactions (
            transaction_id,
            customer_id,
            transaction_date,
            transaction_type,
            amount,
            currency,
            payment_method,
            status,
            source_file,
            run_id,
            raw_payload,
            source_name,
            source_type,
            source_transaction_id,
            source_account_id,
            source_reference,
            source_metadata,
            source_execution_id
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """

    counter_sql = """
        UPDATE ops.source_executions
        SET
            records_received = %s,
            records_loaded = %s
        WHERE source_execution_id = %s
    """

    try:
        with get_database_connection() as connection:
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    SELECT
                        sr.source_name,
                        se.execution_status
                    FROM ops.source_executions se
                    JOIN ops.source_registry sr
                        ON sr.source_id = se.source_id
                    WHERE se.source_execution_id = %s
                      AND se.run_id = %s
                    FOR UPDATE OF se
                    """,
                    (source_execution_id, run_id),
                )

                execution = cursor.fetchone()

                if execution is None:
                    raise SourceIngestionError(
                        "Source execution does not belong to "
                        "the supplied pipeline run."
                    )

                registered_source, execution_status = execution

                if registered_source.upper() != source_name:
                    raise SourceIngestionError(
                        "Source name does not match the registered "
                        "source execution."
                    )

                if execution_status != "RUNNING":
                    raise SourceIngestionError(
                        "Source execution must be RUNNING before "
                        "raw ingestion."
                    )

                for record in records:
                    if not isinstance(record, dict):
                        raise SourceIngestionError(
                            "Every source record must be a dictionary."
                        )

                    raw_payload = Jsonb(_json_safe(record))

                    source_metadata = {
                        "file_name": file_name,
                        "file_format": result["file_format"],
                        "record_metadata": metadata,
                    }

                    cursor.execute(
                        insert_sql,
                        (
                            _raw_text(record.get("transaction_id")),
                            _raw_text(record.get("customer_id")),
                            _raw_text(record.get("transaction_date")),
                            _raw_text(record.get("transaction_type")),
                            _raw_text(record.get("amount")),
                            _raw_text(record.get("currency")),
                            _raw_text(record.get("payment_method")),
                            _raw_text(record.get("status")),
                            file_name,
                            run_id,
                            raw_payload,
                            source_name,
                            "FILE",
                            _raw_text(record.get("source_transaction_id")),
                            _raw_text(
                                record.get("source_account_id")
                                or metadata.get("source_account_id")
                            ),
                            _raw_text(record.get("source_reference")),
                            Jsonb(_json_safe(source_metadata)),
                            source_execution_id,
                        ),
                    )

                cursor.execute(
                    counter_sql,
                    (
                        records_received,
                        records_loaded,
                        source_execution_id,
                    ),
                )

                if cursor.rowcount != 1:
                    raise SourceIngestionError(
                        "Unable to update source execution counters."
                    )

        return {
            "run_id": run_id,
            "source_execution_id": source_execution_id,
            "source_name": source_name,
            "file_name": file_name,
            "file_format": result["file_format"],
            "records_received": records_received,
            "records_loaded": records_loaded,
            "metadata": metadata,
        }

    except SourceIngestionError:
        raise

    except Exception as exc:
        raise SourceIngestionError(
            f"Raw ingestion failed for {source_name} "
            f"file {file_name}: {exc}"
        ) from exc
