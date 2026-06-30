"""Chat UI server for Agentic Accounting — serves the HTML frontend and bridges
WebSocket connections to the accounting API backend.

Pattern: Follows the Git-Maid pattern — single HTML file, FastAPI + WebSocket.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path

import httpx
import json as _json
import logging
import re
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

logger = logging.getLogger("chat-ui")


def _instrument_log(module: str, function: str, event: str, **kwargs) -> None:
    """Phase 2 structured logging for chat-ui bridge — mirrors
    the API-side instrument.py contract-check format."""
    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "correlation_id": kwargs.pop("correlation_id", "no-correlation-id"),
        "module": module,
        "function": function,
        "event": event,
        "state_snapshot": kwargs,
    }
    logger.warning("INSTRUMENT %s", _json.dumps(entry, default=str))

API_BASE_URL = os.getenv("API_BASE_URL", "http://accounting-api:8000")


def _strip_html(text: str) -> str:
    """Last-resort sanitizer: convert any HTML tags to plain-text equivalents
    so the frontend's markdown renderer can process them cleanly."""
    if not text or "<" not in text:
        return text
    text = re.sub(r"<(strong|b)[^>]*>(.*?)</\1>", r"**\2**", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<(em|i)[^>]*>(.*?)</\1>", r"*\2*", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"</?[ou]l[^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _sanitize_msg(obj):
    """Recursively sanitize every string in a JSON-serialisable object.
    No HTML tag can survive this — every field of every message is cleaned."""
    if isinstance(obj, str):
        return _strip_html(obj)
    if isinstance(obj, dict):
        return {k: _sanitize_msg(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_msg(v) for v in obj]
    return obj

app = FastAPI(title="Agentic Accounting Chat UI", version="0.1.0")

UI_DIR = Path(__file__).parent


@app.get("/")
async def root():
    """Serve the chat UI from disk or embedded fallback."""
    index_path = UI_DIR / "index.html"
    content = index_path.read_text() if index_path.exists() else _get_ui_html()
    headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return HTMLResponse(content=content, headers=headers)


@app.get("/api/health")
async def health():
    """Check if the accounting API backend is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{API_BASE_URL}/health")
            return {
                "status": "ok",
                "backend": "connected" if resp.status_code == 200 else "unhealthy",
            }
    except Exception:
        return {"status": "ok", "backend": "unreachable"}


@app.get("/api/account")
async def account():
    """Return backend connection info."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{API_BASE_URL}/health")
            return {
                "backend_configured": resp.status_code == 200,
                "api_base_url": API_BASE_URL,
            }
    except Exception:
        return {"backend_configured": False, "api_base_url": API_BASE_URL}


@app.post("/api/settings")
async def update_settings(data: dict):
    """Update API backend URL (runtime override)."""
    global API_BASE_URL
    new_url = (data.get("api_base_url") or "").strip()
    if new_url:
        API_BASE_URL = new_url
        return {"status": "ok", "updated": ["api_base_url"], "message": "Settings saved. Reconnect to use new URL."}
    return {"status": "ok", "updated": [], "message": "No settings changed."}


# ---------------------------------------------------------------------------
# WebSocket chat bridge
# ---------------------------------------------------------------------------

@app.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    """Bridge browser WebSocket to the accounting API WebSocket.

    Translates message formats between the Git-Maid UI protocol and the
    accounting API's chat protocol.
    """
    await ws.accept()

    # Accept client-supplied session_id if provided (enables session persistence across refreshes)
    client_sid = ws.query_params.get("session_id")
    session_id = client_sid if client_sid else str(uuid.uuid4())
    backend_ws_url = f"{API_BASE_URL.replace('http', 'ws')}/api/v1/ws/chat/{session_id}"

    await ws.send_text(json.dumps({
        "type": "connected",
        "session_id": session_id,
    }))

    try:
        import websockets as ws_client

        async def forward_to_backend(backend):
            """Read browser messages, translate, and send to backend."""
            try:
                while True:
                    data = await ws.receive_text()
                    msg = json.loads(data)
                    msg_type = msg.get("type", "message")

                    if msg_type == "message":
                        content = msg.get("content", "")
                        persona = msg.get("persona", "professional")
                        # ── I7: log every user message through bridge ────
                        _instrument_log(
                            "chat_ui_bridge", "forward_to_backend", "message_forward",
                            correlation_id="via-websocket-bridge",
                            direction="browser_to_backend",
                            msg_type="message",
                            content_chars=len(content),
                            session_id=session_id,
                        )
                        await backend.send(json.dumps({
                            "type": "user_message",
                            "session_id": session_id,
                            "content": content,
                            "persona": persona,
                        }))
                    elif msg_type in ("confirm", "reject"):
                        await backend.send(json.dumps({
                            "type": "confirmation_response",
                            "session_id": session_id,
                            "confirmed": msg_type == "confirm",
                        }))
                    elif msg_type == "stop":
                        # Forward stop to backend so it can cancel processing
                        try:
                            await backend.send(json.dumps({"type": "stop", "session_id": session_id}))
                        except Exception:
                            pass
                        await ws.send_text(json.dumps({
                            "type": "cancelled",
                            "content": "Processing stopped.",
                        }))
                    elif msg_type == "ping":
                        await ws.send_text(json.dumps({"type": "pong"}))

            except WebSocketDisconnect:
                pass

        async def forward_to_browser(backend):
            """Read backend messages, translate, and send to browser."""
            _send = lambda m: ws.send_text(json.dumps(_sanitize_msg(m)))
            try:
                async for raw in backend:
                    msg = json.loads(raw)
                    msg_type = msg.get("type", "")

                    if msg_type == "error":
                        await _send({
                            "type": "error",
                            "content": msg.get("message", msg.get("content", "Backend error")),
                        })

                    elif msg_type == "tool_call":
                        skill_id = msg.get("skill_id", "unknown")
                        params = msg.get("params", {})
                        await _send({
                            "type": "tool_calls",
                            "content": f"Invoking {skill_id}...",
                            "tools": [{
                                "id": msg.get("tool_call_id", ""),
                                "name": skill_id,
                                "args": params,
                            }],
                        })
                        await _send({
                            "type": "thinking",
                            "content": f"Processing {skill_id}...",
                        })

                    elif msg_type == "tool_result":
                        result_data = msg.get("result", {})
                        response = result_data.get("response", "")
                        skill_name = result_data.get("skill", "unknown")
                        persona = result_data.get("persona", "professional")

                        await _send({
                            "type": "text",
                            "content": response or f"Completed {skill_name}.",
                            "persona": persona,
                            "session_id": session_id,
                        })

                    elif msg_type == "confirmation_request":
                        await _send({
                            "type": "confirm_request",
                            "content": msg.get("message", "Confirm this action?"),
                            "tools": [msg.get("action", "unknown")],
                        })

                    elif msg_type == "stream_start":
                        pass  # Skip — tokens follow

                    elif msg_type in ("stream_token", "stream_end"):
                        token = msg.get("token", msg.get("content", ""))
                        if token:
                            await _send({
                                "type": "text",
                                "content": token,
                            })

                    else:
                        content = msg.get("content", "")
                        if content:
                            await _send({
                                "type": "text",
                                "content": content,
                            })

            except Exception as exc:
                logger.warning("forward_to_browser: backend connection error: %s", exc)

        # ── Reconnection loop with exponential backoff ────────────────────
        retry_delay = 1
        max_delay = 30

        while True:
            try:
                async with ws_client.connect(
                    backend_ws_url,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=10,
                ) as backend:
                    retry_delay = 1  # reset on successful connect
                    logger.info("Connected to accounting backend WebSocket (session %s)", session_id)
                    await ws.send_text(json.dumps({
                        "type": "backend_reconnected",
                        "session_id": session_id,
                    }))
                    await asyncio.gather(
                        forward_to_backend(backend),
                        forward_to_browser(backend),
                    )
            except (WebSocketDisconnect, ws_client.exceptions.ConnectionClosedOK):
                logger.info("Browser WebSocket closed cleanly (session %s)", session_id)
                break
            except ws_client.exceptions.ConnectionClosedError as e:
                logger.warning("Backend WebSocket closed: %s — retrying in %ds", e, retry_delay)
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_delay)
            except Exception as e:
                logger.error("Bridge error (session %s): %s", session_id, e)
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_delay)
        # ── End reconnection loop ─────────────────────────────────────────

    except ImportError:
        # websockets lib not available — fall back to HTTP REST bridge
        await _fallback_http_bridge(ws, session_id)
    except Exception as e:
        logger.error("Fatal bridge error (session %s): %s", session_id, e)
        await ws.send_text(json.dumps({
            "type": "error",
            "content": f"Cannot connect to accounting backend: {e}",
        }))


