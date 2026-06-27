"""Pydantic models for Invoice request/response validation — Module 6."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

VatRate = str  # "20%", "5%", "0%", "exempt"


class InvoiceLineCreate(BaseModel):
    """Schema for creating an invoice line item."""

    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Line item description",
        examples=["Website design - 10 hours @ £85/hr"],
    )
    quantity: int = Field(
        default=1,
        gt=0,
        description="Quantity (whole units)",
    )
    unit_price: int = Field(
        ...,
        ge=0,
        description="Unit price in pence",
        examples=[8500],
    )
    vat_rate: str = Field(
        ...,
        pattern=r"^(20%|5%|0%|exempt)$",
        description="VAT rate: 20%, 5%, 0%, or exempt",
        examples=["20%"],
    )


class InvoiceLineResponse(BaseModel):
    """Schema for invoice line responses."""

    id: uuid.UUID
    invoice_id: uuid.UUID
    description: str
    quantity: int
    unit_price: int
    vat_rate: str
    vat_amount: int
    line_total: int
    sort_order: int

    model_config = {"from_attributes": True}


class InvoiceCreate(BaseModel):
    """Schema for creating a draft invoice."""

    contact_id: uuid.UUID = Field(
        ...,
        description="UUID of the customer contact",
    )
    issue_date: date = Field(
        ...,
        description="Date the invoice was issued",
    )
    due_date: date = Field(
        ...,
        description="Date payment is due (must be >= issue_date)",
    )
    lines: list[InvoiceLineCreate] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Invoice line items (at least 1 required)",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional invoice notes / payment instructions",
    )
    currency: str = Field(
        default="GBP",
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code",
    )


class InvoiceResponse(BaseModel):
    """Schema for invoice responses (all fields including computed totals)."""

    id: uuid.UUID
    reference: Optional[str] = None
    contact_id: uuid.UUID
    status: str
    issue_date: date
    due_date: date
    subtotal: int
    vat_total: int
    total: int
    currency: str
    notes: Optional[str] = None
    sent_at: Optional[datetime] = None
    viewed_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    lines: list[InvoiceLineResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class InvoiceListResponse(BaseModel):
    """Wrapper for listing multiple invoices."""

    invoices: list[InvoiceResponse]
    total: int


class CreditNoteResponse(BaseModel):
    """Schema for credit note responses."""

    id: uuid.UUID
    invoice_id: uuid.UUID
    reference: Optional[str] = None
    contact_id: uuid.UUID
    total: int
    reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
