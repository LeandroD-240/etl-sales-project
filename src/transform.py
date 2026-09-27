from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

INPUT_COLUMNS = [
    "order_id",
    "order_date",
    "customer_id",
    "product_id",
    "quantity",
    "unit_price",
]

OUTPUT_COLUMNS = [
    "order_id",
    "order_date",
    "customer_id",
    "product_id",
    "quantity",
    "unit_price",
    "total_amount",
    "source_file",
    "ingested_at",
]


class TransformationError(Exception):
    """Raised when the validated input cannot be transformed safely."""


def transform_sales(
    valid_df: pd.DataFrame,
    *,
    source_file: str,
    ingested_at: datetime | None = None,
) -> pd.DataFrame:
    """Transform validated sales into the staging-table contract.

    The function assumes validation has already happened. It does not repair
    bad records; it only normalizes the trusted rows, derives total_amount,
    and adds batch-level lineage metadata.
    """
    if list(valid_df.columns) != INPUT_COLUMNS:
        raise TransformationError(
            f"Unexpected input columns. Expected {INPUT_COLUMNS}, "
            f"got {list(valid_df.columns)}"
        )

    if valid_df.empty:
        raise TransformationError("Validated input is empty.")

    work = valid_df.copy()

    # Enforce the destination data types explicitly.
    try:
        work["order_id"] = work["order_id"].astype(str)
        work["customer_id"] = work["customer_id"].astype(str)
        work["product_id"] = work["product_id"].astype(str)
        work["order_date"] = pd.to_datetime(
            work["order_date"], format="%Y-%m-%d", errors="raise"
        ).dt.date
        work["quantity"] = pd.to_numeric(
            work["quantity"], errors="raise"
        ).astype("int16")
        work["unit_price"] = pd.to_numeric(
            work["unit_price"], errors="raise"
        ).round(2)
    except (TypeError, ValueError) as exc:
        raise TransformationError(
            "Validated data could not be converted to the staging types."
        ) from exc

    # Derived business measure required by staging.sales_validated.
    work["total_amount"] = (
        work["quantity"].astype("int64") * work["unit_price"]
    ).round(2)

    # Lineage/batch metadata. ingested_at means the timestamp
    # at which this transformed batch is prepared for staging ingestion.
    batch_timestamp = ingested_at or datetime.now(timezone.utc)
    if batch_timestamp.tzinfo is None:
        batch_timestamp = batch_timestamp.replace(tzinfo=timezone.utc)
    batch_timestamp = batch_timestamp.astimezone(timezone.utc)

    work["source_file"] = Path(source_file).name
    work["ingested_at"] = batch_timestamp.isoformat()

    result = work[OUTPUT_COLUMNS].copy()

    # Contract-level sanity checks before handing data to PostgreSQL.
    if result[["order_id", "customer_id", "product_id"]].isna().any().any():
        raise TransformationError("Identifier columns contain NULL values.")

    if result["quantity"].lt(1).any() or result["quantity"].gt(100).any():
        raise TransformationError("Quantity violates the destination contract.")

    if result["unit_price"].le(0).any() or result["unit_price"].gt(100_000).any():
        raise TransformationError("Unit price violates the destination contract.")

    if result.duplicated(subset=["order_id", "product_id"]).any():
        raise TransformationError(
            "Business key (order_id, product_id) is not unique."
        )

    expected_total = (
        result["quantity"].astype("int64") * result["unit_price"]
    ).round(2)
    if not result["total_amount"].eq(expected_total).all():
        raise TransformationError("total_amount does not match quantity × unit_price.")

    return result


def write_transformation_output(
    transformed_df: pd.DataFrame,
    root: str | Path,
) -> Path:
    """Write the transformed batch for the next database-loading phase."""
    project_root = Path(root)
    processed_dir = project_root / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    output_path = processed_dir / "sales_transformed.csv"
    transformed_df.to_csv(
        output_path,
        index=False,
        float_format="%.2f",
    )
    return output_path
