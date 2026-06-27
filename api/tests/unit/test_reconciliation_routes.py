"""Unit tests for Reconciliation routes using FastAPI TestClient with mocked service layer."""

from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure DATABASE_URL is set before src.config.database is imported
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test_db"

import src.config.database as _db_mod
_db_mod.DATABASE_URL = os.environ["DATABASE_URL"]

from src.index import app
from src.services.reconciliation_service import (
    ReconciliationServiceError,
    SessionClosedError,
    SessionNotFoundError,
    BankAccountNotFoundError,
    BankTransactionAlreadyMatchedError,
    BankTransactionNotFoundError,
    TransactionNotFoundError,
)
from src.validators.reconciliation import (
    ReconciliationMatchResponse,
    ReconciliationReport,
    ReconciliationSessionResponse,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SESSION_ID = uuid.uuid4()
BANK_ACCOUNT_ID = uuid.uuid4()
BANK_TRANSACTION_ID = uuid.uuid4()
TRANSACTION_ID = uuid.uuid4()
TRANSACTION_ID_2 = uuid.uuid4()
MATCH_ID = uuid.uuid4()
NOW = "2026-06-27T12:00:00Z"


def make_session_response(**overrides) -> ReconciliationSessionResponse:
    """Build a ReconciliationSessionResponse with defaults."""
    defaults = {
        "id": SESSION_ID,
        "bank_account_id": BANK_ACCOUNT_ID,
        "start_date": date(2026, 6, 1),
        "end_date": date(2026, 6, 30),
        "opening_balance": 100000,
        "closing_balance": 350000,
        "status": "open",
        "matched_count": 3,
        "unmatched_count": 2,
        "total_bank_lines": 5,
        "created_at": datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc),
        "closed_at": None,
    }
    defaults.update(overrides)
    return ReconciliationSessionResponse(**defaults)


