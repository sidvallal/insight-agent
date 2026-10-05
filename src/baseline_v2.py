"""RAG-enhanced Text-to-SQL baseline."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from llm import get_llm
from retrieve_schema import retrieve_schema
from retrieve_examples import retrieve_examples


# ---------------------------------------------------------
# Project configuration
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# ---------------------------------------------------------
# LLM
# ---------------------------------------------------------

llm = get_llm()


# ---------------------------------------------------------
# Database
# ---------------------------------------------------------

def get_database_url():
    """Build the PostgreSQL database URL from environment variables."""

    return (
        f"postgresql+psycopg2://"
        f"{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
        f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}"
        f"/{os.getenv('DB_NAME')}"
    )


engine = create_engine(get_database_url())


# ---------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------

def build_prompt(question: str) -> str:
    """
    Build the RAG prompt using:
    - 4 retrieved schema chunks
    - 3 similar question/SQL examples
    """

    # Retrieve relevant database schema
    schema_results = retrieve_schema(
        question,
        k=4,
    )

    # Retrieve similar question/SQL examples
    example_results = retrieve_examples(
        question,
        k=3,
    )

    # Build schema context
    schema_context = "\n\n".join(
        f"TABLE: {item['table']}\n"
        f"{item['content']}"
        for item in schema_results
    )

    # Build few-shot example context
    examples_context = "\n\n".join(
        f"QUESTION: {item['question']}\n"
        f"SQL:\n"
        f"{item['content'].split('SQL:', 1)[1].strip()}"
        for item in example_results
    )

    prompt = f"""
You are a PostgreSQL Text-to-SQL assistant.

Generate one SQL query that answers the user's question.

Rules:
1. Use only the tables and columns provided in the schema context.
2. Follow the SQL patterns shown in the similar examples when relevant.
3. Generate valid PostgreSQL SQL.
4. Return ONLY the SQL query.
5. Do not use markdown code fences.
6. Do not explain the query.
7. Do not invent tables or columns.

SCHEMA CONTEXT:
{schema_context}

SIMILAR QUESTION AND SQL EXAMPLES:
{examples_context}

USER QUESTION:
{question}
"""

    return prompt.strip()


# ---------------------------------------------------------
# SQL generation
# ---------------------------------------------------------

def generate_sql(question: str) -> str:
    """Generate SQL using retrieved schema and few-shot examples."""

    prompt = build_prompt(question)

    response = llm.invoke(prompt)

    sql = response.content.strip()

    # Remove markdown code fences if the model returns them.
    if sql.startswith("```"):
        lines = sql.splitlines()

        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        sql = "\n".join(lines).strip()

    return sql


# ---------------------------------------------------------
# SQL execution
# ---------------------------------------------------------

def run_query(sql: str):
    """Execute generated SQL against PostgreSQL."""

    with engine.connect() as connection:
        result = connection.execute(text(sql))

        columns = list(result.keys())

        rows = [
            dict(row._mapping)
            for row in result
        ]

    return columns, rows


# ---------------------------------------------------------
# Test
# ---------------------------------------------------------

if __name__ == "__main__":

    question = "How many orders are there in total?"

    print(f"Question: {question}\n")

    print("Generating SQL using schema retrieval + few-shot examples...")

    sql = generate_sql(question)

    print("\nGenerated SQL:")
    print(sql)

    print("\nResult:")

    columns, rows = run_query(sql)

    print(columns)

    for row in rows:
        print(row)