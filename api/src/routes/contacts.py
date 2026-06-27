"""FastAPI router for Contact Management endpoints."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.services.contact_service import (
    ContactNotFoundError,
    ContactService,
    DuplicateContactError,
)
from src.validators.contact import (
    ContactCreate,
    ContactListResponse,
    ContactResponse,
    ContactUpdate,
)

router = APIRouter(prefix="/api/v1/contacts", tags=["Contacts"])


# ---------------------------------------------------------------------------
# POST / — Create contact
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=ContactResponse,
    summary="Create a new contact",
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "Duplicate contact detected"}},
)
async def create_contact(
    data: ContactCreate,
    db: AsyncSession = Depends(get_db),
) -> ContactResponse:
    """Create a new contact. Name, email, and VAT number must be unique."""
    try:
        return await ContactService.create_contact(db, data)
    except DuplicateContactError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# GET / — List contacts
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=ContactListResponse,
    summary="List contacts with optional filters",
    status_code=status.HTTP_200_OK,
)
async def list_contacts(
    type: Optional[str] = Query(
        None,
        description="Filter by contact type: customer, supplier, or both",
    ),
    status_filter: str = Query(
        "active",
        alias="status",
        description="Filter by status: active (default) or archived",
    ),
    search: Optional[str] = Query(
        None,
        description="Search contacts by name, company, or email",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> ContactListResponse:
    """List contacts with optional type, status, and search filters."""
    items, total = await ContactService.list_contacts(
        db,
        type=type,
        status=status_filter,
        search=search,
        limit=limit,
        offset=offset,
    )
    return ContactListResponse(contacts=items, total=total)


# ---------------------------------------------------------------------------
# GET /{contact_id} — Get contact by ID
# ---------------------------------------------------------------------------

@router.get(
    "/{contact_id}",
    response_model=ContactResponse,
    summary="Get contact by ID",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Contact not found"}},
)
async def get_contact(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ContactResponse:
    """Return a single contact by its UUID."""
    contact = await ContactService.get_contact(db, contact_id)
    if contact is None:
        raise HTTPException(
            status_code=404,
            detail=f"Contact '{contact_id}' not found",
        )
    return contact


# ---------------------------------------------------------------------------
# PATCH /{contact_id} — Update contact
# ---------------------------------------------------------------------------

@router.patch(
    "/{contact_id}",
    response_model=ContactResponse,
    summary="Partially update a contact",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Contact not found"},
        409: {"description": "Duplicate contact detected"},
    },
)
async def update_contact(
    contact_id: uuid.UUID,
    data: ContactUpdate,
    db: AsyncSession = Depends(get_db),
) -> ContactResponse:
    """Update one or more fields on an existing contact."""
    try:
        return await ContactService.update_contact(db, contact_id, data)
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except DuplicateContactError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /{contact_id}/archive — Archive contact
# ---------------------------------------------------------------------------

@router.post(
    "/{contact_id}/archive",
    response_model=ContactResponse,
    summary="Archive a contact",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Contact not found"}},
)
async def archive_contact(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ContactResponse:
    """Archive a contact by setting status='archived'."""
    try:
        return await ContactService.archive_contact(db, contact_id)
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /find-or-create — Find or create contact
# ---------------------------------------------------------------------------

@router.post(
    "/find-or-create",
    response_model=ContactResponse,
    summary="Find or create a contact",
    responses={200: {"description": "Contact found"}, 201: {"description": "Contact created"}},
)
async def find_or_create_contact(
    response: Response,
    name: str = Query(..., description="Contact name to find or create"),
    email: Optional[str] = Query(None, description="Email for lookup"),
    vat_number: Optional[str] = Query(None, description="VAT number for lookup"),
    db: AsyncSession = Depends(get_db),
) -> ContactResponse:
    """Find a contact by email, VAT number, or name; auto-create if not found."""
    contact, created = await ContactService.find_or_create(
        db,
        name=name,
        email=email,
        vat_number=vat_number,
    )
    if created:
        response.status_code = status.HTTP_201_CREATED
    return contact
