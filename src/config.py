"""Central configuration: paths, environment variables and tunable constants."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Paths
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = DATA_DIR / "chroma"
SCHEMA_DOCS_FILE = DATA_DIR / "schema_docs.md"
SCHEMA_CHUNKS_FILE = DATA_DIR / "schema_chunks.json"
EXAMPLES_FILE = DATA_DIR / "few_shot_examples.json"
EVAL_DIR = BASE_DIR / "eval"
QUESTIONS_FILE = EVAL_DIR / "questions.json"
RESULTS_DIR = EVAL_DIR / "results"

# Models
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Agent behaviour
SCHEMA_TOP_K = 4
EXAMPLES_TOP_K = 3
MAX_RETRIES = 3
MAX_ROWS_TO_LLM = 20
STATEMENT_TIMEOUT_MS = 30_000

# Approximate Groq pricing in USD per 1M tokens (check the current price list).
PRICE_PER_M_INPUT = 0.15
PRICE_PER_M_OUTPUT = 0.60


def database_url() -> URL:
    """Build the PostgreSQL URL (URL.create safely handles special characters)."""
    return URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME"),
    )
