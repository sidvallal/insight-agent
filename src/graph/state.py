"""State shared by all nodes of the LangGraph workflow."""

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    question: str
    route: str                      # "SQL question" | "Follow-up" | "Out of scope"
    schema_context: list[dict]      # retrieved table descriptions
    example_context: list[dict]     # retrieved question/SQL examples
    exclude_example_ids: list[str]  # examples that must not be retrieved (evaluation)
    sql: str
    columns: list[str]
    rows: list[list[Any]]
    error: str
    retries: int
    answer: str
