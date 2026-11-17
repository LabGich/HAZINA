
from fastapi import APIRouter, Depends, HTTPException, status

from server.auth.dependencies import require_roles
from server.auth.service import AuthenticationService
from server.schemas.auth_schema import (
    AdminCreateUserRequest,
    AdminUpdateMembershipRequest,
    AdminUserResponse,
)


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "/users",
    response_model=list[AdminUserResponse],
)
def list_users(
    auth_context: dict = Depends(require_roles("ADMIN")),
):
    organization_id = auth_context["organization_id"]

    return AuthenticationService.list_organization_users(
        organization_id=organization_id,
    )


@router.post(
    "/users",
    response_model=AdminUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    request: AdminCreateUserRequest,
    auth_context: dict = Depends(require_roles("ADMIN")),
):
    organization_id = auth_context["organization_id"]

    try:
        return AuthenticationService.create_organization_user(
            organization_id=organization_id,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            role_code=request.role_code,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserResponse,
)
def update_user(
    user_id: int,
    request: AdminUpdateMembershipRequest,
    auth_context: dict = Depends(require_roles("ADMIN")),
):
    organization_id = auth_context["organization_id"]
    current_user_id = auth_context["user_id"]

    if request.role_code is None and request.is_active is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one membership field must be provided.",
        )

    if user_id == current_user_id:
        if request.role_code is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot change your own role.",
            )

        if request.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot deactivate your own membership.",
            )

    try:
        result = AuthenticationService.update_organization_user(
            organization_id=organization_id,
            user_id=user_id,
            role_code=request.role_code,
            is_active=request.is_active,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User membership not found in this organization.",
        )

    return result
