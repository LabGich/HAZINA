
import json
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from hazina_pipeline.database.connection import get_database_connection


SIGNATURE_FIELDS = (
    "customer_id",
    "transaction_date",
    "transaction_type",
    "amount",
    "currency",
    "direction",
    "payment_method",
    "status",
)


def _transaction_signature(record):
    return tuple(record[field] for field in SIGNATURE_FIELDS)


def _json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, dict):
        return {
            key: _json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]

    return value


def _record_values(record):
    return {
        "transaction_id": record["transaction_id"],
        "customer_id": record["customer_id"],
        "transaction_date": record["transaction_date"],
        "transaction_type": record["transaction_type"],
        "amount": record["amount"],
        "currency": record["currency"],
        "direction": record["direction"],
        "payment_method": record["payment_method"],
        "status": record["status"],
        "description": record["description"],
        "counterparty": record["counterparty"],
        "fee_amount": record["fee_amount"],
        "account_balance": record["account_balance"],
    }


def _insert_core_transaction(cursor, record, organization_id):
    cursor.execute(
        """
        INSERT INTO core.transactions (
            transaction_id,
            customer_id,
            transaction_date,
            transaction_type,
            amount,
            currency,
            payment_method,
            status,
            direction,
            description,
            counterparty,
            fee_amount,
            account_balance,
            organization_id
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s
        )
        """,
        (
            record["transaction_id"],
            record["customer_id"],
            record["transaction_date"],
            record["transaction_type"],
            record["amount"],
            record["currency"],
            record["payment_method"],
            record["status"],
            record["direction"],
            record["description"],
            record["counterparty"],
            record["fee_amount"],
            record["account_balance"],
            organization_id,
        ),
    )


def _insert_source_identity(
    cursor,
    source_id,
    record,
    organization_id,
):
    cursor.execute(
        """
        INSERT INTO ops.source_transaction_identity (
            source_id,
            source_account_id,
            source_transaction_id,
            transaction_id,
            metadata,
            organization_id
        )
        VALUES (%s, %s, %s, %s, %s::jsonb, %s)
        """,
        (
            source_id,
            record["source_account_id"],
            record["source_transaction_id"],
            record["transaction_id"],
            json.dumps(
                _json_safe({
                    "source_name": record["source_name"],
                    "source_execution_id": record["source_execution_id"],
                    "run_id": record["run_id"],
                    "raw_id": record["raw_id"],
                    "mapping_id": record["mapping_id"],
                    "mapping_version": record["mapping_version"],
                })
            ),
            organization_id,
        ),
    )


def _insert_transaction_audit(
    cursor,
    source_id,
    record,
    organization_id,
):
    new_values = _record_values(record)
    changed_fields = list(new_values.keys())

    metadata = {
        "source_name": record["source_name"],
        "file_source_execution": True,
    }

    cursor.execute(
        """
        INSERT INTO ops.transaction_audit (
            transaction_id,
            source_id,
            source_execution_id,
            run_id,
            raw_id,
            action_type,
            previous_values,
            new_values,
            changed_fields,
            mapping_id,
            mapping_version,
            changed_by,
            metadata,
            organization_id
        )
        VALUES (
            %s, %s, %s, %s, %s,
            'INSERT',
            '{}'::jsonb,
            %s::jsonb,
            %s::jsonb,
            %s, %s,
            'V2_PIPELINE',
            %s::jsonb,
            %s
        )
        """,
        (
            record["transaction_id"],
            source_id,
            record["source_execution_id"],
            record["run_id"],
            record["raw_id"],
            json.dumps(_json_safe(new_values)),
            json.dumps(changed_fields),
            record["mapping_id"],
            record["mapping_version"],
            json.dumps(metadata),
            organization_id,
        ),
    )


def _get_existing_source_identity(
    cursor,
    source_id,
    source_account_id,
    source_transaction_id,
    organization_id,
):
    cursor.execute(
        """
        SELECT
            identity.transaction_id,
            core.customer_id,
            core.transaction_date,
            core.transaction_type,
            core.amount,
            core.currency,
            core.direction,
            core.payment_method,
            core.status
        FROM ops.source_transaction_identity identity
        JOIN core.transactions core
          ON core.transaction_id = identity.transaction_id
         AND core.organization_id
             IS NOT DISTINCT FROM identity.organization_id
        WHERE identity.source_id = %s
          AND identity.source_account_id IS NOT DISTINCT FROM %s
          AND identity.source_transaction_id = %s
          AND identity.organization_id IS NOT DISTINCT FROM %s
          AND identity.is_active = TRUE
        FOR UPDATE OF identity
        """,
        (
            source_id,
            source_account_id,
            source_transaction_id,
            organization_id,
        ),
    )

    return cursor.fetchone()


