from sqlalchemy.dialects import postgresql

from src.database import database_url
from src.load import core_sales


def test_database_url_reads_environment(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_DRIVER", "postgresql+psycopg")
    monkeypatch.setenv("POSTGRES_USER", "test_user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test_password")
    monkeypatch.setenv("POSTGRES_HOST", "db.example")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    monkeypatch.setenv("POSTGRES_DB", "test_db")

    url = database_url()

    assert url.drivername == "postgresql+psycopg"
    assert url.username == "test_user"
    assert url.host == "db.example"
    assert url.port == 5433
    assert url.database == "test_db"


def test_core_sales_metadata_matches_expected_schema() -> None:
    assert core_sales.schema == "core"
    assert list(core_sales.c.keys()) == [
        "sale_id",
        "order_id",
        "order_date",
        "customer_id",
        "product_id",
        "quantity",
        "unit_price",
        "total_amount",
        "source_file",
        "loaded_at",
    ]


def test_postgresql_dialect_is_available() -> None:
    assert postgresql.dialect().name == "postgresql"
