"""Pydantic models for Contact Management request/response validation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

ContactType = Literal["customer", "supplier", "both", "other"]
ContactStatus = Literal["active", "archived"]


class ContactCreate(BaseModel):
    """Schema for creating a new contact."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Contact display name",
        examples=["Acme Corp", "John Doe"],
    )
    type: ContactType = Field(
        ...,
        description="Contact type: customer, supplier, or both",
    )
    company: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Company / trading name",
    )
    email: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Primary email address",
    )
    phone: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Primary phone number",
    )
    address_line1: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Address line 1",
    )
    address_line2: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Address line 2",
    )
    city: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Town / city",
    )
    postcode: Optional[str] = Field(
        default=None,
        max_length=10,
        description="Postcode / ZIP",
    )
    country: str = Field(
        default="GB",
        min_length=2,
        max_length=2,
        description="ISO 3166-1 alpha-2 country code",
    )
    vat_number: Optional[str] = Field(
        default=None,
        max_length=20,
        description="UK/EU VAT registration number",
    )
    payment_terms: str = Field(
        default="Net 30",
        max_length=50,
        description="Default payment terms",
    )
    default_gl_account_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Default GL account for transactions with this contact",
    )
    currency: str = Field(
        default="GBP",
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code",
    )


class ContactUpdate(BaseModel):
    """Schema for partial contact update. All fields optional."""

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated contact name",
    )
    type: Optional[ContactType] = Field(
        default=None,
        description="Updated contact type",
    )
    company: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Updated company name",
    )
    email: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Updated email address",
    )
    phone: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Updated phone number",
    )
    address_line1: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Updated address line 1",
    )
    address_line2: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Updated address line 2",
    )
    city: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Updated city",
    )
    postcode: Optional[str] = Field(
        default=None,
        max_length=10,
        description="Updated postcode",
    )
    country: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=2,
        description="Updated country code",
    )
    vat_number: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Updated VAT number",
    )
    payment_terms: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Updated payment terms",
    )
    default_gl_account_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Updated default GL account",
    )
    currency: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=3,
        description="Updated currency code",
    )


class ContactResponse(BaseModel):
    """Schema for contact responses (all fields)."""

    id: uuid.UUID
    type: str
    name: str
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    postcode: Optional[str] = None
    country: str
    vat_number: Optional[str] = None
    payment_terms: str
    default_gl_account_id: Optional[uuid.UUID] = None
    currency: str
    status: str
    total_invoiced: int
    total_paid: int
    total_owing: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ContactListResponse(BaseModel):
    """Wrapper for listing multiple contacts."""

    contacts: list[ContactResponse]
    total: int
