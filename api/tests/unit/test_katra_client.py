"""Unit tests for Katra cognitive memory MCP client."""

from __future__ import annotations

import json
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.services.katra_client import KatraClient, KatraError, get_katra_client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> KatraClient:
    """Return a KatraClient pointed at a test URL."""
    return KatraClient(base_url="http://katra:3113/mcp")


@pytest.fixture
def disabled_client(monkeypatch) -> KatraClient:
    """Return a KatraClient that is disabled (KATRA_ENABLED=False)."""
    monkeypatch.setattr("src.services.katra_client.KATRA_ENABLED", False)
    return KatraClient()


def _make_rpc_success(result: dict) -> dict:
    """Build a full JSON-RPC 2.0 success envelope."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": result,
    }


def _make_rpc_error(code: int, message: str) -> dict:
    """Build a full JSON-RPC 2.0 error envelope."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {"code": code, "message": message},
    }


def _mock_httpx_post(json_response: dict) -> AsyncMock:
    """Create a mocked AsyncClient whose post returns the given JSON-RPC response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = json_response

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post.return_value = mock_response
    return mock_client


# ---------------------------------------------------------------------------
# 1. test_katra_disabled_when_url_not_set
# ---------------------------------------------------------------------------


def test_katra_disabled_when_url_not_set(disabled_client: KatraClient) -> None:
    """When KATRA_MCP_URL is empty, client.enabled == False."""
    assert disabled_client.enabled is False


# ---------------------------------------------------------------------------
# 2. test_store_conversation_event_sends_correct_payload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_store_conversation_event_sends_correct_payload(client: KatraClient) -> None:
    """Mock httpx, verify store_memory is called with correct arguments."""
    mock_client = _mock_httpx_post(
        _make_rpc_success({"content": [{"text": '{"event_id":"evt-abc123"}'}]})
    )

    with patch("src.services.katra_client.httpx.AsyncClient", return_value=mock_client):
        event_id = await client.store_conversation_event(
            session_id="sess-001",
            role="user",
            content="Record an expense for office supplies",
            metadata={"tags": ["expense"]},
        )

    assert event_id == "evt-abc123"

    call_args = mock_client.__aenter__.return_value.post.call_args
    assert call_args[0][0] == "http://katra:3113/mcp"

    body = call_args[1]["json"]
    assert body["method"] == "tools/call"
    assert body["params"]["name"] == "store_memory"

    args = body["params"]["arguments"]
    assert args["content"] == "Record an expense for office supplies"
    assert args["user_id"] == "accounting-agent"
    assert args["category"] == "event"
    assert args["session_id"] == "sess-001"
    assert args["source"] == "accounting-chat"
    assert "conversation" in args["tags"]
    assert "user" in args["tags"]
    assert "expense" in args["tags"]


# ---------------------------------------------------------------------------
# 3. test_store_conversation_event_skips_when_disabled
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_store_conversation_event_skips_when_disabled(
    disabled_client: KatraClient,
) -> None:
    """enabled=False, should return "" without calling httpx."""
    mock_client = AsyncMock()

    with patch("src.services.katra_client.httpx.AsyncClient", return_value=mock_client):
        result = await disabled_client.store_conversation_event(
            session_id="sess-001",
            role="user",
            content="test",
        )

    assert result == ""
    mock_client.assert_not_called()


# ---------------------------------------------------------------------------
# 4. test_store_session_context
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_store_session_context(client: KatraClient) -> None:
    """Verify add_semantic_fact is called."""
    mock_client = _mock_httpx_post(_make_rpc_success({}))

    with patch("src.services.katra_client.httpx.AsyncClient", return_value=mock_client):
        await client.store_session_context(
            session_id="sess-001",
            context={"contact_id": "abc", "ledger": "main"},
        )

    call_args = mock_client.__aenter__.return_value.post.call_args
    body = call_args[1]["json"]
    assert body["params"]["name"] == "add_semantic_fact"

    args = body["params"]["arguments"]
    assert args["session_id"] == "sess-001"
    assert args["source"] == "accounting-context"
    assert "session-context" in args["tags"]

    parsed = json.loads(args["content"])
    assert parsed["contact_id"] == "abc"
    assert parsed["ledger"] == "main"


# ---------------------------------------------------------------------------
# 5. test_search_relevant_context
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_relevant_context(client: KatraClient) -> None:
    """Mock vector_search response, verify results are parsed."""
    mock_client = _mock_httpx_post(
        _make_rpc_success({
            "content": [
                {"text": json.dumps([
                    {"id": "mem-1", "content": "Expense entry", "score": 0.92},
                    {"id": "mem-2", "content": "Supplier payment", "score": 0.85},
                ])}
            ]
        })
    )

    with patch("src.services.katra_client.httpx.AsyncClient", return_value=mock_client):
        results = await client.search_relevant_context(
            query="office supplies expense",
            limit=5,
        )

    assert len(results) == 2
    assert results[0]["id"] == "mem-1"
    assert results[0]["content"] == "Expense entry"
    assert results[0]["score"] == 0.92
    assert results[1]["id"] == "mem-2"

    call_args = mock_client.__aenter__.return_value.post.call_args
    body = call_args[1]["json"]
    assert body["params"]["name"] == "vector_search"
    assert body["params"]["arguments"]["query"] == "office supplies expense"
    assert body["params"]["arguments"]["limit"] == 5


# ---------------------------------------------------------------------------
# 6. test_get_recent_events
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_recent_events(client: KatraClient) -> None:
    """Mock temporal_recall response, verify events list."""
    mock_client = _mock_httpx_post(
        _make_rpc_success({
            "content": [
                {"text": json.dumps([
                    {"event_id": "evt-1", "role": "user", "content": "Hello"},
                    {"event_id": "evt-2", "role": "assistant", "content": "Hi there"},
                ])}
            ]
        })
    )

    with patch("src.services.katra_client.httpx.AsyncClient", return_value=mock_client):
        events = await client.get_recent_events(
            session_id="sess-001",
            limit=10,
        )

    assert len(events) == 2
    assert events[0]["event_id"] == "evt-1"
    assert events[0]["role"] == "user"
    assert events[1]["content"] == "Hi there"

    call_args = mock_client.__aenter__.return_value.post.call_args
    body = call_args[1]["json"]
    assert body["params"]["name"] == "temporal_recall"
    assert body["params"]["arguments"]["session_id"] == "sess-001"
    assert body["params"]["arguments"]["limit"] == 10


# ---------------------------------------------------------------------------
# 7. test_health_check_success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_success(client: KatraClient) -> None:
    """Mock initialize returns ok."""
    mock_client = _mock_httpx_post(_make_rpc_success({"status": "ok"}))

    with patch("src.services.katra_client.httpx.AsyncClient", return_value=mock_client):
        result = await client.health_check()

    assert result is True

    call_args = mock_client.__aenter__.return_value.post.call_args
    body = call_args[1]["json"]
    assert body["method"] == "initialize"


# ---------------------------------------------------------------------------
# 8. test_health_check_failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_failure(client: KatraClient) -> None:
    """Mock httpx raises exception, returns False."""
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post.side_effect = Exception("Connection refused")

    with patch("src.services.katra_client.httpx.AsyncClient", return_value=mock_client):
        result = await client.health_check()

    assert result is False


# ---------------------------------------------------------------------------
# 9. test_katra_error_raised_on_mcp_error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_katra_error_raised_on_mcp_error(client: KatraClient) -> None:
    """Mock JSON-RPC error response, assert KatraError raised."""
    mock_client = _mock_httpx_post(
        _make_rpc_error(-32000, "Internal Katra error")
    )

    with patch("src.services.katra_client.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(KatraError, match="Katra error -32000"):
            await client.store_conversation_event(
                session_id="sess-001",
                role="user",
                content="test",
            )


# ---------------------------------------------------------------------------
# 10. test_graceful_degradation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_graceful_degradation_store_returns_empty(client: KatraClient) -> None:
    """When httpx raises, store returns "" without crashing."""
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post.side_effect = httpx.ConnectError(
        "Connection refused"
    )

    with patch("src.services.katra_client.httpx.AsyncClient", return_value=mock_client):
        result = await client.store_conversation_event(
            session_id="sess-001",
            role="user",
            content="test",
        )

    assert result == ""


@pytest.mark.asyncio
async def test_graceful_degradation_search_returns_empty(client: KatraClient) -> None:
    """When httpx raises, search returns [] without crashing."""
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post.side_effect = httpx.TimeoutException(
        "Timeout"
    )

    with patch("src.services.katra_client.httpx.AsyncClient", return_value=mock_client):
        results = await client.search_relevant_context("test query")

    assert results == []
