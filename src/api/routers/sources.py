from fastapi import APIRouter, HTTPException
from src.api.services.source_service import SourceService
from src.api.schemas.source_schema import SourceListResponse

from src.mapping.mapping_registry import (
    MappingRegistry,
    MappingRegistryError,
)


router = APIRouter()


@router.get("/sources", tags=["Sources"], response_model=SourceListResponse)
def list_sources():
    try:
      service = SourceService()
      return service.list_sources()

    except MappingRegistryError:
       raise HTTPException(
          status_code=500,
          detail="Unable to load source configurations."
       )