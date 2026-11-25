
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from hazina_pipeline.database.connection import get_database_connection


# manager.py:
# hazina_pipeline/hazina_pipeline/database/migrations/manager.py
# SQL files:
# hazina_pipeline/sql/
DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "sql"

# A fixed, application-specific PostgreSQL advisory lock.
MIGRATION_LOCK_ID = 724_202_611

FOUNDATIONAL_SCHEMAS = (
    "raw",
    "staging",
    "core",
    "ops",
    "analytics",
)

LEGACY_TABLES = (
    "raw.transactions",
    "staging.transactions",
    "core.transactions",
    "ops.pipeline_runs",
    "auth.users",
)

MIGRATION_FILENAME_PATTERN = re.compile(r"^(\d+)_.*\.sql$", re.IGNORECASE)

TRANSACTION_BOUNDARY_PATTERN = re.compile(
    r"(?im)^\s*(?:BEGIN|COMMIT)\s*;\s*(?:--[^\n]*)?$"
)


class MigrationError(RuntimeError):
    """Raised when database migrations cannot safely proceed."""


@dataclass(frozen=True)
class Migration:
    version: int
    filename: str
    path: Path
    checksum: str


@dataclass(frozen=True)
class MigrationSummary:
    applied: tuple[str, ...]
    already_applied: tuple[str, ...]

    @property
    def applied_count(self) -> int:
        return len(self.applied)


def calculate_checksum(content: str) -> str:
    """Return the SHA-256 checksum of a migration's exact contents."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def remove_transaction_wrappers(sql: str) -> str:
    """
    Remove standalone BEGIN and COMMIT statements.

    The migration manager owns the transaction surrounding each migration,
    so existing SQL files do not need to be modified.
    """
    return TRANSACTION_BOUNDARY_PATTERN.sub("", sql)


def discover_migrations(
    migrations_dir: Path = DEFAULT_MIGRATIONS_DIR,
) -> list[Migration]:
    """Find and validate numbered SQL migration files."""
    if not migrations_dir.is_dir():
        raise MigrationError(
            f"Migration directory does not exist: {migrations_dir}"
        )

    migrations: list[Migration] = []

    for path in migrations_dir.iterdir():
        if not path.is_file() or path.suffix.lower() != ".sql":
            continue

        match = MIGRATION_FILENAME_PATTERN.match(path.name)
        if not match:
            raise MigrationError(
                f"SQL migration has an invalid filename: {path.name}. "
                "Expected a filename beginning with a numeric version "
                "followed by an underscore."
            )

        version = int(match.group(1))
        content = path.read_text(encoding="utf-8")

        migrations.append(
            Migration(
                version=version,
                filename=path.name,
                path=path,
                checksum=calculate_checksum(content),
            )
        )

    migrations.sort(key=lambda migration: migration.version)

    if not migrations:
        raise MigrationError(
            f"No SQL migration files found in {migrations_dir}"
        )

    versions = [migration.version for migration in migrations]

    if len(versions) != len(set(versions)):
        raise MigrationError("Duplicate migration version numbers found.")

    expected_versions = list(range(1, len(versions) + 1))
    if versions != expected_versions:
        raise MigrationError(
            "Migration versions must be consecutive, starting at 1. "
            f"Found: {versions}"
        )

    return migrations


def _prepare_database(connection) -> None:
    """
    Create foundational schemas and the migration history table.

    Existing databases without migration history are deliberately rejected
    when application tables are already present. They need a separately
    verified baseline before automatic migrations can safely manage them.
    """
    with connection.transaction():
        with connection.cursor() as cursor:
            for schema in FOUNDATIONAL_SCHEMAS:
                cursor.execute(
                    f'CREATE SCHEMA IF NOT EXISTS "{schema}"'
                )

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT to_regclass('ops.schema_migrations')"
        )
        history_exists = cursor.fetchone()[0] is not None

        if not history_exists:
            existing_tables = []

            for table_name in LEGACY_TABLES:
                cursor.execute(
                    "SELECT to_regclass(%s)",
                    (table_name,),
                )
                if cursor.fetchone()[0] is not None:
                    existing_tables.append(table_name)

            if existing_tables:
                raise MigrationError(
                    "This database already contains Hazina application "
                    "tables but has no migration history. Automatic "
                    "migration has stopped to protect existing data. "
                    "A verified baseline is required before proceeding. "
                    f"Detected tables: {', '.join(existing_tables)}"
                )

    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ops.schema_migrations (
                    version INTEGER PRIMARY KEY,
                    filename TEXT NOT NULL UNIQUE,
                    checksum CHAR(64) NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    execution_time_ms INTEGER NOT NULL
                        CHECK (execution_time_ms >= 0)
                )
                """
            )


