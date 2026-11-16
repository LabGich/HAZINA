from fastapi import APIRouter, HTTPException, Query, Depends

from server.services.mapping_service import MappingService
from server.schemas.mapping_schema import MappingListResponse
from hazina_pipeline.mapping.mapping_registry import MappingRegistryError
from server.auth.dependencies import get_current_auth_context


router = APIRouter()


@router.get("/mappings", tags=["Mappings"], response_model=MappingListResponse)
def list_mappings(
    source_name: str = Query(..., min_length=1),
    auth_context: dict = Depends(get_current_auth_context),
):
    try:
       service = MappingService()
       return service.list_mappings(source_name)

    except MappingRegistryError:
        raise HTTPException(
            status_code=500,
            detail="Source not found, diasbled, or unavailable."
        )
    