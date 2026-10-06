"""Database access: shared engines and query helpers."""

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from functools import lru_cache

from sqlalchemy import create_engine, text

from src import config
from src.safety.validator import validate_sql


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list]
    truncated: bool = False


def _make_engine(readonly: bool):
    return create_engine(
        config.database_url(readonly=readonly),
        pool_pre_ping=True,
        connect_args={"options": f"-c statement_timeout={config.STATEMENT_TIMEOUT_MS}"},
    )


@lru_cache(maxsize=1)
def get_engine():
    """Engine for the agent: uses the read-only DB user when DB_RO_USER is set."""
    return _make_engine(readonly=True)


@lru_cache(maxsize=1)
def get_admin_engine():
    """Engine for setup scripts (create tables, import data, create users)."""
    return _make_engine(readonly=False)


def to_jsonable(value):
    """Convert PostgreSQL values into JSON-safe Python values."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def execute(sql: str, max_rows: int | None = None) -> QueryResult:
    """Run SQL in a read-only transaction; fetch at most max_rows rows."""
    with get_engine().connect() as connection:
        connection = connection.execution_options(postgresql_readonly=True)
        if max_rows is None:
            result = connection.execute(text(sql))
            fetched = result.fetchall()
            truncated = False
        else:
            result = connection.execution_options(stream_results=True).execute(text(sql))
            fetched = result.fetchmany(max_rows + 1)
            truncated = len(fetched) > max_rows
            fetched = fetched[:max_rows]
        columns = list(result.keys())
        rows = [[to_jsonable(v) for v in row] for row in fetched]
    return QueryResult(columns, rows, truncated)


def run_query(sql: str) -> tuple[list[str], list[list]]:
    """Trusted helper (gold SQL, scripts): no validation, no row cap."""
    result = execute(sql)
    return result.columns, result.rows


def run_guarded_query(sql: str, max_rows: int = config.MAX_ROWS) -> QueryResult:
    """Validate the SQL, then run it with a row cap. Raises UnsafeSQLError if rejected."""
    return execute(validate_sql(sql), max_rows=max_rows)