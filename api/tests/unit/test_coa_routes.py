"""Unit tests for COA routes using FastAPI TestClient with mocked service layer."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.index import app
from src.services.coa_service import (
    AccountNotFoundError,
    DuplicateCodeError,
    InvalidCodeRangeError,
    TemplateNotFoundError,
)
from src.validators.account import AccountResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ACCOUNT_ID = uuid.uuid4()
ANOTHER_ID = uuid.uuid4()

SAMPLE_ACCOUNT_RESPONSE: dict = {
    "id": str(ACCOUNT_ID),
    "code": "1000",
    "name": "Bank Current Account",
    "category": "Asset",
    "type": "Bank",
    "vat_rate": None,
    "parent_id": None,
    "is_active": True,
    "created_at": "2026-06-27T12:00:00Z",
    "updated_at": "2026-06-27T12:00:00Z",
}


def make_response(**overrides) -> AccountResponse:
    """Build an AccountResponse with defaults overridden."""
    data = SAMPLE_ACCOUNT_RESPONSE.copy()
    data.update(overrides)
    data["id"] = str(data.get("id", ACCOUNT_ID))
    return AccountResponse(**data)


@pytest.fixture
def client() -> TestClient:
    """Return a FastAPI TestClient."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET / — list_accounts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_accounts_success(client: TestClient) -> None:
    """Should return list of active accounts."""
    mock_account = make_response()

    with patch("src.routes.coa.CoaService.list_accounts", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [mock_account]
        response = client.get("/api/v1/coa/")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["accounts"]) == 1
    assert data["accounts"][0]["code"] == "1000"


