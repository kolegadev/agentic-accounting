"""Pydantic models for VAT request/response validation — Module 7."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

VALID_SCHEMES = ("standard", "cash", "flat_rate")


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class VatPeriodCreate(BaseModel):
    """Schema for creating a new VAT period."""

    start_date: date = Field(
        ...,
        description="First day of the VAT period (inclusive)",
    )
    end_date: date = Field(
        ...,
        description="Last day of the VAT period (inclusive). Must be >= start_date.",
    )
    scheme: str = Field(
        "standard",
        pattern=r"^(standard|cash|flat_rate)$",
        description="VAT scheme: standard, cash, or flat_rate",
    )
    flat_rate_percentage: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Flat rate percentage (required if scheme=flat_rate)",
    )


class VatAdjustmentCreate(BaseModel):
    """Schema for creating a manual adjustment to a VAT return box."""

    box_number: int = Field(
        ...,
        ge=1,
        le=9,
        description="Box number being adjusted (1-9)",
    )
    amount: int = Field(
        ...,
        description="Absolute adjustment amount in pence (signed: positive=increase, negative=decrease)",
    )
    reason: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Human-readable reason for the adjustment",
    )
    source_reference: Optional[str] = Field(
        default=None,
        description="Digital link: source transaction/posting reference",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class VatPeriodResponse(BaseModel):
    """Schema for VAT period responses."""

    id: uuid.UUID
    start_date: date
    end_date: date
    scheme: str
    flat_rate_percentage: Optional[float] = None
    status: str
    closed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VatPeriodListResponse(BaseModel):
    """Wrapper for listing multiple VAT periods."""

    periods: list[VatPeriodResponse]
    total: int


class VatReturnResponse(BaseModel):
    """Schema for VAT return responses (9-box)."""

    id: uuid.UUID
    period_id: uuid.UUID
    box1: int = Field(description="VAT due on sales (output VAT) in pence")
    box2: int = Field(description="VAT due on EU acquisitions in pence")
    box3: int = Field(description="Total output VAT: Box 1 + Box 2")
    box4: int = Field(description="VAT reclaimed on purchases (input VAT) in pence")
    box5: int = Field(description="Net VAT: Box 3 - Box 4. Positive=payable, negative=reclaimable")
    box6: int = Field(description="Total sales excluding VAT in pence")
    box7: int = Field(description="Total purchases excluding VAT in pence")
    box8: int = Field(description="EU sales in pence")
    box9: int = Field(description="EU acquisitions in pence")
    submitted_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VatAdjustmentResponse(BaseModel):
    """Schema for VAT adjustment responses."""

    id: uuid.UUID
    vat_return_id: uuid.UUID
    box_number: int
    amount_before: int
    amount_after: int
    reason: str
    source_reference: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VatAuditEntry(BaseModel):
    """Schema for a single audit trail entry."""

    source_type: str = Field(
        description="Type of source: transaction|posting|vat_line|adjustment",
    )
    source_id: uuid.UUID
    source_reference: Optional[str] = None
    description: Optional[str] = None
    box_number: Optional[int] = Field(default=None, description="Which box this contributes to")
    amount: int = Field(description="Amount contributed in pence")
    net_amount: Optional[int] = Field(default=None, description="Net (pre-VAT) amount in pence")
    vat_type: Optional[str] = Field(default=None, description="input|output")
    vat_rate: Optional[str] = Field(default=None, description="20%|5%|0%|exempt")
    effective_date: Optional[date] = None


class VatAuditResponse(BaseModel):
    """Schema for the full VAT audit trail."""

    vat_return_id: uuid.UUID
    period: VatPeriodResponse
    entries: list[VatAuditEntry]
    summary: dict[str, int] = Field(
        description="Box number → total amount contributed",
    )


class VatReturnCalculationResponse(BaseModel):
    """Schema for VAT return calculation result — includes preview and audit."""

    vat_return: VatReturnResponse
    audit: VatAuditResponse
