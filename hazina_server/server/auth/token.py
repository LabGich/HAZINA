import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from dotenv import load_dotenv
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = SERVER_ROOT.parent

load_dotenv(PROJECT_ROOT / ".env")


JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15")
)

REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
)


def _get_secret_key():
    if not JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY is not configured.")

    return JWT_SECRET_KEY


def create_access_token(user_id: int, organization_id: int, role: str) -> str:
    """Create a short-lived JWT access token."""
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "organization_id": organization_id,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": str(uuid4()),
    }

    return jwt.encode(payload, _get_secret_key(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int, organization_id: int) -> str:
    """Create a longer-lived JWT refresh token."""
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "organization_id": organization_id,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "jti": str(uuid4()),
    }

    return jwt.encode(payload, _get_secret_key(), algorithm=JWT_ALGORITHM)


def decode_token(token: str, expected_type: str | None = None) -> dict:
    """Decode and validate a JWT."""
    if not isinstance(token, str) or not token:
        raise ValueError("A valid token is required.")

    try:
        payload = jwt.decode(
            token,
            _get_secret_key(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub", "jti", "type"]},
        )
    except jwt.InvalidTokenError as exc:
        raise ValueError("Invalid or expired token.") from exc

    if expected_type and payload.get("type") != expected_type:
        raise ValueError("Invalid token type.")

    return payload