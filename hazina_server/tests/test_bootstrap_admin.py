
from server.commands import bootstrap_admin


def test_bootstrap_admin_success(monkeypatch, capsys):
    inputs = iter(
        [
            "Test Organization",
            "test-organization",
            "admin@example.test",
            "Test Admin",
        ]
    )
    passwords = iter(
        [
            "Secure-Password-123!",
            "Secure-Password-123!",
        ]
    )

    captured = {}

    monkeypatch.setattr(
        "builtins.input",
        lambda prompt="": next(inputs),
    )
    monkeypatch.setattr(
        bootstrap_admin.getpass,
        "getpass",
        lambda prompt="": next(passwords),
    )
    monkeypatch.setattr(
        bootstrap_admin,
        "hash_password",
        lambda password: f"hashed-{password}",
    )

    def fake_create_organization_with_admin(**kwargs):
        captured.update(kwargs)
        return {
            "organization_name": kwargs["organization_name"],
            "organization_slug": kwargs["organization_slug"],
            "email": kwargs["email"],
            "user_id": 10,
            "organization_id": 20,
        }

    monkeypatch.setattr(
        bootstrap_admin.AuthService,
        "create_organization_with_admin",
        fake_create_organization_with_admin,
    )

    result = bootstrap_admin.main()

    output = capsys.readouterr().out

    assert result == 0
    assert captured["organization_name"] == "Test Organization"
    assert captured["organization_slug"] == "test-organization"
    assert captured["email"] == "admin@example.test"
    assert captured["full_name"] == "Test Admin"
    assert captured["password_hash"] == (
        "hashed-Secure-Password-123!"
    )
    assert "Bootstrap completed successfully." in output
    assert "Secure-Password-123!" not in output


def test_bootstrap_admin_rejects_short_password(monkeypatch, capsys):
    inputs = iter(
        [
            "Test Organization",
            "test-organization",
            "admin@example.test",
            "Test Admin",
        ]
    )
    passwords = iter(
        [
            "short",
            "Secure-Password-123!",
            "Secure-Password-123!",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda prompt="": next(inputs),
    )
    monkeypatch.setattr(
        bootstrap_admin.getpass,
        "getpass",
        lambda prompt="": next(passwords),
    )

    captured = {}

    def fake_create_organization_with_admin(**kwargs):
        captured.update(kwargs)
        return {
            "organization_name": kwargs["organization_name"],
            "organization_slug": kwargs["organization_slug"],
            "email": kwargs["email"],
            "user_id": 10,
            "organization_id": 20,
        }

    monkeypatch.setattr(
        bootstrap_admin.AuthService,
        "create_organization_with_admin",
        fake_create_organization_with_admin,
    )
    monkeypatch.setattr(
        bootstrap_admin,
        "hash_password",
        lambda password: f"hashed-{password}",
    )

    result = bootstrap_admin.main()

    output = capsys.readouterr().out

    assert result == 0
    assert "at least 12 characters" in output
    assert captured["password_hash"] == (
        "hashed-Secure-Password-123!"
    )


def test_bootstrap_admin_handles_creation_failure(
    monkeypatch,
    capsys,
):
    inputs = iter(
        [
            "Test Organization",
            "test-organization",
            "admin@example.test",
            "Test Admin",
        ]
    )
    passwords = iter(
        [
            "Secure-Password-123!",
            "Secure-Password-123!",
        ]
    )

    monkeypatch.setattr(
        "builtins.input",
        lambda prompt="": next(inputs),
    )
    monkeypatch.setattr(
        bootstrap_admin.getpass,
        "getpass",
        lambda prompt="": next(passwords),
    )
    monkeypatch.setattr(
        bootstrap_admin,
        "hash_password",
        lambda password: "hashed-password",
    )
    monkeypatch.setattr(
        bootstrap_admin.AuthService,
        "create_organization_with_admin",
        lambda **kwargs: (_ for _ in ()).throw(
            RuntimeError("Database failure")
        ),
    )

    result = bootstrap_admin.main()

    output = capsys.readouterr().out

    assert result == 1
    assert "Bootstrap failed" in output
    assert "Database failure" not in output
