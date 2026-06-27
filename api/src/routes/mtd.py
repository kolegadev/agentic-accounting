"""FastAPI router for HMRC MTD VAT Submissions — Module 8."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.services.mtd_service import (
    MtdAuthenticationError,
    MtdService,
    MtdServiceError,
    MtdSubmissionError,
    MtdValidationError,
    VatReturnAlreadySubmittedError,
    VatReturnNotFoundError,
)
from src.validators.mtd import (
    ObligationResponse,
    SubmissionStatusResponse,
    SubmitResponse,
    HmrcConnectionResponse,
)

router = APIRouter(prefix="/api/v1/mtd", tags=["MTD - HMRC"])


# ---------------------------------------------------------------------------
# POST /submit/{vat_return_id} — Submit VAT return to HMRC
# ---------------------------------------------------------------------------


@router.post(
    "/submit/{vat_return_id}",
    response_model=SubmitResponse,
    summary="Submit a 9-box VAT return to HMRC",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "VAT return not found"},
        409: {"description": "VAT return already submitted"},
        422: {"description": "MTD digital link validation failed"},
        502: {"description": "HMRC submission or authentication failure"},
    },
)
async def submit_vat_return(
    vat_return_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SubmitResponse:
    """Submit a calculated 9-box UK VAT return to HMRC's MTD VAT API.

    Performs MTD digital-link validation before submission:
    - All 9 box figures must be traceable to source transactions.
    - Box 3 = Box 1 + Box 2, Box 5 = Box 3 - Box 4.

    Stores the HMRC correlation ID and submission receipt upon success.

    Requires OAuth 2.0 credentials (HMRC_CLIENT_ID, HMRC_CLIENT_SECRET).
    Includes fraud-prevention headers as required by HMRC.
    """
    try:
        return await MtdService.submit_vat_return(db, vat_return_id)
    except VatReturnNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except VatReturnAlreadySubmittedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except MtdValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except MtdAuthenticationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except MtdSubmissionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except MtdServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# GET /obligations — Get VAT obligations from HMRC
# ---------------------------------------------------------------------------


@router.get(
    "/obligations",
    response_model=ObligationResponse,
    summary="Get VAT obligations from HMRC",
    status_code=status.HTTP_200_OK,
    responses={
        502: {"description": "HMRC API unreachable"},
    },
)
async def get_obligations() -> ObligationResponse:
    """Fetch open VAT obligations (filing periods) from HMRC MTD API.

    Returns a list of open periods with their due dates.
    Uses HMRC_VRN from environment if no query parameter provided.
    """
    try:
        return await MtdService.get_obligations()
    except MtdServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# GET /submissions/{submission_id} — Check submission status
# ---------------------------------------------------------------------------


@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionStatusResponse,
    summary="Check HMRC submission status",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Submission not found locally"},
    },
)
async def get_submission_status(
    submission_id: str,
    db: AsyncSession = Depends(get_db),
) -> SubmissionStatusResponse:
    """Check the status of a previously submitted VAT return.

    Returns the current status (pending/accepted/rejected) and metadata.
    Queries the local database for stored submission receipts.
    """
    try:
        return await MtdService.get_submission_status(db, submission_id)
    except VatReturnNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except MtdServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# GET /test-connection — Test HMRC API connectivity
# ---------------------------------------------------------------------------


@router.get(
    "/test-connection",
    response_model=HmrcConnectionResponse,
    summary="Test HMRC API connectivity",
    status_code=status.HTTP_200_OK,
)
async def test_connection() -> HmrcConnectionResponse:
    """Test connectivity to HMRC's MTD VAT API.

    Attempts OAuth 2.0 authentication and fetches obligations.
    Use this to verify API credentials and network connectivity.
    """
    return await MtdService.test_connection()
