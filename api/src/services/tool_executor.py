"""Tool Executor — maps skill IDs from the registry to actual async service method
calls.  This is the bridge between LLM-selected tools and the real accounting
infrastructure.  No simulation — every call hits the database.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ToolExecutorError(Exception):
    """A tool execution failed at the service layer."""


class ToolExecutor:
    """Stateless executor that dispatches skill IDs to the correct service."""

    # Map of supported tool IDs — everything in the registry that has a
    # corresponding service method.
    SUPPORTED_TOOLS: set[str] = {
        "business.set_profile",
        "memory.search",
        "coa.list", "coa.add_account", "coa.edit_account", "coa.set_vat_rate",
        "coa.load_template",
        "coa.detail",
        "gl.record_expense", "gl.record_income", "gl.record_transfer",
        "gl.journal_entry", "gl.list_transactions", "gl.transaction_detail",
        "gl.undo_transaction",
        "contact.create", "contact.edit", "contact.list", "contact.detail",
        "contact.archive",
        "bank.import_csv", "bank.import_ofx", "bank.list_accounts",
        "bank.add_account", "bank.transactions", "bank.categorize",
        "recon.start", "recon.match", "recon.create_and_match",
        "recon.status", "recon.report",
        "invoice.create", "invoice.send", "invoice.list", "invoice.mark_paid",
        "invoice.credit_note", "invoice.overdue",
        "vat.preview_return", "vat.transaction_detail", "vat.adjustment",
        "vat.audit_trail",
        "report.run", "report.list", "report.schedule",
    }

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    @staticmethod
    async def execute(
        db: AsyncSession,
        skill_id: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a tool by skill_id with the given params.

        Returns a dict with at least {"success": True, "result": ...}
        or {"success": False, "error": "..."}.
        """
        if skill_id not in ToolExecutor.SUPPORTED_TOOLS:
            return {"success": False, "error": f"Unknown tool: {skill_id}"}

        try:
            handler = _HANDLERS.get(skill_id)
            if handler is None:
                return {"success": False, "error": f"No handler for tool: {skill_id}"}
            result = await handler(db, params)
            return {"success": True, "result": result}
        except Exception as exc:
            logger.exception("Tool %s failed: %s", skill_id, exc)
            return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Handler registry — one async function per skill_id
# ---------------------------------------------------------------------------
# Each handler: async (db: AsyncSession, params: dict) -> Any

async def _coa_list(db: AsyncSession, params: dict) -> Any:
    from src.services.coa_service import CoaService
    from src.services.formatting import render_table
    include = params.get("include_inactive", False)
    accounts = await CoaService.list_accounts(db, include_inactive=include)
    return render_table(
        [a.model_dump() for a in accounts],
        columns=[
            ("code", "Code"),
            ("name", "Account Name"),
            ("category", "Category"),
            ("type", "Type"),
            ("vat_rate", "VAT"),
        ],
    )


async def _coa_add_account(db: AsyncSession, params: dict) -> Any:
    from src.services.coa_service import CoaService
    from src.validators.account import AccountCreate
    data = AccountCreate(
        code=str(params["code"]),
        name=str(params["name"]),
        category=str(params["category"]),
        type=str(params["type"]),
        vat_rate=params.get("vat_rate"),
        parent_id=uuid.UUID(params["parent_id"]) if params.get("parent_id") else None,
    )
    account = await CoaService.create_account(db, data)
    return account.model_dump()


async def _coa_edit_account(db: AsyncSession, params: dict) -> Any:
    from src.services.coa_service import CoaService
    from src.validators.account import AccountUpdate
    data = AccountUpdate(**{k: v for k, v in params.items() if k != "account_id" and v is not None})
    account = await CoaService.update_account(db, uuid.UUID(params["account_id"]), data)
    return account.model_dump()


async def _coa_load_template(db: AsyncSession, params: dict) -> Any:
    from src.services.coa_service import CoaService
    accounts = await CoaService.load_template(db, str(params["template_name"]))
    return {
        "loaded": len(accounts),
        "template": params["template_name"],
        "accounts": [{"code": a.code, "name": a.name, "category": a.category} for a in accounts],
    }


