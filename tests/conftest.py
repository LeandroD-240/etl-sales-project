from pathlib import Path

import pandas as pd
import pytest

RAW_COLUMNS = [
    "order_id",
    "order_date",
    "customer_id",
    "product_id",
    "quantity",
    "unit_price",
]


# Reusable data and structures for unit tests. These fixtures are not used by the pipeline itself, but are used by the unit tests in this project.
@pytest.fixture
def valid_sales_df() -> pd.DataFrame:
    """Small deterministic valid dataset for unit tests."""
    return pd.DataFrame(
        [
            ["O100001", "2026-01-15", "C00001", "P001", "2", "10.50"],
            ["O100002", "2026-02-20", "C00002", "P002", "3", "25.00"],
        ],
        columns=RAW_COLUMNS,
    )


@pytest.fixture
def project_with_small_raw_csv(tmp_path: Path) -> Path:
    """Create the minimum project layout needed by run_pipeline."""
    raw_dir = tmp_path / "data" / "raw"
    raw_dir.mkdir(parents=True)

    raw_df = pd.DataFrame(
        [
            ["O100001", "2026-01-15", "C00001", "P001", "2", "10.50"],
            ["O100002", "2026-02-20", "C00002", "P002", "3", "25.00"],
            ["O100003", "2026-03-03", "C00003", "P003", "1", "7.25"],
            ["O100004", "2026-03-03", "", "P004", "1", "8.00"],
        ],
        columns=RAW_COLUMNS,
    )
    raw_df.to_csv(raw_dir / "sales.csv", index=False)
    return tmp_path
