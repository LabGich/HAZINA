# Hazina Installation Guide

This guide explains how to prepare a local development environment for the Hazina Financial Transactions Pipeline.

Hazina consists of three components:

- **Pipeline:** Python package for financial transaction ingestion, mapping, validation, deduplication, and reporting.
- **Backend:** FastAPI application providing authentication, organization management, pipeline operations, and dashboard APIs.
- **Frontend:** React and TypeScript application providing the user interface.

## 1. Prerequisites

Install the following software before proceeding:

| Software | Requirement |
|---|---|
| Python | 3.11 or newer |
| PostgreSQL | Database server |
| Node.js | Version compatible with the frontend dependencies |
| npm | Installed with Node.js |
| Git | For cloning and managing the repository |

Verify the installations:

```powershell
python --version
node --version
npm --version
git --version
```

Confirm that PostgreSQL is running and accessible.

## 2. Obtain the repository

Clone the repository:

```powershell
git clone https://github.com/LabGich/HAZINA.git hazina_fin_trans_pipeline
```

Move into the project directory:

```powershell
cd hazina_fin_trans_pipeline
```

The repository contains:

```text
hazina_fin_trans_pipeline/
├── docs/
├── hazina_pipeline/
├── hazina_server/
├── hazina_frontend/
├── README.md
└── .gitignore
```

If the repository is already cloned, use the existing project directory instead.

## 3. Create the Python environment

From the repository root, create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell prevents activation, you can invoke the virtual environment's Python executable directly:

```powershell
.\.venv\Scripts\python.exe --version
```

Upgrade pip:

```powershell
python -m pip install --upgrade pip
```

## 4. Install the Python packages

Install the pipeline package and its development dependencies:

```powershell
python -m pip install -e .\hazina_pipeline
python -m pip install -r .\hazina_pipeline\requirements-dev.txt
```

Install the backend package and its development dependencies:

```powershell
python -m pip install -e .\hazina_server
python -m pip install -r .\hazina_server\requirements-dev.txt
```

Both packages use the repository's root virtual environment.

## 5. Configure environment variables

Hazina uses a shared root-level `.env` file for database, authentication, and PDF configuration.

Copy the pipeline environment template:

```powershell
Copy-Item .\hazina_pipeline\.env.example .\.env
```

Open the root `.env` file:

```powershell
notepad .\.env
```

Configure the database connection:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hazina_warehouse
DB_USER=your_database_user
DB_PASSWORD=your_database_password
```

Configure JWT authentication:

```dotenv
JWT_SECRET_KEY=replace_with_a_secure_random_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

Generate a secure JWT secret using Python:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the generated value into `JWT_SECRET_KEY`.

Configure PDF report passwords:

```dotenv
HAZINA_PDF_USER_PASSWORD=your_pdf_open_password
HAZINA_PDF_OWNER_PASSWORD=your_pdf_owner_password
```

Use strong, unique passwords. Keep the root `.env` file private and never commit it to Git.

### Environment variable reference

| Variable | Purpose |
|---|---|
| `DB_HOST` | PostgreSQL host |
| `DB_PORT` | PostgreSQL port |
| `DB_NAME` | Database name |
| `DB_USER` | Database username |
| `DB_PASSWORD` | Database password |
| `JWT_SECRET_KEY` | Secret used to sign JWTs |
| `JWT_ALGORITHM` | JWT signing algorithm; defaults to `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime; defaults to 15 minutes |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime; defaults to 7 days |
| `HAZINA_PDF_USER_PASSWORD` | Password required to open protected PDF reports |
| `HAZINA_PDF_OWNER_PASSWORD` | Owner password for protected PDF reports |

The pipeline and backend both load configuration from the repository root `.env` file.

## 6. Configure the frontend

Move into the frontend directory:

```powershell
cd .\hazina_frontend
```

Copy the frontend environment template:

```powershell
Copy-Item .\.env.example .\.env
```

The default configuration is:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

This points the frontend to the local FastAPI backend.

Install the frontend dependencies:

```powershell
npm ci
```

Return to the repository root:

```powershell
cd ..
```

## 7. Database preparation

Before using the application, PostgreSQL must be running and the configured database must exist.

The database schema and application tables must also be initialized using the SQL migrations in:

```text
hazina_pipeline/sql/
```

Migration execution and database initialization are covered separately in the database setup guide.

The application requires the database schema to be initialized before normal authentication and pipeline operations can work.

## 8. Start the backend

Open a terminal at the repository root and move into the backend directory:

```powershell
cd .\hazina_server
```

Start the FastAPI application:

```powershell
..\.venv\Scripts\python.exe -m uvicorn server.main:app --reload
```

The backend runs at:

```text
http://127.0.0.1:8000
```

Useful endpoints:

| Endpoint | Purpose |
|---|---|
| `/health` | Application health |
| `/health/database` | Database connectivity |
| `/docs` | Interactive API documentation |

Keep this terminal running.

## 9. Start the frontend

Open a second terminal at the repository root:

```powershell
cd .\hazina_frontend
npm run dev
```

The frontend is available at:

```text
http://localhost:5173
```

Keep this terminal running as well.

## 10. Access the application

Open the frontend in your browser:

```text
http://localhost:5173
```

The application presents the login page. Sign in using an administrator account provisioned for the organization.

Administrator account provisioning and database bootstrap procedures are covered in the database and administration documentation.

## 11. Build the frontend for production

To verify the frontend production build:

```powershell
cd .\hazina_frontend
npx tsc --noEmit
npm run build
```

The production build is generated in:

```text
hazina_frontend/dist/
```

The development server is intended for local development, not production hosting.

## 12. Run automated tests

Run the pipeline tests from the repository root:

```powershell
python -m pytest .\hazina_pipeline\tests
```

Run the backend tests:

```powershell
python -m pytest .\hazina_server\tests
```

Run frontend type checking and build verification:

```powershell
cd .\hazina_frontend
npx tsc --noEmit
npm run build
```

## 13. Common setup issues

### Database connection errors

Check that:

- PostgreSQL is running.
- The configured database exists.
- The database username and password are correct.
- The root `.env` contains all required database variables.
- The database migrations have been applied.

### JWT configuration errors

Check that:

- `JWT_SECRET_KEY` is configured in the root `.env`.
- The secret is not empty.
- The backend is restarted after changing environment configuration.

### Frontend cannot reach the backend

Check that:

- The backend is running on port 8000.
- `VITE_API_BASE_URL` points to the correct backend URL.
- The frontend is running on port 5173.
- The backend CORS configuration permits the frontend origin.

### Python package import errors

Confirm that:

- The root virtual environment is activated, or its Python executable is being used.
- Both Python packages have been installed.
- The backend is started from the `hazina_server` directory.

---

**End of installation guide.**