async def _fallback_http_bridge(ws: WebSocket, session_id: str):
    """Fallback: use HTTP REST endpoint when WebSocket bridge is not available."""
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type", "message")

            if msg_type == "message":
                content = msg.get("content", "")
                persona = msg.get("persona", "professional")

                await ws.send_text(json.dumps({
                    "type": "thinking",
                    "content": "Processing...",
                }))

                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{API_BASE_URL}/api/v1/chat/message",
                        json={
                            "session_id": session_id,
                            "message": content,
                            "persona": persona,
                        },
                    )
                    if resp.status_code == 200:
                        result = resp.json()
                        response_text = result.get("message", {}).get("text", "I processed your request.")
                        tool_call = result.get("tool_call")

                        # Send tool call info if present
                        if tool_call:
                            await ws.send_text(json.dumps({
                                "type": "tool_calls",
                                "content": f"Invoking {tool_call.get('skill_id', 'unknown')}...",
                                "tools": [{
                                    "id": tool_call.get("tool_call_id", ""),
                                    "name": tool_call.get("skill_id", "unknown"),
                                    "args": tool_call.get("params", {}),
                                }],
                            }))

                        await ws.send_text(json.dumps({
                            "type": "text",
                            "content": response_text,
                            "session_id": session_id,
                        }))
                    else:
                        await ws.send_text(json.dumps({
                            "type": "error",
                            "content": f"Backend error: {resp.status_code}",
                        }))

            elif msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))

    except WebSocketDisconnect:
        pass


