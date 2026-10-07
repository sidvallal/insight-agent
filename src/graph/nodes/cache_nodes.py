"""Answer cache nodes (only used when the graph is built with use_cache=True)."""

from src import cache
from src.graph.state import AgentState

MAX_CACHED_ROWS = 5000
FIELDS = ("sql", "columns", "rows", "row_count", "answer", "chart")


def cache_lookup_node(state: AgentState) -> AgentState:
    hit = cache.get(cache.make_key(state["question"], state.get("memory_context", "")))
    if hit is None:
        return {**state, "cache_hit": False}
    return {**state, **hit, "cache_hit": True, "error": ""}


def cache_store_node(state: AgentState) -> AgentState:
    if not state.get("error") and state.get("rows") and state.get("row_count", 0) <= MAX_CACHED_ROWS:
        key = cache.make_key(state["question"], state.get("memory_context", ""))
        cache.put(key, {field: state.get(field) for field in FIELDS})
    return state