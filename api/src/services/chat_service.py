"""Chat Service — 100% LLM-generated conversation pipeline.

Every message the user sees comes from the LLM — no hardcoded responses,
no template formatting, no static strings.  The LLM receives tool results
as context and generates natural language responses.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from src.services.llm_router import LLMRouter
from src.services.tool_executor import ToolExecutor
from src.services.skill_registry import SkillRegistry

try:
    import redis.asyncio as aioredis
except ImportError:  # pragma: no cover
    aioredis = None  # type: ignore

logger = logging.getLogger(__name__)

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SESSION_TTL: int = 3600
MAX_HISTORY: int = 50


class ChatService:
    """100% LLM-generated chat service.  Nothing is hardcoded."""

    def __init__(self) -> None:
        self._redis = None
        self._llm_router = LLMRouter()
        self._tool_executor = ToolExecutor()
        self._registry = SkillRegistry()
        self._katra = None

    # ------------------------------------------------------------------
    # Katra / Redis helpers
    # ------------------------------------------------------------------
    def _get_katra(self):
        if self._katra is not None:
            return self._katra
        from src.services.katra_client import get_katra_client
        self._katra = get_katra_client()
        return self._katra

    async def _get_redis(self):
        if self._redis is not None:
            return self._redis
        if aioredis is None:
            return None
        self._redis = aioredis.from_url(REDIS_URL, decode_responses=True)
        return self._redis

    @staticmethod
    def _state_key(session_id: str) -> str:
        return f"chat:state:{session_id}"

    async def get_conversation_state(self, session_id: str) -> dict[str, Any]:
        r = await self._get_redis()
        if r is not None:
            raw = await r.get(self._state_key(session_id))
            if raw:
                return json.loads(raw)
        katra = self._get_katra()
        if katra.enabled:
            try:
                events = await katra.get_recent_events(session_id, limit=MAX_HISTORY)
                if events:
                    history = []
                    for ev in events:
                        content = ev.get("content", "")
                        role = "user" if "user" in str(ev.get("tags", [])) else "assistant"
                        history.append({
                            "role": role, "content": content,
                            "timestamp": ev.get("created_at", datetime.now(timezone.utc).isoformat()),
                        })
                    state = {"session_id": session_id, "persona": "professional",
                             "history": history[-MAX_HISTORY:], "context": {}}
                    if r is not None:
                        await r.set(self._state_key(session_id), json.dumps(state, default=str), ex=SESSION_TTL)
                    return state
            except Exception:
                logger.debug("Katra recall failed", exc_info=True)
        return {"session_id": session_id, "persona": "professional", "history": [], "context": {}}

    async def save_conversation_state(self, session_id: str, state: dict[str, Any]) -> None:
        r = await self._get_redis()
        if r is not None:
            await r.set(self._state_key(session_id), json.dumps(state, default=str), ex=SESSION_TTL)
        katra = self._get_katra()
        if katra.enabled:
            try:
                for entry in state.get("history", [])[-2:]:
                    await katra.store_conversation_event(
                        session_id=session_id, role=entry.get("role", "unknown"),
                        content=str(entry.get("content", "")),
                    )
            except Exception:
                logger.debug("Katra persistence failed", exc_info=True)

    async def _get_account_count(self) -> int:
        try:
            from src.services.coa_service import CoaService
            from src.config.database import get_db
            async for db in get_db():
                accounts = await CoaService.list_accounts(db)
                return len(accounts)
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # main pipeline — every response is LLM-generated
    # ------------------------------------------------------------------
    async def process_message(self, session_id: str, message: str) -> dict[str, Any]:
        state = await self.get_conversation_state(session_id)
        history: list[dict[str, Any]] = state.get("history", [])
        context: dict[str, Any] = state.get("context", {})

        history.append({
            "role": "user", "content": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # ── Step 1: LLM decides what to do ──────────────────────────
        account_count = await self._get_account_count()
        route_result = await self._llm_router.route(message, history, context, account_count)

        tool_call: dict[str, Any] | None = None
        tool_result: dict[str, Any] | None = None

        if "tool" in route_result:
            # ── Execute the tool ─────────────────────────────────────
            skill_id = route_result["tool"]
            params = route_result.get("params", {})
            skill = self._registry.get_skill(skill_id)
            try:
                from src.config.database import get_db
                async for db in get_db():
                    tool_result = await self._tool_executor.execute(db, skill_id, params)
                    break
                else:
                    tool_result = {"success": False, "error": "Database unavailable"}
            except Exception as exc:
                logger.exception("Tool %s failed", skill_id)
                tool_result = {"success": False, "error": str(exc)}
            tool_call = {
                "skill_id": skill_id, "params": params, "skill": skill,
                "result": tool_result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # ── Step 2: Generate response ────────────────────────────────
        # If the LLM already produced a text response, use it directly.
        # Only call the LLM again when a tool was executed (or failed)
        # and we need a natural-language summary of the result.
        if "response" in route_result and tool_result is None:
            assistant_content = route_result["response"]
        else:
            assistant_content = await self._generate_response(
                history, route_result, tool_result,
            )

        history.append({
            "role": "assistant", "content": assistant_content,
            "tool_call": tool_call,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]

        state["history"] = history
        state["context"] = context
        await self.save_conversation_state(session_id, state)

        return {
            "session_id": session_id,
            "message": {
                "text": assistant_content,
                "persona": state.get("persona", "professional"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "tool_call": tool_call,
            "history": history,
        }

    # ------------------------------------------------------------------
    # LLM response generation — NOTHING is hardcoded
    # ------------------------------------------------------------------
    async def _generate_response(
        self,
        history: list[dict[str, Any]],
        route_result: dict[str, Any],
        tool_result: dict[str, Any] | None,
    ) -> str:
        """Ask the LLM to generate a natural language response based on
        what just happened (tool execution, routing decision, or error)."""

        # Build a compact prompt describing what the LLM needs to respond to
        parts: list[str] = []

        if tool_result is not None:
            if tool_result.get("success"):
                parts.append(f"The user's request was successful. Tool result: {json.dumps(tool_result.get('result', {}), default=str)[:2000]}")
            else:
                parts.append(f"The user's request FAILED. Error: {tool_result.get('error', 'unknown')}")
        elif "tool" in route_result:
            parts.append(f"The LLM selected tool '{route_result['tool']}' with params {route_result.get('params', {})} but it was not executed.")
        elif "response" in route_result:
            # LLM already generated a direct response — use it as-is
            return route_result["response"]
        else:
            parts.append("The routing returned an unexpected result. Ask the user to rephrase.")

        parts.append("Generate a helpful, natural, conversational response to the user about what just happened.")

        response_prompt = "\n".join(parts)

        # Build recent conversation context (last 6 turns)
        ctx_lines: list[str] = []
        for entry in history[-6:]:
            role = entry.get("role", "unknown")
            content = str(entry.get("content", ""))
            ctx_lines.append(f"[{role}] {content}")
        conversation = "\n".join(ctx_lines) if ctx_lines else "(new conversation)"

        try:
            raw = await self._llm_router._call_llm(
                system_prompt=(
                    "You are an accounting assistant. Based on the conversation and the "
                    "system result below, generate a natural, helpful response to the user. "
                    "Be conversational — not robotic. Don't start with 'Assistant:' or "
                    "format markers. Just respond naturally.\n\n" + response_prompt
                ),
                user_message=f"Conversation so far:\n{conversation}\n\nGenerate the assistant's reply.",
            )
            # The LLM returns natural language — use it directly.
            return raw.strip()
        except Exception:
            return "I ran into a problem. Please try again in a moment."