# ---------------------------------------------------------------------------
# Server launcher
# ---------------------------------------------------------------------------

def start_server(host: str = "0.0.0.0", port: int = 3000):
    """Start the uvicorn server."""
    ui_path = UI_DIR / "index.html"
    if not ui_path.exists():
        _generate_ui(ui_path)

    print(f"🚀 Agentic Accounting Chat UI starting at http://{host}:{port}")
    print("Press Ctrl+C to stop.")

    uvicorn.run(
        "server:app",
        host=host,
        port=port,
        log_level="warning",
    )


def _generate_ui(path: Path):
    """Write the embedded UI HTML to disk."""
    html = _get_ui_html()
    path.write_text(html)


def _get_ui_html() -> str:
    """Return the complete UI HTML as a string (accounting themed)."""
    return r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agentic Accounting — AI Bookkeeper</title>
<style>
  :root {
    --bg: #0d0d0d;
    --surface: #161616;
    --surface2: #1e1e1e;
    --border: #2a2a2a;
    --text: #d4d4d4;
    --text-dim: #6b6b6b;
    --accent: #4ec9b0;
    --accent-glow: rgba(78,201,176,0.15);
    --accent-text: #1a1a1a;
    --green: #4ec9b0;
    --red: #f44747;
    --blue: #569cd6;
    --radius: 8px;
    --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --mono: "SF Mono", "JetBrains Mono", "Fira Code", monospace;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: var(--font);
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  /* Header */
  header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 12px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }
  header .logo {
    font-size: 18px;
    font-weight: 700;
    color: var(--accent);
    letter-spacing: -0.3px;
  }
  header .logo span { color: var(--text-dim); font-weight: 400; }
  header .status {
    margin-left: auto;
    font-size: 12px;
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--text-dim);
  }
  .status-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 6px rgba(78,201,176,0.4);
  }
  .status-dot.off { background: var(--red); box-shadow: 0 0 6px rgba(244,71,71,0.4); }

  /* Chat area */
  .chat-container {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .chat-container::-webkit-scrollbar { width: 6px; }
  .chat-container::-webkit-scrollbar-track { background: transparent; }
  .chat-container::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

  /* Messages */
  .msg {
    display: flex;
    flex-direction: column;
    max-width: 85%;
    animation: fadeIn 0.25s ease;
  }
  @keyframes fadeIn { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }
  .msg.user { align-self: flex-end; }
  .msg.assistant { align-self: flex-start; }
  .msg.system { align-self: center; max-width: 100%; }

  .msg-bubble {
    padding: 12px 16px;
    border-radius: var(--radius);
    line-height: 1.55;
    font-size: 14px;
    word-wrap: break-word;
  }
  .msg.user .msg-bubble {
    background: var(--accent);
    color: var(--accent-text);
    border-bottom-right-radius: 2px;
  }
  .msg.assistant .msg-bubble {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-bottom-left-radius: 2px;
  }
  .msg.system .msg-bubble {
    background: var(--surface);
    border: 1px solid var(--border);
    font-size: 13px;
    color: var(--text-dim);
    text-align: center;
    padding: 8px 16px;
  }
  .msg.system.error .msg-bubble {
    border-color: rgba(244,71,71,0.3);
    color: var(--red);
  }
  .msg-bubble p { margin-bottom: 8px; }
  .msg-bubble p:last-child { margin-bottom: 0; }
  .msg-bubble code {
    font-family: var(--mono);
    font-size: 13px;
    background: rgba(255,255,255,0.06);
    padding: 2px 6px;
    border-radius: 3px;
  }
  .msg-bubble pre {
    background: rgba(0,0,0,0.3);
    border-radius: 6px;
    padding: 12px;
    overflow-x: auto;
    margin: 8px 0;
    font-family: var(--mono);
    font-size: 12px;
    line-height: 1.5;
  }

  /* Tool call display */
  .tool-call {
    margin-top: 6px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    font-size: 13px;
  }
  .tool-call-header {
    background: var(--surface);
    padding: 8px 12px;
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    user-select: none;
  }
  .tool-call-header:hover { background: var(--surface2); }
  .tool-call-icon { font-size: 14px; }
  .tool-call-name { font-family: var(--mono); color: var(--blue); font-size: 12px; }
  .tool-call-chevron { margin-left: auto; color: var(--text-dim); transition: transform 0.2s; }
  .tool-call.open .tool-call-chevron { transform: rotate(180deg); }
  .tool-call-body {
    display: none;
    padding: 10px 12px;
    background: rgba(0,0,0,0.2);
    font-family: var(--mono);
    font-size: 12px;
    white-space: pre-wrap;
    color: var(--text-dim);
    max-height: 200px;
    overflow-y: auto;
  }
  .tool-call.open .tool-call-body { display: block; }

  /* Confirmation bar */
  .confirm-bar {
    align-self: center;
    background: var(--surface);
    border: 1px solid var(--accent);
    border-radius: var(--radius);
    padding: 14px 20px;
    display: flex;
    align-items: center;
    gap: 14px;
    animation: fadeIn 0.25s ease;
  }
  .confirm-bar .text { font-size: 14px; color: var(--accent); flex: 1; }
  .confirm-bar button {
    padding: 8px 18px;
    border-radius: 5px;
    border: none;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }
  .btn-confirm {
    background: var(--accent);
    color: var(--accent-text);
  }
  .btn-confirm:hover { filter: brightness(1.1); }
  .btn-reject {
    background: transparent;
    color: var(--text-dim);
    border: 1px solid var(--border) !important;
  }
  .btn-reject:hover { color: var(--text); border-color: var(--text-dim) !important; }

  /* Input area */
  .input-container {
    background: var(--surface);
    border-top: 1px solid var(--border);
    padding: 14px 20px;
    display: flex;
    gap: 10px;
    flex-shrink: 0;
  }
  .input-container input {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 12px 16px;
    color: var(--text);
    font-size: 14px;
    font-family: var(--font);
    outline: none;
    transition: border-color 0.15s;
  }
  .input-container input:focus { border-color: var(--accent); }
  .input-container input::placeholder { color: var(--text-dim); }
  .input-container button {
    background: var(--accent);
    color: var(--accent-text);
    border: none;
    border-radius: var(--radius);
    padding: 0 20px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }
  .input-container button:hover { filter: brightness(1.1); }
  .input-container button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
  .input-container button.btn-stop {
    background: var(--red);
    color: #fff;
    animation: pulseStop 1.5s infinite;
  }
  @keyframes pulseStop {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
  }

  /* Settings modal */
  .settings-btn {
    background: none;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    color: var(--text-dim);
    font-size: 16px;
    padding: 4px 8px;
    cursor: pointer;
    transition: all 0.15s;
    margin-right: 8px;
  }
  .settings-btn:hover { color: var(--text); border-color: var(--text-dim); }
  .modal-overlay {
    display: none;
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.7);
    z-index: 100;
    align-items: center;
    justify-content: center;
  }
  .modal-overlay.open { display: flex; }
  .modal {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    width: 90%;
    max-width: 440px;
    animation: fadeIn 0.2s ease;
  }
  .modal h2 { font-size: 18px; color: var(--accent); margin-bottom: 20px; }
  .modal label { font-size: 12px; color: var(--text-dim); display: block; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
  .modal input {
    width: 100%;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 10px 12px;
    color: var(--text);
    font-size: 13px;
    font-family: var(--mono);
    margin-bottom: 14px;
    outline: none;
    transition: border-color 0.15s;
  }
  .modal input:focus { border-color: var(--accent); }
  .modal .account-info {
    background: var(--surface2);
    border-radius: var(--radius);
    padding: 10px 14px;
    margin-bottom: 16px;
    font-size: 13px;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .modal .account-info .dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--green);
    flex-shrink: 0;
  }
  .modal .account-info .dot.off { background: var(--red); }
  .modal .account-info .label { color: var(--text-dim); }
  .modal .account-info .value { color: var(--accent); font-weight: 600; }
  .modal .account-info .source { color: var(--text-dim); font-size: 11px; }
  .modal .btn-row { display: flex; gap: 10px; justify-content: flex-end; margin-top: 6px; }
  .modal .btn-row button {
    padding: 8px 18px;
    border-radius: 5px;
    border: none;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }
  .modal .btn-save { background: var(--accent); color: var(--accent-text); }
  .modal .btn-save:hover { filter: brightness(1.1); }
  .modal .btn-cancel { background: transparent; color: var(--text-dim); border: 1px solid var(--border); }
  .modal .btn-cancel:hover { color: var(--text); }
  .modal .saved-msg {
    text-align: center;
    color: var(--green);
    font-size: 13px;
    margin-top: 10px;
    display: none;
  }

  /* Loading dots */
  .typing-dots {
    display: flex;
    gap: 4px;
    padding: 4px 0;
  }
  .typing-dots span {
    width: 6px; height: 6px;
    background: var(--text-dim);
    border-radius: 50%;
    animation: bounce 1.2s infinite;
  }
  .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
  .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes bounce { 0%,60%,100% { transform:translateY(0); } 30% { transform:translateY(-6px); } }
