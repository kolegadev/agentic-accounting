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

from src.services.instrument import log_event

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
        "coa.list", "coa.add_account", "coa.edit_account", "coa.delete_account",
        "coa.set_vat_rate",
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
        "report.trial_balance",
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
            # ── I6: tool execution path ──────────────────────────────
            log_event(
                module="tool_executor", function="execute", event="entry",
                state_snapshot={
                    "skill_id": skill_id,
                    "params_keys": list(params.keys()) if params else [],
                    "handler_exists": handler is not None,
                    "via_mcp_gateway": False,
                },
            )
            result = await handler(db, params)
            log_event(
                module="tool_executor", function="execute", event="exit",
                state_snapshot={
                    "skill_id": skill_id,
                    "success": True,
                },
            )
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
    """Edit an account — accepts either account_id (UUID) or code (string)."""
    from src.services.coa_service import CoaService
    from src.validators.account import AccountUpdate
    from src.models.account import Account
    from sqlalchemy import select

    # Resolve account by code if account_id not provided
    account_id = params.get("account_id")
    if not account_id and "code" in params:
        code = str(params["code"])
        stmt = select(Account).where(Account.code == code)
        result = await db.execute(stmt)
        acct = result.scalar_one_or_none()
        if acct is None:
            return {"edited": False, "reason": f"No account with code {code}"}
        account_id = str(acct.id)
    if not account_id:
        return {"edited": False, "reason": "Provide account_id (UUID) or code"}

    update_fields = {k: v for k, v in params.items()
                     if k not in ("account_id", "code") and v is not None}
    data = AccountUpdate(**update_fields)
    account = await CoaService.update_account(db, uuid.UUID(account_id), data)
    return account.model_dump()


