"""Setup Wizard — guides a first-time user through company initialization.

State machine: WELCOME → ASK_BUSINESS_TYPE → ASK_COA_TEMPLATE → ASK_VAT → ASK_BANK → COMPLETE

This is NOT regex-based — it tracks state in the conversation context and
calls actual accounting services (CoaService.load_template, BankService, etc.)
to set up the company.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────────
BUSINESS_TYPE_TEMPLATES: dict[str, str] = {
    "sole trader": "uk_sole_trader",
    "sole_trader": "uk_sole_trader",
    "limited company": "uk_limited_company",
    "limited_company": "uk_limited_company",
    "ltd": "uk_limited_company",
    "partnership": "uk_partnership",
    "micro-entity": "uk_micro_entity",
    "micro_entity": "uk_micro_entity",
    "property landlord": "uk_property_landlord",
    "property_landlord": "uk_property_landlord",
}

COA_TEMPLATE_DESCRIPTIONS: dict[str, str] = {
    "uk_sole_trader": "UK Sole Trader — simplified accounts for self-employed individuals",
    "uk_limited_company": "UK Limited Company — full double-entry for Ltd companies (Companies House ready)",
    "uk_partnership": "UK Partnership — shared accounts for business partnerships",
    "uk_micro_entity": "UK Micro-Entity — minimal FRS 105 accounts for very small companies",
    "uk_property_landlord": "UK Property Landlord — specialised accounts for rental income and expenses",
}

SETUP_STEPS = ["welcome", "ask_business_type", "ask_coa_template", "ask_vat", "ask_bank", "complete"]


class SetupWizardError(Exception):
    """Setup wizard encountered an error."""


class SetupWizard:
    """Stateless wizard that manages company setup conversation flow."""

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    @staticmethod
    async def handle_step(
        db: AsyncSession,
        current_step: str,
        user_message: str,
        setup_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Process one setup wizard step and return the next state + response.

        Returns: {"next_step": str, "response": str, "setup_context": dict}
        When next_step == "complete", the setup is finished.
        """
        step = current_step or "welcome"

        if step == "welcome":
            return SetupWizard._step_welcome()
        elif step == "ask_business_type":
            return await SetupWizard._step_business_type(db, user_message, setup_context)
        elif step == "ask_coa_template":
            return await SetupWizard._step_coa_template(db, user_message, setup_context)
        elif step == "ask_vat":
            return await SetupWizard._step_vat(user_message, setup_context)
        elif step == "ask_bank":
            return await SetupWizard._step_bank(db, user_message, setup_context)
        else:
            return SetupWizard._step_welcome()

    # ------------------------------------------------------------------
    # step handlers
    # ------------------------------------------------------------------
    @staticmethod
    def _step_welcome() -> dict[str, Any]:
        return {
            "next_step": "ask_business_type",
            "response": (
                "👋 **Welcome to Agentic Accounting!**\n\n"
                "Let's get your business set up. I'll guide you through a few quick steps.\n\n"
                "**First — what type of business are you?**\n"
                "• Sole Trader\n"
                "• Limited Company (Ltd)\n"
                "• Partnership\n"
                "• Micro-Entity\n"
                "• Property Landlord"
            ),
            "setup_context": {"business_type": None, "coa_template": None, "vat_registered": None, "vat_scheme": None},
        }

    @staticmethod
    async def _step_business_type(
        db: AsyncSession,
        user_message: str,
        ctx: dict[str, Any],
    ) -> dict[str, Any]:
        msg = user_message.lower().strip()
        template_key = None
        for keyword, tpl in BUSINESS_TYPE_TEMPLATES.items():
            if keyword in msg:
                template_key = tpl
                break

        if template_key is None:
            return {
                "next_step": "ask_business_type",
                "response": (
                    "I didn't quite catch that. Are you a:\n"
                    "• **Sole Trader**\n"
                    "• **Limited Company** (Ltd)\n"
                    "• **Partnership**\n"
                    "• **Micro-Entity**\n"
                    "• **Property Landlord**\n\n"
                    "Just type one of the above."
                ),
                "setup_context": ctx,
            }

        from src.services.coa_service import CoaService
        available = CoaService.list_available_templates()
        ctx["business_type"] = template_key

        # Build template list matching this business type
        matching = [t for t in available if template_key in t]
        if not matching:
            matching = available[:3]  # fallback

        template_list = "\n".join(
            f"• **{t}** — {COA_TEMPLATE_DESCRIPTIONS.get(t, '')}"
            for t in matching[:5]
        )

        return {
            "next_step": "ask_coa_template",
            "response": (
                f"✅ Business type set to **{template_key.replace('_', ' ').title()}**.\n\n"
                f"I found these chart of accounts templates:\n{template_list}\n\n"
                f"Which template would you like to use? Type the name (e.g., `uk_sole_trader`)."
            ),
            "setup_context": ctx,
        }

    @staticmethod
    async def _step_coa_template(
        db: AsyncSession,
        user_message: str,
        ctx: dict[str, Any],
    ) -> dict[str, Any]:
        from src.services.coa_service import CoaService

        template_name = user_message.strip().lower().replace(" ", "_")
        available = CoaService.list_available_templates()

        if template_name not in available:
            return {
                "next_step": "ask_coa_template",
                "response": (
                    f"`{template_name}` is not one of the available templates.\n"
                    f"Available: {', '.join(f'`{t}`' for t in available)}\n\n"
                    f"Type the exact template name."
                ),
                "setup_context": ctx,
            }

        # Load the template
        try:
            accounts = await CoaService.load_template(db, template_name)
            ctx["coa_template"] = template_name
            return {
                "next_step": "ask_vat",
                "response": (
                    f"✅ Loaded **{len(accounts)} accounts** from the `{template_name}` chart of accounts.\n\n"
                    f"**Are you VAT registered?** (yes/no)\n"
                    f"If yes, I'll also ask which VAT scheme you use."
                ),
                "setup_context": ctx,
            }
        except Exception as exc:
            logger.exception("Failed to load COA template %s", template_name)
            return {
                "next_step": "ask_coa_template",
                "response": f"❌ Could not load template: {exc}. Try a different template.",
                "setup_context": ctx,
            }

    @staticmethod
    async def _step_vat(
        user_message: str,
        ctx: dict[str, Any],
    ) -> dict[str, Any]:
        msg = user_message.lower().strip()

        if msg in ("yes", "y", "yeah", "yep", "true"):
            ctx["vat_registered"] = True
            return {
                "next_step": "ask_vat",
                "response": (
                    "Which VAT scheme do you use?\n"
                    "• **Standard** — reclaim VAT on purchases, charge on sales (most common)\n"
                    "• **Cash** — VAT accounted for when payments are made/received\n"
                    "• **Flat Rate** — pay a fixed percentage of turnover\n\n"
                    "Type one: `standard`, `cash`, or `flat rate`."
                ),
                "setup_context": ctx,
            }

        if msg in ("no", "n", "nope", "false"):
            ctx["vat_registered"] = False
            ctx["vat_scheme"] = "none"
            return {
                "next_step": "ask_bank",
                "response": (
                    "✅ VAT: not registered. You can add VAT later if needed.\n\n"
                    "**Last step — what's your main bank account called?**\n"
                    "e.g., 'Business Current Account' or 'Starling Business'"
                ),
                "setup_context": ctx,
            }

        # Check for VAT scheme selection
        if msg in ("standard", "cash", "flat rate", "flat_rate"):
            scheme = msg.replace(" ", "_")
            ctx["vat_scheme"] = scheme
            scheme_display = scheme.replace("_", " ").title()
            return {
                "next_step": "ask_bank",
                "response": (
                    f"✅ VAT: registered — **{scheme_display}** scheme.\n\n"
                    "**Last step — what's your main bank account called?**\n"
                    "e.g., 'Business Current Account' or 'Starling Business'"
                ),
                "setup_context": ctx,
            }

        return {
            "next_step": "ask_vat",
            "response": "I didn't understand. Are you VAT registered? (yes/no)",
            "setup_context": ctx,
        }

    @staticmethod
    async def _step_bank(
        db: AsyncSession,
        user_message: str,
        ctx: dict[str, Any],
    ) -> dict[str, Any]:
        from src.services.bank_service import BankService
        from src.validators.bank_account import BankAccountCreate

        bank_name = user_message.strip()
        if len(bank_name) < 2:
            return {
                "next_step": "ask_bank",
                "response": "Please enter a name for your bank account (e.g., 'Business Current Account').",
                "setup_context": ctx,
            }

        try:
            data = BankAccountCreate(
                name=bank_name,
                currency="GBP",
                opening_balance=0,
            )
            account = await BankService.create_account(db, data)
            ctx["bank_account_id"] = str(account.id)
            ctx["bank_name"] = bank_name

            vat_info = ""
            if ctx.get("vat_registered"):
                vat_info = f"\n📊 VAT: {ctx.get('vat_scheme', 'standard').replace('_', ' ').title()} scheme"
            else:
                vat_info = "\n📊 VAT: not registered"

            return {
                "next_step": "complete",
                "response": (
                    "🎉 **Setup complete!** Here's a summary:\n\n"
                    f"🏢 Business type: **{ctx.get('business_type', 'unknown').replace('_', ' ').title()}**\n"
                    f"📚 Chart of accounts: **{ctx.get('coa_template', 'unknown')}**\n"
                    f"{vat_info}\n"
                    f"🏦 Bank account: **{bank_name}**\n\n"
                    "You're all set! You can now:\n"
                    "• Record expenses — *'Paid £50 for office supplies'*\n"
                    "• Record income — *'Received £1,200 from Acme Ltd'*\n"
                    "• Create invoices — *'Create an invoice for £500 to Client X'*\n"
                    "• Run reports — *'Show me my profit and loss'\n\n"
                    "What would you like to do first?"
                ),
                "setup_context": ctx,
            }
        except Exception as exc:
            logger.exception("Failed to create bank account")
            return {
                "next_step": "ask_bank",
                "response": f"❌ Could not create bank account: {exc}. Try a different name.",
                "setup_context": ctx,
            }
