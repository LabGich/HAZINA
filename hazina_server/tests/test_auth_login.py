
import uuid

import pytest

from server.auth.password import hash_password
from server.auth.service import AuthenticationService
from server.auth.token import decode_token
from server.services.auth_service import AuthService


@pytest.fixture
def login_account():
    suffix = uuid.uuid4().hex[:12]

    organization = AuthService.create_organization(
        name="Authentication Login Test",
        slug=f"auth-login-{suffix}",
    )

    password = "Test-Login-Password-2026!"

    user = AuthService.create_user(
        email=f"login-{suffix}@example.test",
        password_hash=hash_password(password),
        full_name="Authentication Login User",
    )

    AuthService.create_membership(
        organization_id=organization["organization_id"],
        user_id=user["user_id"],
        role_code="OPERATOR",
    )

    return {
        "organization": organization,
        "user": user,
        "password": password,
    }


def test_login_success(login_account):
    organization = login_account["organization"]
    user = login_account["user"]

    result = AuthenticationService.login(
        email=user["email"],
        password=login_account["password"],
        organization_slug=organization["slug"],
    )

    assert result["token_type"] == "bearer"
    assert result["access_token"]
    assert result["refresh_token"]
    assert result["access_token_expires_in"] > 0

    assert result["user"]["user_id"] == user["user_id"]
    assert result["user"]["email"] == user["email"]
    assert result["user"]["organization_id"] == organization["organization_id"]
    assert result["user"]["role_code"] == "OPERATOR"

    assert len(result["user"]["memberships"]) == 1


def test_login_creates_active_refresh_session(login_account):
    organization = login_account["organization"]
    user = login_account["user"]

    result = AuthenticationService.login(
        email=user["email"],
        password=login_account["password"],
        organization_slug=organization["slug"],
    )

    refresh_payload = decode_token(
        result["refresh_token"],
        expected_type="refresh",
    )

    session = AuthService.get_active_refresh_session(
        refresh_payload["jti"]
    )

    assert session is not None
    assert session["user_id"] == user["user_id"]
    assert session["organization_id"] == organization["organization_id"]


def test_login_access_token_contains_selected_role(login_account):
    organization = login_account["organization"]
    user = login_account["user"]

    result = AuthenticationService.login(
        email=user["email"],
        password=login_account["password"],
        organization_slug=organization["slug"],
    )

    payload = decode_token(
        result["access_token"],
        expected_type="access",
    )

    assert payload["sub"] == str(user["user_id"])
    assert payload["organization_id"] == organization["organization_id"]
    assert payload["role"] == "OPERATOR"


def test_login_rejects_wrong_password(login_account):
    with pytest.raises(ValueError, match="Invalid email, password, or organization"):
        AuthenticationService.login(
            email=login_account["user"]["email"],
            password="Wrong-Password",
            organization_slug=login_account["organization"]["slug"],
        )


def test_login_rejects_unknown_email(login_account):
    with pytest.raises(ValueError, match="Invalid email, password, or organization"):
        AuthenticationService.login(
            email="unknown@example.test",
            password=login_account["password"],
            organization_slug=login_account["organization"]["slug"],
        )


def test_login_rejects_wrong_organization(login_account):
    with pytest.raises(ValueError, match="Invalid email, password, or organization"):
        AuthenticationService.login(
            email=login_account["user"]["email"],
            password=login_account["password"],
            organization_slug="wrong-organization",
        )


@pytest.mark.parametrize(
    ("email", "password", "organization_slug"),
    [
        ("", "password", "organization"),
        ("user@example.test", "", "organization"),
        ("user@example.test", "password", ""),
    ],
)
def test_login_rejects_missing_inputs(email, password, organization_slug):
    with pytest.raises(ValueError):
        AuthenticationService.login(
            email=email,
            password=password,
            organization_slug=organization_slug,
        )