def make_match_response(**overrides) -> ReconciliationMatchResponse:
    """Build a ReconciliationMatchResponse with defaults."""
    defaults = {
        "id": MATCH_ID,
        "session_id": SESSION_ID,
        "bank_transaction_id": BANK_TRANSACTION_ID,
        "transaction_id": TRANSACTION_ID,
        "match_type": "one_to_one",
        "amount_difference": 0,
        "description": None,
        "created_at": datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return ReconciliationMatchResponse(**defaults)


def make_report(**overrides) -> ReconciliationReport:
    """Build a ReconciliationReport with defaults."""
    defaults = {
        "session_id": SESSION_ID,
        "bank_account_id": BANK_ACCOUNT_ID,
        "start_date": date(2026, 6, 1),
        "end_date": date(2026, 6, 30),
        "opening_balance": 100000,
        "closing_balance": 350000,
        "total_bank_lines": 5,
        "matched_count": 3,
        "unmatched_count": 2,
        "matched_net_amount": 250000,
        "difference": 0,
        "matches": [],
    }
    defaults.update(overrides)
    return ReconciliationReport(**defaults)


@pytest.fixture
def client() -> TestClient:
    """Return a FastAPI TestClient."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /start — start_session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_session_success(client: TestClient) -> None:
    """Should start a reconciliation session and return 201."""
    with patch(
        "src.routes.reconciliation.ReconciliationService.start_session",
        new_callable=AsyncMock,
    ) as mock_start:
        mock_start.return_value = make_session_response()
        response = client.post(
            "/api/v1/reconciliation/start",
            json={
                "bank_account_id": str(BANK_ACCOUNT_ID),
                "start_date": "2026-06-01",
                "end_date": "2026-06-30",
                "opening_balance": 100000,
                "closing_balance": 350000,
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "open"
    assert data["total_bank_lines"] == 5
    mock_start.assert_called_once()


@pytest.mark.asyncio
async def test_start_session_bank_account_not_found(client: TestClient) -> None:
    """Should return 404 when bank account not found."""
    with patch(
        "src.routes.reconciliation.ReconciliationService.start_session",
        new_callable=AsyncMock,
    ) as mock_start:
        mock_start.side_effect = BankAccountNotFoundError(uuid.uuid4())
        response = client.post(
            "/api/v1/reconciliation/start",
            json={
                "bank_account_id": str(uuid.uuid4()),
                "start_date": "2026-06-01",
                "end_date": "2026-06-30",
                "opening_balance": 0,
                "closing_balance": 0,
            },
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_start_session_validation_error(client: TestClient) -> None:
    """Should return 422 for invalid request body."""
    response = client.post(
        "/api/v1/reconciliation/start",
        json={},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /{session_id}/match — match_one_to_one
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_match_one_to_one_success(client: TestClient) -> None:
    """Should create a one-to-one match and return 200."""
    with patch(
        "src.routes.reconciliation.ReconciliationService.match_one_to_one",
        new_callable=AsyncMock,
    ) as mock_match:
        mock_match.return_value = make_match_response()
        response = client.post(
            f"/api/v1/reconciliation/{SESSION_ID}/match",
            json={
                "bank_transaction_id": str(BANK_TRANSACTION_ID),
                "transaction_ids": [str(TRANSACTION_ID)],
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["match_type"] == "one_to_one"
    assert data["amount_difference"] == 0


@pytest.mark.asyncio
async def test_match_one_to_one_multiple_ids_error(client: TestClient) -> None:
    """Should return 422 when multiple transaction_ids sent to match endpoint."""
    response = client.post(
        f"/api/v1/reconciliation/{SESSION_ID}/match",
        json={
            "bank_transaction_id": str(BANK_TRANSACTION_ID),
            "transaction_ids": [str(TRANSACTION_ID), str(TRANSACTION_ID_2)],
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_match_one_to_one_session_not_found(client: TestClient) -> None:
    """Should return 404 when session not found."""
    with patch(
        "src.routes.reconciliation.ReconciliationService.match_one_to_one",
        new_callable=AsyncMock,
    ) as mock_match:
        mock_match.side_effect = SessionNotFoundError(uuid.uuid4())
        response = client.post(
            f"/api/v1/reconciliation/{uuid.uuid4()}/match",
            json={
                "bank_transaction_id": str(BANK_TRANSACTION_ID),
                "transaction_ids": [str(TRANSACTION_ID)],
            },
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_match_one_to_one_bank_tx_not_found(client: TestClient) -> None:
    """Should return 404 when bank transaction not found."""
    with patch(
        "src.routes.reconciliation.ReconciliationService.match_one_to_one",
        new_callable=AsyncMock,
    ) as mock_match:
        mock_match.side_effect = BankTransactionNotFoundError(uuid.uuid4())
        response = client.post(
            f"/api/v1/reconciliation/{SESSION_ID}/match",
            json={
                "bank_transaction_id": str(uuid.uuid4()),
                "transaction_ids": [str(TRANSACTION_ID)],
            },
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_match_one_to_one_already_reconciled(client: TestClient) -> None:
    """Should return 422 when bank tx already reconciled."""
    with patch(
        "src.routes.reconciliation.ReconciliationService.match_one_to_one",
        new_callable=AsyncMock,
    ) as mock_match:
        mock_match.side_effect = BankTransactionAlreadyMatchedError(uuid.uuid4())
        response = client.post(
            f"/api/v1/reconciliation/{SESSION_ID}/match",
            json={
                "bank_transaction_id": str(BANK_TRANSACTION_ID),
                "transaction_ids": [str(TRANSACTION_ID)],
            },
        )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /{session_id}/match-many — match_one_to_many
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_match_many_success(client: TestClient) -> None:
    """Should create one-to-many matches and return 200."""
    with patch(
        "src.routes.reconciliation.ReconciliationService.match_one_to_many",
        new_callable=AsyncMock,
    ) as mock_match:
        mock_match.return_value = [
            make_match_response(match_type="one_to_many"),
            make_match_response(
                id=uuid.uuid4(), transaction_id=TRANSACTION_ID_2, match_type="one_to_many"
            ),
        ]
        response = client.post(
            f"/api/v1/reconciliation/{SESSION_ID}/match-many",
            json={
                "bank_transaction_id": str(BANK_TRANSACTION_ID),
                "transaction_ids": [str(TRANSACTION_ID), str(TRANSACTION_ID_2)],
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["match_type"] == "one_to_many"
    mock_match.assert_called_once()


@pytest.mark.asyncio
async def test_match_many_session_closed(client: TestClient) -> None:
    """Should return 422 when session closed."""
    with patch(
        "src.routes.reconciliation.ReconciliationService.match_one_to_many",
        new_callable=AsyncMock,
    ) as mock_match:
        mock_match.side_effect = SessionClosedError(SESSION_ID)
        response = client.post(
            f"/api/v1/reconciliation/{SESSION_ID}/match-many",
            json={
                "bank_transaction_id": str(BANK_TRANSACTION_ID),
                "transaction_ids": [str(TRANSACTION_ID)],
            },
        )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /{session_id}/create-and-match — create_and_match
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_and_match_success(client: TestClient) -> None:
    """Should create a new transaction and match it, return 201."""
    with patch(
        "src.routes.reconciliation.ReconciliationService.create_and_match",
        new_callable=AsyncMock,
    ) as mock_cam:
        mock_cam.return_value = make_match_response(match_type="new_entry")
        response = client.post(
            f"/api/v1/reconciliation/{SESSION_ID}/create-and-match",
            json={
                "bank_transaction_id": str(BANK_TRANSACTION_ID),
                "description": "Office Supplies Payment",
                "debit_account_id": str(uuid.uuid4()),
                "credit_account_id": str(uuid.uuid4()),
                "amount": 5000,
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["match_type"] == "new_entry"
    mock_cam.assert_called_once()


@pytest.mark.asyncio
async def test_create_and_match_session_not_found(client: TestClient) -> None:
    """Should return 404."""
    with patch(
        "src.routes.reconciliation.ReconciliationService.create_and_match",
        new_callable=AsyncMock,
    ) as mock_cam:
        mock_cam.side_effect = SessionNotFoundError(uuid.uuid4())
        response = client.post(
            f"/api/v1/reconciliation/{uuid.uuid4()}/create-and-match",
            json={
                "bank_transaction_id": str(BANK_TRANSACTION_ID),
                "description": "Test",
                "debit_account_id": str(uuid.uuid4()),
                "credit_account_id": str(uuid.uuid4()),
                "amount": 100,
            },
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_and_match_validation_error(client: TestClient) -> None:
    """Should return 422 for invalid request body."""
    response = client.post(
        f"/api/v1/reconciliation/{SESSION_ID}/create-and-match",
        json={"bank_transaction_id": str(BANK_TRANSACTION_ID)},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /{session_id}/status — get_session_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_status_success(client: TestClient) -> None:
    """Should return session status."""
    with patch(
        "src.routes.reconciliation.ReconciliationService.get_session_status",
        new_callable=AsyncMock,
    ) as mock_status:
        mock_status.return_value = make_session_response()
        response = client.get(f"/api/v1/reconciliation/{SESSION_ID}/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "open"
    assert data["matched_count"] == 3
    assert data["unmatched_count"] == 2


@pytest.mark.asyncio
async def test_get_status_not_found(client: TestClient) -> None:
    """Should return 404."""
    with patch(
        "src.routes.reconciliation.ReconciliationService.get_session_status",
        new_callable=AsyncMock,
    ) as mock_status:
        mock_status.side_effect = SessionNotFoundError(uuid.uuid4())
        response = client.get(f"/api/v1/reconciliation/{uuid.uuid4()}/status")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /{session_id}/close — close_session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_session_success(client: TestClient) -> None:
    """Should close session and return 200."""
    with patch(
        "src.routes.reconciliation.ReconciliationService.close_session",
        new_callable=AsyncMock,
    ) as mock_close:
        mock_close.return_value = make_session_response(status="closed", closed_at=datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc))
        response = client.post(f"/api/v1/reconciliation/{SESSION_ID}/close")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "closed"
    mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_close_session_already_closed(client: TestClient) -> None:
    """Should return 422."""
    with patch(
        "src.routes.reconciliation.ReconciliationService.close_session",
        new_callable=AsyncMock,
    ) as mock_close:
        mock_close.side_effect = SessionClosedError(SESSION_ID)
        response = client.post(f"/api/v1/reconciliation/{SESSION_ID}/close")

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /{session_id}/report — get_report
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_report_success(client: TestClient) -> None:
    """Should return reconciliation report."""
    with patch(
        "src.routes.reconciliation.ReconciliationService.generate_report",
        new_callable=AsyncMock,
    ) as mock_report:
        mock_report.return_value = make_report()
        response = client.get(f"/api/v1/reconciliation/{SESSION_ID}/report")

    assert response.status_code == 200
    data = response.json()
    assert data["opening_balance"] == 100000
    assert data["closing_balance"] == 350000
    assert data["matched_count"] == 3
    assert data["difference"] == 0


@pytest.mark.asyncio
async def test_get_report_session_not_found(client: TestClient) -> None:
    """Should return 404."""
    with patch(
        "src.routes.reconciliation.ReconciliationService.generate_report",
        new_callable=AsyncMock,
    ) as mock_report:
        mock_report.side_effect = SessionNotFoundError(uuid.uuid4())
        response = client.get(f"/api/v1/reconciliation/{uuid.uuid4()}/report")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def test_health_check(client: TestClient) -> None:
    """Should return ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
