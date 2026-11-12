# Hazina
# AI Powered Financial Transactions Pipeline

A production-style financial data engineering pipeline built with **Python and PostgreSQL** to ingest, validate, standardize, deduplicate, and analyze financial transaction data.

## 1. Project Overview

Hazina is a financial data engineering project demonstrating how transaction data can be processed through a structured, reliable, and auditable data pipeline.

The current V1 implementation uses synthetic CSV transaction data and PostgreSQL as its data warehouse.

The pipeline focuses on:

- Data quality and validation.
- Transaction standardization.
- Duplicate detection and handling.
- Reliable database loading.
- Pipeline execution tracking.
- Error monitoring and reporting.
- Analytical SQL views.
- Automated testing.

The architecture is designed to support future extensions such as API-based ingestion and additional financial data sources.

## 2. Project Objectives

- Build a structured financial data ingestion process.
- Validate transaction records against technical and business rules.
- Standardize valid transaction records.
- Identify exact and conflicting duplicates without discarding legitimate transactions.
- Reject invalid records with traceable rejection reasons.
- Store trusted transaction data in PostgreSQL.
- Develop analytical SQL views.
- Track pipeline execution, errors, and data quality metrics.
- Prevent unnecessary duplicate promotions into the core database.
- Generate automated pipeline execution reports.

## 3. Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.14 | Pipeline development |
| PostgreSQL 18 | Relational data warehouse |
| SQL | Database transformations and analytics |
| pandas | Data manipulation |
| Psycopg 3 | PostgreSQL connectivity |
| SQLAlchemy | Database tooling |
| python-dotenv | Environment configuration |
| pytest | Automated testing |
| ReportLab | PDF report generation |
| pypdf | PDF inspection and verification |
| Git and GitHub | Version control |
| VS Code | Development environment |

## 4. Pipeline Architecture

The implemented processing flow is:

1. **Raw ingestion** – Read incoming CSV transaction data and register a pipeline run.
2. **Raw storage** – Preserve source transaction records and ingestion metadata.
3. **Validation** – Check required fields, timestamps, amounts, identifiers, and allowed values.
4. **Rejection handling** – Record invalid records and their rejection reasons.
5. **Standardization** – Normalize valid transaction values and load them into staging.
6. **Deduplication** – Identify unique transactions, exact duplicates, and conflicting duplicates.
7. **Core promotion** – Promote eligible transactions into the core schema while protecting existing records.
8. **Analytics** – Expose transaction summaries through SQL views.
9. **Monitoring** – Track pipeline execution, processing metrics, errors, and promotion results.
10. **Reporting** – Generate and save a PDF report for each completed or failed pipeline run where a run ID is available.

## 5. Database Architecture

The PostgreSQL database is named `hazina_warehouse`.

It uses five logical schemas:

| Schema | Responsibility |
|---|---|
| `raw` | Original source transaction records and ingestion metadata |
| `staging` | Validated and standardized transaction records, including duplicate classifications |
| `core` | Trusted transaction records |
| `analytics` | Analytical summaries and reporting views |
| `ops` | Pipeline execution history, validation errors, and operational metrics |

### Database objects

The implementation includes:

- Raw transaction storage.
- Staging transaction storage.
- Core transaction storage.
- Pipeline run tracking.
- Pipeline error tracking.
- Transaction summary views.
- Daily transaction summaries.
- Transaction overview and status summaries.
- Pipeline monitoring view.

## 6. Transaction Data Model

The initial CSV dataset contains eight fields:

| Field | Description |
|---|---|
| `transaction_id` | Unique transaction identifier |
| `customer_id` | Customer identifier |
| `transaction_date` | Transaction timestamp |
| `transaction_type` | Financial transaction classification |
| `amount` | Transaction amount |
| `currency` | Transaction currency |
| `payment_method` | Transaction payment channel |
| `status` | Transaction processing status |

### Supported transaction types

- `PAYMENT`
- `DEPOSIT`
- `WITHDRAWAL`
- `TRANSFER`
- `REFUND`
- `FEE`

### Supported statuses

- `INITIATED`
- `PENDING`
- `COMPLETED`
- `FAILED`
- `REVERSED`

### Supported currencies

- `KES`
- `USD`

### Supported payment methods

- `MPESA`
- `BANK_TRANSFER`
- `CARD`
- `CASH`
- `DIGITAL_WALLET`
- `USSD`
- `AGENT`

## 7. Sample Dataset

The project uses a synthetic CSV dataset located at:

`data/sample/hazina_transactions.csv`

The dataset contains 1,000 transaction records with deliberately introduced data-quality issues.

| Record category | Count |
|---|---:|
| Valid unique records | 850 |
| Exact duplicate records | 50 |
| Records with missing required values | 50 |
| Records with invalid amounts | 20 |
| Records with invalid timestamps | 10 |
| Records with invalid enum values | 10 |
| Records with conflicting duplicate identifiers | 10 |
| **Total** | **1,000** |

The dataset is used to demonstrate validation, rejection handling, deduplication, and reliable data loading.

## 8. Project Structure

