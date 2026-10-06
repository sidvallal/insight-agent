"""SQL safety validator (sqlglot).

Only a single, read-only SELECT over the known tables is allowed. This is one
of several layers: the database user is also read-only and every query runs in
a read-only transaction with a timeout, so a bug here is not catastrophic.
"""

import logging

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from src import config

# sqlglot warns when it falls back to a generic "Command"; we reject those anyway.
logging.getLogger("sqlglot").setLevel(logging.ERROR)


class UnsafeSQLError(ValueError):
    """Raised when a query is rejected by the validator."""


# Statements / clauses that can change data, schema, settings or the session.
FORBIDDEN_NODES = tuple(
    getattr(exp, name)
    for name in (
        "Insert", "Update", "Delete", "Merge", "Drop", "Create", "Alter",
        "TruncateTable", "Copy", "Grant", "Command", "Set", "Use", "Transaction",
        "Commit", "Rollback", "Into", "Lock",
    )
    if hasattr(exp, name)
)

FORBIDDEN_FUNCTIONS = {
    "set_config", "current_setting", "query_to_xml", "table_to_xml",
    "database_to_xml", "cursor_to_xml", "txid_current",
}
FORBIDDEN_FUNCTION_PREFIXES = ("pg_", "lo_", "dblink")

SET_OPERATION = getattr(exp, "SetOperation", exp.Union)


def _function_name(node: exp.Func) -> str:
    name = node.name if isinstance(node, exp.Anonymous) else node.sql_name()
    return name.lower()


def validate_sql(sql: str) -> str:
    """Return the SQL (without a trailing semicolon) if it is safe, else raise UnsafeSQLError."""
    if not sql or not sql.strip():
        raise UnsafeSQLError("Empty query.")
    if len(sql) > config.MAX_SQL_LENGTH:
        raise UnsafeSQLError("Query is too long.")

    try:
        statements = [s for s in sqlglot.parse(sql, read="postgres") if s is not None]
    except SqlglotError as exc:
        raise UnsafeSQLError(f"Query could not be parsed: {exc}") from exc

    if len(statements) != 1:
        raise UnsafeSQLError("Only a single SQL statement is allowed.")

    tree = statements[0]
    if isinstance(tree, exp.Subquery):
        tree = tree.unnest()

    if not isinstance(tree, (exp.Select, SET_OPERATION)):
        raise UnsafeSQLError("Only SELECT queries are allowed.")

    for node in tree.walk():
        if isinstance(node, FORBIDDEN_NODES):
            raise UnsafeSQLError(f"Forbidden SQL operation: {type(node).__name__}.")

        if isinstance(node, exp.Func):
            name = _function_name(node)
            if name in FORBIDDEN_FUNCTIONS or name.startswith(FORBIDDEN_FUNCTION_PREFIXES):
                raise UnsafeSQLError(f"Forbidden function: {name}.")

    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}

    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        if not name:            # table-valued function such as generate_series()
            continue
        schema = table.db.lower()
        if schema not in ("", "public"):
            raise UnsafeSQLError(f"Access to schema '{schema}' is not allowed.")
        if name in cte_names and not schema:
            continue
        if name not in config.ALLOWED_TABLES:
            raise UnsafeSQLError(f"Unknown or forbidden table: {name}.")

    return sql.strip().rstrip(";").strip()