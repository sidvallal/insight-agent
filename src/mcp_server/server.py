"""MCP server: the single, controlled gateway between the agent and the database.

Run it by hand to inspect it:
    python -m src.mcp_server.server

Tools:
    list_tables()            -> names of the tables the agent may query
    describe_schema(table)   -> columns, types and nullability of one table
    run_query(sql)           -> validate the SQL, run it read-only, return rows as JSON
"""

import json

from mcp.server.fastmcp import FastMCP
from sqlalchemy import text

from src import config, db
from src.safety.validator import UnsafeSQLError

mcp = FastMCP("insight-agent-db", log_level="WARNING")


@mcp.tool()
def list_tables() -> str:
    """List the tables that can be queried."""
    return json.dumps(sorted(config.ALLOWED_TABLES))


@mcp.tool()
def describe_schema(table_name: str) -> str:
    """Describe the columns of one table (name, data type, nullable)."""
    table = table_name.strip().lower()
    if table not in config.ALLOWED_TABLES:
        return json.dumps({"ok": False, "error": f"Unknown table: {table_name}"})

    query = text(
        "SELECT column_name, data_type, is_nullable "
        "FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = :table "
        "ORDER BY ordinal_position"
    )
    with db.get_engine().connect() as connection:
        rows = connection.execute(query, {"table": table}).fetchall()

    columns = [{"name": r[0], "type": r[1], "nullable": r[2] == "YES"} for r in rows]
    return json.dumps({"ok": True, "table": table, "columns": columns})


@mcp.tool()
def run_query(sql: str) -> str:
    """Validate a SQL query and run it read-only. Returns JSON: ok, columns, rows, truncated or error."""
    try:
        result = db.run_guarded_query(sql)
    except UnsafeSQLError as exc:
        return json.dumps({"ok": False, "error": f"Query rejected: {exc}"})
    except Exception as exc:  # database error: send the message back so the SQL can be repaired
        return json.dumps({"ok": False, "error": str(exc)})

    return json.dumps(
        {"ok": True, "columns": result.columns, "rows": result.rows, "truncated": result.truncated}
    )

@mcp.tool()
def explain_query(sql: str) -> str:
    """Estimate how expensive a query is (planner cost) without running it. Returns JSON: total_cost or null."""
    return json.dumps({"total_cost": db.estimate_cost(sql)})


if __name__ == "__main__":
    mcp.run()  # stdio transport