# Hazina
# AI powered Financial Transactions Pipeline

**Hazina** is a multi-tenant financial data platform built around a configurable financial transaction ingestion and analytics pipeline.

Hazina V2 provides a shared, file-based processing framework for financial data from multiple providers. It combines source-specific mappings with common ingestion, validation, deduplication, persistence, monitoring and reporting components.

The application consists of three components:

- **Pipeline:** Python-based financial transaction processing.
- **API server:** FastAPI backend providing authentication, organization isolation and application services.
- **Frontend:** React and TypeScript web application.

V2 focuses on file-based ingestion. API integrations and other deferred capabilities are documented in the V3 roadmap.

---

## 1. Project objectives

Hazina is designed to:

- Ingest financial statements from multiple providers.
- Process multiple files in one pipeline run.
- Preserve original source records.
- Map provider-specific fields into a canonical transaction model.
- Validate transactions against technical and business rules.
- Record mapping and validation errors.
- Identify provider-ID-based duplicate and conflicting transactions.
- Promote eligible transactions into trusted core storage.
- Isolate individual file failures.
- Track pipeline and source execution metrics.
- Generate operational PDF reports.
- Provide authenticated, organization-scoped access to financial data.

## 2. Technology stack

| Component | Technologies |
|---|---|
| Pipeline | Python 3.11+, pandas, Psycopg 3, PyYAML |
| Database | PostgreSQL |
| API | FastAPI, Pydantic, Uvicorn |
| Authentication | JWT, PyJWT, Argon2 password hashing |
| Frontend | React 19, TypeScript, Vite |
| UI and charts | Tailwind CSS, Lucide, Recharts |
| File processing | pandas, openpyxl, PyArrow |
| PDF reports | ReportLab |
| Testing | pytest, HTTPX, TypeScript compiler |
| Version control | Git and GitHub |

The exact dependency versions are maintained in the component-specific dependency files.

## 3. Repository structure

Hazina is maintained as a monorepo.

```text
hazina_fin_trans_pipeline/
│
├── hazina_pipeline/
│   ├── config/
│   │   ├── sources/
│   │   └── mappings/
│   ├── data/
│   ├── logs/
│   ├── reports/
│   ├── sql/
│   ├── tests/
│   ├── hazina_pipeline/
│   │   ├── database/
│   │   ├── deduplication/
│   │   ├── ingestion/
│   │   ├── mapping/
│   │   ├── monitoring/
│   │   ├── orchestration/
│   │   └── validation/
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── requirements-dev.txt
│
├── hazina_server/
│   ├── data/
│   ├── server/
│   │   ├── auth/
│   │   ├── commands/
│   │   ├── routers/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── requirements-dev.txt
│
├── hazina_frontend/
│   ├── public/
│   ├── src/
│   ├── package.json
│   ├── package-lock.json
│   └── vite.config.ts
│
├── .env
├── .env.example
├── .gitignore
└── README.md
```

Generated files, uploaded data, local environments and secrets should not be committed.

## 4. System architecture

Hazina uses a shared processing architecture. Each provider has a source registration and mapping configuration, while common components perform the processing.

```text
                  WEB FRONTEND
                       |
                       v
                  FASTAPI SERVER
                       |
             Authentication and
             organization isolation
                       |
                       v
               PIPELINE SERVICE
                       |
                       v
             V2 PIPELINE ORCHESTRATOR
                       |
             One parent pipeline run
                       |
          +------------+------------+
          |            |            |
          v            v            v
        File 1       File 2       File 3
          |            |            |
          v            v            v
      Ingestion     Ingestion     Ingestion
          |            |            |
          +------------+------------+
                       |
                       v
                 RAW STORAGE
                       |
                       v
              SOURCE-SPECIFIC MAPPING
                       |
                       v
                   STAGING
                       |
                       v
                  VALIDATION
                       |
                       v
              DEDUPLICATION
                       |
                       v
               CORE PROMOTION
                       |
                       v
             EXECUTION FINALIZATION
                       |
                       v
               PARENT FINALIZATION
                       |
                       v
               MONITORING AND
                  REPORTING
```

