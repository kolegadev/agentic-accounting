"""Setup Wizard — injects context into the LLM prompt when the system is fresh
(empty chart of accounts).  The LLM handles the entire setup conversation
naturally — asking about business type, loading COA templates, and configuring
VAT/bank accounts — by calling the appropriate tools through the tool executor.

There is NO hardcoded state machine — every response is LLM-generated.
"""

from __future__ import annotations

from typing import Any

SETUP_CONTEXT_PROMPT = """
## SETUP MODE

This is a FRESH system with NO chart of accounts. The user needs to set up
their company before they can use any accounting features.

Guide the user through setup conversationally. When they provide information,
call the appropriate tools:

- `coa.add_account` or `coa.load_template` — when user picks a business type
- `bank.add_account` — when user provides bank details
- `contact.create` — when user provides business/contact info

Respond naturally — don't use a rigid step-by-step form. Be conversational
and helpful. If the user asks about reports, explain they need to set up
first, then guide them back to setup.

Available COA templates: uk_sole_trader, uk_limited_company, uk_partnership,
  uk_micro_entity, uk_property_landlord

When the user indicates their business type, immediately call the appropriate
tool to load the template (e.g., coa.add_account or suggest the template).
Then ask about VAT registration and bank accounts.
"""


class SetupWizard:
    """Provides setup context for the LLM prompt. No state machine."""

    @staticmethod
    def get_setup_prompt() -> str:
        """Return the setup context to inject into the LLM system prompt."""
        return SETUP_CONTEXT_PROMPT
