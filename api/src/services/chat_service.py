"""Chat Service — conversation pipeline (context, route, execute, format)."""

from __future__ import annotations

import json
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
    """Stateless service for processing chat messages."""

    def __init__(self) -> None:
        self._redis = None  # type: aioredis.Redis | None
        self._router = IntentRouter()
        self._registry = SkillRegistry()

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
        """Load conversation state from Redis (or return default if unavailable)."""
        r = await self._get_redis()
        if r is not None:
            raw = await r.get(self._state_key(session_id))
            if raw:
                return json.loads(raw)
        return {
            "session_id": session_id,
            "persona": "professional",
            "history": [],
            "context": {},
        }

    async def save_conversation_state(self, session_id: str, state: dict[str, Any]) -> None:
        """Persist conversation state to Redis (no-op if unavailable)."""
        r = await self._get_redis()
        if r is not None:
            await r.set(self._state_key(session_id), json.dumps(state, default=str), ex=SESSION_TTL)

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
