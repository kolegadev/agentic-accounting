"""Unit tests for Open Banking routes using FastAPI TestClient with mocked service layer."""

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
from src.services.bank_service import BankAccountNotFoundError
from src.services.open_banking_service import (
    AccountNotConnectedError,
    AlreadyConnectedError,
    ProviderNotFoundError,
)
from src.validators.open_banking import (
    ConnectionResponse,
    ConnectionStatusResponse,
    ProviderResponse,
    SyncAllResponse,
    SyncResponse,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ACCOUNT_ID = uuid.uuid4()
CONNECTION_ID = uuid.uuid4()
NOW = "2026-06-27T12:00:00Z"


def make_connection_response(**overrides) -> ConnectionResponse:
    """Build a ConnectionResponse with defaults overridden."""
    defaults = {
        "connection_id": CONNECTION_ID,
        "bank_account_id": ACCOUNT_ID,
        "provider": "test",
        "status": "connected",
        "connected_at": datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc),
        "last_sync_at": None,
        "error_message": None,
    }
    defaults.update(overrides)
    return ConnectionResponse(**defaults)


def make_status_response(**overrides) -> ConnectionStatusResponse:
    """Build a ConnectionStatusResponse with defaults overridden."""
    defaults = {
        "bank_account_id": ACCOUNT_ID,
        "provider": "test",
        "status": "connected",
        "connected_at": datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc),
        "last_sync_at": None,
        "transaction_count": 0,
        "error_message": None,
    }
    defaults.update(overrides)
    return ConnectionStatusResponse(**defaults)


def make_sync_response(**overrides) -> SyncResponse:
    """Build a SyncResponse with defaults overridden."""
    defaults = {
        "account_id": ACCOUNT_ID,
        "imported_count": 15,
        "skipped_count": 0,
        "from_date": date(2026, 6, 1),
        "to_date": date(2026, 6, 27),
    }
    defaults.update(overrides)
    return SyncResponse(**defaults)


def make_sync_all_response(**overrides) -> SyncAllResponse:
    """Build a SyncAllResponse with defaults overridden."""
    defaults = {
        "accounts_synced": 2,
        "total_imported": 30,
        "total_skipped": 0,
        "results": {
            str(ACCOUNT_ID): make_sync_response(),
        },
    }
    defaults.update(overrides)
    return SyncAllResponse(**defaults)


def make_provider_response(name="truelayer") -> ProviderResponse:
    """Build a ProviderResponse."""
    return ProviderResponse(
        name=name,
        display_name=name.title(),
        region="UK",
        description="Test provider",
        is_test=(name == "test"),
    )


