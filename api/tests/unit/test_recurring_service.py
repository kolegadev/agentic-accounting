"""Unit tests for RecurringService with mocked DB session."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.account import Account
from src.models.contact import Contact
from src.models.recurring import RecurringInvoice, RecurringTemplate, RecurringTransaction
from src.services.recurring_service import (
    AccountNotFoundError,
    ContactNotFoundError,
    RecurringService,
    TemplateNotFoundError,
    TemplateNotActiveError,
    _calculate_next_date,
)
from src.validators.recurring import (
    RecurringInvoiceDetail,
    RecurringInvoiceItem,
    RecurringTemplateCreate,
    RecurringTransactionDetail,
)

NOW = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)
TODAY = date(2026, 6, 27)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db() -> AsyncMock:
    """Return an AsyncMock that behaves like an async SQLAlchemy session.

    Tracks added objects so that flush() can simulate assigning DB-generated
    values (id, created_at, updated_at) and refresh() can wire up relationships.
    """
    db = AsyncMock()
    _added_objects: list = []

    def _add(obj):
        _added_objects.append(obj)
    db.add = _add

    async def _flush():
        for obj in _added_objects:
            if isinstance(obj, RecurringTemplate) and obj.id is None:
                obj.id = uuid.uuid4()
                obj.run_count = obj.run_count or 0
                obj.created_at = obj.created_at or NOW
                obj.updated_at = obj.updated_at or NOW
            elif isinstance(obj, RecurringTransaction) and obj.id is None:
                obj.id = uuid.uuid4()
            elif isinstance(obj, RecurringInvoice) and obj.id is None:
                obj.id = uuid.uuid4()
    db.flush = _flush

    async def _refresh(obj, attribute_names=None):
        if isinstance(obj, RecurringTemplate):
            obj.run_count = obj.run_count if obj.run_count else 0
            obj.created_at = obj.created_at if obj.created_at else NOW
            obj.updated_at = obj.updated_at if obj.updated_at else NOW

            if attribute_names and "recurring_transaction" in attribute_names:
                # Find the RecurringTransaction that was added with this template_id
                for added in _added_objects:
                    if isinstance(added, RecurringTransaction) and added.template_id == obj.id:
                        added.id = added.id or uuid.uuid4()
                        obj.recurring_transaction = added
                        break
            if attribute_names and "recurring_invoice" in attribute_names:
                for added in _added_objects:
                    if isinstance(added, RecurringInvoice) and added.template_id == obj.id:
                        added.id = added.id or uuid.uuid4()
                        obj.recurring_invoice = added
                        break

    db.refresh = _refresh
    db.commit = AsyncMock()
    db.delete = AsyncMock()

    return db


@pytest.fixture
def bank_account() -> Account:
    return Account(
        id=uuid.uuid4(),
        code="1000",
        name="Bank Current",
        category="Asset",
        type="Bank",
        is_active=True,
    )


@pytest.fixture
def expense_account() -> Account:
    return Account(
        id=uuid.uuid4(),
        code="5210",
        name="Rent Expense",
        category="Expense",
        type="Expense",
        is_active=True,
    )


@pytest.fixture
def sample_contact() -> Contact:
    return Contact(
        id=uuid.uuid4(),
        type="customer",
        name="Test Customer",
    )


@pytest.fixture
def sample_transaction_create(
    bank_account: Account,
    expense_account: Account,
) -> RecurringTemplateCreate:
    return RecurringTemplateCreate(
        name="Monthly Rent",
        template_type="transaction",
        frequency="monthly",
        next_run_date=TODAY,
        end_type="never",
        is_active=True,
        transaction_detail=RecurringTransactionDetail(
            description="Monthly office rent",
            debit_account_id=expense_account.id,
            credit_account_id=bank_account.id,
            amount_pence=150000,
            vat_rate="20%",
        ),
    )


@pytest.fixture
def sample_invoice_create(sample_contact: Contact) -> RecurringTemplateCreate:
    return RecurringTemplateCreate(
        name="Monthly Hosting",
        template_type="invoice",
        frequency="monthly",
        next_run_date=TODAY,
        end_type="never",
        is_active=True,
        invoice_detail=RecurringInvoiceDetail(
            contact_id=sample_contact.id,
            items=[
                RecurringInvoiceItem(
                    description="Website hosting",
                    quantity=1,
                    unit_price=2999,
                    vat_rate="20%",
                ),
            ],
            payment_terms="Net 30",
            notes="Monthly hosting fee",
        ),
    )


# ---------------------------------------------------------------------------
# Helper: mock execute that returns a result
# ---------------------------------------------------------------------------


def _mock_result(return_value):
    """Create a MagicMock that mimics an AsyncResult."""
    m = MagicMock()
    m.scalar_one_or_none.return_value = return_value
    m.scalars.return_value.all.return_value = (
        return_value if isinstance(return_value, list) else [return_value]
    )
    m.scalar_one.return_value = (
        1 if return_value is None else (len(return_value) if isinstance(return_value, list) else 1)
    )
    return m


# ---------------------------------------------------------------------------
# _calculate_next_date tests
# ---------------------------------------------------------------------------


def test_calculate_next_date_daily() -> None:
    assert _calculate_next_date(date(2026, 6, 27), "daily") == date(2026, 6, 28)


def test_calculate_next_date_weekly() -> None:
    assert _calculate_next_date(date(2026, 6, 27), "weekly") == date(2026, 7, 4)


def test_calculate_next_date_bi_weekly() -> None:
    assert _calculate_next_date(date(2026, 6, 27), "bi_weekly") == date(2026, 7, 11)


def test_calculate_next_date_monthly() -> None:
    assert _calculate_next_date(date(2026, 6, 27), "monthly") == date(2026, 7, 27)


def test_calculate_next_date_quarterly() -> None:
    assert _calculate_next_date(date(2026, 6, 27), "quarterly") == date(2026, 9, 27)


def test_calculate_next_date_annual() -> None:
    assert _calculate_next_date(date(2026, 6, 27), "annual") == date(2027, 6, 27)


def test_calculate_next_date_month_end() -> None:
    """Jan 31 + 1 month → Feb 28 (non-leap)."""
    assert _calculate_next_date(date(2026, 1, 31), "monthly") == date(2026, 2, 28)


# ---------------------------------------------------------------------------
# create_template — transaction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_transaction_template_success(
    mock_db: AsyncMock,
    sample_transaction_create: RecurringTemplateCreate,
    bank_account: Account,
    expense_account: Account,
) -> None:
    """Should create a recurring transaction template."""
    # Mock account lookups
    mock_db.get = AsyncMock()
    mock_db.get.side_effect = lambda model, ident: {
        (Account, expense_account.id): expense_account,
        (Account, bank_account.id): bank_account,
    }.get((model, ident), None)

    result = await RecurringService.create_template(mock_db, sample_transaction_create)

    assert result.name == "Monthly Rent"
    assert result.template_type == "transaction"
    assert result.frequency == "monthly"
    assert result.transaction_detail is not None
    assert result.transaction_detail.amount_pence == 150000
    assert mock_db.commit.call_count == 1


# ---------------------------------------------------------------------------
# create_template — invoice
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_invoice_template_success(
    mock_db: AsyncMock,
    sample_invoice_create: RecurringTemplateCreate,
    sample_contact: Contact,
) -> None:
    """Should create a recurring invoice template."""
    mock_db.get = AsyncMock(return_value=sample_contact)

    result = await RecurringService.create_template(mock_db, sample_invoice_create)

    assert result.name == "Monthly Hosting"
    assert result.template_type == "invoice"
    assert result.invoice_detail is not None
    assert len(result.invoice_detail.items) == 1
    assert mock_db.commit.call_count == 1


# ---------------------------------------------------------------------------
# create_template — missing account
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_template_missing_account(
    mock_db: AsyncMock,
    bank_account: Account,
) -> None:
    """Should raise AccountNotFoundError when debit account doesn't exist."""
    fake_id = uuid.uuid4()
    mock_db.get = AsyncMock(return_value=None)  # Account not found

    data = RecurringTemplateCreate(
        name="Test",
        template_type="transaction",
        frequency="monthly",
        next_run_date=TODAY,
        end_type="never",
        transaction_detail=RecurringTransactionDetail(
            description="Test",
            debit_account_id=fake_id,
            credit_account_id=bank_account.id,
            amount_pence=10000,
        ),
    )

    with pytest.raises(AccountNotFoundError) as exc_info:
        await RecurringService.create_template(mock_db, data)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# create_template — missing contact
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_template_missing_contact(
    mock_db: AsyncMock,
) -> None:
    """Should raise ContactNotFoundError when contact doesn't exist."""
    mock_db.get = AsyncMock(return_value=None)

    data = RecurringTemplateCreate(
        name="Test Invoice",
        template_type="invoice",
        frequency="monthly",
        next_run_date=TODAY,
        end_type="never",
        invoice_detail=RecurringInvoiceDetail(
            contact_id=uuid.uuid4(),
            items=[
                RecurringInvoiceItem(
                    description="Item",
                    quantity=1,
                    unit_price=1000,
                    vat_rate="20%",
                ),
            ],
        ),
    )

    with pytest.raises(ContactNotFoundError) as exc_info:
        await RecurringService.create_template(mock_db, data)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# get_template
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_template_not_found(mock_db: AsyncMock) -> None:
    """Should return None for non-existent template."""
    mock_db.get = AsyncMock(return_value=None)

    result = await RecurringService.get_template(mock_db, uuid.uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# list_templates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_templates_with_filters(mock_db: AsyncMock) -> None:
    """Should list templates with type and active filters."""
    mock_db.execute = AsyncMock()
    mock_db.execute.side_effect = [
        _mock_result(None),  # Count (scalar_one → 1)
        _mock_result([]),  # Fetch results
    ]

    templates, total = await RecurringService.list_templates(
        mock_db,
        template_type="transaction",
        is_active=True,
    )

    assert total == 1


# ---------------------------------------------------------------------------
# skip_next
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skip_next_success(mock_db: AsyncMock) -> None:
    """Should advance next_run_date by one period."""
    template_id = uuid.uuid4()
    template = RecurringTemplate(
        id=template_id,
        name="Test",
        template_type="transaction",
        frequency="monthly",
        next_run_date=TODAY,
        end_type="never",
        is_active=True,
        run_count=0,
        created_at=NOW,
        updated_at=NOW,
    )
    mock_db.get = AsyncMock(return_value=template)

    result = await RecurringService.skip_next(mock_db, template_id)

    assert result.next_run_date == date(2026, 7, 27)
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_skip_next_inactive(mock_db: AsyncMock) -> None:
    """Should raise TemplateNotActiveError if template is paused."""
    template_id = uuid.uuid4()
    template = RecurringTemplate(
        id=template_id,
        name="Test",
        template_type="transaction",
        frequency="monthly",
        next_run_date=TODAY,
        end_type="never",
        is_active=False,
        run_count=0,
        created_at=NOW,
        updated_at=NOW,
    )
    mock_db.get = AsyncMock(return_value=template)

    with pytest.raises(TemplateNotActiveError):
        await RecurringService.skip_next(mock_db, template_id)


# ---------------------------------------------------------------------------
# pause / resume / delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pause_template_success(mock_db: AsyncMock) -> None:
    """Should set is_active=False."""
    template_id = uuid.uuid4()
    template = RecurringTemplate(
        id=template_id,
        name="Test",
        template_type="transaction",
        frequency="monthly",
        next_run_date=TODAY,
        end_type="never",
        is_active=True,
        run_count=0,
        created_at=NOW,
        updated_at=NOW,
    )
    mock_db.get = AsyncMock(return_value=template)

    result = await RecurringService.pause_template(mock_db, template_id)
    assert result.is_active is False


@pytest.mark.asyncio
async def test_resume_template_success(mock_db: AsyncMock) -> None:
    """Should set is_active=True."""
    template_id = uuid.uuid4()
    template = RecurringTemplate(
        id=template_id,
        name="Test",
        template_type="transaction",
        frequency="monthly",
        next_run_date=TODAY,
        end_type="never",
        is_active=False,
        run_count=0,
        created_at=NOW,
        updated_at=NOW,
    )
    mock_db.get = AsyncMock(return_value=template)

    result = await RecurringService.resume_template(mock_db, template_id)
    assert result.is_active is True


@pytest.mark.asyncio
async def test_resume_template_past_date(mock_db: AsyncMock) -> None:
    """When resuming, if next_run_date is in the past, set to today."""
    template_id = uuid.uuid4()
    past_date = date(2026, 1, 1)
    template = RecurringTemplate(
        id=template_id,
        name="Test",
        template_type="transaction",
        frequency="monthly",
        next_run_date=past_date,
        end_type="never",
        is_active=False,
        run_count=0,
        created_at=NOW,
        updated_at=NOW,
    )
    mock_db.get = AsyncMock(return_value=template)

    result = await RecurringService.resume_template(mock_db, template_id)
    assert result.next_run_date == TODAY


@pytest.mark.asyncio
async def test_delete_template_success(mock_db: AsyncMock) -> None:
    """Should delete the template."""
    template_id = uuid.uuid4()
    template = RecurringTemplate(
        id=template_id,
        name="Test",
        template_type="transaction",
        frequency="monthly",
        next_run_date=TODAY,
        end_type="never",
        is_active=True,
        run_count=0,
        created_at=NOW,
        updated_at=NOW,
    )
    mock_db.get = AsyncMock(return_value=template)

    await RecurringService.delete_template(mock_db, template_id)
    assert mock_db.delete.call_count == 1
    assert mock_db.commit.call_count == 1


@pytest.mark.asyncio
async def test_delete_template_not_found(mock_db: AsyncMock) -> None:
    """Should raise TemplateNotFoundError."""
    mock_db.get = AsyncMock(return_value=None)

    with pytest.raises(TemplateNotFoundError):
        await RecurringService.delete_template(mock_db, uuid.uuid4())


# ---------------------------------------------------------------------------
# process_due_templates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_due_templates_no_templates(mock_db: AsyncMock) -> None:
    """Should return 0 when no templates are due."""
    mock_db.execute = AsyncMock(return_value=_mock_result([]))

    count = await RecurringService.process_due_templates(mock_db)
    assert count == 0


@pytest.mark.asyncio
async def test_update_template_not_found(mock_db: AsyncMock) -> None:
    """Should raise TemplateNotFoundError when updating non-existent template."""
    mock_db.get = AsyncMock(return_value=None)

    data = RecurringTemplateCreate(
        name="Updated",
        template_type="transaction",
        frequency="monthly",
        next_run_date=TODAY,
        end_type="never",
        transaction_detail=RecurringTransactionDetail(
            description="Test",
            debit_account_id=uuid.uuid4(),
            credit_account_id=uuid.uuid4(),
            amount_pence=10000,
        ),
    )

    with pytest.raises(TemplateNotFoundError):
        await RecurringService.update_template(mock_db, uuid.uuid4(), data)


# ---------------------------------------------------------------------------
# Validation — end conditions
# ---------------------------------------------------------------------------


def test_validate_end_after_count_missing() -> None:
    """Should reject end_type=after_count without end_after_count."""
    with pytest.raises(ValueError, match="end_after_count"):
        RecurringTemplateCreate(
            name="Test",
            template_type="transaction",
            frequency="monthly",
            next_run_date=TODAY,
            end_type="after_count",
            transaction_detail=RecurringTransactionDetail(
                description="Test",
                debit_account_id=uuid.uuid4(),
                credit_account_id=uuid.uuid4(),
                amount_pence=10000,
            ),
        )


def test_validate_end_until_date_missing() -> None:
    """Should reject end_type=until_date without end_until_date."""
    with pytest.raises(ValueError, match="end_until_date"):
        RecurringTemplateCreate(
            name="Test",
            template_type="transaction",
            frequency="monthly",
            next_run_date=TODAY,
            end_type="until_date",
            transaction_detail=RecurringTransactionDetail(
                description="Test",
                debit_account_id=uuid.uuid4(),
                credit_account_id=uuid.uuid4(),
                amount_pence=10000,
            ),
        )


def test_validate_detail_missing_for_transaction() -> None:
    """Should reject transaction template without transaction_detail."""
    with pytest.raises(ValueError, match="transaction_detail"):
        RecurringTemplateCreate(
            name="Test",
            template_type="transaction",
            frequency="monthly",
            next_run_date=TODAY,
            end_type="never",
        )


def test_validate_detail_missing_for_invoice() -> None:
    """Should reject invoice template without invoice_detail."""
    with pytest.raises(ValueError, match="invoice_detail"):
        RecurringTemplateCreate(
            name="Test",
            template_type="invoice",
            frequency="monthly",
            next_run_date=TODAY,
            end_type="never",
        )
