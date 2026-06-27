"""Pydantic schemas for Transaction, Posting, and VATLine request/response validation."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# PostingCreate
# ---------------------------------------------------------------------------

class PostingCreate(BaseModel):
    """Schema for creating a single posting line within a transaction."""

    account_id: uuid.UUID = Field(
        ...,
        description="Chart of Accounts account UUID",
    )
    debit_amount: int = Field(
        default=0,
        ge=0,
        description="Debit amount in pence (must be >= 0)",
    )
    credit_amount: int = Field(
        default=0,
        ge=0,
        description="Credit amount in pence (must be >= 0)",
    )
    description: Optional[str] = Field(
        default=None,
        description="Line-level narrative",
    )

    @model_validator(mode="after")
    def exactly_one_positive(self) -> "PostingCreate":
        """Ensure exactly one of debit_amount or credit_amount is > 0."""
        debit_positive = self.debit_amount > 0
        credit_positive = self.credit_amount > 0
        if debit_positive == credit_positive:
            raise ValueError(
                "Each posting must have exactly one of debit_amount or credit_amount > 0"
            )
        return self


# ---------------------------------------------------------------------------
# TransactionCreate
# ---------------------------------------------------------------------------

class TransactionCreate(BaseModel):
    """Schema for creating a new journal entry transaction (draft)."""

    description: str = Field(
        ...,
        min_length=1,
        description="Human-readable transaction description",
    )
    contact_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional contact reference (Module 6)",
    )
    currency: str = Field(
        default="GBP",
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code, defaults to GBP",
    )
    effective_date: Optional[date] = Field(
        default=None,
        description="Business date for this transaction",
    )
    postings: list[PostingCreate] = Field(
        ...,
        min_length=2,
        description="At least 2 posting lines (double-entry)",
    )
    idempotency_key: uuid.UUID = Field(
        ...,
        description="Client-generated UUID to prevent duplicate transactions",
    )

    @model_validator(mode="after")
    def balanced_transaction(self) -> "TransactionCreate":
        """Validate sum-to-zero: total debits must equal total credits and > 0."""
        total_debits = sum(p.debit_amount for p in self.postings)
        total_credits = sum(p.credit_amount for p in self.postings)

        if total_debits == 0 and total_credits == 0:
            raise ValueError("Transaction must have at least one positive amount")

        if total_debits != total_credits:
            raise ValueError(
                f"Transaction is unbalanced: total debits {total_debits} != "
                f"total credits {total_credits} (in pence)"
            )

        return self


# ---------------------------------------------------------------------------
# PostingResponse
# ---------------------------------------------------------------------------

class PostingResponse(BaseModel):
    """Schema for posting responses including account details."""

    id: uuid.UUID
    transaction_id: uuid.UUID
    account_id: uuid.UUID
    account_code: Optional[str] = None
    account_name: Optional[str] = None
    debit_amount: int
    credit_amount: int
    description: Optional[str] = None
    vat_lines: list["VATLineResponse"] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# VATLineResponse
# ---------------------------------------------------------------------------

class VATLineResponse(BaseModel):
    """Schema for VAT line responses."""

    id: uuid.UUID
    posting_id: uuid.UUID
    vat_rate: str
    vat_amount: int
    net_amount: int
    vat_type: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# TransactionResponse
# ---------------------------------------------------------------------------

class TransactionResponse(BaseModel):
    """Schema for transaction responses including all postings."""

    id: uuid.UUID
    reference: Optional[str] = None
    description: Optional[str] = None
    contact_id: Optional[uuid.UUID] = None
    total_amount: Optional[int] = None
    currency: str
    status: str
    effective_date: Optional[date] = None
    idempotency_key: Optional[uuid.UUID] = None
    recorded_at: Optional[datetime] = None
    postings: list[PostingResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# TransactionListResponse
# ---------------------------------------------------------------------------

class TransactionListResponse(BaseModel):
    """Wrapper for listing multiple transactions."""

    transactions: list[TransactionResponse]
    total: int
