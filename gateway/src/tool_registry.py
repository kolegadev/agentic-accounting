"""MCP Tool Registry — loads tool definitions from YAML and maps to accounting-API endpoints."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import yaml


class ToolRegistry:
    """Registry of all 40+ accounting tools with endpoint mappings."""

    # Maps tool IDs to accounting API endpoints
    ENDPOINT_MAP: dict[str, dict[str, str]] = {
        # ── Chart of Accounts ──────────────────────────────────────────
        "coa.list": {
            "method": "GET",
            "path": "/api/v1/coa/",
            "query_params": ["include_inactive"],
        },
        "coa.add_account": {
            "method": "POST",
            "path": "/api/v1/coa/",
        },
        "coa.edit_account": {
            "method": "PATCH",
            "path": "/api/v1/coa/{account_id}",
        },
        "coa.set_vat_rate": {
            "method": "PUT",
            "path": "/api/v1/coa/{account_id}/vat-rate",
            "body_as": {"vat_rate": "vat_rate"},
        },
        # ── General Ledger ─────────────────────────────────────────────
        "gl.record_expense": {
            "method": "POST",
            "path": "/api/v1/transactions/",
        },
        "gl.record_income": {
            "method": "POST",
            "path": "/api/v1/transactions/",
        },
        "gl.record_transfer": {
            "method": "POST",
            "path": "/api/v1/transactions/",
        },
        "gl.journal_entry": {
            "method": "POST",
            "path": "/api/v1/transactions/",
        },
        "gl.list_transactions": {
            "method": "GET",
            "path": "/api/v1/transactions/",
            "query_params": ["start_date", "end_date", "account_id", "contact_id", "limit"],
            "param_map": {"start_date": "date_from", "end_date": "date_to"},
        },
        "gl.transaction_detail": {
            "method": "GET",
            "path": "/api/v1/transactions/{transaction_id}",
        },
        "gl.undo_transaction": {
            "method": "POST",
            "path": "/api/v1/transactions/{transaction_id}/reverse",
        },
        # ── Contacts ───────────────────────────────────────────────────
        "contact.create": {
            "method": "POST",
            "path": "/api/v1/contacts/",
        },
        "contact.edit": {
            "method": "PATCH",
            "path": "/api/v1/contacts/{contact_id}",
        },
        "contact.list": {
            "method": "GET",
            "path": "/api/v1/contacts/",
            "query_params": ["type", "search"],
        },
        "contact.detail": {
            "method": "GET",
            "path": "/api/v1/contacts/{contact_id}",
        },
        "contact.archive": {
            "method": "POST",
            "path": "/api/v1/contacts/{contact_id}/archive",
        },
        # ── Bank ───────────────────────────────────────────────────────
        "bank.import_csv": {
            "method": "POST_FILE",
            "path": "/api/v1/bank/import/csv",
            "query_params": ["account_id", "template"],
            "param_map": {"bank_account_id": "account_id", "format": "template"},
        },
        "bank.import_ofx": {
            "method": "POST_FILE",
            "path": "/api/v1/bank/import/ofx",
            "query_params": ["account_id"],
            "param_map": {"bank_account_id": "account_id"},
        },
        "bank.list_accounts": {
            "method": "GET",
            "path": "/api/v1/bank/accounts",
        },
        "bank.add_account": {
            "method": "POST",
            "path": "/api/v1/bank/accounts",
        },
        "bank.transactions": {
            "method": "GET",
            "path": "/api/v1/bank/transactions",
            "query_params": ["account_id", "start_date", "end_date", "status"],
            "param_map": {"bank_account_id": "account_id", "start_date": "date_from", "end_date": "date_to"},
        },
        "bank.categorize": {
            "method": "PATCH",
            "path": "/api/v1/bank/transactions/{bank_transaction_id}/categorize",
        },
        # ── Reconciliation ─────────────────────────────────────────────
        "recon.start": {
            "method": "POST",
            "path": "/api/v1/reconciliation/start",
        },
        "recon.match": {
            "method": "POST",
            "path": "/api/v1/reconciliation/{reconciliation_id}/match",
        },
        "recon.create_and_match": {
            "method": "POST",
            "path": "/api/v1/reconciliation/{reconciliation_id}/create-and-match",
        },
        "recon.status": {
            "method": "GET",
            "path": "/api/v1/reconciliation/{reconciliation_id}/status",
        },
        "recon.report": {
            "method": "GET",
            "path": "/api/v1/reconciliation/{reconciliation_id}/report",
        },
        # ── Invoices ───────────────────────────────────────────────────
        "invoice.create": {
            "method": "POST",
            "path": "/api/v1/invoices/",
        },
        "invoice.send": {
            "method": "POST",
            "path": "/api/v1/invoices/{invoice_id}/send",
        },
        "invoice.list": {
            "method": "GET",
            "path": "/api/v1/invoices/",
            "query_params": ["status", "contact_id"],
        },
        "invoice.mark_paid": {
            "method": "POST",
            "path": "/api/v1/invoices/{invoice_id}/mark-paid",
        },
        "invoice.credit_note": {
            "method": "POST",
            "path": "/api/v1/invoices/{invoice_id}/credit-note",
            "query_params": ["reason"],
        },
        "invoice.overdue": {
            "method": "GET",
            "path": "/api/v1/invoices/overdue",
        },
        # ── VAT ────────────────────────────────────────────────────────
        "vat.preview_return": {
            "method": "POST",
            "path": "/api/v1/vat/preview",
            "special": "vat_preview",
        },
        "vat.transaction_detail": {
            "method": "GET",
            "path": "/api/v1/vat/returns/{vat_period_id}/audit",
            "param_map": {"vat_period_id": "return_id"},
        },
        "vat.adjustment": {
            "method": "POST",
            "path": "/api/v1/vat/returns/{vat_period_id}/adjustment",
            "param_map": {"vat_period_id": "return_id"},
        },
        "vat.audit_trail": {
            "method": "GET",
            "path": "/api/v1/vat/returns/{vat_period_id}/audit",
            "param_map": {"vat_period_id": "return_id"},
        },
        # ── Reports ────────────────────────────────────────────────────
        "report.run": {
            "method": "POST",
            "path": "/api/v1/reports/run",
        },
        "report.list": {
            "method": "GET",
            "path": "/api/v1/reports/templates",
        },
        "report.schedule": {
            "method": "POST",
            "path": "/api/v1/reports/schedules",
        },
    }

    def __init__(self, registry_path: str | None = None) -> None:
        self._tools: list[dict[str, Any]] = []
        self._tools_by_id: dict[str, dict[str, Any]] = {}
        self._registry_path = registry_path or os.environ.get(
            "SKILL_REGISTRY_PATH", "/app/skills/registry.yaml"
        )
        self.load_tools()

    def load_tools(self) -> None:
        """Load tool definitions from the YAML registry."""
        try:
            with open(self._registry_path, "r") as f:
                raw_tools: list[dict[str, Any]] = yaml.safe_load(f) or []
        except FileNotFoundError:
            print(f"WARNING: Registry file not found at {self._registry_path}")
            raw_tools = []
        except yaml.YAMLError as exc:
            print(f"ERROR: Failed to parse registry YAML: {exc}")
            raw_tools = []

        self._tools = []
        self._tools_by_id = {}

        for tool in raw_tools:
            tool_id = tool.get("id", "")
            if not tool_id:
                continue

            endpoint = self.ENDPOINT_MAP.get(tool_id, {})
            enriched = {
                "name": tool_id,
                "description": tool.get("description", ""),
                "inputSchema": tool.get("inputSchema", {"type": "object", "properties": {}}),
                "category": tool.get("category", "Other"),
                "displayName": tool.get("name", tool_id),
                "example": tool.get("example", ""),
                "endpoint": {
                    "method": endpoint.get("method", "POST"),
                    "path": endpoint.get("path", "/"),
                },
            }
            self._tools.append(enriched)
            self._tools_by_id[tool_id] = enriched

    def list_tools(self) -> list[dict[str, Any]]:
        """Return all tools in MCP-compatible format."""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t["inputSchema"],
            }
            for t in self._tools
        ]

    def get_tool(self, name: str) -> dict[str, Any] | None:
        """Look up a single tool by name."""
        return self._tools_by_id.get(name)

    def get_endpoint(self, name: str) -> dict[str, Any] | None:
        """Return the endpoint mapping for a tool."""
        return self.ENDPOINT_MAP.get(name)

    def get_all_tools(self) -> list[dict[str, Any]]:
        """Return full tool objects with endpoint info (for internal use)."""
        return self._tools

    @property
    def tool_count(self) -> int:
        return len(self._tools)


# Singleton instance
_global_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    """Return the global ToolRegistry singleton."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry
