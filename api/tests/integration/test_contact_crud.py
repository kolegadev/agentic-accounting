"""Integration tests for Contact CRUD cycle.

Uses mocked DB (no real database required) but tests the full
create → get → list → update → archive → find-or-create workflow.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.contact import Contact
from src.services.contact_service import (
    ContactNotFoundError,
    ContactService,
    DuplicateContactError,
)
from src.validators.contact import ContactCreate, ContactUpdate

NOW = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _mock_refresh(contact: Contact) -> None:
    """Populate server-default fields on a Contact (simulates DB refresh)."""
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
        contact.created_at = NOW
    if contact.updated_at is None:
        contact.updated_at = NOW


def _mock_result(return_value):
    """Create a MagicMock that mimics an AsyncResult."""
    m = MagicMock()
    m.scalar_one_or_none.return_value = return_value
    m.scalars.return_value.all.return_value = (
        return_value if isinstance(return_value, list) else [return_value]
    )
    m.scalar_one.return_value = (
        1
        if return_value is None
        else (len(return_value) if isinstance(return_value, list) else 1)
    )
    return m


def _make_contact(**overrides) -> Contact:
    """Create a Contact ORM instance with defaults (all required fields populated)."""
    defaults = {
        "id": uuid.uuid4(),
        "type": "customer",
        "name": "Acme Corp",
        "company": "Acme Ltd",
        "email": "info@acme.com",
        "phone": "+44 20 7946 0958",
        "address_line1": "10 Downing Street",
        "address_line2": None,
        "city": "London",
        "postcode": "SW1A 2AA",
        "country": "GB",
        "vat_number": "GB123456789",
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


def _setup_db_for_create() -> AsyncMock:
    """Return a mock DB pre-configured for create_contact (no duplicates, refresh populates)."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = _mock_refresh
    db.execute.return_value = _mock_result(None)
    return db


# ======================================================================
# Full CRUD Cycle
# ======================================================================

