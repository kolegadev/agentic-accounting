"""Pydantic schemas for Bank Rules Engine request/response validation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

VALID_CONDITION_FIELDS = ("description", "amount", "reference")
VALID_CONDITION_OPERATORS = ("contains", "equals", "starts_with", "regex", "greater_than", "less_than")
VALID_ACTION_TYPES = ("set_category", "set_contact", "set_account")


class BankRuleCreate(BaseModel):
    """Schema for creating a new bank rule."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable rule name",
        examples=["TESCO → Groceries"],
    )
    condition_field: str = Field(
        ...,
        description="Field to test: description, amount, reference",
    )
    condition_operator: str = Field(
        ...,
        description="Operator: contains, equals, starts_with, regex, greater_than, less_than",
    )
    condition_value: str = Field(
        ...,
        min_length=1,
        description="Value to compare against",
    )
    action_type: str = Field(
        ...,
        description="Action: set_category, set_contact, set_account",
    )
    action_value: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Target value (category name, contact name, or account code)",
    )
    priority: int = Field(
        default=1000,
        ge=0,
        description="Lower = higher priority",
    )
    is_active: bool = Field(
        default=True,
        description="Whether this rule is currently active",
    )


class BankRuleUpdate(BaseModel):
    """Schema for updating an existing bank rule (all fields optional)."""

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Human-readable rule name",
    )
    condition_field: Optional[str] = Field(
        default=None,
        description="Field to test: description, amount, reference",
    )
    condition_operator: Optional[str] = Field(
        default=None,
        description="Operator: contains, equals, starts_with, regex, greater_than, less_than",
    )
    condition_value: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Value to compare against",
    )
    action_type: Optional[str] = Field(
        default=None,
        description="Action: set_category, set_contact, set_account",
    )
    action_value: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Target value (category name, contact name, or account code)",
    )
    priority: Optional[int] = Field(
        default=None,
        ge=0,
        description="Lower = higher priority",
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Whether this rule is currently active",
    )


class BankRuleResponse(BaseModel):
    """Schema for bank rule responses."""

    id: uuid.UUID
    name: str
    condition_field: str
    condition_operator: str
    condition_value: str
    action_type: str
    action_value: str
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BankRuleApplyResponse(BaseModel):
    """Result of applying rules to pending transactions."""

    categorized_count: int = Field(
        default=0,
        description="Number of transactions categorized",
    )


class BankRuleLoadDefaultsResponse(BaseModel):
    """Result of loading default rules from JSON template."""

    created_count: int = Field(
        default=0,
        description="Number of rules created from defaults",
    )
    skipped_count: int = Field(
        default=0,
        description="Number of rules skipped (already exist)",
    )
