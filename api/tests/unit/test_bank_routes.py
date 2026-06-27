"""Unit tests for Bank routes using FastAPI TestClient with mocked service layer."""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure DATABASE_URL is set before src.config.database is imported
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test_db"

# If src.config.database is already cached, patch its DATABASE_URL
import src.config.database as _db_mod
_db_mod.DATABASE_URL = os.environ["DATABASE_URL"]

from src.index import app
from src.services.bank_service import (
    BankAccountNotFoundError,
    BankServiceError,
    BankTransactionNotFoundError,
)
from src.validators.bank import BankAccountResponse, BankImportResult, BankTransactionResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ACCOUNT_ID = uuid.uuid4()
TRANSACTION_ID = uuid.uuid4()
NOW = "2026-06-27T12:00:00Z"


def make_account_response(**overrides) -> BankAccountResponse:
    """Build a BankAccountResponse with defaults overridden."""
    defaults = {
        "id": ACCOUNT_ID,
        "name": "Test Business Account",
        "sort_code": "20-00-00",
        "account_number": "12345678",
        "iban": None,
        "currency": "GBP",
        "opening_balance": 100000,
        "current_balance": 100000,
        "is_active": True,
        "created_at": datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return BankAccountResponse(**defaults)


def make_transaction_response(**overrides) -> BankTransactionResponse:
    """Build a BankTransactionResponse with defaults overridden."""
    defaults = {
        "id": TRANSACTION_ID,
        "bank_account_id": ACCOUNT_ID,
        "bank_account_name": "Test Business Account",
        "date": date(2026, 6, 1),
        "description": "Test payment",
        "amount": -5000,
        "reference": "REF001",
        "type": "DD",
        "fitid": None,
        "import_hash": "abc123",
        "status": "imported",
        "matched_transaction_id": None,
        "contact_id": None,
        "category": None,
        "created_at": datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return BankTransactionResponse(**defaults)


def make_import_result(**overrides) -> BankImportResult:
    """Build a BankImportResult."""
    defaults = {
        "imported_count": 5,
        "skipped_count": 2,
        "errors": [],
    }
    defaults.update(overrides)
    return BankImportResult(**defaults)


@pytest.fixture
def client() -> TestClient:
    """Return a FastAPI TestClient."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /accounts — create_account
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_account_success(client: TestClient) -> None:
    """Should create bank account and return 201."""
    with patch(
        "src.routes.bank.BankService.create_account",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = make_account_response()
        response = client.post(
            "/api/v1/bank/accounts",
            json={"name": "Test Account"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Business Account"
    assert data["currency"] == "GBP"


@pytest.mark.asyncio
async def test_create_account_validation_error(client: TestClient) -> None:
    """Should return 422 for invalid body."""
    response = client.post(
        "/api/v1/bank/accounts",
        json={},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /accounts — list_accounts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_accounts_success(client: TestClient) -> None:
    """Should return list of accounts."""
    with patch(
        "src.routes.bank.BankService.list_accounts",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = [make_account_response()]
        response = client.get("/api/v1/bank/accounts")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Test Business Account"


@pytest.mark.asyncio
async def test_list_accounts_with_inactive(client: TestClient) -> None:
    """Should pass include_inactive param."""
    with patch(
        "src.routes.bank.BankService.list_accounts",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = []
        response = client.get("/api/v1/bank/accounts?include_inactive=true")

    assert response.status_code == 200
    mock_list.assert_called_once()


@pytest.mark.asyncio
async def test_list_accounts_empty(client: TestClient) -> None:
    """Should return empty list."""
    with patch(
        "src.routes.bank.BankService.list_accounts",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = []
        response = client.get("/api/v1/bank/accounts")

    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# GET /accounts/{id} — get_account
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_account_found(client: TestClient) -> None:
    """Should return account when found."""
    with patch(
        "src.routes.bank.BankService.get_account",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = make_account_response()
        response = client.get(f"/api/v1/bank/accounts/{ACCOUNT_ID}")

    assert response.status_code == 200
    assert response.json()["id"] == str(ACCOUNT_ID)


@pytest.mark.asyncio
async def test_get_account_not_found(client: TestClient) -> None:
    """Should return 404."""
    with patch(
        "src.routes.bank.BankService.get_account",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = None
        response = client.get(f"/api/v1/bank/accounts/{uuid.uuid4()}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /import/csv — import_csv
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_csv_success(client: TestClient) -> None:
    """Should import CSV and return result."""
    with patch(
        "src.routes.bank.BankService.import_csv",
        new_callable=AsyncMock,
    ) as mock_import:
        mock_import.return_value = make_import_result()
        response = client.post(
            f"/api/v1/bank/import/csv?account_id={ACCOUNT_ID}",
            files={"file": ("test.csv", b"Date,Description,Amount\n01/06/2026,Test,100\n", "text/csv")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["imported_count"] == 5
    assert data["skipped_count"] == 2


@pytest.mark.asyncio
async def test_import_csv_with_template(client: TestClient) -> None:
    """Should import CSV with template."""
    with patch(
        "src.routes.bank.BankService.import_csv",
        new_callable=AsyncMock,
    ) as mock_import:
        mock_import.return_value = make_import_result(imported_count=3, skipped_count=0)
        response = client.post(
            f"/api/v1/bank/import/csv?account_id={ACCOUNT_ID}&template=barclays",
            files={"file": ("test.csv", b"Date,Description,Amount\n01/06/2026,Test,100\n", "text/csv")},
        )

    assert response.status_code == 200
    mock_import.assert_called_once()
    kwargs = mock_import.call_args.kwargs
    assert kwargs["template_name"] == "barclays"


@pytest.mark.asyncio
async def test_import_csv_account_not_found(client: TestClient) -> None:
    """Should return 404 when account not found."""
    with patch(
        "src.routes.bank.BankService.import_csv",
        new_callable=AsyncMock,
    ) as mock_import:
        mock_import.side_effect = BankAccountNotFoundError(str(uuid.uuid4()))
        response = client.post(
            f"/api/v1/bank/import/csv?account_id={uuid.uuid4()}",
            files={"file": ("test.csv", b"date,desc,amt\n", "text/csv")},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_import_csv_parse_error(client: TestClient) -> None:
    """Should return 422 for CSV parse error."""
    with patch(
        "src.routes.bank.BankService.import_csv",
        new_callable=AsyncMock,
    ) as mock_import:
        mock_import.side_effect = BankServiceError("No date column found", status_code=422)
        response = client.post(
            f"/api/v1/bank/import/csv?account_id={ACCOUNT_ID}",
            files={"file": ("test.csv", b"col1,col2\nval1,val2\n", "text/csv")},
        )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /import/ofx — import_ofx
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_ofx_success(client: TestClient) -> None:
    """Should import OFX and return result."""
    with patch(
        "src.routes.bank.BankService.import_ofx",
        new_callable=AsyncMock,
    ) as mock_import:
        mock_import.return_value = make_import_result(imported_count=10, skipped_count=0)
        response = client.post(
            f"/api/v1/bank/import/ofx?account_id={ACCOUNT_ID}",
            files={"file": ("test.ofx", b"OFXHEADER:100\n...", "application/x-ofx")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["imported_count"] == 10


@pytest.mark.asyncio
async def test_import_ofx_account_not_found(client: TestClient) -> None:
    """Should return 404."""
    with patch(
        "src.routes.bank.BankService.import_ofx",
        new_callable=AsyncMock,
    ) as mock_import:
        mock_import.side_effect = BankAccountNotFoundError(str(uuid.uuid4()))
        response = client.post(
            f"/api/v1/bank/import/ofx?account_id={uuid.uuid4()}",
            files={"file": ("test.ofx", b"dummy", "application/x-ofx")},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_import_ofx_parse_error(client: TestClient) -> None:
    """Should return 422 for OFX parse error."""
    with patch(
        "src.routes.bank.BankService.import_ofx",
        new_callable=AsyncMock,
    ) as mock_import:
        mock_import.side_effect = BankServiceError("Invalid OFX", status_code=422)
        response = client.post(
            f"/api/v1/bank/import/ofx?account_id={ACCOUNT_ID}",
            files={"file": ("test.ofx", b"not-ofx", "application/x-ofx")},
        )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /transactions — list_transactions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_transactions_success(client: TestClient) -> None:
    """Should list transactions."""
    with patch(
        "src.routes.bank.BankService.list_transactions",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([make_transaction_response()], 1)
        response = client.get(f"/api/v1/bank/transactions?account_id={ACCOUNT_ID}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["description"] == "Test payment"


@pytest.mark.asyncio
async def test_list_transactions_with_filters(client: TestClient) -> None:
    """Should filter by status and date range."""
    with patch(
        "src.routes.bank.BankService.list_transactions",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([], 0)
        response = client.get(
            f"/api/v1/bank/transactions?account_id={ACCOUNT_ID}"
            "&status=imported&date_from=2026-01-01&date_to=2026-12-31&limit=10&offset=0"
        )

    assert response.status_code == 200
    mock_list.assert_called_once()
    kwargs = mock_list.call_args.kwargs
    assert kwargs["status"] == "imported"
    assert kwargs["date_from"] == date(2026, 1, 1)
    assert kwargs["date_to"] == date(2026, 12, 31)


@pytest.mark.asyncio
async def test_list_transactions_empty(client: TestClient) -> None:
    """Should return empty list."""
    with patch(
        "src.routes.bank.BankService.list_transactions",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([], 0)
        response = client.get(f"/api/v1/bank/transactions?account_id={ACCOUNT_ID}")

    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# PATCH /transactions/{id}/categorize — categorize_transaction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_categorize_transaction_success(client: TestClient) -> None:
    """Should categorize and return 200."""
    with patch(
        "src.routes.bank.BankService.categorize_transaction",
        new_callable=AsyncMock,
    ) as mock_cat:
        mock_cat.return_value = make_transaction_response(
            status="categorized",
            category="Office Expenses",
            contact_id=uuid.uuid4(),
        )
        response = client.patch(
            f"/api/v1/bank/transactions/{TRANSACTION_ID}/categorize",
            json={"category": "Office Expenses"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "categorized"
    assert data["category"] == "Office Expenses"


@pytest.mark.asyncio
async def test_categorize_transaction_not_found(client: TestClient) -> None:
    """Should return 404."""
    with patch(
        "src.routes.bank.BankService.categorize_transaction",
        new_callable=AsyncMock,
    ) as mock_cat:
        mock_cat.side_effect = BankTransactionNotFoundError(str(uuid.uuid4()))
        response = client.patch(
            f"/api/v1/bank/transactions/{uuid.uuid4()}/categorize",
            json={"category": "Test"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_categorize_transaction_contact_only(client: TestClient) -> None:
    """Should categorize with contact only."""
    contact_id = uuid.uuid4()
    with patch(
        "src.routes.bank.BankService.categorize_transaction",
        new_callable=AsyncMock,
    ) as mock_cat:
        mock_cat.return_value = make_transaction_response(
            status="categorized",
            contact_id=contact_id,
        )
        response = client.patch(
            f"/api/v1/bank/transactions/{TRANSACTION_ID}/categorize",
            json={"contact_id": str(contact_id)},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "categorized"


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def test_health_check(client: TestClient) -> None:
    """Should return ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
