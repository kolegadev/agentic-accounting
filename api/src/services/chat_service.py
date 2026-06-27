"""Chat Service — conversation pipeline (context, route, execute, format).

Persistence is layered: Katra cognitive memory (primary, cross-session) →
Redis (fast, ephemeral fallback).  When Katra is available every conversation
turn is stored as an episodic event and session context as a semantic fact,
enabling cross-agent recall.  When Katra is unavailable the service degrades
gracefully to Redis-only operation.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from src.services.intent_router import IntentRouter
from src.services.skill_registry import SkillRegistry

try:
    import redis.asyncio as aioredis
except ImportError:  # pragma: no cover
    aioredis = None  # type: ignore

logger = logging.getLogger(__name__)

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SESSION_TTL: int = 3600  # 1 hour
MAX_HISTORY: int = 50

PERSONAS: dict[str, str] = {
    "professional": "formal_precise",
    "friendly": "conversational_warm",
    "minimal": "terse_bullets",
}

# ---------------------------------------------------------------------------
# Prompt / tone snippets per persona
# ---------------------------------------------------------------------------
_TONE: dict[str, dict[str, str]] = {
    "professional": {
        "prefix": "Here is the result:",
        "suffix": "Please let me know if you need any further details.",
        "style": "Formal, precise, and uses proper accounting terminology.",
    },
    "friendly": {
        "prefix": "Here you go! 😊",
        "suffix": "Need anything else? I'm happy to help!",
        "style": "Conversational, warm, and encouraging tone.",
    },
    "minimal": {
        "prefix": "",
        "suffix": "",
        "style": "Terse responses, bullet points, minimal fluff.",
    },
}


class ChatService:
    """Stateless service for processing chat messages.

    Uses Katra cognitive memory as the primary persistence layer, falling
    back to Redis when Katra is unavailable.  Katra provides four memory
    modalities (episodic, semantic, knowledge graph, temporal) that enable
    cross-session recall — an agent started in Claude Code can continue a
    conversation in OpenClaw or Kolega Code without losing context.
    """

    def __init__(self) -> None:
        self._redis = None  # type: aioredis.Redis | None
        self._router = IntentRouter()
        self._registry = SkillRegistry()
        # Katra client is lazy-loaded so tests can mock without importing
        self._katra = None

    def _get_katra(self):
        """Lazy-load the Katra client singleton."""
        if self._katra is not None:
            return self._katra
        from src.services.katra_client import get_katra_client
        self._katra = get_katra_client()
        return self._katra

    async def _get_redis(self):
        """Lazy Redis connection — returns None if redis package unavailable."""
        if self._redis is not None:
            return self._redis
        if aioredis is None:
            return None
        self._redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        return self._redis

    # ------------------------------------------------------------------
    # conversation state
    # ------------------------------------------------------------------
    @staticmethod
    def _state_key(session_id: str) -> str:
        return f"chat:state:{session_id}"

    async def get_conversation_state(self, session_id: str) -> dict[str, Any]:
        """Load conversation state.

        Priority: Redis cache → Katra episodic memory → default empty state.
        Redis is tried first for sub-millisecond latency; Katra is the
        authoritative long-term store queried when the Redis cache is cold.
        """
        # 1) Try Redis (fast cache)
        r = await self._get_redis()
        if r is not None:
            raw = await r.get(self._state_key(session_id))
            if raw:
                return json.loads(raw)

        # 2) Try Katra (authoritative long-term store)
        katra = self._get_katra()
        if katra.enabled:
            try:
                events = await katra.get_recent_events(session_id, limit=MAX_HISTORY)
                if events:
                    history = []
                    context: dict[str, Any] = {}
                    for ev in events:
                        content = ev.get("content", "")
                        role = "user" if "user" in str(ev.get("tags", [])) else "assistant"
                        history.append({
                            "role": role,
                            "content": content,
                            "timestamp": ev.get("created_at", datetime.now(timezone.utc).isoformat()),
                        })
                    state = {
                        "session_id": session_id,
                        "persona": "professional",
                        "history": history[-MAX_HISTORY:],
                        "context": context,
                    }
                    # Populate Redis cache for next time
                    if r is not None:
                        await r.set(
                            self._state_key(session_id),
                            json.dumps(state, default=str),
                            ex=SESSION_TTL,
                        )
                    return state
            except Exception:
                logger.debug("Katra recall failed, using Redis-only mode", exc_info=True)

        # 3) Default empty state
        return {
            "session_id": session_id,
            "persona": "professional",
            "history": [],
            "context": {},
        }

    async def save_conversation_state(self, session_id: str, state: dict[str, Any]) -> None:
        """Persist conversation state to Redis + Katra.

        Redis is the fast cache (always written).  Katra is the durable
        long-term store (written optimistically — failures are logged but
        never block the chat pipeline).
        """
        # Always write Redis (fast, non-blocking)
        r = await self._get_redis()
        if r is not None:
            await r.set(
                self._state_key(session_id),
                json.dumps(state, default=str),
                ex=SESSION_TTL,
            )

        # Store the last user turn in Katra as an episodic event
        katra = self._get_katra()
        if katra.enabled:
            history = state.get("history", [])
            try:
                # Store the last 2 turns (user + assistant) as episodic events
                for entry in history[-2:]:
                    await katra.store_conversation_event(
                        session_id=session_id,
                        role=entry.get("role", "unknown"),
                        content=str(entry.get("content", "")),
                        metadata={"tool_call": entry.get("tool_call")} if entry.get("tool_call") else None,
                    )
                # Store context snapshot as a semantic fact
                await katra.store_session_context(
                    session_id=session_id,
                    context=state.get("context", {}),
                )
            except Exception:
                logger.debug("Katra persistence failed, continuing with Redis-only", exc_info=True)

    # ------------------------------------------------------------------
    # main pipeline
    # ------------------------------------------------------------------
    async def process_message(self, session_id: str, message: str) -> dict[str, Any]:
        """Full chat pipeline: load state → route intent → build result → save state."""
        state = await self.get_conversation_state(session_id)
        context = state.get("context", {})
        persona = state.get("persona", "professional")

        # 1. Route intent
        skill_id, params, confidence = self._router.route(message, context)

        # 2. Look up skill definition
        skill = self._registry.get_skill(skill_id)

        # 3. Build tool-call result (simulated for MVP — no actual DB operations here)
        tool_result = {
            "skill_id": skill_id,
            "params": params,
            "confidence": round(confidence, 2),
            "skill": skill,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 4. Format response for the matched persona
        formatted = self.format_response(tool_result, persona)

        # 5. Update history
        history: list[dict[str, Any]] = state.get("history", [])
        history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        history.append({
            "role": "assistant",
            "content": formatted["text"],
            "tool_call": tool_result,
            "timestamp": formatted["timestamp"],
        })
        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]

        # 6. Update context with extracted entities
        new_context = dict(context)
        for key in ("description", "amount", "date", "contact_id", "account_id",
                     "bank_account_id", "reconciliation_id"):
            if key in params:
                new_context[key] = params[key]

        state["history"] = history
        state["context"] = new_context
        await self.save_conversation_state(session_id, state)

        return {
            "session_id": session_id,
            "message": formatted,
            "tool_call": tool_result,
            "history": history,
        }

    # ------------------------------------------------------------------
    # response formatting
    # ------------------------------------------------------------------
    def format_response(self, result: dict[str, Any], persona: str) -> dict[str, Any]:
        """Format a tool result in the given persona's tone."""
        tone = _TONE.get(persona, _TONE["professional"])
        skill_id = result.get("skill_id", "unknown")
        params = result.get("params", {})
        skill = result.get("skill")

        skill_name = skill["name"] if skill else skill_id
        desc = params.get("description", "")
        amount = params.get("amount")

        lines: list[str] = []
        if tone["prefix"]:
            lines.append(tone["prefix"])

        if persona == "minimal":
            lines.append(f"• Skill: {skill_name}")
            if desc:
                lines.append(f"• Description: {desc}")
            if amount is not None:
                lines.append(f"• Amount: £{amount / 100:,.2f}")
            for k, v in params.items():
                if k not in ("description", "amount") and v:
                    lines.append(f"• {k}: {v}")
        elif persona == "friendly":
            lines.append(f"I'll help you with **{skill_name}**!")
            if desc:
                lines.append(f"So you want to record: _{desc}_")
            if amount is not None:
                lines.append(f"That's for **£{amount / 100:,.2f}** — got it! 💰")
        else:  # professional
            lines.append(f"**Action:** {skill_name}")
            if desc:
                lines.append(f"**Details:** {desc}")
            if amount is not None:
                lines.append(f"**Amount:** £{amount / 100:,.2f}")

        if tone["suffix"]:
            lines.append("")
            lines.append(tone["suffix"])

        return {
            "text": "\n".join(lines),
            "persona": persona,
            "tone": tone["style"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
