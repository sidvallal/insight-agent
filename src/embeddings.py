"""Hugging Face embedding function used by ChromaDB (single shared copy)."""

import os
from functools import lru_cache

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from src import config


class HuggingFaceEmbeddingFunction(EmbeddingFunction):
    def __init__(self):
        from huggingface_hub import InferenceClient

        token = os.getenv("HF_TOKEN")
        if not token:
            raise ValueError("HF_TOKEN is missing from .env")

        self.client = InferenceClient(provider="hf-inference", api_key=token)

    def __call__(self, input: Documents) -> Embeddings:
        return [
            self.client.feature_extraction(text, model=config.EMBED_MODEL).tolist()
            for text in input
        ]


@lru_cache(maxsize=1)
def get_embedding_function() -> HuggingFaceEmbeddingFunction:
    """Create the embedding client once instead of once per question."""
    return HuggingFaceEmbeddingFunction()