async def _coa_delete_account(db: AsyncSession, params: dict) -> Any:
    """Soft-delete an account by code — only allowed for accounts with no transactions."""
    from src.services.coa_service import CoaService
    from src.models.account import Account
    from src.models.transaction import Posting
    from sqlalchemy import select, func

    code = str(params["code"])
    stmt = select(Account).where(Account.code == code)
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()
    if account is None:
        return {"deleted": False, "reason": f"No account with code {code}"}

    # Guard: refuse deletion if any postings reference this account
    tx_count = await db.scalar(
        select(func.count()).where(Posting.account_id == account.id)
    )
    if tx_count and tx_count > 0:
        return {
            "deleted": False,
            "reason": (
                f"Account {code} ({account.name}) has {tx_count} "
                f"posting(s).  To preserve immutable provenance, this "
                f"account cannot be deleted.  Use coa.edit_account to rename "
                f"it or mark it inactive instead."
            ),
            "posting_count": tx_count,
        }

    deleted = await CoaService.soft_delete_account(db, account.id)
    return {"deleted": True, "code": code, "name": deleted.name}


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
    postings = []
    for p in postings_data:
        # Resolve account — accept UUID or code
        acct_id = p.get("account_id")
        if acct_id and len(str(acct_id)) < 32:  # looks like a code, not UUID
            from src.services.coa_service import CoaService
            acct = await CoaService.get_account_by_code(db, str(acct_id))
            if acct:
                acct_id = str(acct.id)
            else:
                return {"success": False, "error": f"Account code {acct_id} not found"}

        amount = int(p.get("amount", 0) or 0)
        side = str(p.get("side", "")).lower()

        if side == "credit":
            debit_amt, credit_amt = 0, amount
        elif side == "debit":
            debit_amt, credit_amt = amount, 0
        else:
            # Explicit debit_amount / credit_amount (no side field)
            debit_amt = int(p.get("debit_amount", 0) or 0)
            credit_amt = int(p.get("credit_amount", 0) or 0)
            # If only amount given without side, treat as debit
            if not debit_amt and not credit_amt and amount:
                debit_amt = amount

        postings.append(PostingCreate(
            account_id=uuid.UUID(acct_id),
            debit_amount=debit_amt,
            credit_amount=credit_amt,
            description=p.get("description", ""),
        ))
    tx_data = TransactionCreate(
        idempotency_key=uuid.uuid4(),
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
    from src.services.formatting import render_table, format_pence

    tx_id = params.get("transaction_id") or params.get("ref")
    tx = None
    if tx_id:
        # Try UUID first
        try:
            tx = await TransactionService.get_transaction(db, uuid.UUID(str(tx_id)))
        except (ValueError, TypeError):
            pass
        # Fallback: look up by reference string
        if tx is None:
            from src.models.transaction import Transaction
            from sqlalchemy import select
            stmt = select(Transaction).where(Transaction.reference == str(tx_id))
            result = await db.execute(stmt)
            tx = result.scalar_one_or_none()
    if tx is None:
        raise TransactionNotFoundError(str(tx_id))
    d = TransactionService._transaction_to_response(tx).model_dump()
    postings = d.get("postings", [])
    if not postings:
        return {"reference": d.get("reference"), "description": d.get("description"),
                "postings": [], "message": "No postings found"}

    rows = []
    for p in postings:
        pd = dict(p)
        pd["debit_fmt"] = format_pence(pd.get("debit_amount", 0)) if pd.get("debit_amount") else ""
        pd["credit_fmt"] = format_pence(pd.get("credit_amount", 0)) if pd.get("credit_amount") else ""
        rows.append(pd)

    return render_table(
        rows,
        columns=[
            ("account_code", "Code"),
            ("account_name", "Account"),
            ("debit_fmt", "Debit (£)"),
            ("credit_fmt", "Credit (£)"),
            ("description", "Description"),
        ],
    )


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
    from src.validators.invoice import InvoiceCreate, InvoiceLineCreate
    from src.models.contact import Contact
    from sqlalchemy import select
    from datetime import date, timedelta

    # Resolve contact by name or ID
    contact_id = params.get("contact_id")
    if not contact_id or len(str(contact_id)) < 32:
        contact_name = params.get("contact_name", str(contact_id or ""))
        stmt = select(Contact).where(Contact.name.ilike(f"%{contact_name}%"))
        result = await db.execute(stmt)
        contact = result.scalar_one_or_none()
        if contact:
            contact_id = str(contact.id)
        else:
            return {"success": False, "error": f"Contact '{contact_name}' not found"}

    today = date.today()
    lines_data = params.get("lines", [])
    data = InvoiceCreate(
        contact_id=uuid.UUID(str(contact_id)),
        issue_date=date.fromisoformat(params["issue_date"]) if params.get("issue_date") else today,
        due_date=date.fromisoformat(params["due_date"]) if params.get("due_date") else (today + timedelta(days=30)),
        lines=[InvoiceLineCreate(
            description=l.get("description", "Services"),
            quantity=int(l.get("quantity", 1)),
            unit_price=int(l.get("unit_price", 0)),
            vat_rate=l.get("vat_rate", "20%"),
        ) for l in lines_data] if lines_data else [
            InvoiceLineCreate(
                description="Services",
                quantity=1,
                unit_price=0,
                vat_rate="20%",
            )
        ],
        notes=params.get("notes"),
    )
    invoice = await InvoiceService.create_invoice(db, data)
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

async def _report_trial_balance(db: AsyncSession, params: dict) -> Any:
    from src.services.coa_service import CoaService
    from src.services.formatting import render_table, format_pence
    from sqlalchemy import select, func
    from src.models.transaction import Posting
    accounts = await CoaService.list_accounts(db)
    rows = []
    total_debits = 0
    total_credits = 0
    for acct in accounts:
        # Sum debits and credits for this account
        debit_result = await db.execute(
            select(func.coalesce(func.sum(Posting.debit_amount), 0))
            .where(Posting.account_id == acct.id)
        )
        credit_result = await db.execute(
            select(func.coalesce(func.sum(Posting.credit_amount), 0))
            .where(Posting.account_id == acct.id)
        )
        debits = debit_result.scalar() or 0
        credits = credit_result.scalar() or 0
        net = debits - credits
        total_debits += max(net, 0)
        total_credits += max(-net, 0) if net < 0 else 0
        rows.append({
            "code": acct.code,
            "name": acct.name,
            "category": acct.category,
            "debit": format_pence(net) if net > 0 else "",
            "credit": format_pence(abs(net)) if net < 0 else "",
        })
    # Add totals row
    rows.append({
        "code": "", "name": "**TOTALS**", "category": "",
        "debit": format_pence(total_debits), "credit": format_pence(total_credits),
    })
    return render_table(
        rows,
        columns=[
            ("code", "Code"),
            ("name", "Account"),
            ("category", "Category"),
            ("debit", "Debit (£)"),
            ("credit", "Credit (£)"),
        ],
    )


async def _direct_pl(db: AsyncSession, start_date: date, end_date: date) -> dict:
    """Direct Profit & Loss with proper section headers and subtotals."""
    from src.services.coa_service import CoaService
    from src.services.formatting import render_table, format_pence
    from sqlalchemy import select, func
    from src.models.transaction import Posting, Transaction
    accounts = await CoaService.list_accounts(db)
    income_rows = [{"section": "", "account": "**REVENUE**", "amount": ""}]
    expense_rows = [{"section": "", "account": "**EXPENSES**", "amount": ""}]
    revenue_total = 0
    expense_total = 0
    for acct in accounts:
        if acct.category not in ("Revenue", "Expense"):
            continue
        debit_q = select(func.coalesce(func.sum(Posting.debit_amount), 0)).where(
            Posting.account_id == acct.id,
            Posting.transaction_id.in_(
                select(Transaction.id).where(Transaction.effective_date.between(start_date, end_date))
            )
        )
        credit_q = select(func.coalesce(func.sum(Posting.credit_amount), 0)).where(
            Posting.account_id == acct.id,
            Posting.transaction_id.in_(
                select(Transaction.id).where(Transaction.effective_date.between(start_date, end_date))
            )
        )
        debits = (await db.execute(debit_q)).scalar() or 0
        credits = (await db.execute(credit_q)).scalar() or 0
        if acct.category == "Revenue":
            net = credits - debits
            revenue_total += net
            income_rows.append({"section": "", "account": "  " + acct.name, "amount": format_pence(net) if net else "£0.00"})
        elif acct.category == "Expense":
            net = debits - credits
            expense_total += net
            expense_rows.append({"section": "", "account": "  " + acct.name, "amount": format_pence(net) if net else "£0.00"})
    income_rows.append({"section": "", "account": "**Total Revenue**", "amount": format_pence(revenue_total)})
    expense_rows.append({"section": "", "account": "**Total Expenses**", "amount": format_pence(expense_total)})
    net_profit = revenue_total - expense_total
    rows = income_rows + expense_rows + [
        {"section": "", "account": "", "amount": ""},
        {"section": "", "account": "**NET PROFIT / (LOSS)**", "amount": format_pence(net_profit)},
    ]
    return render_table(rows, [("account", "Account"), ("amount", "Amount (£)")])


async def _direct_bs(db: AsyncSession, as_at: date) -> dict:
    """Direct Balance Sheet with proper section headers and subtotals."""
    from src.services.coa_service import CoaService
    from src.services.formatting import render_table, format_pence
    from sqlalchemy import select, func
    from src.models.transaction import Posting, Transaction
    accounts = await CoaService.list_accounts(db)
    rows = []
    for cat, label in [("Asset", "ASSETS"), ("Liability", "LIABILITIES"), ("Equity", "EQUITY")]:
        rows.append({"account": f"**{label}**", "amount": ""})
        cat_total = 0
        for acct in accounts:
            if acct.category != cat:
                continue
            debit_q = select(func.coalesce(func.sum(Posting.debit_amount), 0)).where(
                Posting.account_id == acct.id,
                Posting.transaction_id.in_(
                    select(Transaction.id).where(Transaction.effective_date <= as_at)
                )
            )
            credit_q = select(func.coalesce(func.sum(Posting.credit_amount), 0)).where(
                Posting.account_id == acct.id,
                Posting.transaction_id.in_(
                    select(Transaction.id).where(Transaction.effective_date <= as_at)
                )
            )
            debits = (await db.execute(debit_q)).scalar() or 0
            credits = (await db.execute(credit_q)).scalar() or 0
            if cat == "Asset":
                balance = debits - credits
            else:
                balance = credits - debits
            cat_total += balance
            rows.append({"account": "  " + acct.name, "amount": format_pence(balance)})
        rows.append({"account": f"**Total {label.title()}**", "amount": format_pence(cat_total)})
        rows.append({"account": "", "amount": ""})
    return render_table(rows, [("account", "Account"), ("amount", "Amount (£)")])


async def _direct_aging(db: AsyncSession, report_type: str, as_at: date) -> dict:
    """Direct Aged Receivables or Payables report."""
    from src.services.formatting import render_table, format_pence
    from src.services.contact_service import ContactService
    contacts, _ = await ContactService.list_contacts(db)
    rows = []
    for c in contacts:
        owing = c.total_invoiced - c.total_paid
        if report_type == "aged_receivables" and owing > 0 and c.type in ("customer", "both", "other"):
            rows.append({"name": c.name, "type": c.type, "owing": format_pence(owing)})
        elif report_type == "aged_payables" and owing < 0 and c.type in ("supplier", "both", "other"):
            rows.append({"name": c.name, "type": c.type, "owing": format_pence(abs(owing))})
    return render_table(rows, [("name", "Contact"), ("type", "Type"), ("owing", "Outstanding (£)")])


async def _report_run(db: AsyncSession, params: dict) -> Any:
    """Route to the correct report handler based on report_type."""
    report_type = str(params.get("report_type", "profit_and_loss"))
    start_date = date.fromisoformat(params["start_date"]) if params.get("start_date") else date.today().replace(month=1, day=1)
    end_date = date.fromisoformat(params["end_date"]) if params.get("end_date") else date.today()
    as_at = date.fromisoformat(params["as_at_date"]) if params.get("as_at_date") else end_date

    if report_type == "profit_and_loss":
        return await _direct_pl(db, start_date, end_date)
    elif report_type == "balance_sheet":
        return await _direct_bs(db, as_at)
    elif report_type == "trial_balance":
        return await _report_trial_balance(db, {})
    elif report_type in ("aged_receivables", "aged_payables"):
        return await _direct_aging(db, report_type, as_at)
    else:
        return {"error": f"Unknown report type: {report_type}"}


async def _report_list(db: AsyncSession, params: dict) -> Any:
    return {
        "reports": [
            {"name": "Profit & Loss", "type": "profit_and_loss", "description": "Revenue minus expenses over a date range"},
            {"name": "Balance Sheet", "type": "balance_sheet", "description": "Assets, liabilities, and equity as at a date"},
            {"name": "Trial Balance", "type": "trial_balance", "description": "All accounts with debit and credit balances"},
            {"name": "Aged Receivables", "type": "aged_receivables", "description": "Outstanding customer invoices by age"},
            {"name": "Aged Payables", "type": "aged_payables", "description": "Outstanding supplier bills by age"},
        ],
        "usage": "Use report.run with the report_type field to generate any of these reports."
    }


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
    "coa.delete_account": _coa_delete_account,
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
    "report.trial_balance": _report_trial_balance,
    "report.run": _report_run,
    "report.list": _report_list,
    "report.schedule": _report_schedule,
    "business.set_profile": _business_set_profile,
    "memory.search": _memory_search,
}
