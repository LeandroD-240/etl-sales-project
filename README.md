# Sales Data Pipeline

A **data engineering** mini-project designed to practice, in a simple and reproducible way, the fundamentals of an ETL pipeline.

The project simulates a retail scenario in which a company receives a sales CSV file. The data goes through ingestion, validation, cleaning, transformation, and loading before becoming available in PostgreSQL.

> **Level:** Beginner
>
> **Focus:** Practical fundamentals, simple architecture, and reproducible practices

---

## Objective

The goal of this project is not to build a large-scale production data platform, but to **understand how a data engineer approaches the construction of a simple pipeline**.

Throughout the project, there are concepts such as:

- Data ingestion
- Data profiling and inspection
- Validation and data quality rules
- Quarantining invalid records
- Data transformation
- Relational data modeling
- Staging and core layers
- Batch loading
- Transactions
- Idempotency
- Logging
- Automated testing
- Containers and reproducibility

---

## Architecture

```text
                         RAW SOURCE
                       data/raw/sales.csv
                              │
                              ▼
                       ┌─────────────┐
                       │  INGESTION  │
                       └──────┬──────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │ VALIDATION + DQ  │
                    └────────┬─────────┘
                             │
                    ┌────────┴─────────┐
                    ▼                  ▼
             VALID RECORDS         REJECTED
                    │                  │
                    ▼                  ▼
             TRANSFORMATION      data/rejected/
                    │
                    ▼
          data/processed/*.csv
                    │
                    ▼
              SQLAlchemy Core
                    │
                    ▼
               PostgreSQL
              ┌─────┴─────┐
              ▼           ▼
           staging       core
                          │
                 ┌────────┼────────┐
                 ▼        ▼        ▼
             customers  products  sales
```

The pipeline is executed through a single entry point:

```bash
python scripts/run_pipeline.py
```

The orchestrator connects the stages without manual intervention between them.

---

## Technologies

| Technology | Use in the project |
|---|---|
| **Python** | Pipeline logic and automation |
| **Pandas** | Reading, profiling, validation and CSV transformation |
| **SQLAlchemy** | Connections, transactions and SQL operations |
| **PostgreSQL** | Relational target database |
| **Docker** | Reproducible PostgreSQL environment |
| **pytest** | Unit, integration and end-to-end tests |
| **Git / GitHub** | Version control and project distribution |

For staging loads, **PostgreSQL `COPY`** is kept as a database-specific operation where it provides value, while SQLAlchemy is used as the main database access layer.

---

## Dataset

The project uses a synthetic sales dataset with **10,000 records**.

The input file is:

```text
data/raw/sales.csv
```

Expected columns:

| Field | Description |
|---|---|
| `order_id` | Order identifier |
| `order_date` | Sale date |
| `customer_id` | Customer identifier |
| `product_id` | Product identifier |
| `quantity` | Units sold |
| `unit_price` | Unit price |

The dataset intentionally includes problematic records to practice data quality engineering.

The generator (on `scripts/generate_sales.csv`) can reproduce the dataset using a fixed seed, allowing an equivalent scenario to be recreated during development and testing.

---

## Data Quality Rules

The main rules are based on data quality dimensions such as **completeness, uniqueness, validity, and consistency**, together with business-specific rules.

### Schema

The CSV must contain exactly the expected columns:

```text
order_id
order_date
customer_id
product_id
quantity
unit_price
```

### Completeness

Required fields cannot be null or empty.

### Validity

- `order_id`: `O` + 6 digits.
- `customer_id`: `C` + 5 digits.
- `product_id`: `P` + 3 digits.
- `quantity`: integer between `1` and `100`.
- `unit_price`: greater than `0` and less than or equal to `100000`.
- `order_date`: valid date between `2026-01-01` and `2026-06-30`.

### Uniqueness

The business key for a sales line is:

```text
(order_id, product_id)
```

The same combination cannot appear more than once in the accepted dataset.

### Referential Integrity

