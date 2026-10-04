"""Basic Text-to-SQL baseline using Groq and PostgreSQL."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from llm import get_llm

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = BASE_DIR / "data" / "schema_docs.md"

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

if not all([DB_NAME, DB_USER, DB_PASSWORD]):
    raise ValueError("Database configuration is incomplete in .env.")

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(DATABASE_URL)


def load_schema() -> str:
    """Load the complete database schema documentation."""
    return SCHEMA_PATH.read_text(encoding="utf-8")


def generate_sql(question: str) -> str:
    """Generate SQL from a natural-language question."""
    llm = get_llm()
    schema = load_schema()

    prompt = f"""
You are an expert PostgreSQL Text-to-SQL assistant.

Use only the tables and columns in the schema below.
Generate one valid PostgreSQL SELECT query for the user's question.

Rules:
- Return only SQL.
- Do not use Markdown code fences.
- Do not generate INSERT, UPDATE, DELETE, DROP, or other modifying statements.
- Do not invent table or column names.

Database schema:
{schema}

Question:
{question}
"""

    response = llm.invoke(prompt)
    return response.content.strip().removeprefix("```sql").removesuffix("```").strip()


def execute_sql(sql: str):
    """Execute generated SQL and return rows as dictionaries."""
    with engine.connect() as connection:
        result = connection.execute(text(sql))
        return [dict(row._mapping) for row in result]


def ask(question: str) -> dict:
    """Generate SQL, execute it, and return the result."""
    sql = generate_sql(question)
    rows = execute_sql(sql)

    return {
        "question": question,
        "sql": sql,
        "result": rows,
    }


if __name__ == "__main__":
    question = input("Ask a question about the Olist database: ")

    try:
        response = ask(question)
        print("\nGenerated SQL:")
        print(response["sql"])

        print("\nQuery Result:")
        for row in response["result"]:
            print(row)

    except Exception as error:
        print(f"Error: {error}")

    finally:
        engine.dispose()