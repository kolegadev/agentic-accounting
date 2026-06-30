"""Katra Cognitive Memory client for Agentic Accounting.

Connects to a Katra-Agentic-Memory MCP server for persistent conversation
context, episodic memory, and semantic search across agent sessions.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

KATRA_URL: str = os.getenv("KATRA_MCP_URL", "http://localhost:3113/mcp")
KATRA_API_KEY: str = os.getenv("KATRA_API_KEY", "")
KATRA_ENABLED: bool = os.getenv("KATRA_ENABLED", "true").lower() == "true"


class KatraClient:
    """Async client for the Katra cognitive memory MCP server.

    Katra provides four memory modalities through a single Docker appliance:

    * **episodic** — conversation history and agent decision traces (MongoDB)
    * **semantic** — vector search across stored sessions (vector store)
    * **knowledge graph** — entity relationships between contacts, accounts,
      transactions, invoices
    * **temporal** — time-series awareness for trends, seasonality, deadlines

    All four layers are backed by MongoDB + Redis + MinIO inside the Katra
    container stack.  This client focuses on episodic memory (store
    conversation turns) and semantic search (retrieve relevant context).

    Connection is via JSON-RPC 2.0 over HTTP to the Katra MCP endpoint.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        user_id: str = "accounting-agent",
    ) -> None:
        full_url = (base_url or KATRA_URL).rstrip("/")
        self.base_url = full_url.rsplit("/", 1)[0]  # e.g. http://host:3113
        self.api_key = api_key or KATRA_API_KEY
        self.user_id = user_id
        self._request_id: int = 0
        self._mcp_message_url: str | None = None  # set after SSE handshake

    @property
    def enabled(self) -> bool:
        """Katra is enabled only when KATRA_ENABLED is true and a URL is set."""
        return KATRA_ENABLED and bool(self.base_url)

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    # ── MCP SSE handshake ────────────────────────────────────────────

    async def _ensure_initialized(self) -> None:
        """Perform the MCP SSE handshake if not already done.

        MCP SSE flow:
        1. GET /sse → receive endpoint event with message URI
        2. POST initialize to that URI
        """
        if self._mcp_message_url is not None:
            return

        headers = self._headers()
        headers["Accept"] = "text/event-stream"

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Step 1: open SSE and read the endpoint event
            async with client.stream("GET", f"{self.base_url}/sse", headers=headers) as resp:
                resp.raise_for_status()
                buffer = ""
                async for chunk in resp.aiter_text():
                    buffer += chunk
                    # Parse SSE: look for "event: endpoint\ndata: {...}\n\n"
                    while "\n\n" in buffer:
                        event_block, buffer = buffer.split("\n\n", 1)
                        if "event: endpoint" in event_block:
                            for line in event_block.split("\n"):
                                if line.startswith("data: "):
                                    data = json.loads(line[6:])
                                    self._mcp_message_url = data.get("uri", "/message")
                                    break
                        if self._mcp_message_url:
                            break
                    if self._mcp_message_url:
                        break

        if not self._mcp_message_url:
            self._mcp_message_url = "/message"  # fallback

        # Step 2: initialize
        try:
            await self._call_raw("initialize", {
                "protocolVersion": "0.1.0",
                "clientInfo": {"name": "accounting-chat", "version": "0.1.0"},
            })
        except KatraError:
            pass  # some servers don't require explicit init, keep going

    async def _call_raw(self, method: str, params: Optional[dict] = None) -> dict:
        """Send JSON-RPC without handshake check (used during init)."""
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }
        url = f"{self.base_url}{self._mcp_message_url or '/message'}"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=self._headers())
            resp.raise_for_status()
            body = resp.json()
            if "error" in body:
                err = body["error"]
                raise KatraError(f"Katra error {err.get('code')}: {err.get('message')}")
            return body.get("result", {})

    # ── low-level MCP transport ──────────────────────────────────────

    async def _call(self, method: str, params: Optional[dict] = None) -> dict:
        """Send a JSON-RPC 2.0 call, ensuring MCP handshake first."""
        await self._ensure_initialized()
        return await self._call_raw(method, params)

    # ── episodic memory (conversation persistence) ───────────────────

    async def store_conversation_event(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """Persist a single conversation turn as an episodic event.

        Returns the event ID assigned by Katra.
        """
        if not self.enabled:
            return ""
        try:
            result = await self._call("tools/call", {
                "name": "store_memory",
                "arguments": {
                    "content": content,
                    "user_id": self.user_id,
                    "category": "event",
                    "session_id": session_id,
                    "source": "accounting-chat",
                    "tags": ["conversation", role] + (
                        metadata.get("tags", []) if metadata else []
                    ),
                },
            })
            # Extract the event ID from the response
            inner = result.get("content", [{}])
            text = inner[0].get("text", "{}") if inner else "{}"
            data = json.loads(text)
            return data.get("event_id", data.get("id", ""))
        except KatraError:
            raise
        except Exception:
            return ""

    async def store_session_context(
        self,
        session_id: str,
        context: dict[str, Any],
    ) -> None:
        """Persist the full conversation context snapshot as a semantic fact."""
        if not self.enabled:
            return
        try:
            await self._call("tools/call", {
                "name": "add_semantic_fact",
                "arguments": {
                    "content": json.dumps(context, default=str),
                    "user_id": self.user_id,
                    "session_id": session_id,
                    "source": "accounting-context",
                    "tags": ["session-context"],
                },
            })
        except KatraError:
            raise
        except Exception:
            return

    # ── semantic search (context retrieval) ──────────────────────────

    async def search_relevant_context(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Semantic search across prior conversations for relevant context.

        Returns a list of memory items ranked by relevance.
        """
        if not self.enabled:
            return []
        try:
            result = await self._call("tools/call", {
                "name": "vector_search",
                "arguments": {
                    "query": query,
                    "user_id": self.user_id,
                    "limit": limit,
                },
            })
            inner = result.get("content", [{}])
            text = inner[0].get("text", "{}") if inner else "{}"
            data = json.loads(text)
            return data if isinstance(data, list) else data.get("items", data.get("results", []))
        except KatraError:
            raise
        except Exception:
            return []

    async def get_recent_events(
        self,
        session_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Retrieve recent episodic events for a session."""
        if not self.enabled:
            return []
        try:
            result = await self._call("tools/call", {
                "name": "temporal_recall",
                "arguments": {
                    "user_id": self.user_id,
                    "session_id": session_id,
                    "limit": limit,
                    "days": 7,
                },
            })
            inner = result.get("content", [{}])
            text = inner[0].get("text", "{}") if inner else "{}"
            data = json.loads(text)
            return data if isinstance(data, list) else data.get("items", data.get("events", []))
        except KatraError:
            raise
        except Exception:
            return []

    # ── health ───────────────────────────────────────────────────────

    async def health_check(self) -> bool:
        """Check whether Katra is reachable and responding."""
        try:
            await self._call("initialize", {})
            return True
        except Exception:
            return False


class KatraError(RuntimeError):
    """Raised when Katra returns an error or is unreachable."""


# Singletons — created lazily so tests can mock
_katra_client: Optional[KatraClient] = None


def get_katra_client() -> KatraClient:
    """Return the singleton KatraClient, creating it on first access."""
    global _katra_client
    if _katra_client is None:
        _katra_client = KatraClient()
    return _katra_client
