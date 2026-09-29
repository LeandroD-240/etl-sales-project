import csv
from pathlib import Path

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Table,
    TIMESTAMP,
    delete,
    func,
    select,
)
from sqlalchemy.engine import Connection
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.database import create_database_engine

TRANSFORMED_COLUMNS = [
    "order_id",
    "order_date",
    "customer_id",
    "product_id",
    "quantity",
    "unit_price",
    "total_amount",
    "source_file",
    "ingested_at",
]

metadata = MetaData()

# SQLAlchemy Core table objects describe the parts of the target schema used by
# the loading layer. PostgreSQL remains the actual system enforcing the DDL
# constraints defined in sql/schema.sql.
staging_sales = Table(
    "sales_validated",
    metadata,
    Column("order_id", String(7)),
    Column("order_date", Date),
    Column("customer_id", String(6)),
    Column("product_id", String(4)),
    Column("quantity", SmallInteger),
    Column("unit_price", Numeric(12, 2)),
    Column("total_amount", Numeric(14, 2)),
    Column("source_file", String(255)),
    Column("ingested_at", TIMESTAMP(timezone=True)),
    schema="staging",
)

customers = Table(
    "customers",
    metadata,
    Column("customer_id", String(6), primary_key=True),
    schema="core",
)

products = Table(
    "products",
    metadata,
    Column("product_id", String(4), primary_key=True),
    schema="core",
)

core_sales = Table(
    "sales",
    metadata,
    Column("sale_id", BigInteger, primary_key=True),
    Column("order_id", String(7)),
    Column("order_date", Date),
    Column("customer_id", String(6)),
    Column("product_id", String(4)),
    Column("quantity", SmallInteger),
    Column("unit_price", Numeric(12, 2)),
    Column("total_amount", Numeric(14, 2)),
    Column("source_file", String(255)),
    Column("loaded_at", TIMESTAMP(timezone=True)),
    schema="core",
)


def copy_csv_to_staging(conn: Connection, csv_path: str | Path) -> int:
    """Load the transformed CSV into staging using PostgreSQL COPY.

    SQLAlchemy owns the connection and transaction. COPY is a PostgreSQL/psycopg
    capability, so this one operation intentionally uses the underlying DBAPI
    cursor while staying inside SQLAlchemy's transaction boundary.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Transformed file not found: {path}")

    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.reader(source)
        header = next(reader, None)
        if header != TRANSFORMED_COLUMNS:
            raise ValueError(
                "Unexpected transformed schema. "
                f"Expected {TRANSFORMED_COLUMNS}, got {header}"
            )

    # SQLAlchemy's Core API has no database-agnostic equivalent of PostgreSQL
    # COPY, so we deliberately drop one level to the DBAPI for this operation.
    # The outer SQLAlchemy Connection continues to own the transaction.
    dbapi_conn = conn.connection
    with dbapi_conn.cursor() as cursor:
        with cursor.copy(
            """
            COPY staging.sales_validated
                (order_id, order_date, customer_id, product_id,
                 quantity, unit_price, total_amount, source_file, ingested_at)
            FROM STDIN WITH (FORMAT CSV, HEADER TRUE)
            """
        ) as copy:
            with path.open("rb") as csv_file:
                while chunk := csv_file.read(1024 * 1024):
                    copy.write(chunk)

    return int(conn.execute(select(func.count()).select_from(staging_sales)).scalar_one())


def seed_reference_tables(conn: Connection) -> None:
    """Ensure customers and products exist using PostgreSQL-aware SQLAlchemy Core."""
    customer_rows = [{"customer_id": f"C{i:05d}"} for i in range(1, 501)]
    product_rows = [{"product_id": f"P{i:03d}"} for i in range(1, 51)]

    customer_stmt = pg_insert(customers).values(customer_rows).on_conflict_do_nothing(
        index_elements=[customers.c.customer_id]
    )
    product_stmt = pg_insert(products).values(product_rows).on_conflict_do_nothing(
        index_elements=[products.c.product_id]
    )

    conn.execute(customer_stmt)
    conn.execute(product_stmt)


def promote_staging_to_core(conn: Connection) -> tuple[int, int]:
    """Promote the current staging batch into core using SQLAlchemy Core."""
    source = select(
        staging_sales.c.order_id,
        staging_sales.c.order_date,
        staging_sales.c.customer_id,
        staging_sales.c.product_id,
        staging_sales.c.quantity,
        staging_sales.c.unit_price,
        staging_sales.c.total_amount,
        staging_sales.c.source_file,
        staging_sales.c.ingested_at.label("loaded_at"),
    )

    stmt = (
        pg_insert(core_sales)
        .from_select(
            [
                "order_id",
                "order_date",
                "customer_id",
                "product_id",
                "quantity",
                "unit_price",
                "total_amount",
                "source_file",
                "loaded_at",
            ],
            source,
        )
        .on_conflict_do_nothing(
            index_elements=[core_sales.c.order_id, core_sales.c.product_id]
        )
        .returning(core_sales.c.sale_id)
    )

    inserted_ids = conn.execute(stmt).scalars().all()
    inserted_rows = len(inserted_ids)
    core_total_rows = int(conn.execute(select(func.count()).select_from(core_sales)).scalar_one())

    return inserted_rows, core_total_rows


def load_sales(csv_path: str | Path) -> tuple[int, int, int]:
    """Run one atomic batch load through SQLAlchemy Core.

    Returns:
        (staging_rows, inserted_rows, core_total_rows)
    """
    engine = create_database_engine()

    # Engine.begin() gives us one Connection and one transaction. SQLAlchemy
    # commits on successful exit and rolls back automatically on exceptions.
    try:
        with engine.begin() as conn:
            # Staging is the current-batch landing area in this project.
            conn.execute(delete(staging_sales))

            seed_reference_tables(conn)
            staging_rows = copy_csv_to_staging(conn, csv_path)
            inserted_rows, core_total_rows = promote_staging_to_core(conn)

            # if staging_rows != 9500:
            #     raise RuntimeError(
            #         f"Unexpected staging row count: expected 9500, got {staging_rows}"
            #     )

        return staging_rows, inserted_rows, core_total_rows
    finally:
        engine.dispose()