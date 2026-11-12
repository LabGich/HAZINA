from src.ingestion.load_raw import load_raw_transactions
from src.validation.validate_transactions import validate_transactions
from src.deduplication.deduplicate_transactions import (
    deduplicate_transactions,
)


def run_pipeline():

    print("\nSTARTING HAZINA FINANCIAL TRANSACTIONS PIPELINE")
    print("================================================")

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


if __name__ == "__main__":
    run_pipeline()