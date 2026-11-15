# Hazina
# AI Powered Financial Transactions Pipeline

An AI powered configurable, multi-source financial data engineering pipeline built to ingest, preserve, map, validate, deduplicate, and analyze financial transaction data.

Hazina V2 provides a shared file-based ingestion framework for financial data from multiple providers. It uses source-specific configuration and mapping rules while reusing common processing, validation, deduplication, persistence, monitoring, and reporting components.

---

## 1. Project Overview

Hazina is a financial data engineering project designed to process transaction data from different financial providers through a consistent, auditable pipeline.

V2 moves beyond the original single-source CSV implementation by introducing a configurable, multi-source architecture.

The pipeline supports:

- Multiple financial statement sources.
- Multiple files within a single pipeline run.
- Source-specific mapping configurations.
- Shared file readers for different file formats.
- Preservation of original source records.
- Canonical transaction standardization.
- Mapping and validation error tracking.
- Source-aware transaction deduplication.
- Controlled promotion into the core database.
- Independent file execution and failure isolation.
- Pipeline monitoring and operational reporting.
- Password-protected PDF reports.

The architecture is designed so that adding a new file-based source primarily involves registering the source and defining its mapping configuration rather than building a separate ingestion pipeline.

**V2 focuses on file-based ingestion. API-based ingestion is deferred to V3.**

## 2. Project Objectives

- Build a reusable multi-source financial data ingestion framework.
- Support different financial statement formats.
- Preserve original records for traceability and auditing.
- Map provider-specific fields into a canonical transaction model.
- Validate transactions against technical and business rules.
- Record mapping and validation errors.
- Identify provider-ID-based duplicates and conflicting transactions.
- Prevent conflicting transactions from entering core storage.
- Promote eligible transactions safely.
- Support multiple files in a single pipeline run.
- Isolate file-level failures without unnecessarily interrupting other files.
- Track pipeline execution and per-file processing metrics.
- Generate detailed operational reports.
- Keep the architecture extensible without unnecessary complexity.

## 3. Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.14 | Pipeline development |
| PostgreSQL 18 | Financial data warehouse |
| SQL | Database schemas, migrations and analytics |
| pandas | Data manipulation and file processing |
| Psycopg 3 | PostgreSQL connectivity |
| SQLAlchemy | Database tooling |
| python-dotenv | Environment configuration |
| PyYAML | Source and mapping configuration |
| openpyxl | Excel file reading |
| pyarrow | Parquet file processing |
| charset-normalizer | Character encoding detection |
| ReportLab | PDF report generation and encryption |
| pypdf | PDF inspection and verification |
| pytest | Automated testing |
| Git and GitHub | Version control |

## 4. V2 Architecture

V2 uses a shared processing architecture.

Each financial provider has its own source registration and mapping configuration. All providers use the same underlying ingestion, mapping, validation, deduplication, persistence, orchestration, and reporting framework.

### Processing architecture

```text
                  SOURCE CONFIGURATION
                          |
                          v
                   SOURCE REGISTRY
                          |
                          v
              PIPELINE RUN ORCHESTRATOR
                          |
               One parent pipeline run
                          |
             +------------+------------+
             |            |            |
             v            v            v
          File 1       File 2       File 3
          Child        Child        Child
        Execution    Execution    Execution
             |            |            |
             v            v            v
        File Reader  File Reader  File Reader
             |            |            |
             v            v            v
         RAW STORAGE  RAW STORAGE  RAW STORAGE
             |            |            |
             v            v            v
        SOURCE-SPECIFIC MAPPING
             |            |            |
             v            v            v
          STAGING      STAGING      STAGING
             |            |            |
             v            v            v
         VALIDATION   VALIDATION   VALIDATION
             |            |            |
             v            v            v
        DEDUPLICATION AND CORE PROMOTION
             |            |            |
             +------------+------------+
                          |
                          v
                 EXECUTION FINALIZATION
                          |
                          v
                 PARENT RUN FINALIZATION
                          |
                          v
                 ANALYTICS AND REPORTING
                          |
                          v
                    PDF REPORT
```

