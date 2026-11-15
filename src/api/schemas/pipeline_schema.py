# this schema defines the metadata for one uploaded file

from pydantic import BaseModel, Field

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
