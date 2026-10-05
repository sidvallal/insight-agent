import chromadb
from pathlib import Path

from embed_schema import HuggingFaceEmbeddingFunction


BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = BASE_DIR / "data" / "chroma"


def retrieve_schema(question: str, k: int = 4):
    # Use the same Hugging Face embedding function
    # that was used when storing the schema chunks.
    embedding_function = HuggingFaceEmbeddingFunction()

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    collection = client.get_collection(
        name="schema_chunks",
        embedding_function=embedding_function,
    )

    # Generate the query embedding using Hugging Face.
    query_embedding = embedding_function(
        [question]
    )[0].tolist()

    # Search Chroma using the precomputed embedding.
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
    )

    retrieved = []

    for metadata, document, distance in zip(
        results["metadatas"][0],
        results["documents"][0],
        results["distances"][0],
    ):
        retrieved.append(
            {
                "table": metadata["table"],
                "content": document,
                "distance": distance,
            }
        )

    return retrieved


if __name__ == "__main__":
    question = "How many orders were placed in each month?"

    results = retrieve_schema(question, k=4)

    print(f"\nQuestion: {question}")
    print("\nRetrieved schema:\n")

    for i, result in enumerate(results, start=1):
        print(f"{i}. {result['table']}")
        print(f"   Distance: {result['distance']:.4f}")
        print()