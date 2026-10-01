import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import run_pipeline


def main() -> int:
    try:
        result = run_pipeline(ROOT)
    except Exception as exc:
        print(f"PIPELINE FAILED: {exc}")
        return 1

    print("\n=== PIPELINE SUMMARY ===")
    print(f"Raw rows:          {result.raw_rows:,}")
    print(f"Valid rows:        {result.valid_rows:,}")
    print(f"Rejected rows:     {result.rejected_rows:,}")
    print(f"Transformed rows:  {result.transformed_rows:,}")

    print(f"Staging rows:      {result.staging_rows:,}")
    print(f"Inserted to core:  {result.inserted_rows:,}")
    print(f"Core total rows:   {result.core_total_rows:,}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
