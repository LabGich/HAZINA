from xml.sax.saxutils import escape
from reportlab.platypus import Table, TableStyle, KeepTogether
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
from src.monitoring.pdf_security import get_pdf_encryption

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

# =====================+
# ==> ADD V2 REPORTING |
# =====================+

def get_pipeline_v2_report_data(run_id):
    """
    Retrieve a complete V2 pipeline run report, including
    source executions and mapping/validation error summaries.
    """

    if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id <= 0:
        raise ValueError("run_id must be a positive integer.")

    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            # Parent pipeline run
            cursor.execute(
                """
                SELECT
                    run_id,
                    source_file,
                    started_at,
                    completed_at,
                    run_status,
                    records_received,
                    records_loaded,
                    records_rejected,
                    records_skipped,
                    records_updated,
                    records_duplicated,
                    records_unique_eligible,
                    records_promoted,
                    records_already_in_core,
                    run_type,
                    triggered_by,
                    metadata
                FROM ops.pipeline_runs
                WHERE run_id = %s
                """,
                (run_id,),
            )

            row = cursor.fetchone()

            if row is None:
                raise ValueError(f"Pipeline run {run_id} does not exist.")

            columns = [item.name for item in cursor.description]
            pipeline = dict(zip(columns, row))

            # Child source executions
            cursor.execute(
                """
                SELECT
                    e.source_execution_id,
                    e.source_id,
                    s.source_name,
                    e.mapping_id,
                    e.mapping_version,
                    e.execution_status,
                    e.started_at,
                    e.completed_at,
                    e.records_received,
                    e.records_loaded,
                    e.records_mapped,
                    e.records_rejected,
                    e.records_skipped,
                    e.records_updated,
                    e.records_duplicated,
                    e.records_unique_eligible,
                    e.records_promoted,
                    e.records_already_in_core,
                    e.error_code,
                    e.error_message,
                    e.metadata
                FROM ops.source_executions e
                JOIN ops.source_registry s
                    ON s.source_id = e.source_id
                WHERE e.run_id = %s
                ORDER BY e.source_execution_id
                """,
                (run_id,),
            )

            execution_columns = [
                item.name for item in cursor.description
            ]

            executions = [
                dict(zip(execution_columns, item))
                for item in cursor.fetchall()
            ]

            # Mapping error summaries
            cursor.execute(
                """
                SELECT
                    source_execution_id,
                    error_code,
                    error_message,
                    field_name,
                    COUNT(DISTINCT raw_id) AS affected_records
                FROM ops.mapping_errors
                WHERE run_id = %s
                GROUP BY
                    source_execution_id,
                    error_code,
                    error_message,
                    field_name
                ORDER BY source_execution_id, affected_records DESC
                """,
                (run_id,),
            )

            mapping_columns = [
                item.name for item in cursor.description
            ]

            mapping_errors = [
                dict(zip(mapping_columns, item))
                for item in cursor.fetchall()
            ]

            # Validation error summaries
            cursor.execute(
                """
                SELECT
                    source_execution_id,
                    error_code,
                    error_message,
                    field_name,
                    COUNT(DISTINCT staging_id) AS affected_records
                FROM ops.validation_errors
                WHERE run_id = %s
                GROUP BY
                    source_execution_id,
                    error_code,
                    error_message,
                    field_name
                ORDER BY source_execution_id, affected_records DESC
                """,
                (run_id,),
            )

            validation_columns = [
                item.name for item in cursor.description
            ]

            validation_errors = [
                dict(zip(validation_columns, item))
                for item in cursor.fetchall()
            ]

    return {
        "pipeline": pipeline,
        "source_executions": executions,
        "mapping_errors": mapping_errors,
        "validation_errors": validation_errors,
    }


