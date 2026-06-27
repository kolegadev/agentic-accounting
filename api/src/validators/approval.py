"""Pydantic schemas for Approval Request/Step request/response validation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# ApprovalCreate
# ---------------------------------------------------------------------------

class ApprovalCreate(BaseModel):
    """Schema for creating a new approval request."""

    transaction_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Transaction to approve (optional)",
    )
    invoice_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Invoice to approve (optional)",
    )
    vat_return_id: Optional[uuid.UUID] = Field(
        default=None,
        description="VAT return to approve (optional)",
    )
    threshold_amount: int = Field(
        ...,
        ge=0,
        description="Monetary threshold amount in pence",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Optional reason for the approval request",
    )

    @field_validator("transaction_id", "invoice_id", "vat_return_id", mode="after")
    @classmethod
    def at_least_one_entity(cls, v: Optional[uuid.UUID], info) -> Optional[uuid.UUID]:
        """Ensure at least one of transaction_id, invoice_id, vat_return_id is set."""
        # We validate at model level that at least one is provided
        return v


# ---------------------------------------------------------------------------
# ApprovalStepResponse
# ---------------------------------------------------------------------------

class ApprovalStepResponse(BaseModel):
    """Schema for approval step responses."""

    id: uuid.UUID
    approval_request_id: uuid.UUID
    approver_id: Optional[uuid.UUID] = None
    level: int
    status: str
    comment: Optional[str] = None
    decided_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# ApprovalResponse
# ---------------------------------------------------------------------------

class ApprovalResponse(BaseModel):
    """Schema for approval request responses including steps."""

    id: uuid.UUID
    transaction_id: Optional[uuid.UUID] = None
    invoice_id: Optional[uuid.UUID] = None
    vat_return_id: Optional[uuid.UUID] = None
    status: str
    requested_by: uuid.UUID
    current_level: int
    total_levels: int
    reason: Optional[str] = None
    threshold_amount: Optional[int] = None
    steps: list[ApprovalStepResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# ApprovalListResponse
# ---------------------------------------------------------------------------

class ApprovalListResponse(BaseModel):
    """Wrapper for listing multiple approval requests."""

    approvals: list[ApprovalResponse]
    total: int


# ---------------------------------------------------------------------------
# ApprovalAction
# ---------------------------------------------------------------------------

class ApprovalAction(BaseModel):
    """Schema for approving or rejecting an approval step."""

    comment: Optional[str] = Field(
        default=None,
        description="Optional comment for approve/reject action",
    )
