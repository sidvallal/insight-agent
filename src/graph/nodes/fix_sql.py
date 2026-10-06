"""Repair SQL that failed (or returned nothing) using the error message."""

from src import llm
from src.graph.state import AgentState
from src.utils import clean_sql, format_examples, format_schema

PROMPT = """
You are an expert PostgreSQL SQL developer.

The SQL below failed or returned no rows. Fix it.

Rules:
- Return only the corrected SQL. No markdown, no explanation.
- Use only the exact table and column names shown in the schema.
- Keep the original intent of the question.
- Do not modify the database.

Question:
{question}

Schema:
{schema}

Similar examples:
{examples}

Previous SQL:
{sql}

Problem:
{error}
"""


def fix_sql_node(state: AgentState) -> AgentState:
    prompt = PROMPT.format(
        question=state["question"],
        schema=format_schema(state.get("schema_context", [])),
        examples=format_examples(state.get("example_context", [])),
        sql=state.get("sql", ""),
        error=state.get("error", ""),
    )
    return {
        **state,
        "sql": clean_sql(llm.ask_llm(prompt)),
        "error": "",
        "retries": state.get("retries", 0) + 1,
    }