Each submitted file receives an independent child source execution. Multiple files, including multiple files from the same source, can belong to one parent pipeline run.

An individual file failure does not automatically prevent its sibling files from being processed.

## 5. Pipeline processing lifecycle

The V2 pipeline follows this lifecycle:

1. Resolve the explicitly supplied source and mapping configuration.
2. Create a parent pipeline run.
3. Create child source executions for submitted files.
4. Start each source execution.
5. Read the submitted file.
6. Preserve original records in raw storage.
7. Map records into the canonical transaction model.
8. Record mapping errors.
9. Validate mapped transactions.
10. Record validation errors.
11. Deduplicate eligible transactions.
12. Promote eligible transactions into core storage.
13. Update execution metrics.
14. Finalize each child execution.
15. Finalize the parent run after all child executions reach terminal states.
16. Generate the PDF report.

Report generation takes place after pipeline finalization. A reporting failure does not change the outcome of an already finalized pipeline run.

### Execution levels

**Parent pipeline run**

One parent run represents one submission containing one or more files.

Stored in:

`ops.pipeline_runs`

**Child source execution**

Each submitted file receives its own execution record.

Stored in:

`ops.source_executions`

This structure supports independent processing, metrics, error tracking and failure isolation.

## 6. Database architecture

The application uses the PostgreSQL database:

`hazina_warehouse`

The database has five principal schemas:

| Schema | Responsibility |
|---|---|
| `raw` | Original provider records and ingestion metadata |
| `staging` | Mapped canonical transactions and validation state |
| `core` | Trusted promoted financial transactions |
| `analytics` | Analytical summaries and reporting views |
| `ops` | Pipeline execution, source configuration, errors and operational tracking |
| `auth` | Organizations, users, roles, memberships and refresh tokens |

The operational schema includes objects for:

- Pipeline runs.
- Source registry.
- Source executions.
- Pipeline errors.
- Mapping errors.
- Validation errors.
- Source transaction identity.
- Ingestion checkpoints.
- Transaction audit history.

The authentication schema manages organizations, users, roles and organization memberships.

### Database migrations

SQL migrations are maintained in:

`hazina_pipeline/sql/`

The migration history currently extends through migration **29**.

The migration sequence includes:

- Initial database tables and analytics structures.
- Raw, staging and core transaction extensions.
- Source registry and source execution tracking.
- Deduplication and transaction identity.
- Mapping and validation error tracking.
- Ingestion checkpoints and transaction auditing.
- Performance indexes.
- Authentication schema.
- Refresh token management.
- Organization-level pipeline and financial data isolation.

Migration files must be applied in their intended numerical order.

**Important:** Do not edit migrations that have already been applied to an existing database. Introduce subsequent schema changes through new migration files.

The project does not document an automatic migration runner as part of the V2 workflow. Database migration application should therefore be performed deliberately and verified against the target database.

## 7. Canonical transaction model

Different providers use different field names and transaction representations. Hazina maps these into a shared canonical transaction model.

Principal transaction fields include:

| Field | Description |
|---|---|
| `transaction_id` | Hazina transaction identifier |
| `source_name` | Financial provider or source |
| `source_transaction_id` | Provider transaction identifier, when available |
| `source_account_id` | Source account identifier |
| `customer_id` | Optional customer identifier |
| `transaction_date` | Transaction timestamp |
| `transaction_type` | Standardized transaction classification |
| `amount` | Transaction amount |
| `currency` | Currency code |
| `direction` | Debit, credit or unknown |
| `payment_method` | Standardized payment channel |
| `status` | Standardized transaction status |
| `description` | Transaction description |
| `counterparty` | Transaction counterparty |
| `fee_amount` | Transaction fee, when available |
| `account_balance` | Account balance, when available |

