# A single pipeline entry point (orchestrator) for executing all the stages

from src.ingestion.load_raw import load_raw_transactions
from src.validation.validate_transactions import validate_transactions
from src.deduplication.deduplicate_transactions import (
    deduplicate_transactions,
)


def run_pipeline():
    print("\nSTARTING HAZINA FINANCIAL TRANSACTIONS PIPELINE")
    print("================================================")

    # Stage 1: Raw ingestion
    run_id = load_raw_transactions()

    # Stage 2: Transaction validation
    validate_transactions(run_id)

    # Stage 3: Deduplication and core promotion
    deduplicate_transactions(run_id)

    print("\nPIPELINE EXECUTION COMPLETED")
    print("================================")
    print(f"Pipeline run ID: {run_id}")
    print("Final status: SUCCESS")


if __name__ == "__main__":
    run_pipeline()
