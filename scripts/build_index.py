"""Build the ChromaDB index (schema chunks + few-shot examples).

    python -m scripts.build_index

Run it again whenever data/schema_docs.md or data/few_shot_examples.json changes.
The index lives in data/chroma/ and is NOT committed to Git.
"""

import json
import re

from src import config
from src.embeddings import get_embedding_function
from src.retrieval.store import get_client

TABLE_PATTERN = re.compile(
    r"##\s+\d+\.\s+.*?—\s+`([^`]+)`(.*?)(?=\n##\s+\d+\.|\Z)",
    re.DOTALL,
)


def chunk_schema() -> list[dict]:
    """Split data/schema_docs.md into one chunk per table."""
    text = config.SCHEMA_DOCS_FILE.read_text(encoding="utf-8")
    chunks = [
        {"table": table, "content": content.strip()}
        for table, content in TABLE_PATTERN.findall(text)
    ]
    config.SCHEMA_CHUNKS_FILE.write_text(
        json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return chunks


def fresh_collection(client, name: str):
    """Drop and recreate a collection so re-running never leaves stale items."""
    try:
        client.delete_collection(name)
    except Exception:
        pass
    return client.create_collection(name=name, embedding_function=get_embedding_function())


def main():
    client = get_client()

    chunks = chunk_schema()
    schema_collection = fresh_collection(client, "schema_chunks")
    schema_collection.add(
        ids=[c["table"] for c in chunks],
        # The table name is part of the embedded text so that
        # "orders" in a question matches the orders table.
        documents=[f"Table: {c['table']}\n{c['content']}" for c in chunks],
        metadatas=[{"table": c["table"]} for c in chunks],
    )
    print(f"Indexed {len(chunks)} schema chunks.")

    examples = json.loads(config.EXAMPLES_FILE.read_text(encoding="utf-8"))
    example_collection = fresh_collection(client, "sql_examples")
    example_collection.add(
        ids=[e["id"] for e in examples],
        documents=[f"Question: {e['question']}\nSQL: {e['sql']}" for e in examples],
        metadatas=[{"question_id": e["id"], "question": e["question"]} for e in examples],
    )
    print(f"Indexed {len(examples)} few-shot examples.")


if __name__ == "__main__":
    main()
