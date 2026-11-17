
import uuid

import pytest

from server.services.auth_service import AuthService
from hazina_pipeline.database.connection import get_database_connection


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


def test_update_membership_role(test_organization, test_user):
    AuthService.create_membership(
        organization_id=test_organization["organization_id"],
        user_id=test_user["user_id"],
        role_code="VIEWER",
    )

    updated = AuthService.update_organization_membership(
        organization_id=test_organization["organization_id"],
        user_id=test_user["user_id"],
        role_code="OPERATOR",
    )

    assert updated is not None
    assert updated["role_code"] == "OPERATOR"
    assert updated["is_active"] is True


def test_deactivate_membership(test_organization, test_user):
    AuthService.create_membership(
        organization_id=test_organization["organization_id"],
        user_id=test_user["user_id"],
        role_code="OPERATOR",
    )

    updated = AuthService.update_organization_membership(
        organization_id=test_organization["organization_id"],
        user_id=test_user["user_id"],
        is_active=False,
    )

    assert updated is not None
    assert updated["is_active"] is False

    # Deactivating membership must not deactivate the global account.
    user = AuthService.get_user_by_email(test_user["email"])
    assert user["is_active"] is True


def test_update_membership_returns_none_for_unknown_user(
    test_organization,
):
    updated = AuthService.update_organization_membership(
        organization_id=test_organization["organization_id"],
        user_id=999999999,
        role_code="ADMIN",
    )

    assert updated is None


def test_update_membership_rejects_unknown_role(
    test_organization,
    test_user,
):
    AuthService.create_membership(
        organization_id=test_organization["organization_id"],
        user_id=test_user["user_id"],
        role_code="VIEWER",
    )

    with pytest.raises(ValueError, match="Unknown role"):
        AuthService.update_organization_membership(
            organization_id=test_organization["organization_id"],
            user_id=test_user["user_id"],
            role_code="SUPERADMIN",
        )


def test_update_membership_rejects_empty_update(
    test_organization,
    test_user,
):
    with pytest.raises(ValueError, match="At least one"):
        AuthService.update_organization_membership(
            organization_id=test_organization["organization_id"],
            user_id=test_user["user_id"],
        )


from server.auth.password import hash_password


def test_create_new_user_with_membership(test_organization):
    email = f"{uuid.uuid4().hex}@example.test"

    result = AuthService.create_user_with_membership(
        email=email,
        password_hash=hash_password("Test-Password-123!"),
        full_name="New Admin User",
        organization_id=test_organization["organization_id"],
        role_code="OPERATOR",
    )

    assert result["email"] == email
    assert result["full_name"] == "New Admin User"
    assert result["role_code"] == "OPERATOR"
    assert result["user_is_active"] is True
    assert result["membership_is_active"] is True


def test_add_existing_user_preserves_account_details(
    test_organization,
):
    email = f"{uuid.uuid4().hex}@example.test"
    original_hash = hash_password("Original-Password-123!")

    original_user = AuthService.create_user(
        email=email,
        password_hash=original_hash,
        full_name="Original Full Name",
    )

    result = AuthService.create_user_with_membership(
        email=email,
        password_hash=hash_password("Different-Password-456!"),
        full_name="Different Full Name",
        organization_id=test_organization["organization_id"],
        role_code="VIEWER",
    )

    retrieved = AuthService.get_user_by_email(email)

    assert result["user_id"] == original_user["user_id"]
    assert retrieved["full_name"] == "Original Full Name"
    assert retrieved["password_hash"] == original_hash
    assert result["role_code"] == "VIEWER"


def test_create_user_with_membership_rejects_duplicate_membership(
    test_organization,
    test_user,
):
    AuthService.create_membership(
        organization_id=test_organization["organization_id"],
        user_id=test_user["user_id"],
        role_code="VIEWER",
    )

    with pytest.raises(ValueError, match="already has a membership"):
        AuthService.create_user_with_membership(
            email=test_user["email"],
            password_hash="another-hash",
            full_name="Another Name",
            organization_id=test_organization["organization_id"],
            role_code="OPERATOR",
        )


def test_create_user_with_membership_rejects_unknown_role(
    test_organization,
):
    with pytest.raises(ValueError, match="Unknown role"):
        AuthService.create_user_with_membership(
            email="new-user@example.test",
            password_hash="some-hash",
            full_name="New User",
            organization_id=test_organization["organization_id"],
            role_code="SUPERADMIN",
        )


def test_create_user_with_membership_rejects_inactive_user(
    test_organization,
):
    email = f"{uuid.uuid4().hex}@example.test"
    user = AuthService.create_user(
        email=email,
        password_hash="some-hash",
        full_name="Inactive User",
    )

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE auth.users
                SET is_active = FALSE
                WHERE user_id = %s;
                """,
                (user["user_id"],),
            )

    with pytest.raises(ValueError, match="account is inactive"):
        AuthService.create_user_with_membership(
            email=email,
            password_hash="another-hash",
            full_name="Another Name",
            organization_id=test_organization["organization_id"],
            role_code="VIEWER",
        )
