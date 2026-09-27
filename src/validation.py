import re
from datetime import date
from pathlib import Path
from typing import Tuple

import pandas as pd

ORDER_RE = re.compile(r"^O\d{6}$")
CUSTOMER_RE = re.compile(r"^C\d{5}$")
PRODUCT_RE = re.compile(r"^P\d{3}$")

EXPECTED_COLUMNS = [
    "order_id",
    "order_date",
    "customer_id",
    "product_id",
    "quantity",
    "unit_price",
]

START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 6, 30)
VALID_CUSTOMERS = {f"C{i:05d}" for i in range(1, 501)}
VALID_PRODUCTS = {f"P{i:03d}" for i in range(1, 51)}


class ValidationError(Exception):
    """Raised when the validation input cannot be processed safely."""


def _add_reason(errors: list[list[str]], mask: pd.Series, reason: str) -> None:
    """Append a reason to every row where mask is True."""
    for position in mask[mask].index:
        errors[position].append(reason)


def validate_and_clean(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Validate raw sales and return (clean_valid_rows, quarantined_rows).

    Validation never modifies the source DataFrame. Valid rows are cleaned and
    typed for downstream transformation. Invalid rows remain in their raw form
    and receive a semicolon-separated list of rejection reasons.
    """
    if list(df.columns) != EXPECTED_COLUMNS:
        raise ValidationError(
            f"Unexpected columns. Expected {EXPECTED_COLUMNS}, got {list(df.columns)}"
        )

    work = df.copy()

    # Lightweight normalization: remove accidental surrounding whitespace.
    # This is safe because it does not invent or reinterpret business values.
    for column in EXPECTED_COLUMNS:
        work[column] = work[column].astype(str).str.strip()

    errors: list[list[str]] = [[] for _ in range(len(work))]

    # Completeness.
    for column in EXPECTED_COLUMNS:
        _add_reason(errors, work[column].eq(""), f"missing_{column}")

    # Identifier format + domain checks.
    order_format_invalid = ~work["order_id"].str.fullmatch(ORDER_RE.pattern, na=False)
    customer_format_invalid = ~work["customer_id"].str.fullmatch(CUSTOMER_RE.pattern, na=False)
    product_format_invalid = ~work["product_id"].str.fullmatch(PRODUCT_RE.pattern, na=False)

    _add_reason(errors, order_format_invalid, "invalid_order_id")
    _add_reason(errors, customer_format_invalid, "invalid_customer_id_format")
    _add_reason(errors, product_format_invalid, "invalid_product_id_format")

    _add_reason(
        errors,
        work["customer_id"].ne("") & ~work["customer_id"].isin(VALID_CUSTOMERS),
        "unknown_customer_id",
    )
    _add_reason(
        errors,
        work["product_id"].ne("") & ~work["product_id"].isin(VALID_PRODUCTS),
        "unknown_product_id",
    )

    # Date validity and business range.
    parsed_dates = pd.to_datetime(work["order_date"], format="%Y-%m-%d", errors="coerce")
    invalid_date = (
        work["order_date"].ne("")
        & (
            parsed_dates.isna()
            | (parsed_dates.dt.date < START_DATE)
            | (parsed_dates.dt.date > END_DATE)
        )
    )
    _add_reason(errors, invalid_date, "invalid_order_date")

    # Numeric validity and business ranges.
    quantity_numeric = pd.to_numeric(work["quantity"], errors="coerce")
    invalid_quantity = (
        work["quantity"].ne("")
        & (
            quantity_numeric.isna()
            | (quantity_numeric % 1 != 0)
            | (quantity_numeric < 1)
            | (quantity_numeric > 100)
        )
    )
    _add_reason(errors, invalid_quantity, "invalid_quantity")

    price_numeric = pd.to_numeric(work["unit_price"], errors="coerce")
    invalid_price = (
        work["unit_price"].ne("")
        & (
            price_numeric.isna()
            | (price_numeric <= 0)
            | (price_numeric > 100000)
        )
    )
    _add_reason(errors, invalid_price, "invalid_unit_price")

    # Uniqueness of the business key. Keep the first occurrence and quarantine
    # only subsequent copies. This preserves a legitimate first row while
    # preventing duplicate sales lines from flowing downstream.
    duplicate_key = (
        work["order_id"].ne("")
        & work["product_id"].ne("")
        & work.duplicated(subset=["order_id", "product_id"], keep="first")
    )
    _add_reason(errors, duplicate_key, "duplicate_order_product")

    reason_series = pd.Series(
        [";".join(row_errors) for row_errors in errors], index=work.index
    )

    valid_mask = reason_series.eq("")

    # Clean and type valid rows only. Invalid rows retain their raw values for
    # audit/reprocessing rather than being silently altered or discarded.
    clean = work.loc[valid_mask].copy()
    clean["order_date"] = parsed_dates.loc[valid_mask].dt.date
    clean["quantity"] = quantity_numeric.loc[valid_mask].astype(int)
    clean["unit_price"] = price_numeric.loc[valid_mask].round(2)

    rejected = work.loc[~valid_mask].copy()
    rejected["validation_errors"] = reason_series.loc[~valid_mask]

    return clean.reset_index(drop=True), rejected.reset_index(drop=True)


def write_validation_outputs(
    valid_df: pd.DataFrame,
    rejected_df: pd.DataFrame,
    root: str | Path,
) -> tuple[Path, Path]:
    """Persist clean valid rows and quarantined rows without touching raw data."""
    project_root = Path(root)
    processed_dir = project_root / "data" / "processed"
    rejected_dir = project_root / "data" / "rejected"
    processed_dir.mkdir(parents=True, exist_ok=True)
    rejected_dir.mkdir(parents=True, exist_ok=True)

    valid_path = processed_dir / "sales_validated.csv"
    rejected_path = rejected_dir / "sales_rejected.csv"

    valid_df.to_csv(valid_path, index=False)
    rejected_df.to_csv(rejected_path, index=False)

    return valid_path, rejected_path