</style>
</head>
<body>

<header>
  <div class="logo">ledger.chat <span>/ your AI bookkeeper</span></div>
  <div style="background:var(--accent);color:var(--accent-text);font-size:10px;padding:2px 8px;border-radius:3px;font-weight:700;" id="version-tag">MVP</div>
  <div class="status">
    <button class="settings-btn" id="settings-btn" title="Settings">⚙</button>
    <span id="backend-status" style="color:var(--accent);font-weight:600;font-size:12px;margin-right:12px;"></span>
    <div class="status-dot" id="status-dot"></div>
    <span id="status-text">connecting...</span>
  </div>
</header>

<div class="chat-container" id="chat"></div>

<div class="input-container">
  <input id="msg-input" type="text" placeholder="Record a transaction, create an invoice, check your VAT..." disabled />
  <button id="send-btn" disabled>Send</button>
</div>

<!-- Settings Modal -->
<div class="modal-overlay" id="modal-overlay">
  <div class="modal">
    <h2>Settings</h2>
    <div class="account-info" id="settings-account">
      <div class="dot" id="settings-dot"></div>
      <div>
        <div>Backend: <span class="value" id="settings-url">...</span></div>
        <div class="source" id="settings-source">loading...</div>
      </div>
    </div>
    <label>Accounting API Base URL</label>
    <input type="text" id="settings-api-url" placeholder="http://accounting-api:8000" />
    <div class="btn-row">
      <button class="btn-cancel" onclick="closeSettings()">Cancel</button>
      <button class="btn-save" onclick="saveSettings()">Save &amp; Reconnect</button>
    </div>
    <div class="saved-msg" id="saved-msg">Saved! Reconnecting...</div>
  </div>
