"""Integration tests for Invoice CRUD and lifecycle with mocked DB."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.contact import Contact
from src.models.invoice import CreditNote, Invoice, InvoiceLine
from src.services.invoice_service import (
    ContactNotFoundError,
    InvoiceLifecycleError,
    InvoiceNotFoundError,
    InvoiceService,
)
from src.validators.invoice import InvoiceCreate, InvoiceLineCreate

NOW = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)
TODAY = date(2026, 6, 27)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_result(return_value, scalar_one_value=None):
    """Create a MagicMock that mimics an AsyncResult.

    Args:
        return_value: Value for scalar_one_or_none / scalars().all().
        scalar_one_value: Value for scalar_one(). If None, defaults to:
            - 0 if return_value is None (for count queries)
            - len(return_value) if list, else 1
    """
    m = MagicMock()
    m.scalar_one_or_none.return_value = return_value
    m.scalars.return_value.all.return_value = (
        return_value if isinstance(return_value, list) else [return_value]
    )
    if scalar_one_value is not None:
        m.scalar_one.return_value = scalar_one_value
    elif return_value is None:
        m.scalar_one.return_value = 0  # For count queries returning 0
    elif isinstance(return_value, list):
        m.scalar_one.return_value = len(return_value)
    else:
        m.scalar_one.return_value = 1
    return m


def _make_refresh():
    """Return an async refresh mock that populates server defaults."""
    async def mock_refresh(obj: object) -> None:
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid.uuid4()
        if hasattr(obj, "created_at") and obj.created_at is None:
            obj.created_at = NOW
        if hasattr(obj, "updated_at") and obj.updated_at is None:
            obj.updated_at = NOW
        if hasattr(obj, "lines"):
            for line in obj.lines:
                if hasattr(line, "id") and line.id is None:
                    line.id = uuid.uuid4()
                if hasattr(line, "invoice_id") and line.invoice_id is None:
                    line.invoice_id = obj.id
    return mock_refresh


def _make_contact(**overrides) -> Contact:
    """Create a Contact ORM instance."""
    defaults = {
        "id": uuid.uuid4(),
        "type": "customer",
        "name": "Test Customer",
        "company": None,
        "email": None,
        "phone": None,
        "address_line1": None,
        "address_line2": None,
        "city": None,
        "postcode": None,
        "country": "GB",
        "vat_number": None,
        "payment_terms": "Net 30",
        "default_gl_account_id": None,
        "currency": "GBP",
        "status": "active",
        "total_invoiced": 0,
        "total_paid": 0,
        "total_owing": 0,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    return Contact(**defaults)


def _make_invoice(**overrides) -> Invoice:
    """Create an Invoice ORM instance."""
    inv_id = overrides.pop("id", uuid.uuid4())
    defaults = {
        "id": inv_id,
        "reference": None,
        "contact_id": uuid.uuid4(),
        "status": "draft",
        "issue_date": TODAY,
        "due_date": TODAY,
        "subtotal": 85000,
        "vat_total": 17000,
        "total": 102000,
        "currency": "GBP",
        "notes": None,
        "sent_at": None,
        "viewed_at": None,
        "paid_at": None,
        "created_at": NOW,
        "updated_at": NOW,
        "lines": [
            InvoiceLine(
                id=uuid.uuid4(),
                invoice_id=inv_id,
                description="Consulting",
                quantity=10,
                unit_price=8500,
                vat_rate="20%",
                vat_amount=17000,
                line_total=102000,
                sort_order=0,
            )
        ],
    }
    defaults.update(overrides)
    return Invoice(**defaults)


def _setup_db_for_create(contact_id: uuid.UUID) -> AsyncMock:
    """Return mock DB pre-configured for create_invoice."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = _make_refresh()

    contact = _make_contact(id=contact_id)

    async def mock_get(model, pk):
        if hasattr(model, "__tablename__") and model.__tablename__ == "contacts":
            if str(pk) == str(contact_id):
                return contact
        return None

    db.get = mock_get
    db.execute = AsyncMock(return_value=_mock_result(None, scalar_one_value=0))
    return db


# ======================================================================
# Full Invoice Lifecycle
# ======================================================================


