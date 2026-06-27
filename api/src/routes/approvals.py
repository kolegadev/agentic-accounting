"""FastAPI router for Approval Workflows — Phase 2."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.middleware.auth import get_current_user, require_role
from src.models.user import User
from src.services.approval_service import (
    AlreadyDecidedError,
    ApprovalNotFoundError,
    ApprovalService,
    ApprovalServiceError,
    InsufficientRoleError,
    RequestNotPendingError,
    StepNotFoundError,
)
from src.validators.approval import (
    ApprovalAction,
    ApprovalCreate,
    ApprovalListResponse,
    ApprovalResponse,
)

router = APIRouter(prefix="/api/v1/approvals", tags=["Approvals"])


# ---------------------------------------------------------------------------
# POST / — Create approval request
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=ApprovalResponse,
    summary="Create a new approval request",
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"description": "Forbidden"},
        422: {"description": "Validation error"},
    },
)
async def create_approval(
    data: ApprovalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Create an approval request. Levels auto-calculated from threshold_amount.

    If amount < £500, the request is auto-approved.
    """
    return await ApprovalService.create_request(
        db,
        data,
        current_user.id,
    )


# ---------------------------------------------------------------------------
# GET /pending — My pending approvals
# ---------------------------------------------------------------------------

@router.get(
    "/pending",
    response_model=ApprovalListResponse,
    summary="Get pending approvals awaiting current user",
    status_code=status.HTTP_200_OK,
)
async def pending_approvals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalListResponse:
    """Return all pending approval requests where current user can approve."""
    approvals = await ApprovalService.get_pending_approvals(db, current_user.id)
    return ApprovalListResponse(approvals=approvals, total=len(approvals))


# ---------------------------------------------------------------------------
# GET / — List all approvals (Admin/Owner)
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=ApprovalListResponse,
    summary="List all approval requests",
    status_code=status.HTTP_200_OK,
)
async def list_approvals(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
) -> ApprovalListResponse:
    """List all approval requests. Admin/Owner only."""
    approvals, total = await ApprovalService.list_requests(
        db,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    return ApprovalListResponse(approvals=approvals, total=total)


# ---------------------------------------------------------------------------
# GET /{id} — Get approval detail with steps
# ---------------------------------------------------------------------------

@router.get(
    "/{approval_id}",
    response_model=ApprovalResponse,
    summary="Get approval request detail with steps",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Approval request not found"}},
)
async def get_approval(
    approval_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Return an approval request with all its steps."""
    result = await ApprovalService.get_request(db, approval_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Approval request '{approval_id}' not found",
        )
    return result


# ---------------------------------------------------------------------------
# POST /{id}/approve — Approve current level
# ---------------------------------------------------------------------------

@router.post(
    "/{approval_id}/approve",
    response_model=ApprovalResponse,
    summary="Approve the current level of an approval request",
    status_code=status.HTTP_200_OK,
    responses={
        403: {"description": "Insufficient role for this level"},
        404: {"description": "Approval request not found"},
        409: {"description": "Step already decided"},
        422: {"description": "Request not pending"},
    },
)
async def approve_approval(
    approval_id: uuid.UUID,
    action: ApprovalAction = ApprovalAction(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Approve the current approval level. Advances to next level if available."""
    try:
        return await ApprovalService.approve_step(
            db,
            approval_id,
            current_user.id,
            action.comment,
        )
    except ApprovalNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except RequestNotPendingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except StepNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except AlreadyDecidedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except InsufficientRoleError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except ApprovalServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /{id}/reject — Reject + cancel
# ---------------------------------------------------------------------------

@router.post(
    "/{approval_id}/reject",
    response_model=ApprovalResponse,
    summary="Reject the current level — cancels entire request",
    status_code=status.HTTP_200_OK,
    responses={
        403: {"description": "Insufficient role for this level"},
        404: {"description": "Approval request not found"},
        409: {"description": "Step already decided"},
        422: {"description": "Request not pending"},
    },
)
async def reject_approval(
    approval_id: uuid.UUID,
    action: ApprovalAction = ApprovalAction(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Reject the current approval level. Cancels the entire request."""
    try:
        return await ApprovalService.reject_step(
            db,
            approval_id,
            current_user.id,
            action.comment,
        )
    except ApprovalNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except RequestNotPendingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except StepNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except AlreadyDecidedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except InsufficientRoleError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except ApprovalServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
