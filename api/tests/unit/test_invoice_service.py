"""Unit tests for InvoiceService with mocked DB session."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.invoice import CreditNote, Invoice, InvoiceLine
from src.services.invoice_service import (
    ContactNotFoundError,
    InvoiceLifecycleError,
    InvoiceNotFoundError,
    InvoiceService,
    _calculate_vat,
)
from src.validators.invoice import InvoiceCreate, InvoiceLineCreate

NOW = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)
TODAY = date.today()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db() -> AsyncMock:
    """Return an AsyncMock that behaves like an async SQLAlchemy session.

    The refresh mock populates common server-default fields (id, timestamps)
    so that Pydantic validation passes after create_invoice.
    """
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    async def mock_refresh(obj: object) -> None:
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid.uuid4()
        if hasattr(obj, "created_at") and obj.created_at is None:
            obj.created_at = NOW
        if hasattr(obj, "updated_at") and obj.updated_at is None:
            obj.updated_at = NOW
        # Also refresh nested lines if present
        if hasattr(obj, "lines"):
            for line in obj.lines:
                if hasattr(line, "id") and line.id is None:
                    line.id = uuid.uuid4()
                if hasattr(line, "invoice_id") and line.invoice_id is None:
                    line.invoice_id = obj.id

    db.refresh = mock_refresh
    return db


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


def _make_invoice(**overrides) -> Invoice:
    """Create an Invoice ORM instance with defaults."""
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
                description="Test line",
                quantity=1,
                unit_price=85000,
                vat_rate="20%",
                vat_amount=17000,
                line_total=102000,
                sort_order=0,
            )
        ],
    }
    defaults.update(overrides)
    return Invoice(**defaults)


# ======================================================================
# VAT Calculation
# ======================================================================


class TestVatCalculation:
    """Unit tests for _calculate_vat helper."""

    def test_vat_20_percent(self) -> None:
        """Should calculate 20% VAT correctly."""
        vat, total = _calculate_vat(10000, 2, "20%")
        assert vat == 4000  # 2 * 10000 * 0.20
        assert total == 24000  # 20000 + 4000

    def test_vat_5_percent(self) -> None:
        """Should calculate 5% VAT correctly."""
        vat, total = _calculate_vat(10000, 1, "5%")
        assert vat == 500
        assert total == 10500

    def test_vat_0_percent(self) -> None:
        """Should calculate 0% VAT correctly."""
        vat, total = _calculate_vat(10000, 3, "0%")
        assert vat == 0
        assert total == 30000

    def test_vat_exempt(self) -> None:
        """Should calculate exempt VAT correctly."""
        vat, total = _calculate_vat(5000, 2, "exempt")
        assert vat == 0
        assert total == 10000

    def test_vat_rounding(self) -> None:
        """Should handle rounding correctly (banker's rounding)."""
        vat, total = _calculate_vat(9999, 1, "20%")
        # 9999 * 0.20 = 1999.8, rounds to 2000
        assert vat == 2000
        assert total == 11999


# ======================================================================
# create_invoice
# ======================================================================


class TestCreateInvoice:
    """Unit tests for create_invoice."""

    @pytest.mark.asyncio
    async def test_create_invoice_success(self, mock_db: AsyncMock) -> None:
        """Should create a draft invoice with calculated totals."""
        contact_id = uuid.uuid4()

        from src.models.contact import Contact

        # Mock contact lookup
        async def mock_get(model, pk):
            if str(pk) == str(contact_id):
                return Contact(id=contact_id, name="Test Contact", status="active")
            return None

        mock_db.get = mock_get

        # Mock DB execute for balance update queries
        mock_db.execute.return_value = _mock_result(None, scalar_one_value=0)

        data = InvoiceCreate(
            contact_id=contact_id,
            issue_date=TODAY,
            due_date=TODAY,
            lines=[
                InvoiceLineCreate(
                    description="Service A",
                    quantity=2,
                    unit_price=10000,
                    vat_rate="20%",
                ),
                InvoiceLineCreate(
                    description="Service B",
                    quantity=1,
                    unit_price=50000,
                    vat_rate="20%",
                ),
            ],
            notes="Test invoice",
        )

        result = await InvoiceService.create_invoice(mock_db, data)

        assert result.status == "draft"
        assert result.subtotal == 70000  # 20000 + 50000
        assert result.vat_total == 14000  # 4000 + 10000
        assert result.total == 84000
        assert result.notes == "Test invoice"
        assert len(result.lines) == 2
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_create_invoice_contact_not_found(self, mock_db: AsyncMock) -> None:
        """Should raise ContactNotFoundError for non-existent contact."""
        mock_db.get = AsyncMock(return_value=None)

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
            await InvoiceService.create_invoice(mock_db, data)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_invoice_single_line(self, mock_db: AsyncMock) -> None:
        """Should create invoice with a single line."""
        from src.models.contact import Contact

        contact_id = uuid.uuid4()
        mock_db.get = AsyncMock(
            return_value=Contact(id=contact_id, name="Test", status="active")
        )
        mock_db.execute.return_value = _mock_result(None, scalar_one_value=0)

        data = InvoiceCreate(
            contact_id=contact_id,
            issue_date=TODAY,
            due_date=TODAY,
            lines=[
                InvoiceLineCreate(
                    description="Single item",
                    quantity=5,
                    unit_price=2000,
                    vat_rate="5%",
                ),
            ],
        )

        result = await InvoiceService.create_invoice(mock_db, data)

        assert result.subtotal == 10000  # 5 * 2000
        assert result.vat_total == 500  # 10000 * 0.05
        assert result.total == 10500
        assert result.status == "draft"

    @pytest.mark.asyncio
    async def test_create_invoice_zero_rated(self, mock_db: AsyncMock) -> None:
        """Should create invoice with 0% VAT lines."""
        from src.models.contact import Contact

        contact_id = uuid.uuid4()
        mock_db.get = AsyncMock(
            return_value=Contact(id=contact_id, name="Test", status="active")
        )
        mock_db.execute.return_value = _mock_result(None, scalar_one_value=0)

        data = InvoiceCreate(
            contact_id=contact_id,
            issue_date=TODAY,
            due_date=TODAY,
            lines=[
                InvoiceLineCreate(
                    description="Zero rated",
                    quantity=10,
                    unit_price=500,
                    vat_rate="0%",
                ),
            ],
        )

        result = await InvoiceService.create_invoice(mock_db, data)

        assert result.vat_total == 0
        assert result.subtotal == 5000
        assert result.total == 5000

    @pytest.mark.asyncio
    async def test_create_invoice_exempt_vat(self, mock_db: AsyncMock) -> None:
        """Should create invoice with exempt VAT lines."""
        from src.models.contact import Contact

        contact_id = uuid.uuid4()
        mock_db.get = AsyncMock(
            return_value=Contact(id=contact_id, name="Test", status="active")
        )
        mock_db.execute.return_value = _mock_result(None, scalar_one_value=0)

        data = InvoiceCreate(
            contact_id=contact_id,
            issue_date=TODAY,
            due_date=TODAY,
            lines=[
                InvoiceLineCreate(
                    description="Exempt service",
                    quantity=1,
                    unit_price=100000,
                    vat_rate="exempt",
                ),
            ],
        )

        result = await InvoiceService.create_invoice(mock_db, data)
        assert result.vat_total == 0
        assert result.total == 100000


# ======================================================================
# send_invoice
# ======================================================================


class TestSendInvoice:
    """Unit tests for send_invoice."""

    @pytest.mark.asyncio
    async def test_send_invoice_success(self, mock_db: AsyncMock) -> None:
        """Should send a draft invoice and generate reference."""
        invoice = _make_invoice(status="draft")
        mock_db.get = AsyncMock(return_value=invoice)

        # Mock reference count
        mock_db.execute.return_value = _mock_result(None)

        result = await InvoiceService.send_invoice(mock_db, invoice.id)

        assert result.status == "sent"
        assert result.sent_at is not None
        assert result.reference is not None
        assert result.reference.startswith(f"INV-{TODAY.year}-")
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_invoice_not_found(self, mock_db: AsyncMock) -> None:
        """Should raise InvoiceNotFoundError."""
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(InvoiceNotFoundError) as exc_info:
            await InvoiceService.send_invoice(mock_db, uuid.uuid4())
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_send_invoice_wrong_status(self, mock_db: AsyncMock) -> None:
        """Should raise InvoiceLifecycleError if not draft."""
        invoice = _make_invoice(status="sent")
        mock_db.get = AsyncMock(return_value=invoice)

        with pytest.raises(InvoiceLifecycleError) as exc_info:
            await InvoiceService.send_invoice(mock_db, invoice.id)
        assert exc_info.value.status_code == 422


# ======================================================================
# get_invoice
# ======================================================================


class TestGetInvoice:
    """Unit tests for get_invoice."""

    @pytest.mark.asyncio
    async def test_get_invoice_found(self, mock_db: AsyncMock) -> None:
        """Should return invoice when found."""
        invoice = _make_invoice()
        mock_db.get = AsyncMock(return_value=invoice)

        result = await InvoiceService.get_invoice(mock_db, invoice.id)
        assert result is not None
        assert result.status == "draft"
        assert result.total == 102000
        assert len(result.lines) == 1

    @pytest.mark.asyncio
    async def test_get_invoice_not_found(self, mock_db: AsyncMock) -> None:
        """Should return None when not found."""
        mock_db.get = AsyncMock(return_value=None)
        result = await InvoiceService.get_invoice(mock_db, uuid.uuid4())
        assert result is None


# ======================================================================
# list_invoices
# ======================================================================


class TestListInvoices:
    """Unit tests for list_invoices."""

    @pytest.mark.asyncio
    async def test_list_invoices_empty(self, mock_db: AsyncMock) -> None:
        """Should return empty list when no invoices."""
        count_mock = MagicMock()
        count_mock.scalar_one.return_value = 0
        fetch_mock = MagicMock()
        fetch_mock.scalars.return_value.all.return_value = []

        mock_db.execute.side_effect = [count_mock, fetch_mock]

        items, total = await InvoiceService.list_invoices(mock_db)
        assert total == 0
        assert len(items) == 0

    @pytest.mark.asyncio
    async def test_list_invoices_with_filters(self, mock_db: AsyncMock) -> None:
        """Should filter by status, contact, and date range."""
        invoice = _make_invoice()
        count_mock = MagicMock()
        count_mock.scalar_one.return_value = 1
        fetch_mock = MagicMock()
        fetch_mock.scalars.return_value.all.return_value = [invoice]

        mock_db.execute.side_effect = [count_mock, fetch_mock]

        items, total = await InvoiceService.list_invoices(
            mock_db,
            status="draft",
            contact_id=invoice.contact_id,
            date_from=TODAY,
            date_to=TODAY,
        )
        assert total == 1
        assert len(items) == 1


# ======================================================================
# mark_as_viewed
# ======================================================================


class TestMarkAsViewed:
    """Unit tests for mark_as_viewed."""

    @pytest.mark.asyncio
    async def test_mark_viewed_success(self, mock_db: AsyncMock) -> None:
        """Should mark sent invoice as viewed."""
        invoice = _make_invoice(status="sent")
        mock_db.get = AsyncMock(return_value=invoice)

        result = await InvoiceService.mark_as_viewed(mock_db, invoice.id)
        assert result.status == "viewed"
        assert result.viewed_at is not None
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_viewed_not_found(self, mock_db: AsyncMock) -> None:
        """Should raise InvoiceNotFoundError."""
        mock_db.get = AsyncMock(return_value=None)
        with pytest.raises(InvoiceNotFoundError):
            await InvoiceService.mark_as_viewed(mock_db, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_mark_viewed_wrong_status(self, mock_db: AsyncMock) -> None:
        """Should raise InvoiceLifecycleError if not sent."""
        invoice = _make_invoice(status="draft")
        mock_db.get = AsyncMock(return_value=invoice)

        with pytest.raises(InvoiceLifecycleError) as exc_info:
            await InvoiceService.mark_as_viewed(mock_db, invoice.id)
        assert exc_info.value.status_code == 422


# ======================================================================
# mark_as_paid
# ======================================================================


class TestMarkAsPaid:
    """Unit tests for mark_as_paid."""

    @pytest.mark.asyncio
    async def test_mark_paid_from_sent(self, mock_db: AsyncMock) -> None:
        """Should mark sent invoice as paid."""
        invoice = _make_invoice(status="sent")
        mock_db.get = AsyncMock(return_value=invoice)
        # mock_db.execute for balance update
        mock_db.execute.return_value = _mock_result(None)

        result = await InvoiceService.mark_as_paid(mock_db, invoice.id)
        assert result.status == "paid"
        assert result.paid_at is not None

    @pytest.mark.asyncio
    async def test_mark_paid_from_overdue(self, mock_db: AsyncMock) -> None:
        """Should mark overdue invoice as paid."""
        invoice = _make_invoice(status="overdue")
        mock_db.get = AsyncMock(return_value=invoice)
        mock_db.execute.return_value = _mock_result(None)

        result = await InvoiceService.mark_as_paid(mock_db, invoice.id)
        assert result.status == "paid"

    @pytest.mark.asyncio
    async def test_mark_paid_from_viewed(self, mock_db: AsyncMock) -> None:
        """Should mark viewed invoice as paid."""
        invoice = _make_invoice(status="viewed")
        mock_db.get = AsyncMock(return_value=invoice)
        mock_db.execute.return_value = _mock_result(None)

        result = await InvoiceService.mark_as_paid(mock_db, invoice.id)
        assert result.status == "paid"

    @pytest.mark.asyncio
    async def test_mark_paid_already_paid(self, mock_db: AsyncMock) -> None:
        """Should raise InvoiceLifecycleError if already paid."""
        invoice = _make_invoice(status="paid")
        mock_db.get = AsyncMock(return_value=invoice)

        with pytest.raises(InvoiceLifecycleError):
            await InvoiceService.mark_as_paid(mock_db, invoice.id)


# ======================================================================
# cancel_invoice
# ======================================================================


class TestCancelInvoice:
    """Unit tests for cancel_invoice."""

    @pytest.mark.asyncio
    async def test_cancel_draft(self, mock_db: AsyncMock) -> None:
        """Should cancel a draft invoice."""
        invoice = _make_invoice(status="draft")
        mock_db.get = AsyncMock(return_value=invoice)

        result = await InvoiceService.cancel_invoice(mock_db, invoice.id)
        assert result.status == "cancelled"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_sent_not_allowed(self, mock_db: AsyncMock) -> None:
        """Should raise InvoiceLifecycleError for sent invoice."""
        invoice = _make_invoice(status="sent")
        mock_db.get = AsyncMock(return_value=invoice)

        with pytest.raises(InvoiceLifecycleError) as exc_info:
            await InvoiceService.cancel_invoice(mock_db, invoice.id)
        assert exc_info.value.status_code == 422


# ======================================================================
# check_overdue
# ======================================================================


class TestCheckOverdue:
    """Unit tests for check_overdue."""

    @pytest.mark.asyncio
    async def test_check_overdue_finds_overdue(self, mock_db: AsyncMock) -> None:
        """Should mark sent invoices past due date as overdue."""
        past_date = date(2026, 1, 1)
        invoice = _make_invoice(status="sent", due_date=past_date)
        mock_db.execute.return_value = _mock_result([invoice])

        result = await InvoiceService.check_overdue(mock_db)
        assert len(result) == 1
        assert result[0].status == "overdue"

    @pytest.mark.asyncio
    async def test_check_overdue_none_found(self, mock_db: AsyncMock) -> None:
        """Should return empty list when no overdue invoices."""
        mock_db.execute.return_value = _mock_result([])
        result = await InvoiceService.check_overdue(mock_db)
        assert len(result) == 0


# ======================================================================
# create_credit_note
# ======================================================================


class TestCreateCreditNote:
    """Unit tests for create_credit_note."""

    @pytest.mark.asyncio
    async def test_create_credit_note_success(self, mock_db: AsyncMock) -> None:
        """Should create credit note and cancel original invoice."""
        invoice = _make_invoice(status="sent", total=102000)
        mock_db.get = AsyncMock(return_value=invoice)
        # mock_db.execute for reference count + balance update
        mock_db.execute.return_value = _mock_result(None, scalar_one_value=0)

        result = await InvoiceService.create_credit_note(
            mock_db,
            invoice.id,
            reason="Duplicate invoice",
        )

        assert result.total == -102000
        assert result.reason == "Duplicate invoice"
        assert result.reference.startswith(f"CN-{NOW.year}-")
        assert invoice.status == "cancelled"
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_credit_note_draft_not_allowed(self, mock_db: AsyncMock) -> None:
        """Should raise InvoiceLifecycleError for draft invoice."""
        invoice = _make_invoice(status="draft")
        mock_db.get = AsyncMock(return_value=invoice)

        with pytest.raises(InvoiceLifecycleError):
            await InvoiceService.create_credit_note(mock_db, invoice.id)

    @pytest.mark.asyncio
    async def test_create_credit_note_cancelled_not_allowed(self, mock_db: AsyncMock) -> None:
        """Should raise InvoiceLifecycleError for already cancelled."""
        invoice = _make_invoice(status="cancelled")
        mock_db.get = AsyncMock(return_value=invoice)

        with pytest.raises(InvoiceLifecycleError):
            await InvoiceService.create_credit_note(mock_db, invoice.id)

    @pytest.mark.asyncio
    async def test_create_credit_note_not_found(self, mock_db: AsyncMock) -> None:
        """Should raise InvoiceNotFoundError."""
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(InvoiceNotFoundError):
            await InvoiceService.create_credit_note(mock_db, uuid.uuid4())


# ======================================================================
# _generate_inv_reference
# ======================================================================


class TestGenerateReference:
    """Unit tests for reference generation."""

    @pytest.mark.asyncio
    async def test_generate_first_reference(self, mock_db: AsyncMock) -> None:
        """Should generate INV-YYYY-0001 for first invoice."""
        mock_db.execute.return_value = _mock_result(None)
        ref = await InvoiceService._generate_inv_reference(mock_db, TODAY)
        assert ref == f"INV-{TODAY.year}-0001"

    @pytest.mark.asyncio
    async def test_generate_sequential(self, mock_db: AsyncMock) -> None:
        """Should generate sequential numbers."""
        # Count returns 5 → next is 6
        count_mock = MagicMock()
        count_mock.scalar_one.return_value = 5
        mock_db.execute.return_value = count_mock

        ref = await InvoiceService._generate_inv_reference(mock_db, TODAY)
        assert ref == f"INV-{TODAY.year}-0006"
