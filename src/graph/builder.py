"""Build and compile the LangGraph Text-to-SQL workflow.

    START -> router -+-> refuse -> END                       (out of scope)
                     |
                     +-> retrieve_schema -> retrieve_examples -> generate_sql
                                                                     |
                                       +------- fix_sql <--(error)---+
                                       |                             |
                                       +--> execute_sql <------------+
                                                 |
                                              analyst -> END
"""

from langgraph.graph import END, START, StateGraph

from src import config
from src.graph.nodes.analyst import analyst_node
from src.graph.nodes.execute_sql import execute_sql_node
from src.graph.nodes.fix_sql import fix_sql_node
from src.graph.nodes.generate_sql import generate_sql_node
from src.graph.nodes.refuse import refuse_node
from src.graph.nodes.retrieve import retrieve_examples_node, retrieve_schema_node
from src.graph.nodes.router import OUT_OF_SCOPE, router_node
from src.graph.state import AgentState


def route_question(state: AgentState) -> str:
    """Out-of-scope questions are refused; everything else goes through SQL."""
    return "refuse" if state.get("route") == OUT_OF_SCOPE else "retrieve_schema"


def should_retry(state: AgentState) -> str:
    """Retry failed SQL until the retry cap is reached."""
    if state.get("error") and state.get("retries", 0) < config.MAX_RETRIES:
        return "fix_sql"
    return "analyst"


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("router", router_node)
    workflow.add_node("refuse", refuse_node)
    workflow.add_node("retrieve_schema", retrieve_schema_node)
    workflow.add_node("retrieve_examples", retrieve_examples_node)
    workflow.add_node("generate_sql", generate_sql_node)
    workflow.add_node("execute_sql", execute_sql_node)
    workflow.add_node("fix_sql", fix_sql_node)
    workflow.add_node("analyst", analyst_node)

    workflow.add_edge(START, "router")
    workflow.add_conditional_edges(
        "router",
        route_question,
        {"refuse": "refuse", "retrieve_schema": "retrieve_schema"},
    )
    workflow.add_edge("retrieve_schema", "retrieve_examples")
    workflow.add_edge("retrieve_examples", "generate_sql")
    workflow.add_edge("generate_sql", "execute_sql")
    workflow.add_conditional_edges(
        "execute_sql",
        should_retry,
        {"fix_sql": "fix_sql", "analyst": "analyst"},
    )
    workflow.add_edge("fix_sql", "execute_sql")
    workflow.add_edge("analyst", END)
    workflow.add_edge("refuse", END)

    return workflow.compile()


if __name__ == "__main__":
    graph = build_graph()
    final = graph.invoke({"question": "How many orders are there in total?", "retries": 0})

    print("Route  :", final.get("route"))
    print("SQL    :", final.get("sql"))
    print("Rows   :", final.get("rows"))
    print("Retries:", final.get("retries"))
    print("Answer :", final.get("answer"))
