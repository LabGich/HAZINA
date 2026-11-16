
import uuid

import pytest

from server.services.auth_service import AuthService


@pytest.fixture
def test_organization(): #for test only, we are supposed to use conftest,py otherwise
    slug = f"membership-org-{uuid.uuid4().hex[:12]}"
    return AuthService.create_organization(
        name="Membership Test Organization",
        slug=slug,
    )


@pytest.fixture
def test_user():
    email = f"{uuid.uuid4().hex}@example.test"
    return AuthService.create_user(
        email=email,
        password_hash="test-password-hash",
        full_name="Membership Test User",
    )


@pytest.mark.parametrize("role_code", ["ADMIN", "OPERATOR", "VIEWER"])
def test_create_membership(test_organization, test_user, role_code):
    membership = AuthService.create_membership(
        organization_id=test_organization["organization_id"],
        user_id=test_user["user_id"],
        role_code=role_code,
    )

    assert membership["organization_id"] == test_organization["organization_id"]
    assert membership["user_id"] == test_user["user_id"]
    assert membership["role_code"] == role_code
    assert membership["is_active"] is True


def test_get_user_memberships(test_organization, test_user):
    AuthService.create_membership(
        organization_id=test_organization["organization_id"],
        user_id=test_user["user_id"],
        role_code="OPERATOR",
    )

    memberships = AuthService.get_user_memberships(
        test_user["user_id"]
    )

    assert len(memberships) == 1
    assert memberships[0]["organization_name"] == test_organization["name"]
    assert memberships[0]["organization_slug"] == test_organization["slug"]
    assert memberships[0]["role_code"] == "OPERATOR"
    assert memberships[0]["is_active"] is True


def test_create_membership_rejects_unknown_role(test_organization, test_user):
    with pytest.raises(ValueError, match="Unknown role"):
        AuthService.create_membership(
            organization_id=test_organization["organization_id"],
            user_id=test_user["user_id"],
            role_code="SUPERADMIN",
        )


def test_create_membership_rejects_invalid_ids():
    with pytest.raises(ValueError):
        AuthService.create_membership(0, 1, "ADMIN")

    with pytest.raises(ValueError):
        AuthService.create_membership(1, 0, "ADMIN")


def test_get_user_memberships_rejects_invalid_user_id():
    with pytest.raises(ValueError):
        AuthService.get_user_memberships(0)


def test_get_user_memberships_returns_empty_for_unknown_user():
    memberships = AuthService.get_user_memberships(999999999)
    assert memberships == []
