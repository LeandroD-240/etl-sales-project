from pathlib import Path

import pandas as pd
import pytest

from src.extract import EXPECTED_COLUMNS, IngestionError, ingest_sales


def test_ingest_sales_reads_csv_and_preserves_raw_values(tmp_path: Path) -> None:
    path = tmp_path / "sales.csv"
    path.write_text(
        "order_id,order_date,customer_id,product_id,quantity,unit_price\n"
        "O100001,2026-01-15,C00001,P001,2,10.50\n",
        encoding="utf-8",
    )

    df = ingest_sales(path)

    assert list(df.columns) == EXPECTED_COLUMNS
    assert len(df) == 1
    assert df.iloc[0]["quantity"] == "2"
    assert df.iloc[0]["unit_price"] == "10.50"
    assert isinstance(df.iloc[0]["quantity"], str)


def test_ingest_sales_fails_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(IngestionError, match="does not exist"):
        ingest_sales(tmp_path / "missing.csv")


def test_ingest_sales_fails_for_unexpected_schema(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    pd.DataFrame({"order_id": ["O100001"]}).to_csv(path, index=False)

    with pytest.raises(IngestionError, match="Unexpected CSV schema"):
        ingest_sales(path)


def test_ingest_sales_fails_for_directory(tmp_path: Path) -> None:
    path = tmp_path / "sales_dir"
    path.mkdir()

    with pytest.raises(IngestionError, match="is not a file"):
        ingest_sales(path)