def _get_applied_migrations(connection) -> dict[int, dict[str, str]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT version, filename, checksum
            FROM ops.schema_migrations
            ORDER BY version
            """
        )
        rows = cursor.fetchall()

    return {
        row[0]: {
            "filename": row[1],
            "checksum": row[2].strip(),
        }
        for row in rows
    }


def run_migrations(
    connection_factory: Callable = get_database_connection,
    migrations_dir: Path = DEFAULT_MIGRATIONS_DIR,
) -> MigrationSummary:
    """
    Apply pending database migrations in order.

    Each migration and its history record are committed atomically.
    A PostgreSQL advisory lock prevents concurrent migration processes.
    """
    migrations = discover_migrations(migrations_dir)
    connection = connection_factory()

    applied_names: list[str] = []
    already_applied_names: list[str] = []
    lock_acquired = False

    try:
        # Advisory locks and explicit transaction contexts work together
        # cleanly when the connection is in autocommit mode.
        connection.autocommit = True

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_lock(%s)",
                (MIGRATION_LOCK_ID,),
            )
            lock_acquired = True

        _prepare_database(connection)
        applied_history = _get_applied_migrations(connection)

        available_versions = {
            migration.version for migration in migrations
        }

        unknown_versions = (
            set(applied_history) - available_versions
        )
        if unknown_versions:
            raise MigrationError(
                "The database contains migration history entries that "
                "are not present in this codebase: "
                f"{sorted(unknown_versions)}"
            )

        for migration in migrations:
            existing = applied_history.get(migration.version)

            if existing:
                if existing["filename"] != migration.filename:
                    raise MigrationError(
                        f"Migration {migration.version} has a filename "
                        "that differs from the applied migration. "
                        f"Database: {existing['filename']}; "
                        f"Code: {migration.filename}"
                    )

                if existing["checksum"] != migration.checksum:
                    raise MigrationError(
                        f"Migration {migration.version} "
                        f"({migration.filename}) has been modified "
                        "after it was applied. Restore the original "
                        "migration file or create a new migration."
                    )

                already_applied_names.append(migration.filename)
                continue

            sql = migration.path.read_text(encoding="utf-8")
            sql = remove_transaction_wrappers(sql)

            started_at = time.perf_counter()

            try:
                with connection.transaction():
                    with connection.cursor() as cursor:
                        cursor.execute(sql)

                        execution_time_ms = int(
                            (time.perf_counter() - started_at) * 1000
                        )

                        cursor.execute(
                            """
                            INSERT INTO ops.schema_migrations (
                                version,
                                filename,
                                checksum,
                                execution_time_ms
                            )
                            VALUES (%s, %s, %s, %s)
                            """,
                            (
                                migration.version,
                                migration.filename,
                                migration.checksum,
                                execution_time_ms,
                            ),
                        )
            except Exception as exc:
                raise MigrationError(
                    f"Migration {migration.version} "
                    f"({migration.filename}) failed. "
                    "Its transaction was rolled back. "
                    f"Database error: {exc}"
                ) from exc

            applied_names.append(migration.filename)

    finally:
        if lock_acquired:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT pg_advisory_unlock(%s)",
                        (MIGRATION_LOCK_ID,),
                    )
            finally:
                connection.close()
        else:
            connection.close()

    return MigrationSummary(
        applied=tuple(applied_names),
        already_applied=tuple(already_applied_names),
    )
