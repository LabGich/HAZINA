
import uuid

import pytest

from server.auth.password import hash_password
from server.auth.service import AuthenticationService
from server.auth.token import decode_token
from server.services.auth_service import AuthService


@pytest.fixture
def logout_account():
    suffix = uuid.uuid4().hex[:12]

    organization = AuthService.create_organization(
        name="Logout Test Organization",
        slug=f"logout-org-{suffix}",
    )

    user = AuthService.create_user(
        email=f"logout-{suffix}@example.test",
        password_hash=hash_password("Test-Logout-Password-2026!"),
        full_name="Logout Test User",
    )

    AuthService.create_membership(
        organization_id=organization["organization_id"],
        user_id=user["user_id"],
        role_code="OPERATOR",
    )

    first_login = AuthenticationService.login(
        email=user["email"],
        password="Test-Logout-Password-2026!",
        organization_slug=organization["slug"],
    )

    second_login = AuthenticationService.login(
        email=user["email"],
        password="Test-Logout-Password-2026!",
        organization_slug=organization["slug"],
    )

    return {
        "organization": organization,
        "user": user,
        "first_login": first_login,
        "second_login": second_login,
    }


def test_logout_revokes_refresh_session(logout_account):
    refresh_token = logout_account["first_login"]["refresh_token"]
    payload = decode_token(refresh_token, expected_type="refresh")

    result = AuthenticationService.logout(refresh_token)

    assert result["message"] == "Successfully logged out."
    assert AuthService.get_active_refresh_session(payload["jti"]) is None


def test_logout_does_not_revoke_other_device_session(logout_account):
    first_token = logout_account["first_login"]["refresh_token"]
    second_token = logout_account["second_login"]["refresh_token"]

    first_payload = decode_token(first_token, expected_type="refresh")
    second_payload = decode_token(second_token, expected_type="refresh")

    AuthenticationService.logout(first_token)

    assert AuthService.get_active_refresh_session(first_payload["jti"]) is None
    assert AuthService.get_active_refresh_session(second_payload["jti"]) is not None


def test_logout_rejects_repeated_logout(logout_account):
    refresh_token = logout_account["first_login"]["refresh_token"]

    AuthenticationService.logout(refresh_token)

    with pytest.raises(ValueError, match="already revoked"):
        AuthenticationService.logout(refresh_token)


def test_logout_rejects_invalid_token():
    with pytest.raises(ValueError, match="Invalid or expired token"):
        AuthenticationService.logout("invalid-token")


def test_logout_rejects_access_token(logout_account):
    access_token = logout_account["first_login"]["access_token"]

    with pytest.raises(ValueError, match="Invalid token type"):
        AuthenticationService.logout(access_token)


def test_logout_rejects_empty_token():
    with pytest.raises(ValueError, match="refresh token is required"):
        AuthenticationService.logout("")
