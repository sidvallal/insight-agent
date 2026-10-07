"""Execute the generated SQL through the safe gateway and store rows or the error."""

from src import config, gateway
from src.graph.state import AgentState

EMPTY_RESULT_MESSAGE = (
    "The query ran but returned 0 rows. Re-check the filters, joins, status "
    "values and the spelling of any literal values."
)


def execute_sql_node(state: AgentState) -> AgentState:
    try:
        columns, rows = gateway.run_agent_query(state["sql"])
    except Exception as exc:  # rejected or failed query -> let fix_sql try to repair it
        return {**state, "columns": [], "rows": [], "row_count": 0, "error": str(exc)}

    row_count = len(rows)
    truncated = row_count >= config.MAX_ROWS   # the gateway stops fetching at MAX_ROWS
    if config.STATE_MAX_ROWS and row_count > config.STATE_MAX_ROWS:
        rows = rows[: config.STATE_MAX_ROWS]   # keep checkpoints small

    # An empty result is often a wrong filter, so allow ONE repair attempt.
    if not row_count and state.get("retries", 0) == 0:
        return {**state, "columns": columns, "rows": rows, "row_count": 0, "error": EMPTY_RESULT_MESSAGE}

    return {**state, "columns": columns, "rows": rows, "row_count": row_count, "truncated": truncated, "error": ""}