async def _coa_detail(db: AsyncSession, params: dict) -> Any:
    from src.services.coa_service import CoaService
    from src.services.transaction_service import TransactionService
    code = str(params["code"])
    account = await CoaService.get_account_by_code(db, code)
    if not account:
        return {"error": f"Account {code} not found"}
    acct_data = account.model_dump()
    # Also get recent transactions for this account
    transactions, total = await TransactionService.list_transactions(db, limit=10)
    recent = []
    for tx in transactions:
        txd = TransactionService._transaction_to_response(tx).model_dump()
        for p in txd.get("postings", []):
            if p.get("account_code") == code:
                recent.append({
                    "date": str(txd.get("effective_date", "")),
                    "description": txd.get("description", ""),
                    "reference": txd.get("reference", ""),
                    "debit": p.get("debit_amount", 0),
                    "credit": p.get("credit_amount", 0),
                })
    return {
        "account": acct_data,
        "recent_transactions": recent[:20],
        "total_transactions": total,
    }


async def _coa_set_vat_rate(db: AsyncSession, params: dict) -> Any:
    from src.services.coa_service import CoaService
    account = await CoaService.set_vat_rate(
        db, uuid.UUID(params["account_id"]), str(params["vat_rate"])
    )
    return account.model_dump()


# ── GL ──────────────────────────────────────────────────────────────

async def _gl_record_expense(db: AsyncSession, params: dict) -> Any:
    from src.services.coa_service import CoaService
    from src.services.contact_service import ContactService
    from src.services.transaction_service import TransactionService
    from src.validators.transaction import PostingCreate, TransactionCreate

    # Find or resolve accounts
    expense_acct = await CoaService.get_account_by_code(db, "5000")
    if not expense_acct:
        # fallback: look for first Expense account
        all_accts = await CoaService.list_accounts(db)
        expense_acct = next((a for a in all_accts if a.category == "Expense"), None)
    if not expense_acct:
        raise ToolExecutorError("No expense account found — set up chart of accounts first")

    bank_accts = await CoaService.list_accounts(db)
    bank_acct = next((a for a in bank_accts if a.category == "Asset" and a.type == "Bank"), None)
    if not bank_acct:
        raise ToolExecutorError("No bank account found — add a bank account first")

    # Handle contact
    contact_id = None
    contact_name = params.get("contact")
    if contact_name:
        contact, _ = await ContactService.find_or_create(db, name=str(contact_name))
        contact_id = contact.id

    amount = int(params["amount"])
    description = str(params.get("description", "Expense"))
    vat_rate = params.get("vat_rate", "20%")

    postings = [
        PostingCreate(account_id=expense_acct.id, debit_amount=amount, credit_amount=0, description=description),
        PostingCreate(account_id=bank_acct.id, debit_amount=0, credit_amount=amount, description=description),
    ]

    tx_data = TransactionCreate(
        description=description,
        contact_id=contact_id,
        effective_date=date.fromisoformat(params["date"]) if params.get("date") else date.today(),
        postings=postings,
    )
    tx = await TransactionService.create_transaction(db, tx_data)
    posted = await TransactionService.post_transaction(db, tx.id)
    return TransactionService._transaction_to_response(posted).model_dump()


async def _gl_record_income(db: AsyncSession, params: dict) -> Any:
    from src.services.coa_service import CoaService
    from src.services.contact_service import ContactService
    from src.services.transaction_service import TransactionService
    from src.validators.transaction import PostingCreate, TransactionCreate

    all_accts = await CoaService.list_accounts(db)
    income_acct = next((a for a in all_accts if a.category == "Revenue"), None)
    if not income_acct:
        raise ToolExecutorError("No revenue account found")
    bank_acct = next((a for a in all_accts if a.category == "Asset" and a.type == "Bank"), None)
    if not bank_acct:
        raise ToolExecutorError("No bank account found")

    contact_id = None
    if params.get("contact"):
        from src.services.contact_service import ContactService
        contact, _ = await ContactService.find_or_create(db, name=str(params["contact"]))
        contact_id = contact.id

    amount = int(params["amount"])
    description = str(params.get("description", "Income"))

    postings = [
        PostingCreate(account_id=bank_acct.id, debit_amount=amount, credit_amount=0, description=description),
        PostingCreate(account_id=income_acct.id, debit_amount=0, credit_amount=amount, description=description),
    ]
    tx_data = TransactionCreate(
        description=description,
        contact_id=contact_id,
        effective_date=date.fromisoformat(params["date"]) if params.get("date") else date.today(),
        postings=postings,
    )
    tx = await TransactionService.create_transaction(db, tx_data)
    posted = await TransactionService.post_transaction(db, tx.id)
    return TransactionService._transaction_to_response(posted).model_dump()


