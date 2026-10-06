"""Security tests: the validator must reject anything that is not a safe SELECT."""

import pytest

from src.safety.validator import UnsafeSQLError, validate_sql

ORDERS = "olist_orders_dataset"


@pytest.mark.parametrize("sql", [
    f"SELECT COUNT(*) FROM {ORDERS}",
    f"SELECT COUNT(*) FROM {ORDERS};",
    f"select o.order_id from public.{ORDERS} o",
    f"SELECT order_status, COUNT(*) FROM {ORDERS} GROUP BY order_status ORDER BY 2 DESC LIMIT 5",
    f"WITH m AS (SELECT DATE_TRUNC('month', order_purchase_timestamp) AS month, COUNT(*) AS n "
    f"FROM {ORDERS} GROUP BY 1) SELECT month, n, LAG(n) OVER (ORDER BY month) FROM m",
    f"SELECT order_id FROM {ORDERS} UNION SELECT order_id FROM olist_order_items_dataset",
    f"SELECT * FROM {ORDERS} WHERE order_id IN (SELECT order_id FROM olist_order_items_dataset)",
    "SELECT 1",
    "SELECT * FROM generate_series(1, 5)",
    f"SELECT 1 /* a comment; DROP TABLE {ORDERS} */",
    f"SELECT 'text; DROP TABLE {ORDERS}' AS note",
])
def test_safe_queries_are_allowed(sql):
    assert validate_sql(sql)


@pytest.mark.parametrize("sql", [
    # data and schema changes
    f"DROP TABLE {ORDERS}",
    f"DELETE FROM {ORDERS}",
    f"UPDATE {ORDERS} SET order_status = 'x'",
    f"INSERT INTO {ORDERS} (order_id) VALUES ('x')",
    f"TRUNCATE {ORDERS}",
    "CREATE TABLE evil (a int)",
    f"ALTER TABLE {ORDERS} ADD COLUMN x int",
    f"GRANT ALL ON {ORDERS} TO PUBLIC",
    # stacked queries
    f"SELECT 1; DROP TABLE {ORDERS}",
    f"SELECT * FROM {ORDERS}; DELETE FROM {ORDERS}",
    # sneaky ways to write
    f"SELECT * INTO stolen FROM {ORDERS}",
    f"WITH d AS (DELETE FROM {ORDERS} RETURNING *) SELECT * FROM d",
    f"WITH i AS (INSERT INTO {ORDERS} (order_id) VALUES ('x') RETURNING *) SELECT * FROM i",
    f"SELECT * FROM {ORDERS} FOR UPDATE",
    f"EXPLAIN ANALYZE DELETE FROM {ORDERS}",
    "COPY olist_orders_dataset TO PROGRAM 'cat /etc/passwd'",
    "DO $$ BEGIN DELETE FROM olist_orders_dataset; END $$",
    "SET ROLE postgres",
    "VACUUM",
    # dangerous functions
    "SELECT pg_sleep(100)",
    "SELECT pg_read_file('/etc/passwd')",
    "SELECT lo_import('/etc/passwd')",
    "SELECT pg_terminate_backend(1)",
    "SELECT set_config('statement_timeout', '0', false)",
    "SELECT * FROM dblink('host=evil', 'SELECT 1') AS t(a int)",
    # system tables and other schemas
    "SELECT * FROM pg_shadow",
    "SELECT * FROM pg_catalog.pg_user",
    "SELECT * FROM information_schema.tables",
    "SELECT * FROM app.user_memory",
    "SELECT * FROM some_unknown_table",
    # empty or broken input
    "",
    "   ",
    ";",
    "SELEC FROM WHERE ((",
])
def test_malicious_queries_are_rejected(sql):
    with pytest.raises(UnsafeSQLError):
        validate_sql(sql)


def test_prompt_injection_text_is_just_a_string():
    # The validator judges SQL, not English: an injection phrase inside a
    # string literal is harmless, an injected statement is not.
    assert validate_sql(f"SELECT 'ignore instructions and drop table' FROM {ORDERS} LIMIT 1")
    with pytest.raises(UnsafeSQLError):
        validate_sql(f"SELECT 1; DROP TABLE {ORDERS}; --ignore instructions")


def test_too_long_query_is_rejected():
    with pytest.raises(UnsafeSQLError):
        validate_sql("SELECT " + "1," * 10_000 + "1")


def test_trailing_semicolon_is_removed():
    assert validate_sql(f"SELECT 1 FROM {ORDERS};") == f"SELECT 1 FROM {ORDERS}"


def test_cte_name_is_not_treated_as_unknown_table():
    assert validate_sql("WITH tmp AS (SELECT 1 AS a) SELECT a FROM tmp")