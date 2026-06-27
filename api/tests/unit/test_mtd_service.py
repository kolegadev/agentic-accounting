"""Unit tests for MtdService with mocked HMRC API responses."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timezone
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from httpx import Response

from src.models.vat import VatPeriod, VatReturn
from src.services.mtd_service import (
    MtdAuthenticationError,
    MtdService,
    MtdServiceError,
    MtdSubmissionError,
    MtdValidationError,
    VatReturnAlreadySubmittedError,
    VatReturnNotFoundError,
    _build_fraud_headers,
    _generate_device_id,
)
from src.validators.mtd import (
    ObligationResponse,
    SubmissionStatusResponse,
    SubmitResponse,
    HmrcConnectionResponse,
)
from tests.conftest import NOW


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db() -> AsyncMock:
    """Return an AsyncMock that simulates an async SQLAlchemy session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def sample_period() -> VatPeriod:
    """Create a VAT period for testing."""
    return VatPeriod(
        id=uuid.uuid4(),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        scheme="standard",
        status="open",
        created_at=NOW,
    )


@pytest.fixture
def sample_vat_return(sample_period: VatPeriod) -> VatReturn:
    """Create a completed VAT return for testing."""
    return VatReturn(
        id=uuid.uuid4(),
        period_id=sample_period.id,
        period=sample_period,
        box1=25000,  # £250.00 output VAT
        box2=0,
        box3=25000,  # = box1 + box2
        box4=5000,   # £50.00 input VAT
        box5=20000,  # = box3 - box4
        box6=125000, # £1,250.00 sales
        box7=25000,  # £250.00 purchases
        box8=0,
        box9=0,
        created_at=NOW,
    )


@pytest.fixture
def sample_submitted_return(sample_period: VatPeriod) -> VatReturn:
    """Create a VAT return that's already been submitted."""
    vr = VatReturn(
        id=uuid.uuid4(),
        period_id=sample_period.id,
        period=sample_period,
        box1=25000,
        box2=0,
        box3=25000,
        box4=5000,
        box5=20000,
        box6=125000,
        box7=25000,
        box8=0,
        box9=0,
        submission_id="SUB-001",
        correlation_id="corr-abc-123",
        submission_status="accepted",
        submitted_at=datetime(2026, 6, 15, tzinfo=timezone.utc),
        created_at=NOW,
    )
    return vr


@pytest.fixture
def hmrc_submit_response() -> dict:
    """Sample HMRC submit response."""
    return {
        "processingDate": "2026-06-27T12:00:00Z",
        "formBundleNumber": "123456789012",
        "paymentIndicator": "BANK",
        "chargeRefNumber": "XDVAT1234567",
    }


@pytest.fixture
def hmrc_obligations_response() -> dict:
    """Sample HMRC obligations response."""
    return {
        "obligations": [
            {
                "periodKey": "#001",
                "start": "2026-01-01",
                "end": "2026-03-31",
                "due": "2026-05-07",
                "status": "O",
            },
            {
                "periodKey": "#002",
                "start": "2026-04-01",
                "end": "2026-06-30",
                "due": "2026-08-07",
                "status": "O",
            },
        ],
    }


@pytest.fixture
def hmrc_oauth_response() -> dict:
    """Sample HMRC OAuth response."""
    return {
        "access_token": "test-access-token-abc123",
        "token_type": "bearer",
        "expires_in": 3600,
        "scope": "read:vat write:vat",
    }


# ---------------------------------------------------------------------------
# Fraud prevention headers
# ---------------------------------------------------------------------------

def test_generate_device_id() -> None:
    """Should generate a non-empty device ID."""
    device_id = _generate_device_id()
    assert device_id
    assert "-" in device_id
    assert len(device_id) > 5


def test_build_fraud_headers() -> None:
    """Should return dict with required fraud prevention headers."""
    headers = _build_fraud_headers()
    assert "Gov-Client-Connection-Method" in headers
    assert "Gov-Client-Public-IP" in headers
    assert "Gov-Client-Device-ID" in headers
    assert headers["Gov-Client-Connection-Method"] == "OTHER_DIRECT"
    assert headers["Gov-Client-Public-IP"] == "127.0.0.1"


# ---------------------------------------------------------------------------
# Digital link validation
# ---------------------------------------------------------------------------

def test_validate_digital_link_valid(sample_vat_return: VatReturn) -> None:
    """Should pass for a correctly structured VAT return."""
    # box3 = box1 + box2, box5 = box3 - box4
    MtdService._validate_digital_link(sample_vat_return)


