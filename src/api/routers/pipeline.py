# This endpoint accepts multiple files, with corresponding source and mapping details for each file
# We'll use parallel multipart fields:
# - files
# - source_names
# - mapping_ids
# - mapping_versions
# Each list must contain the same number of entries, in matching order

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, Query

from src.api.schemas.pipeline_schema import (
    PipelineFileMetadata,
    PipelineRunResponse,
)
from src.api.services.pipeline_service import PipelineService
from src.mapping.mapping_registry import MappingRegistryError
from src.run_pipeline_v2 import PipelineV2ExecutionError
from src.api.schemas.pipeline_schema import PipelineRunListResponse, PipelineRunDetailEnvelope


router = APIRouter()


@router.post(
    "/pipeline-runs",
    tags=["Pipeline"],
    response_model=PipelineRunResponse,
)
async def submit_pipeline_files(
    files: list[UploadFile] = File(...),
    source_names: list[str] = Form(...),
    mapping_ids: list[str] = Form(...),
    mapping_versions: list[str] = Form(...),
):
    if not (
        len(files)
        == len(source_names)
        == len(mapping_ids)
        == len(mapping_versions)
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Each uploaded file must have exactly one "
                "source name, mapping ID and mapping version."
            ),
        )

    uploads = []

    try:
        for index, uploaded_file in enumerate(files):
            metadata = PipelineFileMetadata(
                source_name=source_names[index],
                mapping_id=mapping_ids[index],
                mapping_version=mapping_versions[index],
            )

            uploads.append({
                "file": uploaded_file,
                **metadata.model_dump(),
            })

        service = PipelineService()
        return await service.submit_files(uploads)

    except (ValueError, MappingRegistryError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except PipelineV2ExecutionError as exc:
        raise HTTPException(
            status_code=500,
            detail="The pipeline could not complete safely.",
        ) from exc

@router.get(
    "/pipeline-runs",
    response_model=PipelineRunListResponse,
)
def list_pipeline_runs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return PipelineService.list_runs(limit=limit, offset=offset)

@router.get(
    "/pipeline-runs/{run_id}",
    response_model=PipelineRunDetailEnvelope,
)
def get_pipeline_run_details(run_id: int):
    try:
        return PipelineService.get_run_details(run_id)
    except ValueError as exc:
        status_code = 404 if "was not found" in str(exc) else 400
        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc