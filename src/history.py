"""Query history: one row per finished question (schema `app`)."""

from functools import lru_cache

from sqlalchemy import text

from src.db import get_admin_engine


@lru_cache(maxsize=1)
def ensure_table() -> None:
    with get_admin_engine().begin() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS app"))
        connection.execute(text(
            "CREATE TABLE IF NOT EXISTS app.query_history ("
            " id SERIAL PRIMARY KEY,"
            " user_id TEXT NOT NULL,"
            " thread_id TEXT NOT NULL,"
            " question TEXT NOT NULL,"
            " sql TEXT,"
            " row_count INTEGER,"
            " status TEXT NOT NULL,"
            " latency_ms INTEGER,"
            " created_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        ))


def log_query(user_id: str, thread_id: str, question: str, sql: str,
              row_count: int, status: str, latency_ms: int) -> None:
    ensure_table()
    with get_admin_engine().begin() as connection:
        connection.execute(
            text("INSERT INTO app.query_history "
                 "(user_id, thread_id, question, sql, row_count, status, latency_ms) "
                 "VALUES (:u, :t, :q, :s, :r, :st, :l)"),
            {"u": user_id, "t": thread_id, "q": question, "s": sql,
             "r": row_count, "st": status, "l": latency_ms},
        )


def list_history(user_id: str, limit: int = 50) -> list[dict]:
    ensure_table()
    with get_admin_engine().connect() as connection:
        rows = connection.execute(
            text("SELECT id, thread_id, question, sql, row_count, status, latency_ms, created_at "
                 "FROM app.query_history WHERE user_id = :u ORDER BY id DESC LIMIT :n"),
            {"u": user_id, "n": limit},
        ).mappings().all()
    return [{**row, "created_at": row["created_at"].isoformat()} for row in rows]

def delete_entry(user_id: str, entry_id: int) -> bool:
    """Delete one entry of this user. Returns False if it does not exist (or belongs to someone else)."""
    ensure_table()
    with get_admin_engine().begin() as connection:
        result = connection.execute(
            text("DELETE FROM app.query_history WHERE id = :id AND user_id = :u"),
            {"id": entry_id, "u": user_id},
        )
    return result.rowcount > 0


def clear_history(user_id: str) -> int:
    """Delete all entries of this user. Returns how many were removed."""
    ensure_table()
    with get_admin_engine().begin() as connection:
        result = connection.execute(
            text("DELETE FROM app.query_history WHERE user_id = :u"), {"u": user_id}
        )
    return result.rowcount