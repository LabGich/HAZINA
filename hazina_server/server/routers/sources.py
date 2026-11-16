from fastapi import APIRouter, HTTPException, Depends
from server.services.source_service import SourceService
from server.schemas.source_schema import SourceListResponse
from server.auth.dependencies import get_current_auth_context

from hazina_pipeline.mapping.mapping_registry import (
    MappingRegistry,
    MappingRegistryError,
)


router = APIRouter()


@router.get("/sources", tags=["Sources"], response_model=SourceListResponse)
def list_sources(auth_context: dict = Depends(get_current_auth_context)): #or:  _: dict = Depends(get_current_auth_context)
    try:
      service = SourceService()
      return service.list_sources()

    except MappingRegistryError:
       raise HTTPException(
          status_code=500,
          detail="Unable to load source configurations."
       )