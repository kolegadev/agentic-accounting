"""Unit tests for Invoice routes using FastAPI TestClient with mocked service layer."""

from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure DATABASE_URL is set before importing app (mirrors conftest.py)
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5432/test_db",
)

from src.index import app
from src.services.invoice_service import (
    ContactNotFoundError,
    InvoiceLifecycleError,
    InvoiceNotFoundError,
)
from src.validators.invoice import (
    CreditNoteResponse,
    InvoiceLineResponse,
    InvoiceListResponse,
    InvoiceResponse,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

INVOICE_ID = uuid.uuid4()
CONTACT_ID = uuid.uuid4()
NOW = "2026-06-27T12:00:00Z"
TODAY = date(2026, 6, 27)

SAMPLE_LINE: dict = {
    "id": str(uuid.uuid4()),
    "invoice_id": str(INVOICE_ID),
    "description": "Consulting services",
    "quantity": 10,
    "unit_price": 8500,
    "vat_rate": "20%",
    "vat_amount": 17000,
    "line_total": 102000,
    "sort_order": 0,
}

SAMPLE_INVOICE_RESPONSE: dict = {
    "id": str(INVOICE_ID),
    "reference": None,
    "contact_id": str(CONTACT_ID),
    "status": "draft",
    "issue_date": "2026-06-27",
    "due_date": "2026-07-27",
    "subtotal": 85000,
    "vat_total": 17000,
    "total": 102000,
    "currency": "GBP",
    "notes": None,
    "sent_at": None,
    "viewed_at": None,
    "paid_at": None,
    "created_at": NOW,
    "updated_at": NOW,
    "lines": [SAMPLE_LINE],
}

SAMPLE_CREDIT_NOTE_RESPONSE: dict = {
    "id": str(uuid.uuid4()),
    "invoice_id": str(INVOICE_ID),
    "reference": f"CN-{datetime.now(timezone.utc).year}-0001",
    "contact_id": str(CONTACT_ID),
    "total": -102000,
    "reason": "Duplicate invoice",
    "created_at": NOW,
}


def make_response(**overrides) -> InvoiceResponse:
    """Build an InvoiceResponse with defaults overridden."""
    data = SAMPLE_INVOICE_RESPONSE.copy()
    data.update(overrides)
    data["id"] = str(data.get("id", INVOICE_ID))
    data["contact_id"] = str(data.get("contact_id", CONTACT_ID))
    if "lines" not in data:
        data["lines"] = [SAMPLE_LINE]
    return InvoiceResponse(**data)


@pytest.fixture
def client() -> TestClient:
    """Return a FastAPI TestClient."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST / — create_invoice
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_invoice_success(client: TestClient) -> None:
    """Should create invoice and return 201."""
    with patch(
        "src.routes.invoices.InvoiceService.create_invoice",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = make_response(status="draft")
        response = client.post(
            "/api/v1/invoices/",
            json={
                "contact_id": str(CONTACT_ID),
                "issue_date": "2026-06-27",
                "due_date": "2026-07-27",
                "lines": [
                    {
                        "description": "Test service",
                        "quantity": 1,
                        "unit_price": 85000,
                        "vat_rate": "20%",
                    }
                ],
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "draft"
    assert data["total"] == 102000


@pytest.mark.asyncio
async def test_create_invoice_contact_not_found(client: TestClient) -> None:
    """Should return 404 when contact not found."""
    with patch(
        "src.routes.invoices.InvoiceService.create_invoice",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.side_effect = ContactNotFoundError(CONTACT_ID)
        response = client.post(
            "/api/v1/invoices/",
            json={
                "contact_id": str(CONTACT_ID),
                "issue_date": "2026-06-27",
                "due_date": "2026-07-27",
                "lines": [
                    {
                        "description": "Test",
                        "unit_price": 1000,
                        "vat_rate": "20%",
                    }
                ],
            },
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_invoice_validation_error(client: TestClient) -> None:
    """Should return 422 for missing lines."""
    response = client.post(
        "/api/v1/invoices/",
        json={
            "contact_id": str(CONTACT_ID),
            "issue_date": "2026-06-27",
            "due_date": "2026-07-27",
            "lines": [],
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_invoice_invalid_vat_rate(client: TestClient) -> None:
    """Should return 422 for invalid VAT rate."""
    response = client.post(
        "/api/v1/invoices/",
        json={
            "contact_id": str(CONTACT_ID),
            "issue_date": "2026-06-27",
            "due_date": "2026-07-27",
            "lines": [
                {
                    "description": "Test",
                    "unit_price": 1000,
                    "vat_rate": "invalid",
                }
            ],
        },
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /{id}/send — send_invoice
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_invoice_success(client: TestClient) -> None:
    """Should send invoice and return 200."""
    with patch(
        "src.routes.invoices.InvoiceService.send_invoice",
        new_callable=AsyncMock,
    ) as mock_send:
        mock_send.return_value = make_response(
            status="sent",
            reference="INV-2026-0001",
            sent_at=NOW,
        )
        response = client.post(f"/api/v1/invoices/{INVOICE_ID}/send")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "sent"
    assert data["reference"] == "INV-2026-0001"


@pytest.mark.asyncio
async def test_send_invoice_not_found(client: TestClient) -> None:
    """Should return 404 when invoice not found."""
    with patch(
        "src.routes.invoices.InvoiceService.send_invoice",
        new_callable=AsyncMock,
    ) as mock_send:
        mock_send.side_effect = InvoiceNotFoundError(str(uuid.uuid4()))
        response = client.post(f"/api/v1/invoices/{uuid.uuid4()}/send")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_send_invoice_wrong_status(client: TestClient) -> None:
    """Should return 422 when invoice is not draft."""
    with patch(
        "src.routes.invoices.InvoiceService.send_invoice",
        new_callable=AsyncMock,
    ) as mock_send:
        mock_send.side_effect = InvoiceLifecycleError(INVOICE_ID, "sent", "send")
        response = client.post(f"/api/v1/invoices/{INVOICE_ID}/send")

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET / — list_invoices
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_invoices_success(client: TestClient) -> None:
    """Should return list of invoices."""
    with patch(
        "src.routes.invoices.InvoiceService.list_invoices",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([make_response()], 1)
        response = client.get("/api/v1/invoices/")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["invoices"]) == 1
    assert data["invoices"][0]["status"] == "draft"


@pytest.mark.asyncio
async def test_list_invoices_with_filters(client: TestClient) -> None:
    """Should pass filter params to service."""
    with patch(
        "src.routes.invoices.InvoiceService.list_invoices",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([], 0)
        response = client.get(
            "/api/v1/invoices/?status=draft&contact_id="
            + str(CONTACT_ID)
            + "&date_from=2026-01-01&date_to=2026-06-30&limit=10&offset=0"
        )

    assert response.status_code == 200
    mock_list.assert_called_once()
    kwargs = mock_list.call_args.kwargs
    assert kwargs["status"] == "draft"
    assert kwargs["limit"] == 10


@pytest.mark.asyncio
async def test_list_invoices_empty(client: TestClient) -> None:
    """Should return empty list."""
    with patch(
        "src.routes.invoices.InvoiceService.list_invoices",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([], 0)
        response = client.get("/api/v1/invoices/")

    assert response.status_code == 200
    assert response.json()["total"] == 0


# ---------------------------------------------------------------------------
# GET /{id} — get_invoice
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_invoice_success(client: TestClient) -> None:
    """Should return invoice when found."""
    with patch(
        "src.routes.invoices.InvoiceService.get_invoice",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = make_response()
        response = client.get(f"/api/v1/invoices/{INVOICE_ID}")

    assert response.status_code == 200
    assert response.json()["id"] == str(INVOICE_ID)


@pytest.mark.asyncio
async def test_get_invoice_not_found(client: TestClient) -> None:
    """Should return 404 for non-existent invoice."""
    with patch(
        "src.routes.invoices.InvoiceService.get_invoice",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = None
        response = client.get(f"/api/v1/invoices/{uuid.uuid4()}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /{id}/viewed — mark_as_viewed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_viewed_success(client: TestClient) -> None:
    """Should mark invoice as viewed."""
    with patch(
        "src.routes.invoices.InvoiceService.mark_as_viewed",
        new_callable=AsyncMock,
    ) as mock_viewed:
        mock_viewed.return_value = make_response(status="viewed", viewed_at=NOW)
        response = client.patch(f"/api/v1/invoices/{INVOICE_ID}/viewed")

    assert response.status_code == 200
    assert response.json()["status"] == "viewed"


@pytest.mark.asyncio
async def test_mark_viewed_not_found(client: TestClient) -> None:
    """Should return 404 for non-existent invoice."""
    with patch(
        "src.routes.invoices.InvoiceService.mark_as_viewed",
        new_callable=AsyncMock,
    ) as mock_viewed:
        mock_viewed.side_effect = InvoiceNotFoundError(str(uuid.uuid4()))
        response = client.patch(f"/api/v1/invoices/{uuid.uuid4()}/viewed")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /{id}/mark-paid — mark_as_paid
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_paid_success(client: TestClient) -> None:
    """Should mark invoice as paid."""
    with patch(
        "src.routes.invoices.InvoiceService.mark_as_paid",
        new_callable=AsyncMock,
    ) as mock_paid:
        mock_paid.return_value = make_response(status="paid", paid_at=NOW)
        response = client.post(f"/api/v1/invoices/{INVOICE_ID}/mark-paid")

    assert response.status_code == 200
    assert response.json()["status"] == "paid"


@pytest.mark.asyncio
async def test_mark_paid_not_found(client: TestClient) -> None:
    """Should return 404 for non-existent invoice."""
    with patch(
        "src.routes.invoices.InvoiceService.mark_as_paid",
        new_callable=AsyncMock,
    ) as mock_paid:
        mock_paid.side_effect = InvoiceNotFoundError(str(uuid.uuid4()))
        response = client.post(f"/api/v1/invoices/{uuid.uuid4()}/mark-paid")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_mark_paid_wrong_status(client: TestClient) -> None:
    """Should return 422 for invalid transition."""
    with patch(
        "src.routes.invoices.InvoiceService.mark_as_paid",
        new_callable=AsyncMock,
    ) as mock_paid:
        mock_paid.side_effect = InvoiceLifecycleError(INVOICE_ID, "draft", "paid")
        response = client.post(f"/api/v1/invoices/{INVOICE_ID}/mark-paid")

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /{id}/cancel — cancel_invoice
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_invoice_success(client: TestClient) -> None:
    """Should cancel draft invoice."""
    with patch(
        "src.routes.invoices.InvoiceService.cancel_invoice",
        new_callable=AsyncMock,
    ) as mock_cancel:
        mock_cancel.return_value = make_response(status="cancelled")
        response = client.post(f"/api/v1/invoices/{INVOICE_ID}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_invoice_not_found(client: TestClient) -> None:
    """Should return 404."""
    with patch(
        "src.routes.invoices.InvoiceService.cancel_invoice",
        new_callable=AsyncMock,
    ) as mock_cancel:
        mock_cancel.side_effect = InvoiceNotFoundError(str(uuid.uuid4()))
        response = client.post(f"/api/v1/invoices/{uuid.uuid4()}/cancel")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /overdue — check_overdue
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_overdue_success(client: TestClient) -> None:
    """Should return overdue invoices."""
    with patch(
        "src.routes.invoices.InvoiceService.check_overdue",
        new_callable=AsyncMock,
    ) as mock_overdue:
        mock_overdue.return_value = [make_response(status="overdue")]
        response = client.get("/api/v1/invoices/overdue")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "overdue"


@pytest.mark.asyncio
async def test_check_overdue_empty(client: TestClient) -> None:
    """Should return empty list when no overdue invoices."""
    with patch(
        "src.routes.invoices.InvoiceService.check_overdue",
        new_callable=AsyncMock,
    ) as mock_overdue:
        mock_overdue.return_value = []
        response = client.get("/api/v1/invoices/overdue")

    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# POST /{id}/credit-note — create_credit_note
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_credit_note_success(client: TestClient) -> None:
    """Should create credit note and return 201."""
    with patch(
        "src.routes.invoices.InvoiceService.create_credit_note",
        new_callable=AsyncMock,
    ) as mock_cn:
        cn = CreditNoteResponse(**SAMPLE_CREDIT_NOTE_RESPONSE)
        mock_cn.return_value = cn
        response = client.post(
            f"/api/v1/invoices/{INVOICE_ID}/credit-note",
            params={"reason": "Duplicate invoice"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["total"] == -102000
    assert data["reason"] == "Duplicate invoice"


@pytest.mark.asyncio
async def test_create_credit_note_not_found(client: TestClient) -> None:
    """Should return 404."""
    with patch(
        "src.routes.invoices.InvoiceService.create_credit_note",
        new_callable=AsyncMock,
    ) as mock_cn:
        mock_cn.side_effect = InvoiceNotFoundError(str(uuid.uuid4()))
        response = client.post(f"/api/v1/invoices/{uuid.uuid4()}/credit-note")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_credit_note_wrong_status(client: TestClient) -> None:
    """Should return 422 for draft invoice."""
    with patch(
        "src.routes.invoices.InvoiceService.create_credit_note",
        new_callable=AsyncMock,
    ) as mock_cn:
        mock_cn.side_effect = InvoiceLifecycleError(INVOICE_ID, "draft", "credit-credited")
        response = client.post(f"/api/v1/invoices/{INVOICE_ID}/credit-note")

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /{id}/pdf — generate_pdf
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_pdf_success(client: TestClient) -> None:
    """Should generate PDF and return 200."""
    with patch(
        "src.routes.invoices.InvoiceService.generate_pdf",
        new_callable=AsyncMock,
    ) as mock_pdf:
        mock_pdf.return_value = b"%PDF-1.4 fake pdf content"
        with patch(
            "src.routes.invoices.InvoiceService.get_invoice",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = make_response(reference="INV-2026-0001")

            response = client.get(f"/api/v1/invoices/{INVOICE_ID}/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "invoice-INV-2026-0001.pdf" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_generate_pdf_not_found(client: TestClient) -> None:
    """Should return 404 when invoice not found."""
    with patch(
        "src.routes.invoices.InvoiceService.generate_pdf",
        new_callable=AsyncMock,
    ) as mock_pdf:
        mock_pdf.side_effect = InvoiceNotFoundError(str(uuid.uuid4()))
        response = client.get(f"/api/v1/invoices/{uuid.uuid4()}/pdf")

    assert response.status_code == 404