</div>

<script>
// --- Debug banner ---
var DEBUG = document.createElement('div');
DEBUG.style.cssText = 'position:fixed;top:8px;right:8px;background:#111;color:#4ec9b0;font:10px monospace;padding:3px 8px;z-index:999;max-width:360px;max-height:24px;overflow:hidden;border-radius:4px;border:1px solid #2a2a2a;opacity:0.75;transition:max-height 0.3s;cursor:pointer;';
DEBUG.id = 'debug-log';
DEBUG.title = 'Click to expand';
DEBUG.onclick = function() {
  if (DEBUG.style.maxHeight === '200px') {
    DEBUG.style.maxHeight = '24px';
    DEBUG.title = 'Click to expand';
  } else {
    DEBUG.style.maxHeight = '200px';
    DEBUG.style.overflowY = 'auto';
    DEBUG.title = 'Click to collapse';
  }
};
var DBG_CLOSE = document.createElement('span');
DBG_CLOSE.textContent = '\u00d7';
DBG_CLOSE.style.cssText = 'position:absolute;top:1px;right:4px;cursor:pointer;color:#6b6b6b;font-size:12px;display:none;';
DBG_CLOSE.onclick = function(e) { e.stopPropagation(); DEBUG.style.display = 'none'; };
DEBUG.appendChild(DBG_CLOSE);
var DBG_TEXT = document.createElement('div');
DBG_TEXT.style.cssText = 'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;';
DEBUG.appendChild(DBG_TEXT);
document.body.appendChild(DEBUG);