async def _gl_record_transfer(db: AsyncSession, params: dict) -> Any:
    from src.services.coa_service import CoaService
    from src.services.transaction_service import TransactionService
    from src.validators.transaction import PostingCreate, TransactionCreate

    from_acct = await CoaService.get_account_by_code(db, str(params.get("from_account", "")))
    to_acct = await CoaService.get_account_by_code(db, str(params.get("to_account", "")))
    if not from_acct or not to_acct:
        raise ToolExecutorError("Source or destination account not found")

    amount = int(params["amount"])
    postings = [
        PostingCreate(account_id=to_acct.id, debit_amount=amount, credit_amount=0, description="Transfer in"),
        PostingCreate(account_id=from_acct.id, debit_amount=0, credit_amount=amount, description="Transfer out"),
    ]
    tx_data = TransactionCreate(
        description=params.get("description", "Bank transfer"),
        effective_date=date.fromisoformat(params["date"]) if params.get("date") else date.today(),
        postings=postings,
    )
    tx = await TransactionService.create_transaction(db, tx_data)
    posted = await TransactionService.post_transaction(db, tx.id)
    return TransactionService._transaction_to_response(posted).model_dump()


async def _gl_journal_entry(db: AsyncSession, params: dict) -> Any:
    from src.services.transaction_service import TransactionService
    from src.validators.transaction import PostingCreate, TransactionCreate

    postings_data = params.get("postings", [])
    postings = [
        PostingCreate(
            account_id=uuid.UUID(p["account_id"]),
            debit_amount=int(p.get("debit_amount", 0) or p.get("amount", 0)),
            credit_amount=int(p.get("credit_amount", 0) or 0),
            description=p.get("description", ""),
        )
        for p in postings_data
    ]
    tx_data = TransactionCreate(
        description=params.get("description", "Journal entry"),
        reference=params.get("reference"),
        effective_date=date.fromisoformat(params["date"]) if params.get("date") else date.today(),
        postings=postings,
    )
    tx = await TransactionService.create_transaction(db, tx_data)
    posted = await TransactionService.post_transaction(db, tx.id)
    return TransactionService._transaction_to_response(posted).model_dump()


async def _gl_list_transactions(db: AsyncSession, params: dict) -> Any:
    from src.services.transaction_service import TransactionService
    from datetime import date

    date_from = date.fromisoformat(params["start_date"]) if params.get("start_date") else None
    date_to = date.fromisoformat(params["end_date"]) if params.get("end_date") else None
    contact_id = uuid.UUID(params["contact_id"]) if params.get("contact_id") else None
    limit = int(params.get("limit", 50))

    from src.services.formatting import render_table, format_pence
    items, total = await TransactionService.list_transactions(
        db, date_from=date_from, date_to=date_to, contact_id=contact_id, limit=limit,
    )
    rows = []
    for t in items:
        d = TransactionService._transaction_to_response(t).model_dump()
        d["amount"] = format_pence(d.get("total_amount"))
        rows.append(d)
    return render_table(
        rows,
        columns=[
            ("reference", "Ref"),
            ("description", "Description"),
            ("amount", "Amount"),
            ("status", "Status"),
            ("effective_date", "Date"),
        ],
    )


