# Hazina 
# AI Powered Financial Transactions Pipeline

A production-style financial data engineering pipeline built with **Python and PostgreSQL** to ingest, validate, clean, deduplicate, transform, and analyze financial transaction data.

## 1. Project Overview

Hazina is a data engineering project that demonstrates how financial transaction data can be processed through a structured, reliable, and auditable data pipeline.

The project initially uses synthetic CSV transaction data, with API-based ingestion planned as a future extension.

The pipeline is designed around data quality, traceability, reliability, security, and repeatable execution.

## 2. Project Objectives

- Build a structured financial data ingestion process.
- Validate transaction records against technical and business rules.
- Clean and standardize incoming data.
- Identify duplicate transactions without discarding legitimate records.
- Quarantine invalid records with clear rejection reasons.
- Store trusted transaction data in PostgreSQL.
- Develop analytical SQL transformations.
- Track pipeline execution, errors, and data quality metrics.
- Support safe reruns and recovery from failures.

## 3. Technology Stack

| Technology     | Purpose                           |
| -------------- | --------------------------------- |
| Python         | Pipeline development              |
| PostgreSQL 18  | Relational data warehouse         |
| SQL            | Data transformation and analytics |
| pandas         | Data manipulation                 |
| SQLAlchemy     | Database interaction              |
| Psycopg        | PostgreSQL connectivity           |
| pytest         | Automated testing                 |
| Git and GitHub | Version control                   |
| VS Code        | Development environment           |

Additional technologies may be introduced as the project evolves.

## 4. Data Pipeline Architecture

The planned processing flow is:

1. **Ingestion** – Discover and extract incoming CSV files.
2. **Raw storage** – Preserve source records and ingestion metadata.
3. **Validation** – Check structural, technical, and business requirements.
4. **Quarantine** – Isolate invalid records and record rejection reasons.
5. **Cleaning** – Normalize and standardize valid records.
6. **Deduplication** – Identify repeated records across files and pipeline runs.
7. **Loading** – Store trusted records in PostgreSQL.
8. **Transformation** – Generate analytical datasets using SQL.
9. **Monitoring** – Record execution status, metrics, errors, and processing history.

## 5. Database Architecture

The PostgreSQL database is named `hazina_warehouse`.

It uses five logical schemas:

| Schema      | Responsibility                                                 |
| ----------- | -------------------------------------------------------------- |
| `raw`       | Original source transaction records                            |
| `staging`   | Parsed and standardized transaction records                    |
| `core`      | Trusted business entities and transactions                     |
| `analytics` | Analytical summaries and reporting datasets                    |
| `ops`       | Pipeline runs, processed files, quarantine, and quality issues |

## 6. Transaction Data Model

The planned transaction model includes:

- Transaction ID
- Customer ID
- Transaction date and time
- Transaction type
- Amount
- Currency
- Payment method
- Transaction status
- Merchant ID, where applicable
- Reference ID, where applicable
- Source system

Technical metadata will support ingestion tracking, batch identification, source provenance, and auditability.

Initial transaction types include payments, refunds, deposits, withdrawals, transfers, and reversals.

## 7. Project Structure

```text
hazina_fin_trans_pipeline/
├── config/
├── data/
│   ├── incoming/
│   ├── processed/
│   ├── archive/
│   └── sample/
├── src/
│   ├── ingestion/
│   ├── validation/
│   ├── cleaning/
│   ├── deduplication/
│   ├── transformations/
│   ├── database/
│   └── monitoring/
├── sql/
├── logs/
├── tests/
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── main.py
```

## 8. Reliability and Data Quality

Hazina is designed to demonstrate:

- Idempotent pipeline execution.
- Duplicate detection and database-level uniqueness.
- Transactional database loading.
- Invalid-record quarantine.
- Pipeline execution auditing.
- Controlled failure handling and recovery.
- Automated testing of individual components and complete pipeline runs.

## 9. Security

- Database credentials will be stored in environment variables.
- Secrets will be excluded from version control.
- The application will use a dedicated PostgreSQL role.
- Generated transaction data and operational logs will be excluded from Git.
- Synthetic data will be used for development and demonstrations.

## 10. Project Status

**Current phase:** Environment setup and project architecture preparation.

Completed:

- Python virtual environment configured.
- PostgreSQL installed and verified.
- `hazina_warehouse` database created.
- Five database schemas created.
- VS Code and Git configured.
- Git repository initialized on the `main` branch.
- Project directory structure established.
- Python package markers created.
- `.gitignore` configured and verified.

Upcoming:

- Complete project documentation.
- Confirm Python package compatibility.
- Define dependency versions.
- Design the database schema.
- Develop synthetic transaction datasets.
- Implement and test the pipeline incrementally.

## 11. Development Philosophy

Hazina will be developed incrementally, with each component designed, implemented, and tested before moving to the next stage.

The focus is not simply to move data from CSV files into a database, but to demonstrate sound data engineering principles through a reliable, traceable, and maintainable financial data pipeline.

---

**Project:** Hazina Financial Transactions Pipeline
**Database:** `hazina_warehouse`
**Primary technologies:** Python and PostgreSQL
**Project type:** Data Engineering Project
