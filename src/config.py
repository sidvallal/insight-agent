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

# Safety
MAX_ROWS = 100_000            # hard cap on rows fetched per agent query
MAX_SQL_LENGTH = 10_000
ALLOWED_TABLES = frozenset({
    "olist_customers_dataset",
    "olist_geolocation_dataset",
    "olist_orders_dataset",
    "olist_order_items_dataset",
    "olist_order_payments_dataset",
    "olist_order_reviews_dataset",
    "olist_products_dataset",
    "olist_sellers_dataset",
    "product_category_name_translation",
})

# Phase 7: conversation, approval, cache
CHECKPOINTER = os.getenv("CHECKPOINTER", "memory").lower()      # "memory" or "postgres"
HISTORY_TURNS = 5                                               # previous turns kept for follow-ups
STATE_MAX_ROWS = int(os.getenv("STATE_MAX_ROWS", "0"))          # 0 = keep every row in the graph state
APPROVAL_COST_THRESHOLD = float(os.getenv("APPROVAL_COST_THRESHOLD", "100000"))
CACHE_TTL_SECONDS = 3600
CHART_MAX_POINTS = 200

# How the agent reaches the database: "mcp" (through the MCP server) or "direct"
DB_ACCESS = os.getenv("DB_ACCESS", "mcp").lower()

# Approximate Groq pricing in USD per 1M tokens (check the current price list).
PRICE_PER_M_INPUT = 0.15
PRICE_PER_M_OUTPUT = 0.60


def database_url(readonly: bool = False) -> URL:
    """Build the PostgreSQL URL (URL.create safely handles special characters).

    readonly=True uses the restricted DB_RO_USER account when it is configured;
    otherwise it falls back to the main account.
    """
    use_ro = readonly and os.getenv("DB_RO_USER")
    return URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("DB_RO_USER") if use_ro else os.getenv("DB_USER"),
        password=os.getenv("DB_RO_PASSWORD") if use_ro else os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME"),
    )