async def _gl_transaction_detail(db: AsyncSession, params: dict) -> Any:
    from src.services.transaction_service import TransactionService, TransactionNotFoundError
    tx = await TransactionService.get_transaction(db, uuid.UUID(params["transaction_id"]))
    if tx is None:
        raise TransactionNotFoundError(uuid.UUID(params["transaction_id"]))
    return TransactionService._transaction_to_response(tx).model_dump()


async def _gl_undo_transaction(db: AsyncSession, params: dict) -> Any:
    from src.services.transaction_service import TransactionService
    reversed_tx = await TransactionService.reverse_transaction(db, uuid.UUID(params["transaction_id"]))
    return TransactionService._transaction_to_response(reversed_tx).model_dump()


# ── Contacts ─────────────────────────────────────────────────────────

async def _contact_create(db: AsyncSession, params: dict) -> Any:
    from src.services.contact_service import ContactService
    from src.validators.contact import ContactCreate
    data = ContactCreate(
        name=str(params["name"]),
        type=str(params.get("type", "customer")),
        email=params.get("email"),
        phone=params.get("phone"),
        address_line1=params.get("address_line1"),
        city=params.get("city"),
        postcode=params.get("postcode"),
        notes=params.get("notes"),
    )
    contact = await ContactService.create_contact(db, data)
    return contact.model_dump()


async def _contact_edit(db: AsyncSession, params: dict) -> Any:
    from src.services.contact_service import ContactService
    from src.validators.contact import ContactUpdate
    data = ContactUpdate(**{k: v for k, v in params.items() if k != "contact_id" and v is not None})
    contact = await ContactService.update_contact(db, uuid.UUID(params["contact_id"]), data)
    return contact.model_dump()


async def _contact_list(db: AsyncSession, params: dict) -> Any:
    from src.services.contact_service import ContactService
    from src.services.formatting import render_table
    items, total = await ContactService.list_contacts(
        db,
        type=params.get("type"),
        search=params.get("search"),
    )
    return render_table(
        [c.model_dump() for c in items],
        columns=[
            ("name", "Name"),
            ("type", "Type"),
            ("email", "Email"),
            ("phone", "Phone"),
            ("city", "City"),
            ("status", "Status"),
        ],
    )


async def _contact_detail(db: AsyncSession, params: dict) -> Any:
    from src.services.contact_service import ContactService, ContactNotFoundError
    contact = await ContactService.get_contact(db, uuid.UUID(params["contact_id"]))
    if contact is None:
        raise ContactNotFoundError(params["contact_id"])
    return contact.model_dump()


async def _contact_archive(db: AsyncSession, params: dict) -> Any:
    from src.services.contact_service import ContactService
    contact = await ContactService.archive_contact(db, uuid.UUID(params["contact_id"]))
    return contact.model_dump()


# ── Bank ─────────────────────────────────────────────────────────────

async def _bank_import_csv(db: AsyncSession, params: dict) -> Any:
    from src.services.bank_service import BankService
    result = await BankService.import_csv(db, uuid.UUID(params["bank_account_id"]), params.get("file_path", ""))
    return {"imported": result.get("imported", 0), "skipped": result.get("skipped", 0)}


async def _bank_import_ofx(db: AsyncSession, params: dict) -> Any:
    from src.services.bank_service import BankService
    result = await BankService.import_ofx(db, uuid.UUID(params["bank_account_id"]), params.get("file_path", ""))
    return {"imported": result.get("imported", 0), "skipped": result.get("skipped", 0)}


async def _bank_list_accounts(db: AsyncSession, params: dict) -> Any:
    from src.services.bank_service import BankService
    accounts = await BankService.list_accounts(db)
    return [a.model_dump() for a in accounts]


async def _bank_add_account(db: AsyncSession, params: dict) -> Any:
    from src.services.bank_service import BankService
    from src.validators.bank_account import BankAccountCreate
    data = BankAccountCreate(
        name=str(params["name"]),
        account_number=params.get("account_number", ""),
        sort_code=params.get("sort_code", ""),
        currency=params.get("currency", "GBP"),
        opening_balance=int(params.get("opening_balance", 0)),
    )
    account = await BankService.create_account(db, data)
    return account.model_dump()


