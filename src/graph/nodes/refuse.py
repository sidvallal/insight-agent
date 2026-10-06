"""Politely decline questions that are not about the database."""

from src.graph.state import AgentState

MESSAGE = (
    "I can only answer questions about the e-commerce database "
    "(orders, customers, products, sellers, payments and reviews). "
    "Please ask a data question."
)


def refuse_node(state: AgentState) -> AgentState:
    return {**state, "sql": "", "rows": [], "columns": [], "error": "", "answer": MESSAGE}
