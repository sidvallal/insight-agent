"""Generate SQL from the question, retrieved schema and examples."""

from src import llm
from src.graph.state import AgentState
from src.utils import clean_sql, format_examples, format_schema

PROMPT = """
You are an expert PostgreSQL SQL generator.

Write ONE PostgreSQL SELECT query that answers the question.

Rules:
- Return only the SQL. No markdown, no explanation.
- Use only the tables and columns in the schema. Copy names exactly.
- Follow the patterns in the similar examples when they are relevant, but do
  not copy an example that does not match the question.
- Do not modify the database.

Schema:
{schema}

Similar examples:
{examples}

Question:
{question}
"""


def generate_sql_node(state: AgentState) -> AgentState:
    prompt = PROMPT.format(
        schema=format_schema(state.get("schema_context", [])),
        examples=format_examples(state.get("example_context", [])),
        question=state["question"],
    )
    return {**state, "sql": clean_sql(llm.ask_llm(prompt))}
