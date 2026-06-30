"""Prompt Assembler — loads architecture documentation at startup and builds
comprehensive system prompts for every LLM turn.

Replaces the thin SYSTEM_PROMPT template in llm_router.py with a multi-section
prompt that includes:

  Section A — System Identity & Accounting Domain Model
  Section B — Architecture Overview (Formance, Katra, MCP Gateway)
  Section C — Katra Cognitive Memory Primer (4 modalities)
  Section D — Formance Ledger Primer (double-entry engine)
  Section E — Full Tool Catalog (from SKILL.md + YAML registry)
  Section F — Conversation Context (last N turns)
  Section G — Formatting & Output Rules

The documentation (SKILL.md, MCP_DOCUMENTATION.md) is loaded once at module
import time and cached.  Each prompt assembly injects the relevant sections
without re-reading files.

Usage:
    from src.services.prompt_assembler import assemble_system_prompt

    prompt = assemble_system_prompt(tools, history, context, account_count)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Documentation cache — loaded once at module import
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # .../agentic-accounting/

_CACHE: dict[str, str] = {}


def _load_doc(filename: str) -> str:
    """Load a documentation file from the project root, with caching."""
    if filename in _CACHE:
        return _CACHE[filename]
    path = _PROJECT_ROOT / filename
    if path.exists():
        _CACHE[filename] = path.read_text(encoding="utf-8")
        return _CACHE[filename]
    logger.warning("Documentation file not found: %s", path)
    return ""


def _extract_section(doc: str, heading: str, next_heading: str | None = None) -> str:
    """Extract a markdown section between two headings.  Stops at the next
    same-level heading or *next_heading* if given."""
    lines = doc.split("\n")
    start = -1
    depth = 0
    for i, line in enumerate(lines):
        if line.strip().startswith(heading):
            start = i
            depth = len(heading) - len(heading.lstrip("#"))
            continue
        if start >= 0:
            stripped = line.strip()
            if stripped.startswith("#"):
                h_depth = len(stripped) - len(stripped.lstrip("#"))
                if h_depth <= depth:
                    return "\n".join(lines[start:i]).strip()
            if next_heading and stripped.startswith(next_heading):
                return "\n".join(lines[start:i]).strip()
    if start >= 0:
        return "\n".join(lines[start:]).strip()
    return ""


# ---------------------------------------------------------------------------
# Section builders — each returns a string for one prompt section
# ---------------------------------------------------------------------------

def _section_identity() -> str:
    """System identity and accounting domain model (from SKILL.md overview)."""
    skill = _load_doc("SKILL.md")
    overview = _extract_section(skill, "## Overview", "## Quick Start")
    if not overview:
        overview = _extract_section(skill, "# Agentic Accounting — MCP SKILL.md", "## Quick Start")
    return (
        "## SYSTEM IDENTITY\n\n"
        + (overview or "You are an AI bookkeeper for Agentic Accounting.")
        + "\n\nYou are the Chat UI LLM — your job is to understand the user's "
        "intent and route it to the appropriate accounting tool.  You have "
        "FULL access to all 40+ tools in the system.  Every tool call you "
        "make executes REAL accounting operations against a PostgreSQL "
        "double-entry ledger backed by Formance (immutable postings, full "
        "audit trails, MTD-compliant VAT records)."
    )


def _section_architecture() -> str:
    """Architecture overview — Formance, Katra, MCP Gateway (from MCP_DOCUMENTATION.md)."""
    mcp_doc = _load_doc("MCP_DOCUMENTATION.md")
    overview = _extract_section(mcp_doc, "## 1. MCP Gateway Overview", "## 2. Connection")
    if not overview:
        overview = _extract_section(mcp_doc, "# Agentic Accounting — MCP Documentation", "## 2.")

    # Also grab the Katra-specific section
    katra_section = _extract_section(mcp_doc, "### Katra Cognitive Memory Integration", "## 2.")
    if not katra_section:
        # Try broader extraction
        for h in mcp_doc.split("\n"):
            if "Katra Cognitive" in h:
                katra_section = _extract_section(mcp_doc, h.strip(), "## 2.")
                break

    return (
        "## SYSTEM ARCHITECTURE\n\n"
        "You operate within a multi-service accounting platform:\n\n"
        "| Service | Port | Purpose |\n"
        "|---------|------|---------|\n"
        "| **Formance Ledger** | 3068 | Immutable double-entry ledger engine — "
        "every transaction flows through Formance as numbered postings with "
        "source/destination/amount/asset fields |\n"
        "| **Katra Cognitive Memory** | 3113 | Four-layer cognitive memory — "
        "episodic (conversation history), semantic (vector search), knowledge "
        "graph (entity relationships), temporal (time-series awareness) |\n"
        "| **MCP Gateway** | 3200 | Exposes 45+ tools to external AI agents "
        "(OpenClaw, Claude Code) via SSE + JSON-RPC |\n"
        "| **Accounting API** | 8000 | Headless REST API — your direct backend |\n"
        "| **PostgreSQL** | 5432 | Primary data store with full audit trails |\n\n"
        + (overview[:2000] if overview else "")
    )


def _section_katra() -> str:
    """Katra cognitive memory primer — four modalities and how to use them."""
    mcp_doc = _load_doc("MCP_DOCUMENTATION.md")
    katra_section = ""
    for heading in [
        "### Katra Cognitive Memory Integration",
        "Katra Cognitive Memory Integration",
    ]:
        katra_section = _extract_section(mcp_doc, heading)
        if katra_section:
            break

    return (
        "## KATRA COGNITIVE MEMORY\n\n"
        "Katra provides FOUR memory modalities accessible via the `memory.search` tool:\n\n"
        "1. **Episodic Memory** — Every conversation turn, tool call, and transaction "
        "is stored as an event.  Search for 'what did we discuss last session' or "
        "'show my recent expense recordings'.\n\n"
        "2. **Semantic Memory** — Vector search across ALL stored sessions.  Find "
        "conceptually similar past interactions even with different wording.\n\n"
        "3. **Knowledge Graph** — Entities (contacts, accounts, invoices, transactions) "
        "are linked.  'Which invoices are linked to Acme Ltd?' traverses the graph.\n\n"
        "4. **Temporal Memory** — Time-series awareness.  'What was my revenue trend "
        "over Q2?' or 'Show me transaction volume by month'.\n\n"
        "Use `memory.search` with natural language queries — Katra handles the routing "
        "to the appropriate memory layer automatically.\n\n"
        + (katra_section[:1500] if katra_section else "")
    )


def _section_formance() -> str:
    """Formance Ledger primer — what it does and key API concepts."""
    return (
        "## FORNANCE LEDGER (DOUBLE-ENTRY ENGINE)\n\n"
        "Formance Ledger is the immutable double-entry engine that underpins every "
        "accounting operation.  Key concepts:\n\n"
        "- **Transactions** are numbered, immutable postings.  Once written, they "
        "cannot be modified — corrections are made via reversing entries.\n"
        "- **Postings** have four fields: `source` (account address), `destination` "
        "(account address), `amount` (in the smallest currency unit — INTEGER PENCE "
        "for GBP), and `asset` (currency, e.g., 'GBP/2').\n"
        "- **Balances** are computed from the sum of all postings — there is no "
        "separate 'balance' table.  Every balance query is a live aggregation.\n"
        "- **Idempotency** is enforced — duplicate postings are rejected.\n\n"
        "When the user records an expense, income, transfer, or journal entry, the "
        "system creates a Formance transaction behind the scenes.  The GL tools "
        "(`gl.record_expense`, `gl.record_income`, etc.) abstract this away — you "
        "don't need to construct Formance postings manually.  But you SHOULD mention "
        "Formance when users ask about data integrity, audit trails, or how their "
        "transactions are stored."
    )


def _section_tools(tools: list[dict[str, Any]]) -> str:
    """Build the tool catalog section — richer than the old bare snippets.

    Includes the tool reference from SKILL.md plus the compact JSON snippets
    the LLM needs for tool-calling decisions.
    """
    # Rich reference from SKILL.md (domain-organized)
    skill_doc = _load_doc("SKILL.md")
    tool_reference = _extract_section(skill_doc, "## Tool Reference")
    if not tool_reference:
        tool_reference = _extract_section(skill_doc, "## Tool Reference", "## Server Configuration")

    # Compact JSON snippets (same format as before — needed for structured output)
    import json
    tool_snippets = []
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

    parts = ["## TOOL CATALOG\n"]
    if tool_reference:
        # Truncate to keep prompt manageable — the full SKILL.md is ~15K chars
        parts.append(tool_reference[:8000])
        parts.append("\n\n### Tool Schemas (JSON)\n")
    parts.append(tools_json)
    return "\n".join(parts)


def _section_context(history: list[dict[str, Any]]) -> str:
    """Build the conversation context section from recent history."""
    lines: list[str] = []
    for entry in history[-10:]:
        role = entry.get("role", "unknown")
        content = entry.get("content", "")
        if isinstance(content, str) and len(content) > 300:
            content = content[:300] + "..."
        lines.append(f"[{role}] {content}")
    ctx_str = "\n".join(lines) if lines else "(no prior conversation — this is the first turn)"
    return "## CONVERSATION CONTEXT\n\n" + ctx_str


def _section_rules() -> str:
    """Formatting and operational rules (distilled from the original SYSTEM_PROMPT)."""
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return (
        "## OPERATIONAL RULES\n\n"
        f"1. **All monetary amounts in INTEGER PENCE.**  £50.00 → 5000.  Never use floats.\n"
        f"2. **Dates in ISO 8601 format** (YYYY-MM-DD).  Today is {today}.\n"
        "3. **Only call tools that exist** in the catalog above.\n"
        "4. **For setup: use `coa.load_template`** — never list individual accounts.\n"
        "5. **Use markdown formatting — NEVER emit raw HTML tags.**\n"
        "6. **For accounts, use markdown TABLES, not bullet lists.**\n"
        "7. **Keep responses concise** — let tool results speak for themselves.\n"
        "8. **Tool-chaining: only respond with text when the ENTIRE request is fulfilled.**\n"
        "   If the task is incomplete, call the NEXT required tool.\n"
        "9. **When creating invoices for new customers: create contact FIRST, then invoice.**\n"
        "10. **For reports without dates: use current financial year or year-to-date.**\n"
        "11. **Use `memory.search` for past activity, tools for current state.**"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def assemble_system_prompt(
    tools: list[dict[str, Any]],
    history: list[dict[str, Any]],
    account_count: int = 0,
    *,
    mode: str = "routing",
) -> str:
    """Assemble the complete system prompt for an LLM turn.

    Args:
        tools: Tool definitions from SkillRegistry.list_skills().
        history: Conversation history (list of {role, content} dicts).
        account_count: Number of accounts in COA (0 = fresh system).
        mode: "routing" (full prompt with tool catalog) or "response"
              (lighter prompt for response generation — still includes
              architecture context but omits the full tool JSON).

    Returns:
        Complete system prompt string ready for LLM injection.
    """
    sections: list[str] = []

    # Sections A–D: architecture context (ALWAYS included, even in response mode)
    sections.append(_section_identity())
    sections.append(_section_architecture())
    sections.append(_section_katra())
    sections.append(_section_formance())

    if mode == "routing":
        # Full mode: include tool catalog + context + rules
        sections.append(_section_tools(tools))
        sections.append(_section_context(history))
        sections.append(_section_rules())
    else:
        # Response mode: lighter — architecture context + rules but no full tool JSON
        sections.append(_section_context(history))
        sections.append(_section_rules())
        sections.append(
            "\n## RESPONSE INSTRUCTIONS\n\n"
            "Generate a natural, conversational response to the user.  "
            "Be helpful and concise.  Use markdown formatting — NEVER emit "
            "raw HTML tags.  For tabular data, use markdown tables."
        )

    # Append setup wizard context if fresh system
    if account_count == 0 and mode == "routing":
        from src.services.setup_wizard import SetupWizard
        sections.append(SetupWizard.get_setup_prompt())

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Cache warming — load docs at import time
# ---------------------------------------------------------------------------

# Trigger loading now so first prompt assembly is instant
_load_doc("SKILL.md")
_load_doc("MCP_DOCUMENTATION.md")
