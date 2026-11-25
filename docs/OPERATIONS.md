# Hazina Operations Guide

This guide covers the day-to-day operation of the Hazina Financial Transactions Pipeline in a local development environment.

It assumes that the repository has already been installed and configured using [INSTALLATION.md](INSTALLATION.md), and that the database has been initialized using [DATABASE.md](DATABASE.md).

## 1. Development Environment

Hazina runs as three main components:

| Component | Technology | Local address |
|---|---|---|
| Database | PostgreSQL | `localhost:5432` |
| Backend | FastAPI / Uvicorn | `http://127.0.0.1:8000` |
| Frontend | React / Vite | `http://localhost:5173` |

The Python virtual environment is located at the repository root:

```text
.venv/
```

The backend and pipeline packages are installed into this shared environment.

## 2. Start the Application

Start PostgreSQL first and confirm that the configured database is accessible.

### 2.1 Start the backend

Open a PowerShell terminal at the repository root:

```powershell
cd .\hazina_server
```

Start the API:

```powershell
..\.venv\Scripts\python.exe -m uvicorn server.main:app --reload
```

The backend is available at:

```text
http://127.0.0.1:8000
```

The `--reload` option automatically restarts the development server when backend source files change.

Keep this terminal running.

### 2.2 Start the frontend

Open a second PowerShell terminal at the repository root:

-> You can choose to deactivate the venv here
```powershell
cd .\hazina_frontend
```

Start the development server:

```powershell
npm run dev
```

The frontend is available at:

```text
http://localhost:5173
```

Keep this terminal running.

### 2.3 Access Hazina

Open the application in a browser:

```text
http://localhost:5173
```

Sign in using an administrator or other provisioned organization account.

## 3. Stop the Application

To stop either development server, select its terminal and press:

```text
Ctrl + C
```

Stop the backend and frontend independently.

PostgreSQL can remain running if other local applications depend on it. Otherwise, stop the PostgreSQL service using the Windows Services application or the PostgreSQL service-management method configured on the machine.

## 4. Check Application Health

### 4.1 Backend health

Open:

```text
http://127.0.0.1:8000/health
```

This endpoint checks application health.

### 4.2 Database health

Open:

```text
http://127.0.0.1:8000/health/database
```

This endpoint checks database connectivity.

### 4.3 Interactive API documentation

Open:

```text
http://127.0.0.1:8000/docs
```

FastAPI provides interactive API documentation through Swagger UI.

The API documentation can be used to inspect available endpoints, request schemas, and responses.

## 5. Database Operations

Database creation, permissions, migration history, and migration procedures are documented in [DATABASE.md](DATABASE.md).

### 5.1 Check migration status

From the repository root, run:

```powershell
python -m hazina_pipeline.database.migrations
```

The migration manager checks the available SQL migration files against the database migration history.

If all migrations have been applied, it reports that there are no pending migrations.

### 5.2 Apply pending migrations

Use the same command:

```powershell
python -m hazina_pipeline.database.migrations
```

Pending migrations are applied in version order.

Do not edit migrations that have already been applied. Introduce a new numbered migration for subsequent schema changes.

### 5.3 Migration safety

The migration manager maintains migration history and checksums in:

```text
ops.schema_migrations
```

It detects changes to previously applied migration files and prevents an inconsistent migration history from being silently accepted.

Review migration output before continuing with application operations.

## 6. Run Automated Tests

Run tests from the repository root.

### 6.1 Pipeline tests

```powershell
python -m pytest .\hazina_pipeline\tests
```

### 6.2 Backend tests

```powershell
python -m pytest .\hazina_server\tests
```

### 6.3 Frontend type checking

```powershell
cd .\hazina_frontend
npx tsc --noEmit
```

### 6.4 Frontend production build

```powershell
npm run build
```

The production build is generated in:

```text
hazina_frontend/dist/
```

Return to the repository root when finished:

```powershell
cd ..
```

Run the relevant tests after making changes to the corresponding component.

## 7. Pipeline Operations

Hazina processes financial transaction files through the backend API and pipeline orchestration layer.

The normal workflow is:

1. An authorized user signs in.
2. The user selects a supported financial data source.
3. The user selects the appropriate mapping.
4. The user uploads one or more source files.
5. The backend submits the files to the pipeline.
6. The pipeline ingests, maps, validates, and deduplicates transactions.
7. Eligible transactions are promoted into the core transaction tables.
8. The pipeline records execution results and final run status.
9. The user reviews the run in Pipeline Runs and accesses its report where available.

### 7.1 Review pipeline runs

Use the frontend Pipeline Runs page to:

