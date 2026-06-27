"""Pydantic models for Chart of Accounts request/response validation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

Category = Literal["Asset", "Liability", "Equity", "Revenue", "Expense"]
AccountType = Literal[
    "Bank",
    "CurrentAsset",
    "FixedAsset",
    "CurrentLiability",
    "LongTermLiability",
    "Equity",
    "Revenue",
    "DirectCost",
    "Expense",
]
VatRate = Literal["20%", "5%", "0%", "exempt"]


class AccountCreate(BaseModel):
    """Schema for creating a new account."""

    code: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="4-digit account code (e.g. 1000, 5210)",
        examples=["1000", "5210"],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable account name",
        examples=["Bank Current Account"],
    )
    category: Category = Field(
        ...,
        description="Account category: Asset, Liability, Equity, Revenue, or Expense",
    )
    type: AccountType = Field(
        ...,
        description="Account type within its category",
    )
    vat_rate: Optional[VatRate] = Field(
        default=None,
        description="Default VAT rate for transactions posted to this account",
    )
    parent_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Parent account ID for hierarchical grouping (max 2 levels deep)",
    )

    @model_validator(mode="after")
    def validate_code_in_category_range(self) -> "AccountCreate":
        """Ensure the account code falls within the valid range for its category."""
        from src.models.account import CATEGORY_CODE_RANGES, Account

        if not Account.validate_code_for_category(self.code, self.category):
            min_val, max_val = CATEGORY_CODE_RANGES.get(self.category, (0, 0))
            raise ValueError(
                f"Code '{self.code}' is not in valid range {min_val}-{max_val} "
                f"for category '{self.category}'"
            )
        return self


class AccountUpdate(BaseModel):
    """Schema for partial account update. All fields optional."""

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated account name",
    )
    category: Optional[Category] = Field(
        default=None,
        description="Updated category",
    )
    type: Optional[AccountType] = Field(
        default=None,
        description="Updated account type",
    )
    vat_rate: Optional[VatRate] = Field(
        default=None,
        description="Updated VAT rate",
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Enable or disable account (soft delete toggle)",
    )
    parent_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Updated parent account ID",
    )


class VatRateUpdate(BaseModel):
    """Schema for setting the VAT rate on an account."""

    vat_rate: VatRate = Field(
        ...,
        description="VAT rate: one of '20%', '5%', '0%', or 'exempt'",
    )


class AccountResponse(BaseModel):
    """Schema for account responses (all fields)."""

    id: uuid.UUID
    code: str
    name: str
    category: str
    type: str
    vat_rate: Optional[str] = None
    parent_id: Optional[uuid.UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AccountListResponse(BaseModel):
    """Wrapper for listing multiple accounts."""

    accounts: list[AccountResponse]
    total: int
