"""MCP Gateway Server — SSE transport + JSON-RPC handler for Agentic Accounting.

Exposes all 40+ accounting tools via the Model Context Protocol (MCP)
over Server-Sent Events (SSE) transport on port 3200.
"""

from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from src.tool_registry import get_registry

# ── Configuration ──────────────────────────────────────────────────────────

API_BASE_URL: str = os.environ.get("API_BASE_URL", "http://accounting-api:8000")
MCP_TRANSPORT: str = os.environ.get("MCP_TRANSPORT", "sse")
SERVER_NAME: str = "agentic-accounting-mcp"
SERVER_VERSION: str = "0.1.0"
PROTOCOL_VERSION: str = "0.1.0"

# ── Lifespan ───────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle."""
    registry = get_registry()
    print(f"✓ MCP Gateway started — {registry.tool_count} tools loaded")
    print(f"  API backend: {API_BASE_URL}")
    print(f"  Transport: {MCP_TRANSPORT}")
    yield


# ── Application ────────────────────────────────────────────────────────────

app = FastAPI(
    title="Agentic Accounting MCP Gateway",
    description="MCP protocol gateway for Agentic Accounting — exposing 40+ tools via SSE transport",
    version=SERVER_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Models ─────────────────────────────────────────────────────────────────


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Union[int, str]] = None
    method: str
    params: Optional[Dict[str, Any]] = None


# ── Resources ──────────────────────────────────────────────────────────────

COA_TEMPLATES: List[str] = [
    "uk_sole_trader_no_vat",
    "uk_sole_trader_vat",
    "uk_limited_company_no_vat",
    "uk_limited_company_vat",
    "uk_partnership_no_vat",
    "uk_partnership_vat",
    "micro_entity_simplified",
    "property_landlord_vat",
]

BANK_TEMPLATES: List[str] = [
    "barclays",
    "hsbc",
    "lloyds",
    "natwest",
    "monzo",
    "starling",
    "revolut",
]


def build_resources() -> List[Dict[str, Any]]:
    """Build the static resources list for MCP resources/list."""
    resources: List[Dict[str, Any]] = []

    for tmpl in COA_TEMPLATES:
        resources.append({
            "uri": f"coa://templates/{tmpl}",
            "name": f"COA Template: {tmpl}",
            "description": f"Chart of Accounts template: {tmpl.replace('_', ' ').title()}",
            "mimeType": "application/json",
        })

    for tmpl in BANK_TEMPLATES:
        resources.append({
            "uri": f"bank://templates/{tmpl}",
            "name": f"Bank Template: {tmpl}",
            "description": f"Bank statement import template for {tmpl.title()}",
            "mimeType": "application/json",
        })

    return resources


# ── MCP JSON-RPC Handler ──────────────────────────────────────────────────


def jsonrpc_response(id: Optional[Union[int, str]], result: Any) -> Dict[str, Any]:
    """Build a JSON-RPC 2.0 success response."""
    return {"jsonrpc": "2.0", "id": id, "result": result}


def jsonrpc_error(
    id: Optional[Union[int, str]],
    code: int,
    message: str,
    data: Any = None,
) -> Dict[str, Any]:
    """Build a JSON-RPC 2.0 error response."""
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": id, "error": err}