Customers must belong to the valid customer catalog and products must belong to the valid product catalog.

---

## Quarantine

Records that do not satisfy the validation rules are not silently deleted.

They are separated from the main flow and stored in:

```text
data/rejected/sales_rejected.csv
```

Each rejected record also keeps a `validation_errors` column containing the detected reasons.

The overall behavior is:

```text
raw
 │
 ▼
validation
 ├── valid   ───────► processed
 │
 └── invalid ───────► rejected
```

This allows errors to be audited and preserves the original data for possible reprocessing.

---

## Transformation

Accepted records are written to:

```text
data/processed/sales_validated.csv
```

and then:

```text
data/processed/sales_transformed.csv
```

Main transformations include:

- type conversion
- date normalization
- numeric normalization
- calculation of `total_amount`:

```text
quantity × unit_price = total_amount
```

- addition of lineage metadata such as `source_file` and `ingested_at`
- conformance with the `staging.sales_validated` schema

---

## Database

PostgreSQL contains two conceptual zones:

```text
staging
└── sales_validated

core
├── customers
├── products
└── sales
```

### Staging

Receives the transformed batch before promotion to the main model.

### Core

Contains data considered trusted and structured for downstream consumption.

The `core.sales` table uses:

- A technical key `sale_id`
- The business key `(order_id, product_id)` as a `UNIQUE` constraint
- Foreign keys to `customers` and `products`
- `NOT NULL` and `CHECK` constraints for structural protection

---

## Loading and Idempotency

Loading into PostgreSQL uses transactions.

The conceptual pattern is:

```text
BEGIN
  │
  ├── clear staging
  ├── load batch
  ├── ensure reference data
  ├── promote staging → core
  └── verify
       │
       ▼
     COMMIT
```

If an exception occurs, the transaction is rolled back.

Loading into `core.sales` uses the business key and `ON CONFLICT DO NOTHING` so that processing the same batch again does not duplicate sales.

For example:

```text
1st run → 9,500 new rows
2nd run → 0 new rows
result  → 9,500 total rows
```

This allows the project to practice **idempotency**, an important property for pipelines that may be retried.

---

## Tests

The project uses **pytest**.

The test suite is organized by level:

```text
tests/
├── unit/
├── integration/
├── e2e/
└── regression/
```

The suite covers, among other things:

- Ingestion and schema
- Validation rules
- Multiple validation errors per record
- Duplicates
- `total_amount` transformation
- Input preservation
- Record reconciliation
- Idempotency
- PostgreSQL connectivity
- end-to-end pipeline execution

Run the full test suite:

```bash
pytest -v
```

Tests that require a real database use `TEST_DATABASE_URL`.

---

## Requirements

You need:

- Git
- Python 3.11+ recommended
- Docker

---

## Reproducing the Project from Scratch

### 1. Clone the repository

```bash
git clone https://github.com/LeandroD-240/etl-sales-project.git
cd sales-data-pipeline
```

### 2. Create a virtual environment

Windows / PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create local configuration

Windows / PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux / macOS:

```bash
cp .env.example .env
```

This is not for production environments, so be carefull with `.env`

### 5. Start PostgreSQL

```bash
docker compose up -d --wait
```

Check the service:

```bash
docker compose ps
```

### 6. Run the tests

```bash
pytest -v
```

### 7. Run the complete pipeline

```bash
python scripts/run_pipeline.py
```

### 8. Check PostgreSQL

Open `psql` inside the container:

```bash
docker compose exec postgres psql -U salesuser -d salesdb
```

Check the data:

```sql
SELECT COUNT(*) FROM staging.sales_validated;
SELECT COUNT(*) FROM core.sales;
SELECT COUNT(*) FROM core.customers;
SELECT COUNT(*) FROM core.products;
```

Expected results for the initial batch:

```text
staging.sales_validated → 9,500
core.sales              → 9,500
core.customers          → 500
core.products           → 50
```

---

## Rebuilding PostgreSQL from Scratch

During development, you may want to remove the PostgreSQL volume and recreate the database from scratch:

