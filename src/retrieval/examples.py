"""Retrieve similar question/SQL examples (few-shot)."""

from src import config
from src.embeddings import get_embedding_function
from src.retrieval.store import get_client


def retrieve_examples(
    question: str,
    k: int = config.EXAMPLES_TOP_K,
    exclude_ids: list[str] | None = None,
) -> list[dict]:
    """Return the k most similar examples.

    ``exclude_ids`` removes examples by id. The evaluation passes the id of the
    question being tested so its own gold SQL can never be retrieved
    (otherwise the benchmark leaks the answer).
    """
    embedding = get_embedding_function()([question])[0]

    query = {"query_embeddings": [embedding], "n_results": k}
    if exclude_ids:
        query["where"] = {"question_id": {"$nin": list(exclude_ids)}}

    collection = get_client().get_collection(name="sql_examples")
    results = collection.query(**query)

    return [
        {
            "id": meta["question_id"],
            "question": meta["question"],
            "content": document,
            "distance": distance,
        }
        for meta, document, distance in zip(
            results["metadatas"][0],
            results["documents"][0],
            results["distances"][0],
        )
    ]


if __name__ == "__main__":
    for item in retrieve_examples("What is the total number of orders?"):
        print(f"{item['id']}: {item['question']} ({item['distance']:.4f})")
