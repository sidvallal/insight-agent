"""Shared ChromaDB client."""

from functools import lru_cache

from src import config


@lru_cache(maxsize=1)
def get_client():
    import chromadb

    return chromadb.PersistentClient(path=str(config.CHROMA_DIR))
