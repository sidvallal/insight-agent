"""Single entry point the agent uses to read from the database.

DB_ACCESS=mcp    -> through the MCP server (default)
DB_ACCESS=direct -> in-process, same validator and read-only rules (faster, no subprocess)
"""

from src import config, db


def run_agent_query(sql: str) -> tuple[list[str], list[list]]:
    """Run agent-generated SQL safely. Raises an exception with a readable message on failure."""
    if config.DB_ACCESS == "mcp":
        from src.mcp_server.client import get_client

        return get_client().run_query(sql)

    result = db.run_guarded_query(sql)
    return result.columns, result.rows

def estimate_cost(sql: str) -> float | None:
    """Estimated planner cost of agent-generated SQL (None if unknown)."""
    if config.DB_ACCESS == "mcp":
        from src.mcp_server.client import get_client

        return get_client().estimate_cost(sql)
    return db.estimate_cost(sql)