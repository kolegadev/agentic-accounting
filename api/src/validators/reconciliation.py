"""Pydantic schemas for Reconciliation request/response validation."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class StartReconciliation(BaseModel):
    """Schema for starting a new reconciliation session."""

    bank_account_id: uuid.UUID = Field(
        ...,
        description="Bank account UUID to reconcile",
    )
    start_date: date = Field(
        ...,
        description="Start date of the reconciliation period",
    )
    end_date: date = Field(
        ...,
        description="End date of the reconciliation period",
    )
    opening_balance: int = Field(
        ...,
        description="Opening balance in pence",
    )
    closing_balance: int = Field(
        ...,
        description="Expected closing balance in pence",
    )


class MatchRequest(BaseModel):
    """Schema for matching a bank transaction to one or more ledger transactions."""

    bank_transaction_id: uuid.UUID = Field(
        ...,
        description="Bank transaction UUID to match",
    )
    transaction_ids: list[uuid.UUID] = Field(
        ...,
        min_length=1,
        description="One or more ledger transaction UUIDs to match against (1:1 or 1:many)",
    )


class CreateAndMatchRequest(BaseModel):
    """Schema for creating a new ledger transaction and matching it to a bank line."""

    bank_transaction_id: uuid.UUID = Field(
        ...,
        description="Bank transaction UUID to match",
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Transaction description for the new ledger entry",
    )
    debit_account_id: uuid.UUID = Field(
        ...,
        description="Account UUID for the debit side",
    )
    credit_account_id: uuid.UUID = Field(
        ...,
        description="Account UUID for the credit side",
    )
    amount: int = Field(
        ...,
        gt=0,
        description="Transaction amount in pence (positive)",
    )
    vat_rate: Optional[str] = Field(
        default=None,
        description="Optional VAT rate: 20%, 5%, 0%, or exempt",
    )


class ReconciliationSessionResponse(BaseModel):
    """Schema for reconciliation session responses."""

    id: uuid.UUID
    bank_account_id: uuid.UUID
    start_date: date
    end_date: date
    opening_balance: int
    closing_balance: int
    status: str
    matched_count: int
    unmatched_count: int
    total_bank_lines: int
    created_at: datetime
    closed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReconciliationMatchResponse(BaseModel):
    """Schema for reconciliation match responses."""

    id: uuid.UUID
    session_id: uuid.UUID
    bank_transaction_id: uuid.UUID
    transaction_id: Optional[uuid.UUID] = None
    match_type: str
    amount_difference: int
    description: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReconciliationReport(BaseModel):
    """Schema for reconciliation report."""

    session_id: uuid.UUID
    bank_account_id: uuid.UUID
    start_date: date
    end_date: date
    opening_balance: int
    closing_balance: int
    total_bank_lines: int
    matched_count: int
    unmatched_count: int
    matched_net_amount: int = Field(
        default=0,
        description="Net total of matched bank transaction amounts in pence",
    )
    difference: int = Field(
        default=0,
        description="Difference between opening+matched and closing balance",
    )
    matches: list[ReconciliationMatchResponse] = Field(default_factory=list)
