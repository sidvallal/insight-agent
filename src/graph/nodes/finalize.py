"""End-of-turn node: remember this turn so follow-up questions can use it."""

from src import config
from src.graph.state import AgentState


def finalize_node(state: AgentState) -> AgentState:
    if state.get("error") or not state.get("sql"):
        return state

    turn = {
        "user_question": state["user_question"],
        "question": state["question"],
        "sql": state["sql"],
        "answer": state.get("answer", "")[:300],
    }
    history = (state.get("history", []) + [turn])[-config.HISTORY_TURNS:]
    return {**state, "history": history}