class TestFullCRUDCycle:
    """End-to-end test of the create → get → list → update → archive cycle."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self) -> None:
        """Complete contact lifecycle from creation to archival."""
        # ================================================================
        # PHASE 1: Create Contact
        # ================================================================
        db_create = _setup_db_for_create()

        create_data = ContactCreate(
            name="Acme Corp",
            type="customer",
            email="info@acme.com",
            company="Acme Ltd",
            vat_number="GB123456789",
            payment_terms="Net 30",
        )

        result = await ContactService.create_contact(db_create, create_data)

        assert result.name == "Acme Corp"
        assert result.type == "customer"
        assert result.status == "active"
        assert result.email == "info@acme.com"
        contact_id = uuid.UUID(result.id) if isinstance(result.id, str) else result.id

        # ================================================================
        # PHASE 2: Get Contact
        # ================================================================
        # We need to rebuild the ORM object with the response data
        contact_orm = _make_contact(
            id=contact_id,
            name="Acme Corp",
            type="customer",
            email="info@acme.com",
            company="Acme Ltd",
            vat_number="GB123456789",
            payment_terms="Net 30",
        )

        db_get = AsyncMock()
        db_get.execute.return_value = _mock_result(contact_orm)

        fetched = await ContactService.get_contact(db_get, contact_id)
        assert fetched is not None
        assert fetched.name == "Acme Corp"
        assert fetched.email == "info@acme.com"

        # ================================================================
        # PHASE 3: List Contacts
        # ================================================================
        db_list = AsyncMock()

        count_mock = MagicMock()
        count_mock.scalar_one.return_value = 1

        fetch_mock = MagicMock()
        fetch_mock.scalars.return_value.all.return_value = [contact_orm]

        db_list.execute.side_effect = [count_mock, fetch_mock]

        items, total = await ContactService.list_contacts(
            db_list,
            type="customer",
            status="active",
        )

        assert total == 1
        assert len(items) == 1
        assert items[0].name == "Acme Corp"

        # ================================================================
        # PHASE 4: Update Contact
        # ================================================================
        db_update = AsyncMock()
        db_update.commit = AsyncMock()
        db_update.refresh = AsyncMock()

        # Get contact, then duplicate check (no duplicates, self excluded)
        db_update.execute.side_effect = [
            _mock_result(contact_orm),  # get
            _mock_result(None),  # duplicate check
        ]

        update_data = ContactUpdate(
            name="Acme Corp Updated",
            company="Acme Holdings Ltd",
        )

        updated = await ContactService.update_contact(
            db_update,
            contact_id,
            update_data,
        )

        assert updated.name == "Acme Corp Updated"
        assert updated.company == "Acme Holdings Ltd"

        # ================================================================
        # PHASE 5: Archive Contact
        # ================================================================
        db_archive = AsyncMock()
        db_archive.commit = AsyncMock()
        db_archive.refresh = AsyncMock()
        db_archive.execute.return_value = _mock_result(contact_orm)

        # After archive, status should be "archived" in response
        # The mock doesn't actually change contact_orm, but the service sets it
        archived = await ContactService.archive_contact(db_archive, contact_id)

        assert archived.status == "archived"


# ======================================================================
# Duplicate Detection Scenarios
# ======================================================================

class TestDuplicateDetection:
    """Integration-level tests for duplicate detection."""

    @pytest.mark.asyncio
    async def test_duplicate_name_rejected(self) -> None:
        """Should reject creation when name already exists."""
        db = AsyncMock()
        existing = _make_contact(name="Acme Corp")
        db.execute.return_value = _mock_result(existing)

        data = ContactCreate(name="Acme Corp", type="customer")

        with pytest.raises(DuplicateContactError) as exc_info:
            await ContactService.create_contact(db, data)
        assert exc_info.value.status_code == 409
        assert exc_info.value.field == "name"

    @pytest.mark.asyncio
    async def test_duplicate_email_rejected(self) -> None:
        """Should reject creation when email already exists."""
        db = AsyncMock()
        existing = _make_contact(name="Other Corp", email="dup@example.com")
        db.execute.return_value = _mock_result(existing)

        data = ContactCreate(
            name="New Corp",
            type="customer",
            email="dup@example.com",
        )

        with pytest.raises(DuplicateContactError) as exc_info:
            await ContactService.create_contact(db, data)
        assert exc_info.value.status_code == 409
        assert exc_info.value.field == "email"

    @pytest.mark.asyncio
    async def test_duplicate_vat_rejected(self) -> None:
        """Should reject creation when VAT number already exists."""
        db = AsyncMock()
        existing = _make_contact(
            name="Other Corp",
            email="other@example.com",
            vat_number="GB999999999",
        )
        db.execute.return_value = _mock_result(existing)

        data = ContactCreate(
            name="New Corp",
            type="supplier",
            vat_number="GB999999999",
        )

        with pytest.raises(DuplicateContactError) as exc_info:
            await ContactService.create_contact(db, data)
        assert exc_info.value.status_code == 409
        assert "VAT" in exc_info.value.field

    @pytest.mark.asyncio
    async def test_duplicate_name_case_insensitive(self) -> None:
        """Should detect duplicate name regardless of case."""
        db = AsyncMock()
        existing = _make_contact(name="Acme Corp", email="existing@acme.com")
        db.execute.return_value = _mock_result(existing)

        data = ContactCreate(name="ACME CORP", type="customer")

        with pytest.raises(DuplicateContactError) as exc_info:
            await ContactService.create_contact(db, data)
        assert exc_info.value.field == "name"


# ======================================================================
# Find or Create Scenarios
# ======================================================================

class TestFindOrCreate:
    """Integration-level tests for find-or-create."""

    @pytest.mark.asyncio
    async def test_find_by_email_returns_existing(self) -> None:
        """Should find contact by email before attempting create."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        existing = _make_contact(
            name="Existing Corp",
            email="existing@corp.com",
        )
        db.execute.return_value = _mock_result(existing)

        contact, created = await ContactService.find_or_create(
            db,
            name="Existing Corp",
            email="existing@corp.com",
        )

        assert created is False
        assert contact.name == "Existing Corp"
        assert contact.email == "existing@corp.com"

    @pytest.mark.asyncio
    async def test_find_by_vat_when_email_not_found(self) -> None:
        """Should try VAT lookup when email returns nothing."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        existing = _make_contact(
            name="VAT Corp",
            email="different@corp.com",
            vat_number="GB555555555",
        )

        db.execute.side_effect = [
            _mock_result(None),  # email lookup → not found
            _mock_result(existing),  # VAT lookup → found
        ]

        contact, created = await ContactService.find_or_create(
            db,
            name="VAT Corp",
            email="unknown@corp.com",
            vat_number="GB555555555",
        )

        assert created is False
        assert contact.vat_number == "GB555555555"

    @pytest.mark.asyncio
    async def test_auto_create_when_nothing_found(self) -> None:
        """Should auto-create when no match found by any field."""
        db = _setup_db_for_create()

        # All lookups return None, then duplicate check returns None
        # Order: email → VAT (skipped, not provided) → name → duplicate check
        # But find_or_create doesn't provide vat_number here, so no VAT lookup
        # So: email (None) → name (None) → duplicate check (None)
        db.execute.side_effect = [
            _mock_result(None),  # email lookup
            _mock_result(None),  # name lookup
            _mock_result(None),  # duplicate check in create_contact
        ]

        contact, created = await ContactService.find_or_create(
            db,
            name="Brand New Supplier",
        )

        assert created is True
        assert contact.name == "Brand New Supplier"
        assert contact.type == "supplier"
        assert contact.status == "active"

    @pytest.mark.asyncio
    async def test_auto_create_sets_type_supplier(self) -> None:
        """Auto-created contacts should have type='supplier'."""
        db = _setup_db_for_create()

        db.execute.side_effect = [
            _mock_result(None),  # email
            _mock_result(None),  # name
            _mock_result(None),  # duplicate check
        ]

        contact, created = await ContactService.find_or_create(
            db,
            name="Auto Supplier Ltd",
            email="auto@supplier.com",
        )

        assert created is True
        assert contact.type == "supplier"


# ======================================================================
# Update with Duplicate Detection
# ======================================================================

class TestUpdateDuplicateDetection:
    """Integration-level tests for duplicate detection during updates."""

    @pytest.mark.asyncio
    async def test_update_self_not_duplicate(self) -> None:
        """Should allow updating a contact's own fields without flagging as duplicate."""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        contact = _make_contact()
        contact_id = contact.id

        # Get contact succeeds; duplicate check finds self → excluded by ID
        db.execute.side_effect = [
            _mock_result(contact),  # get
            _mock_result(None),  # duplicate check (self excluded, no other)
        ]

        result = await ContactService.update_contact(
            db,
            contact_id,
            ContactUpdate(company="New Company Name"),
        )

        assert result.company == "New Company Name"

    @pytest.mark.asyncio
    async def test_update_email_to_existing_rejected(self) -> None:
        """Should reject update when new email belongs to another contact."""
        db = AsyncMock()

        my_contact = _make_contact(name="My Contact", email="mine@example.com")
        other_contact = _make_contact(
            name="Other Contact",
            email="other@example.com",
        )

        db.execute.side_effect = [
            _mock_result(my_contact),  # get
            _mock_result(other_contact),  # duplicate check finds other
        ]

        with pytest.raises(DuplicateContactError) as exc_info:
            await ContactService.update_contact(
                db,
                my_contact.id,
                ContactUpdate(email="other@example.com"),
            )
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_update_vat_to_existing_rejected(self) -> None:
        """Should reject update when new VAT number belongs to another contact."""
        db = AsyncMock()

        my_contact = _make_contact(name="My Contact", vat_number="GB111111111")
        other_contact = _make_contact(
            name="Other Contact",
            email="other@example.com",
            vat_number="GB222222222",
        )

        db.execute.side_effect = [
            _mock_result(my_contact),  # get
            _mock_result(other_contact),  # duplicate check
        ]

        with pytest.raises(DuplicateContactError) as exc_info:
            await ContactService.update_contact(
                db,
                my_contact.id,
                ContactUpdate(vat_number="GB222222222"),
            )
        assert exc_info.value.status_code == 409


