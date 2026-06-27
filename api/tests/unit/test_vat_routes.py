"""Unit tests for VAT routes using FastAPI TestClient with mocked service layer."""

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
from src.services.vat_service import (
    VatFlatRateMissingError,
    VatPeriodClosedError,
    VatPeriodNotFoundError,
    VatReturnNotFoundError,
)
from src.validators.vat import (
    VatAdjustmentResponse,
    VatAuditEntry,
    VatAuditResponse,
    VatPeriodResponse,
    VatReturnCalculationResponse,
    VatReturnResponse,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PERIOD_ID = uuid.uuid4()
RETURN_ID = uuid.uuid4()
NOW = "2026-06-27T12:00:00Z"
TODAY = date(2026, 6, 27)

SAMPLE_PERIOD_RESPONSE: dict = {
    "id": str(PERIOD_ID),
    "start_date": "2026-04-01",
    "end_date": "2026-06-30",
    "scheme": "standard",
    "flat_rate_percentage": None,
    "status": "open",
    "closed_at": None,
    "created_at": NOW,
}

SAMPLE_RETURN_RESPONSE: dict = {
    "id": str(RETURN_ID),
    "period_id": str(PERIOD_ID),
    "box1": 10000,
    "box2": 0,
    "box3": 10000,
    "box4": 5000,
    "box5": 5000,
    "box6": 50000,
    "box7": 25000,
    "box8": 0,
    "box9": 0,
    "submitted_at": None,
    "created_at": NOW,
}

SAMPLE_AUDIT_ENTRY: dict = {
    "source_type": "vat_line",
    "source_id": str(uuid.uuid4()),
    "source_reference": "JE-2026-0001",
    "description": "Test sale",
    "box_number": 1,
    "amount": 2000,
    "vat_type": "output",
    "vat_rate": "20%",
    "effective_date": "2026-05-15",
}

SAMPLE_AUDIT_RESPONSE: dict = {
    "vat_return_id": str(RETURN_ID),
    "period": SAMPLE_PERIOD_RESPONSE,
    "entries": [SAMPLE_AUDIT_ENTRY],
    "summary": {
        "box1": 10000,
        "box2": 0,
        "box3": 10000,
        "box4": 5000,
        "box5": 5000,
        "box6": 50000,
        "box7": 25000,
        "box8": 0,
        "box9": 0,
    },
}

SAMPLE_ADJUSTMENT_RESPONSE: dict = {
    "id": str(uuid.uuid4()),
    "vat_return_id": str(RETURN_ID),
    "box_number": 4,
    "amount_before": 5000,
    "amount_after": 7000,
    "reason": "Additional purchase VAT",
    "source_reference": "INV-2026-0042",
    "created_at": NOW,
}


def make_period_response(**overrides) -> VatPeriodResponse:
    """Build a VatPeriodResponse with defaults overridden."""
    data = SAMPLE_PERIOD_RESPONSE.copy()
    data.update(overrides)
    data["id"] = str(data.get("id", PERIOD_ID))
    return VatPeriodResponse(**data)


def make_return_response(**overrides) -> VatReturnResponse:
    """Build a VatReturnResponse with defaults overridden."""
    data = SAMPLE_RETURN_RESPONSE.copy()
    data.update(overrides)
    data["id"] = str(data.get("id", RETURN_ID))
    data["period_id"] = str(data.get("period_id", PERIOD_ID))
    return VatReturnResponse(**data)


def make_calculation_response() -> VatReturnCalculationResponse:
    """Build a VatReturnCalculationResponse."""
    audit = VatAuditResponse(**SAMPLE_AUDIT_RESPONSE)
    return VatReturnCalculationResponse(
        vat_return=make_return_response(),
        audit=audit,
    )


@pytest.fixture
def client() -> TestClient:
    """Return a FastAPI TestClient."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /periods — create_period
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_period_success(client: TestClient) -> None:
    """Should create a VAT period and return 201."""
    with patch(
        "src.routes.vat.VatService.create_period",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = make_period_response()
        response = client.post(
            "/api/v1/vat/periods",
            json={
                "start_date": "2026-04-01",
                "end_date": "2026-06-30",
                "scheme": "standard",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["scheme"] == "standard"
    assert data["status"] == "open"


@pytest.mark.asyncio
async def test_create_period_flat_rate_missing_percentage(client: TestClient) -> None:
    """Should return 422 when flat_rate without percentage."""
    with patch(
        "src.routes.vat.VatService.create_period",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.side_effect = VatFlatRateMissingError()
        response = client.post(
            "/api/v1/vat/periods",
            json={
                "start_date": "2026-04-01",
                "end_date": "2026-06-30",
                "scheme": "flat_rate",
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_period_invalid_scheme(client: TestClient) -> None:
    """Should return 422 for invalid scheme."""
    response = client.post(
        "/api/v1/vat/periods",
        json={
            "start_date": "2026-04-01",
            "end_date": "2026-06-30",
            "scheme": "invalid_scheme",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_period_flat_rate_with_percentage(client: TestClient) -> None:
    """Should create flat_rate period with percentage."""
    with patch(
        "src.routes.vat.VatService.create_period",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = make_period_response(
            scheme="flat_rate", flat_rate_percentage=7.5
        )
        response = client.post(
            "/api/v1/vat/periods",
            json={
                "start_date": "2026-04-01",
                "end_date": "2026-06-30",
                "scheme": "flat_rate",
                "flat_rate_percentage": 7.5,
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["scheme"] == "flat_rate"
    assert data["flat_rate_percentage"] == 7.5


# ---------------------------------------------------------------------------
# GET /periods — list_periods
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_periods_success(client: TestClient) -> None:
    """Should return list of periods."""
    with patch(
        "src.routes.vat.VatService.list_periods",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([make_period_response()], 1)
        response = client.get("/api/v1/vat/periods")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["periods"]) == 1


@pytest.mark.asyncio
async def test_list_periods_with_filters(client: TestClient) -> None:
    """Should pass filter params to service."""
    with patch(
        "src.routes.vat.VatService.list_periods",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([], 0)
        response = client.get(
            "/api/v1/vat/periods?status=open&scheme=standard&limit=10&offset=0"
        )

    assert response.status_code == 200
    mock_list.assert_called_once()
    kwargs = mock_list.call_args.kwargs
    assert kwargs["status"] == "open"
    assert kwargs["scheme"] == "standard"


@pytest.mark.asyncio
async def test_list_periods_empty(client: TestClient) -> None:
    """Should return empty list."""
    with patch(
        "src.routes.vat.VatService.list_periods",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([], 0)
        response = client.get("/api/v1/vat/periods")

    assert response.status_code == 200
    assert response.json()["total"] == 0


# ---------------------------------------------------------------------------
# POST /periods/{id}/calculate — calculate_return
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_calculate_return_success(client: TestClient) -> None:
    """Should calculate return and return 201."""
    with patch(
        "src.routes.vat.VatService.calculate_return",
        new_callable=AsyncMock,
    ) as mock_calc:
        mock_calc.return_value = make_calculation_response()
        response = client.post(f"/api/v1/vat/periods/{PERIOD_ID}/calculate")

    assert response.status_code == 201
    data = response.json()
    assert data["vat_return"]["box1"] == 10000
    assert data["vat_return"]["box5"] == 5000
    assert data["audit"] is not None
    assert len(data["audit"]["entries"]) == 1


@pytest.mark.asyncio
async def test_calculate_return_period_not_found(client: TestClient) -> None:
    """Should return 404 when period not found."""
    with patch(
        "src.routes.vat.VatService.calculate_return",
        new_callable=AsyncMock,
    ) as mock_calc:
        mock_calc.side_effect = VatPeriodNotFoundError(uuid.uuid4())
        response = client.post(f"/api/v1/vat/periods/{uuid.uuid4()}/calculate")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_calculate_return_period_closed(client: TestClient) -> None:
    """Should return 422 when period is closed."""
    with patch(
        "src.routes.vat.VatService.calculate_return",
        new_callable=AsyncMock,
    ) as mock_calc:
        mock_calc.side_effect = VatPeriodClosedError(PERIOD_ID)
        response = client.post(f"/api/v1/vat/periods/{PERIOD_ID}/calculate")

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /returns/{id} — get_return
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_return_success(client: TestClient) -> None:
    """Should return VAT return when found."""
    with patch(
        "src.routes.vat.VatService.get_return",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = make_return_response()
        response = client.get(f"/api/v1/vat/returns/{RETURN_ID}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(RETURN_ID)
    assert data["box1"] == 10000
    assert data["box5"] == 5000


@pytest.mark.asyncio
async def test_get_return_not_found(client: TestClient) -> None:
    """Should return 404 for non-existent return."""
    with patch(
        "src.routes.vat.VatService.get_return",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = None
        response = client.get(f"/api/v1/vat/returns/{uuid.uuid4()}")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /returns/{id}/audit — get_audit_trail
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_audit_trail_success(client: TestClient) -> None:
    """Should return audit trail when return found."""
    with patch(
        "src.routes.vat.VatService.get_audit_trail",
        new_callable=AsyncMock,
    ) as mock_audit:
        audit = VatAuditResponse(**SAMPLE_AUDIT_RESPONSE)
        mock_audit.return_value = audit
        response = client.get(f"/api/v1/vat/returns/{RETURN_ID}/audit")

    assert response.status_code == 200
    data = response.json()
    assert data["vat_return_id"] == str(RETURN_ID)
    assert len(data["entries"]) == 1
    assert data["summary"]["box5"] == 5000


@pytest.mark.asyncio
async def test_get_audit_trail_not_found(client: TestClient) -> None:
    """Should return 404 for non-existent return."""
    with patch(
        "src.routes.vat.VatService.get_audit_trail",
        new_callable=AsyncMock,
    ) as mock_audit:
        mock_audit.side_effect = VatReturnNotFoundError(uuid.uuid4())
        response = client.get(f"/api/v1/vat/returns/{uuid.uuid4()}/audit")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /returns/{id}/adjustment — add_adjustment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_adjustment_success(client: TestClient) -> None:
    """Should add adjustment and return 201."""
    with patch(
        "src.routes.vat.VatService.add_adjustment",
        new_callable=AsyncMock,
    ) as mock_adj:
        adj = VatAdjustmentResponse(**SAMPLE_ADJUSTMENT_RESPONSE)
        mock_adj.return_value = adj
        response = client.post(
            f"/api/v1/vat/returns/{RETURN_ID}/adjustment",
            json={
                "box_number": 4,
                "amount": 2000,
                "reason": "Additional purchase VAT",
                "source_reference": "INV-2026-0042",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["box_number"] == 4
    assert data["amount_before"] == 5000
    assert data["amount_after"] == 7000


@pytest.mark.asyncio
async def test_add_adjustment_return_not_found(client: TestClient) -> None:
    """Should return 404 for non-existent return."""
    with patch(
        "src.routes.vat.VatService.add_adjustment",
        new_callable=AsyncMock,
    ) as mock_adj:
        mock_adj.side_effect = VatReturnNotFoundError(uuid.uuid4())
        response = client.post(
            f"/api/v1/vat/returns/{uuid.uuid4()}/adjustment",
            json={
                "box_number": 1,
                "amount": 1000,
                "reason": "Test",
            },
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_adjustment_invalid_box(client: TestClient) -> None:
    """Should return 422 for box outside 1-9."""
    response = client.post(
        f"/api/v1/vat/returns/{RETURN_ID}/adjustment",
        json={
            "box_number": 10,
            "amount": 1000,
            "reason": "Invalid box",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_adjustment_negative_amount(client: TestClient) -> None:
    """Should accept negative adjustment amount."""
    with patch(
        "src.routes.vat.VatService.add_adjustment",
        new_callable=AsyncMock,
    ) as mock_adj:
        adj = VatAdjustmentResponse(
            id=uuid.uuid4(),
            vat_return_id=RETURN_ID,
            box_number=1,
            amount_before=10000,
            amount_after=7000,
            reason="Corrected output VAT",
            source_reference=None,
            created_at=datetime.now(timezone.utc),
        )
        mock_adj.return_value = adj
        response = client.post(
            f"/api/v1/vat/returns/{RETURN_ID}/adjustment",
            json={
                "box_number": 1,
                "amount": -3000,
                "reason": "Corrected output VAT",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["amount_before"] == 10000
    assert data["amount_after"] == 7000
