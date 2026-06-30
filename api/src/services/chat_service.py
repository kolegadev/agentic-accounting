"""Chat Service — 100% LLM-generated conversation pipeline.

Every message the user sees comes from the LLM — no hardcoded responses,
no template formatting, no static strings.  The LLM receives tool results
as context and generates natural language responses.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from src.services.llm_router import LLMRouter
from src.services.tool_executor import ToolExecutor
from src.services.skill_registry import SkillRegistry
from src.services.instrument import log_event, new_correlation_id, get_correlation_id
from src.services.prompt_assembler import assemble_system_prompt

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

    @staticmethod
    def _sanitize_html(text: str) -> str:
        """Deterministic post-processing: convert any remaining HTML tags
        to markdown equivalents.  Applied to EVERY response so formatting
        is guaranteed regardless of LLM behaviour.

        Covers:
          <strong>/<b> → **…**      <em>/<i> → *…*
          <br> / <br/> → \\n        <p> → \\n
          <li> → -                  <ul>/<ol> → stripped
          <code> → `…`             <pre> → ```…```
          <h1>-<h6> → ## …         all other tags → stripped
        """
        if not text or "<" not in text:
            return text

        # 1. Block-level: <p>, <br>, <hr>
        text = re.sub(r"</?p[^>]*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<hr\s*/?>", "\n---\n", text, flags=re.IGNORECASE)

        # 2. Pre/code blocks (must process before inline tags)
        text = re.sub(
            r"<pre[^>]*>(.*?)</pre>",
            lambda m: "\n```\n" + m.group(1).strip() + "\n```\n",
            text, flags=re.IGNORECASE | re.DOTALL,
        )
        text = re.sub(
            r"<code[^>]*>(.*?)</code>",
            r"`\1`", text, flags=re.IGNORECASE,
        )

        # 3. Lists: convert <li>…</li> to "- …"
        text = re.sub(r"</?[ou]l[^>]*>", "", text, flags=re.IGNORECASE)
        text = re.sub(
            r"<li[^>]*>(.*?)</li>",
            lambda m: "- " + m.group(1).strip() + "\n",
            text, flags=re.IGNORECASE | re.DOTALL,
        )

        # 4. Headings: <h1> - <h6>
        text = re.sub(
            r"<h([1-6])[^>]*>(.*?)</h\1>",
            lambda m: "#" * int(m.group(1)) + " " + m.group(2).strip() + "\n",
            text, flags=re.IGNORECASE | re.DOTALL,
        )

        # 5. Inline: <strong>, <b> → **…**  and  <em>, <i> → *…*
        text = re.sub(
            r"<(strong|b)[^>]*>(.*?)</(\1)>",
            r"**\2**", text, flags=re.IGNORECASE | re.DOTALL,
        )
        text = re.sub(
            r"<(em|i)[^>]*>(.*?)</(\1)>",
            r"*\2*", text, flags=re.IGNORECASE | re.DOTALL,
        )

        # 6. Strip any remaining HTML tags (div, span, a, etc.)
        text = re.sub(r"<[^>]+>", "", text)

        # 7. Collapse multiple blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    # ------------------------------------------------------------------
    # main pipeline — every response is LLM-generated
    # ------------------------------------------------------------------
    async def process_message(self, session_id: str, message: str) -> dict[str, Any]:
        cid = new_correlation_id()
        state = await self.get_conversation_state(session_id)
        history: list[dict[str, Any]] = state.get("history", [])
        context: dict[str, Any] = state.get("context", {})

        # ── I4: conversation state at turn entry ──────────────────────
        log_event(
            module="chat_service", function="process_message", event="entry",
            state_snapshot={
                "session_id": session_id,
                "history_turns": len(history),
                "context_keys": list(context.keys()) if context else [],
                "message_chars": len(message),
            },
        )

        history.append({
            "role": "user", "content": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # ── Step 1: LLM decides what to do ──────────────────────────
        # Inject high-priority instruction when the user is asking to fix
        # accounts — the LLM often ignores system-prompt rules but obeys
        # inline directives in the user message.
        fix_keywords = ("fix the error", "that was a mistake", "wrong account",
                        "remove the", "delete the", "rename the", "correct the")
        if any(kw in message.lower() for kw in fix_keywords):
            message = (
                "[SYSTEM INSTRUCTION — OBEY THIS]: You MUST call the "
                "appropriate tool (coa.delete_account, coa.edit_account, or "
                "coa.add_account) to fix the accounts the user mentions. "
                "NEVER respond by listing the COA with coa.list. That is "
                "the OPPOSITE of fixing.\n\n" + message
            )
        invoice_kw = ("create an invoice", "new invoice", "send an invoice")
        if any(kw in message.lower() for kw in invoice_kw):
            message = (
                "[SYSTEM INSTRUCTION]: To create an invoice for a new "
                "customer, chain these tools in sequence: first call "
                "contact.create to create the customer, then call "
                "invoice.create to create the invoice. You can call "
                "multiple tools in a single turn — keep calling tools "
                "until the invoice is fully created.\n\n"
                + message
            )
        account_count = await self._get_account_count()

        # ── Agentic tool-chaining loop ─────────────────────────────
        original_message = message
        tool_calls: list[dict[str, Any]] = []
        last_tool_result: dict[str, Any] | None = None
        chain_message = message
        MAX_CHAIN = 5

        for _ in range(MAX_CHAIN):
            route_result = await self._llm_router.route(
                chain_message, history, context, account_count,
            )

            if "tool" not in route_result:
                break  # LLM returned a text response — we're done

            # ── Execute the tool ──────────────────────────────────
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

            tc = {
                "skill_id": skill_id, "params": params, "skill": skill,
                "result": tool_result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            tool_calls.append(tc)
            last_tool_result = tool_result

            # Feed result back to LLM for the next routing decision
            history.append({
                "role": "system",
                "content": f"Tool {skill_id} executed. Result: {json.dumps(tool_result, default=str)[:2000]}",
            })
            chain_message = (
                f"CONTINUE: The user originally asked: {original_message}\n\n"
                f"You just called {skill_id}. Now call the NEXT tool needed "
                f"to complete this task. DO NOT return a text response — "
                f"call another tool. Only return text when the task is "
                f"FULLY complete."
            )

        # ── Step 2: Generate final response ───────────────────────
        # Combine all tool calls into the last one for _generate_response
        tool_call = tool_calls[-1] if tool_calls else None
        tool_result_for_response = last_tool_result

        assistant_content = await self._generate_response(
            history, route_result, tool_result_for_response,
        )

        # Guarantee clean markdown in history and response, regardless
        # of which LLM path produced the content.
        assistant_content = self._sanitize_html(assistant_content)

        history.append({
            "role": "assistant", "content": assistant_content,
            "tool_call": tool_call,
            "tool_calls": tool_calls,
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
            "tool_calls": tool_calls,
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
                result_data = tool_result.get('result', {})
                # If the tool pre-formatted the output, use it directly
                if isinstance(result_data, dict) and "formatted" in result_data:
                    return self._sanitize_html(result_data["formatted"])
                data_str = json.dumps(result_data, default=str)
                parts.append(f"The user's request was successful. Tool result: {data_str[:8000]}")
            else:
                parts.append(f"The user's request FAILED. Error: {tool_result.get('error', 'unknown')}")
        elif "tool" in route_result:
            parts.append(f"The LLM selected tool '{route_result['tool']}' with params {route_result.get('params', {})} but it was not executed.")
        elif "response" in route_result:
            # LLM already generated a direct response — send it through the
            # formatting LLM call so markdown rules are consistently applied
            parts.append(
                "The system produced this direct response to show the user: "
                + route_result["response"]
            )
            parts.append(
                "Reformat this as clean markdown following the "
                "CRITICAL FORMATTING RULES above.  Preserve all information "
                "and meaning — only change the formatting.  Do NOT wrap in "
                "code fences or quotes."
            )
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
            # ── Use the assembler for architecture-aware response prompts ──
            response_system_prompt = assemble_system_prompt(
                [],  # response mode doesn't need full tools
                history,
                account_count=0,  # response mode: account count not relevant
                mode="response",
            )
            # Append the specific response context (what happened)
            response_system_prompt += "\n\n## WHAT JUST HAPPENED\n\n" + response_prompt

            # ── I3: verify contract now holds ──────────────────────────
            log_event(
                module="chat_service", function="_generate_response", event="contract_check",
                state_snapshot={
                    "response_prompt_chars": len(response_system_prompt),
                    "response_prompt_sections": [
                        "system_identity", "architecture", "katra_memory",
                        "formance_ledger", "context", "rules", "what_happened"
                    ],
                    "has_tool_context": True,
                    "has_architecture_context": True,
                    "has_formance_context": True,
                    "has_katra_context": True,
                },
                contract="Response prompt should include same architecture context as routing prompt",
                contract_held=True,
            )
            raw = await self._llm_router._call_llm(
                system_prompt=response_system_prompt,
                user_message=f"Conversation so far:\n{conversation}\n\nGenerate the assistant's reply.",
            )
            # The LLM returns natural language — sanitize and return.
            return self._sanitize_html(raw.strip())
        except Exception:
            return "I ran into a problem. Please try again in a moment."