Each submitted file receives an independent source execution.

A single parent pipeline run can contain multiple files, including multiple files belonging to the same source.

### Shared processing components

The following components are shared across supported sources:

- File readers.
- Source file reader and adapter registry.
- Mapping engine.
- Mapping configuration validator.
- Canonical transaction model.
- Validation engine.
- Deduplication engine.
- Database persistence.
- Pipeline orchestration.
- Monitoring and reporting.

Source-specific behavior is primarily defined through configuration and mapping rules.

Adapters are introduced only when a source has genuinely different file-reading requirements.

## 5. Pipeline Processing Lifecycle

The V2 orchestrator is implemented in:

`src/run_pipeline_v2.py`

The main entry point is:

`run_pipeline_v2(files)`

The orchestrator performs the following operations:

1. Synchronize configured sources with the database source registry.
2. Create one parent pipeline run and its child source executions.
3. Start each source execution.
4. Read the submitted file.
5. Preserve original records in raw storage.
6. Map source records into canonical transactions.
7. Record mapping errors.
8. Validate staged transactions.
9. Record validation errors.
10. Deduplicate eligible transactions.
11. Promote eligible transactions into core storage.
12. Update source execution metrics.
13. Finalize each source execution.
14. Continue processing sibling files after an individual file failure.
15. Finalize the parent pipeline run after all child executions reach terminal states.
16. Generate the PDF report after parent finalization.

### Execution boundaries

Each source execution is processed independently.

A failure in one file should not roll back completed work belonging to successful sibling files.

Processing stages use transactional boundaries so that failed work can be recorded without unnecessarily affecting other executions.

Failure handling records fatal errors separately through `fail_source_execution()`.

Report generation occurs after pipeline finalization. A reporting failure does not change the outcome of an already completed pipeline run.

## 6. Database Architecture

The PostgreSQL database is named:

`hazina_warehouse`

It uses five logical schemas.

| Schema | Responsibility |
|---|---|
| `raw` | Original provider records and ingestion metadata |
| `staging` | Canonical mapped transactions and validation state |
| `core` | Trusted promoted financial transactions |
| `analytics` | Analytical summaries and reporting views |
| `ops` | Pipeline execution, source configuration, errors and operational tracking |

### Operational database objects

The operational schema includes:

- `ops.pipeline_runs`
- `ops.source_registry`
- `ops.source_executions`
- `ops.pipeline_errors`
- `ops.mapping_errors`
- `ops.validation_errors`
- `ops.source_transaction_identity`
- `ops.ingestion_checkpoints`
- `ops.transaction_audit`

### Transaction storage

The principal transaction storage layers are:

- `raw.transactions`
- `staging.transactions`
- `core.transactions`

Raw and staging records are associated with their source execution where applicable.

This allows records to be traced back to the file and pipeline execution that processed them.

### Database migrations

Database migration scripts are maintained directly under:

`sql/`

The implemented database migration history extends through migration 25.

Historical migrations should be preserved. Schema changes should be introduced through new migrations rather than editing migrations that have already been applied.

## 7. Canonical Transaction Model

Different financial providers use different field names and transaction representations.

V2 maps these provider-specific records into a shared canonical transaction model.

### Canonical fields

| Field | Description |
|---|---|
| `transaction_id` | Hazina-generated transaction identifier |
| `source_name` | Financial provider or source name |
| `source_transaction_id` | Provider transaction identifier, when available |
| `source_account_id` | Source account identifier |
| `customer_id` | Optional customer identifier |
| `transaction_date` | Transaction timestamp |
| `transaction_type` | Standardized transaction classification |
| `amount` | Positive transaction amount |
| `currency` | ISO 4217 currency code |
| `direction` | DEBIT, CREDIT or UNKNOWN |
| `payment_method` | Standardized payment channel |
| `status` | Standardized transaction status |
| `description` | Transaction description |
| `counterparty` | Transaction counterparty |
| `fee_amount` | Transaction fee, when available |
| `account_balance` | Account balance, when available |

