"""Database access: one shared engine and a read-only query helper."""

from datetime import date, datetime, time
from decimal import Decimal
from functools import lru_cache

from sqlalchemy import create_engine, text

from src import config


@lru_cache(maxsize=1)
def get_engine():
    """Return the shared SQLAlchemy engine (created once, with a query timeout)."""
    return create_engine(
        config.database_url(),
        pool_pre_ping=True,
        connect_args={"options": f"-c statement_timeout={config.STATEMENT_TIMEOUT_MS}"},
    )


def to_jsonable(value):
    """Convert PostgreSQL values into JSON-safe Python values."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def run_query(sql: str) -> tuple[list[str], list[list]]:
    """Run SQL inside a read-only transaction and return (columns, rows)."""
    with get_engine().connect() as connection:
        connection = connection.execution_options(postgresql_readonly=True)
        result = connection.execute(text(sql))
        columns = list(result.keys())
        rows = [[to_jsonable(v) for v in row] for row in result.fetchall()]
    return columns, rows
