"""Build and compile the LangGraph Text-to-SQL workflow.

    START -> load_context -> router -+-> refuse -> END                        (out of scope)
                                     +-> save_memory -> END                   ("remember ...")
                                     +-> rewrite_question --+                 (follow-up)
                                     |                       v
                                     +-----------------> [cache_lookup] -- hit --> finalize
                                                              | miss
                                  retrieve_schema -> retrieve_examples -> generate_sql
                                                                              |
                          +------- fix_sql <---(error)--- execute_sql <-- [cost_check] -- denied --> cancelled
                          |                                    |
                          +--------------------------------> analyst -> chart -> [cache_store] -> finalize -> END

Optional parts (in brackets) are switched on with build_graph(...) flags.
"""

from langgraph.graph import END, START, StateGraph

from src import config
from src.graph.nodes.analyst import analyst_node
from src.graph.nodes.approval import cancelled_node, cost_check_node
from src.graph.nodes.cache_nodes import cache_lookup_node, cache_store_node
from src.graph.nodes.chart import chart_node
from src.graph.nodes.context import load_context_node
from src.graph.nodes.execute_sql import execute_sql_node
from src.graph.nodes.finalize import finalize_node
from src.graph.nodes.fix_sql import fix_sql_node
from src.graph.nodes.generate_sql import generate_sql_node
from src.graph.nodes.memory_node import save_memory_node
from src.graph.nodes.refuse import refuse_node
from src.graph.nodes.retrieve import retrieve_examples_node, retrieve_schema_node
from src.graph.nodes.rewrite import rewrite_question_node
from src.graph.nodes.router import FOLLOW_UP, MEMORY, OUT_OF_SCOPE, router_node
from src.graph.state import AgentState


def route_question(state: AgentState) -> str:
    route = state.get("route")
    if route == OUT_OF_SCOPE:
        return "refuse"
    if route == MEMORY:
        return "save_memory"
    if route == FOLLOW_UP:
        return "rewrite_question"
    return "start_sql"


def should_retry(state: AgentState) -> str:
    """Retry failed SQL until the retry cap is reached."""
    if state.get("error") and state.get("retries", 0) < config.MAX_RETRIES:
        return "fix_sql"
    return "analyst"


def after_cache_lookup(state: AgentState) -> str:
    return "finalize" if state.get("cache_hit") else "retrieve_schema"


def after_cost_check(state: AgentState) -> str:
    return "execute_sql" if state.get("approved", True) else "cancelled"


def build_graph(checkpointer=None, use_cache: bool = False, require_approval: bool = False):
    """Compile the workflow.

    checkpointer      keeps conversations (needed for follow-ups across calls and for approval)
    use_cache         answer repeated questions from the cache
    require_approval  ask a human before running expensive queries (needs a checkpointer)
    """
    if require_approval and checkpointer is None:
        raise ValueError("require_approval=True needs a checkpointer.")

    workflow = StateGraph(AgentState)

    for name, node in {
        "load_context": load_context_node,
        "router": router_node,
        "refuse": refuse_node,
        "save_memory": save_memory_node,
        "rewrite_question": rewrite_question_node,
        "retrieve_schema": retrieve_schema_node,
        "retrieve_examples": retrieve_examples_node,
        "generate_sql": generate_sql_node,
        "execute_sql": execute_sql_node,
        "fix_sql": fix_sql_node,
        "analyst": analyst_node,
        "chart": chart_node,
        "finalize": finalize_node,
    }.items():
        workflow.add_node(name, node)

    # Where a new SQL attempt goes before it is executed
    run_sql = "execute_sql"
    if require_approval:
        workflow.add_node("cost_check", cost_check_node)
        workflow.add_node("cancelled", cancelled_node)
        run_sql = "cost_check"
        workflow.add_conditional_edges(
            "cost_check", after_cost_check, {"execute_sql": "execute_sql", "cancelled": "cancelled"}
        )
        workflow.add_edge("cancelled", END)

    # Start of the SQL path: through the cache or straight to retrieval
    start_sql = "retrieve_schema"
    if use_cache:
        workflow.add_node("cache_lookup", cache_lookup_node)
        workflow.add_node("cache_store", cache_store_node)
        start_sql = "cache_lookup"
        workflow.add_conditional_edges(
            "cache_lookup", after_cache_lookup,
            {"finalize": "finalize", "retrieve_schema": "retrieve_schema"},
        )
        workflow.add_edge("chart", "cache_store")
        workflow.add_edge("cache_store", "finalize")
    else:
        workflow.add_edge("chart", "finalize")

    workflow.add_edge(START, "load_context")
    workflow.add_edge("load_context", "router")
    workflow.add_conditional_edges(
        "router", route_question,
        {
            "refuse": "refuse",
            "save_memory": "save_memory",
            "rewrite_question": "rewrite_question",
            "start_sql": start_sql,
        },
    )
    workflow.add_edge("rewrite_question", start_sql)

    workflow.add_edge("retrieve_schema", "retrieve_examples")
    workflow.add_edge("retrieve_examples", "generate_sql")
    workflow.add_edge("generate_sql", run_sql)
    workflow.add_conditional_edges(
        "execute_sql", should_retry, {"fix_sql": "fix_sql", "analyst": "analyst"}
    )
    workflow.add_edge("fix_sql", run_sql)
    workflow.add_edge("analyst", "chart")

    workflow.add_edge("finalize", END)
    workflow.add_edge("refuse", END)
    workflow.add_edge("save_memory", END)

    return workflow.compile(checkpointer=checkpointer)


if __name__ == "__main__":
    graph = build_graph()
    final = graph.invoke({"question": "How many orders are there in total?"})

    print("Route  :", final.get("route"))
    print("SQL    :", final.get("sql"))
    print("Rows   :", final.get("rows"))
    print("Retries:", final.get("retries"))
    print("Answer :", final.get("answer"))