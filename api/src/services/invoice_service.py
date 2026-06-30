"""Business logic for Invoicing — InvoiceService — Module 6."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.contact import Contact
from src.models.invoice import CreditNote, Invoice, InvoiceLine
from src.validators.invoice import (
    CreditNoteResponse,
    InvoiceCreate,
    InvoiceLineCreate,
    InvoiceListResponse,
    InvoiceResponse,
)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class InvoiceServiceError(Exception):
    """Base exception for invoice service errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class InvoiceNotFoundError(InvoiceServiceError):
    """Invoice not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Invoice '{identifier}' not found", status_code=404)


class InvoiceImmutableError(InvoiceServiceError):
    """Attempted to modify a sent invoice."""

    def __init__(self, invoice_id: uuid.UUID, status: str) -> None:
        super().__init__(
            f"Invoice {invoice_id} is already {status} and cannot be modified",
            status_code=422,
        )


class InvoiceLifecycleError(InvoiceServiceError):
    """Invalid status transition."""

    def __init__(self, invoice_id: uuid.UUID, current: str, target: str) -> None:
        super().__init__(
            f"Cannot transition invoice {invoice_id} from '{current}' to '{target}'",
            status_code=422,
        )


class ContactNotFoundError(InvoiceServiceError):
    """Contact not found."""

    def __init__(self, contact_id: uuid.UUID) -> None:
        super().__init__(f"Contact '{contact_id}' not found", status_code=404)


# ---------------------------------------------------------------------------
# VAT calculation
# ---------------------------------------------------------------------------

VAT_MULTIPLIERS: dict[str, float] = {
    "20%": 0.20,
    "5%": 0.05,
    "0%": 0.00,
    "exempt": 0.00,
}


def _calculate_vat(unit_price: int, quantity: int, vat_rate: str) -> tuple[int, int]:
    """Calculate vat_amount and line_total for a line item.

    Returns (vat_amount, line_total) both in pence.
    """
    net = unit_price * quantity
    multiplier = VAT_MULTIPLIERS.get(vat_rate, 0.0)

    if multiplier == 0.0:
        vat_amount = 0
    else:
        # Banker's rounding: use round()
        vat_amount = round(net * multiplier)

    line_total = net + vat_amount
    return vat_amount, line_total


# ---------------------------------------------------------------------------
# Response mapping
# ---------------------------------------------------------------------------

def _invoice_to_response(invoice: Invoice) -> InvoiceResponse:
    """Map an ORM Invoice to an InvoiceResponse."""
    return InvoiceResponse.model_validate(invoice)


def _credit_note_to_response(cn: CreditNote) -> CreditNoteResponse:
    """Map an ORM CreditNote to a CreditNoteResponse."""
    return CreditNoteResponse.model_validate(cn)


# ---------------------------------------------------------------------------
# InvoiceService
# ---------------------------------------------------------------------------


class InvoiceService:
    """Stateless service for invoice lifecycle, credit notes, and PDF generation."""

    # ------------------------------------------------------------------
    # Reference generation
    # ------------------------------------------------------------------

    @staticmethod
    async def _generate_inv_reference(db: AsyncSession, issue_date: date) -> str:
        """Generate the next INV-YYYY-NNNN reference for the given year."""
        year = issue_date.year
        prefix = f"INV-{year}-"

        # Count existing invoices with references for this year
        stmt = select(func.count()).where(
            Invoice.reference.like(f"INV-{year}-%")
        )
        result = await db.execute(stmt)
        count = result.scalar_one() + 1

        return f"{prefix}{count:04d}"

    @staticmethod
    async def _generate_cn_reference(db: AsyncSession) -> str:
        """Generate the next CN-YYYY-NNNN reference for the current year."""
        year = datetime.now(timezone.utc).year
        prefix = f"CN-{year}-"

        stmt = select(func.count()).where(
            CreditNote.reference.like(f"CN-{year}-%")
        )
        result = await db.execute(stmt)
        count = result.scalar_one() + 1

        return f"{prefix}{count:04d}"

    # ------------------------------------------------------------------
    # Create invoice (Draft)
    # ------------------------------------------------------------------

    @staticmethod
    async def create_invoice(
        db: AsyncSession,
        data: InvoiceCreate,
    ) -> InvoiceResponse:
        """Create a new invoice in Draft status with calculated totals.

        Raises ContactNotFoundError if contact_id does not exist.
        """
        # Validate contact exists
        contact = await db.get(Contact, data.contact_id)
        if contact is None:
            raise ContactNotFoundError(data.contact_id)

        # Calculate line totals
        lines_orm: list[InvoiceLine] = []
        subtotal = 0
        vat_total = 0

        for i, line_data in enumerate(data.lines):
            vat_amount, line_total = _calculate_vat(
                line_data.unit_price,
                line_data.quantity,
                line_data.vat_rate,
            )
            line = InvoiceLine(
                description=line_data.description,
                quantity=line_data.quantity,
                unit_price=line_data.unit_price,
                vat_rate=line_data.vat_rate,
                vat_amount=vat_amount,
                line_total=line_total,
                sort_order=i,
            )
            lines_orm.append(line)
            subtotal += line_data.unit_price * line_data.quantity
            vat_total += vat_amount

        total = subtotal + vat_total

        invoice = Invoice(
            contact_id=data.contact_id,
            status="draft",
            issue_date=data.issue_date,
            due_date=data.due_date,
            subtotal=subtotal,
            vat_total=vat_total,
            total=total,
            currency=data.currency,
            notes=data.notes,
            lines=lines_orm,
        )
        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)

        # Update contact AR balance
        await InvoiceService._update_contact_balance(db, data.contact_id)

        return _invoice_to_response(invoice)

    @staticmethod
    async def _post_invoice_to_gl(
        db: AsyncSession,
        invoice: Invoice,
    ) -> None:
        """Create the double-entry journal entries for a sent invoice.

        Debits Accounts Receivable (1100) for the gross amount, credits
        Sales (4000) for the net subtotal, and credits VAT Control (2100)
        for the VAT portion.  All amounts are in pence.
        """
        from src.validators.transaction import PostingCreate, TransactionCreate
        from src.services.transaction_service import TransactionService
        from src.services.coa_service import CoaService

        gross = invoice.subtotal + invoice.vat_total

        ar_acct = await CoaService.get_account_by_code(db, "1100")
        sales_acct = await CoaService.get_account_by_code(db, "4000")
        vat_acct = await CoaService.get_account_by_code(db, "2100")

        ref = invoice.reference or "INV"
        postings = [
            PostingCreate(
                account_id=ar_acct.id, debit_amount=gross, credit_amount=0,
                description=f"{ref} — Accounts Receivable",
            ),
            PostingCreate(
                account_id=sales_acct.id, debit_amount=0,
                credit_amount=invoice.subtotal,
                description=f"{ref} — Revenue",
            ),
        ]
        if invoice.vat_total > 0:
            postings.append(PostingCreate(
                account_id=vat_acct.id, debit_amount=0,
                credit_amount=invoice.vat_total,
                description=f"{ref} — VAT",
            ))

        tx = TransactionCreate(
            idempotency_key=uuid.uuid4(),
            description=f"Invoice {ref}",
            effective_date=invoice.issue_date,
            postings=postings,
        )
        created = await TransactionService.create_transaction(db, tx)
        await TransactionService.post_transaction(db, created.id)

    # ------------------------------------------------------------------
    # Send invoice (Draft → Sent)
    # ------------------------------------------------------------------

    @staticmethod
    async def send_invoice(
        db: AsyncSession,
        invoice_id: uuid.UUID,
    ) -> InvoiceResponse:
        """Send an invoice: Draft → Sent, set reference, enforce immutability.

        Raises:
            InvoiceNotFoundError if invoice does not exist.
            InvoiceLifecycleError if not in Draft status.
        """
        invoice = await db.get(
            Invoice,
            invoice_id,
            options=[selectinload(Invoice.lines)],
        )
        if invoice is None:
            raise InvoiceNotFoundError(str(invoice_id))

        if invoice.status != "draft":
            raise InvoiceLifecycleError(invoice_id, invoice.status, "sent")

        now = datetime.now(timezone.utc)
        invoice.status = "sent"
        invoice.sent_at = now
        invoice.updated_at = now

        # Generate reference if not already set
        if invoice.reference is None:
            invoice.reference = await InvoiceService._generate_inv_reference(
                db, invoice.issue_date
            )

        await db.commit()
        await db.refresh(invoice)

        # ── Post journal entries to the General Ledger ──────────────
        await InvoiceService._post_invoice_to_gl(db, invoice)

        return _invoice_to_response(invoice)

    # ------------------------------------------------------------------
    # Get invoice by ID
    # ------------------------------------------------------------------

    @staticmethod
    async def get_invoice(
        db: AsyncSession,
        invoice_id: uuid.UUID,
    ) -> Optional[InvoiceResponse]:
        """Return a single invoice with its lines, or None if not found."""
        invoice = await db.get(
            Invoice,
            invoice_id,
            options=[selectinload(Invoice.lines)],
        )
        if invoice is None:
            return None
        return _invoice_to_response(invoice)

    # ------------------------------------------------------------------
    # List invoices
    # ------------------------------------------------------------------

    @staticmethod
    async def list_invoices(
        db: AsyncSession,
        *,
        status: Optional[str] = None,
        contact_id: Optional[uuid.UUID] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[InvoiceResponse], int]:
        """List invoices with optional filters. Returns (items, total_count)."""
        stmt = select(Invoice).options(selectinload(Invoice.lines))

        if status:
            stmt = stmt.where(Invoice.status == status)
        if contact_id:
            stmt = stmt.where(Invoice.contact_id == contact_id)
        if date_from:
            stmt = stmt.where(Invoice.issue_date >= date_from)
        if date_to:
            stmt = stmt.where(Invoice.issue_date <= date_to)

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # Fetch
        stmt = stmt.order_by(Invoice.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        invoices = list(result.scalars().all())

        return [_invoice_to_response(i) for i in invoices], total

    # ------------------------------------------------------------------
    # Mark as viewed (Sent → Viewed)
    # ------------------------------------------------------------------

    @staticmethod
    async def mark_as_viewed(
        db: AsyncSession,
        invoice_id: uuid.UUID,
    ) -> InvoiceResponse:
        """Mark invoice as viewed by customer: Sent → Viewed.

        Raises:
            InvoiceNotFoundError if invoice does not exist.
            InvoiceLifecycleError if not in Sent status.
        """
        invoice = await db.get(
            Invoice,
            invoice_id,
            options=[selectinload(Invoice.lines)],
        )
        if invoice is None:
            raise InvoiceNotFoundError(str(invoice_id))

        if invoice.status != "sent":
            raise InvoiceLifecycleError(invoice_id, invoice.status, "viewed")

        invoice.status = "viewed"
        invoice.viewed_at = datetime.now(timezone.utc)
        invoice.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(invoice)

        return _invoice_to_response(invoice)

    # ------------------------------------------------------------------
    # Mark as paid (Sent/Viewed/Overdue → Paid)
    # ------------------------------------------------------------------

    @staticmethod
    async def mark_as_paid(
        db: AsyncSession,
        invoice_id: uuid.UUID,
    ) -> InvoiceResponse:
        """Mark invoice as paid: Sent/Viewed/Overdue → Paid.

        Raises:
            InvoiceNotFoundError if invoice does not exist.
            InvoiceLifecycleError if status cannot transition to paid.
        """
        invoice = await db.get(
            Invoice,
            invoice_id,
            options=[selectinload(Invoice.lines)],
        )
        if invoice is None:
            raise InvoiceNotFoundError(str(invoice_id))

        allowed = {"sent", "viewed", "overdue"}
        if invoice.status not in allowed:
            raise InvoiceLifecycleError(invoice_id, invoice.status, "paid")

        invoice.status = "paid"
        invoice.paid_at = datetime.now(timezone.utc)
        invoice.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(invoice)

        # Update contact AR balance
        await InvoiceService._update_contact_balance(db, invoice.contact_id)

        return _invoice_to_response(invoice)

    # ------------------------------------------------------------------
    # Cancel invoice (Draft → Cancelled)
    # ------------------------------------------------------------------

    @staticmethod
    async def cancel_invoice(
        db: AsyncSession,
        invoice_id: uuid.UUID,
    ) -> InvoiceResponse:
        """Cancel a draft invoice: Draft → Cancelled.

        Only draft invoices can be cancelled directly.
        Sent invoices require a credit note instead.

        Raises:
            InvoiceNotFoundError if invoice does not exist.
            InvoiceLifecycleError if not in Draft status.
        """
        invoice = await db.get(
            Invoice,
            invoice_id,
            options=[selectinload(Invoice.lines)],
        )
        if invoice is None:
            raise InvoiceNotFoundError(str(invoice_id))

        if invoice.status != "draft":
            raise InvoiceLifecycleError(invoice_id, invoice.status, "cancelled")

        invoice.status = "cancelled"
        invoice.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(invoice)

        return _invoice_to_response(invoice)

    # ------------------------------------------------------------------
    # Check overdue
    # ------------------------------------------------------------------

    @staticmethod
    async def check_overdue(
        db: AsyncSession,
    ) -> list[InvoiceResponse]:
        """Auto-detect and mark overdue invoices.

        Finds invoices where due_date < today and status is sent/viewed
        (not yet paid or cancelled), and transitions them to 'overdue'.
        Returns the list of newly overdue invoices.
        """
        today = date.today()

        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.lines))
            .where(
                Invoice.due_date < today,
                Invoice.status.in_(["sent", "viewed"]),
            )
        )
        result = await db.execute(stmt)
        overdue = list(result.scalars().all())

        now = datetime.now(timezone.utc)
        for invoice in overdue:
            invoice.status = "overdue"
            invoice.updated_at = now

        if overdue:
            await db.commit()

        return [_invoice_to_response(i) for i in overdue]

    # ------------------------------------------------------------------
    # Create credit note
    # ------------------------------------------------------------------

    @staticmethod
    async def create_credit_note(
        db: AsyncSession,
        invoice_id: uuid.UUID,
        reason: Optional[str] = None,
        lines: Optional[list[InvoiceLineCreate]] = None,
    ) -> CreditNoteResponse:
        """Create a credit note for an invoice and mark the original as cancelled.

        The credit note total is the negative of the original invoice total
        (or calculated from provided lines). Only sent/viewed/paid/overdue
        invoices can be credited (not draft or already cancelled).

        Raises:
            InvoiceNotFoundError if invoice does not exist.
            InvoiceLifecycleError if invoice cannot be credited.
        """
        invoice = await db.get(
            Invoice,
            invoice_id,
            options=[selectinload(Invoice.lines)],
        )
        if invoice is None:
            raise InvoiceNotFoundError(str(invoice_id))

        if invoice.status in ("draft", "cancelled"):
            raise InvoiceLifecycleError(
                invoice_id, invoice.status, "credit-credited"
            )

        # Calculate credit note total (negative)
        if lines:
            # Compute from provided lines (all negative)
            cn_total = 0
            for line_data in lines:
                _, line_total = _calculate_vat(
                    line_data.unit_price,
                    line_data.quantity,
                    line_data.vat_rate,
                )
                cn_total -= line_total
        else:
            # Default: full reversal of original invoice total
            cn_total = -invoice.total

        reference = await InvoiceService._generate_cn_reference(db)

        credit_note = CreditNote(
            invoice_id=invoice_id,
            reference=reference,
            contact_id=invoice.contact_id,
            total=cn_total,
            reason=reason,
        )
        db.add(credit_note)

        # Mark original invoice as cancelled
        invoice.status = "cancelled"
        invoice.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(credit_note)

        # Update contact AR balance
        await InvoiceService._update_contact_balance(db, invoice.contact_id)

        return _credit_note_to_response(credit_note)

    # ------------------------------------------------------------------
    # Generate PDF
    # ------------------------------------------------------------------

    @staticmethod
    async def generate_pdf(db: AsyncSession, invoice_id: uuid.UUID) -> bytes:
        """Generate a PDF for an invoice using Jinja2 + WeasyPrint.

        Returns the PDF as bytes. Assumes the template exists at
        src/templates/invoice_template.html relative to the api package.

        Raises:
            InvoiceNotFoundError if invoice does not exist.
        """
        from pathlib import Path

        from jinja2 import Environment, FileSystemLoader

        invoice = await db.get(
            Invoice,
            invoice_id,
            options=[selectinload(Invoice.lines), selectinload(Invoice.contact)],
        )
        if invoice is None:
            raise InvoiceNotFoundError(str(invoice_id))

        # Find the templates directory
        templates_dir = Path(__file__).resolve().parent.parent / "templates"
        env = Environment(loader=FileSystemLoader(str(templates_dir)))
        template = env.get_template("invoice_template.html")

        # Convert monetary amounts for display
        def pence_to_pounds(pence: int) -> str:
            return f"{pence / 100:.2f}"

        # Build context
        context = {
            "invoice": invoice,
            "pence_to_pounds": pence_to_pounds,
            "now": datetime.now(timezone.utc),
        }

        html = template.render(**context)

        # Generate PDF
        from weasyprint import HTML

        pdf_bytes = HTML(string=html).write_pdf()
        return pdf_bytes

    # ------------------------------------------------------------------
    # Contact balance helper
    # ------------------------------------------------------------------

    @staticmethod
    async def _update_contact_balance(
        db: AsyncSession, contact_id: uuid.UUID
    ) -> None:
        """Recalculate and update contact AR/AP balances from invoices."""
        contact = await db.get(Contact, contact_id)
        if contact is None:
            return

        # Sum total from all non-draft, non-cancelled invoices
        stmt_invoiced = select(func.coalesce(func.sum(Invoice.total), 0)).where(
            Invoice.contact_id == contact_id,
            Invoice.status.notin_(["draft", "cancelled"]),
        )
        result = await db.execute(stmt_invoiced)
        total_invoiced = result.scalar_one()

        # Sum total from all paid invoices
        stmt_paid = select(func.coalesce(func.sum(Invoice.total), 0)).where(
            Invoice.contact_id == contact_id,
            Invoice.status == "paid",
        )
        result = await db.execute(stmt_paid)
        total_paid = result.scalar_one()

        # Subtract credit notes
        stmt_cn = select(func.coalesce(func.sum(CreditNote.total), 0)).where(
            CreditNote.contact_id == contact_id,
        )
        result = await db.execute(stmt_cn)
        cn_total = result.scalar_one()  # negative or 0

        contact.total_invoiced = total_invoiced + cn_total
        contact.total_paid = total_paid
        contact.total_owing = total_invoiced - total_paid + cn_total

        contact.updated_at = datetime.now(timezone.utc)
        await db.commit()
