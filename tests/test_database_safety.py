"""Integration tests: need a running PostgreSQL (skipped automatically otherwise)."""

import json
import os

import pytest

from src import db
from src.safety.validator import UnsafeSQLError


@pytest.fixture(scope="module", autouse=True)
def database_available():
    try:
        db.run_query("SELECT 1")
    except Exception:
        pytest.skip("PostgreSQL is not available")


def test_guarded_query_returns_rows():
    result = db.run_guarded_query("SELECT 1 AS one")
    assert result.columns == ["one"] and result.rows == [[1]]


def test_row_cap_truncates_large_results():
    result = db.run_guarded_query("SELECT * FROM generate_series(1, 50)", max_rows=10)
    assert len(result.rows) == 10 and result.truncated


def test_row_cap_exact_size_is_not_truncated():
    result = db.run_guarded_query("SELECT * FROM generate_series(1, 10)", max_rows=10)
    assert len(result.rows) == 10 and not result.truncated


def test_validator_blocks_before_the_database():
    with pytest.raises(UnsafeSQLError):
        db.run_guarded_query("DELETE FROM olist_orders_dataset")


def test_database_refuses_writes_even_without_the_validator():
    # Bypass the validator on purpose: the read-only transaction must still stop it.
    with pytest.raises(Exception, match="read-only"):
        db.execute("DELETE FROM olist_orders_dataset")


@pytest.mark.skipif(not os.getenv("DB_RO_USER"), reason="DB_RO_USER is not configured")
def test_agent_connects_as_the_read_only_user():
    result = db.execute("SELECT current_user")
    assert result.rows[0][0] == os.getenv("DB_RO_USER")


@pytest.fixture(scope="module")
def mcp_client():
    from src.mcp_server.client import get_client

    client = get_client()
    yield client
    client.close()


def test_mcp_lists_tables(mcp_client):
    assert "olist_orders_dataset" in mcp_client.list_tables()


def test_mcp_describes_a_table(mcp_client):
    columns = [c["name"] for c in mcp_client.describe_schema("olist_orders_dataset")["columns"]]
    assert "order_id" in columns


def test_mcp_refuses_to_describe_system_tables(mcp_client):
    assert mcp_client.describe_schema("pg_shadow")["ok"] is False


def test_mcp_runs_a_safe_query(mcp_client):
    columns, rows = mcp_client.run_query("SELECT 1 AS one")
    assert columns == ["one"] and rows == [[1]]


def test_mcp_rejects_unsafe_and_broken_queries(mcp_client):
    from src.mcp_server.client import QueryFailed

    with pytest.raises(QueryFailed, match="rejected"):
        mcp_client.run_query("DROP TABLE olist_orders_dataset")
    with pytest.raises(QueryFailed):
        mcp_client.run_query("SELECT missing_column FROM olist_orders_dataset")