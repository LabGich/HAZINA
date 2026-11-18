
from fastapi import APIRouter, Depends, HTTPException

from server.auth.dependencies import require_roles
from server.schemas.dashboard_schema import DashboardSummaryResponse
from server.services.pipeline_service import PipelineService


router = APIRouter()


@router.get(
    "/dashboard/summary",
    tags=["Dashboard"],
    response_model=DashboardSummaryResponse,
)
def get_dashboard_summary(
    auth_context: dict = Depends(
        require_roles("ADMIN", "OPERATOR", "VIEWER")
    ),
):
    try:
        return PipelineService.get_dashboard_summary(
            organization_id=auth_context["organization_id"],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