Provider identifiers remain distinct from Hazina-generated identifiers.

Original provider data is preserved in raw storage for traceability.

### Standardization principles

- Amounts are represented as positive values, with direction stored separately.
- Currency values use ISO 4217 codes.
- Transaction timestamps are normalized according to the pipeline's configured timestamp rules.
- Provider identifiers remain separate from Hazina identifiers.
- Original source information is preserved where available.

## 8. Supported sources and mappings

V2 supports the following configured file-based sources.

| Source | Supported formats | Mapping configurations |
|---|---|---|
| EQUITY | CSV, JSON | `equity_csv_v1`, `equity_json_v1` |
| KCB | CSV, JSON | `kcb_csv_v1`, `kcb_json_v1` |
| COOP | CSV, JSON | `coop_csv_v1`, `coop_json_v1` |
| NCBA | CSV, JSON | `ncba_csv_v1`, `ncba_json_v1` |
| EXPLORE_MY_DATA | CSV, XLSX, JSON, JSONL, Parquet | `explore_my_data_v1` |
| UTILLY | CSV, XLSX | `utilly_bank_csv_v1`, `utilly_bank_xlsx_v1` |

The mapping must match the submitted file format.

For example, Utilly CSV statements use `utilly_bank_csv_v1`, while Utilly XLSX statements use `utilly_bank_xlsx_v1`.

### MPESA status

The MPESA source registration is retained, but its file mapping is incomplete. It is not currently an enabled, usable source in the V2 frontend workflow.

A representative statement sample and validated mapping are required before enabling it.

### File readers

The shared reader framework supports:

- CSV.
- XLSX.
- JSON.
- JSON Lines.
- Parquet.

Source-specific adapters can handle genuinely different file-reading requirements without duplicating the common processing framework.

### Source selection

Automatic source detection is not implemented.

The caller must explicitly provide:

- `source_name`
- `file_path`
- `mapping_id`
- `mapping_version`

The source and mapping must correspond to registered configurations.

## 9. Source and mapping configuration

Source configuration and mapping files are maintained under:

- `hazina_pipeline/config/sources/`
- `hazina_pipeline/config/mappings/`

Mapping configurations define:

- Mapping identifier and version.
- Source field names.
- Canonical destination fields.
- Date formats and timezone handling.
- Amount and debit/credit handling.
- Default values.
- Required fields.
- Transformations.
- Derived transaction types.

The mapping engine supports direct field mapping, split debit and credit amounts, signed amount handling, defaults and field transformations.

Actual source values take precedence over configured defaults.

### Adding a new file-based source

The general onboarding process is:

1. Register the source.
2. Define supported file formats.
3. Create its mapping configuration.
4. Configure source fields and transformations.
5. Validate the mapping configuration.
6. Obtain representative source samples.
7. Test ingestion and mapping.
8. Verify validation, deduplication and core promotion.

New sources should reuse the shared readers and processing components wherever possible.

## 10. Validation

Mapped staging transactions are validated before deduplication and promotion.

Validation covers applicable requirements such as:

- Required canonical fields.
- Valid transaction timestamps.
- Valid transaction amounts.
- Supported transaction types.
- Valid currencies.
- Supported payment methods.
- Supported transaction statuses.
- Valid transaction direction.
- Required source information.

Staging records use validation states:

- `PENDING`
- `VALID`
- `INVALID`

Validation failures are recorded in:

`ops.validation_errors`

Invalid transactions are excluded from core promotion.

## 11. Deduplication and core promotion

V2 implements source-aware provider transaction identity.

The identity uses:

- Source.
- Provider transaction identifier.
- Source account identifier.

### Duplicate classifications

| Classification | Handling |
|---|---|
| UNIQUE | Eligible for core promotion |
| EXACT_DUPLICATE | Redundant identical transaction |
| CONFLICTING_DUPLICATE | Conflicting records sharing an identity; excluded from promotion |

The pipeline also checks whether an eligible transaction is already represented in core storage.

