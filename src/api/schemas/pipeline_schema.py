# this schema defines the metadata for one uploaded file

from pydantic import BaseModel, Field
from datetime import datetime

class PipelineFileMetadata(BaseModel):
    source_name: str = Field(min_length=1)
    mapping_id: str = Field(min_length=1)
    mapping_version: str = Field(min_length=1)

# The models below describe the response from the existing V2 orchestrator
# without exposing internal implementation details

class SourceExecutionResponse(BaseModel):
    source_execution_id: int
    source_name: str
    file_path: str
    execution_status: str
    stages: dict
    error: dict | None = None


class PipelineRunResponse(BaseModel):
    run_id: int
    run_status: str
    pipeline: dict
    source_executions: list[SourceExecutionResponse]
    report_path: str | None = None
    report_error: str | None = None

class PipelineRunSummary(BaseModel):
    run_id: int
    source_file: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    run_status: str
    records_received: int
    records_loaded: int
    records_rejected: int
    records_promoted: int
    run_type: str | None = None
    triggered_by: str | None = None


class PipelineRunListResponse(BaseModel):
    items: list[PipelineRunSummary]
    total: int
    limit: int
    offset: int

class PipelineRunDetailResponse(BaseModel):
    pipeline: dict
    source_executions: list[dict]
    mapping_errors: list[dict]
    validation_errors: list[dict]


class PipelineRunDetailEnvelope(BaseModel):
    run_id: int
    report: PipelineRunDetailResponse