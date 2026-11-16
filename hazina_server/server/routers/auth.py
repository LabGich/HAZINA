from fastapi import APIRouter, Depends, HTTPException, status

from server.auth.dependencies import get_current_auth_context
from server.auth.service import AuthenticationService
from server.schemas.auth_schema import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    AuthUserResponse,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest):
    try:
        return AuthenticationService.login(
            email=request.email,
            password=request.password,
            organization_slug=request.organization_slug,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: RefreshRequest):
    try:
        return AuthenticationService.refresh(
            refresh_token=request.refresh_token,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )


@router.post("/logout")
def logout(request: LogoutRequest):
    try:
        return AuthenticationService.logout(
            refresh_token=request.refresh_token,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )


@router.get("/me", response_model=AuthUserResponse)
def get_me(
    auth_context: dict = Depends(get_current_auth_context),
):
    try:
        return AuthenticationService.get_current_user(
            user_id=auth_context["user_id"],
            organization_id=auth_context["organization_id"],
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )