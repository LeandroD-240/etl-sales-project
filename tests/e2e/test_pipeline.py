from pathlib import Path

import pandas as pd

from src.pipeline import run_pipeline


def test_pipeline_runs_end_to_end_without_database(project_with_small_raw_csv: Path, monkeypatch) -> None:
    def fake_load_sales(path):
        transformed = pd.read_csv(path)
        return len(transformed), len(transformed), len(transformed)

    monkeypatch.setattr("src.pipeline.load_sales", fake_load_sales)

    result = run_pipeline(project_with_small_raw_csv)

    assert result.raw_rows == 4
    assert result.valid_rows == 3
    assert result.rejected_rows == 1
    assert result.transformed_rows == 3
    assert result.staging_rows == 3
    assert result.inserted_rows == 3
    assert result.core_total_rows == 3