async def _bank_transactions(db: AsyncSession, params: dict) -> Any:
    from src.services.bank_service import BankService
    from datetime import date
    date_from = date.fromisoformat(params["start_date"]) if params.get("start_date") else None
    date_to = date.fromisoformat(params["end_date"]) if params.get("end_date") else None
    items, total = await BankService.list_transactions(
        db, uuid.UUID(params["bank_account_id"]),
        date_from=date_from, date_to=date_to, status=params.get("status", "all"),
    )
    return {"transactions": [t.model_dump() for t in items], "total": total}


async def _bank_categorize(db: AsyncSession, params: dict) -> Any:
    from src.services.bank_service import BankService
    result = await BankService.categorize_transaction(
        db,
        uuid.UUID(params["bank_transaction_id"]),
        uuid.UUID(params["account_id"]),
        contact_id=uuid.UUID(params["contact_id"]) if params.get("contact_id") else None,
        vat_rate=params.get("vat_rate"),
    )
    return result.model_dump()


# ── Reconciliation ──────────────────────────────────────────────────

async def _recon_start(db: AsyncSession, params: dict) -> Any:
    from src.services.reconciliation_service import ReconciliationService
    session = await ReconciliationService.start_session(
        db, uuid.UUID(params["bank_account_id"]),
        statement_date=date.fromisoformat(params["statement_date"]) if params.get("statement_date") else None,
        statement_balance=int(params["statement_balance"]) if params.get("statement_balance") else None,
    )
    return session.model_dump()


async def _recon_match(db: AsyncSession, params: dict) -> Any:
    from src.services.reconciliation_service import ReconciliationService
    result = await ReconciliationService.match_one_to_one(
        db, uuid.UUID(params["reconciliation_id"]),
        uuid.UUID(params["bank_transaction_id"]),
        uuid.UUID(params["transaction_id"]),
    )
    return result.model_dump() if result else None


async def _recon_create_and_match(db: AsyncSession, params: dict) -> Any:
    from src.services.reconciliation_service import ReconciliationService
    result = await ReconciliationService.create_and_match(
        db, uuid.UUID(params["reconciliation_id"]),
        uuid.UUID(params["bank_transaction_id"]),
        description=params.get("description"),
        amount=int(params.get("amount", 0)),
        vat_rate=params.get("vat_rate"),
        account_id=uuid.UUID(params["account_id"]) if params.get("account_id") else None,
    )
    return result.model_dump()


async def _recon_status(db: AsyncSession, params: dict) -> Any:
    from src.services.reconciliation_service import ReconciliationService
    status = await ReconciliationService.get_session_status(db, uuid.UUID(params["reconciliation_id"]))
    return status.model_dump()


async def _recon_report(db: AsyncSession, params: dict) -> Any:
    from src.services.reconciliation_service import ReconciliationService
    report = await ReconciliationService.generate_report(db, uuid.UUID(params["reconciliation_id"]))
    return report.model_dump()


# ── Invoices ────────────────────────────────────────────────────────

async def _invoice_create(db: AsyncSession, params: dict) -> Any:
    from src.services.invoice_service import InvoiceService
    lines = params.get("lines", [])
    invoice = await InvoiceService.create_invoice(
        db, uuid.UUID(params["contact_id"]),
        lines=[{
            "description": l.get("description", ""),
            "quantity": int(l.get("quantity", 1)),
            "unit_price": int(l.get("unit_price", 0)),
            "vat_rate": l.get("vat_rate", "20%"),
        } for l in lines],
        issue_date=date.fromisoformat(params["issue_date"]) if params.get("issue_date") else None,
        due_date=date.fromisoformat(params["due_date"]) if params.get("due_date") else None,
        notes=params.get("notes"),
    )
    return invoice.model_dump()


async def _invoice_send(db: AsyncSession, params: dict) -> Any:
    from src.services.invoice_service import InvoiceService
    invoice = await InvoiceService.send_invoice(db, uuid.UUID(params["invoice_id"]))
    return invoice.model_dump()


