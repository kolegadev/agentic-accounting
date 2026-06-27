"""Unit tests for Recurring routes using FastAPI TestClient with mocked service layer."""

from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure DATABASE_URL is set before importing app
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/test_db",
)

from src.index import app
from src.services.recurring_service import (
    AccountNotFoundError,
    ContactNotFoundError,
    TemplateNotFoundError,
    TemplateNotActiveError,
)
from src.validators.recurring import (
    RecurringTemplateResponse,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEMPLATE_ID = uuid.uuid4()
CONTACT_ID = uuid.uuid4()
DEBIT_ACCOUNT_ID = uuid.uuid4()
CREDIT_ACCOUNT_ID = uuid.uuid4()
NOW = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)
TODAY = date(2026, 6, 27)

SAMPLE_TRANSACTION_DETAIL = {
    "id": str(uuid.uuid4()),
    "template_id": str(TEMPLATE_ID),
    "description": "Monthly office rent",
    "debit_account_id": str(DEBIT_ACCOUNT_ID),
    "credit_account_id": str(CREDIT_ACCOUNT_ID),
    "amount_pence": 150000,
    "vat_rate": "20%",
    "contact_id": None,
}

SAMPLE_INVOICE_DETAIL = {
    "id": str(uuid.uuid4()),
    "template_id": str(TEMPLATE_ID),
    "contact_id": str(CONTACT_ID),
    "items": [
        {
            "description": "Website hosting",
            "quantity": 1,
            "unit_price": 2999,
            "vat_rate": "20%",
        },
    ],
    "payment_terms": "Net 30",
    "notes": "Monthly hosting fee",
}

SAMPLE_TEMPLATE_RESPONSE: dict = {
    "id": str(TEMPLATE_ID),
    "name": "Monthly Rent",
    "template_type": "transaction",
    "frequency": "monthly",
    "next_run_date": "2026-06-27",
    "end_type": "never",
    "end_after_count": None,
    "end_until_date": None,
    "is_active": True,
    "last_run_date": None,
    "run_count": 0,
    "created_at": NOW.isoformat(),
    "updated_at": NOW.isoformat(),
    "transaction_detail": SAMPLE_TRANSACTION_DETAIL,
    "invoice_detail": None,
}


def make_response(**overrides) -> RecurringTemplateResponse:
    """Build a RecurringTemplateResponse with defaults overridden."""
    data = SAMPLE_TEMPLATE_RESPONSE.copy()
    data.update(overrides)
    # Convert UUIDs
    for field in ("id",):
        if isinstance(data.get(field), uuid.UUID):
            data[field] = str(data[field])
    return RecurringTemplateResponse.model_validate(data)


