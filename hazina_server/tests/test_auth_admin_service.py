
import uuid

import pytest

from server.services.auth_service import AuthService


@pytest.fixture
def test_organization():
    return AuthService.create_organization(
        name="Admin Test Organization",
        slug=f"admin-org-{uuid.uuid4().hex[:12]}",
    )


@pytest.fixture
def test_user():
    return AuthService.create_user(
        email=f"{uuid.uuid4().hex}@example.test",
        password_hash="test-password-hash",
        full_name="Admin Test User",
    )


def test_list_organization_users(test_organization, test_user):
    AuthService.create_membership(
        organization_id=test_organization["organization_id"],
        user_id=test_user["user_id"],
        role_code="OPERATOR",
    )

    users = AuthService.list_organization_users(
        test_organization["organization_id"]
    )

    assert len(users) == 1
    assert users[0]["user_id"] == test_user["user_id"]
    assert users[0]["email"] == test_user["email"]
    assert users[0]["role_code"] == "OPERATOR"
    assert users[0]["user_is_active"] is True
    assert users[0]["membership_is_active"] is True


def test_list_organization_users_returns_empty(test_organization):
    users = AuthService.list_organization_users(
        test_organization["organization_id"]
    )

    assert users == []


@pytest.mark.parametrize("organization_id", [0, -1, True, "1", None])
def test_list_organization_users_rejects_invalid_id(organization_id):
    with pytest.raises(ValueError):
        AuthService.list_organization_users(organization_id)
