from server.auth.password import hash_password, verify_password


def test_hash_password_returns_hash():
    password = "Hazina-Test-Password-123!"

    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2")


def test_hash_password_generates_unique_hashes():
    password = "Hazina-Test-Password-123!"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash


def test_verify_password_accepts_correct_password():
    password = "Hazina-Test-Password-123!"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_rejects_incorrect_password():
    hashed = hash_password("Hazina-Test-Password-123!")

    assert verify_password("Wrong-Password", hashed) is False


def test_hash_password_rejects_empty_password():
    import pytest

    with pytest.raises(ValueError):
        hash_password("")


def test_verify_password_rejects_invalid_inputs():
    assert verify_password("", "some-hash") is False
    assert verify_password("password", "") is False
    assert verify_password(None, "some-hash") is False
    assert verify_password("password", None) is False