"""Pydantic models for Recurring request/response validation — Module 7."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# RecurringInvoiceItem — line item within a recurring invoice template
# ---------------------------------------------------------------------------


class RecurringInvoiceItem(BaseModel):
    """Schema for an item within a recurring invoice template."""

    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Line item description",
        examples=["Monthly website hosting"],
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
        examples=[2999],
    )
    vat_rate: str = Field(
        ...,
        pattern=r"^(20%|5%|0%|exempt)$",
        description="VAT rate: 20%, 5%, 0%, or exempt",
        examples=["20%"],
    )


# ---------------------------------------------------------------------------
# Base template create/response shared fields
# ---------------------------------------------------------------------------


class RecurringTemplateBase(BaseModel):
    """Shared fields for template creation and responses."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Template name",
        examples=["Monthly Office Rent"],
    )
    template_type: str = Field(
        ...,
        pattern=r"^(transaction|invoice)$",
        description="Template type: transaction or invoice",
    )
    frequency: str = Field(
        ...,
        pattern=r"^(daily|weekly|bi_weekly|monthly|quarterly|annual)$",
        description="Recurrence frequency",
    )
    next_run_date: date = Field(
        ...,
        description="Date of the next scheduled run",
    )
    end_type: str = Field(
        default="never",
        pattern=r"^(never|after_count|until_date)$",
        description="End condition",
    )
    end_after_count: Optional[int] = Field(
        default=None,
        gt=0,
        description="Stop after this many occurrences (required if end_type=after_count)",
    )
    end_until_date: Optional[date] = Field(
        default=None,
        description="Stop after this date (required if end_type=until_date)",
    )
    is_active: bool = Field(
        default=True,
        description="Whether the template is active",
    )

    @model_validator(mode="after")
    def validate_end_conditions(self) -> "RecurringTemplateBase":
        """Validate that end conditions are properly specified."""
        if self.end_type == "after_count" and self.end_after_count is None:
            raise ValueError(
                "end_after_count is required when end_type is 'after_count'"
            )
        if self.end_type == "until_date" and self.end_until_date is None:
            raise ValueError(
                "end_until_date is required when end_type is 'until_date'"
            )
        return self


# ---------------------------------------------------------------------------
# Transaction-specific detail
# ---------------------------------------------------------------------------


class RecurringTransactionDetail(BaseModel):
    """Detail schema for recurring templates of type 'transaction'."""

    description: str = Field(
        ...,
        min_length=1,
        description="Transaction description applied on each recurrence",
        examples=["Monthly office rent payment"],
    )
    debit_account_id: uuid.UUID = Field(
        ...,
        description="Account to debit",
    )
    credit_account_id: uuid.UUID = Field(
        ...,
        description="Account to credit",
    )
    amount_pence: int = Field(
        ...,
        gt=0,
        description="Transaction amount in pence (always positive)",
        examples=[150000],
    )
    vat_rate: Optional[str] = Field(
        default=None,
        pattern=r"^(20%|5%|0%|exempt)$",
        description="VAT rate (if applicable)",
    )
    contact_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional contact for this transaction",
    )


# ---------------------------------------------------------------------------
# Invoice-specific detail
# ---------------------------------------------------------------------------


class RecurringInvoiceDetail(BaseModel):
    """Detail schema for recurring templates of type 'invoice'."""

    contact_id: uuid.UUID = Field(
        ...,
        description="Customer to invoice",
    )
    items: list[RecurringInvoiceItem] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Line items for each invoice",
    )
    payment_terms: str = Field(
        default="Net 30",
        min_length=1,
        max_length=50,
        description="Payment terms",
        examples=["Net 30", "Net 7", "Due on receipt"],
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional notes applied to each invoice",
    )


# ---------------------------------------------------------------------------
# Template Create
# ---------------------------------------------------------------------------


class RecurringTemplateCreate(RecurringTemplateBase):
    """Schema for creating a recurring template.

    Must include either transaction_detail or invoice_detail depending on
    template_type.
    """

    transaction_detail: Optional[RecurringTransactionDetail] = Field(
        default=None,
        description="Transaction detail (required if template_type=transaction)",
    )
    invoice_detail: Optional[RecurringInvoiceDetail] = Field(
        default=None,
        description="Invoice detail (required if template_type=invoice)",
    )

    @model_validator(mode="after")
    def validate_detail_present(self) -> "RecurringTemplateCreate":
        """Validate that the correct detail is provided for the template type."""
        if self.template_type == "transaction" and self.transaction_detail is None:
            raise ValueError(
                "transaction_detail is required when template_type is 'transaction'"
            )
        if self.template_type == "invoice" and self.invoice_detail is None:
            raise ValueError(
                "invoice_detail is required when template_type is 'invoice'"
            )
        return self


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class RecurringTransactionResponse(BaseModel):
    """Response schema for the transaction detail."""

    id: uuid.UUID
    template_id: uuid.UUID
    description: str
    debit_account_id: uuid.UUID
    credit_account_id: uuid.UUID
    amount_pence: int
    vat_rate: Optional[str] = None
    contact_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


class RecurringInvoiceResponse(BaseModel):
    """Response schema for the invoice detail."""

    id: uuid.UUID
    template_id: uuid.UUID
    contact_id: uuid.UUID
    items: list[dict]
    payment_terms: str
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class RecurringTemplateResponse(BaseModel):
    """Response schema for a recurring template with its detail."""

    id: uuid.UUID
    name: str
    template_type: str
    frequency: str
    next_run_date: date
    end_type: str
    end_after_count: Optional[int] = None
    end_until_date: Optional[date] = None
    is_active: bool
    last_run_date: Optional[date] = None
    run_count: int
    created_at: datetime
    updated_at: datetime
    transaction_detail: Optional[RecurringTransactionResponse] = None
    invoice_detail: Optional[RecurringInvoiceResponse] = None

    model_config = {"from_attributes": True}


class RecurringTemplateListResponse(BaseModel):
    """Wrapper for listing multiple templates."""

    templates: list[RecurringTemplateResponse]
    total: int


class RecurringProcessResponse(BaseModel):
    """Response after processing due templates."""

    processed: int
    message: str
