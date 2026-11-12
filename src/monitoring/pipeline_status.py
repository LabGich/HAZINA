# Failure handling for pipeline status monitoring
# when a Psycopg connection transaction fails, its changes are rolled back
# therefore, we must record FAILED using a separate database connection
# -- after the failed transaction has rolled back

from src.database.connection import get_database_connection


def mark_pipeline_run_failed(run_id):
    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE ops.pipeline_runs
                SET run_status = 'FAILED',
                    completed_at = CURRENT_TIMESTAMP
                WHERE run_id = %s
                    AND run_status = 'RUNNING'
                """,
                (run_id,),
            )

            return cursor.rowcount == 1

# monitoring retrieval func
#return as a py dict
def get_pipeline_run_summary(run_id):

    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT *
                FROM ops.pipeline_monitoring
                WHERE run_id = %s
                """,
                (run_id,),
            )

            result = cursor.fetchone()

            if result is None:
                raise ValueError(
                    f"Pipeline run {run_id} does not exist."
                )

            columns = [
                description.name
                for description in cursor.description
            ]

            return dict(zip(columns, result))

def get_rejection_reason_summary(run_id):

    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    error_reason,
                    COUNT(DISTINCT raw_id) AS affected_records
                FROM ops.pipeline_errors
                WHERE run_id = %s
                GROUP BY error_reason
                ORDER BY affected_records DESC, error_reason;
                """,
                (run_id,),
            )

            results = cursor.fetchall()

            columns = [
                description.name
                for description in cursor.description
            ]

            return [
                dict(zip(columns, row))
                for row in results
            ]

#pipeline report

def print_pipeline_run_report(run_id):

    summary = get_pipeline_run_summary(run_id)
    rejection_summary = get_rejection_reason_summary(run_id)

    print("\n" + "=" * 65)
    print("HAZINA FINANCIAL TRANSACTIONS PIPELINE REPORT")
    print("=" * 65)

    print("\nRUN DETAILS")
    print("-" * 65)
    print(f"Run ID:             {summary['run_id']}")
    print(f"Source file:        {summary['source_file']}")
    print(f"Status:             {summary['run_status']}")
    print(f"Started at:         {summary['started_at']}")
    print(f"Completed at:       {summary['completed_at']}")

    print("\nRECORD PROCESSING")
    print("-" * 65)
    print(f"Records received:   {summary['records_received']}")
    print(f"Records staged:     {summary['records_staged']}")
    print(f"Records rejected:   {summary['records_rejected']}")

    print("\nDEDUPLICATION")
    print("-" * 65)
    print(f"Unique records:     {summary['unique_records']}")
    print(f"Exact duplicates:   {summary['exact_duplicates']}")
    print(f"Conflicting records:{summary['conflicting_duplicates']}")

    print("\nCORE PROMOTION")
    print("-" * 65)
    print(
        f"Eligible records:   "
        f"{summary['records_unique_eligible']}"
    )
    print(f"Newly promoted:     {summary['records_promoted']}")
    print(
        f"Already in core:    "
        f"{summary['records_already_in_core']}"
    )

    if summary["records_promoted"] > 0:
        print("\nPromotion result: New transactions successfully promoted.")

    elif summary["records_unique_eligible"] == 0:
        print("\nPromotion explanation: No eligible unique records were available.")

    elif (
        summary["records_already_in_core"]
        == summary["records_unique_eligible"]
    ):
        print("\nPromotion explanation: All eligible unique transactions already exist in core.")

    else:
        print("\nPromotion explanation: No new records were promoted. Further investigation may be required.")

    print("\nREJECTION REASONS")
    print("-" * 65)

    if rejection_summary:
        for item in rejection_summary:
            print(
                f"{item['error_reason']}: "
                f"{item['affected_records']} affected record(s)"
            )
    else:
        print("No validation errors recorded.")

    print("\n" + "=" * 65)
    print("END OF PIPELINE REPORT")
    print("=" * 65)
