# Hazina Database Setup and Migrations

## 1. Overview

Hazina uses PostgreSQL as its primary database.

The database stores financial transactions, ingestion records, pipeline execution history, source configuration, validation results, audit records, analytics, and user and organization information.

Hazina includes a database migration manager that creates the required database schemas and applies SQL migrations in numerical order.

The migration manager supports:

- Initializing a fresh, empty database.
- Applying new migrations to an existing managed database.
- Registering an existing, previously migrated database without re-executing its SQL.
- Detecting modifications to migrations that have already been applied.
- Rolling back a failed migration and its migration-history record.

**Important:** The migration manager does not install PostgreSQL or create the PostgreSQL database itself. Those steps must be completed before running migrations.

## 2. PostgreSQL prerequisites

Install and start a supported PostgreSQL server.

You will need:

- PostgreSQL running and accessible.
- A database dedicated to Hazina.
- A PostgreSQL role for the Hazina application.
- Permission for that role to connect to the database and create schemas.

Create the database using a PostgreSQL administrator account.

For example:

```sql
CREATE DATABASE hazina_warehouse;
```

Grant the application role the required database permissions:

```sql
GRANT CONNECT, CREATE, TEMPORARY
ON DATABASE hazina_warehouse
TO hazina;
```

Replace the database and role names with the values appropriate for your environment.

The application role must also have the necessary privileges on the database objects it accesses.

## 3. Database environment configuration

Hazina loads its database configuration from the repository-root `.env` file.

Configure the following variables:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hazina_warehouse
DB_USER=hazina
DB_PASSWORD=your_database_password
```

Use the actual connection details for your PostgreSQL installation.

Keep `.env` private. Do not commit database credentials to source control or include real passwords in documentation, screenshots, logs, or support requests.

## 4. Initializing a fresh database

Use this procedure when installing Hazina into a newly created, empty database.

### Step 1: Install the Python packages

From the repository root, install the pipeline package and its dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .\hazina_pipeline
```

If you are following the development installation instructions, install the development dependencies as well:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\hazina_pipeline\requirements-dev.txt
```

### Step 2: Configure the database

Make sure the repository-root `.env` contains the correct PostgreSQL connection variables.

Confirm that the database exists and that the configured application role can connect and create schemas.

### Step 3: Run the migration manager

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m hazina_pipeline.database.migrations
```

The migration manager:

1. Acquires a PostgreSQL advisory lock to prevent concurrent migration processes.
2. Creates the foundational schemas if they do not exist.
3. Creates the migration-history table.
4. Discovers and validates the numbered SQL migration files.
5. Applies pending migrations in numerical order.
6. Records each successful migration and its checksum.

The current migration sequence contains 29 migrations.

A successful fresh installation should report:

```text
Applied during this run: 29
Already applied: 0

Database migrations completed successfully.
```

The exact output may change as new migrations are added.

**Do not manually execute the numbered SQL files when using the migration manager.** It is responsible for executing them and recording their history.

## 5. Existing database adoption

Use this procedure only when an existing Hazina database has already had all the migrations represented by the current migration files successfully executed in numerical order, but does not yet have a migration-history table.

This is relevant when bringing an older, manually maintained Hazina database under migration management.

### Important precautions

Before adopting an existing database:

- Back up the database.
- Confirm that all migrations being registered were previously executed successfully and in order.
- Verify that the existing database has the expected Hazina schema and tables.
- Do not use this option on a fresh database.
- Do not use it to bypass missing or failed migrations.

The baseline operation checks for the required Hazina tables and refuses adoption if they are missing.