@pytest.mark.asyncio
async def test_list_accounts_with_inactive(client: TestClient) -> None:
    """Should pass include_inactive param to service."""
    with patch("src.routes.coa.CoaService.list_accounts", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = []
        response = client.get("/api/v1/coa/?include_inactive=true")

    assert response.status_code == 200
    mock_list.assert_called_once()
    args, kwargs = mock_list.call_args
    assert kwargs.get("include_inactive") is True


# ---------------------------------------------------------------------------
# GET /{account_id} — get_account
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_account_success(client: TestClient) -> None:
    """Should return account when found."""
    mock_account = make_response()

    with patch("src.routes.coa.CoaService.get_account", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_account
        response = client.get(f"/api/v1/coa/{ACCOUNT_ID}")

    assert response.status_code == 200
    assert response.json()["id"] == str(ACCOUNT_ID)


@pytest.mark.asyncio
async def test_get_account_not_found(client: TestClient) -> None:
    """Should return 404 for non-existent account."""
    with patch("src.routes.coa.CoaService.get_account", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        response = client.get(f"/api/v1/coa/{uuid.uuid4()}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST / — create_account
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_account_success(client: TestClient) -> None:
    """Should create account and return 201."""
    mock_account = make_response(code="5210", name="Marketing Expenses", category="Expense", type="Expense", vat_rate="20%")

    with patch("src.routes.coa.CoaService.create_account", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_account
        response = client.post("/api/v1/coa/", json={
            "code": "5210",
            "name": "Marketing Expenses",
            "category": "Expense",
            "type": "Expense",
            "vat_rate": "20%",
        })

    assert response.status_code == 201
    assert response.json()["code"] == "5210"


@pytest.mark.asyncio
async def test_create_account_duplicate(client: TestClient) -> None:
    """Should return 409 for duplicate code."""
    with patch("src.routes.coa.CoaService.create_account", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = DuplicateCodeError("1000")
        response = client.post("/api/v1/coa/", json={
            "code": "1000",
            "name": "Bank",
            "category": "Asset",
            "type": "Bank",
        })

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_account_validation_error(client: TestClient) -> None:
    """Should return 422 for invalid request body (missing required fields)."""
    response = client.post("/api/v1/coa/", json={
        "code": "1000",
        # missing name, category, type
    })

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_account_invalid_category(client: TestClient) -> None:
    """Should return 422 for invalid category."""
    response = client.post("/api/v1/coa/", json={
        "code": "1000",
        "name": "Test",
        "category": "InvalidCategory",
        "type": "Bank",
    })

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_account_invalid_vat_rate(client: TestClient) -> None:
    """Should return 422 for invalid VAT rate."""
    response = client.post("/api/v1/coa/", json={
        "code": "1000",
        "name": "Test",
        "category": "Asset",
        "type": "Bank",
        "vat_rate": "15%",  # invalid
    })

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /{account_id} — update_account
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_account_success(client: TestClient) -> None:
    """Should update account and return 200."""
    mock_account = make_response(name="Updated Name")

    with patch("src.routes.coa.CoaService.update_account", new_callable=AsyncMock) as mock_update:
        mock_update.return_value = mock_account
        response = client.patch(f"/api/v1/coa/{ACCOUNT_ID}", json={"name": "Updated Name"})

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_account_not_found(client: TestClient) -> None:
    """Should return 404 for non-existent account."""
    with patch("src.routes.coa.CoaService.update_account", new_callable=AsyncMock) as mock_update:
        mock_update.side_effect = AccountNotFoundError(str(uuid.uuid4()))
        response = client.patch(f"/api/v1/coa/{uuid.uuid4()}", json={"name": "Nope"})

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /{account_id} — soft_delete_account
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_soft_delete_account_success(client: TestClient) -> None:
    """Should soft-delete and return 200 with is_active=False."""
    mock_account = make_response(is_active=False)

    with patch("src.routes.coa.CoaService.soft_delete_account", new_callable=AsyncMock) as mock_delete:
        mock_delete.return_value = mock_account
        response = client.delete(f"/api/v1/coa/{ACCOUNT_ID}")

    assert response.status_code == 200
    assert response.json()["is_active"] is False


@pytest.mark.asyncio
async def test_soft_delete_account_not_found(client: TestClient) -> None:
    """Should return 404 for non-existent account."""
    with patch("src.routes.coa.CoaService.soft_delete_account", new_callable=AsyncMock) as mock_delete:
        mock_delete.side_effect = AccountNotFoundError(str(uuid.uuid4()))
        response = client.delete(f"/api/v1/coa/{uuid.uuid4()}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PUT /{account_id}/vat-rate — set_vat_rate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_set_vat_rate_success(client: TestClient) -> None:
    """Should set VAT rate and return 200."""
    mock_account = make_response(vat_rate="20%")

    with patch("src.routes.coa.CoaService.set_vat_rate", new_callable=AsyncMock) as mock_set:
        mock_set.return_value = mock_account
        response = client.put(f"/api/v1/coa/{ACCOUNT_ID}/vat-rate", json={"vat_rate": "20%"})

    assert response.status_code == 200
    assert response.json()["vat_rate"] == "20%"


@pytest.mark.asyncio
async def test_set_vat_rate_invalid(client: TestClient) -> None:
    """Should return 422 for invalid VAT rate."""
    response = client.put(f"/api/v1/coa/{ACCOUNT_ID}/vat-rate", json={"vat_rate": "50%"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_set_vat_rate_not_found(client: TestClient) -> None:
    """Should return 404 for non-existent account."""
    with patch("src.routes.coa.CoaService.set_vat_rate", new_callable=AsyncMock) as mock_set:
        mock_set.side_effect = AccountNotFoundError(str(uuid.uuid4()))
        response = client.put(f"/api/v1/coa/{uuid.uuid4()}/vat-rate", json={"vat_rate": "20%"})

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /templates/{template_name}/load — load_template
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_load_template_success(client: TestClient) -> None:
    """Should load template and return 200."""
    acc1 = make_response(code="1000", name="Bank", category="Asset", type="Bank")
    acc2 = make_response(id=ANOTHER_ID, code="1010", name="Petty Cash", category="Asset", type="CurrentAsset")

    with patch("src.routes.coa.CoaService.load_template", new_callable=AsyncMock) as mock_load:
        mock_load.return_value = [acc1, acc2]
        response = client.post("/api/v1/coa/templates/uk_sole_trader_no_vat/load")

    assert response.status_code == 200
    assert response.json()["total"] == 2


@pytest.mark.asyncio
async def test_load_template_not_found(client: TestClient) -> None:
    """Should return 404 for non-existent template."""
    with patch("src.routes.coa.CoaService.load_template", new_callable=AsyncMock) as mock_load:
        mock_load.side_effect = TemplateNotFoundError("nonexistent")
        response = client.post("/api/v1/coa/templates/nonexistent/load")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def test_health_check(client: TestClient) -> None:
    """Should return ok for health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
