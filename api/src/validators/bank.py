"""Pydantic schemas for Bank Statement Import request/response validation."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class BankAccountCreate(BaseModel):
    """Schema for creating a new bank account."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable bank account name",
        examples=["Barclays Business Current"],
    )
    sort_code: Optional[str] = Field(
        default=None,
        max_length=10,
        description="UK sort code (XX-XX-XX format)",
    )
    account_number: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Bank account number",
    )
    iban: Optional[str] = Field(
        default=None,
        max_length=34,
        description="International Bank Account Number",
    )
    currency: str = Field(
        default="GBP",
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code",
    )
    opening_balance: int = Field(
        default=0,
        description="Opening balance in pence",
    )


class BankAccountResponse(BaseModel):
    """Schema for bank account responses (all fields)."""

    id: uuid.UUID
    name: str
    sort_code: Optional[str] = None
    account_number: Optional[str] = None
    iban: Optional[str] = None
    currency: str
    opening_balance: int
    current_balance: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BankTransactionResponse(BaseModel):
    """Schema for bank transaction responses."""

    id: uuid.UUID
    bank_account_id: uuid.UUID
    bank_account_name: Optional[str] = None
    date: date
    description: str
    amount: int
    reference: Optional[str] = None
    type: Optional[str] = None
    fitid: Optional[str] = None
    import_hash: Optional[str] = None
    status: str
    matched_transaction_id: Optional[uuid.UUID] = None
    contact_id: Optional[uuid.UUID] = None
    category: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BankImportResult(BaseModel):
    """Result of a bank statement import operation."""

    imported_count: int = Field(
        default=0,
        description="Number of new transactions created",
    )
    skipped_count: int = Field(
        default=0,
        description="Number of duplicate transactions skipped",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="List of error messages for failed rows",
    )


class CategorizeTransaction(BaseModel):
    """Schema for categorizing a bank transaction."""

    contact_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional contact to associate",
    )
    category: Optional[str] = Field(
        default=None,
        max_length=100,
        description="User-assigned category label",
    )