- Identical existing transactions are counted as already in core.
- Conflicting transactions are not allowed to overwrite existing core records.
- Newly promoted transactions are recorded in transaction audit history.

### Known limitation

Content-based transaction fingerprinting has not yet been implemented.

For sources without provider transaction identifiers, such as the current Equity and NCBA sample mappings, repeated submission of the same statement can result in transactions being promoted again.

Repeated uploads from these sources should therefore not be assumed to be safely deduplicated.

This enhancement is deferred to V3.

## 12. Execution statuses and metrics

### Source execution statuses

| Status | Meaning |
|---|---|
| PENDING | Created but not started |
| RUNNING | Processing in progress |
| SUCCESS | Completed without record-level errors |
| PARTIAL_SUCCESS | Completed with rejected or skipped records |
| FAILED | Fatal failure prevented completion |
| SKIPPED | Deliberately skipped |
| CANCELLED | Cancelled |

### Parent pipeline statuses

| Status | Meaning |
|---|---|
| PENDING | Pipeline run created |
| RUNNING | Child executions are being processed |
| SUCCESS | All child executions succeeded |
| PARTIAL_SUCCESS | At least one child completed, but another was partial, failed, skipped or cancelled |
| FAILED | No child execution completed successfully |
| CANCELLED | Overall pipeline run was cancelled |

### Metrics

Hazina tracks metrics at child execution level and aggregates them at parent run level.

| Metric | Meaning |
|---|---|
| `records_received` | Records returned by the file reader |
| `records_loaded` | Raw records successfully persisted |
| `records_mapped` | Successfully mapped records |
| `records_rejected` | Mapping and validation failures |
| `records_skipped` | Deliberately excluded records |
| `records_duplicated` | Duplicate and conflicting records |
| `records_unique_eligible` | Valid unique records eligible for core |
| `records_promoted` | Newly inserted core transactions |
| `records_already_in_core` | Identical transactions already in core |
| `records_updated` | Existing records actually updated, where applicable |

## 13. Monitoring and PDF reporting

Hazina provides operational reporting at parent run and source execution levels.

Reports include:

- Parent run details.
- Overall pipeline status.
- Aggregate processing metrics.
- Per-file execution details.
- Source and mapping information.
- Execution timestamps.
- Child execution statuses.
- Mapping errors.
- Validation errors.
- Fatal execution errors.
- Deduplication results.
- Core promotion metrics.

PDF reports are generated after parent pipeline finalization.

Report generation failure does not change an already finalized pipeline outcome.

### PDF security

V2 PDF reports require an open password.

The pipeline configuration uses:

```dotenv
HAZINA_PDF_USER_PASSWORD=your_report_open_password
HAZINA_PDF_OWNER_PASSWORD=your_report_owner_password
```

The user password opens the report. The owner password controls configured PDF permissions.

Use strong, distinct passwords. Never commit these values to version control or expose them in logs or source code.

PDF permission restrictions are advisory and should not be treated as absolute document security.

## 14. API server

The backend is implemented using FastAPI.

It provides the application services used by the frontend, including:

- Authentication.
- Session refresh and logout.
- User and organization management.
- Source and mapping information.
- Pipeline submission.
- Pipeline run listing and filtering.
- Pipeline run details.
- PDF report access.
- Dashboard summary information.
- Health checks.

### Authentication

Hazina uses JWT-based authentication.

The authentication system supports:

- Login.
- Access tokens.
- Refresh tokens.
- Refresh token rotation.
- Logout and token revocation.
- Current-user information.
- Password hashing using Argon2.

Access and refresh token lifetimes are configured by the backend. The current defaults are 15 minutes for access tokens and 7 days for refresh tokens.

### Roles and permissions

Hazina uses three application roles.

| Role | Capabilities |
|---|---|
| ADMIN | Organization administration, user management and full application access |
| OPERATOR | Submit files and view pipeline information |
| VIEWER | Read-only access to permitted application information |

