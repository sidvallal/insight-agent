"""Router node: classify the question."""

from src import llm
from src.graph.state import AgentState

SQL = "SQL question"
FOLLOW_UP = "Follow-up"
OUT_OF_SCOPE = "Out of scope"

PROMPT = """
You are a router for a Text-to-SQL data analysis agent that answers questions
about a Brazilian e-commerce database (orders, customers, products, sellers,
payments, reviews).

Classify the user's message into exactly ONE category:

SQL question  - asks for information that can be answered from the database.
                e.g. "How many orders are there?", "Show the top 10 sellers."
Follow-up     - refers to a previous answer.
                e.g. "What about the top 5?", "Break that down by state."
Out of scope  - unrelated to the database or to data analysis.
                e.g. "What is the weather today?", "Write a Python program."

User message:
{question}

Return ONLY one of: SQL question, Follow-up, Out of scope
"""


def parse_route(text: str) -> str:
    """Map the LLM's answer to a route, tolerating case and punctuation.

    If the answer is unrecognisable we default to SQL question, so a valid
    question is never silently refused because of a formatting slip.
    """
    cleaned = text.strip().strip("`'\".*").lower()

    if cleaned.startswith("out"):
        return OUT_OF_SCOPE
    if cleaned.startswith("follow"):
        return FOLLOW_UP
    return SQL


def router_node(state: AgentState) -> AgentState:
    answer = llm.ask_llm(PROMPT.format(question=state["question"]))
    return {**state, "route": parse_route(answer)}
