"""Start-of-turn node: reset per-turn fields and load the user's saved preferences."""

from src import memory
from src.graph.state import AgentState


def load_context_node(state: AgentState) -> AgentState:
    # With a checkpointer the state survives between turns, so everything that
    # belongs to ONE turn must be reset here.
    fresh = {
        **state,
        "user_question": state["question"],
        "route": "",
        "sql": "",
        "columns": [],
        "rows": [],
        "row_count": 0,
        "truncated": False,
        "error": "",
        "retries": 0,
        "approved": True,
        "answer": "",
        "chart": None,
        "cache_hit": False,
        "schema_context": [],
        "example_context": [],
        "memory_context": "",
    }

    user_id = state.get("user_id")
    if user_id:
        try:
            fresh["memory_context"] = memory.format_for_prompt(memory.list_memories(user_id))
        except Exception:   # memory is optional: never block a question because of it
            pass
    return fresh