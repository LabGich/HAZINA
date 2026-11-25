
from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from hazina_pipeline.database.connection import get_database_connection


DEFAULT_MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "sql"

MIGRATION_LOCK_ID = 724_202_611

FOUNDATIONAL_SCHEMAS = (
    "raw",
    "staging",
    "core",
    "ops",
    "analytics",
)

# These tables must already exist before an existing database can
# be adopted into migration management.
BASELINE_REQUIRED_TABLES = {
    ("auth", "organization_memberships"),
    ("auth", "organizations"),
    ("auth", "refresh_tokens"),
    ("auth", "roles"),
    ("auth", "users"),
    ("core", "transactions"),
    ("ops", "ingestion_checkpoints"),
    ("ops", "mapping_errors"),
    ("ops", "pipeline_errors"),
    ("ops", "pipeline_runs"),
    ("ops", "source_executions"),
    ("ops", "source_registry"),
    ("ops", "source_transaction_identity"),
    ("ops", "transaction_audit"),
    ("ops", "validation_errors"),
    ("raw", "transactions"),
    ("staging", "transactions"),
}

MIGRATION_FILENAME_PATTERN = re.compile(
    r"^(\d+)_.*\.sql$",
    re.IGNORECASE,
)

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

    The migration manager owns the transaction surrounding each
    migration, so existing SQL files do not need to be modified.
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


def validate_baseline_schema(
    existing_tables: set[tuple[str, str]],
) -> None:
    """Ensure the existing database has the expected Hazina tables."""
    missing_tables = sorted(
        BASELINE_REQUIRED_TABLES - existing_tables
    )

    if missing_tables:
        formatted = ", ".join(
            f"{schema}.{table}"
            for schema, table in missing_tables
        )
        raise MigrationError(
            "The database does not contain all required Hazina tables. "
            "Baseline adoption has been stopped. Missing: "
            f"{formatted}"
        )


def _prepare_database(connection) -> None:
    """
    Prepare a fresh database for normal migrations.

    Existing application tables without migration history are rejected.
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

            for table_name in (
                "raw.transactions",
                "staging.transactions",
                "core.transactions",
                "ops.pipeline_runs",
                "auth.users",
            ):
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
                    "Use the explicit baseline adoption process after "
                    "verifying the existing schema. Detected tables: "
                    f"{', '.join(existing_tables)}"
                )

    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ops.schema_migrations (
                    version INTEGER PRIMARY KEY,
                    filename TEXT NOT NULL UNIQUE,
                    checksum CHAR(64) NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
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


def _acquire_migration_lock(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_lock(%s)",
            (MIGRATION_LOCK_ID,),
        )


def _release_migration_lock(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_unlock(%s)",
            (MIGRATION_LOCK_ID,),
        )


def baseline_existing_database(
    connection_factory: Callable = get_database_connection,
    migrations_dir: Path = DEFAULT_MIGRATIONS_DIR,
) -> tuple[str, ...]:
    """
    Adopt an existing Hazina database without executing migration SQL.

    This operation:
    - Requires all expected existing Hazina tables.
    - Refuses to run if migration history already exists.
    - Records the current migration filenames and checksums.
    - Does not modify existing application tables or financial data.

    The caller must independently confirm that all migrations represented
    by this baseline were previously executed successfully and in order.
    """
    migrations = discover_migrations(migrations_dir)
    connection = connection_factory()
    lock_acquired = False

    try:
        connection.autocommit = True

        _acquire_migration_lock(connection)
        lock_acquired = True

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'ops'
                      AND table_name = 'schema_migrations'
                      AND table_type = 'BASE TABLE'
                )
                """
            )
            if cursor.fetchone()[0]:
                raise MigrationError(
                    "Migration history already exists. "
                    "Baseline adoption is only permitted for a database "
                    "that has not yet been registered."
                )

            cursor.execute(
                """
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema IN (
                    'raw', 'staging', 'core', 'ops', 'auth'
                )
                  AND table_type = 'BASE TABLE'
                """
            )
            existing_tables = {
                (row[0], row[1])
                for row in cursor.fetchall()
            }

        validate_baseline_schema(existing_tables)

        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE ops.schema_migrations (
                        version INTEGER PRIMARY KEY,
                        filename TEXT NOT NULL UNIQUE,
                        checksum CHAR(64) NOT NULL,
                        applied_at TIMESTAMPTZ NOT NULL
                            DEFAULT CURRENT_TIMESTAMP,
                        execution_time_ms INTEGER NOT NULL
                            CHECK (execution_time_ms >= 0)
                    )
                    """
                )

                for migration in migrations:
                    cursor.execute(
                        """
                        INSERT INTO ops.schema_migrations (
                            version,
                            filename,
                            checksum,
                            execution_time_ms
                        )
                        VALUES (%s, %s, %s, 0)
                        """,
                        (
                            migration.version,
                            migration.filename,
                            migration.checksum,
                        ),
                    )

        return tuple(
            migration.filename for migration in migrations
        )

    finally:
        try:
            if lock_acquired:
                _release_migration_lock(connection)
        finally:
            connection.close()


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
        connection.autocommit = True

        _acquire_migration_lock(connection)
        lock_acquired = True

        _prepare_database(connection)
        applied_history = _get_applied_migrations(connection)

        available_versions = {
            migration.version for migration in migrations
        }

        unknown_versions = set(applied_history) - available_versions
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
        try:
            if lock_acquired:
                _release_migration_lock(connection)
        finally:
            connection.close()

    return MigrationSummary(
        applied=tuple(applied_names),
        already_applied=tuple(already_applied_names),
    )
