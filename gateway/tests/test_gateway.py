"""Tests for MCP Gateway endpoints."""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Set the registry path to the project-level skills directory before importing server
os.environ.setdefault(
    "SKILL_REGISTRY_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "skills", "registry.yaml"),
)

from src.server import app


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Async client for the FastAPI test app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    """GET /health returns 200 and {"status": "ok"}."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient) -> None:
    """GET / returns service info."""
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "Agentic Accounting MCP Gateway"
    assert "endpoints" in data
    assert "tools_count" in data


@pytest.mark.asyncio
async def test_initialize(client: AsyncClient) -> None:
    """MCP initialize returns server info + capabilities."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {},
    }
    resp = await client.post("/message", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["jsonrpc"] == "2.0"
    assert data["id"] == 1
    assert "result" in data
    result = data["result"]
    assert result["protocolVersion"] == "0.1.0"
    assert result["serverInfo"]["name"] == "agentic-accounting-mcp"
    assert "tools" in result["capabilities"]
    assert "resources" in result["capabilities"]


@pytest.mark.asyncio
async def test_tools_list(client: AsyncClient) -> None:
    """MCP tools/list returns all tools."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {},
    }
    resp = await client.post("/message", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data
    result = data["result"]
    assert "tools" in result
    tools = result["tools"]
    assert len(tools) >= 25  # At least 25 tools

    # Check tool format
    for tool in tools:
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool

    # Verify some expected tools
    tool_names = {t["name"] for t in tools}
    assert "coa.list" in tool_names
    assert "gl.record_expense" in tool_names
    assert "contact.create" in tool_names
    assert "bank.import_csv" in tool_names
    assert "recon.start" in tool_names
    assert "invoice.create" in tool_names
    assert "vat.preview_return" in tool_names
    assert "report.run" in tool_names


@pytest.mark.asyncio
async def test_tools_call_unknown_tool(client: AsyncClient) -> None:
    """MCP tools/call with unknown tool returns error."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "nonexistent.tool", "arguments": {}},
    }
    resp = await client.post("/message", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_resources_list(client: AsyncClient) -> None:
    """MCP resources/list returns static resources."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "resources/list",
        "params": {},
    }
    resp = await client.post("/message", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data
    resources = data["result"]["resources"]
    assert len(resources) > 0
    # Check for COA templates
    uris = [r["uri"] for r in resources]
    assert any("coa://" in u for u in uris)
    assert any("bank://" in u for u in uris)


@pytest.mark.asyncio
async def test_sse_endpoint_connects(client: AsyncClient) -> None:
    """GET /sse returns SSE stream."""
    async with client.stream("GET", "/sse") as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_message_method_not_found(client: AsyncClient) -> None:
    """MCP unknown method returns error."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "nonexistent/method",
    }
    resp = await client.post("/message", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == -32601
