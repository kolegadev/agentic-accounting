"""Chat Service — LLM-powered conversation pipeline.

Routes user messages through:
  1. Setup Wizard (if fresh company)
  2. LLM Router (tool selection via LLM)
  3. Tool Executor (actual service calls — no simulation)
  4. Response Formatter (persona-aware)

Persistence: Katra cognitive memory (primary) → Redis fallback.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from src.services.llm_router import LLMRouter
from src.services.tool_executor import ToolExecutor
from src.services.setup_wizard import SetupWizard
from src.services.skill_registry import SkillRegistry

try:
    import redis.asyncio as aioredis
except ImportError:  # pragma: no cover
    aioredis = None  # type: ignore

logger = logging.getLogger(__name__)

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SESSION_TTL: int = 3600
MAX_HISTORY: int = 50

_TONE: dict[str, dict[str, str]] = {
    "professional": {
        "prefix": "",
        "suffix": "",
        "style": "Formal, precise, proper accounting terminology.",
    },
    "friendly": {
        "prefix": "",
        "suffix": "Need anything else? I'm happy to help! 😊",
        "style": "Conversational, warm, encouraging.",
    },
    "minimal": {
        "prefix": "",
        "suffix": "",
        "style": "Terse, bullet points, minimal fluff.",
    },
}


class ChatService:
    """LLM-powered chat service.

    Uses the LLM Router for intent understanding (NOT regex), the Tool Executor
    for actual accounting operations, and the Setup Wizard for first-time
    company initialization.
    """

    def __init__(self) -> None:
        self._redis = None
        self._llm_router = LLMRouter()
        self._tool_executor = ToolExecutor()
        self._wizard = SetupWizard()
        self._registry = SkillRegistry()
        self._katra = None

    # ------------------------------------------------------------------
    # Katra / Redis helpers (unchanged)
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
                            "role": role,
                            "content": content,
                            "timestamp": ev.get("created_at", datetime.now(timezone.utc).isoformat()),
                        })
                    state = {
                        "session_id": session_id,
                        "persona": "professional",
                        "history": history[-MAX_HISTORY:],
                        "context": {},
                    }
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
                        session_id=session_id,
                        role=entry.get("role", "unknown"),
                        content=str(entry.get("content", "")),
                        metadata=entry.get("tool_call"),
                    )
            except Exception:
                logger.debug("Katra persistence failed", exc_info=True)

    # ------------------------------------------------------------------
    # account count helper (for setup detection)
    # ------------------------------------------------------------------
    async def _get_account_count(self) -> int:
        """Return the number of accounts in the COA (0 = fresh system)."""
        try:
            from src.services.coa_service import CoaService
            from src.config.database import get_db
            async for db in get_db():
                accounts = await CoaService.list_accounts(db)
                return len(accounts)
        except Exception:
            logger.debug("Could not query COA count", exc_info=True)
            return 0

    # ------------------------------------------------------------------
    # main pipeline
    # ------------------------------------------------------------------
    async def process_message(self, session_id: str, message: str) -> dict[str, Any]:
        """Full LLM-powered chat pipeline."""
        state = await self.get_conversation_state(session_id)
        history: list[dict[str, Any]] = state.get("history", [])
        context: dict[str, Any] = state.get("context", {})
        persona: str = state.get("persona", "professional")

        # Add user message to history
        history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # ── Check for setup wizard ──────────────────────────────────
        setup_step = context.get("_setup_step")
        if setup_step and setup_step != "complete":
            try:
                from src.config.database import get_db
                async for db in get_db():
                    wizard_result = await self._wizard.handle_step(
                        db, setup_step, message, context.get("_setup_context", {})
                    )
                    break
                else:
                    wizard_result = {"next_step": "welcome", "response": "Database unavailable — try again.", "setup_context": {}}
            except Exception as exc:
                logger.exception("Setup wizard failed")
                wizard_result = {"next_step": "welcome", "response": f"Setup error: {exc}", "setup_context": {}}

            context["_setup_step"] = wizard_result["next_step"]
            context["_setup_context"] = wizard_result.get("setup_context", {})

            assistant_content = wizard_result["response"]
            history.append({
                "role": "assistant",
                "content": assistant_content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            if len(history) > MAX_HISTORY:
                history = history[-MAX_HISTORY:]

            state["history"] = history
            state["context"] = context
            await self.save_conversation_state(session_id, state)

            return {
                "session_id": session_id,
                "message": {"text": assistant_content, "persona": persona, "tone": _TONE[persona]["style"]},
                "history": history,
            }

        # ── LLM Router ──────────────────────────────────────────────
        account_count = await self._get_account_count()
        try:
            route_result = await self._llm_router.route(message, history, context, account_count)
        except Exception as exc:
            logger.exception("LLM routing failed")
            route_result = {"response": f"I'm having trouble understanding. Could you rephrase? ({exc})"}

        # ── Setup detection ──────────────────────────────────────────
        if route_result.get("setup_required"):
            context["_setup_step"] = route_result.get("step", "welcome")
            context["_setup_context"] = {}
            # Recurse into process message to run wizard's welcome step
            try:
                from src.config.database import get_db
                async for db in get_db():
                    wizard_result = await self._wizard.handle_step(
                        db, "welcome", message, {}
                    )
                    break
                else:
                    wizard_result = {"next_step": "welcome", "response": "Database unavailable.", "setup_context": {}}
            except Exception as exc:
                wizard_result = {"next_step": "welcome", "response": f"Setup error: {exc}", "setup_context": {}}

            context["_setup_step"] = wizard_result["next_step"]
            context["_setup_context"] = wizard_result.get("setup_context", {})

            assistant_content = wizard_result["response"]
            history.append({
                "role": "assistant",
                "content": assistant_content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            if len(history) > MAX_HISTORY:
                history = history[-MAX_HISTORY:]

            state["history"] = history
            state["context"] = context
            await self.save_conversation_state(session_id, state)

            return {
                "session_id": session_id,
                "message": {"text": assistant_content, "persona": persona, "tone": _TONE[persona]["style"]},
                "history": history,
            }

        # ── Tool execution ───────────────────────────────────────────
        tool_call: dict[str, Any] | None = None
        tool_result: dict[str, Any] | None = None
        assistant_content: str = ""

        if "tool" in route_result:
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
                logger.exception("Tool execution failed: %s", skill_id)
                tool_result = {"success": False, "error": str(exc)}

            tool_call = {
                "skill_id": skill_id,
                "params": params,
                "skill": skill,
                "result": tool_result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            if tool_result.get("success"):
                assistant_content = self._format_success(skill_id, params, tool_result, persona)
            else:
                error_msg = tool_result.get("error", "Unknown error")
                assistant_content = f"❌ Could not complete **{skill.get('name', skill_id) if skill else skill_id}**: {error_msg}"

        elif "response" in route_result:
            assistant_content = route_result["response"]
        else:
            assistant_content = "I'm not sure how to help with that. Could you rephrase?"

        # ── Update state ─────────────────────────────────────────────
        history.append({
            "role": "assistant",
            "content": assistant_content,
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
                "persona": persona,
                "tone": _TONE[persona]["style"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "tool_call": tool_call,
            "history": history,
        }

    # ------------------------------------------------------------------
    # response formatting
    # ------------------------------------------------------------------
    @staticmethod
    def _format_success(
        skill_id: str,
        params: dict[str, Any],
        result: dict[str, Any],
        persona: str,
    ) -> str:
        """Format a successful tool execution as a human-readable response."""
        data = result.get("result", {})

        # Reasonable defaults
        if persona == "minimal":
            lines = [f"✅ {skill_id}"]
            if isinstance(data, dict):
                for k, v in data.items():
                    if k in ("id", "reference", "status", "total", "name"):
                        lines.append(f"• {k}: {v}")
            return "\n".join(lines[:10])

        if persona == "friendly":
            prefix = f"✅ Done! Here's what happened with **{skill_id}**:\n"
        else:
            prefix = f"**{skill_id.replace('_', ' ').title()}** completed.\n"

        # Build a compact summary
        summary_parts: list[str] = []
        if isinstance(data, dict):
            if "reference" in data:
                summary_parts.append(f"Reference: {data['reference']}")
            if "status" in data:
                summary_parts.append(f"Status: {data['status']}")
            if "total" in data:
                summary_parts.append(f"Total: {data['total']}")
            if "name" in data:
                summary_parts.append(f"Name: {data['name']}")
            if "transactions" in data and isinstance(data["transactions"], list):
                summary_parts.append(f"Found {len(data['transactions'])} transaction(s)")
            if "contacts" in data and isinstance(data["contacts"], list):
                summary_parts.append(f"Found {len(data['contacts'])} contact(s)")
            if "invoices" in data and isinstance(data["invoices"], list):
                summary_parts.append(f"Found {len(data['invoices'])} invoice(s)")
            if "imported" in data:
                summary_parts.append(f"Imported {data['imported']}, skipped {data.get('skipped', 0)}")

        if summary_parts:
            return prefix + "\n".join(f"• {p}" for p in summary_parts)
        return prefix + "(details available on request)"