class TestFullInvoiceLifecycle:
    """Test the complete invoice lifecycle: create → send → view → pay."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self) -> None:
        """Complete draft → sent → viewed → paid flow."""
        contact_id = uuid.uuid4()

        # ================================================================
        # PHASE 1: Create draft invoice
        # ================================================================
        db_create = _setup_db_for_create(contact_id)

        data = InvoiceCreate(
            contact_id=contact_id,
            issue_date=TODAY,
            due_date=date(2026, 7, 27),
            lines=[
                InvoiceLineCreate(
                    description="Website design",
                    quantity=2,
                    unit_price=50000,
                    vat_rate="20%",
                ),
                InvoiceLineCreate(
                    description="Hosting setup",
                    quantity=1,
                    unit_price=25000,
                    vat_rate="20%",
                ),
            ],
            notes="Payment due within 30 days",
        )

        result = await InvoiceService.create_invoice(db_create, data)
        assert result.status == "draft"
        assert result.subtotal == 125000  # 100000 + 25000
        assert result.vat_total == 25000  # 20000 + 5000
        assert result.total == 150000
        assert result.notes == "Payment due within 30 days"
        assert len(result.lines) == 2

        inv_id = uuid.UUID(result.id) if isinstance(result.id, str) else result.id

        # ================================================================
        # PHASE 2: Send invoice
        # ================================================================
        invoice = _make_invoice(
            id=inv_id,
            contact_id=contact_id,
            status="draft",
            subtotal=125000,
            vat_total=25000,
            total=150000,
            notes="Payment due within 30 days",
            lines=[
                InvoiceLine(
                    id=uuid.uuid4(),
                    invoice_id=inv_id,
                    description="Website design",
                    quantity=2,
                    unit_price=50000,
                    vat_rate="20%",
                    vat_amount=20000,
                    line_total=120000,
                    sort_order=0,
                ),
                InvoiceLine(
                    id=uuid.uuid4(),
                    invoice_id=inv_id,
                    description="Hosting setup",
                    quantity=1,
                    unit_price=25000,
                    vat_rate="20%",
                    vat_amount=5000,
                    line_total=30000,
                    sort_order=1,
                ),
            ],
        )

        db_send = AsyncMock()
        db_send.commit = AsyncMock()
        db_send.refresh = AsyncMock()
        db_send.get = AsyncMock(return_value=invoice)

        # Reference count mock
        count_mock = MagicMock()
        count_mock.scalar_one.return_value = 0
        db_send.execute = AsyncMock(return_value=count_mock)

        sent = await InvoiceService.send_invoice(db_send, inv_id)
        assert sent.status == "sent"
        assert sent.sent_at is not None
        assert sent.reference == f"INV-{TODAY.year}-0001"

        # Update invoice for next phase
        invoice.status = "sent"
        invoice.reference = sent.reference
        invoice.sent_at = NOW

        # ================================================================
        # PHASE 3: Mark as viewed
        # ================================================================
        db_view = AsyncMock()
        db_view.commit = AsyncMock()
        db_view.refresh = AsyncMock()
        db_view.get = AsyncMock(return_value=invoice)

        viewed = await InvoiceService.mark_as_viewed(db_view, inv_id)
        assert viewed.status == "viewed"
        assert viewed.viewed_at is not None

        invoice.status = "viewed"
        invoice.viewed_at = NOW

        # ================================================================
        # PHASE 4: Mark as paid
        # ================================================================
        db_paid = AsyncMock()
        db_paid.commit = AsyncMock()
        db_paid.refresh = _make_refresh()
        db_paid.get = AsyncMock(return_value=invoice)

        # Balance update mocks: each execute returns a mock result with scalar_one=0
        db_paid.execute = AsyncMock(return_value=_mock_result(None, scalar_one_value=0))

        async def mock_get_paid(model, pk, **kwargs):
            if hasattr(model, "__tablename__") and model.__tablename__ == "contacts":
                return _make_contact(id=contact_id)
            if hasattr(model, "__tablename__") and model.__tablename__ == "invoices":
                return invoice
            return None

        db_paid.get = mock_get_paid

        paid = await InvoiceService.mark_as_paid(db_paid, inv_id)
        assert paid.status == "paid"
        assert paid.paid_at is not None


# ======================================================================
# Immutability Enforcement
# ======================================================================


class TestImmutability:
    """Test that sent invoices cannot be modified."""

    @pytest.mark.asyncio
    async def test_cannot_send_twice(self) -> None:
        """Should not allow sending an already sent invoice."""
        invoice = _make_invoice(status="sent")
        db = AsyncMock()
        db.get = AsyncMock(return_value=invoice)

        with pytest.raises(InvoiceLifecycleError) as exc_info:
            await InvoiceService.send_invoice(db, invoice.id)
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_cannot_cancel_sent_invoice(self) -> None:
        """Should not allow direct cancellation of sent invoice."""
        invoice = _make_invoice(status="sent")
        db = AsyncMock()
        db.get = AsyncMock(return_value=invoice)

        with pytest.raises(InvoiceLifecycleError) as exc_info:
            await InvoiceService.cancel_invoice(db, invoice.id)
        assert exc_info.value.status_code == 422


# ======================================================================
# Credit Note Scenarios
# ======================================================================


class TestCreditNoteScenarios:
    """Test credit note creation and invoice cancellation."""

    @pytest.mark.asyncio
    async def test_credit_note_cancels_sent_invoice(self) -> None:
        """Creating credit note should cancel the original sent invoice."""
        invoice = _make_invoice(status="sent", total=102000)
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = _make_refresh()
        db.get = AsyncMock(return_value=invoice)

        # Reference count + balance update mock
        db.execute = AsyncMock(return_value=_mock_result(None, scalar_one_value=0))

        cn = await InvoiceService.create_credit_note(
            db,
            invoice.id,
            reason="Invoice error",
        )

        assert cn.total == -102000
        assert cn.reference == f"CN-{NOW.year}-0001"
        assert invoice.status == "cancelled"

    @pytest.mark.asyncio
    async def test_credit_note_paid_invoice(self) -> None:
        """Should allow credit note on paid invoices."""
        invoice = _make_invoice(status="paid", total=50000)
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = _make_refresh()
        db.get = AsyncMock(return_value=invoice)

        db.execute = AsyncMock(return_value=_mock_result(None, scalar_one_value=0))

        cn = await InvoiceService.create_credit_note(db, invoice.id)
        assert cn.total == -50000
        assert invoice.status == "cancelled"

    @pytest.mark.asyncio
    async def test_credit_note_draft_rejected(self) -> None:
        """Should reject credit note on draft invoices."""
        invoice = _make_invoice(status="draft")
        db = AsyncMock()
        db.get = AsyncMock(return_value=invoice)

        with pytest.raises(InvoiceLifecycleError):
            await InvoiceService.create_credit_note(db, invoice.id)

    @pytest.mark.asyncio
    async def test_credit_note_already_cancelled_rejected(self) -> None:
        """Should reject credit note on already cancelled invoices."""
        invoice = _make_invoice(status="cancelled")
        db = AsyncMock()
        db.get = AsyncMock(return_value=invoice)

        with pytest.raises(InvoiceLifecycleError):
            await InvoiceService.create_credit_note(db, invoice.id)


# ======================================================================
# Overdue Detection
# ======================================================================


class TestOverdueDetection:
    """Test automatic overdue marking."""

    @pytest.mark.asyncio
    async def test_overdue_sent_invoice(self) -> None:
        """Should mark sent invoice with past due date as overdue."""
        past_date = date(2026, 1, 1)
        invoice = _make_invoice(status="sent", due_date=past_date)

        db = AsyncMock()
        db.commit = AsyncMock()
        db.execute.return_value = _mock_result([invoice])

        result = await InvoiceService.check_overdue(db)
        assert len(result) == 1
        assert result[0].status == "overdue"
        assert invoice.status == "overdue"

    @pytest.mark.asyncio
    async def test_overdue_viewed_invoice(self) -> None:
        """Should mark viewed invoice with past due date as overdue."""
        past_date = date(2026, 2, 15)
        invoice = _make_invoice(status="viewed", due_date=past_date)

        db = AsyncMock()
        db.commit = AsyncMock()
        db.execute.return_value = _mock_result([invoice])

        result = await InvoiceService.check_overdue(db)
        assert len(result) == 1
        assert result[0].status == "overdue"
        assert invoice.status == "overdue"

    @pytest.mark.asyncio
    async def test_paid_not_overdue(self) -> None:
        """Should not mark paid invoices as overdue."""
        past_date = date(2026, 1, 1)
        invoice = _make_invoice(status="paid", due_date=past_date)

        db = AsyncMock()
        db.execute.return_value = _mock_result([])  # no overdue found

        result = await InvoiceService.check_overdue(db)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_future_due_not_overdue(self) -> None:
        """Should not mark invoices with future due dates as overdue."""
        future_date = date(2026, 12, 31)
        invoice = _make_invoice(status="sent", due_date=future_date)

        db = AsyncMock()
        db.execute.return_value = _mock_result([])

        result = await InvoiceService.check_overdue(db)
        assert len(result) == 0


# ======================================================================
# Status Transition Validity
# ======================================================================


class TestStatusTransitions:
    """Test all valid and invalid status transitions."""

    @pytest.mark.asyncio
    async def test_valid_transitions(self) -> None:
        """Test all valid status transitions."""
        # draft → sent
        invoice = _make_invoice(status="draft")
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.get = AsyncMock(return_value=invoice)
        # reference count
        count_mock = MagicMock()
        count_mock.scalar_one.return_value = 0
        db.execute = AsyncMock(return_value=count_mock)

        result = await InvoiceService.send_invoice(db, invoice.id)
        assert result.status == "sent"

        # sent → viewed
        invoice.status = "sent"
        db_view = AsyncMock()
        db_view.commit = AsyncMock()
        db_view.refresh = AsyncMock()
        db_view.get = AsyncMock(return_value=invoice)
        result = await InvoiceService.mark_as_viewed(db_view, invoice.id)
        assert result.status == "viewed"

        # viewed → paid
        invoice.status = "viewed"
        db_paid = AsyncMock()
        db_paid.commit = AsyncMock()
        db_paid.refresh = _make_refresh()
        db_paid.get = AsyncMock(return_value=invoice)
        db_paid.execute = AsyncMock(return_value=_mock_result(None, scalar_one_value=0))
        result = await InvoiceService.mark_as_paid(db_paid, invoice.id)
        assert result.status == "paid"

    @pytest.mark.asyncio
    async def test_invalid_transitions(self) -> None:
        """Test invalid transitions are rejected."""
        # Cannot go from draft → paid
        invoice = _make_invoice(status="draft")
        db = AsyncMock()
        db.get = AsyncMock(return_value=invoice)

        with pytest.raises(InvoiceLifecycleError):
            await InvoiceService.mark_as_paid(db, invoice.id)

        # Cannot go from paid → sent
        invoice.status = "paid"
        with pytest.raises(InvoiceLifecycleError):
            await InvoiceService.send_invoice(db, invoice.id)

        # Cannot go from cancelled → paid
        invoice.status = "cancelled"
        with pytest.raises(InvoiceLifecycleError):
            await InvoiceService.mark_as_paid(db, invoice.id)


# ======================================================================
# Reference Generation
# ======================================================================


class TestReferenceGeneration:
    """Test INV-YYYY-NNNN and CN-YYYY-NNNN reference generation."""

    @pytest.mark.asyncio
    async def test_sequential_inv_references(self) -> None:
        """Should generate sequential invoice references."""
        db = AsyncMock()

        # First reference: count returns 0
        count0 = MagicMock()
        count0.scalar_one.return_value = 0
        db.execute.return_value = count0
        ref1 = await InvoiceService._generate_inv_reference(db, TODAY)
        assert ref1 == f"INV-{TODAY.year}-0001"

        # Second reference: count returns 1
        count1 = MagicMock()
        count1.scalar_one.return_value = 1
        db.execute.return_value = count1
        ref2 = await InvoiceService._generate_inv_reference(db, TODAY)
        assert ref2 == f"INV-{TODAY.year}-0002"

        # Third reference: count returns 42
        count42 = MagicMock()
        count42.scalar_one.return_value = 42
        db.execute.return_value = count42
        ref3 = await InvoiceService._generate_inv_reference(db, TODAY)
        assert ref3 == f"INV-{TODAY.year}-0043"

    @pytest.mark.asyncio
    async def test_sequential_cn_references(self) -> None:
        """Should generate sequential credit note references."""
        db = AsyncMock()

        count = MagicMock()
        count.scalar_one.return_value = 0
        db.execute.return_value = count

        ref = await InvoiceService._generate_cn_reference(db)
        assert ref == f"CN-{NOW.year}-0001"


# ======================================================================
# Error Scenarios
# ======================================================================


class TestErrorScenarios:
    """Integration-level error scenarios."""

    @pytest.mark.asyncio
    async def test_create_with_nonexistent_contact(self) -> None:
        """Should raise ContactNotFoundError."""
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        data = InvoiceCreate(
            contact_id=uuid.uuid4(),
            issue_date=TODAY,
            due_date=TODAY,
            lines=[
                InvoiceLineCreate(
                    description="Test",
                    unit_price=1000,
                    vat_rate="20%",
                ),
            ],
        )

        with pytest.raises(ContactNotFoundError) as exc_info:
            await InvoiceService.create_invoice(db, data)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_nonexistent_invoice(self) -> None:
        """Should return None for non-existent invoice."""
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        result = await InvoiceService.get_invoice(db, uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_send_nonexistent_invoice(self) -> None:
        """Should raise InvoiceNotFoundError."""
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        with pytest.raises(InvoiceNotFoundError):
            await InvoiceService.send_invoice(db, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_mark_paid_nonexistent_invoice(self) -> None:
        """Should raise InvoiceNotFoundError."""
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        with pytest.raises(InvoiceNotFoundError):
            await InvoiceService.mark_as_paid(db, uuid.uuid4())
