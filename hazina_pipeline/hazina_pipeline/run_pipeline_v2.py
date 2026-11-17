# # This orchestrator will:
# Create one parent run and its child executions
# Process each file independently
# Start, ingest, map, validate, deduplicate and promote
# Finalize successful or partially successful executions
# Mark fatal failures using fail_source_execution()
# Continue processing sibling files after a failure
# Finalize the parent after all files have reached terminal states
# Return the parent and child execution results
# Perform report generation


from hazina_pipeline.orchestration.create_pipeline_run import create_pipeline_run
from hazina_pipeline.orchestration.start_source_execution import start_source_execution
from hazina_pipeline.ingestion.ingest_source_file import ingest_source_file
from hazina_pipeline.mapping.map_source_execution import map_source_execution
from hazina_pipeline.validation.validate_source_execution import validate_source_execution
from hazina_pipeline.deduplication.deduplicate_source_execution import (
    deduplicate_source_execution,
)
from hazina_pipeline.orchestration.finalize_source_execution import (
    finalize_source_execution,
)
from hazina_pipeline.orchestration.fail_source_execution import fail_source_execution
from hazina_pipeline.orchestration.finalize_pipeline_run import finalize_pipeline_run


class PipelineV2ExecutionError(RuntimeError):
    """Raised when V2 orchestration cannot complete safely."""


def run_pipeline_v2(files, organization_id=None):
    """
    Run the complete V2 file-based financial transaction pipeline.

    Each submitted file receives an independent source execution.
    A fatal error in one execution is recorded without preventing
    processing of its sibling executions.

    The parent pipeline run is finalized after all executions
    reach terminal states.
    """

    if not isinstance(files, (list, tuple)) or not files:
        raise ValueError("files must be a non-empty list or tuple")

    # Create the parent run and all child source executions.
    pipeline = create_pipeline_run(files=files, organization_id=organization_id)

    run_id = pipeline["run_id"]
    source_executions = pipeline["source_executions"]

    execution_results = []

    for index, execution in enumerate(source_executions):

        file_config = files[index]

        source_execution_id = execution["source_execution_id"]
        source_name = execution["source_name"]
        mapping_id = execution["mapping_id"]
        mapping_version = execution["mapping_version"]
        file_path = file_config["file_path"]

        # Start the execution before processing its file.
        # If startup fails, stop rather than leave an execution
        # in an uncertain state.
        start_source_execution(
            run_id=run_id,
            source_execution_id=source_execution_id,
        )

        stage_results = {}

        try:
            # 1. Read the source file and persist raw records.
            stage_results["ingestion"] = ingest_source_file(
                run_id=run_id,
                source_execution_id=source_execution_id,
                source_name=source_name,
                file_path=file_path,
            )

            # 2. Map raw records into canonical staging records.
            stage_results["mapping"] = map_source_execution(
                run_id=run_id,
                source_execution_id=source_execution_id,
                source_name=source_name,
                mapping_id=mapping_id,
                mapping_version=mapping_version,
            )

            # 3. Validate staged transactions.
            stage_results["validation"] = validate_source_execution(
                run_id=run_id,
                source_execution_id=source_execution_id,
            )

            # 4. Deduplicate and promote eligible transactions.
            stage_results["deduplication"] = (
                deduplicate_source_execution(
                    run_id=run_id,
                    source_execution_id=source_execution_id,
                )
            )

            # 5. Finalize the completed source execution.
            stage_results["finalization"] = finalize_source_execution(
                run_id=run_id,
                source_execution_id=source_execution_id,
            )

            execution_results.append({
                "source_execution_id": source_execution_id,
                "source_name": source_name,
                "file_path": str(file_path),
                "execution_status": (
                    stage_results["finalization"]["execution_status"]
                ),
                "stages": stage_results,
                "error": None,
            })

        except Exception as exc:

            # Record a fatal error using a separate transaction.
            # The failed stage's transaction has already rolled back.
            try:
                failure_result = fail_source_execution(
                    run_id=run_id,
                    source_execution_id=source_execution_id,
                    error_code="PIPELINE_STAGE_ERROR",
                    error_message=(
                        f"{type(exc).__name__}: {exc}"
                    ),
                )

            except Exception as failure_exc:
                raise PipelineV2ExecutionError(
                    f"Execution {source_execution_id} failed, "
                    "but its failure could not be recorded. "
                    "The parent run has not been finalized."
                ) from failure_exc

            execution_results.append({
                "source_execution_id": source_execution_id,
                "source_name": source_name,
                "file_path": str(file_path),
                "execution_status": "FAILED",
                "stages": stage_results,
                "error": {
                    "error_code": failure_result["error_code"],
                    "error_message": failure_result["error_message"],
                },
            })

            # Continue processing the remaining source executions.

    # 6. Finalize the parent after every child is terminal.
    try:
        parent_result = finalize_pipeline_run(run_id=run_id)

    except Exception as exc:
        raise PipelineV2ExecutionError(
            f"Source executions were processed, but parent run "
            f"{run_id} could not be finalized: {exc}"
        ) from exc

    # 7. Generate the PDF report after the parent is finalized.
    # Reporting failures must never change the pipeline outcome.
    report_path = None
    report_error = None

    try:
        from hazina_pipeline.monitoring.pipeline_status import (
            save_pipeline_v2_run_report,
        )

        report_path = str(
            save_pipeline_v2_run_report(run_id=run_id, organization_id=organization_id)
        )

    except Exception as exc:
        report_error = f"{type(exc).__name__}: {exc}"

    return {
        "run_id": run_id,
        "run_status": parent_result["run_status"],
        "pipeline": parent_result,
        "source_executions": execution_results,
        "report_path": report_path,
        "report_error": report_error
    }

