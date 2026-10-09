"""FastAPI backend.

    uvicorn src.api.main:app --port 8000

POST /ask        stream the answer to a question (Server-Sent Events)
POST /approve    approve or reject a query that is waiting for a decision (also streams)
GET  /history    past questions of a user      DELETE /history/{id}  removes one,  DELETE /history  clears all
GET  /memory     saved preferences of a user        DELETE /memory  clears them
GET  /health     liveness + database check
"""

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from pydantic import BaseModel, Field

from src import config, db, history, memory
from src.api.events import events_for_update, final_status, sse
from src.graph.builder import build_graph
from src.graph.checkpoint import get_checkpointer


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    thread_id: str | None = None
    user_id: str = Field(default="demo", min_length=1, max_length=64)


class ApproveRequest(BaseModel):
    thread_id: str
    approve: bool


def stream_graph(graph, graph_input, thread_id: str):
    """Run the graph and yield Server-Sent Events as each node finishes."""
    run_config = {"configurable": {"thread_id": thread_id}}
    started = time.perf_counter()
    yield sse("start", {"thread_id": thread_id})

    try:
        for chunk in graph.stream(graph_input, run_config, stream_mode="updates"):
            for node, update in chunk.items():
                if node == "__interrupt__":
                    for item in update:
                        yield sse("approval", item.value)
                    continue
                for name, data in events_for_update(node, update):
                    yield sse(name, data)

        snapshot = graph.get_state(run_config)
        values = snapshot.values
        latency_ms = int((time.perf_counter() - started) * 1000)

        if snapshot.next:   # paused, waiting for /approve
            yield sse("done", {"thread_id": thread_id, "status": "waiting_approval",
                               "cache_hit": False, "latency_ms": latency_ms})
            return

        status = final_status(values)
        try:
            history.log_query(
                values.get("user_id", "demo"), thread_id, values.get("user_question", ""),
                values.get("sql", ""), values.get("row_count", 0), status, latency_ms,
            )
        except Exception:   # the history is a convenience: never break the answer
            pass

        yield sse("done", {"thread_id": thread_id, "status": status,
                           "cache_hit": bool(values.get("cache_hit")), "latency_ms": latency_ms})
    except Exception as exc:
        yield sse("error", {"message": str(exc)})


def streaming(generator) -> StreamingResponse:
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def create_app(graph=None) -> FastAPI:
    """Create the app. Tests pass their own graph; otherwise one is built at startup."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if not config.STATE_MAX_ROWS:
            config.STATE_MAX_ROWS = 1000   # keep conversation checkpoints small
        app.state.graph = graph or build_graph(
            checkpointer=get_checkpointer(), use_cache=True, require_approval=True
        )
        yield

    app = FastAPI(title="InsightAgent", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware, allow_origins=config.CORS_ORIGINS,
        allow_methods=["*"], allow_headers=["*"],
    )

    @app.get("/")
    def root():
        return {"name": "InsightAgent API", "docs": "/docs", "health": "/health"}

    @app.post("/ask")
    def ask(request: AskRequest):
        thread_id = request.thread_id or uuid.uuid4().hex[:12]
        graph_input = {"question": request.question.strip(), "user_id": request.user_id}
        return streaming(stream_graph(app.state.graph, graph_input, thread_id))

    @app.post("/approve")
    def approve(request: ApproveRequest):
        return streaming(
            stream_graph(app.state.graph, Command(resume=request.approve), request.thread_id)
        )

    @app.get("/history")
    def get_history(user_id: str = Query("demo", max_length=64), limit: int = Query(30, le=100)):
        return history.list_history(user_id, limit)

    @app.delete("/history/{entry_id}")
    def delete_history_entry(entry_id: int, user_id: str = Query("demo", max_length=64)):
        if not history.delete_entry(user_id, entry_id):
            raise HTTPException(status_code=404, detail="No such history entry")
        return {"deleted": True}

    @app.delete("/history")
    def clear_history(user_id: str = Query("demo", max_length=64)):
        return {"deleted": history.clear_history(user_id)}

    @app.get("/memory")
    def get_memory(user_id: str = Query("demo", max_length=64)):
        return {"memories": memory.list_memories(user_id)}

    @app.delete("/memory")
    def delete_memory(user_id: str = Query("demo", max_length=64)):
        memory.clear_memories(user_id)
        return {"cleared": True}

    @app.get("/health")
    def health():
        try:
            db.run_query("SELECT 1")
            return {"status": "ok", "database": True}
        except Exception:
            return {"status": "degraded", "database": False}

    return app


app = create_app()