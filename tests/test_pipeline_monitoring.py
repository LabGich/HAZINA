import pytest

from src.monitoring.pipeline_status import (
    get_pipeline_run_summary,
)
from src.database.connection import get_database_connection
from src.validation.validate_transactions import validate_transactions
from src.monitoring.pipeline_status import get_rejection_reason_summary
from src.monitoring.pipeline_status import print_pipeline_run_report
from src.monitoring.pipeline_status import save_pipeline_run_report

def test_pipeline_run_summary_returns_correct_details(
    database_test_context,
):

    run_id = database_test_context["run_id"]

    summary = get_pipeline_run_summary(run_id)

    assert summary["run_id"] == run_id
    assert summary["source_file"] == (
        f"{database_test_context['prefix']}.csv"
    )
    assert summary["run_status"] == "RUNNING"
    assert summary["records_received"] == 0
    assert summary["records_staged"] == 0
    assert summary["records_rejected"] == 0
    assert summary["records_duplicated"] == 0

    assert summary["records_unique_eligible"] == 0
    assert summary["records_promoted"] == 0
    assert summary["records_already_in_core"] == 0

    assert summary["unique_records"] == 0
    assert summary["exact_duplicates"] == 0
    assert summary["conflicting_duplicates"] == 0
    assert summary["rejected_records"] == 0


def test_pipeline_run_summary_rejects_unknown_run():

    with pytest.raises(
        ValueError,
        match="does not exist",
    ):
        get_pipeline_run_summary(-1)

def test_rejection_reason_summary_returns_correct_details(
    database_test_context,
):
    run_id = database_test_context["run_id"]

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
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
                    run_id
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                """,
                (
                    "TEST_INVALID_AMOUNT",
                    "CUST_TEST001",
                    "2026-11-12T14:30:00+03:00",
                    "PAYMENT",
                    "-100.00",
                    "KES",
                    "MPESA",
                    "COMPLETED",
                    "integration_test.csv",
                    run_id,
                ),
            )

    validate_transactions(run_id)

    rejection_summary = get_rejection_reason_summary(run_id)

    assert len(rejection_summary) == 1
    assert rejection_summary[0]["error_reason"] == (
        "amount must be greater than zero"
    )
    assert rejection_summary[0]["affected_records"] == 1

def test_pipeline_run_report_prints_correct_details(
    database_test_context,
    capsys,
):
    run_id = database_test_context["run_id"]

    print_pipeline_run_report(run_id)

    captured = capsys.readouterr()
    report = captured.out

    assert "HAZINA FINANCIAL TRANSACTIONS PIPELINE REPORT" in report
    assert f"Run ID:             {run_id}" in report
    assert "RECORD PROCESSING" in report
    assert "DEDUPLICATION" in report
    assert "CORE PROMOTION" in report
    assert "REJECTION REASONS" in report
    assert "No eligible unique records were available." in report
    assert "No validation errors recorded." in report
    assert "END OF PIPELINE REPORT" in report

#report saving test
def test_pipeline_run_report_is_saved_to_file(
    database_test_context,
    tmp_path,
):
    run_id = database_test_context["run_id"]
    reports_directory = tmp_path / "reports"

    report_path = save_pipeline_run_report(
        run_id,
        reports_directory,
    )

    assert reports_directory.exists()
    assert report_path.exists()
    assert report_path.name == (
        f"pipeline_run_{run_id}_report.pdf"
    )

    assert report_path.stat().st_size > 0

    with report_path.open("rb") as pdf_file:
        assert pdf_file.read(5) == b"%PDF-"