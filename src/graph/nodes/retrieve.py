"""Retrieval nodes: schema chunks and few-shot examples."""

from src import config
from src.graph.state import AgentState
from src.retrieval.examples import retrieve_examples
from src.retrieval.schema import retrieve_schema


def retrieve_schema_node(state: AgentState) -> AgentState:
    chunks = retrieve_schema(state["question"], k=config.SCHEMA_TOP_K)
    return {**state, "schema_context": chunks}


def retrieve_examples_node(state: AgentState) -> AgentState:
    examples = retrieve_examples(
        state["question"],
        k=config.EXAMPLES_TOP_K,
        exclude_ids=state.get("exclude_example_ids"),
    )
    return {**state, "example_context": examples}
