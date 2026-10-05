import chromadb
from pathlib import Path

from embed_schema import HuggingFaceEmbeddingFunction


BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = BASE_DIR / "data" / "chroma"


def retrieve_examples(question: str, k: int = 3):
    embedding_function = HuggingFaceEmbeddingFunction()

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    collection = client.get_collection(
        name="sql_examples"
    )

    # Embed the question with the same Hugging Face model.
    query_embedding = embedding_function(
        [question]
    )[0].tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
    )

    examples = []

    for metadata, document, distance in zip(
        results["metadatas"][0],
        results["documents"][0],
        results["distances"][0],
    ):
        examples.append(
            {
                "id": metadata["question_id"],
                "question": metadata["question"],
                "content": document,
                "distance": distance,
            }
        )

    return examples


if __name__ == "__main__":
    question = "What is the total number of orders?"

    results = retrieve_examples(question, k=3)

    print(f"\nQuestion: {question}")
    print("\nRetrieved examples:\n")

    for i, example in enumerate(results, start=1):
        print(f"{i}. {example['id']}")
        print(f"   Question: {example['question']}")
        print(f"   Distance: {example['distance']:.4f}")
        print(f"   {example['content']}")
        print()