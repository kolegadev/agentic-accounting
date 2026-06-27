"""Business logic for Approval Workflows — ApprovalService.

Handles multi-level approval for transactions, invoices, and VAT returns.
Threshold tiers:
  0-£500      = 1 level  (auto-approve)
  £500-£2,000 = 2 levels
  >£2,000     = 3 levels

Required approvers per tier:
  Level 1 = bookkeeper, accountant
  Level 2 = accountant, admin
  Level 3 = admin, owner
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.approval import ApprovalRequest, ApprovalStep
from src.models.user import User
from src.validators.approval import (
    ApprovalCreate,
    ApprovalResponse,
    ApprovalStepResponse,
    ApprovalListResponse,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class ApprovalServiceError(Exception):
    """Base exception for approval service errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ApprovalNotFoundError(ApprovalServiceError):
    """Approval request not found."""

    def __init__(self, approval_id: uuid.UUID) -> None:
        super().__init__(
            f"Approval request '{approval_id}' not found",
            status_code=404,
        )


class StepNotFoundError(ApprovalServiceError):
    """Approval step not found."""

    def __init__(self, approval_id: uuid.UUID, level: int) -> None:
        super().__init__(
            f"Approval step for request '{approval_id}' level {level} not found",
            status_code=404,
        )


class AlreadyDecidedError(ApprovalServiceError):
    """Step has already been approved or rejected."""

    def __init__(self, approval_id: uuid.UUID, level: int, current_status: str) -> None:
        super().__init__(
            f"Approval step level {level} for request '{approval_id}' "
            f"is already '{current_status}'",
            status_code=409,
        )


class InsufficientRoleError(ApprovalServiceError):
    """User role is not sufficient for this approval level."""

    def __init__(self, level: int, user_role: str, allowed_roles: tuple[str, ...]) -> None:
        super().__init__(
            f"User role '{user_role}' is not sufficient for level {level}. "
            f"Required: one of {allowed_roles}",
            status_code=403,
        )


class RequestNotPendingError(ApprovalServiceError):
    """Approval request is not in pending status."""

    def __init__(self, approval_id: uuid.UUID, current_status: str) -> None:
        super().__init__(
            f"Approval request '{approval_id}' has status '{current_status}', "
            f"expected 'pending'",
            status_code=422,
        )


# ---------------------------------------------------------------------------
# Threshold tier helpers
# ---------------------------------------------------------------------------

# Amount boundaries in pence
AUTO_APPROVE_THRESHOLD = 50000   # £500.00
TWO_LEVEL_THRESHOLD = 200000    # £2,000.00

# Allowed roles per level
LEVEL_ROLES: dict[int, tuple[str, ...]] = {
    1: ("bookkeeper", "accountant"),
    2: ("accountant", "admin"),
    3: ("admin", "owner"),
}


def calculate_levels(amount_pence: int) -> int:
    """Return the number of approval levels required for a given amount.

    Tier 1 (0-£500):     1 level — auto-approve
    Tier 2 (£500-£2,000): 2 levels
    Tier 3 (>£2,000):     3 levels
    """
    if amount_pence < AUTO_APPROVE_THRESHOLD:
        return 1
    elif amount_pence <= TWO_LEVEL_THRESHOLD:
        return 2
    else:
        return 3


# ---------------------------------------------------------------------------
# ApprovalService
# ---------------------------------------------------------------------------

