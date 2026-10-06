"""v2: retrieved schema chunks + retrieved few-shot examples (no graph)."""

from src import config, llm
from src.retrieval.examples import retrieve_examples
from src.retrieval.schema import retrieve_schema
from src.utils import clean_sql, format_examples, format_schema

PROMPT = """
You are a PostgreSQL Text-to-SQL assistant.

Generate one SQL query that answers the user's question.

Rules:
1. Use only the tables and columns provided in the schema context.
2. Follow the SQL patterns in the similar examples when relevant.
3. Generate valid PostgreSQL SQL.
4. Return ONLY the SQL query, without markdown fences or explanation.

SCHEMA CONTEXT:
{schema}

SIMILAR QUESTION AND SQL EXAMPLES:
{examples}

USER QUESTION:
{question}
"""


def generate_sql(question: str, exclude_ids: list[str] | None = None) -> str:
    schema = retrieve_schema(question, k=config.SCHEMA_TOP_K)
    examples = retrieve_examples(question, k=config.EXAMPLES_TOP_K, exclude_ids=exclude_ids)

    prompt = PROMPT.format(
        schema=format_schema(schema),
        examples=format_examples(examples),
        question=question,
    )
    return clean_sql(llm.ask_llm(prompt))