Administrative operations are restricted to authorized administrators.

### Organization isolation

Hazina supports multiple organizations.

Pipeline runs and financial data are scoped to the authenticated user's organization. Users should not be able to access another organization's protected records through API requests.

Organization-level isolation is enforced in the backend and database design.

## 15. Frontend application

The frontend is implemented using React, TypeScript and Vite.

The main application pages include:

| Page | Purpose |
|---|---|
| Dashboard | Operational summary and recent pipeline activity |
| Ingestion | Submit one or more financial statement files |
| Pipeline Runs | Browse, filter and paginate pipeline runs |
| Pipeline Run Details | Inspect individual source executions and processing results |
| Mappings | View available source mappings |
| User Management | Administer organization users |
| Settings | View application and account settings |
| Login | Authenticate users |

The frontend communicates with the FastAPI backend through the configured API base URL.

The frontend environment variable is:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

## 16. Installation and configuration

### Prerequisites

- Python 3.11 or later.
- PostgreSQL.
- Node.js and npm compatible with the installed Vite version.
- Git.
- PowerShell or another terminal.

### Clone the repository

```powershell
git clone <repository-url>
cd hazina_fin_trans_pipeline
```

### Create and activate the Python environment

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Install pipeline dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -e .\hazina_pipeline
```

For pipeline development and testing:

```powershell
python -m pip install -r .\hazina_pipeline\requirements-dev.txt
```

### Install server dependencies

```powershell
python -m pip install -e .\hazina_server
```

For server development and testing:

```powershell
python -m pip install -r .\hazina_server\requirements-dev.txt
```

### Configure environment variables

Create a root-level `.env` file using the pipeline environment template as a starting point.

The pipeline template is:

`hazina_pipeline/.env.example`

Configure the PostgreSQL connection:

```dotenv
APP_NAME=Hazina
APP_ENV=development
APP_DEBUG=true

DB_HOST=localhost
DB_PORT=5432
DB_NAME=hazina_warehouse
DB_USER=your_database_user
DB_PASSWORD=your_database_password
```

Configure PDF report security:

```dotenv
HAZINA_PDF_USER_PASSWORD=your_report_open_password
HAZINA_PDF_OWNER_PASSWORD=your_report_owner_password
```

The frontend has its own environment file:

`hazina_frontend/.env`

Use `hazina_frontend/.env.example` as its template.

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

Additional authentication and production secrets must be configured according to the backend's actual settings. Never commit secrets or share them in source control.

## 17. Database setup

Create the PostgreSQL database:

```sql
CREATE DATABASE hazina_warehouse;
```

Create or configure the application database role and grant the permissions required by the migrations and application.

Apply the SQL migration files from:

`hazina_pipeline/sql/`

Apply them in numerical order, from the earliest migration through migration 29.

After applying the migrations:

1. Verify the expected schemas and tables.
2. Verify the application database role has the necessary permissions.
3. Confirm the backend can connect to the database.
4. Complete the initial organization and administrator setup using the application's supported administrative/bootstrap workflow.

Do not use production credentials in development or commit database passwords.

## 18. Running the application

Hazina has three independently managed components.

### Pipeline

The pipeline package contains the V2 processing implementation and can be exercised through its application services and tests.

The caller must supply the source, file path, mapping identifier and mapping version. Automatic source detection is not implemented.

A file configuration follows this general structure:

```python
file_config = {
    "source_name": "EQUITY",
    "file_path": "path/to/equity_statement.csv",
    "mapping_id": "equity_csv_v1",
    "mapping_version": "1",
}
```

A pipeline run can contain multiple file configurations.

### API server

Run the FastAPI application using the server package's configured ASGI entry point.

The API should be available at:

`http://localhost:8000`

FastAPI interactive API documentation is normally available at:

`http://localhost:8000/docs`

Use the actual ASGI module configured in the server package when starting Uvicorn.

### Frontend

