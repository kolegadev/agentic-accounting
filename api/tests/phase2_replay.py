"""Phase 2 Replay — captures what the LLM actually receives.

Intended to run against a running accounting-api on port 8000
(docker compose up accounting-api).  Sends test messages via the
REST endpoint (simpler than WebSocket for instrumentation capture)
and collects the structured log output.

Usage:
    # Start the API (with Postgres + Redis):
    docker compose up -d postgres redis accounting-api

    # Wait for healthy, then run:
    python tests/phase2_replay.py

    # Collect logs:
    docker compose logs accounting-api 2>&1 | grep INSTRUMENT > phase2_logs.jsonl
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone

import httpx

API_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
CORRELATION_ID = str(uuid.uuid4())

TEST_MESSAGES = [
    # Basic accounting — tests tool context
    "Show me my chart of accounts",

    # Expense recording — tests double-entry awareness
    "Record a £50 expense for office supplies at Tesco",

    # Architecture awareness — LLM should know what Formance IS
    "What is Formance and how does it relate to my transactions?",

    # Memory awareness — LLM should know about Katra
    "Search my memory for recent transaction activity",

    # Multi-step workflow — tests tool chaining awareness
    "Create an invoice for Acme Ltd for £2,500 for consulting services",

    # VAT awareness — tests domain knowledge
    "Show me my VAT return for the current quarter",
]

# Names of common documentation files the LLM should reference
EXPECTED_DOC_SECTIONS = [
    "MCP_DOCUMENTATION",
    "SKILL",
    "Formance",
    "Katra",
    "Formance Ledger",
    "episodic",
    "semantic",
    "knowledge graph",
    "MCP gateway",
    "double-entry",
]


async def send_message(client: httpx.AsyncClient, session_id: str, message: str) -> dict:
    """Send one message and return the response."""
    resp = await client.post(
        f"{API_URL}/api/v1/chat/message",
        json={
            "session_id": session_id,
            "message": message,
            "persona": "professional",
        },
        headers={"X-Correlation-ID": CORRELATION_ID},
        timeout=60.0,
    )
    if resp.status_code != 200:
        return {"error": f"HTTP {resp.status_code}", "body": resp.text[:500]}
    return resp.json()


def analyze_response(message: str, response: dict) -> dict:
    """Check if the response shows awareness of the system architecture."""
    msg_data = response.get("message", {})
    response_text = msg_data.get("text", "")
    tool_call = response.get("tool_call", {})
    skill_id = tool_call.get("skill_id", "")

    # Check for architecture awareness signals
    knows_formance = any(
        kw in response_text.lower()
        for kw in ["formance", "ledger", "double-entry ledger"]
    )
    knows_katra = any(
        kw in response_text.lower()
        for kw in ["katra", "memory", "cognitive", "episodic"]
    )
    knows_mcp = any(
        kw in response_text.lower()
        for kw in ["mcp", "model context protocol", "gateway"]
    )

    analysis = {
        "message": message[:80],
        "skill_called": skill_id or "none (text response)",
        "response_chars": len(response_text),
        "knows_formance": knows_formance,
        "knows_katra": knows_katra,
        "knows_mcp": knows_mcp,
        "architecture_aware": knows_formance or knows_katra or knows_mcp,
        "response_preview": response_text[:200],
    }
    return analysis


async def main():
    print(f"Phase 2 Replay — Correlation ID: {CORRELATION_ID}")
    print(f"API URL: {API_URL}")
    print(f"Sending {len(TEST_MESSAGES)} test messages...\n")

    session_id = f"phase2-replay-{CORRELATION_ID[:8]}"

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Check API health first
        try:
            health = await client.get(f"{API_URL}/health", timeout=5.0)
            print(f"API health: {health.status_code} — {health.text[:100]}")
        except Exception as e:
            print(f"API not reachable: {e}")
            print("Start it with: docker compose up -d postgres redis accounting-api")
            return 1

        results = []
        for msg in TEST_MESSAGES:
            print(f"→ {msg[:80]}...")
            sys.stdout.flush()
            try:
                resp = await send_message(client, session_id, msg)
            except Exception as e:
                print(f"  ERROR: {e}")
                results.append({"message": msg[:80], "error": str(e)})
                continue

            analysis = analyze_response(msg, resp)
            results.append(analysis)

            arch = "✓ AWARE" if analysis["architecture_aware"] else "✗ BLIND"
            print(f"  {arch} | tool={analysis['skill_called']} | "
                  f"Formance={analysis['knows_formance']} | "
                  f"Katra={analysis['knows_katra']} | "
                  f"MCP={analysis['knows_mcp']}")
            print(f"  Preview: {analysis['response_preview'][:120]}")
            print()

    # Summary
    print("=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    aware = sum(1 for r in results if r.get("architecture_aware"))
    total = len([r for r in results if "error" not in r])
    print(f"Architecture-aware responses: {aware}/{total}")
    print(f"Blind responses: {total - aware}/{total}")

    if aware == 0:
        print("\n✓ HYPOTHESIS CONFIRMED: LLM has ZERO architecture awareness.")
        print("  It never mentions Formance, Katra, or the MCP gateway.")
        print("  The system prompt is not injecting any of this documentation.")
    elif aware < total:
        print(f"\n⚠ PARTIAL: {aware}/{total} responses showed awareness.")
    else:
        print("\n✗ HYPOTHESIS REJECTED: LLM shows architecture awareness.")
        print("  The issue may be elsewhere.")

    print(f"\nCorrelation ID: {CORRELATION_ID}")
    print("Collect structured logs with:")
    print("  docker compose logs accounting-api 2>&1 | grep INSTRUMENT > phase2_logs.jsonl")
    print("  docker compose logs chat-ui 2>&1 | grep INSTRUMENT >> phase2_logs.jsonl")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code or 0)