```bash
docker compose down -v
docker compose up -d --wait
```

> `-v` removes the volume and therefore deletes the current PostgreSQL data. Use it only when you want to rebuild the database from scratch.

Initialization scripts are stored in:

```text
sql/
├── 01_create_schema.sql
└── 02_load_reference_data.sql
```

They are mounted into `/docker-entrypoint-initdb.d/` and executed by the official PostgreSQL image when a new database instance is initialized.

---

## Project Structure

```text
sales-data-pipeline/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── rejected/
│
├── scripts/
│   ├── generate_sales.py
│   └── run_pipeline.py
│
├── src/
│   ├── database.py
│   ├── ingestion.py
│   ├── validation.py
│   ├── transformation.py
│   ├── loading.py
│   └── pipeline.py
│
├── sql/
│   ├── 01_schema.sql
│   └── 02_load_references.sql
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── regression/
│   └── conftest.py
│
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
├── .env.example
└── README.md
```

---

## Development Flow

The project was built around a deliberately simple sequence:

```text
1. Define the problem and data contract
2. Design the PostgreSQL target
3. Generate / receive raw data
4. Inspect and extract the source
5. Validate and quarantine
6. Transform
7. Load into staging and core
8. Orchestrate the ETL
9. Containerize PostgreSQL
10. Test the system
11. Document and reproduce
```

The order can vary in real projects because data modeling, target design, and pipeline implementation often evolve iteratively.

---

## Limitations and Possible Next Steps

This project is intentionally small and focused on fundamentals. It is not intended to represent a large-scale production data platform.

Possible extensions include:

- Scheduling with cron
- Orchestration with Airflow or Prefect
- Incremental loading by date
- Parquet / data lake storage
- dbt for SQL transformations
- Pipeline observability and metrics
- CI/CD with GitHub Actions
- Cloud deployment
- Proper production secret management

A natural next step would be to turn the current `run_pipeline.py` into tasks managed by an orchestrator such as Airflow, where dependencies, retries, and scheduling are represented as a workflow.

---

## Resources for Further Study

### 1. Data Quality — GOV.UK

Practical guidance on data quality dimensions including **completeness, uniqueness, consistency, timeliness, validity, and accuracy**.

https://www.gov.uk/government/publications/the-government-data-quality-framework/the-government-data-quality-framework

### 2. Google Cloud — Data Quality

Documentation covering dimensions such as **freshness, volume, completeness, validity, consistency, accuracy, and uniqueness**, with examples of rules and monitoring.

https://docs.cloud.google.com/knowledge-catalog/docs/auto-data-quality-overview

### 3. AWS Prescriptive Guidance — ETL Pipeline

An example of an incremental ETL pipeline architecture showing how source data, transformations, and a target system can be connected.

https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/build-an-etl-service-pipeline-to-load-data-incrementally-from-amazon-s3-to-amazon-redshift-using-aws-glue.html

### 4. PostgreSQL — Official Tutorial

An introduction to relational databases, SQL, tables, joins, foreign keys, and transactions.

https://www.postgresql.org/docs/current/tutorial.html

### 5. SQLAlchemy — Unified Tutorial

The official guide to learning `Engine`, connections, transactions, SQLAlchemy Core, and later ORM concepts.

https://docs.sqlalchemy.org/en/21/tutorial/

### 6. Apache Airflow — Core Concepts

A useful next step for learning DAGs, tasks, dependencies, retries, and scheduling.

https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/

---

## What This Project Teaches

By the end of the project, the goal is to recognize and explain this pattern:

```text
SOURCE
  ↓
INGEST
  ↓
PROFILE
  ↓
VALIDATE
  ├── PASS ──► TRANSFORM ──► LOAD
  │                              │
  │                              ▼
  │                         PostgreSQL
  │
  └── FAIL ──► QUARANTINE
```

Most importantly, you should be able to explain what responsibility each stage has and why it is separated from the others.

---

## Note

This is a practice project.
