
import uuid

import pytest

from hazina_pipeline.database.connection import get_database_connection
from server.services.auth_service import AuthService


@pytest.fixture
def login_test_account():
    suffix = uuid.uuid4().hex[:12]

    organization = AuthService.create_organization(
        name="Login Test Organization",
        slug=f"login-org-{suffix}",
    )

    user = AuthService.create_user(
        email=f"login-{suffix}@example.test",
        password_hash="test-password-hash",
        full_name="Login Test User",
    )

    membership = AuthService.create_membership(
        organization_id=organization["organization_id"],
        user_id=user["user_id"],
        role_code="OPERATOR",
    )

    return {
        "organization": organization,
        "user": user,
        "membership": membership,
    }


def test_get_active_user_membership(login_test_account):
    organization = login_test_account["organization"]
    user = login_test_account["user"]

    result = AuthService.get_active_user_membership(
        user["email"],
        organization["slug"],
    )

    assert result is not None
    assert result["user_id"] == user["user_id"]
    assert result["email"] == user["email"]
    assert result["organization_id"] == organization["organization_id"]
    assert result["organization_slug"] == organization["slug"]
    assert result["role_code"] == "OPERATOR"
    assert result["is_active"] is True
    assert result["membership_is_active"] is True


def test_get_active_user_membership_normalizes_inputs(login_test_account):
    organization = login_test_account["organization"]
    user = login_test_account["user"]

    result = AuthService.get_active_user_membership(
        f"  {user['email'].upper()}  ",
        f"  {organization['slug'].upper()}  ",
    )

    assert result is not None
    assert result["user_id"] == user["user_id"]


def test_get_active_user_membership_returns_none_for_unknown_email(
    login_test_account,
):
    organization = login_test_account["organization"]

    result = AuthService.get_active_user_membership(
        "unknown@example.test",
        organization["slug"],
    )

    assert result is None


def test_get_active_user_membership_returns_none_for_unknown_organization(
    login_test_account,
):
    user = login_test_account["user"]

    result = AuthService.get_active_user_membership(
        user["email"],
        "unknown-organization",
    )

    assert result is None


def test_get_active_user_membership_rejects_inactive_user(
    login_test_account,
):
    user = login_test_account["user"]
    organization = login_test_account["organization"]

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

    result = AuthService.get_active_user_membership(
        user["email"],
        organization["slug"],
    )

    assert result is None


def test_get_active_user_membership_rejects_inactive_organization(
    login_test_account,
):
    user = login_test_account["user"]
    organization = login_test_account["organization"]

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE auth.organizations
                SET is_active = FALSE
                WHERE organization_id = %s;
                """,
                (organization["organization_id"],),
            )

    result = AuthService.get_active_user_membership(
        user["email"],
        organization["slug"],
    )

    assert result is None


def test_get_active_user_membership_rejects_inactive_membership(
    login_test_account,
):
    user = login_test_account["user"]
    organization = login_test_account["organization"]

    with get_database_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE auth.organization_memberships
                SET is_active = FALSE
                WHERE organization_id = %s
                  AND user_id = %s;
                """,
                (
                    organization["organization_id"],
                    user["user_id"],
                ),
            )

    result = AuthService.get_active_user_membership(
        user["email"],
        organization["slug"],
    )

    assert result is None


@pytest.mark.parametrize(
    ("email", "organization_slug"),
    [
        ("", "valid-org"),
        ("valid@example.test", ""),
        ("   ", "valid-org"),
        ("valid@example.test", "   "),
    ],
)
def test_get_active_user_membership_rejects_empty_inputs(
    email,
    organization_slug,
):
    with pytest.raises(ValueError):
        AuthService.get_active_user_membership(
            email,
            organization_slug,
        )
