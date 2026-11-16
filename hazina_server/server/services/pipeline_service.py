# The first servic version implements:
# Server-generated filenames to prevent filename collisions
# File extension validation against the selected source
# File size limit of 10 MB per file
# Cleanup of uploaded files if the pipeline fails before returning
# Invocation of run_pipeline_v2() exactly once per submission

import uuid
from pathlib import Path

from fastapi import UploadFile

from hazina_pipeline.mapping.mapping_registry import MappingRegistry
from hazina_pipeline.run_pipeline_v2 import run_pipeline_v2
from hazina_pipeline.monitoring.pipeline_status import get_pipeline_v2_runs, get_pipeline_v2_report_data


PROJECT_ROOT = Path(__file__).resolve().parents[3]
UPLOAD_DIRECTORY = PROJECT_ROOT / "data" / "uploads"

MAX_FILE_SIZE = 10 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


class PipelineServiceError(RuntimeError):
    """Raised when a pipeline upload or execution fails."""


class PipelineService:
    """Application service for uploaded V2 pipeline submissions."""

    def __init__(self, mapping_registry=None):
        self.mapping_registry = mapping_registry or MappingRegistry()

    async def submit_files(self, uploads):
        if not uploads:
            raise ValueError("At least one file is required.")

        UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)

        saved_paths = []
        file_configs = []

        pipeline_started = False

        try:
            for item in uploads:
                upload = item["file"]
                source_name = item["source_name"].strip().upper()
                mapping_id = item["mapping_id"].strip()
                mapping_version = item["mapping_version"].strip()

                source = self.mapping_registry.get_source(source_name)

                if source.get("source_type") != "FILE":
                    raise ValueError(
                        f"Source {source_name} is not a FILE source."
                    )

                original_name = Path(upload.filename or "").name

                if not original_name:
                    raise ValueError("Uploaded file has no filename.")

                extension = Path(original_name).suffix.lower().lstrip(".")

                supported_formats = [
                    str(value).strip().lower().lstrip(".")
                    for value in source.get("supported_formats", [])
                ]

                if extension not in supported_formats:
                    raise ValueError(
                        f"File format .{extension} is not supported "
                        f"by source {source_name}."
                    )

                self.mapping_registry.resolve_mapping(
                    source_name=source_name,
                    mapping_id=mapping_id,
                    mapping_version=mapping_version,
                )

                stored_name = f"{uuid.uuid4().hex}{Path(original_name).suffix.lower()}"
                destination = UPLOAD_DIRECTORY / stored_name

                saved_paths.append(destination)

                file_size = 0

                with destination.open("wb") as output:
                    while True:
                        chunk = await upload.read(CHUNK_SIZE)

                        if not chunk:
                            break

                        file_size += len(chunk)

                        if file_size > MAX_FILE_SIZE:
                            raise ValueError(
                                f"File {original_name} exceeds the "
                                "10 MB upload limit."
                            )

                        output.write(chunk)

                file_configs.append({
                    "source_name": source_name,
                    "file_path": str(destination),
                    "mapping_id": mapping_id,
                    "mapping_version": mapping_version,
                })

            pipeline_started = True
            result = run_pipeline_v2(file_configs)

            return result

        except Exception:
            if not pipeline_started:
                for path in saved_paths:
                    path.unlink(missing_ok=True)

            raise

        finally:
            for item in uploads:
                await item["file"].close()

    @staticmethod
    def list_runs(limit=20, offset=0):
        """Return a paginated list of V2 pipeline runs."""
        return get_pipeline_v2_runs(limit=limit, offset=offset)

    @staticmethod
    def get_run_details(run_id):
        """Return detailed monitoring data for a V2 pipeline run."""
        if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id <= 0:
            raise ValueError("run_id must be a positive integer.")

        report = get_pipeline_v2_report_data(run_id)

        if report["pipeline"] is None:
            raise ValueError(f"Pipeline run {run_id} was not found.")

        return {
            "run_id": run_id,
            "report": report,
        }