Provider transaction identifiers are kept separate from Hazina-generated transaction identifiers.

Optional source information is preserved where available.

### Supported transaction types

- `PAYMENT`
- `DEPOSIT`
- `WITHDRAWAL`
- `TRANSFER`
- `REFUND`
- `FEE`
- `REVERSAL`

### Supported statuses

- `INITIATED`
- `PENDING`
- `COMPLETED`
- `FAILED`
- `REVERSED`

### Transaction directions

- `DEBIT`
- `CREDIT`
- `UNKNOWN`

### Payment methods

- `MPESA`
- `BANK_TRANSFER`
- `CARD`
- `CASH`
- `DIGITAL_WALLET`
- `USSD`
- `AGENT`
- `OTHER`
- `UNKNOWN`

### Standardization rules

- Transaction amounts use positive numeric values, with direction represented separately.
- Currency values use ISO 4217 codes.
- Transaction timestamps are normalized to UTC.
- Naive timestamps are rejected unless a source timezone is configured.
- Provider identifiers remain distinct from Hazina identifiers.
- Original provider records are preserved in raw storage.

## 8. Supported Sources and File Formats

V2 supports multiple registered financial sources.

### File-based sources

| Source | Supported formats | Default mapping |
|---|---|---|
| EQUITY | CSV, JSON | `equity_csv_v1` |
| KCB | CSV, JSON | `kcb_csv_v1` |
| COOP | CSV, JSON | `coop_csv_v1` |
| NCBA | CSV, JSON | `ncba_csv_v1` |
| EXPLORE_MY_DATA | CSV, XLSX, JSON, JSONL, Parquet | `explore_my_data_v1` |
| UTILLY | CSV, XLSX | `utilly_bank_csv_v1` |
| MPESA | CSV, XLSX, JSON | `mpesa_csv_v1` |

For Utilly XLSX statements, the caller must explicitly select:

`utilly_bank_xlsx_v1`

The default Utilly mapping is for CSV files.

The MPESA file source registration is retained for future statement-file support. Its mapping is not yet implemented, and no sample statement mapping has been completed.

### Shared file readers

The shared file reader implementation is:

`src/ingestion/source_readers.py`

Supported readers:

| Reader | File format |
|---|---|
| CSVReader | CSV |
| XLSXReader | Excel XLSX |
| JSONReader | JSON |
| JSONLReader | JSON Lines |
| ParquetReader | Parquet |

The format registry resolves supported file extensions to their corresponding readers.

### Source-specific file adapters

Some providers require additional handling before their records can enter the shared mapping framework.

The Utilly adapter supports:

- CSV and XLSX statements.
- Statement preamble metadata.
- Configurable header row handling.
- Account and statement-period extraction.
- Filtering of beginning-balance and totals rows.

The adapter is registered through:

`src/ingestion/adapters/registry.py`

Source-specific adapters are not intended to replace the shared processing framework.

## 9. Source and Mapping Configuration

Source configuration is maintained under:

`config/sources/sources.yaml`

Mapping configurations are maintained under:

`config/mappings/`

Each source has its own registration and mapping configuration.

### Mapping inventory

| Source | Mapping configurations |
|---|---|
| EQUITY | `equity_csv_v1`, `equity_json_v1` |
| KCB | `kcb_csv_v1`, `kcb_json_v1` |
| COOP | `coop_csv_v1`, `coop_json_v1` |
| NCBA | `ncba_csv_v1`, `ncba_json_v1` |
| EXPLORE_MY_DATA | `explore_my_data_v1` |
| UTILLY | `utilly_bank_csv_v1`, `utilly_bank_xlsx_v1` |

API source mapping configurations are retained for future development, but API ingestion is outside the V2 implementation scope.

### Mapping configuration responsibilities

Mapping configurations define:

- Mapping identifier and version.
- Source fields.
- Canonical destination fields.
- Date formats and timezone settings.
- Amount handling.
- Debit and credit handling.
- Default values.
- Required source fields.
- Field transformations.
- Derived transaction types.

