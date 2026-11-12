from reportlab.lib.pdfencrypt import StandardEncryption
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
)
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

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

# def save_pipeline_run_report(run_id):
#     """
#     Generate and save a pipeline run report as a text file.
#     """

#     project_root = Path(__file__).resolve().parents[2]
#     reports_directory = project_root / "reports"

#     # Create reports directory if it does not exist.
#     reports_directory.mkdir(parents=True, exist_ok=True)

#     # Capture the existing printed report.
#     report_output = StringIO()

#     with redirect_stdout(report_output):
#         print_pipeline_run_report(run_id)

#     report_content = report_output.getvalue()

#     # Define the report filename.
#     report_path = (
#         reports_directory / f"pipeline_run_{run_id}_report.txt"
#     )

#     # Save the report.
#     report_path.write_text(
#         report_content,
#         encoding="utf-8",
#     )

#     print(f"Pipeline report saved to: {report_path}")

#     return report_path


def save_pipeline_run_report(run_id, reports_directory=None):
    """
    Generate and save a pipeline run report as a PDF file.
    """

    project_root = Path(__file__).resolve().parents[2]

    if reports_directory is None:
        reports_directory = project_root / "reports"
    else:
        reports_directory = Path(reports_directory)

    reports_directory.mkdir(parents=True, exist_ok=True)

    # Capture the existing report.
    report_output = StringIO()

    with redirect_stdout(report_output):
        print_pipeline_run_report(run_id)

    report_content = report_output.getvalue()

    # Create PDF destination.
    report_path = (
        reports_directory / f"pipeline_run_{run_id}_report.pdf"
    )

    document = SimpleDocTemplate(
        str(report_path),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=f"Hazina Pipeline Run {run_id} Report",
        author="Hazina Financial Transactions Pipeline",
        encrypt=StandardEncryption(
            userPassword="",
            ownerPassword="hazina_report_owner  ",
            canPrint=1,
            canModify=0,
            canCopy=0,
            canAnnotate=0,
            strength=128,
        ),
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#17365D"),
        spaceAfter=12,
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=8,
        leading=11,
        spaceAfter=2,
    )

    story = []

    for line in report_content.splitlines():

        stripped_line = line.strip()

        if not stripped_line:
            story.append(Spacer(1, 5))
            continue

        if "HAZINA FINANCIAL TRANSACTIONS PIPELINE REPORT" in stripped_line:
            story.append(Paragraph(stripped_line, title_style))

        elif set(stripped_line) == {"-"} or set(stripped_line) == {"="}:
            story.append(
                HRFlowable(
                    width="100%",
                    thickness=0.6,
                    color=colors.HexColor("#A6A6A6"),
                    spaceBefore=3,
                    spaceAfter=5,
                )
            )

        else:
            story.append(Paragraph(stripped_line, body_style))

    document.build(story)

    print(f"Pipeline PDF report saved to: {report_path}")

    return report_path
