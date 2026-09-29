import logging
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.extract import ingest_sales
from src.load import load_sales
from src.transform import transform_sales, write_transformation_output
from src.validation import validate_and_clean, write_validation_outputs


@dataclass(frozen=True)
class PipelineResult:
    """Summary returned after a successful pipeline execution."""

    raw_rows: int
    valid_rows: int
    rejected_rows: int
    transformed_rows: int
    staging_rows: int | None
    inserted_rows: int | None
    core_total_rows: int | None
    # load_executed: bool


LOGGER = logging.getLogger("sales_pipeline")


def _configure_logging() -> None:
    """Configure concise console logging for a CLI execution."""
    if LOGGER.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False


def run_pipeline(root: str | Path) -> PipelineResult:
    """Run the complete sales ETL pipeline as one controlled workflow.

    The normal production path is:

        raw CSV -> ingestion -> validation/quarantine -> transformation -> load

    ``load_to_database=False`` is a development/testing mode that executes all
    file-based ETL stages but deliberately stops before PostgreSQL. No prompt
    or manual decision is required in either mode.
    """
    _configure_logging()

    project_root = Path(root).resolve()
    raw_path = project_root / "data" / "raw" / "sales.csv"
    validated_path = project_root / "data" / "processed" / "sales_validated.csv"
    transformed_path = project_root / "data" / "processed" / "sales_transformed.csv"

    started = time.perf_counter()

    LOGGER.info("=== SALES ETL PIPELINE ===")
    LOGGER.info(f"Project root: {project_root}")
    LOGGER.info("Starting pipeline")

    # ------------------------------------------------------------------
    # 1. Extract / Ingest
    # ------------------------------------------------------------------
    stage_started = time.perf_counter()
    LOGGER.info(f"[1/4] Ingesting raw source: {raw_path.relative_to(project_root)}")

    raw_df = ingest_sales(raw_path)
    timer = time.perf_counter() - stage_started

    LOGGER.info(
        f"Ingestion complete: {len(raw_df):,} rows in {timer:.2f}s",
    )

    # ------------------------------------------------------------------
    # 2. Validate + quarantine
    # ------------------------------------------------------------------
    stage_started = time.perf_counter()
    LOGGER.info("[2/4] Validating and quarantining invalid records")

    valid_df, rejected_df = validate_and_clean(raw_df)
    valid_path, rejected_path = write_validation_outputs(
        valid_df,
        rejected_df,
        project_root,
    )

    if len(valid_df) + len(rejected_df) != len(raw_df):
        raise RuntimeError(
            "Validation accounting error: valid + rejected rows do not equal raw rows."
        )

    timer = time.perf_counter() - stage_started

    validation_rate = len(valid_df) / len(raw_df) if len(raw_df) else 0.0
    LOGGER.info(
        f"Validation complete: {len(valid_df):,} valid | {len(rejected_df):,} rejected | {(validation_rate * 100):.2f}% accepted in {timer:.2f}s"
    )
    LOGGER.info(f"Validated output: {valid_path.relative_to(project_root)}")
    LOGGER.info(f"Rejected output: {rejected_path.relative_to(project_root)}")

    # ------------------------------------------------------------------
    # 3. Transform
    # ------------------------------------------------------------------
    stage_started = time.perf_counter()
    LOGGER.info("[3/4] Transforming validated records")

    validated_for_transform = pd.read_csv(
        validated_path,
        dtype={
            "order_id": str,
            "order_date": str,
            "customer_id": str,
            "product_id": str,
            "quantity": "int64",
            "unit_price": "float64",
        },
    )

    transformed_df = transform_sales(
        validated_for_transform,
        source_file=raw_path,
    )
    transformed_output = write_transformation_output(
        transformed_df,
        project_root,
    )

    if len(transformed_df) != len(valid_df):
        raise RuntimeError(
            "Transformation accounting error: transformed rows do not match valid rows."
        )

    timer = time.perf_counter() - stage_started

    LOGGER.info(
        f"Transformation complete: {len(transformed_df):,} rows in {timer:.2f}s",
    )
    LOGGER.info(f"Transformed output: {transformed_output.relative_to(project_root)}")

    # ------------------------------------------------------------------
    # 4. Load
    # ------------------------------------------------------------------
    staging_rows: int | None = None
    inserted_rows: int | None = None
    core_total_rows: int | None = None

    stage_started = time.perf_counter()
    LOGGER.info("[4/4] Loading batch into PostgreSQL")

    staging_rows, inserted_rows, core_total_rows = load_sales(transformed_path)

    if staging_rows != len(transformed_df):
        raise RuntimeError(
            "Load accounting error: staging row count does not match transformed rows."
        )
        
    timer = time.perf_counter() - stage_started

    LOGGER.info(
        f"Load complete: {staging_rows:,} staging | {inserted_rows:,} inserted into core | {core_total_rows:,} total core rows in {timer:.2f}s",
    )

    return PipelineResult(
        raw_rows=len(raw_df),
        valid_rows=len(valid_df),
        rejected_rows=len(rejected_df),
        transformed_rows=len(transformed_df),
        staging_rows=staging_rows,
        inserted_rows=inserted_rows,
        core_total_rows=core_total_rows,
        # load_executed=load_to_database,
    )
