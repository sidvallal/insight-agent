"""Small in-memory answer cache (repeated questions skip the LLM and the database)."""

import hashlib
import re
import threading
import time

from src import config

_lock = threading.Lock()
_store: dict[str, tuple[float, dict]] = {}


def make_key(question: str, memory_context: str = "") -> str:
    """Same question + same saved preferences -> same key."""
    normalized = re.sub(r"\s+", " ", question.lower()).strip(" ?.!")
    digest = hashlib.sha256(f"{normalized}|{memory_context}".encode()).hexdigest()
    return digest


def get(key: str) -> dict | None:
    with _lock:
        item = _store.get(key)
        if item is None:
            return None
        stored_at, value = item
        if time.time() - stored_at > config.CACHE_TTL_SECONDS:
            del _store[key]
            return None
        return value


def put(key: str, value: dict) -> None:
    with _lock:
        _store[key] = (time.time(), value)


def clear() -> None:
    with _lock:
        _store.clear()