@pytest.fixture
def client() -> TestClient:
    """Return a FastAPI TestClient."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /templates — create_template
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_template_success(client: TestClient) -> None:
    """Should create template and return 201."""
    with patch(
        "src.routes.recurring.RecurringService.create_template",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = make_response()
        response = client.post(
            "/api/v1/recurring/templates",
            json={
                "name": "Monthly Rent",
                "template_type": "transaction",
                "frequency": "monthly",
                "next_run_date": "2026-06-27",
                "end_type": "never",
                "transaction_detail": {
                    "description": "Monthly office rent",
                    "debit_account_id": str(DEBIT_ACCOUNT_ID),
                    "credit_account_id": str(CREDIT_ACCOUNT_ID),
                    "amount_pence": 150000,
                    "vat_rate": "20%",
                },
            },
        )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Monthly Rent"
    assert data["template_type"] == "transaction"


@pytest.mark.asyncio
async def test_create_template_missing_detail(client: TestClient) -> None:
    """Should return 422 when transaction type missing detail."""
    response = client.post(
        "/api/v1/recurring/templates",
        json={
            "name": "Bad Template",
            "template_type": "transaction",
            "frequency": "monthly",
            "next_run_date": "2026-06-27",
            "end_type": "never",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_template_account_not_found(client: TestClient) -> None:
    """Should return 404 when account not found."""
    with patch(
        "src.routes.recurring.RecurringService.create_template",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.side_effect = AccountNotFoundError(uuid.uuid4())
        response = client.post(
            "/api/v1/recurring/templates",
            json={
                "name": "Test",
                "template_type": "transaction",
                "frequency": "monthly",
                "next_run_date": "2026-06-27",
                "end_type": "never",
                "transaction_detail": {
                    "description": "Test",
                    "debit_account_id": str(uuid.uuid4()),
                    "credit_account_id": str(CREDIT_ACCOUNT_ID),
                    "amount_pence": 10000,
                },
            },
        )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /templates — list_templates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_templates_success(client: TestClient) -> None:
    """Should list templates and return 200."""
    with patch(
        "src.routes.recurring.RecurringService.list_templates",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([make_response()], 1)
        response = client.get("/api/v1/recurring/templates")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["templates"]) == 1


@pytest.mark.asyncio
async def test_list_templates_with_filters(client: TestClient) -> None:
    """Should list templates with filters."""
    with patch(
        "src.routes.recurring.RecurringService.list_templates",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([], 0)
        response = client.get(
            "/api/v1/recurring/templates?template_type=invoice&is_active=true&limit=10&offset=0"
        )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


# ---------------------------------------------------------------------------
# GET /templates/{id} — get_template
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_template_success(client: TestClient) -> None:
    """Should get template by ID and return 200."""
    with patch(
        "src.routes.recurring.RecurringService.get_template",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = make_response()
        response = client.get(f"/api/v1/recurring/templates/{TEMPLATE_ID}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(TEMPLATE_ID)


@pytest.mark.asyncio
async def test_get_template_not_found(client: TestClient) -> None:
    """Should return 404 for non-existent template."""
    with patch(
        "src.routes.recurring.RecurringService.get_template",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = None
        response = client.get(f"/api/v1/recurring/templates/{TEMPLATE_ID}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /templates/{id} — update_template
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_template_success(client: TestClient) -> None:
    """Should update template and return 200."""
    with patch(
        "src.routes.recurring.RecurringService.update_template",
        new_callable=AsyncMock,
    ) as mock_update:
        mock_update.return_value = make_response(
            name="Updated Rent",
        )
        response = client.patch(
            f"/api/v1/recurring/templates/{TEMPLATE_ID}",
            json={
                "name": "Updated Rent",
                "template_type": "transaction",
                "frequency": "monthly",
                "next_run_date": "2026-07-01",
                "end_type": "never",
                "transaction_detail": {
                    "description": "Updated office rent",
                    "debit_account_id": str(DEBIT_ACCOUNT_ID),
                    "credit_account_id": str(CREDIT_ACCOUNT_ID),
                    "amount_pence": 160000,
                },
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Rent"


@pytest.mark.asyncio
async def test_update_template_not_found(client: TestClient) -> None:
    """Should return 404 when template not found."""
    with patch(
        "src.routes.recurring.RecurringService.update_template",
        new_callable=AsyncMock,
    ) as mock_update:
        mock_update.side_effect = TemplateNotFoundError(str(TEMPLATE_ID))
        response = client.patch(
            f"/api/v1/recurring/templates/{TEMPLATE_ID}",
            json={
                "name": "Test",
                "template_type": "transaction",
                "frequency": "monthly",
                "next_run_date": "2026-06-27",
                "end_type": "never",
                "transaction_detail": {
                    "description": "Test",
                    "debit_account_id": str(DEBIT_ACCOUNT_ID),
                    "credit_account_id": str(CREDIT_ACCOUNT_ID),
                    "amount_pence": 10000,
                },
            },
        )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /templates/{id} — delete_template
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_template_success(client: TestClient) -> None:
    """Should delete template and return 204."""
    with patch(
        "src.routes.recurring.RecurringService.delete_template",
        new_callable=AsyncMock,
    ) as mock_delete:
        mock_delete.return_value = None
        response = client.delete(f"/api/v1/recurring/templates/{TEMPLATE_ID}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_template_not_found(client: TestClient) -> None:
    """Should return 404 when template not found."""
    with patch(
        "src.routes.recurring.RecurringService.delete_template",
        new_callable=AsyncMock,
    ) as mock_delete:
        mock_delete.side_effect = TemplateNotFoundError(str(TEMPLATE_ID))
        response = client.delete(f"/api/v1/recurring/templates/{TEMPLATE_ID}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /templates/{id}/skip — skip_next
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skip_next_success(client: TestClient) -> None:
    """Should skip next occurrence and return 200."""
    with patch(
        "src.routes.recurring.RecurringService.skip_next",
        new_callable=AsyncMock,
    ) as mock_skip:
        mock_skip.return_value = make_response(next_run_date=date(2026, 7, 27))
        response = client.post(f"/api/v1/recurring/templates/{TEMPLATE_ID}/skip")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_skip_next_not_found(client: TestClient) -> None:
    """Should return 404 when template not found."""
    with patch(
        "src.routes.recurring.RecurringService.skip_next",
        new_callable=AsyncMock,
    ) as mock_skip:
        mock_skip.side_effect = TemplateNotFoundError(str(TEMPLATE_ID))
        response = client.post(f"/api/v1/recurring/templates/{TEMPLATE_ID}/skip")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_skip_next_inactive(client: TestClient) -> None:
    """Should return 422 when template not active."""
    with patch(
        "src.routes.recurring.RecurringService.skip_next",
        new_callable=AsyncMock,
    ) as mock_skip:
        mock_skip.side_effect = TemplateNotActiveError(TEMPLATE_ID)
        response = client.post(f"/api/v1/recurring/templates/{TEMPLATE_ID}/skip")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /templates/{id}/pause — pause_template
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pause_template_success(client: TestClient) -> None:
    """Should pause template and return 200."""
    with patch(
        "src.routes.recurring.RecurringService.pause_template",
        new_callable=AsyncMock,
    ) as mock_pause:
        mock_pause.return_value = make_response(is_active=False)
        response = client.post(f"/api/v1/recurring/templates/{TEMPLATE_ID}/pause")
    assert response.status_code == 200
    assert response.json()["is_active"] is False


# ---------------------------------------------------------------------------
# POST /templates/{id}/resume — resume_template
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resume_template_success(client: TestClient) -> None:
    """Should resume template and return 200."""
    with patch(
        "src.routes.recurring.RecurringService.resume_template",
        new_callable=AsyncMock,
    ) as mock_resume:
        mock_resume.return_value = make_response(is_active=True)
        response = client.post(f"/api/v1/recurring/templates/{TEMPLATE_ID}/resume")
    assert response.status_code == 200
    assert response.json()["is_active"] is True


# ---------------------------------------------------------------------------
# POST /process — process_due
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_due_success(client: TestClient) -> None:
    """Should process due templates and return 200."""
    with patch(
        "src.routes.recurring.RecurringService.process_due_templates",
        new_callable=AsyncMock,
    ) as mock_process:
        mock_process.return_value = 3
        response = client.post("/api/v1/recurring/process")
    assert response.status_code == 200
    data = response.json()
    assert data["processed"] == 3
    assert "3 due template" in data["message"]


@pytest.mark.asyncio
async def test_process_due_none(client: TestClient) -> None:
    """Should return 0 when no templates are due."""
    with patch(
        "src.routes.recurring.RecurringService.process_due_templates",
        new_callable=AsyncMock,
    ) as mock_process:
        mock_process.return_value = 0
        response = client.post("/api/v1/recurring/process")
    assert response.status_code == 200
    data = response.json()
    assert data["processed"] == 0