var _dbgTimeout = null;
function debug(msg) {
  DEBUG.style.display = 'block';
  DBG_TEXT.textContent = msg;
  if (msg.indexOf('FATAL') >= 0 || msg.indexOf('ERROR') >= 0) {
    DEBUG.style.color = '#f44747';
    DEBUG.style.borderColor = 'rgba(244,71,71,0.4)';
    DEBUG.style.maxHeight = '200px';
    DEBUG.style.overflowY = 'auto';
    DBG_CLOSE.style.display = 'inline';
    DBG_TEXT.style.whiteSpace = 'pre-wrap';
    DBG_TEXT.style.wordBreak = 'break-all';
    if (_dbgTimeout) clearTimeout(_dbgTimeout);
  } else if (msg.indexOf('WS onopen fired') >= 0) {
    if (_dbgTimeout) clearTimeout(_dbgTimeout);
    _dbgTimeout = setTimeout(function() { DEBUG.style.display = 'none'; }, 4000);
  } else {
    DBG_TEXT.style.whiteSpace = 'nowrap';
    DBG_TEXT.textContent = msg;
    DEBUG.style.maxHeight = '24px';
    DEBUG.style.overflowY = 'hidden';
  }
}

(function() {
  debug('Script starting...');

  var chat = document.getElementById('chat');
  var input = document.getElementById('msg-input');
  var sendBtn = document.getElementById('send-btn');
  var statusDot = document.getElementById('status-dot');
  var statusText = document.getElementById('status-text');

  debug('Elements found: chat=' + !!chat + ' input=' + !!input + ' sendBtn=' + !!sendBtn);

  var ws = null;
  var pendingConfirm = false;
  var isProcessing = false;

  function connect() {
    debug('connect() called');
    var protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    var host = location.hostname === 'localhost' || location.hostname === '::1'
      ? '127.0.0.1:' + location.port
      : location.host;
    var url = protocol + '//' + host + '/ws/chat';
    debug('WebSocket URL: ' + url);

    statusText.textContent = 'connecting to ' + url + '...';

    try {
      ws = new WebSocket(url);
      debug('WebSocket created, readyState=' + ws.readyState);
    } catch(e) {
      debug('WebSocket constructor ERROR: ' + e.message);
      return;
    }

    ws.onopen = function() {
      debug('WS onopen fired');
      setStatus(true, 'connected');
      input.disabled = false;
      sendBtn.disabled = false;
      input.focus();
    };

    ws.onclose = function(e) {
      debug('WS onclose fired, code=' + e.code + ' reason=' + (e.reason || 'none') + ' wasClean=' + e.wasClean);
      setStatus(false, 'disconnected (code ' + e.code + ')');
      input.disabled = true;
      sendBtn.disabled = true;
      setTimeout(connect, 3000);
    };

    ws.onmessage = function(e) {
      try {
        var msg = JSON.parse(e.data);
        var info = msg.type === 'thinking' ? (' (' + (msg.content||'') + ')') :
                   msg.type === 'tool_calls' ? (' [' + (msg.tools||[]).map(function(t){return t.name;}).join(', ') + ']') :
                   msg.type === 'error' ? (': ' + (msg.content||'')) :
                   msg.type === 'confirm_request' ? (' [' + (msg.tools||[]).join(', ') + ']') :
                   '';
        debug('WS msg: type=' + msg.type + info);
        handleMessage(msg);
      } catch (err) {
        debug('WS parse error: ' + err.message);
        setStatus(false, 'parse error: ' + err.message);
      }
    };

    ws.onerror = function(e) {
      debug('WS onerror fired, readyState=' + ws.readyState);
      setStatus(false, 'ws error');
    };
  }

  function setStatus(ok, text) {
    statusDot.className = 'status-dot' + (ok ? '' : ' off');
    statusText.textContent = text;
  }

  function setIsProcessing(processing) {
    isProcessing = processing;
    if (processing) {
      sendBtn.textContent = 'Stop';
      sendBtn.className = 'btn-stop';
      sendBtn.disabled = false;
    } else {
      sendBtn.textContent = 'Send';
      sendBtn.className = '';
      sendBtn.disabled = false;
    }
  }

  function handleMessage(msg) {
    removeTyping();

    switch (msg.type) {
      case 'connected':
        setStatus(true, 'connected');
        setIsProcessing(false);
        addMessage('assistant', msg.content);
        break;
      case 'text':
        setIsProcessing(false);
        addMessage('assistant', msg.content);
        break;
      case 'tool_calls':
        addToolCalls(msg.content, msg.tools);
        addTyping();
        break;
      case 'confirm_request':
        setIsProcessing(false);
        addConfirmBar(msg.content, msg.tools);
        pendingConfirm = true;
        break;
      case 'thinking':
        addTyping();
        break;
      case 'status':
        addMessage('system', msg.content);
        break;
      case 'cancelled':
        setIsProcessing(false);
        if (msg.content) addMessage('system', msg.content);
        break;
      case 'error':
        setIsProcessing(false);
        addMessage('system', msg.content, true);
        break;
      case 'pong':
        break;
    }
    scrollDown();
  }

  function addMessage(role, content, isError) {
    isError = isError || false;
    var div = document.createElement('div');
    div.className = 'msg ' + role + (isError ? ' error' : '');

    var bubble = document.createElement('div');
    bubble.className = 'msg-bubble';
    bubble.innerHTML = renderMarkdown(content);
    div.appendChild(bubble);

    chat.appendChild(div);
  }

  function addToolCalls(text, tools) {
    var div = document.createElement('div');
    div.className = 'msg assistant';

    if (text) {
      var bubble = document.createElement('div');
      bubble.className = 'msg-bubble';
      bubble.innerHTML = renderMarkdown(text);
      div.appendChild(bubble);
    }

    tools.forEach(function(t) {
      var tc = document.createElement('div');
      tc.className = 'tool-call';
      tc.innerHTML = '<div class="tool-call-header" onclick="this.parentElement.classList.toggle(\'open\')">' +
        '<span class="tool-call-icon">\ud83d\udd27</span>' +
        '<span class="tool-call-name">' + esc(t.name) + '</span>' +
        '<span class="tool-call-chevron">\u25be</span>' +
        '</div>' +
        '<div class="tool-call-body">' + esc(JSON.stringify(t.args, null, 2)) + '</div>';
      div.appendChild(tc);
    });

    chat.appendChild(div);
  }

  function addConfirmBar(text, tools) {
    var div = document.createElement('div');
    div.className = 'confirm-bar';
    div.id = 'confirm-bar';
    div.innerHTML = '<span class="text">\u26a0\ufe0f ' + esc(text) + '</span>' +
      '<button class="btn-confirm" onclick="confirmAction()">\u2713 Confirm</button>' +
      '<button class="btn-reject" onclick="rejectAction()">\u2717 Cancel</button>';
    chat.appendChild(div);
  }

  function addTyping() {
    removeTyping();
    var div = document.createElement('div');
    div.className = 'msg assistant';
    div.id = 'typing-indicator';
    div.innerHTML = '<div class="msg-bubble"><div class="typing-dots"><span></span><span></span><span></span></div></div>';
    chat.appendChild(div);
    scrollDown();
  }

  function removeTyping() {
    var el = document.getElementById('typing-indicator');
    if (el) el.remove();
  }

  function renderMarkdown(text) {
    if (!text) return '';
    // Strip raw HTML tags the LLM might emit (it should use markdown, but
    // sometimes it returns <br>, <strong>, <ul>, etc. — clean those up).
    var cleaned = text.replace(/<[^>]*>/g, '');
    return cleaned
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/```([^`]+)```/g, '<pre>$1</pre>')
      .replace(/^### (.+)/gm, '<strong>$1</strong>')
      .replace(/^## (.+)/gm, '<strong>$1</strong>')
      .replace(/^# (.+)/gm, '<strong>$1</strong>')
      .replace(/^- (.+)/gm, '\u2022 $1')
      .replace(/\n/g, '<br>');
  }

  function esc(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function scrollDown() {
    chat.scrollTop = chat.scrollHeight;
  }

  function sendMessage() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    if (isProcessing) {
      ws.send(JSON.stringify({ type: 'stop' }));
      return;
    }

    var text = input.value.trim();
    if (!text || pendingConfirm) return;

    addMessage('user', text);
    input.value = '';
    setIsProcessing(true);
    addTyping();

    ws.send(JSON.stringify({ type: 'message', content: text }));
  }

  window.confirmAction = function() {
    if (!ws || !pendingConfirm) return;
    removeConfirmBar();
    pendingConfirm = false;
    setIsProcessing(true);
    addTyping();
    ws.send(JSON.stringify({ type: 'confirm' }));
  };

  window.rejectAction = function() {
    if (!ws || !pendingConfirm) return;
    removeConfirmBar();
    pendingConfirm = false;
    setIsProcessing(true);
    addTyping();
    ws.send(JSON.stringify({ type: 'reject' }));
  };

  function removeConfirmBar() {
    var el = document.getElementById('confirm-bar');
    if (el) el.remove();
  }

  input.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') { e.preventDefault(); sendMessage(); }
  });
  sendBtn.addEventListener('click', sendMessage);

  connect();

  // --- Settings Modal ---

  window.openSettings = async function() {
    debug('openSettings() called');
    var overlay = document.getElementById('modal-overlay');
    overlay.classList.add('open');

    try {
      var resp = await fetch('/api/account');
      var data = await resp.json();

      document.getElementById('settings-url').textContent = data.api_base_url || 'not configured';
      document.getElementById('settings-source').textContent = data.backend_configured ? 'connected' : 'unreachable';
      var dot = document.getElementById('settings-dot');
      dot.className = dot.className.replace(' off', '');
      if (!data.backend_configured) dot.className += ' off';

      document.getElementById('settings-api-url').value = '';
      document.getElementById('saved-msg').style.display = 'none';
    } catch (e) {
      document.getElementById('settings-url').textContent = 'error';
      document.getElementById('settings-source').textContent = e.message;
    }
  };

  window.closeSettings = function() {
    document.getElementById('modal-overlay').classList.remove('open');
  };

  window.saveSettings = async function() {
    debug('saveSettings() called');
    var apiUrl = document.getElementById('settings-api-url').value.trim();
    debug('apiUrl=' + apiUrl);

    if (!apiUrl) {
      document.getElementById('saved-msg').textContent = 'Enter a backend URL.';
      document.getElementById('saved-msg').style.color = 'var(--red)';
      document.getElementById('saved-msg').style.display = 'block';
      return;
    }

    var saveBtn = document.querySelector('.btn-save');
    saveBtn.textContent = 'Saving...';
    saveBtn.disabled = true;

    try {
      debug('POST /api/settings...');
      var resp = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_base_url: apiUrl }),
      });
      var data = await resp.json();
      debug('Settings response: ' + JSON.stringify(data));

      if (data.status === 'ok') {
        document.getElementById('saved-msg').style.color = 'var(--green)';
        document.getElementById('saved-msg').textContent = 'Saved! Reconnecting...';
        document.getElementById('saved-msg').style.display = 'block';
        setTimeout(function() {
          if (ws) ws.close();
          connect();
        }, 800);
      } else {
        throw new Error(data.message || 'Unknown error');
      }
    } catch (e) {
      debug('saveSettings ERROR: ' + e.message);
      document.getElementById('saved-msg').textContent = 'Error: ' + e.message;
      document.getElementById('saved-msg').style.color = 'var(--red)';
      document.getElementById('saved-msg').style.display = 'block';
      saveBtn.textContent = 'Save & Reconnect';
      saveBtn.disabled = false;
    }
  };

  document.getElementById('settings-btn').addEventListener('click', window.openSettings);
  document.getElementById('modal-overlay').addEventListener('click', function(e) {
    if (e.target === e.currentTarget) window.closeSettings();
  });

})();
</script>

</body>
</html>'''


if __name__ == "__main__":
    start_server()
