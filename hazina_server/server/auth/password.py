from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Return a secure Argon2id password hash."""
    if not isinstance(password, str) or not password:
        raise ValueError("Password must not be empty.")

    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its stored hash."""
    if not isinstance(password, str) or not isinstance(hashed_password, str):
        return False

    if not password or not hashed_password:
        return False

    try:
        return password_hash.verify(password, hashed_password)
    except (ValueError, TypeError):
        return False