- View submitted pipeline runs.
- Filter runs by status.
- Filter runs by source.
- Navigate through paginated results.
- Open individual run details.
- Review source execution results and file names.

The backend applies organization-level filtering to pipeline run access.

### 7.2 Understand pipeline statuses

The main pipeline run statuses are:

| Status | Meaning |
|---|---|
| `SUCCESS` | All applicable processing completed successfully |
| `PARTIAL_SUCCESS` | Some source executions succeeded while others had issues |
| `FAILED` | The pipeline run failed |
| `RUNNING` | Processing is still in progress |
| `CANCELLED` | The run was cancelled |

Review individual source execution results when a run has a partial-success or failed status.

### 7.3 Review reports

Pipeline reports provide a summary of the processing results.

Reports are available through the pipeline run details and report endpoint when generated successfully.

Protected PDF reports require the configured PDF open password.

## 8. User and Organization Operations

Hazina uses organization-based access control.

The main roles are:

| Role | Responsibilities |
|---|---|
| `ADMIN` | Organization administration, user management, and full application access |
| `OPERATOR` | Submit pipeline files and view pipeline results |
| `VIEWER` | Read-only access to permitted application data |

Administrators can manage organization users through the User Management page.

Typical administration operations include:

- Adding organization users.
- Assigning user roles.
- Changing user roles.
- Activating or deactivating user accounts.

Users should only be granted the permissions required for their responsibilities.

Organization-level data isolation is enforced by the backend.

## 9. Frontend Production Build

To generate a production build:

```powershell
cd .\hazina_frontend
npm run build
```

The output is written to:

```text
dist/
```

The generated files can be deployed to a suitable static hosting environment.

The Vite development server is for local development and should not be used as the production hosting solution.

Production deployment also requires a properly configured backend, database, environment variables, HTTPS, and suitable infrastructure.

## 10. Troubleshooting

### 10.1 Backend does not start

Check that:

- The root virtual environment exists.
- Both Python packages are installed.
- The root `.env` file exists and has the required configuration.
- PostgreSQL is running.
- Port 8000 is not already occupied.
- The backend is started from the `hazina_server` directory.

Use the established startup command:

```powershell
cd .\hazina_server
..\.venv\Scripts\python.exe -m uvicorn server.main:app --reload
```

### 10.2 Frontend does not start

Check that:

- Node.js and npm are installed.
- Frontend dependencies have been installed using `npm ci`.
- The frontend `.env` contains the correct `VITE_API_BASE_URL`.
- Port 5173 is available.

If dependencies need to be restored:

```powershell
cd .\hazina_frontend
npm ci
npm run dev
```

### 10.3 Frontend cannot connect to the backend

Check that:

- The backend is running.
- The API is accessible at `http://127.0.0.1:8000`.
- `VITE_API_BASE_URL` points to the correct API address.
- The backend CORS configuration permits the frontend origin.

Restart the frontend after changing its environment configuration.

### 10.4 Database connectivity errors

Check that:

- PostgreSQL is running.
- The database exists.
- The database credentials in the root `.env` are correct.
- The application database role has the required permissions.
- The database schema migrations have been applied.

Use the database health endpoint to check connectivity.

### 10.5 Authentication failures

Check that:

- The user account exists and is active.
- The organization selection or slug is correct.
- The account has the appropriate organization membership and role.
- The root `.env` contains the correct JWT configuration.

Restart the backend after changing authentication environment variables.

### 10.6 Pipeline run failures

Open the affected pipeline run and inspect its source execution results.

Check:

- The uploaded file format is supported.
- The selected source is correct.
- The selected mapping ID and version are correct.
- The source file contains the expected headers and data.
- Validation errors and ingestion errors reported for the execution.

A partial-success run should be investigated at the individual source execution level.

### 10.7 Migration errors

If the migration manager reports a checksum mismatch, filename mismatch, or migration failure:

- Do not modify an already-applied migration.
- Do not manually mark a failed migration as applied.
- Inspect the migration history and database state.
- Resolve the underlying issue before retrying.

Refer to [DATABASE.md](DATABASE.md) for the migration procedures and safety rules.

## 11. Operational Recommendations

For reliable development and deployment:

- Keep database credentials and JWT secrets out of source control.
- Back up the database before significant schema changes.
- Test new migrations against a separate database before applying them to an important environment.
- Run the relevant automated tests after code changes.
- Use separate database environments for development and production.
- Grant users only the permissions required by their roles.
- Use HTTPS and secure secret management in production.
- Monitor backend logs and database health.
- Do not use the Vite development server as a production hosting service.

---

**End of operations guide.**