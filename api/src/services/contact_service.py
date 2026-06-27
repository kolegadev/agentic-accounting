"""Business logic for Contact Management — ContactService."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.contact import Contact
from src.validators.contact import (
    ContactCreate,
    ContactResponse,
    ContactUpdate,
)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class ContactServiceError(Exception):
    """Base exception for contact service errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class DuplicateContactError(ContactServiceError):
    """Contact with same name, email, or VAT number already exists."""

    def __init__(self, field: str, value: str) -> None:
        super().__init__(
            f"Contact with {field} '{value}' already exists",
            status_code=409,
        )
        self.field = field
        self.value = value


class ContactNotFoundError(ContactServiceError):
    """Contact not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__(
            f"Contact '{identifier}' not found",
            status_code=404,
        )


# ---------------------------------------------------------------------------
# ContactService
# ---------------------------------------------------------------------------

class ContactService:
    """Stateless service for Contact CRUD operations and duplicate detection."""

    # ------------------------------------------------------------------
    # Response mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _to_response(contact: Contact) -> ContactResponse:
        """Map an ORM Contact instance to a ContactResponse."""
        return ContactResponse.model_validate(contact)

    # ------------------------------------------------------------------
    # Duplicate detection
    # ------------------------------------------------------------------

    @staticmethod
    async def _check_duplicates(
        db: AsyncSession,
        name: str,
        email: Optional[str] = None,
        vat_number: Optional[str] = None,
        exclude_id: Optional[uuid.UUID] = None,
    ) -> None:
        """Check for duplicate contacts by name, email, or VAT number.

        Raises DuplicateContactError if a match is found.
        """
        conditions = []

        # Name match (exact, case-insensitive)
        conditions.append(func.lower(Contact.name) == name.lower())

        # Email match (exact, case-insensitive) if provided
        if email:
            conditions.append(func.lower(Contact.email) == email.lower())

        # VAT number match (exact) if provided
        if vat_number:
            conditions.append(Contact.vat_number == vat_number)

        if not conditions:
            return

        stmt = select(Contact).where(or_(*conditions))

        # Exclude self when updating
        if exclude_id is not None:
            stmt = stmt.where(Contact.id != exclude_id)

        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is None:
            return

        # Determine which field caused the conflict
        if email and existing.email and existing.email.lower() == email.lower():
            raise DuplicateContactError("email", email)
        if vat_number and existing.vat_number == vat_number:
            raise DuplicateContactError("VAT number", vat_number)
        if existing.name.lower() == name.lower():
            raise DuplicateContactError("name", name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    async def create_contact(
        db: AsyncSession,
        data: ContactCreate,
    ) -> ContactResponse:
        """Create a new contact after duplicate checks.

        Raises DuplicateContactError if name, email, or VAT number already exists.
        """
        await ContactService._check_duplicates(
            db,
            name=data.name,
            email=data.email,
            vat_number=data.vat_number,
        )

        contact = Contact(
            type=data.type,
            name=data.name,
            company=data.company,
            email=data.email,
            phone=data.phone,
            address_line1=data.address_line1,
            address_line2=data.address_line2,
            city=data.city,
            postcode=data.postcode,
            country=data.country,
            vat_number=data.vat_number,
            payment_terms=data.payment_terms,
            default_gl_account_id=data.default_gl_account_id,
            currency=data.currency,
        )
        db.add(contact)
        await db.commit()
        await db.refresh(contact)
        return ContactService._to_response(contact)

    @staticmethod
    async def get_contact(
        db: AsyncSession,
        contact_id: uuid.UUID,
    ) -> Optional[ContactResponse]:
        """Return a single contact by ID, or None if not found."""
        stmt = select(Contact).where(Contact.id == contact_id)
        result = await db.execute(stmt)
        contact = result.scalar_one_or_none()
        return ContactService._to_response(contact) if contact else None

    @staticmethod
    async def list_contacts(
        db: AsyncSession,
        *,
        type: Optional[str] = None,
        status: str = "active",
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ContactResponse], int]:
        """List contacts with optional filters. Returns (items, total_count)."""
        stmt = select(Contact)

        # ---- Filters ----
        if type:
            stmt = stmt.where(Contact.type == type)
        if status:
            stmt = stmt.where(Contact.status == status)
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Contact.name.ilike(search_term),
                    Contact.company.ilike(search_term),
                    Contact.email.ilike(search_term),
                )
            )

        # ---- Count ----
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # ---- Fetch ----
        stmt = stmt.order_by(Contact.name).offset(offset).limit(limit)
        result = await db.execute(stmt)
        contacts = list(result.scalars().all())

        return [ContactService._to_response(c) for c in contacts], total

    @staticmethod
    async def update_contact(
        db: AsyncSession,
        contact_id: uuid.UUID,
        data: ContactUpdate,
    ) -> ContactResponse:
        """Partially update a contact. Returns updated contact.

        Raises ContactNotFoundError if contact does not exist.
        Raises DuplicateContactError if updated fields conflict with another contact.
        """
        stmt = select(Contact).where(Contact.id == contact_id)
        result = await db.execute(stmt)
        contact = result.scalar_one_or_none()

        if contact is None:
            raise ContactNotFoundError(str(contact_id))

        update_data = data.model_dump(exclude_unset=True)

        # Check duplicates if name, email, or VAT number is being updated
        if any(k in update_data for k in ("name", "email", "vat_number")):
            await ContactService._check_duplicates(
                db,
                name=update_data.get("name", contact.name),
                email=update_data.get("email", contact.email),
                vat_number=update_data.get("vat_number", contact.vat_number),
                exclude_id=contact_id,
            )

        for field, value in update_data.items():
            setattr(contact, field, value)

        await db.commit()
        await db.refresh(contact)
        return ContactService._to_response(contact)

    @staticmethod
    async def archive_contact(
        db: AsyncSession,
        contact_id: uuid.UUID,
    ) -> ContactResponse:
        """Archive a contact by setting status='archived'.

        Raises ContactNotFoundError if contact does not exist.
        """
        stmt = select(Contact).where(Contact.id == contact_id)
        result = await db.execute(stmt)
        contact = result.scalar_one_or_none()

        if contact is None:
            raise ContactNotFoundError(str(contact_id))

        contact.status = "archived"
        await db.commit()
        await db.refresh(contact)
        return ContactService._to_response(contact)

    @staticmethod
    async def find_or_create(
        db: AsyncSession,
        name: str,
        email: Optional[str] = None,
        vat_number: Optional[str] = None,
    ) -> tuple[ContactResponse, bool]:
        """Find a contact by email, VAT number, or name; create if not found.

        Returns (contact, created) where created is True if a new contact
        was auto-created.
        """
        # Try exact match on email first
        if email:
            stmt = select(Contact).where(
                func.lower(Contact.email) == email.lower()
            )
            result = await db.execute(stmt)
            contact = result.scalar_one_or_none()
            if contact:
                return ContactService._to_response(contact), False

        # Try exact match on VAT number
        if vat_number:
            stmt = select(Contact).where(Contact.vat_number == vat_number)
            result = await db.execute(stmt)
            contact = result.scalar_one_or_none()
            if contact:
                return ContactService._to_response(contact), False

        # Try case-insensitive name match
        stmt = select(Contact).where(
            func.lower(Contact.name) == name.lower()
        )
        result = await db.execute(stmt)
        contact = result.scalar_one_or_none()
        if contact:
            return ContactService._to_response(contact), False

        # Not found — auto-create with type=supplier
        create_data = ContactCreate(
            name=name,
            type="supplier",
            email=email,
            vat_number=vat_number,
        )
        created = await ContactService.create_contact(db, create_data)
        return created, True
