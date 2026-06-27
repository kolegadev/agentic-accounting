"""Pydantic models for HMRC MTD VAT API — Module 8."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Obligations
# ---------------------------------------------------------------------------


class ObligationItem(BaseModel):
    """A single VAT obligation returned by HMRC."""

    period_key: str = Field(description="HMRC period key (e.g. '#001')")
    start: date = Field(description="Period start date")
    end: date = Field(description="Period end date")
    due: date = Field(description="Due date for submission")
    status: str = Field(description="O=Open, F=Fulfilled")


class ObligationResponse(BaseModel):
    """Wrapper for HMRC VAT obligations response."""

    obligations: list[ObligationItem] = Field(
        default_factory=list,
        description="List of VAT obligations",
    )


# ---------------------------------------------------------------------------
# Submission
# ---------------------------------------------------------------------------


class SubmitResponse(BaseModel):
    """Response for a VAT return submission to HMRC."""

    vat_return_id: uuid.UUID = Field(
        description="Internal VAT return ID",
    )
    submission_id: str = Field(
        description="HMRC submission ID / payment indicator",
    )
    correlation_id: str = Field(
        description="HMRC correlation ID (fraud-prevention header)",
    )
    status: str = Field(
        default="accepted",
        description="Submission status: accepted|rejected|pending",
    )
    processing_date: datetime = Field(
        description="HMRC processing timestamp",
    )
    form_bundle_number: Optional[str] = Field(
        default=None,
        description="HMRC form bundle number (VAT return reference)",
    )
    payment_indicator: Optional[str] = Field(
        default=None,
        description="HMRC payment indicator (DDI/BANK/NI)",
    )
    charge_ref_number: Optional[str] = Field(
        default=None,
        description="HMRC charge reference number",
    )


class SubmissionStatusResponse(BaseModel):
    """Response for checking a submission's status."""

    submission_id: str = Field(description="HMRC submission ID")
    status: str = Field(description="Status: pending|accepted|rejected")
    vat_return_id: uuid.UUID = Field(description="Internal VAT return ID")
    submitted_at: Optional[datetime] = Field(
        default=None,
        description="When submitted to HMRC",
    )
    correlation_id: Optional[str] = Field(
        default=None,
        description="HMRC correlation ID",
    )


# ---------------------------------------------------------------------------
# Test connection
# ---------------------------------------------------------------------------


class HmrcConnectionResponse(BaseModel):
    """Response for HMRC API connectivity test."""

    connected: bool = Field(description="Whether HMRC API is reachable")
    message: str = Field(description="Human-readable status message")
    obligations_count: Optional[int] = Field(
        default=None,
        description="Number of VAT obligations found (if connected)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.utcnow(),
        description="Test timestamp",
    )