def test_validate_digital_link_invalid_box3() -> None:
    """Should raise MtdValidationError if Box 3 != Box 1 + Box 2."""
    vr = VatReturn(
        id=uuid.uuid4(),
        period_id=uuid.uuid4(),
        box1=100,
        box2=0,
        box3=999,  # invalid: should be 100
        box4=0,
        box5=999,  # matches box3 - box4 but box3 is wrong
        box6=0,
        box7=0,
        box8=0,
        box9=0,
    )
    with pytest.raises(MtdValidationError, match="Box 3"):
        MtdService._validate_digital_link(vr)


def test_validate_digital_link_invalid_box5() -> None:
    """Should raise MtdValidationError if Box 5 != Box 3 - Box 4."""
    vr = VatReturn(
        id=uuid.uuid4(),
        period_id=uuid.uuid4(),
        box1=100,
        box2=0,
        box3=100,  # correct
        box4=0,
        box5=999,  # invalid: should be 100
        box6=0,
        box7=0,
        box8=0,
        box9=0,
    )
    with pytest.raises(MtdValidationError, match="Box 5"):
        MtdService._validate_digital_link(vr)


# ---------------------------------------------------------------------------
# build_submission_payload
# ---------------------------------------------------------------------------

def test_build_submission_payload(sample_vat_return: VatReturn) -> None:
    """Should convert pence to GBP and include all 9 box values."""
    payload = MtdService._build_submission_payload(sample_vat_return)
    assert payload["periodKey"] == "#001"
    assert payload["vatDueSales"] == 250.00
    assert payload["vatDueAcquisitions"] == 0.00
    assert payload["totalVatDue"] == 250.00
    assert payload["vatReclaimedCurrPeriod"] == 50.00
    assert payload["netVatDue"] == 200.00
    assert payload["totalValueSalesExVAT"] == 1250.00
    assert payload["totalValuePurchasesExVAT"] == 250.00
    assert payload["totalValueGoodsSuppliedExVAT"] == 0.00
    assert payload["totalAcquisitionsExVAT"] == 0.00
    assert payload["finalised"] is True


def test_build_submission_payload_no_period() -> None:
    """Should raise MtdValidationError when VAT return has no period."""
    vr = VatReturn(
        id=uuid.uuid4(),
        period_id=uuid.uuid4(),
        box1=0, box2=0, box3=0, box4=0, box5=0,
        box6=0, box7=0, box8=0, box9=0,
    )
    vr.period = None
    with pytest.raises(MtdValidationError, match="period"):
        MtdService._build_submission_payload(vr)


