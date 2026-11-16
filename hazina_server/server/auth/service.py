# Auth orchestration layer

from datetime import datetime, timezone

from server.auth.password import verify_password
from server.auth.token import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from server.services.auth_service import AuthService


class AuthenticationService:

    @staticmethod
    def login(
        email: str,
        password: str,
        organization_slug: str,
    ) -> dict:
        if not isinstance(email, str) or not email.strip():
            raise ValueError("Email is required.")

        if not isinstance(password, str) or not password:
            raise ValueError("Password is required.")

        if (
            not isinstance(organization_slug, str)
            or not organization_slug.strip()
        ):
            raise ValueError("Organization slug is required.")

        membership = AuthService.get_active_user_membership(
            email=email,
            organization_slug=organization_slug,
        )

        if membership is None:
            raise ValueError("Invalid email, password, or organization.")

        if not verify_password(
            password,
            membership["password_hash"],
        ):
            raise ValueError("Invalid email, password, or organization.")

        user_id = membership["user_id"]
        organization_id = membership["organization_id"]
        role_code = membership["role_code"]

        access_token = create_access_token(
            user_id=user_id,
            organization_id=organization_id,
            role=role_code,
        )

        refresh_token = create_refresh_token(
            user_id=user_id,
            organization_id=organization_id,
        )

        refresh_payload = decode_token(
            refresh_token,
            expected_type="refresh",
        )

        refresh_expires_at = datetime.fromtimestamp(
            refresh_payload["exp"],
            tz=timezone.utc,
        )

        AuthService.create_refresh_session(
            user_id=user_id,
            organization_id=organization_id,
            token_jti=refresh_payload["jti"],
            expires_at=refresh_expires_at,
        )

        memberships = AuthService.get_user_memberships(user_id)

        user_response = {
            "user_id": user_id,
            "email": membership["email"],
            "full_name": membership["full_name"],
            "organization_id": organization_id,
            "organization_name": membership["organization_name"],
            "organization_slug": membership["organization_slug"],
            "role_code": role_code,
            "memberships": memberships,
        }

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "access_token_expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": user_response,
        }
