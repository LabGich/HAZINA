
from pydantic import BaseModel, Field


class DashboardSummaryResponse(BaseModel):
    total_runs: int = Field(ge=0)
    successful_runs: int = Field(ge=0)
    partially_successful_runs: int = Field(ge=0)
    failed_runs: int = Field(ge=0)
    cancelled_runs: int = Field(ge=0)
    pending_executions: int = Field(ge=0)

    records_received: int = Field(ge=0)
    records_processed: int = Field(ge=0)
    records_rejected: int = Field(ge=0)
    records_promoted: int = Field(ge=0)
