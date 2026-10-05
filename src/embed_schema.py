import json
import os
from pathlib import Path

import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from huggingface_hub import InferenceClient
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

CHUNKS_FILE = BASE_DIR / "data" / "schema_chunks.json"
CHROMA_DIR = BASE_DIR / "data" / "chroma"

HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class HuggingFaceEmbeddingFunction(EmbeddingFunction):
    def __init__(self):
        if not HF_TOKEN:
            raise ValueError("HF_TOKEN is missing from .env")

        self.client = InferenceClient(
            provider="hf-inference",
            api_key=HF_TOKEN,
        )

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []

        for text in input:
            result = self.client.feature_extraction(
                text,
                model=MODEL_NAME,
            )

            embeddings.append(result.tolist())

        return embeddings


def main():
    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    embedding_function = HuggingFaceEmbeddingFunction()

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    collection = client.get_or_create_collection(
        name="schema_chunks",
        embedding_function=embedding_function,
    )

    collection.upsert(
        ids=[chunk["table"] for chunk in chunks],
        documents=[chunk["content"] for chunk in chunks],
        metadatas=[
            {"table": chunk["table"]}
            for chunk in chunks
        ],
    )

    print(f"Stored {len(chunks)} schema chunks in ChromaDB.")
    print(f"Collection: {collection.name}")
    print(f"Total documents: {collection.count()}")


if __name__ == "__main__":
    main()