### Mapping behavior

The shared mapping engine supports:

- Direct field mapping.
- Split debit and credit amounts.
- Signed amount handling.
- Positive amounts with separate direction.
- Default values.
- Field transformations.
- Derived transaction types.

Default values apply only when the mapped value is missing or blank. Actual source values take precedence.

### Adding a new file-based source

The intended source onboarding process is:

1. Register the source in `config/sources/sources.yaml`.
2. Define its supported file formats.
3. Create a source-specific mapping configuration.
4. Configure the source's field names and transformations.
5. Validate the mapping configuration.
6. Add representative source samples.
7. Test the source through the shared pipeline.
8. Verify raw preservation, mapping, validation, deduplication and promotion.

A new source should reuse the shared readers and processing components wherever possible.

Automatic source detection is not implemented. The caller explicitly supplies the source and mapping.

## 10. Raw Ingestion and Mapping

### Raw ingestion

Implemented in:

`src/ingestion/ingest_source_file.py`

The ingestion component:

- Reads the submitted file through the shared reader framework.
- Preserves original source records.
- Stores ingestion metadata.
- Associates records with their source execution.
- Tracks records received and loaded.
- Handles values such as dates, datetimes and decimals for JSON-safe persistence.

Raw storage provides traceability between provider records and downstream canonical transactions.

### Mapping

Implemented in:

`src/mapping/map_source_execution.py`

The mapping component:

- Retrieves raw records for the source execution.
- Resolves the supplied mapping configuration.
- Applies source-to-canonical transformations.
- Creates canonical staging records.
- Records mapping failures.
- Tracks mapped records.

Mapping errors are stored in:

`ops.mapping_errors`

The mapping framework includes configuration validation to detect invalid or incomplete mappings before processing.

## 11. Validation

Implemented in:

`src/validation/validate_source_execution.py`

Mapped staging transactions are validated before deduplication and promotion.

The validation process checks canonical transaction requirements and applicable business rules.

These include:

- Required canonical fields.
- Valid transaction timestamps.
- Positive and valid transaction amounts.
- Supported transaction types.
- Valid currencies.
- Supported payment methods.
- Supported transaction statuses.
- Valid transaction direction.
- Required source information.

Staging transactions use validation states:

- `PENDING`
- `VALID`
- `INVALID`

Validation failures are recorded in:

`ops.validation_errors`

Invalid transactions are excluded from core promotion.

## 12. Deduplication and Core Promotion

Implemented in:

`src/deduplication/deduplicate_source_execution.py`

V2 uses source-aware provider transaction identity for deduplication.

The identity is based on:

- Source.
- Provider transaction identifier.
- Source account identifier.

### Duplicate classifications

| Classification | Handling |
|---|---|
| UNIQUE | Eligible for core promotion |
| EXACT_DUPLICATE | Redundant identical transaction; retain one representative |
| CONFLICTING_DUPLICATE | Conflicting records sharing an identity; exclude the entire conflicting group |

### Existing core transactions

The pipeline also checks whether an eligible transaction is already represented in core storage.

- An identical existing transaction is counted as already in core.
- A transaction with the same identity but different canonical details is treated as a conflict.
- Existing core transactions are not overwritten by conflicting incoming records.

### Core promotion

Only eligible, unique, non-conflicting transactions are promoted.

Newly promoted transactions are recorded in the transaction audit history.

### Important deduplication limitation

V2 currently implements provider-ID-based identity deduplication.

Content-based transaction fingerprinting has not yet been implemented.

For sources that do not supply provider transaction identifiers, such as the current Equity and NCBA sample mappings, repeated submission of the same statement can result in transactions being promoted again.

Therefore, repeated submissions from sources without provider IDs should not yet be treated as safely deduplicated.

Content-based fingerprinting is a known enhancement for future implementation.

## 13. Orchestration and Execution Statuses

V2 uses two execution levels.

### Parent pipeline run

One parent pipeline run represents one submission of one or more files.

Tracked in:

`ops.pipeline_runs`

