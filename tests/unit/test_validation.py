import pandas as pd
import pytest

from src.validation import EXPECTED_COLUMNS, ValidationError, validate_and_clean


# Try the same rule with different entries to ensure that the validation logic is applied consistently across all rows.
@pytest.mark.parametrize(
    ("column", "value", "expected_reason"),
    [
        ("order_id", "BAD1", "invalid_order_id"),
        ("customer_id", "C99999", "unknown_customer_id"),
        ("product_id", "P999", "unknown_product_id"),
        ("order_date", "2026-02-30", "invalid_order_date"),
        ("order_date", "2027-01-01", "invalid_order_date"),
        ("quantity", "0", "invalid_quantity"),
        ("quantity", "101", "invalid_quantity"),
        ("quantity", "2.5", "invalid_quantity"),
        ("unit_price", "0", "invalid_unit_price"),
        ("unit_price", "100001", "invalid_unit_price"),
    ],
)
def test_validation_rejects_invalid_business_value(
    column: str,
    value: str,
    expected_reason: str,
) -> None:
    row = {
        "order_id": "O100001",
        "order_date": "2026-01-15",
        "customer_id": "C00001",
        "product_id": "P001",
        "quantity": "2",
        "unit_price": "10.50",
    }
    row[column] = value
    df = pd.DataFrame([row], columns=EXPECTED_COLUMNS)

    valid_df, rejected_df = validate_and_clean(df)

    assert valid_df.empty
    assert len(rejected_df) == 1
    assert expected_reason in rejected_df.iloc[0]["validation_errors"]


def test_validation_rejects_missing_required_value() -> None:
    df = pd.DataFrame(
        [["O100001", "2026-01-15", "", "P001", "2", "10.50"]],
        columns=EXPECTED_COLUMNS,
    )

    valid_df, rejected_df = validate_and_clean(df)

    assert valid_df.empty
    assert rejected_df.iloc[0]["validation_errors"] == "missing_customer_id"


def test_validation_accumulates_multiple_errors() -> None:
    df = pd.DataFrame(
        [["BAD", "2026-02-30", "C99999", "P999", "-2", "0"]],
        columns=EXPECTED_COLUMNS,
    )

    valid_df, rejected_df = validate_and_clean(df)

    assert valid_df.empty
    reasons = set(rejected_df.iloc[0]["validation_errors"].split(";"))
    assert {
        "invalid_order_id",
        "unknown_customer_id",
        "unknown_product_id",
        "invalid_order_date",
        "invalid_quantity",
        "invalid_unit_price",
    } <= reasons


def test_validation_detects_duplicate_business_key() -> None:
    df = pd.DataFrame(
        [
            ["O100001", "2026-01-15", "C00001", "P001", "2", "10.50"],
            ["O100001", "2026-01-15", "C00001", "P001", "4", "11.50"],
            ["O100001", "2026-01-15", "C00001", "P002", "4", "11.50"],
        ],
        columns=EXPECTED_COLUMNS,
    )

    valid_df, rejected_df = validate_and_clean(df)

    assert len(valid_df) == 2
    assert len(rejected_df) == 1
    assert rejected_df.iloc[0]["validation_errors"] == "duplicate_order_product"


def test_validation_returns_clean_typed_values_for_valid_rows() -> None:
    df = pd.DataFrame(
        [[" O100001 ", "2026-01-15", "C00001", "P001", "2", "10.50"]],
        columns=EXPECTED_COLUMNS,
    )

    valid_df, rejected_df = validate_and_clean(df)

    assert rejected_df.empty
    assert len(valid_df) == 1
    assert valid_df.iloc[0]["order_id"] == "O100001"
    assert valid_df.iloc[0]["quantity"] == 2
    assert valid_df.iloc[0]["unit_price"] == 10.50


def test_validation_rejects_unexpected_columns() -> None:
    df = pd.DataFrame({"wrong": [1]})

    with pytest.raises(ValidationError, match="Unexpected columns"):
        validate_and_clean(df)
