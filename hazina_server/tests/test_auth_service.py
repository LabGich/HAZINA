import uuid

import pytest

from server.services.auth_service import AuthService
from server.auth.password import hash_password


@pytest.fixture
def test_organization():
    slug = f"test-org-{uuid.uuid4().hex[:12]}"

    organization = AuthService.create_organization(
        name="Hazina Test Organization",
        slug=slug,
    )

    yield organization


def test_create_and_get_organization(test_organization):
    organization = AuthService.get_organization(
        test_organization["organization_id"]
    )

    assert organization is not None
    assert organization["name"] == "Hazina Test Organization"
    assert organization["slug"] == test_organization["slug"]


def test_create_organization_rejects_empty_values():
    with pytest.raises(ValueError):
        AuthService.create_organization("", "test-org")

    with pytest.raises(ValueError):
        AuthService.create_organization("Test Org", "")


def test_get_unknown_organization_returns_none():
    assert AuthService.get_organization(999999999) is None


def test_create_and_get_user():
    email = f"{uuid.uuid4().hex}@example.test"
    password = "Hazina-Test-Password-123!"

    user = AuthService.create_user(
        email=email.upper(),
        password_hash=hash_password(password),
        full_name="Test User",
    )

    retrieved = AuthService.get_user_by_email(email)

    assert retrieved is not None
    assert retrieved["user_id"] == user["user_id"]
    assert retrieved["email"] == email
    assert retrieved["full_name"] == "Test User"
    assert retrieved["is_active"] is True
    assert retrieved["password_hash"] != password


def test_get_unknown_user_returns_none():
    assert (
        AuthService.get_user_by_email(
            f"{uuid.uuid4().hex}@example.test"
        )
        is None
    )


def test_create_user_rejects_empty_values():
    with pytest.raises(ValueError):
        AuthService.create_user("", "some-hash", "Test User")

    with pytest.raises(ValueError):
        AuthService.create_user("test@example.test", "", "Test User")

    with pytest.raises(ValueError):
        AuthService.create_user(
            "test@example.test",
            "some-hash",
            "",
        )