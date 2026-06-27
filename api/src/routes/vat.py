"""FastAPI router for VAT Calculation & MTD Preview — Module 7."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.services.vat_service import (
    VatFlatRateMissingError,
    VatPeriodClosedError,
    VatPeriodNotFoundError,
    VatReturnNotFoundError,
    VatService,
    VatServiceError,
)
from src.validators.vat import (
    VatAdjustmentCreate,
    VatAdjustmentResponse,
    VatAuditResponse,
    VatPeriodCreate,
    VatPeriodListResponse,
    VatPeriodResponse,
    VatReturnCalculationResponse,
    VatReturnResponse,
)

router = APIRouter(prefix="/api/v1/vat", tags=["VAT"])


# ---------------------------------------------------------------------------
# POST /periods — Create VAT period
# ---------------------------------------------------------------------------


@router.post(
    "/periods",
    response_model=VatPeriodResponse,
    summary="Create a new VAT period",
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {"description": "Validation error or missing flat_rate_percentage"},
    },
)
async def create_period(
    data: VatPeriodCreate,
    db: AsyncSession = Depends(get_db),
) -> VatPeriodResponse:
    """Create a new VAT return period (typically quarterly).

    Supports standard, cash, and flat_rate schemes.
    """
    try:
        return await VatService.create_period(db, data)
    except (VatFlatRateMissingError, VatServiceError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# GET /periods — List VAT periods
# ---------------------------------------------------------------------------


@router.get(
    "/periods",
    response_model=VatPeriodListResponse,
    summary="List VAT periods",
    status_code=status.HTTP_200_OK,
)
async def list_periods(
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by status (open|closed)"
    ),
    scheme: Optional[str] = Query(
        None, description="Filter by scheme (standard|cash|flat_rate)"
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> VatPeriodListResponse:
    """List VAT periods with optional status and scheme filters."""
    items, total = await VatService.list_periods(
        db,
        status=status_filter,
        scheme=scheme,
        limit=limit,
        offset=offset,
    )
    return VatPeriodListResponse(periods=items, total=total)


# ---------------------------------------------------------------------------
# POST /periods/{period_id}/calculate — Calculate 9-box return
# ---------------------------------------------------------------------------


@router.post(
    "/periods/{period_id}/calculate",
    response_model=VatReturnCalculationResponse,
    summary="Calculate 9-box VAT return for a period",
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Period not found"},
        422: {"description": "Period is already closed"},
    },
)
async def calculate_return(
    period_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> VatReturnCalculationResponse:
    """Calculate a complete 9-box UK VAT return for the given period.

    Queries all posted transactions within the period and computes:
    - Box 1: VAT due on sales (output VAT)
    - Box 2: VAT due on EU acquisitions (0 for MVP)
    - Box 3: Total output VAT (Box 1 + Box 2)
    - Box 4: VAT reclaimed on purchases (input VAT)
    - Box 5: Net VAT (Box 3 - Box 4). Positive = payable, Negative = reclaimable.
    - Box 6: Total sales excluding VAT
    - Box 7: Total purchases excluding VAT
    - Box 8: EU sales (0 for MVP)
    - Box 9: EU acquisitions (0 for MVP)

    Includes full MTD digital-link audit trail.
    """
    try:
        return await VatService.calculate_return(db, period_id)
    except VatPeriodNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except VatPeriodClosedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except VatFlatRateMissingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# GET /returns/{return_id} — Get VAT return
# ---------------------------------------------------------------------------


@router.get(
    "/returns/{return_id}",
    response_model=VatReturnResponse,
    summary="Get a VAT return by ID",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Return not found"}},
)
async def get_return(
    return_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> VatReturnResponse:
    """Return a single VAT return with its 9-box figures."""
    vat_return = await VatService.get_return(db, return_id)
    if vat_return is None:
        raise HTTPException(
            status_code=404,
            detail=f"VAT return '{return_id}' not found",
        )
    return vat_return


# ---------------------------------------------------------------------------
# GET /returns/{return_id}/audit — Audit trail
# ---------------------------------------------------------------------------


@router.get(
    "/returns/{return_id}/audit",
    response_model=VatAuditResponse,
    summary="Get VAT return audit trail",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Return not found"}},
)
async def get_audit_trail(
    return_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> VatAuditResponse:
    """Return the full MTD digital-link audit trail for a VAT return.

    Shows how each box figure is derived from source transactions.
    """
    try:
        return await VatService.get_audit_trail(db, return_id)
    except VatReturnNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except VatPeriodNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /returns/{return_id}/adjustment — Manual adjustment
# ---------------------------------------------------------------------------


@router.post(
    "/returns/{return_id}/adjustment",
    response_model=VatAdjustmentResponse,
    summary="Add a manual adjustment to a VAT return box",
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Return not found"},
        422: {"description": "Invalid box number"},
    },
)
async def add_adjustment(
    return_id: uuid.UUID,
    data: VatAdjustmentCreate,
    db: AsyncSession = Depends(get_db),
) -> VatAdjustmentResponse:
    """Add a manual adjustment to any of the 9 boxes.

    Updates the box value and records the adjustment for MTD audit trail.
    Dependent boxes (box3 = box1 + box2, box5 = box3 - box4) are recalculated.
    """
    try:
        return await VatService.add_adjustment(db, return_id, data)
    except VatReturnNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except VatServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