def print_pipeline_v2_run_report(run_id):
    """
    Print a human-readable V2 pipeline run report.
    """

    data = get_pipeline_v2_report_data(run_id)

    pipeline = data["pipeline"]
    executions = data["source_executions"]

    print("\n" + "=" * 75)
    print("HAZINA FINANCIAL TRANSACTIONS PIPELINE - V2 REPORT")
    print("=" * 75)

    print("\nPIPELINE DETAILS")
    print("-" * 75)
    print(f"Run ID:                 {pipeline['run_id']}")
    print(f"Status:                 {pipeline['run_status']}")
    print(f"Run type:               {pipeline['run_type']}")
    print(f"Started at:             {pipeline['started_at']}")
    print(f"Completed at:           {pipeline['completed_at']}")
    print(f"Triggered by:           {pipeline['triggered_by']}")

    print("\nAGGREGATE PROCESSING")
    print("-" * 75)

    counters = [
        ("Records received", "records_received"),
        ("Records loaded", "records_loaded"),
        ("Records rejected", "records_rejected"),
        ("Records skipped", "records_skipped"),
        ("Records updated", "records_updated"),
        ("Records duplicated", "records_duplicated"),
        ("Unique eligible", "records_unique_eligible"),
        ("Newly promoted", "records_promoted"),
        ("Already in core", "records_already_in_core"),
    ]

    for label, key in counters:
        print(f"{label:<28} {pipeline.get(key, 0)}")

    for execution in executions:

        metadata = execution.get("metadata") or {}

        file_name = metadata.get("file_name", "Unknown")
        file_format = metadata.get("file_format", "Unknown")

        print("\n" + "=" * 75)
        print(f"SOURCE EXECUTION: {execution['source_execution_id']}")
        print("=" * 75)

        print(f"Source:                 {execution['source_name']}")
        print(f"File:                   {file_name}")
        print(f"Format:                 {file_format}")
        print(f"Mapping:                {execution['mapping_id']}")
        print(f"Mapping version:        {execution['mapping_version']}")
        print(f"Status:                 {execution['execution_status']}")
        print(f"Started at:             {execution['started_at']}")
        print(f"Completed at:           {execution['completed_at']}")

        print("\nPROCESSING METRICS")

        for label, key in counters:
            print(f"{label:<28} {execution.get(key, 0)}")

        print(f"{'Records mapped':<28} {execution.get('records_mapped', 0)}")

        if execution.get("error_code"):
            print("\nEXECUTION ERROR")
            print(f"Code:    {execution['error_code']}")
            print(f"Message: {execution['error_message']}")

    print("\nMAPPING ERRORS")
    print("-" * 75)

    if data["mapping_errors"]:
        for error in data["mapping_errors"]:
            print(
                f"Execution {error['source_execution_id']} | "
                f"{error['error_code']} | "
                f"{error['field_name'] or '-'} | "
                f"{error['affected_records']} record(s)"
            )
            print(f"  {error['error_message']}")
    else:
        print("No mapping errors recorded.")

    print("\nVALIDATION ERRORS")
    print("-" * 75)

    if data["validation_errors"]:
        for error in data["validation_errors"]:
            print(
                f"Execution {error['source_execution_id']} | "
                f"{error['error_code']} | "
                f"{error['field_name'] or '-'} | "
                f"{error['affected_records']} record(s)"
            )
            print(f"  {error['error_message']}")
    else:
        print("No validation errors recorded.")

    print("\n" + "=" * 75)
    print("END OF V2 PIPELINE REPORT")
    print("=" * 75)


