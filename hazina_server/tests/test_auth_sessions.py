
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from server.services.auth_service import AuthService


@pytest.fixture
def active_membership():
    organization = AuthService.create_organization(
        name="Session Test Organization",
        slug=f"session-org-{uuid.uuid4().hex[:12]}",
    )

    user = AuthService.create_user(
        email=f"{uuid.uuid4().hex}@example.test",
        password_hash="test-password-hash",
        full_name="Session Test User",
    )

    AuthService.create_membership(
        organization_id=organization["organization_id"],
        user_id=user["user_id"],
        role_code="OPERATOR",
    )

    return {
        "organization": organization,
        "user": user,
    }


def test_create_and_get_active_refresh_session(active_membership):
    user = active_membership["user"]
    organization = active_membership["organization"]

    token_jti = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    session = AuthService.create_refresh_session(
        user_id=user["user_id"],
        organization_id=organization["organization_id"],
        token_jti=token_jti,
        expires_at=expires_at,
    )

    assert session["user_id"] == user["user_id"]
    assert session["organization_id"] == organization["organization_id"]
    assert session["token_jti"] == token_jti

    retrieved = AuthService.get_active_refresh_session(token_jti)

    assert retrieved is not None
    assert retrieved["refresh_token_id"] == session["refresh_token_id"]
    assert retrieved["token_jti"] == token_jti


def test_revoke_refresh_session(active_membership):
    user = active_membership["user"]
    organization = active_membership["organization"]
    token_jti = str(uuid.uuid4())

    AuthService.create_refresh_session(
        user_id=user["user_id"],
        organization_id=organization["organization_id"],
        token_jti=token_jti,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    assert AuthService.revoke_refresh_session(token_jti) is True
    assert AuthService.get_active_refresh_session(token_jti) is None
    assert AuthService.revoke_refresh_session(token_jti) is False


def test_unknown_refresh_session_returns_none():
    assert AuthService.get_active_refresh_session(
        str(uuid.uuid4())
    ) is None


def test_create_refresh_session_rejects_invalid_jti(active_membership):
    with pytest.raises(ValueError, match="token_jti"):
        AuthService.create_refresh_session(
            user_id=active_membership["user"]["user_id"],
            organization_id=active_membership["organization"]["organization_id"],
            token_jti="invalid-jti",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )


def test_create_refresh_session_rejects_naive_expiration(active_membership):
    with pytest.raises(ValueError, match="timezone"):
        AuthService.create_refresh_session(
            user_id=active_membership["user"]["user_id"],
            organization_id=active_membership["organization"]["organization_id"],
            token_jti=str(uuid.uuid4()),
            expires_at=datetime.now() + timedelta(days=7),
        )


def test_create_refresh_session_rejects_expired_token(active_membership):
    with pytest.raises(ValueError, match="future"):
        AuthService.create_refresh_session(
            user_id=active_membership["user"]["user_id"],
            organization_id=active_membership["organization"]["organization_id"],
            token_jti=str(uuid.uuid4()),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )


def test_create_refresh_session_requires_active_membership(active_membership):
    with pytest.raises(ValueError, match="membership"):
        AuthService.create_refresh_session(
            user_id=999999999,
            organization_id=active_membership["organization"]["organization_id"],
            token_jti=str(uuid.uuid4()),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )


def test_rotate_refresh_session(active_membership):
    user = active_membership["user"]
    organization = active_membership["organization"]

    old_jti = str(uuid.uuid4())
    new_jti = str(uuid.uuid4())

    AuthService.create_refresh_session(
        user_id=user["user_id"],
        organization_id=organization["organization_id"],
        token_jti=old_jti,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    rotated = AuthService.rotate_refresh_session(
        old_token_jti=old_jti,
        new_token_jti=new_jti,
        new_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    assert rotated["token_jti"] == new_jti
    assert rotated["replaced_token_jti"] == old_jti

    assert AuthService.get_active_refresh_session(old_jti) is None
    assert AuthService.get_active_refresh_session(new_jti) is not None


def test_cannot_rotate_same_refresh_token_twice(active_membership):
    user = active_membership["user"]
    organization = active_membership["organization"]

    old_jti = str(uuid.uuid4())

    AuthService.create_refresh_session(
        user_id=user["user_id"],
        organization_id=organization["organization_id"],
        token_jti=old_jti,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    AuthService.rotate_refresh_session(
        old_token_jti=old_jti,
        new_token_jti=str(uuid.uuid4()),
        new_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )

    with pytest.raises(ValueError, match="invalid, expired, or revoked"):
        AuthService.rotate_refresh_session(
            old_token_jti=old_jti,
            new_token_jti=str(uuid.uuid4()),
            new_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )


def test_rotation_rejects_same_jti(active_membership):
    token_jti = str(uuid.uuid4())

    with pytest.raises(ValueError, match="new JTI"):
        AuthService.rotate_refresh_session(
            old_token_jti=token_jti,
            new_token_jti=token_jti,
            new_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )


def test_rotation_rejects_invalid_jti():
    with pytest.raises(ValueError, match="Valid token JTIs"):
        AuthService.rotate_refresh_session(
            old_token_jti="invalid",
            new_token_jti=str(uuid.uuid4()),
            new_expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )


def test_rotation_rejects_naive_expiration():
    with pytest.raises(ValueError, match="timezone"):
        AuthService.rotate_refresh_session(
            old_token_jti=str(uuid.uuid4()),
            new_token_jti=str(uuid.uuid4()),
            new_expires_at=datetime.now() + timedelta(days=7),
        )

# Session revocation integrity test
# if creating the replacement session fails, the original session remains active

def test_failed_rotation_preserves_old_session(active_membership):
    user = active_membership["user"]
    organization = active_membership["organization"]

    old_jti = str(uuid.uuid4())
    duplicate_jti = str(uuid.uuid4())

    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    AuthService.create_refresh_session(
        user_id=user["user_id"],
        organization_id=organization["organization_id"],
        token_jti=old_jti,
        expires_at=expires_at,
    )

    AuthService.create_refresh_session(
        user_id=user["user_id"],
        organization_id=organization["organization_id"],
        token_jti=duplicate_jti,
        expires_at=expires_at,
    )

    with pytest.raises(Exception):
        AuthService.rotate_refresh_session(
            old_token_jti=old_jti,
            new_token_jti=duplicate_jti,
            new_expires_at=expires_at,
        )

    assert AuthService.get_active_refresh_session(old_jti) is not None
    assert AuthService.get_active_refresh_session(duplicate_jti) is not None