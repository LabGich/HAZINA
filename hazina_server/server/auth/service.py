# Auth orchestration layer

from datetime import datetime, timezone

from server.auth.password import verify_password
from server.auth.token import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
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


    @staticmethod
    def refresh(refresh_token: str) -> dict:
        if not isinstance(refresh_token, str) or not refresh_token:
            raise ValueError("A valid refresh token is required.")

        payload = decode_token(
            refresh_token,
            expected_type="refresh",
        )

        try:
            user_id = int(payload["sub"])
            organization_id = int(payload["organization_id"])
            old_jti = payload["jti"]
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid refresh token.") from exc

        session = AuthService.get_active_refresh_session(old_jti)

        if session is None:
            raise ValueError("Refresh token is invalid, expired, or revoked.")

        if (
            session["user_id"] != user_id
            or session["organization_id"] != organization_id
        ):
            raise ValueError("Refresh token session does not match.")

        membership = AuthService.get_active_user_membership(
            email=session["email"],
            organization_slug=session["organization_slug"],
        )

        if membership is None:
            raise ValueError("User membership is no longer active.")

        new_refresh_token = create_refresh_token(
            user_id=user_id,
            organization_id=organization_id,
        )

        new_payload = decode_token(
            new_refresh_token,
            expected_type="refresh",
        )

        new_expires_at = datetime.fromtimestamp(
            new_payload["exp"],
            tz=timezone.utc,
        )

        # Rotate the database session atomically.
        AuthService.rotate_refresh_session(
            old_token_jti=old_jti,
            new_token_jti=new_payload["jti"],
            new_expires_at=new_expires_at,
        )

        new_access_token = create_access_token(
            user_id=user_id,
            organization_id=organization_id,
            role=membership["role_code"],
        )

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "access_token_expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }


    @staticmethod
    def logout(refresh_token: str) -> dict:
        if not isinstance(refresh_token, str) or not refresh_token:
            raise ValueError("A valid refresh token is required.")

        payload = decode_token(
            refresh_token,
            expected_type="refresh",
        )

        token_jti = payload.get("jti")

        if not token_jti:
            raise ValueError("Invalid refresh token.")

        revoked = AuthService.revoke_refresh_session(token_jti)

        if not revoked:
            raise ValueError(
                "Refresh token is invalid, expired, or already revoked."
            )

        return {"message": "Successfully logged out."}


    @staticmethod
    def list_organization_users(organization_id: int) -> list[dict]:
        return AuthService.list_organization_users(organization_id)

    @staticmethod
    def create_organization_user(
        organization_id: int,
        email: str,
        password: str,
        full_name: str,
        role_code: str,
    ) -> dict:
        from server.auth.password import hash_password

        if not isinstance(password, str) or len(password) < 12:
            raise ValueError("Password must contain at least 12 characters.")

        return AuthService.create_user_with_membership(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            organization_id=organization_id,
            role_code=role_code,
        )

    @staticmethod
    def update_organization_user(
        organization_id: int,
        user_id: int,
        role_code: str | None = None,
        is_active: bool | None = None,
    ) -> dict | None:
        return AuthService.update_organization_membership(
            organization_id=organization_id,
            user_id=user_id,
            role_code=role_code,
            is_active=is_active,
        )


    @staticmethod
    def get_current_user(user_id: int, organization_id: int) -> dict:
        if (
            isinstance(user_id, bool)
            or not isinstance(user_id, int)
            or user_id <= 0
        ):
            raise ValueError("A valid user_id is required.")

        if (
            isinstance(organization_id, bool)
            or not isinstance(organization_id, int)
            or organization_id <= 0
        ):
            raise ValueError("A valid organization_id is required.")

        membership = AuthService.get_active_user_context(
            user_id=user_id,
            organization_id=organization_id,
        )

        if membership is None:
            raise ValueError("User or organization membership is no longer active.")

        memberships = AuthService.get_user_memberships(user_id)

        return {
            "user_id": membership["user_id"],
            "email": membership["email"],
            "full_name": membership["full_name"],
            "organization_id": membership["organization_id"],
            "organization_name": membership["organization_name"],
            "organization_slug": membership["organization_slug"],
            "role_code": membership["role_code"],
            "memberships": memberships,
        }
