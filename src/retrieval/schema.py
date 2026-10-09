"""Retrieve the most relevant table descriptions for a question."""

from src import config
from src.embeddings import embed_query
from src.retrieval.store import get_client


def retrieve_schema(question: str, k: int = config.SCHEMA_TOP_K) -> list[dict]:
    embedding = embed_query(question)

    collection = get_client().get_collection(name="schema_chunks")
    results = collection.query(query_embeddings=[embedding], n_results=k)

    return [
        {"table": meta["table"], "content": document, "distance": distance}
        for meta, document, distance in zip(
            results["metadatas"][0],
            results["documents"][0],
            results["distances"][0],
        )
    ]


if __name__ == "__main__":
    for item in retrieve_schema("How many orders were placed in each month?"):
        print(f"{item['table']:40} {item['distance']:.4f}")