@pytest.fixture
def client() -> TestClient:
    """Return a FastAPI TestClient."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /providers — list_providers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_providers_success(client: TestClient) -> None:
    """Should return list of providers."""
    mock_providers = [
        make_provider_response("truelayer"),
        make_provider_response("plaid"),
        make_provider_response("test"),
    ]
    with patch(
        "src.routes.open_banking.OpenBankingService.list_providers",
        return_value=mock_providers,
    ):
        response = client.get("/api/v1/bank/feeds/providers")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["name"] == "truelayer"
    assert data[2]["name"] == "test"
    assert data[2]["is_test"] is True


@pytest.mark.asyncio
async def test_list_providers_empty(client: TestClient) -> None:
    """Should return empty list."""
    with patch(
        "src.routes.open_banking.OpenBankingService.list_providers",
        return_value=[],
    ):
        response = client.get("/api/v1/bank/feeds/providers")

    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# POST /connect — connect_account
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_account_success(client: TestClient) -> None:
    """Should connect account and return 201."""
    with patch(
        "src.routes.open_banking.OpenBankingService.connect_account",
        new_callable=AsyncMock,
    ) as mock_connect:
        mock_connect.return_value = make_connection_response()
        response = client.post(
            "/api/v1/bank/feeds/connect",
            json={
                "bank_account_id": str(ACCOUNT_ID),
                "provider": "test",
                "credentials": {},
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "connected"
    assert data["provider"] == "test"
    assert data["bank_account_id"] == str(ACCOUNT_ID)


@pytest.mark.asyncio
async def test_connect_account_provider_not_found(client: TestClient) -> None:
    """Should return 404 for unknown provider."""
    with patch(
        "src.routes.open_banking.OpenBankingService.connect_account",
        new_callable=AsyncMock,
    ) as mock_connect:
        mock_connect.side_effect = ProviderNotFoundError("nonexistent")
        response = client.post(
            "/api/v1/bank/feeds/connect",
            json={
                "bank_account_id": str(ACCOUNT_ID),
                "provider": "nonexistent",
                "credentials": {},
            },
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_connect_account_already_connected(client: TestClient) -> None:
    """Should return 409 if already connected."""
    with patch(
        "src.routes.open_banking.OpenBankingService.connect_account",
        new_callable=AsyncMock,
    ) as mock_connect:
        mock_connect.side_effect = AlreadyConnectedError(ACCOUNT_ID)
        response = client.post(
            "/api/v1/bank/feeds/connect",
            json={
                "bank_account_id": str(ACCOUNT_ID),
                "provider": "truelayer",
                "credentials": {},
            },
        )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_connect_account_bank_account_not_found(client: TestClient) -> None:
    """Should return 404 if bank account doesn't exist."""
    with patch(
        "src.routes.open_banking.OpenBankingService.connect_account",
        new_callable=AsyncMock,
    ) as mock_connect:
        mock_connect.side_effect = BankAccountNotFoundError(str(ACCOUNT_ID))
        response = client.post(
            "/api/v1/bank/feeds/connect",
            json={
                "bank_account_id": str(ACCOUNT_ID),
                "provider": "test",
                "credentials": {},
            },
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_connect_account_validation_error(client: TestClient) -> None:
    """Should return 422 for invalid body."""
    response = client.post(
        "/api/v1/bank/feeds/connect",
        json={},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /{account_id}/status — get_connection_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_connection_status_success(client: TestClient) -> None:
    """Should return connection status."""
    with patch(
        "src.routes.open_banking.OpenBankingService.get_connection_status",
        new_callable=AsyncMock,
    ) as mock_status:
        mock_status.return_value = make_status_response(transaction_count=42)
        response = client.get(f"/api/v1/bank/feeds/{ACCOUNT_ID}/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"
    assert data["transaction_count"] == 42
    assert data["provider"] == "test"


@pytest.mark.asyncio
async def test_get_connection_status_not_connected(client: TestClient) -> None:
    """Should return 404 if not connected."""
    with patch(
        "src.routes.open_banking.OpenBankingService.get_connection_status",
        new_callable=AsyncMock,
    ) as mock_status:
        mock_status.side_effect = AccountNotConnectedError(ACCOUNT_ID)
        response = client.get(f"/api/v1/bank/feeds/{ACCOUNT_ID}/status")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /{account_id}/sync — sync_account
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_account_success(client: TestClient) -> None:
    """Should sync and return import count."""
    with patch(
        "src.routes.open_banking.OpenBankingService.fetch_transactions",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = 15
        response = client.post(f"/api/v1/bank/feeds/{ACCOUNT_ID}/sync")

    assert response.status_code == 200
    data = response.json()
    assert data["imported_count"] == 15
    assert data["account_id"] == str(ACCOUNT_ID)


@pytest.mark.asyncio
async def test_sync_account_with_date_range(client: TestClient) -> None:
    """Should pass date range parameters."""
    with patch(
        "src.routes.open_banking.OpenBankingService.fetch_transactions",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = 10
        response = client.post(
            f"/api/v1/bank/feeds/{ACCOUNT_ID}/sync?from_date=2026-06-01&to_date=2026-06-27"
        )

    assert response.status_code == 200
    mock_fetch.assert_called_once()
    kwargs = mock_fetch.call_args.kwargs
    assert kwargs["from_date"] == date(2026, 6, 1)
    assert kwargs["to_date"] == date(2026, 6, 27)


@pytest.mark.asyncio
async def test_sync_account_not_connected(client: TestClient) -> None:
    """Should return 404 if not connected."""
    with patch(
        "src.routes.open_banking.OpenBankingService.fetch_transactions",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.side_effect = AccountNotConnectedError(ACCOUNT_ID)
        response = client.post(f"/api/v1/bank/feeds/{ACCOUNT_ID}/sync")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /sync-all — sync_all_accounts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_all_success(client: TestClient) -> None:
    """Should sync all and return summary."""
    with patch(
        "src.routes.open_banking.OpenBankingService.sync_all",
        new_callable=AsyncMock,
    ) as mock_sync_all:
        mock_sync_all.return_value = make_sync_all_response()
        response = client.post("/api/v1/bank/feeds/sync-all")

    assert response.status_code == 200
    data = response.json()
    assert data["accounts_synced"] == 2
    assert data["total_imported"] == 30
    assert str(ACCOUNT_ID) in data["results"]


@pytest.mark.asyncio
async def test_sync_all_no_accounts(client: TestClient) -> None:
    """Should return zero when no accounts connected."""
    with patch(
        "src.routes.open_banking.OpenBankingService.sync_all",
        new_callable=AsyncMock,
    ) as mock_sync_all:
        mock_sync_all.return_value = SyncAllResponse(
            accounts_synced=0,
            total_imported=0,
            total_skipped=0,
            results={},
        )
        response = client.post("/api/v1/bank/feeds/sync-all")

    assert response.status_code == 200
    data = response.json()
    assert data["accounts_synced"] == 0
    assert data["total_imported"] == 0


# ---------------------------------------------------------------------------
# POST /{account_id}/disconnect — disconnect_account
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disconnect_account_success(client: TestClient) -> None:
    """Should disconnect and return 200."""
    with patch(
        "src.routes.open_banking.OpenBankingService.disconnect_account",
        new_callable=AsyncMock,
    ) as mock_disconnect:
        mock_disconnect.return_value = make_connection_response(status="disconnected")
        response = client.post(f"/api/v1/bank/feeds/{ACCOUNT_ID}/disconnect")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "disconnected"


@pytest.mark.asyncio
async def test_disconnect_account_not_connected(client: TestClient) -> None:
    """Should return 404 if not connected."""
    with patch(
        "src.routes.open_banking.OpenBankingService.disconnect_account",
        new_callable=AsyncMock,
    ) as mock_disconnect:
        mock_disconnect.side_effect = AccountNotConnectedError(ACCOUNT_ID)
        response = client.post(f"/api/v1/bank/feeds/{ACCOUNT_ID}/disconnect")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def test_health_check(client: TestClient) -> None:
    """Should return ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
