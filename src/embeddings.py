"""Embeddings for retrieval.

Backends (EMBEDDING_BACKEND in .env):
    gemini  Google Gemini API, free tier (default).  Needs GEMINI_API_KEY.
    hf      Hugging Face Inference Providers.        Needs HF_TOKEN and credits.

Both expose:
    embedding_function(texts)    -> vectors for DOCUMENTS (used by ChromaDB when indexing)
    embedding_function.embed_query(text) -> vector for a QUESTION (cached)
"""

import math
import os
import time
from functools import lru_cache

import httpx
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from src import config

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents"
BATCH_SIZE = 100            # the API accepts up to 100 texts per request
MAX_ATTEMPTS = 4
RETRY_STATUSES = {429, 500, 502, 503, 504}
QUERY_CACHE_SIZE = 512


def _normalize(vector: list[float]) -> list[float]:
    """Only 3072-dimensional Gemini embeddings come normalized, so do it ourselves."""
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


class GeminiEmbeddingFunction(EmbeddingFunction):
    def __init__(self, client: httpx.Client | None = None, sleep=time.sleep):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key and client is None:
            raise ValueError("GEMINI_API_KEY is missing from .env (create one at https://aistudio.google.com/apikey)")
        self.client = client or httpx.Client(timeout=30)
        self._sleep = sleep
        self._query_cache: dict[str, list[float]] = {}

    # ---- HTTP ---------------------------------------------------------------

    def _post(self, texts: list[str], task_type: str) -> list[list[float]]:
        model = config.GEMINI_EMBED_MODEL
        body = {"requests": [
            {
                "model": f"models/{model}",
                "content": {"parts": [{"text": text}]},
                "taskType": task_type,
                "outputDimensionality": config.EMBED_DIMENSIONS,
            }
            for text in texts
        ]}
        headers = {"x-goog-api-key": self.api_key or "", "Content-Type": "application/json"}

        for attempt in range(1, MAX_ATTEMPTS + 1):
            response = self.client.post(GEMINI_URL.format(model=model), json=body, headers=headers)
            if response.status_code == 200:
                return [_normalize(item["values"]) for item in response.json()["embeddings"]]
            if response.status_code in RETRY_STATUSES and attempt < MAX_ATTEMPTS:
                self._sleep(2 ** attempt)      # 2, 4, 8 seconds
                continue
            raise RuntimeError(self._explain(response))

    @staticmethod
    def _explain(response: httpx.Response) -> str:
        detail = response.text[:200].replace("\n", " ")
        if response.status_code == 429:
            return ("Gemini embedding limit reached (free tier: requests per minute or per day). "
                    f"Wait a minute, or until tomorrow if the daily quota is used. Details: {detail}")
        if response.status_code in (400, 401, 403):
            return f"Gemini rejected the request (HTTP {response.status_code}). Check GEMINI_API_KEY. Details: {detail}"
        return f"Gemini embedding request failed (HTTP {response.status_code}): {detail}"

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), BATCH_SIZE):
            vectors.extend(self._post(texts[start:start + BATCH_SIZE], task_type))
        return vectors

    # ---- public API ---------------------------------------------------------

    def __call__(self, input: Documents) -> Embeddings:
        """Embed DOCUMENTS (ChromaDB calls this when indexing)."""
        return self._embed(list(input), "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        """Embed a QUESTION. Cached, so the schema and example lookups cost one API call together."""
        if text not in self._query_cache:
            if len(self._query_cache) >= QUERY_CACHE_SIZE:
                self._query_cache.pop(next(iter(self._query_cache)))
            self._query_cache[text] = self._embed([text], "RETRIEVAL_QUERY")[0]
        return self._query_cache[text]


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

    def embed_query(self, text: str) -> list[float]:
        return self([text])[0]


@lru_cache(maxsize=1)
def get_embedding_function():
    """Create the embedding client once instead of once per question."""
    if config.EMBEDDING_BACKEND == "hf":
        return HuggingFaceEmbeddingFunction()
    return GeminiEmbeddingFunction()


def embed_query(text: str) -> list[float]:
    return get_embedding_function().embed_query(text)