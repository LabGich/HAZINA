import jwt
import pytest

from server.auth.token import (
    create_access_token,
    create_refresh_token,
    decode_token,
)


def test_create_and_decode_access_token():
    token = create_access_token(
        user_id=1,
        organization_id=10,
        role="ADMIN",
    )

    payload = decode_token(token, expected_type="access")

    assert payload["sub"] == "1"
    assert payload["organization_id"] == 10
    assert payload["role"] == "ADMIN"
    assert payload["type"] == "access"


def test_create_and_decode_refresh_token():
    token = create_refresh_token(
        user_id=1,
        organization_id=10,
    )

    payload = decode_token(token, expected_type="refresh")

    assert payload["sub"] == "1"
    assert payload["organization_id"] == 10
    assert payload["type"] == "refresh"


def test_access_token_cannot_be_used_as_refresh_token():
    token = create_access_token(1, 10, "ADMIN")

    with pytest.raises(ValueError, match="Invalid token type"):
        decode_token(token, expected_type="refresh")


def test_refresh_token_cannot_be_used_as_access_token():
    token = create_refresh_token(1, 10)

    with pytest.raises(ValueError, match="Invalid token type"):
        decode_token(token, expected_type="access")


def test_decode_rejects_invalid_token():
    with pytest.raises(ValueError, match="Invalid or expired token"):
        decode_token("invalid.token.value")


def test_decode_rejects_expired_token(monkeypatch):
    import server.auth.token as token_service
    from datetime import datetime, timedelta, timezone

    expired_payload = {
        "sub": "1",
        "organization_id": 10,
        "type": "access",
        "iat": datetime.now(timezone.utc) - timedelta(minutes=30),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=15),
        "jti": "expired-token",
    }

    expired_token = jwt.encode(
        expired_payload,
        token_service._get_secret_key(),
        algorithm=token_service.JWT_ALGORITHM,
    )

    with pytest.raises(ValueError, match="Invalid or expired token"):
        decode_token(expired_token)
