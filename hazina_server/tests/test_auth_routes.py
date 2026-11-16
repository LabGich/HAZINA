
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from server.main import app


client = TestClient(app)


SAMPLE_USER = {
    "user_id": 1,
    "email": "admin@example.com",
    "full_name": "Test Admin",
    "organization_id": 1,
    "organization_name": "Test Organization",
    "organization_slug": "test-org",
    "role_code": "ADMIN",
    "memberships": [
        {
            "organization_id": 1,
            "organization_name": "Test Organization",
            "organization_slug": "test-org",
            "role_code": "ADMIN",
            "is_active": True,
            "created_at": datetime(
                2026, 1, 1, tzinfo=timezone.utc
            ),
        }
    ],
}


def assert_user_response(actual, expected):
    assert actual["user_id"] == expected["user_id"]
    assert actual["email"] == expected["email"]
    assert actual["full_name"] == expected["full_name"]
    assert actual["organization_id"] == expected["organization_id"]
    assert actual["organization_name"] == expected["organization_name"]
    assert actual["organization_slug"] == expected["organization_slug"]
    assert actual["role_code"] == expected["role_code"]

    assert len(actual["memberships"]) == len(expected["memberships"])

    for actual_membership, expected_membership in zip(
        actual["memberships"],
        expected["memberships"],
    ):
        assert (
            actual_membership["organization_id"]
            == expected_membership["organization_id"]
        )
        assert (
            actual_membership["organization_name"]
            == expected_membership["organization_name"]
        )
        assert (
            actual_membership["organization_slug"]
            == expected_membership["organization_slug"]
        )
        assert actual_membership["role_code"] == expected_membership["role_code"]
        assert actual_membership["is_active"] == expected_membership["is_active"]
        assert datetime.fromisoformat(
            actual_membership["created_at"]
        ) == expected_membership["created_at"]


def test_login_endpoint():
    expected = {
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
        "token_type": "bearer",
        "access_token_expires_in": 900,
        "user": SAMPLE_USER,
    }

    with patch(
        "server.routers.auth.AuthenticationService.login",
        return_value=expected,
    ) as mock_login:
        response = client.post(
            "/auth/login",
            json={
                "email": "admin@example.com",
                "password": "StrongPassword123!",
                "organization_slug": "test-org",
            },
        )

    assert response.status_code == 200
    response_data = response.json()

    assert response_data["access_token"] == expected["access_token"]
    assert response_data["refresh_token"] == expected["refresh_token"]
    assert response_data["token_type"] == expected["token_type"]
    assert (
        response_data["access_token_expires_in"]
        == expected["access_token_expires_in"]
    )
    assert_user_response(response_data["user"], SAMPLE_USER)

    mock_login.assert_called_once_with(
        email="admin@example.com",
        password="StrongPassword123!",
        organization_slug="test-org",
    )


def test_login_invalid_credentials():
    with patch(
        "server.routers.auth.AuthenticationService.login",
        side_effect=ValueError(
            "Invalid email, password, or organization."
        ),
    ):
        response = client.post(
            "/auth/login",
            json={
                "email": "admin@example.com",
                "password": "wrong-password",
                "organization_slug": "test-org",
            },
        )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid email, password, or organization."
    )


def test_login_validates_request():
    response = client.post(
        "/auth/login",
        json={
            "email": "not-an-email",
            "password": "",
            "organization_slug": "test-org",
        },
    )

    assert response.status_code == 422


def test_refresh_endpoint():
    expected = {
        "access_token": "new-access-token",
        "refresh_token": "new-refresh-token",
        "token_type": "bearer",
        "access_token_expires_in": 900,
    }

    with patch(
        "server.routers.auth.AuthenticationService.refresh",
        return_value=expected,
    ) as mock_refresh:
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "old-refresh-token"},
        )

    assert response.status_code == 200
    assert response.json() == expected
    mock_refresh.assert_called_once_with(
        refresh_token="old-refresh-token",
    )


def test_refresh_invalid_token():
    with patch(
        "server.routers.auth.AuthenticationService.refresh",
        side_effect=ValueError(
            "Refresh token is invalid, expired, or revoked."
        ),
    ):
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )

    assert response.status_code == 401


def test_logout_endpoint():
    expected = {"message": "Successfully logged out."}

    with patch(
        "server.routers.auth.AuthenticationService.logout",
        return_value=expected,
    ) as mock_logout:
        response = client.post(
            "/auth/logout",
            json={"refresh_token": "valid-refresh-token"},
        )

    assert response.status_code == 200
    assert response.json() == expected
    mock_logout.assert_called_once_with(
        refresh_token="valid-refresh-token",
    )


def test_logout_invalid_token():
    with patch(
        "server.routers.auth.AuthenticationService.logout",
        side_effect=ValueError("Refresh token is invalid."),
    ):
        response = client.post(
            "/auth/logout",
            json={"refresh_token": "invalid-token"},
        )

    assert response.status_code == 401


def test_me_requires_authentication():
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_me_endpoint():
    from server.auth.dependencies import get_current_auth_context

    expected_context = {
        "user_id": 1,
        "organization_id": 1,
        "role_code": "ADMIN",
    }

    app.dependency_overrides[get_current_auth_context] = (
        lambda: expected_context
    )

    try:
        with patch(
            "server.routers.auth.AuthenticationService.get_current_user",
            return_value=SAMPLE_USER,
        ) as mock_get_user:
            response = client.get("/auth/me")

        assert response.status_code == 200
        assert_user_response(response.json(), SAMPLE_USER)

        mock_get_user.assert_called_once_with(
            user_id=1,
            organization_id=1,
        )
    finally:
        app.dependency_overrides.clear()
