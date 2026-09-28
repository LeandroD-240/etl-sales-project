import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL


def database_url() -> URL:
    """Build the PostgreSQL URL from environment variables.

    Keeping configuration here means the loading layer does not care where the
    database lives. With SQLAlchemy, the same engine pattern can be adapted to
    another supported dialect by changing the driver URL.
    """
    return URL.create(
        drivername=os.getenv("DATABASE_DRIVER", "postgresql+psycopg"),
        username=os.getenv("POSTGRES_USER", "salesuser"),
        password=os.getenv("POSTGRES_PASSWORD", "salespassword"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "salesdb"),
    )


def create_database_engine() -> Engine:
    """Create the application's SQLAlchemy Engine.

    pool_pre_ping helps discard stale pooled connections before use. SQLAlchemy
    lazily opens a DB connection when the engine is first used.
    """
    return create_engine(
        database_url(),
        pool_pre_ping=True,
    )