async def _invoice_list(db: AsyncSession, params: dict) -> Any:
    from src.services.invoice_service import InvoiceService
    from src.services.formatting import render_table, format_pence
    items, total = await InvoiceService.list_invoices(
        db,
        status=params.get("status", "all"),
        contact_id=uuid.UUID(params["contact_id"]) if params.get("contact_id") else None,
    )
    rows = []
    for inv in items:
        d = inv.model_dump()
        d["amount"] = format_pence(d.get("total_amount"))
        rows.append(d)
    return render_table(
        rows,
        columns=[
            ("reference", "Invoice"),
            ("status", "Status"),
            ("amount", "Amount"),
            ("issue_date", "Issued"),
            ("due_date", "Due"),
        ],
    )


async def _invoice_mark_paid(db: AsyncSession, params: dict) -> Any:
    from src.services.invoice_service import InvoiceService
    invoice = await InvoiceService.mark_as_paid(db, uuid.UUID(params["invoice_id"]))
    return invoice.model_dump()


async def _invoice_credit_note(db: AsyncSession, params: dict) -> Any:
    from src.services.invoice_service import InvoiceService
    cn = await InvoiceService.create_credit_note(
        db, uuid.UUID(params["invoice_id"]),
        reason=params.get("reason", ""),
        amount=int(params.get("amount", 0)) if params.get("amount") else None,
    )
    return cn.model_dump()


async def _invoice_overdue(db: AsyncSession, params: dict) -> Any:
    from src.services.invoice_service import InvoiceService
    overdue_list = await InvoiceService.check_overdue(db)
    return [i.model_dump() for i in overdue_list]


# ── VAT ─────────────────────────────────────────────────────────────

async def _vat_preview_return(db: AsyncSession, params: dict) -> Any:
    from src.services.vat_service import VatService
    vat_return = await VatService.calculate_return(
        db,
        date.fromisoformat(params["start_date"]),
        date.fromisoformat(params["end_date"]),
    )
    return vat_return.model_dump()


async def _vat_transaction_detail(db: AsyncSession, params: dict) -> Any:
    from src.services.vat_service import VatService
    details = await VatService.get_return(db, uuid.UUID(params["vat_period_id"]))
    return details.model_dump()


async def _vat_adjustment(db: AsyncSession, params: dict) -> Any:
    from src.services.vat_service import VatService
    result = await VatService.add_adjustment(
        db, uuid.UUID(params["vat_period_id"]),
        amount=int(params["amount"]),
        reason=str(params["reason"]),
    )
    return result.model_dump()


async def _vat_audit_trail(db: AsyncSession, params: dict) -> Any:
    from src.services.vat_service import VatService
    limit = int(params.get("limit", 100))
    trail = await VatService.get_audit_trail(db, uuid.UUID(params["vat_period_id"]), limit=limit)
    return [t.model_dump() for t in trail]


# ── Business ───────────────────────────────────────────────────────

async def _business_set_profile(db: AsyncSession, params: dict) -> Any:
    from src.services.contact_service import ContactService
    from src.validators.contact import ContactCreate, ContactUpdate
    name = str(params.get("company_name", "My Business"))

    # First check if this business is already stored
    existing = await ContactService.find_or_create(db, name=name, email=None, vat_number=None)
    contact, is_new = existing

    if is_new:
        # Newly auto-created by find_or_create as type="supplier" — fix the type
        update = ContactUpdate(
            type="other",
            company=params.get("company_name"),
            address_line1=params.get("address_line1"),
            address_line2=params.get("address_line2"),
            city=params.get("city"),
            postcode=params.get("postcode"),
            country=params.get("country", "GB"),
        )
        updated = await ContactService.update_contact(db, contact.id, update)
        return updated.model_dump()
    else:
        # Already exists — update address if provided
        update_data = {}
        for field in ("address_line1", "address_line2", "city", "postcode", "country"):
            if params.get(field):
                update_data[field] = params[field]
        if params.get("company_name"):
            update_data["company"] = params["company_name"]
        if update_data:
            update = ContactUpdate(**update_data)
            updated = await ContactService.update_contact(db, contact.id, update)
            return updated.model_dump()
    return contact.model_dump()


# ── Memory ─────────────────────────────────────────────────────────

