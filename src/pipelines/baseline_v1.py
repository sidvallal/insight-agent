"""v1 baseline: the FULL schema goes into one prompt (no retrieval, no graph)."""

from src import config, llm
from src.utils import clean_sql

PROMPT = """
You are an expert PostgreSQL Text-to-SQL assistant.

Use only the tables and columns in the schema below.
Generate one valid PostgreSQL SELECT query for the user's question.

Rules:
- Return only SQL, without markdown code fences.
- Do not generate INSERT, UPDATE, DELETE, DROP or other modifying statements.
- Do not invent table or column names.

Database schema:
{schema}

Question:
{question}
"""


def generate_sql(question: str, exclude_ids: list[str] | None = None) -> str:
    schema = config.SCHEMA_DOCS_FILE.read_text(encoding="utf-8")
    return clean_sql(llm.ask_llm(PROMPT.format(schema=schema, question=question)))
