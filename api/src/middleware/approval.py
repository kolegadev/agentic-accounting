"""Approval middleware — threshold-based approval routing for write operations.

Provides `require_approval` dependency that auto-approves small amounts
and creates approval requests for amounts above the threshold.
"""

from __future__ import annotations

import uuid
from typing import Callable, Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.middleware.auth import get_current_user
from src.models.user import User
from src.services.approval_service import (
    AUTO_APPROVE_THRESHOLD,
    ApprovalService,
    ApprovalServiceError,
)
from src.validators.approval import ApprovalCreate

# ---------------------------------------------------------------------------
# Threshold constants (imported from service for single source of truth)
# ---------------------------------------------------------------------------

THRESHOLD_AUTO = AUTO_APPROVE_THRESHOLD  # 50000 pence = £500.00


# ---------------------------------------------------------------------------
# require_approval — FastAPI dependency factory
# ---------------------------------------------------------------------------


def require_approval(
    amount_pence: int,
    *,
    transaction_id: Optional[uuid.UUID] = None,
    invoice_id: Optional[uuid.UUID] = None,
    vat_return_id: Optional[uuid.UUID] = None,
    reason: Optional[str] = None,
) -> Callable:
    """Return a FastAPI dependency that gates write operations behind approval.

    Auto-approves amounts below £500.  For amounts >= £500, creates an
    approval request and returns HTTP 202 with the approval details
    (the client must then wait for approval before the operation completes).

    Usage::

        @router.post("/transactions")
        async def create_transaction(
            payload: TransactionCreate,
            current_user: User = Depends(get_current_user),
            db: AsyncSession = Depends(get_db),
            _approved: None = Depends(require_approval(
                payload.total_amount,
                reason="Creating large transaction",
            )),
        ):
            # Reaches here only for amounts < £500 (auto-approved)
            ...

    Args:
        amount_pence: Monetary amount in pence for threshold comparison.
        transaction_id: Optional FK to the transaction entity.
        invoice_id: Optional FK to the invoice entity.
        vat_return_id: Optional FK to the VAT return entity.
        reason: Optional human-readable reason for the approval request.

    Returns:
        A FastAPI dependency.  If the amount is < £500 the dependency
        resolves to ``None`` (pass-through).  Otherwise it raises an
        ``HTTPException(202)`` with the pending approval request details.
    """

    async def approval_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        # Auto-approve: amount below threshold → proceed
        if amount_pence < THRESHOLD_AUTO:
            return

        # Create an approval request and halt with 202
        data = ApprovalCreate(
            transaction_id=transaction_id,
            invoice_id=invoice_id,
            vat_return_id=vat_return_id,
            threshold_amount=amount_pence,
            reason=reason or f"Approval required for amount: {amount_pence}p",
        )
        try:
            approval = await ApprovalService.create_request(
                db,
                data,
                current_user.id,
            )
        except ApprovalServiceError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail=exc.message,
            )

        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail={
                "message": "Approval required",
                "approval_id": str(approval.id),
                "status": approval.status,
                "current_level": approval.current_level,
                "total_levels": approval.total_levels,
            },
        )

    return approval_checker
