import csv
import random
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

SEED = 42
TOTAL_ROWS = 10000
VALID_ROWS = 9500
START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 6, 30)
OUTPUT = Path(__name__).resolve().parents[0] / "data" / "raw" / "sales.csv"

FIELDS = [
    "order_id",
    "order_date",
    "customer_id",
    "product_id",
    "quantity",
    "unit_price",
]


def random_date(rng: random.Random) -> date:
    span = (END_DATE - START_DATE).days
    return START_DATE + timedelta(days=rng.randint(0, span))


def money(rng: random.Random) -> str:
    value = Decimal(rng.randint(100, 100_000)) / Decimal("100")
    return f"{value:.2f}"


def valid_rows(rng: random.Random, count: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for i in range(1, count + 1):
        rows.append(
            {
                "order_id": f"O{i:06d}",
                "order_date": random_date(rng).isoformat(),
                "customer_id": f"C{rng.randint(1, 500):05d}",
                "product_id": f"P{rng.randint(1, 50):03d}",
                "quantity": str(rng.randint(1, 10)),
                "unit_price": money(rng),
            }
        )
    return rows


def inject_problems(rng: random.Random, rows: list[dict[str, str]]) -> list[dict[str, str]]:
    # 100 exact duplicate rows.
    duplicate_indexes = rng.sample(range(len(rows)), 100)
    bad_rows = [rows[i].copy() for i in duplicate_indexes]

    # 80 rows with missing required values.
    for _ in range(80):
        row = rows[rng.randrange(len(rows))].copy()
        field = rng.choice(["order_date", "customer_id", "product_id", "quantity", "unit_price"])
        row[field] = ""
        bad_rows.append(row)

    # 80 rows with invalid dates.
    invalid_dates = ["2026-02-30", "2026-13-01", "not-a-date", "2025-12-31"]
    for _ in range(80):
        row = rows[rng.randrange(len(rows))].copy()
        row["order_date"] = rng.choice(invalid_dates)
        bad_rows.append(row)

    # 80 rows with unknown customer/product IDs.
    for _ in range(80):
        row = rows[rng.randrange(len(rows))].copy()
        if rng.random() < 0.5:
            row["customer_id"] = f"C{rng.randint(501, 999):05d}"
        else:
            row["product_id"] = f"P{rng.randint(51, 999):03d}"
        bad_rows.append(row)

    # 80 rows with invalid quantities.
    for _ in range(80):
        row = rows[rng.randrange(len(rows))].copy()
        row["quantity"] = rng.choice(["0", "-1", "101", "2.5"])
        bad_rows.append(row)

    # 50 rows with invalid prices.
    for _ in range(50):
        row = rows[rng.randrange(len(rows))].copy()
        row["unit_price"] = rng.choice(["0", "-10.00", "100000.01"])
        bad_rows.append(row)

    # 30 rows with malformed identifiers.
    for _ in range(30):
        row = rows[rng.randrange(len(rows))].copy()
        field = rng.choice(["order_id", "customer_id", "product_id"])
        if field == "order_id":
            row[field] = rng.choice(["ORDER123", "100001", "O123"])
        elif field == "customer_id":
            row[field] = rng.choice(["CUSTOMER1", "C1", "X00123"])
        else:
            row[field] = rng.choice(["PROD1", "P1", "X123"])
        bad_rows.append(row)

    assert len(bad_rows) == TOTAL_ROWS - VALID_ROWS
    return bad_rows


def main() -> None:
    rng = random.Random(SEED)
    base = valid_rows(rng, VALID_ROWS)
    bad = inject_problems(rng, base)
    rows = base + bad
    rng.shuffle(rows)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows):,} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