### Child source execution

Each submitted file receives its own source execution.

Tracked in:

`ops.source_executions`

Multiple files from the same source can belong to the same parent pipeline run.

The child execution tracks source-specific processing, errors, metrics and status.

### Child execution statuses

| Status | Meaning |
|---|---|
| PENDING | Execution created but not started |
| RUNNING | File processing is in progress |
| SUCCESS | Processing completed without record-level errors |
| PARTIAL_SUCCESS | Processing completed with rejected or skipped records |
| FAILED | Fatal failure prevented completion |
| SKIPPED | Execution deliberately skipped |
| CANCELLED | Execution cancelled |

A completed execution with all records rejected can still be `PARTIAL_SUCCESS`, because processing completed but records were not successfully processed.

### Parent pipeline statuses

| Status | Meaning |
|---|---|
| PENDING | Pipeline run created |
| RUNNING | Child executions are being processed |
| SUCCESS | All child executions succeeded |
| PARTIAL_SUCCESS | At least one child completed, but another was partial, failed, skipped or cancelled |
| FAILED | No child execution completed successfully |
| CANCELLED | Overall pipeline run was cancelled |

### Failure isolation

A fatal failure in one file does not automatically prevent the remaining files from being processed.

The failed execution is recorded independently.

Successful sibling executions retain their completed work.

The parent run is finalized after all child executions have reached terminal states.

If failure recording itself fails, the orchestrator raises an error and does not finalize the parent run in an uncertain state.

## 14. Pipeline Metrics

V2 tracks metrics at the source execution level and aggregates them at the parent pipeline level.

| Metric | Meaning |
|---|---|
| `records_received` | Records returned by the file reader |
| `records_loaded` | Raw records successfully persisted |
| `records_mapped` | Records successfully mapped |
| `records_rejected` | Mapping and validation failures |
| `records_skipped` | Deliberately excluded records |
| `records_duplicated` | Redundant exact duplicates and all records in conflicting groups |
| `records_unique_eligible` | Unique, non-conflicting validated records eligible for core |
| `records_promoted` | Newly inserted core transactions |
| `records_already_in_core` | Identical eligible transactions already represented in core |
| `records_updated` | Existing records actually updated, where applicable |

Child metrics are maintained independently.

Parent metrics aggregate the corresponding child execution results.

## 15. Monitoring and Reporting

V2 reporting is implemented in:

`src/monitoring/pipeline_status.py`

The V2 reporting functions include:

- `get_pipeline_v2_report_data`
- `print_pipeline_v2_run_report`
- `save_pipeline_v2_run_report`

### Console reporting

Console reporting provides a summary of pipeline execution, child execution outcomes, processing metrics and errors.

### PDF reporting

A PDF report is generated after the parent pipeline run is finalized.

Reports are stored in the root-level:

`reports/`

Example:

```text
reports/
├── pipeline_run_277_report.pdf
├── pipeline_run_278_report.pdf
└── pipeline_run_<run_id>_report.pdf
```

V2 reports contain:

- Parent pipeline run details.
- Overall pipeline status.
- Aggregate processing metrics.
- Per-file source execution details.
- Source and mapping information.
- Execution timestamps.
- Child execution statuses.
- Mapping errors.
- Validation errors.
- Fatal execution errors.
- Deduplication results.
- Core promotion metrics.

Report generation failure is recorded separately and does not change the already finalized pipeline outcome.

### PDF security

V2 PDF reports require an open password.

The PDF security implementation is maintained in:

`src/monitoring/pdf_security.py`

Configuration is supplied through environment variables:

```dotenv
HAZINA_PDF_USER_PASSWORD=
HAZINA_PDF_OWNER_PASSWORD=
```

The user password opens the V2 report.

The owner password controls the configured PDF permissions.

The passwords must be strong, distinct values and must never be committed to version control or shared in source code.

The configured PDF permissions:

- Allow printing.
- Restrict document modification.
- Restrict copying.
- Restrict annotations.

These PDF permission restrictions are advisory and should not be treated as absolute document security or DRM.