Open a separate PowerShell terminal:

```powershell
cd hazina_frontend
npm ci
npm run dev
```

Vite displays the local development URL, normally:

`http://localhost:5173`

Ensure the frontend API base URL points to the running backend.

### Production build

From `hazina_frontend`:

```powershell
npm run build
```

This runs the TypeScript build and creates the production frontend assets in `dist/`.

## 19. Automated testing

Run tests using the repository's Python virtual environment.

### Pipeline tests

From the repository root:

```powershell
python -m pytest .\hazina_pipeline\tests
```

### Server tests

```powershell
python -m pytest .\hazina_server\tests
```

### Frontend type checking

From `hazina_frontend`:

```powershell
npx tsc --noEmit
```

### Frontend production build

```powershell
npm run build
```

### Frontend linting

```powershell
npm run lint
```

The automated tests cover pipeline configuration, file reading, mapping, validation, deduplication, promotion, orchestration, failure isolation, reporting, authentication, authorization, organization isolation and API behavior.

Test counts can change as the project evolves. Run the tests against the current checkout before declaring a release verified.

## 20. Security and operational considerations

Before deploying Hazina beyond a local development environment:

- Use strong database credentials.
- Store secrets outside source control.
- Configure secure JWT signing secrets.
- Use HTTPS.
- Restrict database network access.
- Apply least-privilege database permissions.
- Protect uploaded financial files and generated reports.
- Review file upload size and extension restrictions.
- Configure production CORS origins.
- Establish secure backup and restore procedures.
- Review logging to avoid exposing sensitive financial data.
- Verify organization isolation in the deployment environment.
- Configure a production-grade email service before introducing email-dependent account workflows.

The development configuration is not a production deployment specification.

## 21. Known V2 limitations

The following capabilities are intentionally deferred or incomplete:

### Content-based deduplication

V2 uses provider transaction identifiers for source-aware deduplication. Content-based fingerprinting for sources without provider IDs is not implemented.

### MPESA file mapping

The MPESA file source registration exists, but the mapping and representative sample validation are incomplete.

### API ingestion

V2 does not implement API ingestion clients.

### Account recovery and email workflows

Email verification, password reset and production transactional email are deferred.

### Advanced operational capabilities

More advanced retry frameworks, automated recovery, scheduling and expanded observability remain potential future enhancements.

## 22. V3 roadmap

V3 is intended to extend the shared platform without compromising the stability of the V2 file-based pipeline.

Potential work includes:

- Content-based transaction fingerprinting.
- Complete MPESA statement-file support.
- MPESA API integration through Safaricom Daraja.
- Stripe API ingestion.
- Plaid API ingestion.
- Additional financial APIs.
- API authentication and pagination.
- Rate-limit handling.
- Incremental synchronization.
- Webhook processing.
- API-specific error handling.
- Email verification.
- Password reset.
- Production transactional email.
- Further operational automation and observability.
- Organization-specific user-facing run references while retaining globally unique database run IDs.

These are future enhancements, not claims of completed V2 functionality.

## 23. Legacy V1

V1 was the original single-source CSV-to-PostgreSQL implementation.

Its legacy modules remain available for backward compatibility and regression testing.

V2 is the primary multi-source, file-based financial data pipeline.

## 24. Development principles

Hazina is developed incrementally, with emphasis on:

- Correctness.
- Traceability.
- Data integrity.
- Organization isolation.
- Explicit source configuration.
- Source-specific mapping.
- Preservation of original records.
- Consistent canonical transactions.
- Reliable database transactions.
- Independent file execution.
- Auditable operational metrics.
- Automated testing.
- Maintainable architecture.

The objective is to build a reusable financial data platform that can support additional providers without creating a separate ingestion and processing system for every source.

---

**Project:** Hazina Financial Transactions Pipeline

**Database:** `hazina_warehouse`

**Architecture:** Multi-tenant financial data platform

**Current implementation:** V2 — File-based ingestion and processing