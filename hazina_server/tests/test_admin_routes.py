
from unittest.mock import patch

from fastapi.testclient import TestClient

from server.auth.dependencies import get_current_auth_context
from server.main import app


client = TestClient(app)


SAMPLE_ADMIN = {
    "user_id": 1,
    "organization_id": 10,
    "role_code": "ADMIN",
}

SAMPLE_USER = {
    "user_id": 2,
    "email": "operator@example.com",
    "full_name": "Test Operator",
    "user_is_active": True,
    "email_verified": False,
    "membership_id": 20,
    "membership_is_active": True,
    "role_code": "OPERATOR",
    "membership_created_at": "2026-01-01T00:00:00Z",
}


def set_auth_context(role_code="ADMIN", user_id=1):
    app.dependency_overrides[get_current_auth_context] = lambda: {
        "user_id": user_id,
        "organization_id": 10,
        "role_code": role_code,
    }


def clear_auth_context():
    app.dependency_overrides.clear()


def test_list_users_requires_authentication():
    clear_auth_context()

    response = client.get("/admin/users")

    assert response.status_code == 401


def test_list_users_requires_admin_role():
    set_auth_context(role_code="OPERATOR")

    try:
        response = client.get("/admin/users")
        assert response.status_code == 403
    finally:
        clear_auth_context()


def test_list_users_endpoint():
    set_auth_context()

    expected = [SAMPLE_USER]

    try:
        with patch(
            "server.routers.admin.AuthenticationService.list_organization_users",
            return_value=expected,
        ) as mock_list:
            response = client.get("/admin/users")

        assert response.status_code == 200
        assert response.json() == expected
        mock_list.assert_called_once_with(organization_id=10)
    finally:
        clear_auth_context()


def test_create_user_endpoint():
    set_auth_context()

    request_data = {
        "email": "operator@example.com",
        "password": "StrongPassword123!",
        "full_name": "Test Operator",
        "role_code": "OPERATOR",
    }

    try:
        with patch(
            "server.routers.admin.AuthenticationService.create_organization_user",
            return_value=SAMPLE_USER,
        ) as mock_create:
            response = client.post("/admin/users", json=request_data)

        assert response.status_code == 201
        assert response.json() == SAMPLE_USER

        mock_create.assert_called_once_with(
            organization_id=10,
            email="operator@example.com",
            password="StrongPassword123!",
            full_name="Test Operator",
            role_code="OPERATOR",
        )
    finally:
        clear_auth_context()


def test_create_user_rejects_invalid_data():
    set_auth_context()

    try:
        response = client.post(
            "/admin/users",
            json={
                "email": "invalid-email",
                "password": "short",
                "full_name": "Test Operator",
                "role_code": "INVALID",
            },
        )

        assert response.status_code == 422
    finally:
        clear_auth_context()


def test_create_user_rejects_service_validation_error():
    set_auth_context()

    try:
        with patch(
            "server.routers.admin.AuthenticationService.create_organization_user",
            side_effect=ValueError("Organization is inactive."),
        ):
            response = client.post(
                "/admin/users",
                json={
                    "email": "operator@example.com",
                    "password": "StrongPassword123!",
                    "full_name": "Test Operator",
                    "role_code": "OPERATOR",
                },
            )

        assert response.status_code == 400
        assert response.json()["detail"] == "Organization is inactive."
    finally:
        clear_auth_context()


def test_update_user_endpoint():
    set_auth_context()

    try:
        with patch(
            "server.routers.admin.AuthenticationService.update_organization_user",
            return_value=SAMPLE_USER,
        ) as mock_update:
            response = client.patch(
                "/admin/users/2",
                json={"role_code": "OPERATOR"},
            )

        assert response.status_code == 200
        assert response.json() == SAMPLE_USER

        mock_update.assert_called_once_with(
            organization_id=10,
            user_id=2,
            role_code="OPERATOR",
            is_active=None,
        )
    finally:
        clear_auth_context()


def test_update_user_not_found():
    set_auth_context()

    try:
        with patch(
            "server.routers.admin.AuthenticationService.update_organization_user",
            return_value=None,
        ):
            response = client.patch(
                "/admin/users/999",
                json={"is_active": False},
            )

        assert response.status_code == 404
    finally:
        clear_auth_context()


def test_update_user_rejects_empty_update():
    set_auth_context()

    try:
        response = client.patch(
            "/admin/users/2",
            json={},
        )

        assert response.status_code == 400
    finally:
        clear_auth_context()


def test_admin_cannot_change_own_role():
    set_auth_context(user_id=1)

    try:
        response = client.patch(
            "/admin/users/1",
            json={"role_code": "OPERATOR"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == (
            "You cannot change your own role."
        )
    finally:
        clear_auth_context()


def test_admin_cannot_deactivate_own_membership():
    set_auth_context(user_id=1)

    try:
        response = client.patch(
            "/admin/users/1",
            json={"is_active": False},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == (
            "You cannot deactivate your own membership."
        )
    finally:
        clear_auth_context()


def test_admin_can_update_own_membership_without_self_lockout():
    set_auth_context(user_id=1)

    try:
        with patch(
            "server.routers.admin.AuthenticationService.update_organization_user",
            return_value={
                **SAMPLE_USER,
                "user_id": 1,
                "role_code": "ADMIN",
            },
        ) as mock_update:
            response = client.patch(
                "/admin/users/1",
                json={"is_active": True},
            )

        assert response.status_code == 200
        mock_update.assert_called_once_with(
            organization_id=10,
            user_id=1,
            role_code=None,
            is_active=True,
        )
    finally:
        clear_auth_context()


def test_update_user_requires_admin_role():
    set_auth_context(role_code="VIEWER")

    try:
        response = client.patch(
            "/admin/users/2",
            json={"is_active": False},
        )

        assert response.status_code == 403
    finally:
        clear_auth_context()
