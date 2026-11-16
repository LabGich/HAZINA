from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from server.auth.token import decode_token
from server.services.auth_service import AuthService


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(
            credentials.credentials,
            expected_type="access",
        )
        user_id = int(payload["sub"])
        organization_id = int(payload["organization_id"])

        if user_id <= 0 or organization_id <= 0:
            raise ValueError("Invalid token identity.")

    except (ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    membership = AuthService.get_active_user_context(
        user_id=user_id,
        organization_id=organization_id,
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User or organization membership is no longer active.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return membership

def require_roles(*allowed_roles: str):
    def role_checker(
        auth_context: dict = Depends(get_current_auth_context),
    ) -> dict:
        if auth_context["role_code"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return auth_context

    return role_checker