"""Execute the generated SQL (read-only) and store rows or the error."""

from src import db
from src.graph.state import AgentState

EMPTY_RESULT_MESSAGE = (
    "The query ran but returned 0 rows. Re-check the filters, joins, status "
    "values and the spelling of any literal values."
)


def execute_sql_node(state: AgentState) -> AgentState:
    try:
        columns, rows = db.run_query(state["sql"])
    except Exception as exc:  # database error -> let fix_sql try to repair it
        return {**state, "columns": [], "rows": [], "error": str(exc)}

    # An empty result is often a wrong filter, so allow ONE repair attempt.
    if not rows and state.get("retries", 0) == 0:
        return {**state, "columns": columns, "rows": rows, "error": EMPTY_RESULT_MESSAGE}

    return {**state, "columns": columns, "rows": rows, "error": ""}
