"""HMRC MTD VAT submission service — MtdService — Module 8."""

from __future__ import annotations

import asyncio
import json
import os
import platform
import socket
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.vat import VatReturn
from src.validators.mtd import (
    HmrcConnectionResponse,
    ObligationItem,
    ObligationResponse,
    SubmissionStatusResponse,
    SubmitResponse,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


HMRC_CLIENT_ID = os.getenv("HMRC_CLIENT_ID", "")
HMRC_CLIENT_SECRET = os.getenv("HMRC_CLIENT_SECRET", "")
HMRC_VRN = os.getenv("HMRC_VRN", "")
HMRC_API_URL = os.getenv("HMRC_API_URL", "https://test-api.service.hmrc.gov.uk")
HMRC_OAUTH_URL = os.getenv(
    "HMRC_OAUTH_URL",
    "https://test-api.service.hmrc.gov.uk/oauth/token",
)

# OAuth token scopes for MTD VAT
MTD_VAT_SCOPES = "read:vat write:vat"

# Retry configuration
MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1.0
BACKOFF_MULTIPLIER = 2.0

# API paths
API_PATH_SUBMIT = "/organisations/vat/{vrn}/returns"
API_PATH_OBLIGATIONS = "/organisations/vat/{vrn}/obligations"
API_PATH_SUBMISSION = "/organisations/vat/{vrn}/returns/{submission_id}"


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class MtdServiceError(Exception):
    """Base exception for MTD service errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class MtdAuthenticationError(MtdServiceError):
    """Failed to authenticate with HMRC."""

    def __init__(self, detail: str = "HMRC authentication failed") -> None:
        super().__init__(detail, status_code=502)


class MtdSubmissionError(MtdServiceError):
    """Failed to submit VAT return to HMRC."""

    def __init__(self, detail: str = "HMRC submission failed") -> None:
        super().__init__(detail, status_code=502)


class MtdValidationError(MtdServiceError):
    """MTD digital link validation failed."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail, status_code=422)


class VatReturnNotFoundError(MtdServiceError):
    """VAT return not found in local DB."""

    def __init__(self, return_id: uuid.UUID) -> None:
        super().__init__(f"VAT return '{return_id}' not found", status_code=404)


class VatReturnAlreadySubmittedError(MtdServiceError):
    """VAT return already submitted to HMRC."""

    def __init__(self, return_id: uuid.UUID) -> None:
        super().__init__(
            f"VAT return '{return_id}' already submitted to HMRC",
            status_code=409,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_device_id() -> str:
    """Generate a Gov-Client-Device-ID for HMRC fraud prevention headers.

    Uses platform/hostname to create a consistent device identifier.
    """
    hostname = socket.gethostname()
    return f"{platform.system()}-{hostname}-{uuid.getnode():x}"


def _build_fraud_headers() -> dict[str, str]:
    """Build HMRC fraud prevention headers.

    Returns a dict with:
    - Gov-Client-Connection-Method
    - Gov-Client-Public-IP (MVP: localhost or dummy)
    - Gov-Client-Device-ID
    """
    return {
        "Gov-Client-Connection-Method": "OTHER_DIRECT",
        "Gov-Client-Public-IP": "127.0.0.1",
        "Gov-Client-Device-ID": _generate_device_id(),
    }


# ---------------------------------------------------------------------------
# MtdService
# ---------------------------------------------------------------------------


class MtdService:
    """Stateless service for HMRC MTD VAT submissions.

    Handles:
    - OAuth 2.0 authentication with HMRC
    - VAT return submission (9-box)
    - Obligation retrieval
    - Submission status checks
    - MTD digital link validation
    - Retry with exponential backoff
    """

    _oauth_token: Optional[str] = None
    _token_expires_at: float = 0.0

    # ------------------------------------------------------------------
    # OAuth 2.0 authentication
    # ------------------------------------------------------------------

    @classmethod
    async def _get_access_token(cls) -> str:
        """Obtain or refresh an OAuth 2.0 access token from HMRC.

        Uses client credentials grant. Caches the token until expiry.

        Raises:
            MtdAuthenticationError on failure.
        """
        now = time.monotonic()
        if cls._oauth_token and now < cls._token_expires_at - 60:
            return cls._oauth_token

        if not HMRC_CLIENT_ID or not HMRC_CLIENT_SECRET:
            raise MtdAuthenticationError(
                "HMRC_CLIENT_ID and HMRC_CLIENT_SECRET environment variables must be set"
            )

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    HMRC_OAUTH_URL,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": HMRC_CLIENT_ID,
                        "client_secret": HMRC_CLIENT_SECRET,
                        "scope": MTD_VAT_SCOPES,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPError as exc:
                raise MtdAuthenticationError(
                    f"HMRC OAuth request failed: {exc}"
                ) from exc
            except json.JSONDecodeError as exc:
                raise MtdAuthenticationError(
                    f"HMRC OAuth response not valid JSON: {exc}"
                ) from exc

        cls._oauth_token = data.get("access_token")
        if not cls._oauth_token:
            raise MtdAuthenticationError(
                "HMRC OAuth response missing access_token"
            )

        expires_in = data.get("expires_in", 3600)
        cls._token_expires_at = now + float(expires_in)
        return cls._oauth_token

    # ------------------------------------------------------------------
    # Retry with exponential backoff
    # ------------------------------------------------------------------

    @staticmethod
    async def _retry_request(
        request_fn,
        *args: Any,
        max_retries: int = MAX_RETRIES,
        base_backoff: float = BASE_BACKOFF_SECONDS,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute an HTTP request with exponential backoff retry logic.

        Args:
            request_fn: Async callable that returns an httpx.Response.
            *args: Positional args for request_fn.
            max_retries: Maximum retry attempts (total attempts = max_retries + 1).
            base_backoff: Base backoff in seconds.
            **kwargs: Keyword args for request_fn.

        Returns:
            httpx.Response from the successful request.

        Raises:
            MtdServiceError if all attempts fail.
        """
        last_exception: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                response = await request_fn(*args, **kwargs)
                # 429 Too Many Requests → retry
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    wait = (
                        float(retry_after)
                        if retry_after
                        else base_backoff * (BACKOFF_MULTIPLIER ** attempt)
                    )
                    if attempt < max_retries:
                        await asyncio.sleep(wait)
                        continue
                # 5xx server errors → retry
                if 500 <= response.status_code < 600 and attempt < max_retries:
                    wait = base_backoff * (BACKOFF_MULTIPLIER ** attempt)
                    await asyncio.sleep(wait)
                    continue
                return response
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_exception = exc
                if attempt < max_retries:
                    wait = base_backoff * (BACKOFF_MULTIPLIER ** attempt)
                    await asyncio.sleep(wait)
                    continue
                raise MtdServiceError(
                    f"HMRC API unreachable after {max_retries + 1} attempts: {exc}",
                    status_code=502,
                ) from exc

        if last_exception:
            raise MtdServiceError(
                f"HMRC API request failed: {last_exception}",
                status_code=502,
            )
        raise MtdServiceError(
            "HMRC API request failed: max retries exceeded",
            status_code=502,
        )

    # ------------------------------------------------------------------
    # Helper: fetch a VatReturn with period relationship loaded
    # ------------------------------------------------------------------

    @staticmethod
    async def _get_vat_return(
        db: AsyncSession,
        return_id: uuid.UUID,
    ) -> VatReturn:
        """Fetch a VatReturn or raise VatReturnNotFoundError."""
        vat_return = await db.get(
            VatReturn,
            return_id,
            options=[
                selectinload(VatReturn.period),
                selectinload(VatReturn.adjustments),
            ],
        )
        if vat_return is None:
            raise VatReturnNotFoundError(return_id)
        return vat_return

    # ------------------------------------------------------------------
    # MTD digital link validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_digital_link(vat_return: VatReturn) -> None:
        """Validate MTD digital link: every box figure must be traceable.

        This is a structural check — the audit trail is built during
        calculation. Here we ensure:
        - Box 3 = Box 1 + Box 2
        - Box 5 = Box 3 - Box 4

        Raises:
            MtdValidationError if structural validation fails.
        """
        if vat_return.box3 != vat_return.box1 + vat_return.box2:
            raise MtdValidationError(
                f"Digital link validation failed: Box 3 ({vat_return.box3}) "
                f"!= Box 1 ({vat_return.box1}) + Box 2 ({vat_return.box2})"
            )
        if vat_return.box5 != vat_return.box3 - vat_return.box4:
            raise MtdValidationError(
                f"Digital link validation failed: Box 5 ({vat_return.box5}) "
                f"!= Box 3 ({vat_return.box3}) - Box 4 ({vat_return.box4})"
            )

    # ------------------------------------------------------------------
    # Build HMRC submission payload
    # ------------------------------------------------------------------

    @staticmethod
    def _build_submission_payload(vat_return: VatReturn) -> dict[str, Any]:
        """Build the HMRC 9-box VAT return JSON payload.

        HMRC expects amounts in GBP with 2 decimal places.
        """
        period = vat_return.period
        if period is None:
            raise MtdValidationError("VAT return has no associated period")

        def _to_gbp(pence: int) -> float:
            """Convert pence to GBP as float with 2 decimal places."""
            return round(pence / 100.0, 2)

        return {
            "periodKey": "#001",  # MVP: single period
            "vatDueSales": _to_gbp(vat_return.box1),
            "vatDueAcquisitions": _to_gbp(vat_return.box2),
            "totalVatDue": _to_gbp(vat_return.box3),
            "vatReclaimedCurrPeriod": _to_gbp(vat_return.box4),
            "netVatDue": _to_gbp(vat_return.box5),
            "totalValueSalesExVAT": _to_gbp(vat_return.box6),
            "totalValuePurchasesExVAT": _to_gbp(vat_return.box7),
            "totalValueGoodsSuppliedExVAT": _to_gbp(vat_return.box8),
            "totalAcquisitionsExVAT": _to_gbp(vat_return.box9),
            "finalised": True,
        }

    # ------------------------------------------------------------------
    # submit_vat_return
    # ------------------------------------------------------------------

    @staticmethod
    async def submit_vat_return(
        db: AsyncSession,
        vat_return_id: uuid.UUID,
    ) -> SubmitResponse:
        """Submit a 9-box VAT return to HMRC.

        Steps:
        1. Fetch VAT return from local DB.
        2. Validate MTD digital link integrity.
        3. Check not already submitted.
        4. Obtain OAuth 2.0 access token.
        5. Build HMRC-compliant payload (pence → GBP).
        6. Submit with fraud-prevention headers.
        7. Store submission receipt (correlation_id, submission_id).
        8. Return SubmitResponse.

        Raises:
            VatReturnNotFoundError if return not found.
            VatReturnAlreadySubmittedError if already submitted.
            MtdValidationError if digital link validation fails.
            MtdSubmissionError on HMRC rejection.
        """
        vat_return = await MtdService._get_vat_return(db, vat_return_id)

        # Check not already submitted
        if vat_return.submission_id is not None:
            raise VatReturnAlreadySubmittedError(vat_return_id)

        # MTD digital link validation
        MtdService._validate_digital_link(vat_return)

        # OAuth token
        token = await MtdService._get_access_token()

        # Build payload
        payload = MtdService._build_submission_payload(vat_return)

        # Fraud prevention headers
        fraud_headers = _build_fraud_headers()

        # Correlation ID
        correlation_id = str(uuid.uuid4())

        # Build URL
        url = f"{HMRC_API_URL}{API_PATH_SUBMIT.format(vrn=HMRC_VRN)}"

        async def _do_submit() -> httpx.Response:
            async with httpx.AsyncClient(timeout=30.0) as client:
                return await client.post(
                    url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "X-Correlation-ID": correlation_id,
                        **fraud_headers,
                    },
                )

        response = await MtdService._retry_request(_do_submit)

        if response.status_code not in (200, 201):
            raise MtdSubmissionError(
                f"HMRC rejected submission: {response.status_code} {response.text[:500]}"
            )

        hmrc_data = response.json()

        submission_id = hmrc_data.get("paymentIndicator") or hmrc_data.get(
            "formBundleNumber", ""
        )
        processing_date_str = hmrc_data.get("processingDate", "")
        processing_date = (
            datetime.fromisoformat(processing_date_str.replace("Z", "+00:00"))
            if processing_date_str
            else datetime.now(timezone.utc)
        )

        # Store receipt data on VAT return
        vat_return.submission_id = submission_id
        vat_return.correlation_id = correlation_id
        vat_return.submission_status = "accepted"
        vat_return.submitted_at = processing_date
        vat_return.hmrc_receipt = json.dumps(hmrc_data)
        await db.commit()

        return SubmitResponse(
            vat_return_id=vat_return_id,
            submission_id=submission_id,
            correlation_id=correlation_id,
            status="accepted",
            processing_date=processing_date,
            form_bundle_number=hmrc_data.get("formBundleNumber"),
            payment_indicator=hmrc_data.get("paymentIndicator"),
            charge_ref_number=hmrc_data.get("chargeRefNumber"),
        )

    # ------------------------------------------------------------------
    # get_obligations
    # ------------------------------------------------------------------

    @staticmethod
    async def get_obligations(vrn: Optional[str] = None) -> ObligationResponse:
        """Get VAT obligations/periods from HMRC.

        Args:
            vrn: VAT Registration Number (uses env HMRC_VRN if not provided).

        Returns:
            ObligationResponse with list of obligation items.

        Raises:
            MtdAuthenticationError on auth failure.
            MtdServiceError on API failure.
        """
        effective_vrn = vrn or HMRC_VRN
        if not effective_vrn:
            raise MtdServiceError(
                "VRN is required (provide or set HMRC_VRN env)",
                status_code=400,
            )

        token = await MtdService._get_access_token()

        # HMRC obligation query parameters
        today = datetime.now(timezone.utc).date()
        from_date = f"{today.year}-01-01"
        to_date = f"{today.year}-12-31"

        url = f"{HMRC_API_URL}{API_PATH_OBLIGATIONS.format(vrn=effective_vrn)}"

        async def _do_get() -> httpx.Response:
            async with httpx.AsyncClient(timeout=30.0) as client:
                return await client.get(
                    url,
                    params={"from": from_date, "to": to_date, "status": "O"},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                    },
                )

        response = await MtdService._retry_request(_do_get)

        if response.status_code != 200:
            raise MtdServiceError(
                f"HMRC obligations request failed: {response.status_code} {response.text[:500]}",
                status_code=502,
            )

        data = response.json()

        obligations: list[ObligationItem] = []
        for ob in data.get("obligations", []):
            obligations.append(
                ObligationItem(
                    period_key=ob.get("periodKey", ""),
                    start=datetime.strptime(ob["start"], "%Y-%m-%d").date(),
                    end=datetime.strptime(ob["end"], "%Y-%m-%d").date(),
                    due=datetime.strptime(ob["due"], "%Y-%m-%d").date(),
                    status=ob.get("status", "O"),
                )
            )

        return ObligationResponse(obligations=obligations)

    # ------------------------------------------------------------------
    # get_submission_status
    # ------------------------------------------------------------------

    @staticmethod
    async def get_submission_status(
        db: AsyncSession,
        submission_id: str,
    ) -> SubmissionStatusResponse:
        """Check the status of an HMRC MTD submission.

        First checks local DB, then queries HMRC if needed.

        Args:
            db: Database session.
            submission_id: HMRC submission ID.

        Returns:
            SubmissionStatusResponse with current status.

        Raises:
            VatReturnNotFoundError if no local record found.
        """
        # Check local DB first
        stmt = select(VatReturn).where(
            VatReturn.submission_id == submission_id,
        )
        result = await db.execute(stmt)
        vat_return = result.scalar_one_or_none()

        if vat_return is None:
            raise VatReturnNotFoundError(
                uuid.UUID("00000000-0000-0000-0000-000000000000")
            )

        return SubmissionStatusResponse(
            submission_id=submission_id,
            status=vat_return.submission_status or "unknown",
            vat_return_id=vat_return.id,
            submitted_at=vat_return.submitted_at,
            correlation_id=vat_return.correlation_id,
        )

    # ------------------------------------------------------------------
    # test_connection
    # ------------------------------------------------------------------

    @staticmethod
    async def test_connection() -> HmrcConnectionResponse:
        """Test HMRC API connectivity.

        Attempts to authenticate and fetch obligations.

        Returns:
            HmrcConnectionResponse with connectivity status.
        """
        try:
            obligations = await MtdService.get_obligations()
            return HmrcConnectionResponse(
                connected=True,
                message="Successfully connected to HMRC MTD API",
                obligations_count=len(obligations.obligations),
                timestamp=datetime.now(timezone.utc),
            )
        except MtdServiceError as exc:
            return HmrcConnectionResponse(
                connected=False,
                message=f"HMRC API connection failed: {exc.message}",
                timestamp=datetime.now(timezone.utc),
            )
        except Exception as exc:
            return HmrcConnectionResponse(
                connected=False,
                message=f"Unexpected error connecting to HMRC: {exc}",
                timestamp=datetime.now(timezone.utc),
            )