async def _memory_search(db: AsyncSession, params: dict) -> Any:
    import httpx, os
    katra_url = os.getenv("KATRA_MCP_URL", "http://accounting-katra-server:3113")
    admin_url = katra_url.replace("/mcp", "").replace(":3113", ":9013") + "/api/v1/memory/episodic/events"
    query = params.get("query", "")
    limit = int(params.get("limit", 5))
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{admin_url}?limit={limit}",
                headers={"Authorization": "Bearer katra-admin-key-2026"},
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", data.get("events", []))
            return {
                "found": len(results),
                "events": [
                    {"timestamp": e.get("timestamp",""), "content": e.get("content",""), "session_id": e.get("session_id","")}
                    for e in (results if isinstance(results, list) else [results])
                ],
            }
    except Exception as exc:
        return {"found": 0, "events": [], "error": str(exc)}


# ── Reports ─────────────────────────────────────────────────────────

async def _report_run(db: AsyncSession, params: dict) -> Any:
    from src.services.report_service import ReportService
    report = await ReportService.run(
        db,
        report_type=str(params["report_type"]),
        start_date=date.fromisoformat(params["start_date"]) if params.get("start_date") else None,
        end_date=date.fromisoformat(params["end_date"]) if params.get("end_date") else None,
        as_at_date=date.fromisoformat(params["as_at_date"]) if params.get("as_at_date") else None,
    )
    return report.model_dump()


async def _report_list(db: AsyncSession, params: dict) -> Any:
    from src.services.report_service import ReportService
    templates = await ReportService.list_templates(db)
    return [t.model_dump() for t in templates]


async def _report_schedule(db: AsyncSession, params: dict) -> Any:
    from src.services.report_service import ReportService
    schedule = await ReportService.create_schedule(
        db,
        report_type=str(params["report_type"]),
        frequency=str(params["frequency"]),
        email_to=params.get("email_to"),
    )
    return schedule.model_dump()


# ---------------------------------------------------------------------------
# Handler lookup table
# ---------------------------------------------------------------------------
_HANDLERS: dict[str, Any] = {
    "coa.list": _coa_list,
    "coa.add_account": _coa_add_account,
    "coa.edit_account": _coa_edit_account,
    "coa.load_template": _coa_load_template,
    "coa.detail": _coa_detail,
    "coa.set_vat_rate": _coa_set_vat_rate,
    "gl.record_expense": _gl_record_expense,
    "gl.record_income": _gl_record_income,
    "gl.record_transfer": _gl_record_transfer,
    "gl.journal_entry": _gl_journal_entry,
    "gl.list_transactions": _gl_list_transactions,
    "gl.transaction_detail": _gl_transaction_detail,
    "gl.undo_transaction": _gl_undo_transaction,
    "contact.create": _contact_create,
    "contact.edit": _contact_edit,
    "contact.list": _contact_list,
    "contact.detail": _contact_detail,
    "contact.archive": _contact_archive,
    "bank.import_csv": _bank_import_csv,
    "bank.import_ofx": _bank_import_ofx,
    "bank.list_accounts": _bank_list_accounts,
    "bank.add_account": _bank_add_account,
    "bank.transactions": _bank_transactions,
    "bank.categorize": _bank_categorize,
    "recon.start": _recon_start,
    "recon.match": _recon_match,
    "recon.create_and_match": _recon_create_and_match,
    "recon.status": _recon_status,
    "recon.report": _recon_report,
    "invoice.create": _invoice_create,
    "invoice.send": _invoice_send,
    "invoice.list": _invoice_list,
    "invoice.mark_paid": _invoice_mark_paid,
    "invoice.credit_note": _invoice_credit_note,
    "invoice.overdue": _invoice_overdue,
    "vat.preview_return": _vat_preview_return,
    "vat.transaction_detail": _vat_transaction_detail,
    "vat.adjustment": _vat_adjustment,
    "vat.audit_trail": _vat_audit_trail,
    "report.run": _report_run,
    "report.list": _report_list,
    "report.schedule": _report_schedule,
    "business.set_profile": _business_set_profile,
    "memory.search": _memory_search,
}
