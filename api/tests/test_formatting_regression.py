"""Integration tests that verify the chat pipeline never leaks raw HTML
and always uses markdown formatting.

These tests assume the servers are already running:
  - Chat-UI bridge:    ws://localhost:3002/ws/chat
  - Accounting API:    http://localhost:8000/api/v1/chat/message

Note: test_api_rest_formatting uses Docker exec to bypass host port 8000
conflict (Micro-SaaS Platform occupies 127.0.0.1:8000 on this machine).

Dependencies: websockets, httpx
"""

from __future__ import annotations

import asyncio
import json
import subprocess

import websockets


CHAT_UI_WS_URL = "ws://localhost:3002/ws/chat"
TEST_MESSAGE = "Show me bank account 1000 detail"
TIMEOUT = 15

HTML_TAGS = ("<strong>", "<br", "<b>", "<em>", "<i>")


# ─────────────────────────────────────────────────────────────────────
# WebSocket (chat‑ui bridge) formatting regression test
# ─────────────────────────────────────────────────────────────────────

async def test_ws_formatting_regression() -> None:
    """Connect to the chat‑ui WebSocket bridge, send a request, and assert
    every response is free of raw HTML tags while at least one uses markdown.
    """
    received_messages: list[dict] = []

    async def collect(ws: websockets.WebSocketClientProtocol) -> None:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            received_messages.append(msg)

    try:
        async with websockets.connect(CHAT_UI_WS_URL) as ws:
            await ws.send(json.dumps({
                "type": "message",
                "content": TEST_MESSAGE,
            }))

            # Collect messages until the timeout expires
            await asyncio.wait_for(collect(ws), timeout=TIMEOUT)
    except asyncio.TimeoutError:
        pass  # expected — we stop collecting after the timeout
    except OSError as exc:
        raise AssertionError(
            f"Cannot connect to chat‑ui bridge at {CHAT_UI_WS_URL}: {exc}"
        ) from exc

    # Must have received at least one message
    assert received_messages, (
        f"No messages received from {CHAT_UI_WS_URL} within {TIMEOUT}s"
    )

    # Extract all text content strings
    text_contents: list[str] = []
    for msg in received_messages:
        content = msg.get("content", "")
        if isinstance(content, str) and content.strip():
            text_contents.append(content)

    # Assertion 1 — no raw HTML tags in any message content
    for content in text_contents:
        for tag in HTML_TAGS:
            assert tag not in content, (
                f"Raw HTML tag {tag!r} found in message content:\n"
                f"  {content[:300]}"
            )

    # Assertion 2 — at least one message uses markdown bold
    assert any("**" in c for c in text_contents), (
        "No message content contains markdown bold (**). "
        f"Received {len(text_contents)} text messages: {text_contents}"
    )


# ─────────────────────────────────────────────────────────────────────
# REST API formatting regression test (via Docker internal network)
# ─────────────────────────────────────────────────────────────────────

def test_api_rest_formatting() -> None:
    """Post to the REST chat endpoint via Docker exec and verify no HTML,
    only markdown.  Uses Docker internal network to bypass host port 8000
    conflict with the Micro-SaaS Platform."""
    import json as _json

    cmd = [
        "docker", "exec", "accounting-gateway",
        "curl", "-s", "--connect-timeout", "5", "--max-time", "45",
        "http://accounting-api:8000/api/v1/chat/message",
        "-H", "Content-Type: application/json",
        "-d", _json.dumps({"session_id": "qa-rest", "message": TEST_MESSAGE}),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    assert result.returncode == 0, (
        f"Docker exec failed (stderr): {result.stderr[:500]}"
    )

    data = _json.loads(result.stdout)
    message_text = data.get("message", {}).get("text", "")

    assert message_text, (
        f"Response message.text is empty. Full response: {data}"
    )

    # Assertion 1 — no HTML tags
    for tag in HTML_TAGS:
        assert tag not in message_text, (
            f"Raw HTML tag {tag!r} found in REST response message.text:\n"
            f"  {message_text[:300]}"
        )

    # Assertion 2 — markdown bold present
    assert "**" in message_text, (
        "No markdown bold (**) in REST response message.text:\n"
        f"  {message_text[:300]}"
    )
