
from pathlib import Path

import pytest

from hazina_pipeline.database.migrations.manager import (
    MigrationError,
    calculate_checksum,
    discover_migrations,
    remove_transaction_wrappers,
)


def write_migration(
    directory: Path,
    filename: str,
    content: str = "SELECT 1;",
) -> Path:
    path = directory / filename
    path.write_text(content, encoding="utf-8")
    return path


def test_discover_migrations_returns_files_in_version_order(
    tmp_path: Path,
):
    write_migration(tmp_path, "02_second.sql")
    write_migration(tmp_path, "01_first.sql")
    write_migration(tmp_path, "03_third.sql")

    migrations = discover_migrations(tmp_path)

    assert [migration.version for migration in migrations] == [
        1,
        2,
        3,
    ]
    assert [migration.filename for migration in migrations] == [
        "01_first.sql",
        "02_second.sql",
        "03_third.sql",
    ]


def test_discover_migrations_accepts_existing_filename_with_space(
    tmp_path: Path,
):
    write_migration(tmp_path, "01_first.sql")
    write_migration(
        tmp_path,
        "02_create daily_transaction_summary.sql",
    )

    migrations = discover_migrations(tmp_path)

    assert len(migrations) == 2
    assert migrations[1].filename == (
        "02_create daily_transaction_summary.sql"
    )


def test_discover_migrations_ignores_non_sql_files(
    tmp_path: Path,
):
    write_migration(tmp_path, "01_first.sql")
    (tmp_path / ".gitkeep").write_text("", encoding="utf-8")
    (tmp_path / "notes.txt").write_text(
        "Not a migration",
        encoding="utf-8",
    )

    migrations = discover_migrations(tmp_path)

    assert len(migrations) == 1
    assert migrations[0].filename == "01_first.sql"


def test_discover_migrations_rejects_missing_directory(
    tmp_path: Path,
):
    missing_directory = tmp_path / "missing"

    with pytest.raises(
        MigrationError,
        match="does not exist",
    ):
        discover_migrations(missing_directory)


def test_discover_migrations_rejects_empty_directory(
    tmp_path: Path,
):
    with pytest.raises(
        MigrationError,
        match="No SQL migration files found",
    ):
        discover_migrations(tmp_path)


def test_discover_migrations_rejects_invalid_sql_filename(
    tmp_path: Path,
):
    write_migration(tmp_path, "first_migration.sql")

    with pytest.raises(
        MigrationError,
        match="invalid filename",
    ):
        discover_migrations(tmp_path)


def test_discover_migrations_rejects_duplicate_versions(
    tmp_path: Path,
):
    write_migration(tmp_path, "01_first.sql")
    write_migration(tmp_path, "01_duplicate.sql")

    with pytest.raises(
        MigrationError,
        match="Duplicate migration version",
    ):
        discover_migrations(tmp_path)


def test_discover_migrations_rejects_version_gaps(
    tmp_path: Path,
):
    write_migration(tmp_path, "01_first.sql")
    write_migration(tmp_path, "03_third.sql")

    with pytest.raises(
        MigrationError,
        match="must be consecutive",
    ):
        discover_migrations(tmp_path)


def test_discover_migrations_calculates_checksum(
    tmp_path: Path,
):
    content = "CREATE TABLE example (id INTEGER);"
    write_migration(tmp_path, "01_first.sql", content)

    migrations = discover_migrations(tmp_path)

    assert migrations[0].checksum == calculate_checksum(content)


def test_checksum_changes_when_migration_content_changes():
    original = "SELECT 1;"
    modified = "SELECT 2;"

    assert calculate_checksum(original) != calculate_checksum(
        modified
    )


def test_remove_transaction_wrappers_removes_standalone_boundaries():
    sql = """-- Existing migration
BEGIN;

CREATE TABLE example (
    id INTEGER PRIMARY KEY
);

COMMIT;
"""

    cleaned = remove_transaction_wrappers(sql)

    assert "BEGIN;" not in cleaned
    assert "COMMIT;" not in cleaned
    assert "CREATE TABLE example" in cleaned


def test_remove_transaction_wrappers_preserves_other_sql():
    sql = """-- BEGIN;
SELECT 'BEGIN;';
SELECT 'COMMIT;';
"""

    cleaned = remove_transaction_wrappers(sql)

    assert "-- BEGIN;" in cleaned
    assert "SELECT 'BEGIN;';" in cleaned
    assert "SELECT 'COMMIT;';" in cleaned
