"""Human approval for expensive queries (uses LangGraph interrupt)."""

from langgraph.types import interrupt

from src import config, gateway
from src.graph.state import AgentState

CANCELLED_MESSAGE = "Okay, I did not run that query."


def cost_check_node(state: AgentState) -> AgentState:
    cost = gateway.estimate_cost(state["sql"])

    # Unknown cost (for example invalid SQL) goes straight to execution,
    # where the normal error / repair loop handles it.
    if cost is None or cost <= config.APPROVAL_COST_THRESHOLD:
        return {**state, "approved": True}

    decision = interrupt({
        "type": "approval_needed",
        "sql": state["sql"],
        "estimated_cost": cost,
        "threshold": config.APPROVAL_COST_THRESHOLD,
    })
    return {**state, "approved": bool(decision)}


def cancelled_node(state: AgentState) -> AgentState:
    return {**state, "sql": "", "rows": [], "columns": [], "error": "", "answer": CANCELLED_MESSAGE}