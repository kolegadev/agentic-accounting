"""Pydantic schemas for Open Banking Feed request/response validation."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class ConnectAccountRequest(BaseModel):
    """Schema for connecting a bank account to an Open Banking provider."""

    bank_account_id: uuid.UUID = Field(
        ...,
        description="UUID of the bank account to connect",
    )
    provider: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Open Banking provider name (truelayer, plaid, saltedge, yodlee, test)",
        examples=["truelayer"],
    )
    credentials: dict = Field(
        default_factory=dict,
        description="Provider-specific credentials (API keys, tokens, consent IDs)",
    )


class ConnectionResponse(BaseModel):
    """Schema for connection details after linking an account."""

    connection_id: uuid.UUID = Field(
        ...,
        description="Unique connection identifier",
    )
    bank_account_id: uuid.UUID
    provider: str
    status: str = Field(
        ...,
        description="Connection status: connected, pending, error, disconnected",
    )
    connected_at: datetime
    last_sync_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ConnectionStatusResponse(BaseModel):
    """Schema for connection status query results."""

    bank_account_id: uuid.UUID
    provider: str
    status: str
    connected_at: datetime
    last_sync_at: Optional[datetime] = None
    transaction_count: int = Field(
        default=0,
        description="Total transactions imported via this feed",
    )
    error_message: Optional[str] = None


class ProviderResponse(BaseModel):
    """Schema for available Open Banking provider listing."""

    name: str = Field(
        ...,
        description="Provider machine name",
    )
    display_name: str = Field(
        ...,
        description="Human-readable provider name",
    )
    region: str = Field(
        default="UK",
        description="Primary region (UK, EU, US, Global)",
    )
    description: str
    is_test: bool = Field(
        default=False,
        description="Whether this is a test/sandbox provider",
    )


class SyncResponse(BaseModel):
    """Schema for single-account sync result."""

    account_id: uuid.UUID
    imported_count: int = Field(
        default=0,
        description="Number of new transactions imported",
    )
    skipped_count: int = Field(
        default=0,
        description="Number of duplicate transactions skipped",
    )
    from_date: Optional[date] = None
    to_date: Optional[date] = None


class SyncAllResponse(BaseModel):
    """Schema for sync-all result across all connected accounts."""

    accounts_synced: int = Field(
        default=0,
        description="Number of accounts synced",
    )
    total_imported: int = Field(
        default=0,
        description="Total transactions imported across all accounts",
    )
    total_skipped: int = Field(
        default=0,
        description="Total duplicates skipped across all accounts",
    )
    results: dict[str, SyncResponse] = Field(
        default_factory=dict,
        description="Per-account sync results keyed by account UUID",
    )
