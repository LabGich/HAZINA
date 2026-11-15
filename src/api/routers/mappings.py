from fastapi import APIRouter, HTTPException, Query

from src.api.services.mapping_service import MappingService
from src.api.schemas.mapping_schema import MappingListResponse
from src.mapping.mapping_registry import MappingRegistryError


router = APIRouter()


@router.get("/mappings", tags=["Mappings"], response_model=MappingListResponse)
def list_mappings(
    source_name: str = Query(..., min_length=1),
):
    try:
       service = MappingService()
       return service.list_mappings(source_name)

    except MappingRegistryError:
        raise HTTPException(
            status_code=500,
            detail="Source not found, diasbled, or unavailable."
        )
    