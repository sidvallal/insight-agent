"""Save something the user asked us to remember."""

from src import memory
from src.graph.state import AgentState


def save_memory_node(state: AgentState) -> AgentState:
    content = memory.extract_memory(state["user_question"])
    try:
        memory.add_memory(state["user_id"], content)
        answer = f"Got it. I'll remember: {content}"
    except Exception as exc:
        answer = f"I could not save that preference: {exc}"
    return {**state, "sql": "", "rows": [], "columns": [], "error": "", "answer": answer}