"""Unit tests for ContactService with mocked DB session."""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.contact import Contact
from src.services.contact_service import (
    ContactNotFoundError,
    ContactService,
    DuplicateContactError,
)
from src.validators.contact import ContactCreate, ContactUpdate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db() -> AsyncMock:
    """Return an AsyncMock that behaves like an async SQLAlchemy session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def sample_contact() -> Contact:
    """Create a fully-populated Contact ORM instance."""
    now = datetime(2026, 6, 27, 12, 0, 0)
    return Contact(
        id=uuid.uuid4(),
        type="customer",
        name="Acme Corp",
        company="Acme Ltd",
        email="info@acme.com",
        phone="+44 20 7946 0958",
        address_line1="10 Downing Street",
        address_line2=None,
        city="London",
        postcode="SW1A 2AA",
        country="GB",
        vat_number="GB123456789",
        payment_terms="Net 30",
        default_gl_account_id=None,
        currency="GBP",
        status="active",
        total_invoiced=0,
        total_paid=0,
        total_owing=0,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_contact_create() -> ContactCreate:
    """Return sample contact create data."""
    return ContactCreate(
        name="New Supplier",
        type="supplier",
        email="supplier@example.com",
        vat_number="GB987654321",
    )


# ---------------------------------------------------------------------------
# Helper: mock execute result
# ---------------------------------------------------------------------------

def _mock_result(return_value):
    """Create a MagicMock that mimics an AsyncResult."""
    m = MagicMock()
    m.scalar_one_or_none.return_value = return_value
    m.scalars.return_value.all.return_value = return_value if isinstance(return_value, list) else [return_value]
    m.scalar_one.return_value = 1 if return_value is None else (len(return_value) if isinstance(return_value, list) else 1)
    return m


# ======================================================================
# create_contact
# ======================================================================

@pytest.mark.asyncio
async def test_create_contact_success(
    mock_db: AsyncMock,
    sample_contact_create: ContactCreate,
) -> None:
    """Should create a contact successfully."""
    # No existing contact found for duplicate check
    mock_db.execute.return_value = _mock_result(None)

    # Override refresh to populate server defaults (simulate DB round-trip)
    now = datetime(2026, 6, 27, 12, 0, 0)

    async def mock_refresh(contact: Contact) -> None:
        if contact.id is None:
            contact.id = uuid.uuid4()
        if contact.status is None:
            contact.status = "active"
        if contact.total_invoiced is None:
            contact.total_invoiced = 0
        if contact.total_paid is None:
            contact.total_paid = 0
        if contact.total_owing is None:
            contact.total_owing = 0
        if contact.created_at is None:
            contact.created_at = now
        if contact.updated_at is None:
            contact.updated_at = now

    mock_db.refresh = mock_refresh

    result = await ContactService.create_contact(mock_db, sample_contact_create)

    assert result.name == "New Supplier"
    assert result.type == "supplier"
    assert result.status == "active"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_contact_duplicate_name(
    mock_db: AsyncMock,
    sample_contact: Contact,
) -> None:
    """Should raise DuplicateContactError if name already exists."""
    mock_db.execute.return_value = _mock_result(sample_contact)

    data = ContactCreate(
        name="Acme Corp",
        type="customer",
    )

    with pytest.raises(DuplicateContactError) as exc_info:
        await ContactService.create_contact(mock_db, data)
    assert exc_info.value.status_code == 409
    assert "name" in exc_info.value.field


@pytest.mark.asyncio
async def test_create_contact_duplicate_email(
    mock_db: AsyncMock,
    sample_contact: Contact,
) -> None:
    """Should raise DuplicateContactError if email already exists."""
    mock_db.execute.return_value = _mock_result(sample_contact)

    data = ContactCreate(
        name="Different Name",
        type="customer",
        email="info@acme.com",
    )

    with pytest.raises(DuplicateContactError) as exc_info:
        await ContactService.create_contact(mock_db, data)
    assert exc_info.value.status_code == 409
    assert exc_info.value.field == "email"


@pytest.mark.asyncio
async def test_create_contact_duplicate_vat(
    mock_db: AsyncMock,
    sample_contact: Contact,
) -> None:
    """Should raise DuplicateContactError if VAT number already exists."""
    mock_db.execute.return_value = _mock_result(sample_contact)

    data = ContactCreate(
        name="Different Name",
        type="supplier",
        vat_number="GB123456789",
    )

    with pytest.raises(DuplicateContactError) as exc_info:
        await ContactService.create_contact(mock_db, data)
    assert exc_info.value.status_code == 409
    assert "VAT" in exc_info.value.field


# ======================================================================
# get_contact
# ======================================================================

@pytest.mark.asyncio
async def test_get_contact_found(
    mock_db: AsyncMock,
    sample_contact: Contact,
) -> None:
    """Should return contact when found by ID."""
    mock_db.execute.return_value = _mock_result(sample_contact)

    result = await ContactService.get_contact(mock_db, sample_contact.id)
    assert result is not None
    assert result.name == "Acme Corp"
    assert result.email == "info@acme.com"


@pytest.mark.asyncio
async def test_get_contact_not_found(mock_db: AsyncMock) -> None:
    """Should return None when contact not found."""
    mock_db.execute.return_value = _mock_result(None)

    result = await ContactService.get_contact(mock_db, uuid.uuid4())
    assert result is None


# ======================================================================
# list_contacts
# ======================================================================

@pytest.mark.asyncio
async def test_list_contacts_active_only(
    mock_db: AsyncMock,
    sample_contact: Contact,
) -> None:
    """Should return only active contacts by default."""
    # Two calls: count then fetch
    mock_db.execute.side_effect = [
        _mock_result(None),  # scalar_one returns 1 for count
        _mock_result([sample_contact]),  # fetch
    ]

    items, total = await ContactService.list_contacts(mock_db)

    assert total == 1
    assert len(items) == 1
    assert items[0].status == "active"


@pytest.mark.asyncio
async def test_list_contacts_with_filters(
    mock_db: AsyncMock,
    sample_contact: Contact,
) -> None:
    """Should filter by type, status, and search."""
    mock_db.execute.side_effect = [
        _mock_result(None),  # count
        _mock_result([sample_contact]),  # fetch
    ]

    items, total = await ContactService.list_contacts(
        mock_db,
        type="customer",
        search="Acme",
        limit=10,
    )

    assert total == 1
    assert len(items) == 1


@pytest.mark.asyncio
async def test_list_contacts_empty(mock_db: AsyncMock) -> None:
    """Should return empty list when no contacts match."""
    mock_db.execute.side_effect = [
        _mock_result(None),  # count (scalar_one returns 1, but actually 0)
        _mock_result([]),
    ]

    # Override scalar_one for count to return 0
    count_mock = MagicMock()
    count_mock.scalar_one.return_value = 0
    fetch_mock = MagicMock()
    fetch_mock.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [count_mock, fetch_mock]

    items, total = await ContactService.list_contacts(mock_db, type="supplier")
    assert total == 0
    assert len(items) == 0


# ======================================================================
# update_contact
# ======================================================================

@pytest.mark.asyncio
async def test_update_contact_success(
    mock_db: AsyncMock,
    sample_contact: Contact,
) -> None:
    """Should update contact fields."""
    # First call: get contact, second: duplicate check (self excluded → None)
    mock_db.execute.side_effect = [
        _mock_result(sample_contact),
        _mock_result(None),
    ]

    data = ContactUpdate(name="Updated Acme Ltd")
    result = await ContactService.update_contact(mock_db, sample_contact.id, data)

    assert result.name == "Updated Acme Ltd"
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_update_contact_not_found(mock_db: AsyncMock) -> None:
    """Should raise ContactNotFoundError for non-existent contact."""
    mock_db.execute.return_value = _mock_result(None)

    with pytest.raises(ContactNotFoundError) as exc_info:
        await ContactService.update_contact(
            mock_db,
            uuid.uuid4(),
            ContactUpdate(name="Nope"),
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_contact_duplicate_on_change(
    mock_db: AsyncMock,
    sample_contact: Contact,
) -> None:
    """Should detect duplicates when changing email to existing one."""
    existing_other = Contact(
        id=uuid.uuid4(),
        type="customer",
        name="Other Corp",
        email="other@example.com",
        status="active",
    )

    # First execute: get sample_contact
    # Second execute: duplicate check finds existing_other
    mock_db.execute.side_effect = [
        _mock_result(sample_contact),
        _mock_result(existing_other),
    ]

    with pytest.raises(DuplicateContactError) as exc_info:
        await ContactService.update_contact(
            mock_db,
            sample_contact.id,
            ContactUpdate(email="other@example.com"),
        )
    assert exc_info.value.status_code == 409


# ======================================================================
# archive_contact
# ======================================================================

@pytest.mark.asyncio
async def test_archive_contact_success(
    mock_db: AsyncMock,
    sample_contact: Contact,
) -> None:
    """Should set status to 'archived'."""
    mock_db.execute.return_value = _mock_result(sample_contact)

    result = await ContactService.archive_contact(mock_db, sample_contact.id)

    assert result.status == "archived"
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_archive_contact_not_found(mock_db: AsyncMock) -> None:
    """Should raise ContactNotFoundError."""
    mock_db.execute.return_value = _mock_result(None)

    with pytest.raises(ContactNotFoundError):
        await ContactService.archive_contact(mock_db, uuid.uuid4())


# ======================================================================
# find_or_create
# ======================================================================

@pytest.mark.asyncio
async def test_find_or_create_found_by_email(
    mock_db: AsyncMock,
    sample_contact: Contact,
) -> None:
    """Should find existing contact by email."""
    mock_db.execute.return_value = _mock_result(sample_contact)

    contact, created = await ContactService.find_or_create(
        mock_db,
        name="Acme Corp",
        email="info@acme.com",
    )

    assert created is False
    assert contact.email == "info@acme.com"


@pytest.mark.asyncio
async def test_find_or_create_found_by_vat(
    mock_db: AsyncMock,
    sample_contact: Contact,
) -> None:
    """Should find existing contact by VAT number when email not found."""
    # First: email lookup → None
    # Second: VAT lookup → found
    mock_db.execute.side_effect = [
        _mock_result(None),
        _mock_result(sample_contact),
    ]

    contact, created = await ContactService.find_or_create(
        mock_db,
        name="Acme Corp",
        email="unknown@example.com",
        vat_number="GB123456789",
    )

    assert created is False
    assert contact.vat_number == "GB123456789"


@pytest.mark.asyncio
async def test_find_or_create_found_by_name(
    mock_db: AsyncMock,
    sample_contact: Contact,
) -> None:
    """Should find existing contact by name when email/VAT not matched."""
    # No email or VAT provided, so only the name lookup runs
    mock_db.execute.return_value = _mock_result(sample_contact)

    contact, created = await ContactService.find_or_create(
        mock_db,
        name="Acme Corp",
    )

    assert created is False
    assert contact.name == "Acme Corp"


@pytest.mark.asyncio
async def test_find_or_create_auto_creates(
    mock_db: AsyncMock,
) -> None:
    """Should auto-create a new contact when none found."""
    # Flow: email lookup → None, name lookup → None, duplicate check → None
    mock_db.execute.side_effect = [
        _mock_result(None),  # email lookup
        _mock_result(None),  # name lookup
        _mock_result(None),  # duplicate check in create_contact
    ]

    # Override refresh to populate server defaults
    now = datetime(2026, 6, 27, 12, 0, 0)

    async def mock_refresh(contact: Contact) -> None:
        if contact.id is None:
            contact.id = uuid.uuid4()
        if contact.status is None:
            contact.status = "active"
        if contact.total_invoiced is None:
            contact.total_invoiced = 0
        if contact.total_paid is None:
            contact.total_paid = 0
        if contact.total_owing is None:
            contact.total_owing = 0
        if contact.created_at is None:
            contact.created_at = now
        if contact.updated_at is None:
            contact.updated_at = now

    mock_db.refresh = mock_refresh

    contact, created = await ContactService.find_or_create(
        mock_db,
        name="New Auto Supplier",
        email="auto@supplier.com",
    )

    assert created is True
    assert contact.name == "New Auto Supplier"
    assert contact.type == "supplier"
    assert contact.email == "auto@supplier.com"


# ======================================================================
# _check_duplicates edge cases
# ======================================================================

@pytest.mark.asyncio
async def test_check_duplicates_case_insensitive_name(
    mock_db: AsyncMock,
    sample_contact: Contact,
) -> None:
    """Should detect duplicate name regardless of case."""
    # Set the email on the existing contact to something NOT matching
    sample_contact.email = "existing@acme.com"
    mock_db.execute.return_value = _mock_result(sample_contact)

    with pytest.raises(DuplicateContactError) as exc_info:
        await ContactService._check_duplicates(
            mock_db,
            name="ACME CORP",  # uppercase
        )
    assert exc_info.value.field == "name"


@pytest.mark.asyncio
async def test_check_duplicates_no_duplicates(mock_db: AsyncMock) -> None:
    """Should not raise when no duplicates found."""
    mock_db.execute.return_value = _mock_result(None)

    # Should not raise
    await ContactService._check_duplicates(
        mock_db,
        name="Unique Name",
        email="unique@example.com",
        vat_number="GB111111111",
    )


@pytest.mark.asyncio
async def test_check_duplicates_exclude_self(
    mock_db: AsyncMock,
    sample_contact: Contact,
) -> None:
    """Should not flag self as duplicate when exclude_id matches."""
    # The real SQL would exclude by ID, so no result returned
    mock_db.execute.return_value = _mock_result(None)

    # Should not raise
    await ContactService._check_duplicates(
        mock_db,
        name=sample_contact.name,
        exclude_id=sample_contact.id,
    )
