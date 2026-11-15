# Validate the submission and its mapping details
# Synchronize source configurations
# Verify every requested source is registered and enabled
# Verify each source is a FILE source
# Verify the requested mapping belongs to that source
# Create one parent run with status RUNNING
# Create one PENDING source execution per file
# Store the filename, path, and file format in execution metadata
# Return the run ID and execution IDs


import json
from pathlib import Path

from src.database.connection import get_database_connection
from src.mapping.source_registry import (
    DatabaseSourceRegistry,
    SourceRegistryError,
)


class PipelineRunCreationError(RuntimeError):
    """Raised when a V2 pipeline run cannot be created."""


def create_pipeline_run(files, source_registry=None):
    """
    Create one V2 pipeline run and one PENDING source execution per file.

    Source configurations are synchronized before the creation transaction.
    The parent and all child executions are then created atomically.

    Each file must provide:
        source_name
        file_path
        mapping_id
        mapping_version
    """

    if not isinstance(files, (list, tuple)) or not files:
        raise ValueError("files must be a non-empty list or tuple")

    registry = source_registry or DatabaseSourceRegistry()

    prepared_files = []
    seen = set()

    # Validate submission details and resolve all source/mapping configs
    # before creating any database records.
    for index, file_info in enumerate(files):
        if not isinstance(file_info, dict):
            raise ValueError(
                f"File entry at index {index} must be a dictionary."
            )

        source_name = file_info.get("source_name")
        file_path = file_info.get("file_path")
        mapping_id = file_info.get("mapping_id")
        mapping_version = file_info.get("mapping_version")

        if not isinstance(source_name, str) or not source_name.strip():
            raise ValueError(
                f"File entry at index {index} requires a source_name."
            )

        if not isinstance(file_path, (str, Path)):
            raise ValueError(
                f"File entry at index {index} requires a valid file_path."
            )

        if not isinstance(mapping_id, str) or not mapping_id.strip():
            raise ValueError(
                f"File entry at index {index} requires a mapping_id."
            )

        if (
            not isinstance(mapping_version, str)
            or not mapping_version.strip()
        ):
            raise ValueError(
                f"File entry at index {index} requires a mapping_version."
            )

        source_name = source_name.strip().upper()
        mapping_id = mapping_id.strip()
        mapping_version = mapping_version.strip()

        path = Path(file_path)

        if not path.exists() or not path.is_file():
            raise PipelineRunCreationError(
                f"Source file does not exist or is not a file: {path}"
            )

        file_format = path.suffix.lower()

        if not file_format:
            raise PipelineRunCreationError(
                f"Source file has no file extension: {path}"
            )

        # Validate the registered source and ensure it is file-based.
        try:
            source_config = registry.get_source(source_name)
        except SourceRegistryError as exc:
            raise PipelineRunCreationError(str(exc)) from exc

        if source_config["source_type"] != "FILE":
            raise PipelineRunCreationError(
                f"Source {source_name} is not a FILE source."
            )

        supported_formats = source_config.get("supported_formats") or []

        normalized_file_format = file_format.lstrip(".").lower()

        normalized_supported_formats = [
            str(supported_formats).strip().lower().lstrip(".")
            for supported_format in supported_formats
        ]

        if normalized_file_format not in normalized_supported_formats:

            raise PipelineRunCreationError(
                f"File format {file_format} is not supported "
                f"by source {source_name}."
            )

        # Resolve the explicitly supplied mapping and verify ownership.
        try:
            registry.mapping_registry.resolve_mapping(
                source_name,
                mapping_id=mapping_id,
                mapping_version=mapping_version,
            )
        except Exception as exc:
            raise PipelineRunCreationError(
                f"Invalid mapping for source {source_name}: {exc}"
            ) from exc

        prepared_files.append(
            {
                "source_name": source_name,
                "file_path": str(path),
                "file_name": path.name,
                "file_format": file_format,
                "mapping_id": mapping_id,
                "mapping_version": mapping_version,
                "source_id": None,
            }
        )

    # Synchronize YAML source configurations with the database.
    try:
        synchronized_sources = registry.synchronize()
    except SourceRegistryError as exc:
        raise PipelineRunCreationError(
            f"Source configuration synchronization failed: {exc}"
        ) from exc

    for file_info in prepared_files:
        source_id = synchronized_sources.get(file_info["source_name"])

        if source_id is None:
            raise PipelineRunCreationError(
                f"Source was not synchronized: {file_info['source_name']}"
            )

        file_info["source_id"] = source_id

    # Create the parent and all child executions in one transaction.
    with get_database_connection() as connection:
        with connection.cursor() as cursor:

            source_file = (
                prepared_files[0]["file_name"]
                if len(prepared_files) == 1
                else None
            )

            run_metadata = {
                "pipeline_version": "V2",
                "submission_type": "FILE",
                "submitted_file_count": len(prepared_files),
            }

            cursor.execute(
                """
                INSERT INTO ops.pipeline_runs (
                    source_file,
                    run_status,
                    run_type,
                    triggered_by,
                    metadata
                )
                VALUES (%s, 'RUNNING', 'FILE', 'MANUAL', %s::jsonb)
                RETURNING run_id
                """,
                (
                    source_file,
                    json.dumps(run_metadata),
                ),
            )

            run_id = cursor.fetchone()[0]

            executions = []

            for file_info in prepared_files:
                execution_metadata = {
                    "file_path": file_info["file_path"],
                    "file_name": file_info["file_name"],
                    "file_format": file_info["file_format"],
                }

                cursor.execute(
                    """
                    INSERT INTO ops.source_executions (
                        run_id,
                        source_id,
                        mapping_id,
                        mapping_version,
                        execution_status,
                        metadata
                    )
                    VALUES (%s, %s, %s, %s, 'PENDING', %s::jsonb)
                    RETURNING source_execution_id
                    """,
                    (
                        run_id,
                        file_info["source_id"],
                        file_info["mapping_id"],
                        file_info["mapping_version"],
                        json.dumps(execution_metadata),
                    ),
                )

                source_execution_id = cursor.fetchone()[0]

                executions.append(
                    {
                        "source_execution_id": source_execution_id,
                        "source_name": file_info["source_name"],
                        "file_name": file_info["file_name"],
                        "mapping_id": file_info["mapping_id"],
                        "mapping_version": file_info["mapping_version"],
                        "execution_status": "PENDING",
                    }
                )

    return {
        "run_id": run_id,
        "run_status": "RUNNING",
        "source_executions": executions,
    }