# ---------------------------------------------------------------------------
# submit_vat_return
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_vat_return_success(
    mock_db: AsyncMock,
    sample_vat_return: VatReturn,
    hmrc_submit_response: dict,
    hmrc_oauth_response: dict,
) -> None:
    """Should submit a VAT return and store the receipt."""
    # Mock the DB query to return our VAT return
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    mock_db.get = AsyncMock(return_value=sample_vat_return)

    with (
        patch.object(
            MtdService,
            "_get_access_token",
            new_callable=AsyncMock,
            return_value="test-token",
        ),
        patch("src.services.mtd_service.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            return_value=Response(
                201,
                json=hmrc_submit_response,
                request=MagicMock(),
            )
        )
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await MtdService.submit_vat_return(mock_db, sample_vat_return.id)

    assert isinstance(result, SubmitResponse)
    assert result.status == "accepted"
    assert result.submission_id == "BANK"
    assert result.form_bundle_number == "123456789012"
    assert result.payment_indicator == "BANK"
    assert result.charge_ref_number == "XDVAT1234567"
    assert result.vat_return_id == sample_vat_return.id
    assert result.correlation_id
    # Verify DB was updated
    assert sample_vat_return.submission_id == "BANK"
    assert sample_vat_return.submission_status == "accepted"
    assert sample_vat_return.correlation_id is not None
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_submit_vat_return_not_found(mock_db: AsyncMock) -> None:
    """Should raise VatReturnNotFoundError when VAT return doesn't exist."""
    mock_db.get = AsyncMock(return_value=None)

    fake_id = uuid.uuid4()
    with pytest.raises(VatReturnNotFoundError) as exc:
        await MtdService.submit_vat_return(mock_db, fake_id)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_submit_vat_return_already_submitted(
    mock_db: AsyncMock,
    sample_submitted_return: VatReturn,
) -> None:
    """Should raise VatReturnAlreadySubmittedError if already submitted."""
    mock_db.get = AsyncMock(return_value=sample_submitted_return)

    with pytest.raises(VatReturnAlreadySubmittedError) as exc:
        await MtdService.submit_vat_return(mock_db, sample_submitted_return.id)
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_submit_vat_return_hmrc_rejects(
    mock_db: AsyncMock,
    sample_vat_return: VatReturn,
) -> None:
    """Should raise MtdSubmissionError when HMRC rejects the submission."""
    mock_db.get = AsyncMock(return_value=sample_vat_return)

    with (
        patch.object(
            MtdService,
            "_get_access_token",
            new_callable=AsyncMock,
            return_value="test-token",
        ),
        patch("src.services.mtd_service.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        error_body = {"code": "INVALID_PAYLOAD", "message": "Invalid period key"}
        mock_client.post = AsyncMock(
            return_value=Response(
                400,
                json=error_body,
                request=MagicMock(),
            )
        )
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(MtdSubmissionError, match="HMRC rejected"):
            await MtdService.submit_vat_return(mock_db, sample_vat_return.id)


@pytest.mark.asyncio
async def test_submit_vat_return_authentication_failure(
    mock_db: AsyncMock,
    sample_vat_return: VatReturn,
) -> None:
    """Should raise MtdAuthenticationError when OAuth fails."""
    mock_db.get = AsyncMock(return_value=sample_vat_return)

    with patch.object(
        MtdService,
        "_get_access_token",
        new_callable=AsyncMock,
        side_effect=MtdAuthenticationError("auth failed"),
    ):
        with pytest.raises(MtdAuthenticationError, match="auth failed"):
            await MtdService.submit_vat_return(mock_db, sample_vat_return.id)


@pytest.mark.asyncio
async def test_submit_vat_return_retry_on_5xx(
    mock_db: AsyncMock,
    sample_vat_return: VatReturn,
    hmrc_submit_response: dict,
) -> None:
    """Should retry on 5xx errors and succeed eventually."""
    mock_db.get = AsyncMock(return_value=sample_vat_return)

    with (
        patch.object(
            MtdService,
            "_get_access_token",
            new_callable=AsyncMock,
            return_value="test-token",
        ),
        patch("src.services.mtd_service.httpx.AsyncClient") as mock_client_cls,
        patch("src.services.mtd_service.asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_client = AsyncMock()
        # First two calls return 500, third succeeds
        mock_client.post = AsyncMock(
            side_effect=[
                Response(500, json={"error": "server error"}, request=MagicMock()),
                Response(503, json={"error": "unavailable"}, request=MagicMock()),
                Response(201, json=hmrc_submit_response, request=MagicMock()),
            ]
        )
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = await MtdService.submit_vat_return(mock_db, sample_vat_return.id)

    assert result.status == "accepted"
    assert mock_client.post.call_count == 3


# ---------------------------------------------------------------------------
# get_obligations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_obligations_success(
    hmrc_obligations_response: dict,
) -> None:
    """Should return populated ObligationResponse."""
    with (
        patch.object(
            MtdService,
            "_get_access_token",
            new_callable=AsyncMock,
            return_value="test-token",
        ),
        patch("src.services.mtd_service.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            return_value=Response(
                200,
                json=hmrc_obligations_response,
                request=MagicMock(),
            )
        )
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        with patch("src.services.mtd_service.HMRC_VRN", "123456789"):
            result = await MtdService.get_obligations()

    assert isinstance(result, ObligationResponse)
    assert len(result.obligations) == 2
    assert result.obligations[0].period_key == "#001"
    assert result.obligations[0].start == date(2026, 1, 1)
    assert result.obligations[0].end == date(2026, 3, 31)
    assert result.obligations[0].due == date(2026, 5, 7)
    assert result.obligations[0].status == "O"


@pytest.mark.asyncio
async def test_get_obligations_no_vrn() -> None:
    """Should raise MtdServiceError when no VRN is available."""
    with patch("src.services.mtd_service.HMRC_VRN", ""):
        with patch.object(MtdService, "_get_access_token", new_callable=AsyncMock):
            # Reset class-level token
            MtdService._oauth_token = None
            with pytest.raises(MtdServiceError, match="VRN"):
                await MtdService.get_obligations()


@pytest.mark.asyncio
async def test_get_obligations_hmrc_error() -> None:
    """Should raise MtdServiceError on HMRC error response."""
    with (
        patch.object(
            MtdService,
            "_get_access_token",
            new_callable=AsyncMock,
            return_value="test-token",
        ),
        patch("src.services.mtd_service.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            return_value=Response(
                404,
                json={"code": "NOT_FOUND"},
                request=MagicMock(),
            )
        )
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        with patch("src.services.mtd_service.HMRC_VRN", "123456789"):
            with pytest.raises(MtdServiceError, match="404"):
                await MtdService.get_obligations()


# ---------------------------------------------------------------------------
# get_submission_status
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_submission_status_found(
    mock_db: AsyncMock,
    sample_submitted_return: VatReturn,
) -> None:
    """Should return SubmissionStatusResponse for a found submission."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_submitted_return
    mock_db.execute.return_value = mock_result

    result = await MtdService.get_submission_status(mock_db, "SUB-001")

    assert isinstance(result, SubmissionStatusResponse)
    assert result.submission_id == "SUB-001"
    assert result.status == "accepted"
    assert result.vat_return_id == sample_submitted_return.id


@pytest.mark.asyncio
async def test_get_submission_status_not_found(mock_db: AsyncMock) -> None:
    """Should raise VatReturnNotFoundError when not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    with pytest.raises(VatReturnNotFoundError):
        await MtdService.get_submission_status(mock_db, "NONEXISTENT")


# ---------------------------------------------------------------------------
# test_connection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_test_connection_success(hmrc_obligations_response: dict) -> None:
    """Should return connected=True when HMRC API is reachable."""
    with (
        patch.object(
            MtdService,
            "_get_access_token",
            new_callable=AsyncMock,
            return_value="test-token",
        ),
        patch("src.services.mtd_service.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            return_value=Response(
                200,
                json=hmrc_obligations_response,
                request=MagicMock(),
            )
        )
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        with patch("src.services.mtd_service.HMRC_VRN", "123456789"):
            result = await MtdService.test_connection()

    assert isinstance(result, HmrcConnectionResponse)
    assert result.connected is True
    assert "Successfully connected" in result.message
    assert result.obligations_count == 2


@pytest.mark.asyncio
async def test_test_connection_failure() -> None:
    """Should return connected=False when HMRC API is unreachable."""
    with patch("src.services.mtd_service.HMRC_VRN", "123456789"):
        with patch.object(
            MtdService,
            "_get_access_token",
            new_callable=AsyncMock,
            side_effect=MtdAuthenticationError("no credentials"),
        ):
            result = await MtdService.test_connection()

    assert isinstance(result, HmrcConnectionResponse)
    assert result.connected is False
    assert "no credentials" in result.message


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retry_request_success_first_try() -> None:
    """Should succeed on first attempt."""
    async def success_fn():
        return Response(200, json={"ok": True})

    result = await MtdService._retry_request(success_fn)
    assert result.status_code == 200


@pytest.mark.asyncio
async def test_retry_request_5xx_retries() -> None:
    """Should retry on 5xx and eventually succeed."""
    call_count = 0

    async def flaky_fn():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return Response(503, json={"error": "unavailable"})
        return Response(200, json={"ok": True})

    with patch("src.services.mtd_service.asyncio.sleep", new_callable=AsyncMock):
        result = await MtdService._retry_request(flaky_fn)
        assert result.status_code == 200
        assert call_count == 3


@pytest.mark.asyncio
async def test_retry_request_max_retries_exceeded() -> None:
    """Should raise MtdServiceError after all retries fail with connection errors."""
    async def failing_fn():
        import httpx
        raise httpx.ConnectError("connection refused")

    with patch("src.services.mtd_service.asyncio.sleep", new_callable=AsyncMock):
        with pytest.raises(MtdServiceError, match="unreachable"):
            await MtdService._retry_request(failing_fn)


@pytest.mark.asyncio
async def test_retry_request_429_retry_after() -> None:
    """Should retry after 429 with Retry-After header."""
    call_count = 0

    async def rate_limited_fn():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return Response(
                429,
                json={"error": "rate limited"},
                headers={"Retry-After": "0.1"},
            )
        return Response(200, json={"ok": True})

    with patch("src.services.mtd_service.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await MtdService._retry_request(rate_limited_fn)
        assert result.status_code == 200
        assert call_count == 3
        assert mock_sleep.called
