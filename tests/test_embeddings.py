"""Gemini embedding backend, tested against a fake server (no network, no API key)."""

import hashlib
import json
import math

import httpx
import pytest

from src import config, embeddings
from src.embeddings import GeminiEmbeddingFunction


def fake_vector(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode()).digest()
    return [b / 255 + 0.01 for b in digest[:8]]


class FakeGemini:
    """Behaves like batchEmbedContents and records every request."""

    def __init__(self, failures=()):
        self.requests = []
        self.failures = list(failures)      # HTTP statuses to return before succeeding

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.requests.append({"url": str(request.url), "headers": request.headers, "body": body})
        if self.failures:
            return httpx.Response(self.failures.pop(0), json={"error": {"message": "limit"}})
        texts = [item["content"]["parts"][0]["text"] for item in body["requests"]]
        return httpx.Response(200, json={"embeddings": [{"values": fake_vector(t)} for t in texts]})


def make(failures=()):
    server = FakeGemini(failures)
    sleeps = []
    function = GeminiEmbeddingFunction(
        client=httpx.Client(transport=httpx.MockTransport(server)), sleep=sleeps.append
    )
    function.api_key = "test-key"
    return function, server, sleeps


def test_documents_use_the_document_task_and_the_key_header():
    function, server, _ = make()

    function(["orders table", "customers table"])

    request = server.requests[0]
    assert request["url"].endswith("/models/gemini-embedding-001:batchEmbedContents")
    assert request["headers"]["x-goog-api-key"] == "test-key"
    first = request["body"]["requests"][0]
    assert first["taskType"] == "RETRIEVAL_DOCUMENT"
    assert first["model"] == "models/gemini-embedding-001"
    assert first["outputDimensionality"] == config.EMBED_DIMENSIONS


def test_queries_use_the_query_task():
    function, server, _ = make()

    function.embed_query("How many orders?")

    assert server.requests[0]["body"]["requests"][0]["taskType"] == "RETRIEVAL_QUERY"


def test_vectors_are_normalized():
    function, _, _ = make()

    vector = function.embed_query("anything")

    assert math.isclose(math.sqrt(sum(v * v for v in vector)), 1.0, rel_tol=1e-9)


def test_same_question_is_only_sent_once():
    function, server, _ = make()

    first = function.embed_query("How many orders?")
    second = function.embed_query("How many orders?")

    assert first == second
    assert len(server.requests) == 1


def test_large_inputs_are_split_into_batches_of_100():
    function, server, _ = make()

    vectors = function([f"text {i}" for i in range(250)])

    assert len(vectors) == 250
    assert [len(r["body"]["requests"]) for r in server.requests] == [100, 100, 50]


def test_temporary_failures_are_retried_with_waiting():
    function, server, sleeps = make(failures=[429, 503])

    assert function.embed_query("q")
    assert len(server.requests) == 3
    assert sleeps == [2, 4]


def test_persistent_rate_limit_gives_a_clear_message():
    function, server, sleeps = make(failures=[429] * 10)

    with pytest.raises(RuntimeError, match="limit reached"):
        function.embed_query("q")
    assert len(server.requests) == embeddings.MAX_ATTEMPTS


def test_bad_key_fails_immediately_with_a_hint():
    function, server, sleeps = make(failures=[403])

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        function.embed_query("q")
    assert len(server.requests) == 1 and sleeps == []


def test_missing_key_is_reported(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiEmbeddingFunction()


def test_backend_setting_chooses_the_function(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    embeddings.get_embedding_function.cache_clear()

    monkeypatch.setattr(config, "EMBEDDING_BACKEND", "gemini")
    assert isinstance(embeddings.get_embedding_function(), GeminiEmbeddingFunction)

    embeddings.get_embedding_function.cache_clear()


def test_function_works_inside_chromadb(tmp_path):
    import chromadb

    function, _, _ = make()
    client = chromadb.PersistentClient(path=str(tmp_path))
    collection = client.create_collection("test_collection", embedding_function=function)
    collection.add(ids=["a", "b"], documents=["orders table", "sellers table"])

    result = collection.query(query_embeddings=[function.embed_query("orders table")], n_results=1)

    assert result["ids"][0][0] == "a"