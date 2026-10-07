"""Long-term memory: user preferences saved in PostgreSQL (schema `app`).

Preferences are saved when the user says things like
"remember that I prefer revenue in descending order" or "always show 2 decimals".
They are loaded at the start of every turn and added to the SQL prompts.
"""

import re
from functools import lru_cache

from sqlalchemy import text

from src.db import get_admin_engine

MAX_MEMORIES = 20

_COMMAND = re.compile(
    r"^\s*(please\s+)?(remember|from now on|always|never|i prefer|my preference)\b",
    re.IGNORECASE,
)
_PREFIX = re.compile(r"^\s*(please\s+)?remember(\s+that|\s+to)?\s*[:,]?\s*", re.IGNORECASE)


def is_memory_command(question: str) -> bool:
    """True when the message tells the agent to remember something."""
    return bool(_COMMAND.match(question))


def extract_memory(question: str) -> str:
    """Turn 'Remember that I like X' into 'I like X'."""
    return _PREFIX.sub("", question).strip()


@lru_cache(maxsize=1)
def ensure_table() -> None:
    with get_admin_engine().begin() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS app"))
        connection.execute(text(
            "CREATE TABLE IF NOT EXISTS app.user_memory ("
            " id SERIAL PRIMARY KEY,"
            " user_id TEXT NOT NULL,"
            " content TEXT NOT NULL,"
            " created_at TIMESTAMPTZ NOT NULL DEFAULT now(),"
            " UNIQUE (user_id, content))"
        ))


def add_memory(user_id: str, content: str) -> None:
    ensure_table()
    with get_admin_engine().begin() as connection:
        connection.execute(
            text("INSERT INTO app.user_memory (user_id, content) VALUES (:u, :c) "
                 "ON CONFLICT (user_id, content) DO NOTHING"),
            {"u": user_id, "c": content},
        )


def list_memories(user_id: str) -> list[str]:
    ensure_table()
    with get_admin_engine().connect() as connection:
        rows = connection.execute(
            text("SELECT content FROM app.user_memory WHERE user_id = :u "
                 "ORDER BY created_at DESC LIMIT :n"),
            {"u": user_id, "n": MAX_MEMORIES},
        ).fetchall()
    return [row[0] for row in rows]


def clear_memories(user_id: str) -> None:
    ensure_table()
    with get_admin_engine().begin() as connection:
        connection.execute(text("DELETE FROM app.user_memory WHERE user_id = :u"), {"u": user_id})


def format_for_prompt(memories: list[str]) -> str:
    return "\n".join(f"- {m}" for m in memories)