async def handle_initialize(
    request_id: Optional[Union[int, str]],
    params: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Handle MCP initialize request."""
    return jsonrpc_response(request_id, {
        "protocolVersion": PROTOCOL_VERSION,
        "serverInfo": {
            "name": SERVER_NAME,
            "version": SERVER_VERSION,
        },
        "capabilities": {
            "tools": {},
            "resources": {},
        },
    })


async def handle_tools_list(
    request_id: Optional[Union[int, str]],
    params: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Handle MCP tools/list."""
    registry = get_registry()
    tools = registry.list_tools()
    return jsonrpc_response(request_id, {"tools": tools})


async def handle_tools_call(
    request_id: Optional[Union[int, str]],
    params: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Handle MCP tools/call — proxy to accounting API."""
    if not params:
        return jsonrpc_error(request_id, -32602, "Missing params")

    tool_name = params.get("name", "")
    arguments = params.get("arguments", {}) or {}

    if not tool_name:
        return jsonrpc_error(request_id, -32602, "Missing tool name")

    registry = get_registry()
    endpoint_info = registry.get_endpoint(tool_name)

    if not endpoint_info:
        return jsonrpc_error(request_id, -32601, f"Unknown tool: {tool_name}")

    try:
        result = await proxy_to_api(tool_name, endpoint_info, arguments)
        content_text = json.dumps(result, default=str) if not isinstance(result, str) else result
        return jsonrpc_response(request_id, {
            "content": [{"type": "text", "text": content_text}]
        })
    except Exception as exc:
        return jsonrpc_error(request_id, -32000, f"Tool execution failed: {exc}")


async def handle_resources_list(
    request_id: Optional[Union[int, str]],
    params: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Handle MCP resources/list."""
    resources = build_resources()
    return jsonrpc_response(request_id, {"resources": resources})


async def handle_resources_read(
    request_id: Optional[Union[int, str]],
    params: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Handle MCP resources/read."""
    if not params or "uri" not in params:
        return jsonrpc_error(request_id, -32602, "Missing uri parameter")

    uri: str = params["uri"]
    resource_text = f"Resource: {uri}\n\nThis resource is available through the accounting API."

    return jsonrpc_response(request_id, {
        "contents": [
            {
                "uri": uri,
                "mimeType": "application/json",
                "text": resource_text,
            }
        ]
    })


# ── API Proxy ──────────────────────────────────────────────────────────────


async def proxy_to_api(
    tool_name: str,
    endpoint_info: Dict[str, Any],
    arguments: Dict[str, Any],
) -> Any:
    """Proxy a tool call to the accounting API."""
    method = endpoint_info["method"]
    path_template = endpoint_info["path"]
    param_map = endpoint_info.get("param_map", {})
    query_params = endpoint_info.get("query_params", [])
    body_as = endpoint_info.get("body_as", {})
    special = endpoint_info.get("special")

    # Handle special multi-step flows
    if special == "vat_preview":
        return await _handle_vat_preview(arguments)

    # Apply parameter mapping
    mapped_args: Dict[str, Any] = {}
    for k, v in arguments.items():
        mapped_key = param_map.get(k, k)
        mapped_args[mapped_key] = v

    # Build the actual URL path (replace path parameters)
    path = path_template
    for key, value in list(mapped_args.items()):
        placeholder = f"{{{key}}}"
        if placeholder in path:
            path = path.replace(placeholder, str(value))
            mapped_args.pop(key, None)

    # Split into query params and body
    query_dict: Dict[str, str] = {}
    body: Dict[str, Any] = {}

    for k, v in mapped_args.items():
        if k in query_params and method in ("GET",):
            if v is not None:
                query_dict[k] = str(v)
        else:
            body[k] = v

    # Build body for body_as mappings
    if body_as:
        body = {}
        for api_key, tool_key in body_as.items():
            if tool_key in mapped_args:
                body[api_key] = mapped_args[tool_key]

    url = f"{API_BASE_URL}{path}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        if method == "GET":
            resp = await client.get(url, params=query_dict if query_dict else None)
        elif method == "POST":
            resp = await client.post(url, json=body if body else None, params=query_dict if query_dict else None)
        elif method == "PATCH":
            resp = await client.patch(url, json=body if body else None)
        elif method == "PUT":
            resp = await client.put(url, json=body if body else None)
        elif method == "POST_FILE":
            return await _proxy_file_upload(url, mapped_args, query_dict, arguments)
        else:
            resp = await client.post(url, json=body if body else None, params=query_dict if query_dict else None)

        if resp.status_code >= 400:
            detail = resp.text[:500]
            raise RuntimeError(f"API returned {resp.status_code}: {detail}")

        try:
            return resp.json()
        except Exception:
            return resp.text


async def _proxy_file_upload(
    url: str,
    mapped_args: Dict[str, Any],
    query_dict: Dict[str, str],
    original_args: Dict[str, Any],
) -> Any:
    """Handle file upload proxy."""
    file_path = original_args.get("file_path", "")
    if not file_path:
        raise RuntimeError("file_path is required for file import tools")

    try:
        with open(file_path, "rb") as f:
            file_content = f.read()
    except FileNotFoundError:
        raise RuntimeError(f"File not found: {file_path}")

    filename = os.path.basename(file_path)

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            url,
            params=query_dict if query_dict else None,
            files={"file": (filename, file_content)},
        )

        if resp.status_code >= 400:
            detail = resp.text[:500]
            raise RuntimeError(f"File import API returned {resp.status_code}: {detail}")

        try:
            return resp.json()
        except Exception:
            return resp.text


async def _handle_vat_preview(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle VAT preview: create period + calculate return."""
    start_date = arguments.get("start_date", "")
    end_date = arguments.get("end_date", "")

    if not start_date or not end_date:
        raise RuntimeError("start_date and end_date are required for VAT preview")

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: Create VAT period
        create_url = f"{API_BASE_URL}/api/v1/vat/periods"
        create_resp = await client.post(create_url, json={
            "start_date": start_date,
            "end_date": end_date,
            "scheme": "standard",
        })

        if create_resp.status_code >= 400:
            raise RuntimeError(f"Failed to create VAT period: {create_resp.text[:300]}")

        period = create_resp.json()
        period_id = period.get("id")

        if not period_id:
            raise RuntimeError("VAT period created but no ID returned")

        # Step 2: Calculate the return
        calc_url = f"{API_BASE_URL}/api/v1/vat/periods/{period_id}/calculate"
        calc_resp = await client.post(calc_url)

        if calc_resp.status_code >= 400:
            raise RuntimeError(f"Failed to calculate VAT return: {calc_resp.text[:300]}")

        result = calc_resp.json()
        result["period_id"] = period_id
        result["period"] = period
        return result


# ── Route Handlers ─────────────────────────────────────────────────────────


@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint — return service information."""
    registry = get_registry()
    return {
        "service": "Agentic Accounting MCP Gateway",
        "version": SERVER_VERSION,
        "protocol": "MCP (Model Context Protocol)",
        "transport": MCP_TRANSPORT,
        "endpoints": {
            "sse": "/sse",
            "message": "/message",
            "health": "/health",
        },
        "tools_count": registry.tool_count,
        "api_backend": API_BASE_URL,
        "docs": "/docs",
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/sse")
async def sse_endpoint(request: Request) -> StreamingResponse:
    """SSE endpoint — persistent connection for MCP notifications.

    Uses Starlette's native StreamingResponse instead of sse-starlette
    to avoid EventSourceResponse background-task issues with ASGI test
    transports.  The wire protocol is identical — standard
    ``text/event-stream`` with ``event:`` / ``data:`` fields.
    """

    async def event_stream() -> AsyncGenerator[str, None]:
        import asyncio

        # 1) Tell the client where to POST JSON-RPC messages
        yield _sse_event("endpoint", json.dumps({"uri": "/message"}))

        # 2) Server metadata
        registry = get_registry()
        yield _sse_event(
            "server_info",
            json.dumps({
                "name": SERVER_NAME,
                "version": SERVER_VERSION,
                "tools": registry.tool_count,
                "connected_at": datetime.now(timezone.utc).isoformat(),
            }),
        )

        # 3) Keep-alive heartbeats every 30 s
        while True:
            try:
                if await request.is_disconnected():
                    break
                yield _sse_event(
                    "heartbeat",
                    json.dumps({"timestamp": datetime.now(timezone.utc).isoformat()}),
                )
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception:
                break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def _sse_event(event: str, data: str) -> str:
    """Format a single SSE event as a wire-format string."""
    return f"event: {event}\ndata: {data}\n\n"


@app.post("/message")
async def message_handler(request: Request) -> JSONResponse:
    """MCP JSON-RPC message handler."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            content=jsonrpc_error(None, -32700, "Parse error"),
            status_code=400,
        )

    req = JSONRPCRequest(**body)
    method = req.method
    rid = req.id
    params = req.params

    handlers: Dict[str, Any] = {
        "initialize": handle_initialize,
        "tools/list": handle_tools_list,
        "tools/call": handle_tools_call,
        "resources/list": handle_resources_list,
        "resources/read": handle_resources_read,
    }

    handler = handlers.get(method)
    if handler is None:
        return JSONResponse(
            content=jsonrpc_error(rid, -32601, f"Method not found: {method}"),
            status_code=200,
        )

    try:
        result = await handler(rid, params)
        return JSONResponse(content=result, status_code=200)
    except Exception as exc:
        return JSONResponse(
            content=jsonrpc_error(rid, -32603, f"Internal error: {exc}"),
            status_code=200,
        )