## 16. Installation and Configuration

### Prerequisites

- Python 3.14 or a compatible Python environment.
- PostgreSQL 18 or a compatible PostgreSQL installation.
- Git.
- PowerShell or another terminal.

### Clone the repository

```powershell
git clone <repository-url>

cd hazina_fin_trans_pipeline
```

### Create a virtual environment

```powershell
python -m venv .venv
```

### Activate the virtual environment

```powershell
.venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
pip install -r requirements.txt
```

### Configure environment variables

Create a `.env` file in the project root using `.env.example` as a template.

Configure the database connection:

```dotenv
DB_HOST=
DB_PORT=
DB_NAME=
DB_USER=
DB_PASSWORD=
```

Configure PDF report security:

```dotenv
HAZINA_PDF_USER_PASSWORD=
HAZINA_PDF_OWNER_PASSWORD=
```

Do not commit `.env` or expose database credentials and PDF passwords.

### Database setup

Create the PostgreSQL database:

`hazina_warehouse`

Configure the application database role and permissions.

Execute the SQL migration scripts under:

`sql/`

in their intended order.

The centralized database connection module is:

`src/database/connection.py`

## 17. Running the V2 Pipeline

The V2 orchestrator is:

`src/run_pipeline_v2.py`

The main function is:

```python
run_pipeline_v2(files)
```

The function accepts a non-empty list or tuple of file configurations.

Each file configuration must identify the file path, source and mapping to be used.

The source and mapping are supplied by the caller; the pipeline does not automatically detect them.

### Example invocation

The following illustrates the intended invocation pattern. Replace the sample paths and mapping identifiers with the files available in your environment.

```python
from src.run_pipeline_v2 import run_pipeline_v2

files = [
    {
        "file_path": "data/sample/source_samples/equity.csv",
        "source_name": "EQUITY",
        "mapping_id": "equity_csv_v1",
    },
    {
        "file_path": "data/sample/source_samples/kcb.csv",
        "source_name": "KCB",
        "mapping_id": "kcb_csv_v1",
    },
]

result = run_pipeline_v2(files)

print("Run ID:", result["run_id"])
print("Run status:", result["run_status"])
print("Report:", result["report_path"])
print("Report error:", result["report_error"])
```

The example demonstrates the function interface. File paths must exist, and source and mapping identifiers must match the registered configurations.

For an XLSX Utilly statement, use:

`utilly_bank_xlsx_v1`

For a CSV Utilly statement, use:

`utilly_bank_csv_v1`

### Returned results

The orchestrator returns:

| Field | Description |
|---|---|
| `run_id` | Parent pipeline run identifier |
| `run_status` | Final parent execution status |
| `pipeline` | Parent finalization result |
| `source_executions` | Individual child execution results |
| `report_path` | Generated PDF report path, if successful |
| `report_error` | Reporting error, if report generation fails |

Each child result includes its execution identifier, source, file path, execution status, stage results and error information.

## 18. Automated Testing

Run the complete automated test suite from the project root:

```powershell
python -m pytest
```

For verbose output:

```powershell
python -m pytest -v
```

The V2 test coverage includes:

- Source configuration validation.
- Source registry synchronization.
- Mapping configuration validation.
- Shared CSV reading.
- XLSX reading.
- JSON reading.
- JSONL reading.
- Parquet reading.
- Source-specific adapters.
- Raw record preservation.
- Canonical mapping.
- Mapping error handling.
- Transaction validation.
- Validation error persistence.
- Deduplication.
- Conflicting transaction handling.
- Core promotion.
- Existing core transaction protection.
- Parent pipeline orchestration.
- Child source execution lifecycle.
- Multiple files in one pipeline run.
- Multiple files from the same source.
- Failure isolation between sibling executions.
- Parent and child status finalization.
- Operational metrics.
- Console reporting.
- PDF report generation.
- PDF password protection and permissions.
- Legacy V1 regression coverage.

The completed V2 integration and regression test suite previously passed **182 tests**. Rerun the suite against the current checkout when performing a new release verification.

