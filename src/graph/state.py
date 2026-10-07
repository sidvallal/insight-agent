"""State shared by all nodes of the LangGraph workflow."""

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    # input
    question: str                   # the question being answered (rewritten for follow-ups)
    user_question: str              # exactly what the user typed
    user_id: str                    # enables long-term memory when set
    exclude_example_ids: list[str]  # examples that must not be retrieved (evaluation)

    # routing and context
    route: str                      # "SQL question" | "Follow-up" | "Out of scope" | "Memory"
    history: list[dict]             # previous turns of this conversation thread
    memory_context: str             # the user's saved preferences
    schema_context: list[dict]      # retrieved table descriptions
    example_context: list[dict]     # retrieved question/SQL examples

    # SQL and result
    sql: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int                  # real number of rows (rows may be shortened in the state)
    error: str
    retries: int
    approved: bool

    # output
    answer: str
    chart: dict | None
    cache_hit: bool