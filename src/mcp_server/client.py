"""Synchronous MCP client for the LangGraph nodes.

The MCP SDK is async, but the graph nodes are synchronous. This class starts
the server as a subprocess ONCE, keeps one session open in a background thread,
and exposes plain blocking methods.
"""

import asyncio
import atexit
import json
import os
import sys
import threading
from functools import lru_cache

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from src import config


class QueryFailed(Exception):
    """The MCP server rejected the query or the database returned an error."""


class MCPDatabaseClient:
    def __init__(self, startup_timeout: float = 60):
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

        self._session: ClientSession | None = None
        self._ready = threading.Event()
        self._startup_error: BaseException | None = None
        self._stop: asyncio.Event | None = None

        self._main_future = asyncio.run_coroutine_threadsafe(self._main(), self._loop)
        if not self._ready.wait(startup_timeout):
            raise RuntimeError("MCP server did not start in time.")
        if self._startup_error:
            raise RuntimeError(f"MCP server failed to start: {self._startup_error}")

    async def _main(self):
        # The server connection is opened and closed inside this ONE task,
        # because the MCP stdio transport requires it.
        self._stop = asyncio.Event()
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "src.mcp_server.server"],
            cwd=str(config.BASE_DIR),
            env=os.environ.copy(),
        )
        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self._session = session
                    self._ready.set()
                    await self._stop.wait()
        except BaseException as exc:
            self._startup_error = exc
            self._ready.set()

    def _call(self, name: str, arguments: dict, timeout: float = 120) -> dict | list:
        async def run():
            result = await self._session.call_tool(name, arguments)
            return "".join(part.text for part in result.content if hasattr(part, "text"))

        text = asyncio.run_coroutine_threadsafe(run(), self._loop).result(timeout)
        return json.loads(text)

    # ---- tools -----------------------------------------------------------

    def list_tables(self) -> list[str]:
        return self._call("list_tables", {})

    def describe_schema(self, table_name: str) -> dict:
        return self._call("describe_schema", {"table_name": table_name})

    def run_query(self, sql: str) -> tuple[list[str], list[list]]:
        """Return (columns, rows); raise QueryFailed with the server's message on error."""
        payload = self._call("run_query", {"sql": sql})
        if not payload.get("ok"):
            raise QueryFailed(payload.get("error", "Unknown error"))
        return payload["columns"], payload["rows"]
    
    def estimate_cost(self, sql: str) -> float | None:
        return self._call("explain_query", {"sql": sql}).get("total_cost")
    
    def close(self):
        if self._stop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._stop.set)
            try:
                self._main_future.result(10)
            except Exception:
                pass
            self._loop.call_soon_threadsafe(self._loop.stop)


@lru_cache(maxsize=1)
def get_client() -> MCPDatabaseClient:
    client = MCPDatabaseClient()
    atexit.register(client.close)
    return client