```text
hazina_fin_trans_pipeline/
│
├── config/
├── data/
│   └── sample/
│       └── hazina_transactions.csv
│
├── reports/
│   └── pipeline_run_<run_id>_report.pdf
│
├── logs/
│
├── sql/
│   └── Database schema and migration scripts
│
├── src/
│   ├── database/
│   │   └── connection.py
│   │
│   ├── ingestion/
│   │   └── load_raw.py
│   │
│   ├── validation/
│   │   └── validate_transactions.py
│   │
│   ├── deduplication/
│   │   └── deduplicate_transactions.py
│   │
│   ├── monitoring/
│   │   └── pipeline_status.py
│   │
│   ├── cleaning/
│   ├── transformations/
│   │
│   └── run_pipeline.py
│
├── tests/
│   ├── conftest.py
│   ├── test_validation.py
│   ├── test_deduplication.py
│   ├── test_database_integration.py
│   └── test_pipeline_monitoring.py
│
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## 9. Data Quality and Deduplication

The pipeline implements validation rules covering:

- Required transaction fields.
- Identifier length constraints.
- ISO 8601 timestamps with timezone information.
- Positive and finite transaction amounts.
- Decimal precision and numeric capacity.
- Allowed transaction types, currencies, payment methods, and statuses.

Invalid records are rejected and recorded in `ops.pipeline_errors` with their associated rejection reasons.

### Duplicate handling

The deduplication process distinguishes three classifications:

| Classification | Handling |
|---|---|
| `UNIQUE` | Eligible for core promotion |
| `EXACT_DUPLICATE` | Retain one representative record and identify redundant copies |
| `CONFLICTING_DUPLICATE` | Quarantine conflicting records from core promotion |

The pipeline also checks whether eligible transactions already exist in the core schema.

This prevents unnecessary re-promotion of previously loaded transactions.

## 10. Monitoring and Reporting

Pipeline execution is tracked in `ops.pipeline_runs`.

The monitoring functionality captures:

- Run status.
- Records received.
- Records staged.
- Records rejected.
- Duplicate classifications.
- Unique records eligible for core promotion.
- Newly promoted records.
- Records already existing in core.
- Pipeline execution timestamps.

### PDF reports

Every pipeline execution automatically attempts to generate a PDF report.

Reports are saved in the project's root-level `reports/` directory.

Example:

```text
reports/
├── pipeline_run_1_report.pdf
├── pipeline_run_2_report.pdf
├── pipeline_run_3_report.pdf
└── pipeline_run_<run_id>_report.pdf
```

Each report contains:

- Pipeline run details.
- Record processing statistics.
- Deduplication results.
- Core promotion metrics.
- Explanation of promotion outcomes.
- Validation rejection reasons.

PDF generation reuses the same reporting information displayed by the console reporting functionality.

PDF permission restrictions are configured to allow viewing and printing while restricting modification, copying, and annotation. These restrictions are not equivalent to absolute document security.

## 11. Installation and Configuration

### Prerequisites

- Python 3.14 or compatible Python environment.
- PostgreSQL 18 or compatible PostgreSQL installation.
- Git.
- PowerShell or another terminal.

### Clone the repository

```powershell
git clone <repository-url>
cd hazina_fin_trans_pipeline
```

### Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
pip install -r requirements.txt
```

### Configure environment variables

Create a `.env` file in the project root using `.env.example` as a template.

Configure the following database variables:

```text
DB_HOST=
DB_PORT=
DB_NAME=
DB_USER=
DB_PASSWORD=
```

Do not commit `.env` or expose database credentials.

### Database setup

Create the `hazina_warehouse` database and configure the application database role.

Execute the SQL schema and migration scripts in the `sql/` directory in their intended order.

The application connects to PostgreSQL through the centralized connection module:

`src/database/connection.py`

## 12. Running the Pipeline

Activate the virtual environment and execute the pipeline from the project root:

```powershell
python -m src.run_pipeline
```

The orchestrator executes:

1. Raw ingestion.
2. Transaction validation.
3. Deduplication and core promotion.
4. Pipeline completion and PDF report generation.

The console displays processing statistics and the resulting pipeline run ID.

A corresponding PDF report is automatically saved in `reports/`.

## 13. Running Automated Tests

Run the complete test suite:

```powershell
pytest -v
```

The tests cover:

- Transaction validation.
- Data standardization.
- Duplicate detection.
- Database integration.
- Core promotion.
- Existing transaction protection.
- Pipeline failure handling.
- Monitoring summaries.
- Rejection reason reporting.
- Console report generation.
- PDF report generation and file saving.

The V1 regression suite has passed:

**36 tests passed.**

## 14. Security and Reliability

The project incorporates the following practices:

- Database credentials stored in environment variables.
- Secrets excluded from version control.
- Dedicated PostgreSQL application role.
- Centralized database connection management.
- Validation before core promotion.
- Duplicate protection across pipeline runs.
- Pipeline execution and error tracking.
- Automated component and integration tests.
- Synthetic transaction data for development and demonstration.

## 15. Project Status and Future Extensions

**Current status: V1 implementation and end-to-end verification completed.**

The implemented V1 provides an operational CSV-to-PostgreSQL financial transaction pipeline with validation, deduplication, core promotion, analytics, monitoring, automated testing, and PDF reporting.

Potential future extensions include:

- API-based transaction ingestion.
- Support for additional financial data sources.
- More advanced transformation and analytical models.
- Enhanced operational logging and observability.
- Stronger document security and report distribution.
- Automated pipeline scheduling.

These are future enhancements and are not represented as completed V1 functionality.

## 16. Development Philosophy

Hazina is developed incrementally, with each component implemented and tested before moving to the next stage.

The objective is not simply to transfer CSV records into a database, but to demonstrate sound financial data engineering principles through a reliable, traceable, maintainable, and auditable pipeline.

---

**Project:** Hazina Financial Transactions Pipeline  
**Database:** `hazina_warehouse`  
**Primary technologies:** Python and PostgreSQL  
**Project type:** Financial Data Engineering  
**Current release:** V1
