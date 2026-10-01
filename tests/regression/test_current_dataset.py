from pathlib import Path

import pandas as pd

from src.extract import EXPECTED_COLUMNS, ingest_sales
from src.validation import validate_and_clean


def test_checked_in_dataset_matches_project_baseline() -> None:
    project_root = Path(__file__).resolve().parents[2]
    raw = ingest_sales(project_root / "data" / "raw" / "sales.csv")
    valid, rejected = validate_and_clean(raw)

    assert len(raw) == 10000
    assert list(raw.columns) == EXPECTED_COLUMNS
    assert len(valid) >= 9000
    assert len(rejected) >= 500
    assert len(valid) + len(rejected) == len(raw)
    assert not valid.duplicated(subset=["order_id", "product_id"]).any()
