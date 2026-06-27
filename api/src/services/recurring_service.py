"""Business logic for Recurring Templates — RecurringService — Module 7."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from datetime import timedelta
from typing import Optional

from dateutil.relativedelta import relativedelta
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.account import Account
from src.models.contact import Contact
from src.models.invoice import Invoice, InvoiceLine
from src.models.recurring import (
    RecurringInvoice,
    RecurringTemplate,
    RecurringTransaction,
)
from src.models.transaction import Posting, Transaction
from src.validators.recurring import (
    RecurringTemplateCreate,
    RecurringTemplateListResponse,
    RecurringTemplateResponse,
)

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class RecurringServiceError(Exception):
    """Base exception for recurring service errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class TemplateNotFoundError(RecurringServiceError):
    """Template not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Recurring template '{identifier}' not found", status_code=404)


class AccountNotFoundError(RecurringServiceError):
    """Account not found."""

    def __init__(self, account_id: uuid.UUID) -> None:
        super().__init__(f"Account '{account_id}' not found or inactive", status_code=404)


class ContactNotFoundError(RecurringServiceError):
    """Contact not found."""

    def __init__(self, contact_id: uuid.UUID) -> None:
        super().__init__(f"Contact '{contact_id}' not found", status_code=404)


class TemplateNotActiveError(RecurringServiceError):
    """Operation attempted on inactive template."""

    def __init__(self, template_id: uuid.UUID) -> None:
        super().__init__(
            f"Template '{template_id}' is not active", status_code=422
        )


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
        vat_amount = round(net * multiplier)
    line_total = net + vat_amount
    return vat_amount, line_total


# ---------------------------------------------------------------------------
# Frequency → date arithmetic
# ---------------------------------------------------------------------------

_FREQUENCY_MAP: dict[str, str] = {
    "daily": "days",
    "weekly": "weeks",
    "bi_weekly": "weeks",
    "monthly": "months",
    "quarterly": "months",
    "annual": "years",
}

_FREQUENCY_MULTIPLIER: dict[str, int] = {
    "daily": 1,
    "weekly": 1,
    "bi_weekly": 2,
    "monthly": 1,
    "quarterly": 3,
    "annual": 1,
}


def _calculate_next_date(current_date: date, frequency: str) -> date:
    """Calculate the next recurrence date based on frequency."""
    if frequency == "daily":
        return current_date + timedelta(days=1)
    elif frequency == "weekly":
        return current_date + timedelta(days=7)
    elif frequency == "bi_weekly":
        return current_date + timedelta(days=14)
    else:
        # Use relativedelta for month/year-based frequencies
        if frequency == "monthly":
            return current_date + relativedelta(months=1)
        elif frequency == "quarterly":
            return current_date + relativedelta(months=3)
        elif frequency == "annual":
            return current_date + relativedelta(years=1)
        else:
            raise ValueError(f"Unknown frequency: {frequency}")


# ---------------------------------------------------------------------------
# Response mapping
# ---------------------------------------------------------------------------


def _template_to_response(template: RecurringTemplate) -> RecurringTemplateResponse:
    """Map an ORM RecurringTemplate to a RecurringTemplateResponse."""
    data: dict = {
        "id": template.id,
        "name": template.name,
        "template_type": template.template_type,
        "frequency": template.frequency,
        "next_run_date": template.next_run_date,
        "end_type": template.end_type,
        "end_after_count": template.end_after_count,
        "end_until_date": template.end_until_date,
        "is_active": template.is_active,
        "last_run_date": template.last_run_date,
        "run_count": template.run_count,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }

    if template.recurring_transaction:
        rt = template.recurring_transaction
        data["transaction_detail"] = {
            "id": rt.id,
            "template_id": rt.template_id,
            "description": rt.description,
            "debit_account_id": rt.debit_account_id,
            "credit_account_id": rt.credit_account_id,
            "amount_pence": rt.amount_pence,
            "vat_rate": rt.vat_rate,
            "contact_id": rt.contact_id,
        }

    if template.recurring_invoice:
        ri = template.recurring_invoice
        data["invoice_detail"] = {
            "id": ri.id,
            "template_id": ri.template_id,
            "contact_id": ri.contact_id,
            "items": ri.items,
            "payment_terms": ri.payment_terms,
            "notes": ri.notes,
        }

    return RecurringTemplateResponse.model_validate(data)


# ---------------------------------------------------------------------------
# RecurringService
# ---------------------------------------------------------------------------


class RecurringService:
    """Stateless service for managing recurring templates and processing."""

    # ------------------------------------------------------------------
    # Create template
    # ------------------------------------------------------------------

    @staticmethod
    async def create_template(
        db: AsyncSession,
        data: RecurringTemplateCreate,
    ) -> RecurringTemplateResponse:
        """Create a new recurring template with its detail record.

        Validates referenced accounts and contacts exist and are active.
        """
        # ---- Validate detail references ----
        if data.template_type == "transaction" and data.transaction_detail:
            detail = data.transaction_detail
            await RecurringService._validate_account(
                db, detail.debit_account_id
            )
            await RecurringService._validate_account(
                db, detail.credit_account_id
            )
            if detail.contact_id:
                await RecurringService._validate_contact(db, detail.contact_id)

        if data.template_type == "invoice" and data.invoice_detail:
            detail = data.invoice_detail
            await RecurringService._validate_contact(db, detail.contact_id)

        # ---- Create template ----
        template = RecurringTemplate(
            name=data.name,
            template_type=data.template_type,
            frequency=data.frequency,
            next_run_date=data.next_run_date,
            end_type=data.end_type,
            end_after_count=data.end_after_count,
            end_until_date=data.end_until_date,
            is_active=data.is_active,
        )
        db.add(template)
        await db.flush()  # Get template.id

        # ---- Create detail record ----
        if data.template_type == "transaction" and data.transaction_detail:
            detail = data.transaction_detail
            rt = RecurringTransaction(
                template_id=template.id,
                description=detail.description,
                debit_account_id=detail.debit_account_id,
                credit_account_id=detail.credit_account_id,
                amount_pence=detail.amount_pence,
                vat_rate=detail.vat_rate,
                contact_id=detail.contact_id,
            )
            db.add(rt)

        if data.template_type == "invoice" and data.invoice_detail:
            detail = data.invoice_detail
            items_json = [item.model_dump() for item in detail.items]
            ri = RecurringInvoice(
                template_id=template.id,
                contact_id=detail.contact_id,
                items=items_json,
                payment_terms=detail.payment_terms,
                notes=detail.notes,
            )
            db.add(ri)

        await db.commit()
        await db.refresh(template, attribute_names=["recurring_transaction", "recurring_invoice"])

        return _template_to_response(template)

    # ------------------------------------------------------------------
    # Process due templates
    # ------------------------------------------------------------------

    @staticmethod
    async def process_due_templates(db: AsyncSession) -> int:
        """Process all active templates whose next_run_date <= today.

        For each due template:
          1. Create the transaction or invoice
          2. Update next_run_date based on frequency
          3. Update run_count and last_run_date
          4. Handle end conditions (deactivate if expired)

        Returns the number of templates processed.
        """
        today = date.today()

        # ---- Find all active, due templates ----
        stmt = (
            select(RecurringTemplate)
            .where(
                RecurringTemplate.is_active == True,  # noqa: E712
                RecurringTemplate.next_run_date <= today,
            )
            .options(
                selectinload(RecurringTemplate.recurring_transaction),
                selectinload(RecurringTemplate.recurring_invoice),
            )
            .order_by(RecurringTemplate.next_run_date)
        )
        result = await db.execute(stmt)
        templates = list(result.scalars().all())

        processed = 0

        for template in templates:
            try:
                # ---- Create the transaction or invoice ----
                if template.template_type == "transaction" and template.recurring_transaction:
                    await RecurringService._create_transaction_from_template(
                        db, template, template.recurring_transaction
                    )
                elif template.template_type == "invoice" and template.recurring_invoice:
                    await RecurringService._create_invoice_from_template(
                        db, template, template.recurring_invoice
                    )

                # ---- Update template state ----
                template.last_run_date = template.next_run_date
                template.run_count += 1

                # ---- Check end conditions ----
                should_deactivate = False

                if template.end_type == "after_count" and template.end_after_count:
                    if template.run_count >= template.end_after_count:
                        should_deactivate = True

                if template.end_type == "until_date" and template.end_until_date:
                    # Calculate the next date; if it exceeds the end date, stop
                    next_date = _calculate_next_date(template.next_run_date, template.frequency)
                    if next_date > template.end_until_date:
                        should_deactivate = True

                # ---- Advance next_run_date ----
                if not should_deactivate:
                    template.next_run_date = _calculate_next_date(
                        template.next_run_date, template.frequency
                    )
                else:
                    template.is_active = False
                    # Set next_run_date to None so it won't be picked up again
                    template.next_run_date = date(2099, 12, 31)

                template.updated_at = datetime.now(timezone.utc)

                processed += 1

            except Exception:
                # Log and skip on failure — don't block other templates
                template.updated_at = datetime.now(timezone.utc)
                continue

        if processed > 0:
            await db.commit()

        return processed

    # ------------------------------------------------------------------
    # Skip next occurrence
    # ------------------------------------------------------------------

    @staticmethod
    async def skip_next(
        db: AsyncSession,
        template_id: uuid.UUID,
    ) -> RecurringTemplateResponse:
        """Skip one occurrence: advance next_run_date without creating.

        Raises TemplateNotFoundError if template not found.
        """
        template = await db.get(
            RecurringTemplate,
            template_id,
            options=[
                selectinload(RecurringTemplate.recurring_transaction),
                selectinload(RecurringTemplate.recurring_invoice),
            ],
        )
        if template is None:
            raise TemplateNotFoundError(str(template_id))

        if not template.is_active:
            raise TemplateNotActiveError(template_id)

        template.next_run_date = _calculate_next_date(
            template.next_run_date, template.frequency
        )
        template.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(template)

        return _template_to_response(template)

    # ------------------------------------------------------------------
    # Pause template
    # ------------------------------------------------------------------

    @staticmethod
    async def pause_template(
        db: AsyncSession,
        template_id: uuid.UUID,
    ) -> RecurringTemplateResponse:
        """Pause a template (set is_active=False).

        Raises TemplateNotFoundError if not found.
        """
        template = await db.get(
            RecurringTemplate,
            template_id,
            options=[
                selectinload(RecurringTemplate.recurring_transaction),
                selectinload(RecurringTemplate.recurring_invoice),
            ],
        )
        if template is None:
            raise TemplateNotFoundError(str(template_id))

        template.is_active = False
        template.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(template)

        return _template_to_response(template)

    # ------------------------------------------------------------------
    # Resume template
    # ------------------------------------------------------------------

    @staticmethod
    async def resume_template(
        db: AsyncSession,
        template_id: uuid.UUID,
    ) -> RecurringTemplateResponse:
        """Resume a paused template (set is_active=True).

        If next_run_date is in the past, set it to today.
        Raises TemplateNotFoundError if not found.
        """
        template = await db.get(
            RecurringTemplate,
            template_id,
            options=[
                selectinload(RecurringTemplate.recurring_transaction),
                selectinload(RecurringTemplate.recurring_invoice),
            ],
        )
        if template is None:
            raise TemplateNotFoundError(str(template_id))

        template.is_active = True
        # If the next run date is in the past, bring it forward to today
        today = date.today()
        if template.next_run_date < today:
            template.next_run_date = today

        template.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(template)

        return _template_to_response(template)

    # ------------------------------------------------------------------
    # Delete template
    # ------------------------------------------------------------------

    @staticmethod
    async def delete_template(
        db: AsyncSession,
        template_id: uuid.UUID,
    ) -> None:
        """Delete a template and its detail record (cascade).

        Raises TemplateNotFoundError if not found.
        """
        template = await db.get(RecurringTemplate, template_id)
        if template is None:
            raise TemplateNotFoundError(str(template_id))

        await db.delete(template)
        await db.commit()

    # ------------------------------------------------------------------
    # Get template by ID
    # ------------------------------------------------------------------

    @staticmethod
    async def get_template(
        db: AsyncSession,
        template_id: uuid.UUID,
    ) -> Optional[RecurringTemplateResponse]:
        """Get a single template with its detail."""
        template = await db.get(
            RecurringTemplate,
            template_id,
            options=[
                selectinload(RecurringTemplate.recurring_transaction),
                selectinload(RecurringTemplate.recurring_invoice),
            ],
        )
        if template is None:
            return None
        return _template_to_response(template)

    # ------------------------------------------------------------------
    # List templates
    # ------------------------------------------------------------------

    @staticmethod
    async def list_templates(
        db: AsyncSession,
        *,
        template_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[RecurringTemplateResponse], int]:
        """List templates with optional filters. Returns (items, total_count)."""
        stmt = select(RecurringTemplate).options(
            selectinload(RecurringTemplate.recurring_transaction),
            selectinload(RecurringTemplate.recurring_invoice),
        )

        if template_type:
            stmt = stmt.where(RecurringTemplate.template_type == template_type)
        if is_active is not None:
            stmt = stmt.where(RecurringTemplate.is_active == is_active)

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # Fetch
        stmt = stmt.order_by(RecurringTemplate.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        templates = list(result.scalars().all())

        return [_template_to_response(t) for t in templates], total

    # ------------------------------------------------------------------
    # Update template
    # ------------------------------------------------------------------

    @staticmethod
    async def update_template(
        db: AsyncSession,
        template_id: uuid.UUID,
        data: RecurringTemplateCreate,
    ) -> RecurringTemplateResponse:
        """Update a template and its detail record.

        Raises TemplateNotFoundError if not found.
        """
        template = await db.get(
            RecurringTemplate,
            template_id,
            options=[
                selectinload(RecurringTemplate.recurring_transaction),
                selectinload(RecurringTemplate.recurring_invoice),
            ],
        )
        if template is None:
            raise TemplateNotFoundError(str(template_id))

        # Update template fields
        template.name = data.name
        template.template_type = data.template_type
        template.frequency = data.frequency
        template.next_run_date = data.next_run_date
        template.end_type = data.end_type
        template.end_after_count = data.end_after_count
        template.end_until_date = data.end_until_date
        template.is_active = data.is_active
        template.updated_at = datetime.now(timezone.utc)

        # Update transaction detail
        if data.template_type == "transaction" and data.transaction_detail:
            detail = data.transaction_detail
            if template.recurring_transaction:
                rt = template.recurring_transaction
                rt.description = detail.description
                rt.debit_account_id = detail.debit_account_id
                rt.credit_account_id = detail.credit_account_id
                rt.amount_pence = detail.amount_pence
                rt.vat_rate = detail.vat_rate
                rt.contact_id = detail.contact_id
            else:
                rt = RecurringTransaction(
                    template_id=template.id,
                    description=detail.description,
                    debit_account_id=detail.debit_account_id,
                    credit_account_id=detail.credit_account_id,
                    amount_pence=detail.amount_pence,
                    vat_rate=detail.vat_rate,
                    contact_id=detail.contact_id,
                )
                db.add(rt)

        # Update invoice detail
        if data.template_type == "invoice" and data.invoice_detail:
            detail = data.invoice_detail
            items_json = [item.model_dump() for item in detail.items]
            if template.recurring_invoice:
                ri = template.recurring_invoice
                ri.contact_id = detail.contact_id
                ri.items = items_json
                ri.payment_terms = detail.payment_terms
                ri.notes = detail.notes
            else:
                ri = RecurringInvoice(
                    template_id=template.id,
                    contact_id=detail.contact_id,
                    items=items_json,
                    payment_terms=detail.payment_terms,
                    notes=detail.notes,
                )
                db.add(ri)

        await db.commit()
        await db.refresh(template)

        return _template_to_response(template)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _validate_account(
        db: AsyncSession,
        account_id: uuid.UUID,
    ) -> None:
        """Verify an account exists and is active."""
        account = await db.get(Account, account_id)
        if account is None or not account.is_active:
            raise AccountNotFoundError(account_id)

    @staticmethod
    async def _validate_contact(
        db: AsyncSession,
        contact_id: uuid.UUID,
    ) -> None:
        """Verify a contact exists."""
        contact = await db.get(Contact, contact_id)
        if contact is None:
            raise ContactNotFoundError(contact_id)

    @staticmethod
    async def _create_transaction_from_template(
        db: AsyncSession,
        template: RecurringTemplate,
        rt: RecurringTransaction,
    ) -> None:
        """Create a posted transaction from a recurring template."""
        # Create transaction
        transaction = Transaction(
            description=rt.description,
            contact_id=rt.contact_id,
            currency="GBP",
            status="draft",
            effective_date=template.next_run_date,
            total_amount=rt.amount_pence,
        )
        db.add(transaction)
        await db.flush()

        # Create postings (debit and credit)
        debit_posting = Posting(
            transaction_id=transaction.id,
            account_id=rt.debit_account_id,
            debit_amount=rt.amount_pence,
            credit_amount=0,
            description=rt.description,
        )
        db.add(debit_posting)

        credit_posting = Posting(
            transaction_id=transaction.id,
            account_id=rt.credit_account_id,
            debit_amount=0,
            credit_amount=rt.amount_pence,
            description=rt.description,
        )
        db.add(credit_posting)

        # Post the transaction
        from src.services.transaction_service import TransactionService

        # Generate reference
        effective = transaction.effective_date or date.today()
        reference = await TransactionService._generate_je_reference(db, effective)

        transaction.reference = reference
        transaction.status = "posted"
        transaction.recorded_at = datetime.now(timezone.utc)

    @staticmethod
    async def _create_invoice_from_template(
        db: AsyncSession,
        template: RecurringTemplate,
        ri: RecurringInvoice,
    ) -> None:
        """Create a draft invoice from a recurring template."""
        today = template.next_run_date

        # Calculate payment terms: parse "Net X" to get due_date
        due_days = 30  # default
        if ri.payment_terms.upper().startswith("NET "):
            try:
                due_days = int(ri.payment_terms.split()[1])
            except (IndexError, ValueError):
                due_days = 30
        elif ri.payment_terms.lower().replace(" ", "") == "dueonreceipt":
            due_days = 0

        due_date = today + timedelta(days=due_days)

        # Calculate totals from items
        lines_orm: list[InvoiceLine] = []
        subtotal = 0
        vat_total = 0

        for i, item in enumerate(ri.items):
            vat_amount, line_total = _calculate_vat(
                item["unit_price"],
                item["quantity"],
                item["vat_rate"],
            )
            line = InvoiceLine(
                description=item["description"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                vat_rate=item["vat_rate"],
                vat_amount=vat_amount,
                line_total=line_total,
                sort_order=i,
            )
            lines_orm.append(line)
            subtotal += item["unit_price"] * item["quantity"]
            vat_total += vat_amount

        total = subtotal + vat_total

        invoice = Invoice(
            contact_id=ri.contact_id,
            status="draft",
            issue_date=today,
            due_date=due_date,
            subtotal=subtotal,
            vat_total=vat_total,
            total=total,
            currency="GBP",
            notes=ri.notes,
            lines=lines_orm,
        )
        db.add(invoice)