# ======================================================================
# Error Scenarios
# ======================================================================

class TestErrorScenarios:
    """Integration-level error scenarios."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_contact(self) -> None:
        """Should return None for non-existent contact ID."""
        db = AsyncMock()
        db.execute.return_value = _mock_result(None)

        result = await ContactService.get_contact(db, uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_update_nonexistent_contact(self) -> None:
        """Should raise ContactNotFoundError for non-existent contact."""
        db = AsyncMock()
        db.execute.return_value = _mock_result(None)

        with pytest.raises(ContactNotFoundError) as exc_info:
            await ContactService.update_contact(
                db,
                uuid.uuid4(),
                ContactUpdate(name="Nope"),
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_archive_nonexistent_contact(self) -> None:
        """Should raise ContactNotFoundError for non-existent contact."""
        db = AsyncMock()
        db.execute.return_value = _mock_result(None)

        with pytest.raises(ContactNotFoundError):
            await ContactService.archive_contact(db, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_list_with_multiple_filters(self) -> None:
        """Should handle all filter combinations."""
        db = AsyncMock()

        db.execute.side_effect = [
            _mock_result(None),  # count (scalar_one returns 1)
            _mock_result([]),  # fetch
        ]

        count_mock = MagicMock()
        count_mock.scalar_one.return_value = 0
        fetch_mock = MagicMock()
        fetch_mock.scalars.return_value.all.return_value = []

        db.execute.side_effect = [count_mock, fetch_mock]

        items, total = await ContactService.list_contacts(
            db,
            type="supplier",
            status="active",
            search="test",
            limit=25,
            offset=10,
        )

        assert total == 0
        assert len(items) == 0


# ======================================================================
# AR/AP Balance Tracking
# ======================================================================

class TestBalanceTracking:
    """Integration-level tests for AR/AP balance fields."""

    @pytest.mark.asyncio
    async def test_new_contact_has_zero_balances(self) -> None:
        """Newly created contacts should have 0 for all balance fields."""
        db = _setup_db_for_create()

        data = ContactCreate(name="Zero Balance Co", type="customer")

        result = await ContactService.create_contact(db, data)

        assert result.total_invoiced == 0
        assert result.total_paid == 0
        assert result.total_owing == 0

    @pytest.mark.asyncio
    async def test_balance_fields_preserved_on_update(self) -> None:
        """Balance fields should not be modified by update (handled by Module 6)."""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        contact = _make_contact(
            total_invoiced=100000,  # £1000.00
            total_paid=75000,  # £750.00
            total_owing=25000,  # £250.00
        )

        db.execute.side_effect = [
            _mock_result(contact),  # get
            _mock_result(None),  # duplicate check
        ]

        result = await ContactService.update_contact(
            db,
            contact.id,
            ContactUpdate(name="Updated Name"),
        )

        # Balance fields should remain unchanged
        assert result.total_invoiced == 100000
        assert result.total_paid == 75000
        assert result.total_owing == 25000
