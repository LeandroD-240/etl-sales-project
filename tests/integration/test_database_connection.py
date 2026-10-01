import os

import pytest
from sqlalchemy import create_engine, text


@pytest.mark.db
def test_postgresql_connection_smoke() -> None:
    """Run only against an explicitly configured disposable test database."""
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            assert conn.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        engine.dispose()
