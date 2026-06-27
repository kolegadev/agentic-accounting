"""Unit tests for MTD routes using FastAPI TestClient with mocked service layer."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.index import app
from src.services.mtd_service import (
    MtdAuthenticationError,
    MtdServiceError,
    MtdSubmissionError,
    MtdValidationError,
    VatReturnAlreadySubmittedError,
    VatReturnNotFoundError,
)
from src.validators.mtd import (
    HmrcConnectionResponse,
    ObligationItem,
    ObligationResponse,
    SubmissionStatusResponse,
    SubmitResponse,
)

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

RETURN_ID = uuid.uuid4()
SUBMISSION_ID = "BANK"


SAMPLE_SUBMIT_RESPONSE: dict = {
    "vat_return_id": str(RETURN_ID),
    "submission_id": SUBMISSION_ID,
    "correlation_id": "corr-test-123",
    "status": "accepted",
    "processing_date": "2026-06-27T12:00:00Z",
    "form_bundle_number": "123456789012",
    "payment_indicator": "BANK",
    "charge_ref_number": "XDVAT1234567",
}


SAMPLE_OBLIGATIONS_RESPONSE: dict = {
    "obligations": [
        {
            "period_key": "#001",
            "start": "2026-01-01",
            "end": "2026-03-31",
            "due": "2026-05-07",
            "status": "O",
        },
    ],
}


SAMPLE_STATUS_RESPONSE: dict = {
    "submission_id": SUBMISSION_ID,
    "status": "accepted",
    "vat_return_id": str(RETURN_ID),
    "submitted_at": "2026-06-27T12:00:00Z",
    "correlation_id": "corr-test-123",
}


SAMPLE_CONNECTION_OK: dict = {
    "connected": True,
    "message": "Successfully connected to HMRC MTD API",
    "obligations_count": 2,
    "timestamp": "2026-06-27T12:00:00Z",
}


SAMPLE_CONNECTION_FAIL: dict = {
    "connected": False,
    "message": "HMRC API connection failed: no credentials",
    "obligations_count": None,
    "timestamp": "2026-06-27T12:00:00Z",
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client() -> TestClient:
    """Return a FastAPI TestClient."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /api/v1/mtd/submit/{vat_return_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_vat_return_success(client: TestClient) -> None:
    """Should submit VAT return and return SubmitResponse."""
    with patch(
        "src.routes.mtd.MtdService.submit_vat_return",
        new_callable=AsyncMock,
    ) as mock_submit:
        mock_submit.return_value = SubmitResponse(**SAMPLE_SUBMIT_RESPONSE)
        response = client.post(f"/api/v1/mtd/submit/{RETURN_ID}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["submission_id"] == SUBMISSION_ID
    assert data["form_bundle_number"] == "123456789012"
    mock_submit.assert_called_once()


@pytest.mark.asyncio
async def test_submit_vat_return_not_found(client: TestClient) -> None:
    """Should return 404 when VAT return not found."""
    with patch(
        "src.routes.mtd.MtdService.submit_vat_return",
        new_callable=AsyncMock,
    ) as mock_submit:
        mock_submit.side_effect = VatReturnNotFoundError(RETURN_ID)
        response = client.post(f"/api/v1/mtd/submit/{RETURN_ID}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_submit_vat_return_already_submitted(client: TestClient) -> None:
    """Should return 409 when already submitted."""
    with patch(
        "src.routes.mtd.MtdService.submit_vat_return",
        new_callable=AsyncMock,
    ) as mock_submit:
        mock_submit.side_effect = VatReturnAlreadySubmittedError(RETURN_ID)
        response = client.post(f"/api/v1/mtd/submit/{RETURN_ID}")

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_submit_vat_return_validation_error(client: TestClient) -> None:
    """Should return 422 on digital link validation failure."""
    with patch(
        "src.routes.mtd.MtdService.submit_vat_return",
        new_callable=AsyncMock,
    ) as mock_submit:
        mock_submit.side_effect = MtdValidationError("Box 3 mismatch")
        response = client.post(f"/api/v1/mtd/submit/{RETURN_ID}")

    assert response.status_code == 422
    assert "Box 3 mismatch" in response.json()["detail"]


@pytest.mark.asyncio
async def test_submit_vat_return_auth_failure(client: TestClient) -> None:
    """Should return 502 on HMRC auth failure."""
    with patch(
        "src.routes.mtd.MtdService.submit_vat_return",
        new_callable=AsyncMock,
    ) as mock_submit:
        mock_submit.side_effect = MtdAuthenticationError("OAuth failed")
        response = client.post(f"/api/v1/mtd/submit/{RETURN_ID}")

    assert response.status_code == 502


@pytest.mark.asyncio
async def test_submit_vat_return_submission_error(client: TestClient) -> None:
    """Should return 502 on HMRC rejection."""
    with patch(
        "src.routes.mtd.MtdService.submit_vat_return",
        new_callable=AsyncMock,
    ) as mock_submit:
        mock_submit.side_effect = MtdSubmissionError("HMRC rejected")
        response = client.post(f"/api/v1/mtd/submit/{RETURN_ID}")

    assert response.status_code == 502


# ---------------------------------------------------------------------------
# GET /api/v1/mtd/obligations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_obligations_success(client: TestClient) -> None:
    """Should return obligations from HMRC."""
    obligations = ObligationResponse(
        obligations=[
            ObligationItem(
                period_key="#001",
                start="2026-01-01",
                end="2026-03-31",
                due="2026-05-07",
                status="O",
            )
        ]
    )

    with patch(
        "src.routes.mtd.MtdService.get_obligations",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = obligations
        response = client.get("/api/v1/mtd/obligations")

    assert response.status_code == 200
    data = response.json()
    assert len(data["obligations"]) == 1
    assert data["obligations"][0]["period_key"] == "#001"
    assert data["obligations"][0]["status"] == "O"


@pytest.mark.asyncio
async def test_get_obligations_error(client: TestClient) -> None:
    """Should return 502 on HMRC API error."""
    with patch(
        "src.routes.mtd.MtdService.get_obligations",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.side_effect = MtdServiceError("HMRC unreachable", status_code=502)
        response = client.get("/api/v1/mtd/obligations")

    assert response.status_code == 502


# ---------------------------------------------------------------------------
# GET /api/v1/mtd/submissions/{submission_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_submission_status_success(client: TestClient) -> None:
    """Should return submission status."""
    status_response = SubmissionStatusResponse(**SAMPLE_STATUS_RESPONSE)

    with patch(
        "src.routes.mtd.MtdService.get_submission_status",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = status_response
        response = client.get(f"/api/v1/mtd/submissions/{SUBMISSION_ID}")

    assert response.status_code == 200
    data = response.json()
    assert data["submission_id"] == SUBMISSION_ID
    assert data["status"] == "accepted"
    assert data["vat_return_id"] == str(RETURN_ID)


@pytest.mark.asyncio
async def test_get_submission_status_not_found(client: TestClient) -> None:
    """Should return 404 when submission not found."""
    with patch(
        "src.routes.mtd.MtdService.get_submission_status",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.side_effect = VatReturnNotFoundError(uuid.uuid4())
        response = client.get("/api/v1/mtd/submissions/NONEXISTENT")

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/mtd/test-connection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_test_connection_success(client: TestClient) -> None:
    """Should return connected=True."""
    with patch(
        "src.routes.mtd.MtdService.test_connection",
        new_callable=AsyncMock,
    ) as mock_test:
        mock_test.return_value = HmrcConnectionResponse(
            connected=True,
            message="Successfully connected to HMRC MTD API",
            obligations_count=2,
        )
        response = client.get("/api/v1/mtd/test-connection")

    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["obligations_count"] == 2


@pytest.mark.asyncio
async def test_test_connection_failure(client: TestClient) -> None:
    """Should return connected=False on failure."""
    with patch(
        "src.routes.mtd.MtdService.test_connection",
        new_callable=AsyncMock,
    ) as mock_test:
        mock_test.return_value = HmrcConnectionResponse(
            connected=False,
            message="HMRC API connection failed: bad credentials",
        )
        response = client.get("/api/v1/mtd/test-connection")

    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is False
    assert "bad credentials" in data["message"]
