from datetime import datetime, timezone

import pandas as pd
import pytest

from src.transform import INPUT_COLUMNS, OUTPUT_COLUMNS, TransformationError, transform_sales


def test_transform_sales_calculates_total_and_lineage(valid_sales_df: pd.DataFrame) -> None:
    ingested_at = datetime(2026, 1, 15, 12, 30, tzinfo=timezone.utc)

    result = transform_sales(
        valid_sales_df,
        source_file="/project/data/raw/sales.csv",
        ingested_at=ingested_at,
    )

    assert list(result.columns) == OUTPUT_COLUMNS
    assert result.loc[0, "quantity"] == 2
    assert result.loc[0, "unit_price"] == 10.50
    assert result.loc[0, "total_amount"] == 21.00
    assert result.loc[1, "total_amount"] == 75.00
    assert result["source_file"].eq("sales.csv").all()
    assert result["ingested_at"].eq(ingested_at.isoformat()).all()


def test_transform_sales_rejects_empty_input() -> None:
    df = pd.DataFrame(columns=INPUT_COLUMNS)

    with pytest.raises(TransformationError, match="empty"):
        transform_sales(df, source_file="sales.csv")


def test_transform_sales_rejects_unexpected_schema() -> None:
    df = pd.DataFrame({"order_id": ["O100001"]})

    with pytest.raises(TransformationError, match="Unexpected input columns"):
        transform_sales(df, source_file="sales.csv")


def test_transform_sales_rejects_duplicate_business_key(valid_sales_df: pd.DataFrame) -> None:
    duplicate_df = pd.concat([valid_sales_df, valid_sales_df.iloc[[0]]], ignore_index=True)

    with pytest.raises(TransformationError, match="Business key"):
        transform_sales(duplicate_df, source_file="sales.csv")


def test_transform_sales_preserves_input_dataframe(valid_sales_df: pd.DataFrame) -> None:
    original = valid_sales_df.copy(deep=True)

    transform_sales(valid_sales_df, source_file="sales.csv")

    pd.testing.assert_frame_equal(valid_sales_df, original)
