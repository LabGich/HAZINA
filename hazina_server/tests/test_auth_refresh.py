
import uuid

import pytest

from server.auth.password import hash_password
from server.auth.service import AuthenticationService
from server.auth.token import decode_token
from server.services.auth_service import AuthService


@pytest.fixture
def refresh_account():
    suffix = uuid.uuid4().hex[:12]

    organization = AuthService.create_organization(
        name="Refresh Test Organization",
        slug=f"refresh-org-{suffix}",
    )

    password = "Test-Refresh-Password-2026!"

    user = AuthService.create_user(
        email=f"refresh-{suffix}@example.test",
        password_hash=hash_password(password),
        full_name="Refresh Test User",
    )

    AuthService.create_membership(
        organization_id=organization["organization_id"],
        user_id=user["user_id"],
        role_code="OPERATOR",
    )

    login = AuthenticationService.login(
        email=user["email"],
        password=password,
        organization_slug=organization["slug"],
    )

    return {
        "organization": organization,
        "user": user,
        "login": login,
    }


def test_refresh_issues_new_tokens(refresh_account):
    old_refresh = refresh_account["login"]["refresh_token"]

    result = AuthenticationService.refresh(old_refresh)

    assert result["access_token"]
    assert result["refresh_token"]
    assert result["token_type"] == "bearer"
    assert result["access_token_expires_in"] > 0

    assert result["access_token"] != refresh_account["login"]["access_token"]
    assert result["refresh_token"] != old_refresh


def test_refresh_rotates_database_session(refresh_account):
    old_refresh = refresh_account["login"]["refresh_token"]
    old_payload = decode_token(old_refresh, expected_type="refresh")

    result = AuthenticationService.refresh(old_refresh)
    new_payload = decode_token(
        result["refresh_token"],
        expected_type="refresh",
    )

    assert AuthService.get_active_refresh_session(old_payload["jti"]) is None

    new_session = AuthService.get_active_refresh_session(new_payload["jti"])

    assert new_session is not None
    assert new_session["user_id"] == refresh_account["user"]["user_id"]
    assert new_session["organization_id"] == refresh_account["organization"]["organization_id"]


def test_refresh_access_token_uses_current_role(refresh_account):
    user = refresh_account["user"]
    organization = refresh_account["organization"]

    AuthService.create_membership(
        organization_id=organization["organization_id"],
        user_id=user["user_id"],
        role_code="ADMIN",
    ) if False else None

    old_refresh = refresh_account["login"]["refresh_token"]

    result = AuthenticationService.refresh(old_refresh)
    access_payload = decode_token(
        result["access_token"],
        expected_type="access",
    )

    assert access_payload["role"] == "OPERATOR"


def test_refresh_rejects_reuse_of_rotated_token(refresh_account):
    old_refresh = refresh_account["login"]["refresh_token"]

    AuthenticationService.refresh(old_refresh)

    with pytest.raises(ValueError, match="invalid, expired, or revoked"):
        AuthenticationService.refresh(old_refresh)


def test_refresh_rejects_invalid_token():
    with pytest.raises(ValueError, match="Invalid or expired token"):
        AuthenticationService.refresh("not-a-valid-jwt")


def test_refresh_rejects_access_token(refresh_account):
    access_token = refresh_account["login"]["access_token"]

    with pytest.raises(ValueError, match="Invalid token type"):
        AuthenticationService.refresh(access_token)


def test_refresh_rejects_empty_token():
    with pytest.raises(ValueError, match="refresh token is required"):
        AuthenticationService.refresh("")


def test_refresh_rejects_inactive_membership(refresh_account):
    user = refresh_account["user"]
    organization = refresh_account["organization"]
    old_refresh = refresh_account["login"]["refresh_token"]

    from hazina_pipeline.database.connection import get_database_connection

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE auth.organization_memberships
                SET is_active = FALSE
                WHERE user_id = %s
                  AND organization_id = %s;
                """,
                (user["user_id"], organization["organization_id"]),
            )

    with pytest.raises(ValueError, match="invalid, expired, or revoked"):
        AuthenticationService.refresh(old_refresh)


def test_refresh_uses_updated_membership_role(refresh_account):
    user = refresh_account["user"]
    organization = refresh_account["organization"]
    old_refresh = refresh_account["login"]["refresh_token"]

    from hazina_pipeline.database.connection import get_database_connection

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE auth.organization_memberships
                SET role_id = (
                    SELECT role_id
                    FROM auth.roles
                    WHERE role_code = 'VIEWER'
                )
                WHERE user_id = %s
                  AND organization_id = %s;
                """,
                (user["user_id"], organization["organization_id"]),
            )

    result = AuthenticationService.refresh(old_refresh)

    access_payload = decode_token(
        result["access_token"],
        expected_type="access",
    )

    assert access_payload["role"] == "VIEWER"
