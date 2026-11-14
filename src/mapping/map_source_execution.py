# Retrieve raw records for one source execution
# Map each record using the caller-supplied mapping
# Generate missing Hazina transaction IDs
# Preserve provider transaction IDs
# Record failures in ops.mapping_errors
# Stage successful canonical transactions
# Update records_mapped and records_rejected
# Leave validation, deduplication, promotion, and execution status to their own stages


from typing import Any
from uuid import uuid4

from psycopg.types.json import Jsonb

from src.database.connection import get_database_connection
from src.mapping.mapping_engine import MappingEngine


class SourceMappingError(RuntimeError):
    """Raised when a source execution cannot be mapped or staged."""


def _record_mapping_error(
    cursor,
    run_id: int,
    source_execution_id: int,
    raw_id: int,
    mapping_id: str,
    mapping_version: str,
    error_code: str,
    error_message: str,
    field_name: str | None = None,
) -> None:
    cursor.execute(
        """
        INSERT INTO ops.mapping_errors (
            run_id,
            source_execution_id,
            raw_id,
            mapping_id,
            mapping_version,
            error_code,
            error_message,
            field_name
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            run_id,
            source_execution_id,
            raw_id,
            mapping_id,
            mapping_version,
            error_code,
            error_message,
            field_name,
        ),
    )


def _validate_staging_fields(
    transaction: dict[str, Any],
) -> str | None:
    """Check fields required by the staging database schema."""

    required_fields = (
        "transaction_date",
        "transaction_type",
        "amount",
        "currency",
        "payment_method",
        "status",
    )

    for field_name in required_fields:
        value = transaction.get(field_name)

        if value is None or (
            isinstance(value, str) and not value.strip()
        ):
            return (
                f"Required canonical field is missing: {field_name}"
            )

    if transaction["amount"] <= 0:
        return "Canonical transaction amount must be greater than zero."

    return None


def map_source_execution(
    run_id: int,
    source_execution_id: int,
    source_name: str,
    mapping_id: str,
    mapping_version: str,
    mapping_engine: MappingEngine | None = None,
) -> dict[str, Any]:
    """
    Map and stage all unprocessed raw records for one source execution.

    Mapping errors are recorded individually. Successful records are
    inserted into staging. All database changes for this execution
    are committed together.
    """

    if not isinstance(run_id, int) or run_id <= 0:
        raise SourceMappingError("run_id must be a positive integer.")

    if not isinstance(source_execution_id, int) or source_execution_id <= 0:
        raise SourceMappingError(
            "source_execution_id must be a positive integer."
        )

    if not isinstance(source_name, str) or not source_name.strip():
        raise SourceMappingError("source_name must be provided.")

    if not isinstance(mapping_id, str) or not mapping_id.strip():
        raise SourceMappingError("mapping_id must be provided.")

    if not isinstance(mapping_version, str) or not mapping_version.strip():
        raise SourceMappingError("mapping_version must be provided.")

    source_name = source_name.strip().upper()
    mapping_id = mapping_id.strip()
    mapping_version = mapping_version.strip()

    engine = mapping_engine or MappingEngine()

    records_mapped = 0
    records_rejected = 0

    staging_sql = """
        INSERT INTO staging.transactions (
            transaction_id,
            customer_id,
            transaction_date,
            transaction_type,
            amount,
            currency,
            payment_method,
            status,
            run_id,
            raw_id,
            source_name,
            source_transaction_id,
            source_account_id,
            direction,
            description,
            counterparty,
            fee_amount,
            account_balance,
            mapping_id,
            mapping_version,
            source_metadata,
            source_execution_id
        )
        VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s
        )
    """

    try:
        with get_database_connection() as connection:
            with connection.cursor() as cursor:

                # Verify and lock the source execution.
                cursor.execute(
                    """
                    SELECT
                        sr.source_name,
                        se.execution_status,
                        se.mapping_id,
                        se.mapping_version
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
                    raise SourceMappingError(
                        "Source execution does not belong to the supplied run."
                    )

                (
                    registered_source,
                    execution_status,
                    registered_mapping_id,
                    registered_mapping_version,
                ) = execution

                if registered_source.upper() != source_name:
                    raise SourceMappingError(
                        "Source name does not match the source execution."
                    )

                if execution_status != "RUNNING":
                    raise SourceMappingError(
                        "Source execution must be RUNNING before mapping."
                    )

                if (
                    registered_mapping_id is not None
                    and registered_mapping_id != mapping_id
                ):
                    raise SourceMappingError(
                        "Mapping ID does not match the source execution."
                    )

                if (
                    registered_mapping_version is not None
                    and registered_mapping_version != mapping_version
                ):
                    raise SourceMappingError(
                        "Mapping version does not match the source execution."
                    )

                # Retrieve only records not already staged or rejected
                # by a previous mapping attempt.
                cursor.execute(
                    """
                    SELECT
                        r.raw_id,
                        r.raw_payload,
                        r.source_metadata
                    FROM raw.transactions r
                    WHERE r.run_id = %s
                      AND r.source_execution_id = %s
                      AND NOT EXISTS (
                          SELECT 1
                          FROM staging.transactions s
                          WHERE s.raw_id = r.raw_id
                      )
                      AND NOT EXISTS (
                          SELECT 1
                          FROM ops.mapping_errors me
                          WHERE me.raw_id = r.raw_id
                            AND me.source_execution_id = %s
                      )
                    ORDER BY r.raw_id
                    FOR UPDATE OF r
                    """,
                    (
                        run_id,
                        source_execution_id,
                        source_execution_id,
                    ),
                )

                raw_records = cursor.fetchall()

                for raw_id, raw_payload, source_metadata in raw_records:

                    if not isinstance(source_metadata, dict):
                        source_metadata = {}

                    result = engine.map_transaction(
                        source_name=source_name,
                        raw_record=raw_payload,
                        mapping_id=mapping_id,
                        mapping_version=mapping_version,
                        context={
                            "raw_id": raw_id,
                            "run_id": run_id,
                            "source_metadata": source_metadata,
                        },
                    )

                    if not result.success:
                        errors = result.errors or []

                        if not errors:
                            _record_mapping_error(
                                cursor=cursor,
                                run_id=run_id,
                                source_execution_id=source_execution_id,
                                raw_id=raw_id,
                                mapping_id=mapping_id,
                                mapping_version=mapping_version,
                                error_code="MAPPING_EXECUTION_ERROR",
                                error_message="Mapping failed without an error detail.",
                            )

                        for error in errors:
                            _record_mapping_error(
                                cursor=cursor,
                                run_id=run_id,
                                source_execution_id=source_execution_id,
                                raw_id=raw_id,
                                mapping_id=result.mapping_id or mapping_id,
                                mapping_version=(
                                    result.mapping_version or mapping_version
                                ),
                                error_code=error.error_code,
                                error_message=error.error_message,
                                field_name=error.field_name,
                            )

                        records_rejected += 1
                        continue

                    transaction = result.canonical_transaction

                    if not isinstance(transaction, dict):
                        _record_mapping_error(
                            cursor=cursor,
                            run_id=run_id,
                            source_execution_id=source_execution_id,
                            raw_id=raw_id,
                            mapping_id=mapping_id,
                            mapping_version=mapping_version,
                            error_code="INVALID_CANONICAL_TRANSACTION",
                            error_message=(
                                "Mapping succeeded without a canonical transaction."
                            ),
                        )
                        records_rejected += 1
                        continue

                    # Generate a Hazina ID only when the mapping
                    # did not supply one.
                    transaction_id = transaction.get("transaction_id")

                    if (
                        transaction_id is None
                        or (
                            isinstance(transaction_id, str)
                            and not transaction_id.strip()
                        )
                    ):
                        transaction_id = str(uuid4())

                    transaction["transaction_id"] = transaction_id

                    # Do not invent missing canonical values.
                    staging_error = _validate_staging_fields(transaction)

                    if staging_error:
                        _record_mapping_error(
                            cursor=cursor,
                            run_id=run_id,
                            source_execution_id=source_execution_id,
                            raw_id=raw_id,
                            mapping_id=result.mapping_id or mapping_id,
                            mapping_version=(
                                result.mapping_version or mapping_version
                            ),
                            error_code="STAGING_REQUIRED_FIELD_MISSING",
                            error_message=staging_error,
                        )
                        records_rejected += 1
                        continue

                    direction = transaction.get("direction") or "UNKNOWN"

                    if direction not in {"DEBIT", "CREDIT", "UNKNOWN"}:
                        _record_mapping_error(
                            cursor=cursor,
                            run_id=run_id,
                            source_execution_id=source_execution_id,
                            raw_id=raw_id,
                            mapping_id=result.mapping_id or mapping_id,
                            mapping_version=(
                                result.mapping_version or mapping_version
                            ),
                            error_code="INVALID_CANONICAL_DIRECTION",
                            error_message=(
                                f"Unsupported transaction direction: {direction}"
                            ),
                            field_name="direction",
                        )
                        records_rejected += 1
                        continue

                    transaction_metadata = transaction.get(
                        "source_metadata"
                    )

                    if not isinstance(transaction_metadata, dict):
                        transaction_metadata = source_metadata

                    cursor.execute(
                        staging_sql,
                        (
                            transaction_id,
                            transaction.get("customer_id"),
                            transaction["transaction_date"],
                            transaction["transaction_type"],
                            transaction["amount"],
                            transaction["currency"],
                            transaction["payment_method"],
                            transaction["status"],
                            run_id,
                            raw_id,
                            source_name,
                            transaction.get("source_transaction_id"),
                            transaction.get("source_account_id"),
                            direction,
                            transaction.get("description"),
                            transaction.get("counterparty"),
                            transaction.get("fee_amount"),
                            transaction.get("account_balance"),
                            result.mapping_id or mapping_id,
                            result.mapping_version or mapping_version,
                            Jsonb(transaction_metadata),
                            source_execution_id,
                        ),
                    )

                    records_mapped += 1

                # Persist mapping counters and mapping provenance.
                cursor.execute(
                    """
                    UPDATE ops.source_executions
                    SET records_mapped = records_mapped + %s,
                        records_rejected = records_rejected + %s,
                        mapping_id = COALESCE(mapping_id, %s),
                        mapping_version = COALESCE(mapping_version, %s)
                    WHERE source_execution_id = %s
                      AND run_id = %s
                    """,
                    (
                        records_mapped,
                        records_rejected,
                        mapping_id,
                        mapping_version,
                        source_execution_id,
                        run_id,
                    ),
                )

                if cursor.rowcount != 1:
                    raise SourceMappingError(
                        "Unable to update source execution mapping counters."
                    )

        return {
            "run_id": run_id,
            "source_execution_id": source_execution_id,
            "source_name": source_name,
            "mapping_id": mapping_id,
            "mapping_version": mapping_version,
            "records_examined": len(raw_records),
            "records_mapped": records_mapped,
            "records_rejected": records_rejected,
        }

    except SourceMappingError:
        raise

    except Exception as exc:
        raise SourceMappingError(
            f"Mapping and staging failed for {source_name} "
            f"execution {source_execution_id}: {exc}"
        ) from exc
