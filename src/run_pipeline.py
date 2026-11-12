
from src.ingestion.load_raw import load_raw_transactions
from src.validation.validate_transactions import validate_transactions
from src.deduplication.deduplicate_transactions import (
    deduplicate_transactions,
)
from src.monitoring.pipeline_status import save_pipeline_run_report


def run_pipeline():

    print("\nSTARTING HAZINA FINANCIAL TRANSACTIONS PIPELINE")
    print("================================================")

    run_id = None

    try:
        # Stage 1: Raw ingestion
        try:
            run_id = load_raw_transactions()
        except Exception as error:
            print("\nPIPELINE FAILED")
            print("Failure stage: RAW INGESTION")
            print(f"Reason: {error}")
            raise

        # Stage 2: Transaction validation
        try:
            validate_transactions(run_id)
        except Exception as error:
            print("\nPIPELINE FAILED")
            print("Failure stage: TRANSACTION VALIDATION")
            print(f"Pipeline run ID: {run_id}")
            print(f"Reason: {error}")
            raise

        # Stage 3: Deduplication and core promotion
        try:
            deduplicate_transactions(run_id)
        except Exception as error:
            print("\nPIPELINE FAILED")
            print("Failure stage: DEDUPLICATION AND CORE PROMOTION")
            print(f"Pipeline run ID: {run_id}")
            print(f"Reason: {error}")
            raise

        print("\nPIPELINE EXECUTION COMPLETED")
        print("================================")
        print(f"Pipeline run ID: {run_id}")
        print("Final status: SUCCESS")

    finally:
        # Save a report whenever a pipeline run was created.
        if run_id is not None:
            try:
                save_pipeline_run_report(run_id)
            except Exception as report_error:
                print("\nWARNING: PIPELINE REPORT COULD NOT BE SAVED")
                print(f"Reason: {report_error}")


if __name__ == "__main__":
    run_pipeline()
