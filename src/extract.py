from pathlib import Path
import pandas as pd

EXPECTED_COLUMNS = [
    "order_id",
    "order_date",
    "customer_id",
    "product_id",
    "quantity",
    "unit_price",
]


class IngestionError(Exception):
    """Raised when the raw source cannot be ingested safely."""


def ingest_sales(path: str | Path) -> pd.DataFrame:
    """Read the raw sales CSV without applying business transformations.

    Values are initially loaded as strings so that the raw representation is
    preserved for the validation stage. The ingestion layer only checks that
    the file exists and that its header matches the expected contract.
    """
    source = Path(path)
    if not source.exists():
        raise IngestionError(f"Source file does not exist: {source}")

    if not source.is_file():
        raise IngestionError(f"Source path is not a file: {source}")

    try:
        df = pd.read_csv(
            source,
            dtype=str,
            keep_default_na=False,
            na_filter=False,
        )
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise IngestionError(f"Could not read CSV: {source}") from exc

    actual_columns = list(df.columns)
    if actual_columns != EXPECTED_COLUMNS:
        raise IngestionError(
            "Unexpected CSV schema. "
            f"Expected {EXPECTED_COLUMNS}, got {actual_columns}"
        )

    return df