### Run baseline adoption

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m hazina_pipeline.database.migrations --baseline-existing
```

The manager registers the discovered migration versions, filenames, and checksums in `ops.schema_migrations`.

It does not execute the migration SQL or recreate existing application tables.

A successful adoption reports:

```text
Existing database successfully adopted.
...
Total baseline entries: 29
No migration SQL was executed.
```

The `applied_at` value represents the time the baseline was registered, not necessarily the historical date when the original SQL was executed. Baseline entries have an execution time of zero.

**Baseline adoption is an explicit administrative operation.** It is not a substitute for applying migrations that have not actually been executed.

The manager refuses baseline adoption if migration history already exists.

## 6. Applying future migrations

Once a database is managed by the migration manager, use the normal command whenever a new migration is introduced:

```powershell
.\.venv\Scripts\python.exe -m hazina_pipeline.database.migrations
```

The manager compares the available migration files with the recorded migration history.

It applies only migrations that have not yet been recorded as successfully applied.

For example, if the database already has migrations 1–29 and a new migration 30 is introduced, the manager applies migration 30 without re-executing migrations 1–29.

### Migration file naming

Migration files are stored in:

```text
hazina_pipeline/sql/
```

Use numbered filenames with an underscore after the version:

```text
01_create_tables.sql
02_update_raw_table.sql
...
29_add_financial_data_organization_isolation.sql
30_example_new_change.sql
```

Migration versions must be:

- Numeric.
- Unique.
- Consecutive, starting at 1.
- Followed by an underscore in the filename.

The manager rejects duplicate versions, invalid SQL filenames, and gaps in the migration sequence.

## 7. Migration history

The migration manager maintains its history in:

```text
ops.schema_migrations
```

The table records:

| Column | Description |
|---|---|
| `version` | Numeric migration version |
| `filename` | Applied migration filename |
| `checksum` | SHA-256 checksum of the migration file |
| `applied_at` | Timestamp when the migration was registered or applied |
| `execution_time_ms` | Migration execution time in milliseconds |

The migration-history table is managed by the migration manager and is not one of the numbered SQL migration files.

### Checksum protection

The manager calculates a SHA-256 checksum for each migration file.

When a migration has already been applied, its current checksum is compared with the checksum recorded in the database.

If the contents have changed, the manager stops and reports an error.

**Never edit an already-applied migration to introduce a database change.**

Instead, create a new migration with the next available version.

This preserves migration history and makes database upgrades reproducible.

## 8. Transaction safety and concurrency

Each migration is executed in its own database transaction.

The migration SQL and its corresponding history entry are committed together.

If a migration fails:

- Its transaction is rolled back.
- Changes made by that migration are not committed.
- Its migration-history entry is not recorded.
- The manager reports the failure and stops processing further migrations.

The manager also uses a PostgreSQL advisory lock to prevent multiple migration processes from running concurrently.

Existing SQL migration files may contain standalone transaction-boundary statements. The manager removes those boundaries before execution so that it controls the transaction surrounding each migration.

## 9. Troubleshooting

### Database does not exist

Confirm that the database was created on the PostgreSQL server specified in `.env`.

Check `DB_HOST`, `DB_PORT`, and `DB_NAME`.

### Permission denied when creating schemas

The configured PostgreSQL role needs permission to create schemas in the target database.

An administrator can grant the required database permissions:

```sql
GRANT CONNECT, CREATE, TEMPORARY
ON DATABASE hazina_warehouse
TO hazina;
```

### Existing database has no migration history

The manager deliberately refuses to automatically migrate a database that already contains Hazina application tables but has no migration history.

Verify the existing schema and migration execution history first. If all current migrations have already been executed successfully, use the explicit baseline-adoption procedure.

Do not baseline an incomplete or partially migrated database.

### Migration has been modified after application

Restore the original migration file or create a new migration containing the required change.

Do not change the stored checksum manually to bypass the protection.

### Migration failed

Read the reported migration version and database error.

The failed migration's transaction is rolled back. Resolve the underlying problem, then rerun the migration manager.

Do not manually insert a migration-history record for a failed migration.

### No pending migrations

A message indicating that there are no pending migrations means that all migration files currently available in the codebase have matching entries in the database migration history.

## 10. Backup and production recommendations

Before applying database migrations in a production environment:

1. Take a verified database backup.
2. Review the new SQL migration.
3. Test the migration against a separate database with a representative schema.
4. Confirm that the application role has the required permissions.
5. Apply migrations as a controlled deployment step.
6. Verify the migration history and application health after deployment.

Do not run the migration manager automatically from every API server worker during application startup. Run it explicitly as part of the database setup or deployment process.

Protect the database credentials and migration permissions. Use an appropriately restricted application role for normal application operation.

---

## 11. Migration manager commands reference

Run these commands from the repository root using the configured Python virtual environment.

| Purpose | Command |
|---|---|
| Apply pending migrations | `python -m hazina_pipeline.database.migrations` |
| Adopt an existing migrated database | `python -m hazina_pipeline.database.migrations --baseline-existing` |
| Display available options | `python -m hazina_pipeline.database.migrations --help` |

The commands above assume the Hazina pipeline package has been installed in the active Python environment.

For Windows PowerShell, the repository virtual-environment executable can be used directly:

```powershell
.\.venv\Scripts\python.exe -m hazina_pipeline.database.migrations
```

For installation prerequisites and the full application startup procedure, see [INSTALLATION.md](INSTALLATION.md).