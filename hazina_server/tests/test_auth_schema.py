
import pytest
from pydantic import ValidationError

from server.schemas.auth_schema import (
    LoginRequest,
    RefreshRequest,
    LogoutRequest,
    TokenResponse,
)


def test_login_request_accepts_valid_data():
    request = LoginRequest(
        email="user@example.com",
        password="StrongPassword123!",
        organization_slug="hazina",
    )

    assert request.email == "user@example.com"
    assert request.password == "StrongPassword123!"
    assert request.organization_slug == "hazina"


def test_login_request_rejects_invalid_email():
    with pytest.raises(ValidationError):
        LoginRequest(
            email="invalid-email",
            password="StrongPassword123!",
            organization_slug="hazina",
        )


def test_login_request_rejects_empty_password():
    with pytest.raises(ValidationError):
        LoginRequest(
            email="user@example.com",
            password="",
            organization_slug="hazina",
        )


def test_login_request_rejects_empty_organization_slug():
    with pytest.raises(ValidationError):
        LoginRequest(
            email="user@example.com",
            password="StrongPassword123!",
            organization_slug="",
        )


def test_refresh_request_requires_token():
    with pytest.raises(ValidationError):
        RefreshRequest(refresh_token="")


def test_logout_request_requires_token():
    with pytest.raises(ValidationError):
        LogoutRequest(refresh_token="")


def test_token_response_defaults_to_bearer():
    response = TokenResponse(
        access_token="access-token",
        refresh_token="refresh-token",
        access_token_expires_in=900,
    )

    assert response.token_type == "bearer"
    assert response.access_token_expires_in == 900