## 19. Project Structure

The main project layout is:

```text
hazina_fin_trans_pipeline/
│
├── config/
│   ├── sources/
│   │   └── sources.yaml
│   └── mappings/
│
├── data/
│   └── sample/
│       ├── hazina_transactions.csv
│       └── source_samples/
│
├── reports/
│
├── logs/
│
├── sql/
│
├── src/
│   ├── database/
│   │   └── connection.py
│   │
│   ├── ingestion/
│   │   ├── adapters/
│   │   ├── ingest_source_file.py
│   │   ├── source_file_reader.py
│   │   └── source_readers.py
│   │
│   ├── mapping/
│   │   ├── mapping_engine.py
│   │   ├── mapping_config_validator.py
│   │   ├── mapping_registry.py
│   │   ├── map_source_execution.py
│   │   ├── source_registry.py
│   │   └── transformations.py
│   │
│   ├── validation/
│   │   ├── validate_transactions.py
│   │   └── validate_source_execution.py
│   │
│   ├── deduplication/
│   │   ├── deduplicate_transactions.py
│   │   └── deduplicate_source_execution.py
│   │
│   ├── orchestration/
│   │   ├── create_pipeline_run.py
│   │   ├── start_source_execution.py
│   │   ├── fail_source_execution.py
│   │   ├── finalize_source_execution.py
│   │   └── finalize_pipeline_run.py
│   │
│   ├── monitoring/
│   │   ├── pipeline_status.py
│   │   └── pdf_security.py
│   │
│   ├── cleaning/
│   ├── transformations/
│   │
│   ├── run_pipeline.py
│   └── run_pipeline_v2.py
│
├── tests/
│
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

The original V1 modules remain available for backward compatibility. The V2 modules provide the multi-source file-based processing lifecycle.

## 20. Known Limitations

The following are known limitations or deferred enhancements, not completed V2 functionality.

### Content-based deduplication

Provider-ID-based identity deduplication is implemented.

Content-based transaction fingerprinting for sources without provider transaction IDs is not implemented.

### MPESA file mappings

The MPESA file source registration is retained, but its mapping configuration is not yet implemented. A representative statement sample is required before creating and validating the mapping.

### API ingestion

API-based ingestion is outside V2 scope.

### Advanced operational features

More advanced retry frameworks, automated recovery, scheduling and expanded observability are potential future improvements, not prerequisites for the current V2 implementation.

## 21. V3 Roadmap

V3 is intended to extend the shared financial data pipeline to API-based financial sources.

Potential integrations include:

- Stripe.
- Plaid.
- Safaricom Daraja.
- Additional financial APIs.

Future API ingestion may require:

- API authentication.
- Pagination.
- Rate-limit handling.
- Incremental synchronization.
- Webhook processing.
- API-specific error handling.
- Checkpoint and synchronization management.

These capabilities are deferred to V3. V2 remains focused on completing and stabilizing the file-based ingestion framework.

## 22. Legacy V1

V1 was the original single-source CSV-to-PostgreSQL implementation.

Its original pipeline modules and reporting functionality remain in the project for backward compatibility and regression testing.

V2 is the primary multi-source financial data pipeline.

## 23. Development Philosophy

Hazina is developed incrementally, with emphasis on correctness, traceability, maintainability and practical financial data engineering principles.

The architecture prioritizes:

- Shared processing components.
- Explicit source configuration.
- Source-specific mapping.
- Preservation of original records.
- Consistent canonical transactions.
- Reliable database transactions.
- Independent file execution.
- Traceable errors and operational metrics.
- Automated testing.
- Simple, maintainable design.

The goal is to build a reusable financial data pipeline that can support additional providers without creating a separate ingestion and processing system for every source.

---

**Project:** Hazina Financial Transactions Pipeline  
**Database:** `hazina_warehouse`  
**Primary technologies:** Python and PostgreSQL  
**Architecture:** Configurable multi-source financial data pipeline  
**Current implementation:** V2 — File-based ingestion