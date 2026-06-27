"""Test configuration and shared fixtures."""

import os
import uuid
from datetime import datetime, timezone

import pytest

# Set a dummy DATABASE_URL BEFORE any model imports so the database module
# sees it at import time. Tests that mock the service layer never actually connect.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/test_db",
)

from src.models.account import Account

NOW = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_account() -> Account:
    """Return an Account instance with sample data."""
    return Account(
        id=uuid.uuid4(),
        code="1000",
        name="Bank Current Account",
        category="Asset",
        type="Bank",
        vat_rate=None,
        parent_id=None,
        is_active=True,
    )


@pytest.fixture
def sample_account_dict() -> dict:
    """Return sample account data as a dict for API requests."""
    return {
        "code": "5210",
        "name": "Marketing Expenses",
        "category": "Expense",
        "type": "Expense",
        "vat_rate": "20%",
    }


@pytest.fixture
def sample_account_response_dict() -> dict:
    """Return sample account response data as a dict."""
    return {
        "id": str(uuid.uuid4()),
        "code": "1000",
        "name": "Bank Current Account",
        "category": "Asset",
        "type": "Bank",
        "vat_rate": None,
        "parent_id": None,
        "is_active": True,
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
    }