def _get_existing_core_transaction(
    cursor,
    transaction_id,
    organization_id,
):
    cursor.execute(
        """
        SELECT
            customer_id,
            transaction_date,
            transaction_type,
            amount,
            currency,
            direction,
            payment_method,
            status
        FROM core.transactions
        WHERE transaction_id = %s
          AND organization_id IS NOT DISTINCT FROM %s
        FOR UPDATE
        """,
        (transaction_id, organization_id),
    )

    return cursor.fetchone()


def _deduplicate_source_execution(run_id, source_execution_id):
    if not isinstance(run_id, int) or run_id <= 0:
        raise ValueError("run_id must be a positive integer.")

    if (
        not isinstance(source_execution_id, int)
        or source_execution_id <= 0
    ):
        raise ValueError(
            "source_execution_id must be a positive integer."
        )

    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            # Retrieve ownership from the parent run and lock
            # the source execution being processed.
            cursor.execute(
                """
                SELECT
                    se.execution_status,
                    se.source_id,
                    pr.organization_id
                FROM ops.source_executions se
                JOIN ops.pipeline_runs pr
                  ON pr.run_id = se.run_id
                WHERE se.run_id = %s
                  AND se.source_execution_id = %s
                FOR UPDATE OF se
                """,
                (run_id, source_execution_id),
            )

            execution = cursor.fetchone()

            if execution is None:
                raise ValueError(
                    "Source execution does not belong to the supplied run."
                )

            execution_status, source_id, organization_id = execution

            if execution_status != "RUNNING":
                raise ValueError(
                    "Source execution must be RUNNING before deduplication."
                )

            # Select only validated records belonging to this run's
            # organization. IS NOT DISTINCT FROM also supports
            # historical runs whose organization_id is NULL.
            cursor.execute(
                """
                SELECT
                    staging_id,
                    raw_id,
                    transaction_id,
                    customer_id,
                    transaction_date,
                    transaction_type,
                    amount,
                    currency,
                    direction,
                    payment_method,
                    status,
                    description,
                    counterparty,
                    fee_amount,
                    account_balance,
                    source_name,
                    source_account_id,
                    source_transaction_id,
                    mapping_id,
                    mapping_version,
                    run_id,
                    source_execution_id
                FROM staging.transactions
                WHERE run_id = %s
                  AND source_execution_id = %s
                  AND validation_status = 'VALID'
                  AND organization_id IS NOT DISTINCT FROM %s
                ORDER BY raw_id
                FOR UPDATE
                """,
                (run_id, source_execution_id, organization_id),
            )

            rows = cursor.fetchall()

            records = []

            for row in rows:
                records.append({
                    "staging_id": row[0],
                    "raw_id": row[1],
                    "transaction_id": row[2],
                    "customer_id": row[3],
                    "transaction_date": row[4],
                    "transaction_type": row[5],
                    "amount": row[6],
                    "currency": row[7],
                    "direction": row[8],
                    "payment_method": row[9],
                    "status": row[10],
                    "description": row[11],
                    "counterparty": row[12],
                    "fee_amount": row[13],
                    "account_balance": row[14],
                    "source_name": row[15],
                    "source_account_id": row[16] or None,
                    "source_transaction_id": row[17] or None,
                    "mapping_id": row[18],
                    "mapping_version": row[19],
                    "run_id": row[20],
                    "source_execution_id": row[21],
                })

            # Group only records that have a provider transaction ID.
            # Records without one remain independently identifiable.
            identity_groups = defaultdict(list)
            independent_records = []

            for record in records:
                provider_id = record["source_transaction_id"]

                if provider_id is None:
                    independent_records.append([record])
                    continue

                identity_key = (
                    record["source_account_id"],
                    provider_id,
                )

                identity_groups[identity_key].append(record)

            groups = list(identity_groups.values())
            groups.extend(independent_records)

            classifications = {}

            exact_duplicate_count = 0
            conflicting_record_count = 0
            conflicting_id_count = 0
            exact_duplicate_id_count = 0

            records_unique_eligible = 0
            records_promoted = 0
            records_already_in_core = 0

            for group in groups:
                group.sort(key=lambda item: item["raw_id"])

                keeper = group[0]
                signatures = {
                    _transaction_signature(record)
                    for record in group
                }

                # Different versions of the same provider identity
                # are all quarantined.
                if len(signatures) > 1:
                    for record in group:
                        classifications[record["staging_id"]] = (
                            "CONFLICTING_DUPLICATE",
                            None,
                        )

                    conflicting_record_count += len(group)
                    conflicting_id_count += 1
                    continue

                # Identical records: retain the earliest raw record.
                keeper_signature = _transaction_signature(keeper)

                if len(group) > 1:
                    exact_duplicate_id_count += 1
                    exact_duplicate_count += len(group) - 1

                    for duplicate in group[1:]:
                        classifications[duplicate["staging_id"]] = (
                            "EXACT_DUPLICATE",
                            keeper["raw_id"],
                        )

                # Check whether the provider identity already exists
                # within this organization.
                provider_id = keeper["source_transaction_id"]

                if provider_id is not None:
                    existing_identity = _get_existing_source_identity(
                        cursor,
                        source_id,
                        keeper["source_account_id"],
                        provider_id,
                        organization_id,
                    )

                    if existing_identity is not None:
                        existing_signature = existing_identity[1:]

                        if existing_signature != keeper_signature:
                            for record in group:
                                classifications[record["staging_id"]] = (
                                    "CONFLICTING_DUPLICATE",
                                    None,
                                )

                            conflicting_record_count += len(group)
                            conflicting_id_count += 1
                            exact_duplicate_count -= max(
                                0,
                                len(group) - 1,
                            )
                            exact_duplicate_id_count -= int(len(group) > 1)
                            continue

                        classifications[keeper["staging_id"]] = (
                            "UNIQUE",
                            None,
                        )

                        records_unique_eligible += 1
                        records_already_in_core += 1
                        continue

                # Check the Hazina transaction ID within this
                # organization. This supports safe repeat promotion
                # for records without provider-issued transaction IDs.
                existing_core = _get_existing_core_transaction(
                    cursor,
                    keeper["transaction_id"],
                    organization_id,
                )

                if existing_core is not None:
                    if existing_core != keeper_signature:
                        raise ValueError(
                            "Core transaction conflict detected for "
                            f"{keeper['transaction_id']}."
                        )

                    classifications[keeper["staging_id"]] = (
                        "UNIQUE",
                        None,
                    )

                    records_unique_eligible += 1
                    records_already_in_core += 1
                    continue

                # Promote the new transaction.
                _insert_core_transaction(
                    cursor,
                    keeper,
                    organization_id,
                )

                # Register provider identity only when available.
                if provider_id is not None:
                    _insert_source_identity(
                        cursor,
                        source_id,
                        keeper,
                        organization_id,
                    )

                # Every newly promoted transaction receives one audit row.
                _insert_transaction_audit(
                    cursor,
                    source_id,
                    keeper,
                    organization_id,
                )

                classifications[keeper["staging_id"]] = (
                    "UNIQUE",
                    None,
                )

                records_unique_eligible += 1
                records_promoted += 1

            # Save all staging classifications.
            classification_rows = [
                (
                    status,
                    duplicate_of_raw_id,
                    staging_id,
                )
                for staging_id, (status, duplicate_of_raw_id)
                in classifications.items()
            ]

            if classification_rows:
                cursor.executemany(
                    """
                    UPDATE staging.transactions
                    SET deduplication_status = %s,
                        duplicate_of_raw_id = %s
                    WHERE staging_id = %s
                    """,
                    classification_rows,
                )

            records_duplicated = (
                exact_duplicate_count + conflicting_record_count
            )

            # Update per-file execution counters.
            cursor.execute(
                """
                UPDATE ops.source_executions
                SET records_duplicated = %s,
                    records_unique_eligible = %s,
                    records_promoted = %s,
                    records_already_in_core = %s
                WHERE run_id = %s
                  AND source_execution_id = %s
                """,
                (
                    records_duplicated,
                    records_unique_eligible,
                    records_promoted,
                    records_already_in_core,
                    run_id,
                    source_execution_id,
                ),
            )

            return {
                "run_id": run_id,
                "source_execution_id": source_execution_id,
                "records_examined": len(records),
                "records_unique_eligible": records_unique_eligible,
                "exact_duplicate_ids": exact_duplicate_id_count,
                "exact_duplicate_records": exact_duplicate_count,
                "conflicting_ids": conflicting_id_count,
                "conflicting_records": conflicting_record_count,
                "records_duplicated": records_duplicated,
                "records_promoted": records_promoted,
                "records_already_in_core": records_already_in_core,
            }


def deduplicate_source_execution(run_id, source_execution_id):
    return _deduplicate_source_execution(
        run_id,
        source_execution_id,
    )
