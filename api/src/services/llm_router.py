"""LLM Router — calls an OpenAI-compatible LLM to understand user intent and select the
correct accounting tool with extracted parameters.

Replaces the regex-based intent_router.py with structured LLM prompts that include
the full tool registry, conversation history, and setup-wizard awareness.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from src.services.skill_registry import SkillRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM configuration (env vars)
# ---------------------------------------------------------------------------
LLM_API_URL: str = os.getenv("LLM_API_URL", "http://localhost:11434/v1/chat/completions")
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek-v4-pro")
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))
LLM_TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "15.0"))

# ---------------------------------------------------------------------------
# System prompt template
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an accounting assistant for **Agentic Accounting**, a headless
double-entry accounting system for UK small businesses.

You have access to the following tools.  When the user asks to perform an
accounting action, respond with a JSON object containing the tool call:

    {"tool": "<skill_id>", "params": {<extracted parameters>}}

If you need more information before calling a tool, respond with:

    {"response": "<your clarifying question>"}

If the user is just chatting or asking a general question, respond with:

    {"response": "<helpful answer>"}

## Important Rules

1. **All monetary amounts in INTEGER PENCE.**  £50.00 → 5000, £1,200.00 → 120000.
   Never use floats or decimals for money.

2. **Dates in ISO 8601 format** (YYYY-MM-DD).  If the user says "today",
   "yesterday", "last month", etc., resolve to an actual date.  Today is
   {today}.

3. **Only call tools that exist** in the registry below.  If the user asks for
   something that has no matching tool, respond with a clarifying question
   instead of guessing.

4. **For setup / onboarding** (the system has no chart of accounts yet), guide
   the user through setup steps rather than calling tools that would fail.

## Available Tools

{tools_json}

## Current Conversation Context

{context}
"""

# ---------------------------------------------------------------------------
# Setup wizard detection prompt (used before normal routing)
# ---------------------------------------------------------------------------
SETUP_CHECK_PROMPT = """You are checking whether this accounting system needs initial setup.

The system currently has {account_count} accounts in the chart of accounts.

If account_count is 0:
  - The system is FRESH — this is a first-time user.
  - Respond with: {{"setup_required": true, "step": "welcome"}}

If account_count is greater than 0:
  - The system is already set up.
  - Respond with: {{"setup_required": false}}"""


class LLMRouterError(Exception):
    """LLM call failed or returned unparseable response."""


class LLMRouter:
    """Stateless service that routes user messages to accounting tools via LLM."""

    def __init__(self) -> None:
        self._registry = SkillRegistry()

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    async def route(
        self,
        user_message: str,
        history: list[dict[str, Any]],
        context: dict[str, Any],
        account_count: int = 0,
    ) -> dict[str, Any]:
        """Route a user message to a tool call or text response.

        Returns one of:
          {"tool": "skill_id", "params": {...}}     — tool to execute
          {"response": "text"}                       — chat reply
          {"setup_required": true, "step": "welcome"} — start setup wizard
        """
        # 1) Build prompt with tools + context (inject setup context if fresh)
        tools = self._registry.list_skills()
        prompt = self._build_system_prompt(tools, history, context, account_count)

        # 3) Call LLM
        raw = await self._call_llm(prompt, user_message)

        # 4) Parse JSON response
        return self._parse_response(raw)

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------
    def _build_system_prompt(
        self,
        tools: list[dict[str, Any]],
        history: list[dict[str, Any]],
        context: dict[str, Any],
        account_count: int = 0,
    ) -> str:
        """Build the full system prompt with tools and context."""
        # Inject setup context if system is fresh
        setup_extra = ""
        if account_count == 0:
            from src.services.setup_wizard import SetupWizard
            setup_extra = SetupWizard.get_setup_prompt()

        # Build a compact tool list (id, name, description, params, example)
        tool_snippets: list[dict[str, Any]] = []
        for t in tools:
            snippet = {
                "id": t.get("id"),
                "name": t.get("name", t.get("id")),
                "description": t.get("description", ""),
                "params": t.get("inputSchema", {}).get("properties", {}),
                "required": t.get("inputSchema", {}).get("required", []),
                "example": t.get("example", ""),
            }
            tool_snippets.append(snippet)

        tools_json = json.dumps(tool_snippets, indent=2)

        # Build context string from recent history
        context_lines: list[str] = []
        for entry in history[-10:]:  # last 10 turns
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            if isinstance(content, str) and len(content) > 300:
                content = content[:300] + "..."
            context_lines.append(f"[{role}] {content}")

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ctx_str = "\n".join(context_lines) if context_lines else "(no prior conversation)"
        result = SYSTEM_PROMPT.replace("{today}", today).replace("{tools_json}", tools_json).replace("{context}", ctx_str)
        if setup_extra:
            result += "\n" + setup_extra
        return result

    async def _call_llm(self, system_prompt: str, user_message: str) -> str:
        """Call the LLM API and return the raw response text."""
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if LLM_API_KEY:
            headers["Authorization"] = f"Bearer {LLM_API_KEY}"

        payload = {
            "model": LLM_MODEL,
            "temperature": LLM_TEMPERATURE,
            "max_tokens": LLM_MAX_TOKENS,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                response = await client.post(LLM_API_URL, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return content.strip()
        except httpx.HTTPError as exc:
            logger.error("LLM API call failed: %s", exc)
            raise LLMRouterError(f"LLM API error: {exc}") from exc
        except (KeyError, IndexError) as exc:
            logger.error("Unexpected LLM response format: %s", exc)
            raise LLMRouterError("LLM returned unexpected response format") from exc

    def _parse_response(self, raw: str) -> dict[str, Any]:
        """Parse the LLM's JSON response into a structured result.

        Handles common LLM output quirks: wrapping in ```json fences, trailing commas,
        extra whitespace.
        """
        # Strip markdown code fences
        text = raw.strip()
        if text.startswith("```"):
            # Remove opening fence line
            text = text[text.index("\n") + 1:] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[: text.rindex("```")].strip()

        # Remove trailing commas before closing brackets/braces (common LLM artifact)
        text = text.replace(",}", "}").replace(",]", "]").replace(",\n}", "\n}").replace(",\n]", "\n]")

        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            # Try to extract a JSON object from the text
            import re
            match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group(0))
                except json.JSONDecodeError:
                    logger.warning("Could not parse LLM response as JSON: %s", raw[:200])
                    return {"response": raw[:500]}
            else:
                logger.warning("No JSON object found in LLM response: %s", raw[:200])
                return {"response": raw[:500]}

        # Normalise result
        if "tool" in result:
            return {"tool": result["tool"], "params": result.get("params", {})}
        if "response" in result:
            return {"response": result["response"]}
        if "setup_required" in result:
            return result

        # Fallback: treat whole response as text
        return {"response": raw[:500]}

    async def _check_setup(
        self,
        user_message: str,
        account_count: int,
        history: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Only force setup wizard on the very first message. After that,
        let the LLM handle routing — it will naturally guide the user
        through setup by calling the appropriate tools."""
        if account_count > 0:
            return {"setup_required": False}

        # Only intercept the first-ever message (no history yet).
        # The LLM is perfectly capable of guiding setup via natural conversation.
        if len(history) <= 1:
            return {"setup_required": True, "step": "welcome"}

        return {"setup_required": False}