def save_pipeline_v2_run_report(run_id, reports_directory=None):
    """
    Generate a PDF report for a finalized V2 pipeline run.

    Reporting is read-only and does not modify pipeline statuses
    or processing counters.
    """

    if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id <= 0:
        raise ValueError("run_id must be a positive integer.")

    data = get_pipeline_v2_report_data(run_id)

    pipeline = data["pipeline"]

    if pipeline["run_status"] not in (
        "SUCCESS",
        "PARTIAL_SUCCESS",
        "FAILED",
        "CANCELLED",
    ):
        raise ValueError(
            f"Pipeline run {run_id} is not finalized. "
            "Generate its report after finalization."
        )

    project_root = Path(__file__).resolve().parents[2]

    if reports_directory is None:
        reports_directory = project_root / "reports"
    else:
        reports_directory = Path(reports_directory)

    reports_directory.mkdir(parents=True, exist_ok=True)

    report_path = (
        reports_directory / f"pipeline_run_{run_id}_report.pdf"
    )

    document = SimpleDocTemplate(
        str(report_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Hazina V2 Pipeline Run {run_id} Report",
        author="Hazina Financial Transactions Pipeline",
    )

    document.encrypt = get_pdf_encryption(require_open_password=True)

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "V2ReportTitle",
        parent=styles["Title"],
        fontSize=17,
        leading=22,
        textColor=colors.HexColor("#17365D"),
        spaceAfter=12,
    )

    section_style = ParagraphStyle(
        "V2ReportSection",
        parent=styles["Heading2"],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#17365D"),
        spaceBefore=12,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "V2ReportBody",
        parent=styles["BodyText"],
        fontSize=8,
        leading=11,
    )

    small_style = ParagraphStyle(
        "V2ReportSmall",
        parent=body_style,
        fontSize=7,
        leading=9,
    )

    def paragraph(value, style=body_style):
        if value is None:
            value = "-"
        return Paragraph(escape(str(value)), style)

    def make_table(rows, widths):
        table = Table(
            rows,
            colWidths=widths,
            repeatRows=1,
            hAlign="LEFT",
        )

        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("LEADING", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C9D6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                    colors.white,
                    colors.HexColor("#F2F5F8"),
                ]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ])
        )

        return table

    story = []

    story.append(
        Paragraph(
            "HAZINA FINANCIAL TRANSACTIONS PIPELINE",
            title_style,
        )
    )

    story.append(
        Paragraph(
            f"V2 Pipeline Run Report — Run {run_id}",
            styles["Heading2"],
        )
    )

    story.append(Spacer(1, 8))

    # Pipeline details
    story.append(Paragraph("PIPELINE DETAILS", section_style))

    details = [
        ["Field", "Value"],
        ["Run ID", str(pipeline["run_id"])],
        ["Status", str(pipeline["run_status"])],
        ["Run type", str(pipeline.get("run_type") or "-")],
        ["Started at", str(pipeline.get("started_at") or "-")],
        ["Completed at", str(pipeline.get("completed_at") or "-")],
        ["Triggered by", str(pipeline.get("triggered_by") or "-")],
    ]

    story.append(
        make_table(
            [[paragraph(cell, small_style) for cell in row] for row in details],
            [45 * mm, 125 * mm],
        )
    )

    # Aggregate metrics
    story.append(Paragraph("AGGREGATE PROCESSING", section_style))

    metric_keys = [
        ("Records received", "records_received"),
        ("Records loaded", "records_loaded"),
        ("Records rejected", "records_rejected"),
        ("Records skipped", "records_skipped"),
        ("Records updated", "records_updated"),
        ("Records duplicated", "records_duplicated"),
        ("Unique eligible", "records_unique_eligible"),
        ("Newly promoted", "records_promoted"),
        ("Already in core", "records_already_in_core"),
    ]

    metrics = [["Metric", "Count"]]

    for label, key in metric_keys:
        metrics.append([
            paragraph(label, small_style),
            paragraph(pipeline.get(key, 0), small_style),
        ])

    story.append(
        make_table(
            metrics,
            [125 * mm, 45 * mm],
        )
    )

    # Individual source executions
    for execution in data["source_executions"]:

        metadata = execution.get("metadata") or {}

        story.append(Paragraph(
            f"SOURCE EXECUTION {execution['source_execution_id']}",
            section_style,
        ))

        file_format = metadata.get("file_format", "Unknown")
        if isinstance(file_format, str):
            file_format = file_format.lstrip(".").upper()

        execution_details = [
            ["Field", "Value"],
            ["Source", execution.get("source_name")],
            ["Filename", metadata.get("file_name", "Unknown")],
            ["File format", file_format],
            ["File path", metadata.get("file_path", "Unknown")],
            ["Mapping", execution.get("mapping_id")],
            ["Mapping version", execution.get("mapping_version")],
            ["Status", execution.get("execution_status")],
            ["Started at", execution.get("started_at")],
            ["Completed at", execution.get("completed_at")],
        ]

        story.append(
            make_table(
                [
                    [paragraph(cell, small_style) for cell in row]
                    for row in execution_details
                ],
                [45 * mm, 125 * mm],
            )
        )

        execution_metrics = [["Processing metric", "Count"]]

        execution_keys = [
            ("Records received", "records_received"),
            ("Records loaded", "records_loaded"),
            ("Records mapped", "records_mapped"),
            ("Records rejected", "records_rejected"),
            ("Records skipped", "records_skipped"),
            ("Records updated", "records_updated"),
            ("Records duplicated", "records_duplicated"),
            ("Unique eligible", "records_unique_eligible"),
            ("Newly promoted", "records_promoted"),
            ("Already in core", "records_already_in_core"),
        ]

        for label, key in execution_keys:
            execution_metrics.append([
                paragraph(label, small_style),
                paragraph(execution.get(key, 0), small_style),
            ])

        story.append(Spacer(1, 5))

        story.append(
            make_table(
                execution_metrics,
                [125 * mm, 45 * mm],
            )
        )

        if execution.get("error_code"):
            story.append(Paragraph("EXECUTION ERROR", section_style))
            story.append(
                paragraph(
                    f"Code: {execution['error_code']}"
                )
            )
            story.append(
                paragraph(
                    f"Message: {execution.get('error_message')}"
                )
            )

    # Mapping and validation errors
    for heading, error_key in [
        ("MAPPING ERRORS", "mapping_errors"),
        ("VALIDATION ERRORS", "validation_errors"),
    ]:

        story.append(Paragraph(heading, section_style))

        errors = data[error_key]

        if not errors:
            story.append(paragraph("No errors recorded."))
            continue

        rows = [[
            "Execution",
            "Error code",
            "Field",
            "Affected",
            "Message",
        ]]

        for error in errors:
            rows.append([
                paragraph(error.get("source_execution_id"), small_style),
                paragraph(error.get("error_code"), small_style),
                paragraph(error.get("field_name"), small_style),
                paragraph(error.get("affected_records"), small_style),
                paragraph(error.get("error_message"), small_style),
            ])

        story.append(
            make_table(
                rows,
                [17 * mm, 31 * mm, 23 * mm, 18 * mm, 81 * mm],
            )
        )

    story.append(Spacer(1, 12))
    story.append(
        HRFlowable(
            width="100%",
            thickness=0.6,
            color=colors.HexColor("#A6A6A6"),
        )
    )
    story.append(
        paragraph(
            "End of Hazina V2 Pipeline Report",
            small_style,
        )
    )

    document.build(story)

    return report_path