class ApprovalService:
    """Stateless service for approval request CRUD and lifecycle."""

    # ------------------------------------------------------------------
    # Response mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _step_to_response(step: ApprovalStep) -> ApprovalStepResponse:
        """Map an ORM ApprovalStep to an ApprovalStepResponse."""
        return ApprovalStepResponse(
            id=step.id,
            approval_request_id=step.approval_request_id,
            approver_id=step.approver_id,
            level=step.level,
            status=step.status,
            comment=step.comment,
            decided_at=step.decided_at,
        )

    @staticmethod
    def _request_to_response(request: ApprovalRequest) -> ApprovalResponse:
        """Map an ORM ApprovalRequest to an ApprovalResponse."""
        return ApprovalResponse(
            id=request.id,
            transaction_id=request.transaction_id,
            invoice_id=request.invoice_id,
            vat_return_id=request.vat_return_id,
            status=request.status,
            requested_by=request.requested_by,
            current_level=request.current_level,
            total_levels=request.total_levels,
            reason=request.reason,
            threshold_amount=request.threshold_amount,
            steps=[
                ApprovalService._step_to_response(s)
                for s in (request.steps or [])
            ],
            created_at=request.created_at,
            updated_at=request.updated_at,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    async def create_request(
        db: AsyncSession,
        data: ApprovalCreate,
        requested_by: uuid.UUID,
    ) -> ApprovalResponse:
        """Create a new approval request with auto-calculated levels.

        If threshold_amount < £500 (50000 pence), the request is auto-approved.
        Otherwise, approval steps are created for each level.
        """
        total_levels = calculate_levels(data.threshold_amount)

        approval_request = ApprovalRequest(
            transaction_id=data.transaction_id,
            invoice_id=data.invoice_id,
            vat_return_id=data.vat_return_id,
            status="pending",
            requested_by=requested_by,
            current_level=1,
            total_levels=total_levels,
            reason=data.reason,
            threshold_amount=data.threshold_amount,
        )
        db.add(approval_request)
        await db.flush()  # Get approval_request.id

        # Create steps for each level
        for level in range(1, total_levels + 1):
            step = ApprovalStep(
                approval_request_id=approval_request.id,
                approver_id=None,
                level=level,
                status="pending",
                comment=None,
                decided_at=None,
            )
            db.add(step)

        await db.commit()

        # Auto-approve if within auto-approve threshold
        if data.threshold_amount < AUTO_APPROVE_THRESHOLD:
            return await ApprovalService.auto_approve(db, approval_request.id)

        await db.refresh(approval_request, attribute_names=["steps"])
        return ApprovalService._request_to_response(approval_request)

    @staticmethod
    async def get_pending_approvals(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[ApprovalResponse]:
        """Get all pending approval requests awaiting this user's approval.

        Returns requests where the current_level step is pending and the
        user's role is allowed for that level.
        """
        # Get user role
        user_stmt = select(User).where(User.id == user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if user is None:
            return []

        user_role = user.role

        # Load all pending requests with their steps
        stmt = (
            select(ApprovalRequest)
            .where(ApprovalRequest.status == "pending")
            .options(selectinload(ApprovalRequest.steps))
            .order_by(ApprovalRequest.created_at.desc())
        )
        result = await db.execute(stmt)
        requests = result.scalars().all()

        # Filter: only return requests where user's role can approve the current level
        pending: list[ApprovalResponse] = []
        for req in requests:
            allowed_roles = LEVEL_ROLES.get(req.current_level)
            if allowed_roles and user_role in allowed_roles:
                pending.append(ApprovalService._request_to_response(req))

        return pending

    @staticmethod
    async def approve_step(
        db: AsyncSession,
        approval_id: uuid.UUID,
        user_id: uuid.UUID,
        comment: Optional[str] = None,
    ) -> ApprovalResponse:
        """Approve the current level of an approval request.

        Moves to the next level if available, otherwise marks request as fully approved.
        """
        # Load request with steps
        stmt = (
            select(ApprovalRequest)
            .where(ApprovalRequest.id == approval_id)
            .options(selectinload(ApprovalRequest.steps))
        )
        result = await db.execute(stmt)
        approval_request = result.scalar_one_or_none()

        if approval_request is None:
            raise ApprovalNotFoundError(approval_id)

        if approval_request.status != "pending":
            raise RequestNotPendingError(approval_id, approval_request.status)

        # Get user role
        user_stmt = select(User).where(User.id == user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if user is None:
            raise ApprovalServiceError(f"User '{user_id}' not found", status_code=404)

        # Check role for current level
        allowed_roles = LEVEL_ROLES.get(approval_request.current_level)
        if allowed_roles and user.role not in allowed_roles:
            raise InsufficientRoleError(
                approval_request.current_level,
                user.role,
                allowed_roles,
            )

        # Find the current level step
        current_step = None
        for step in approval_request.steps or []:
            if step.level == approval_request.current_level:
                current_step = step
                break

        if current_step is None:
            raise StepNotFoundError(approval_id, approval_request.current_level)

        if current_step.status != "pending":
            raise AlreadyDecidedError(
                approval_id,
                approval_request.current_level,
                current_step.status,
            )

        # Update step
        current_step.approver_id = user_id
        current_step.status = "approved"
        current_step.comment = comment
        current_step.decided_at = datetime.now(timezone.utc)

        # Advance to next level or mark as fully approved
        if approval_request.current_level >= approval_request.total_levels:
            approval_request.status = "approved"
        else:
            approval_request.current_level += 1

        await db.commit()
        await db.refresh(approval_request, attribute_names=["steps"])
        return ApprovalService._request_to_response(approval_request)

    @staticmethod
    async def reject_step(
        db: AsyncSession,
        approval_id: uuid.UUID,
        user_id: uuid.UUID,
        comment: Optional[str] = None,
    ) -> ApprovalResponse:
        """Reject the current level of an approval request.

        Sets the request status to 'rejected' and cancels all remaining steps.
        """
        # Load request with steps
        stmt = (
            select(ApprovalRequest)
            .where(ApprovalRequest.id == approval_id)
            .options(selectinload(ApprovalRequest.steps))
        )
        result = await db.execute(stmt)
        approval_request = result.scalar_one_or_none()

        if approval_request is None:
            raise ApprovalNotFoundError(approval_id)

        if approval_request.status != "pending":
            raise RequestNotPendingError(approval_id, approval_request.status)

        # Get user role
        user_stmt = select(User).where(User.id == user_id)
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if user is None:
            raise ApprovalServiceError(f"User '{user_id}' not found", status_code=404)

        # Check role for current level
        allowed_roles = LEVEL_ROLES.get(approval_request.current_level)
        if allowed_roles and user.role not in allowed_roles:
            raise InsufficientRoleError(
                approval_request.current_level,
                user.role,
                allowed_roles,
            )

        # Find the current level step
        current_step = None
        for step in approval_request.steps or []:
            if step.level == approval_request.current_level:
                current_step = step
                break

        if current_step is None:
            raise StepNotFoundError(approval_id, approval_request.current_level)

        if current_step.status != "pending":
            raise AlreadyDecidedError(
                approval_id,
                approval_request.current_level,
                current_step.status,
            )

        # Update current step to rejected
        current_step.approver_id = user_id
        current_step.status = "rejected"
        current_step.comment = comment
        current_step.decided_at = datetime.now(timezone.utc)

        # Mark request as rejected, cancel remaining pending steps
        approval_request.status = "rejected"
        for step in approval_request.steps or []:
            if step.status == "pending":
                step.status = "cancelled"
                step.decided_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(approval_request, attribute_names=["steps"])
        return ApprovalService._request_to_response(approval_request)

    @staticmethod
    async def auto_approve(
        db: AsyncSession,
        approval_id: uuid.UUID,
    ) -> ApprovalResponse:
        """Auto-approve an approval request (for amounts < £500).

        Marks the request as 'approved' and all steps as 'approved'.
        """
        stmt = (
            select(ApprovalRequest)
            .where(ApprovalRequest.id == approval_id)
            .options(selectinload(ApprovalRequest.steps))
        )
        result = await db.execute(stmt)
        approval_request = result.scalar_one_or_none()

        if approval_request is None:
            raise ApprovalNotFoundError(approval_id)

        now = datetime.now(timezone.utc)
        approval_request.status = "approved"

        for step in approval_request.steps or []:
            if step.status == "pending":
                step.status = "approved"
                step.comment = "Auto-approved — below £500 threshold"
                step.decided_at = now

        await db.commit()
        await db.refresh(approval_request, attribute_names=["steps"])
        return ApprovalService._request_to_response(approval_request)

    @staticmethod
    async def get_request(
        db: AsyncSession,
        approval_id: uuid.UUID,
    ) -> Optional[ApprovalResponse]:
        """Get a single approval request by ID with all steps."""
        stmt = (
            select(ApprovalRequest)
            .where(ApprovalRequest.id == approval_id)
            .options(selectinload(ApprovalRequest.steps))
        )
        result = await db.execute(stmt)
        approval_request = result.scalar_one_or_none()
        return (
            ApprovalService._request_to_response(approval_request)
            if approval_request
            else None
        )

    @staticmethod
    async def list_requests(
        db: AsyncSession,
        *,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ApprovalResponse], int]:
        """List all approval requests with optional status filter."""
        stmt = (
            select(ApprovalRequest)
            .options(selectinload(ApprovalRequest.steps))
        )

        if status_filter:
            stmt = stmt.where(ApprovalRequest.status == status_filter)

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # Fetch
        stmt = stmt.order_by(ApprovalRequest.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        requests = result.scalars().all()

        items = [ApprovalService._request_to_response(r) for r in requests]
        return items, total
