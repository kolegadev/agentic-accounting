"""Test configuration and shared fixtures."""

import os
import uuid
from datetime import datetime, timezone

import pytest

# Set DATABASE_URL in environ BEFORE any imports from src.config.database.
# The get_engine() function reads directly from os.environ at call time
# (not at module-import time), so this works for all test files.
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test_db"

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
        created_at=NOW,
        updated_at=NOW,
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
