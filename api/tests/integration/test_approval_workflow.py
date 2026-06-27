"""Integration tests for Approval Workflow — full lifecycle.

Uses mocked DB session to test the complete create → approve → approve → reject workflows.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.approval import ApprovalRequest, ApprovalStep
from src.models.user import User
from src.services.approval_service import (
    ApprovalService,
    InsufficientRoleError,
)
from src.validators.approval import ApprovalCreate
from tests.conftest import NOW


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db() -> AsyncMock:
    """Return an AsyncMock simulating an async SQLAlchemy session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()

    async def _refresh(obj: object, **kwargs: object) -> None:
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid.uuid4()
        if hasattr(obj, "created_at") and obj.created_at is None:
            obj.created_at = NOW
        if hasattr(obj, "updated_at") and obj.updated_at is None:
            obj.updated_at = NOW

    db.refresh = _refresh
    return db


@pytest.fixture
def bookkeeper() -> User:
    return User(
        id=uuid.uuid4(),
        email="bk@example.com",
        hashed_password="hash",
        display_name="Bookkeeper",
        role="bookkeeper",
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def accountant() -> User:
    return User(
        id=uuid.uuid4(),
        email="acc@example.com",
        hashed_password="hash",
        display_name="Accountant",
        role="accountant",
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def admin() -> User:
    return User(
        id=uuid.uuid4(),
        email="admin@example.com",
        hashed_password="hash",
        display_name="Admin",
        role="admin",
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )


# ---------------------------------------------------------------------------
# Workflow: Auto-approve (< £500)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_auto_approve_workflow(mock_db: AsyncMock) -> None:
    """Auto-approve should mark request and all steps as approved."""
    REQ_ID = uuid.uuid4()

    req = ApprovalRequest(
        id=REQ_ID,
        transaction_id=uuid.uuid4(),
        status="pending",
        current_level=1,
        total_levels=1,
        requested_by=uuid.uuid4(),
        threshold_amount=10000,
        reason="Small purchase",
        created_at=NOW,
        updated_at=NOW,
    )
    s1 = ApprovalStep(
        id=uuid.uuid4(), approval_request_id=REQ_ID,
        level=1, status="pending",
    )
    req.steps = [s1]

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = req
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await ApprovalService.auto_approve(mock_db, REQ_ID)

    assert result.status == "approved"
    assert result.total_levels == 1
    assert s1.status == "approved"


# ---------------------------------------------------------------------------
# Workflow: Two-level approval (£500 - £2,000)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_two_level_approval_workflow(
    mock_db: AsyncMock,
    bookkeeper: User,
    accountant: User,
    admin: User,
) -> None:
    """Create → Level 1 approve (bookkeeper/accountant) → Level 2 approve (accountant/admin)."""
    REQ_ID = uuid.uuid4()

    # Build the request in-memory
    req = ApprovalRequest(
        id=REQ_ID,
        transaction_id=uuid.uuid4(),
        status="pending",
        current_level=1,
        total_levels=2,
        requested_by=bookkeeper.id,
        threshold_amount=100000,
        reason="Medium purchase",
        created_at=NOW,
        updated_at=NOW,
    )
    s1 = ApprovalStep(
        id=uuid.uuid4(), approval_request_id=REQ_ID,
        level=1, status="pending",
    )
    s2 = ApprovalStep(
        id=uuid.uuid4(), approval_request_id=REQ_ID,
        level=2, status="pending",
    )
    req.steps = [s1, s2]

    # ---- Level 1 approve (by accountant) ----
    mock_req_result = MagicMock()
    mock_req_result.scalar_one_or_none.return_value = req
    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = accountant
    mock_db.execute = AsyncMock(
        side_effect=[mock_req_result, mock_user_result]
    )

    result = await ApprovalService.approve_step(
        mock_db, REQ_ID, accountant.id, "Level 1 OK"
    )
    assert result.current_level == 2
    assert s1.status == "approved"

    # ---- Level 2 approve (by admin) → fully approved ----
    mock_db.execute = AsyncMock(
        side_effect=[mock_req_result, mock_user_result]
    )
    # Update the user mock to return admin
    mock_user_result.scalar_one_or_none.return_value = admin

    result2 = await ApprovalService.approve_step(
        mock_db, REQ_ID, admin.id, "Level 2 OK"
    )
    assert result2.status == "approved"
    assert s2.status == "approved"


# ---------------------------------------------------------------------------
# Workflow: Three-level approval (> £2,000)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_three_level_approval_workflow(
    mock_db: AsyncMock,
    bookkeeper: User,
    accountant: User,
    admin: User,
) -> None:
    """Create → L1 (bookkeeper) → L2 (accountant) → L3 (admin) → fully approved."""
    REQ_ID = uuid.uuid4()

    req = ApprovalRequest(
        id=REQ_ID,
        transaction_id=uuid.uuid4(),
        status="pending",
        current_level=1,
        total_levels=3,
        requested_by=bookkeeper.id,
        threshold_amount=500000,
        reason="Large purchase",
        created_at=NOW,
        updated_at=NOW,
    )
    s1 = ApprovalStep(
        id=uuid.uuid4(), approval_request_id=REQ_ID,
        level=1, status="pending",
    )
    s2 = ApprovalStep(
        id=uuid.uuid4(), approval_request_id=REQ_ID,
        level=2, status="pending",
    )
    s3 = ApprovalStep(
        id=uuid.uuid4(), approval_request_id=REQ_ID,
        level=3, status="pending",
    )
    req.steps = [s1, s2, s3]

    mock_req_result = MagicMock()
    mock_req_result.scalar_one_or_none.return_value = req

    # ---- L1: bookkeeper ----
    mock_user = MagicMock()
    mock_user.scalar_one_or_none.return_value = bookkeeper
    mock_db.execute = AsyncMock(side_effect=[mock_req_result, mock_user])
    r1 = await ApprovalService.approve_step(mock_db, REQ_ID, bookkeeper.id, "L1 OK")
    assert r1.current_level == 2
    assert s1.status == "approved"

    # ---- L2: accountant ----
    mock_user.scalar_one_or_none.return_value = accountant
    mock_db.execute = AsyncMock(side_effect=[mock_req_result, mock_user])
    r2 = await ApprovalService.approve_step(mock_db, REQ_ID, accountant.id, "L2 OK")
    assert r2.current_level == 3
    assert s2.status == "approved"

    # ---- L3: admin ----
    mock_user.scalar_one_or_none.return_value = admin
    mock_db.execute = AsyncMock(side_effect=[mock_req_result, mock_user])
    r3 = await ApprovalService.approve_step(mock_db, REQ_ID, admin.id, "L3 OK")
    assert r3.status == "approved"
    assert s3.status == "approved"


# ---------------------------------------------------------------------------
# Workflow: Reject at level 1
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reject_at_level_1(
    mock_db: AsyncMock,
    accountant: User,
) -> None:
    """Reject at level 1 should cancel entire request."""
    REQ_ID = uuid.uuid4()

    req = ApprovalRequest(
        id=REQ_ID,
        status="pending",
        current_level=1,
        total_levels=3,
        requested_by=uuid.uuid4(),
        threshold_amount=500000,
        created_at=NOW,
        updated_at=NOW,
    )
    s1 = ApprovalStep(
        id=uuid.uuid4(), approval_request_id=REQ_ID,
        level=1, status="pending",
    )
    s2 = ApprovalStep(
        id=uuid.uuid4(), approval_request_id=REQ_ID,
        level=2, status="pending",
    )
    s3 = ApprovalStep(
        id=uuid.uuid4(), approval_request_id=REQ_ID,
        level=3, status="pending",
    )
    req.steps = [s1, s2, s3]

    mock_req_result = MagicMock()
    mock_req_result.scalar_one_or_none.return_value = req
    mock_user = MagicMock()
    mock_user.scalar_one_or_none.return_value = accountant
    mock_db.execute = AsyncMock(side_effect=[mock_req_result, mock_user])

    result = await ApprovalService.reject_step(
        mock_db, REQ_ID, accountant.id, "Not valid"
    )

    assert result.status == "rejected"
    assert s1.status == "rejected"
    assert s2.status == "cancelled"
    assert s3.status == "cancelled"


# ---------------------------------------------------------------------------
# Workflow: Role enforcement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_role_enforcement_l3(
    mock_db: AsyncMock,
    bookkeeper: User,
    accountant: User,
) -> None:
    """Bookkeeper/accountant should NOT be able to approve level 3 (admin/owner only)."""
    REQ_ID = uuid.uuid4()

    req = ApprovalRequest(
        id=REQ_ID,
        status="pending",
        current_level=3,
        total_levels=3,
        requested_by=uuid.uuid4(),
        threshold_amount=500000,
        created_at=NOW,
        updated_at=NOW,
    )
    req.steps = [
        ApprovalStep(
            id=uuid.uuid4(), approval_request_id=REQ_ID,
            level=3, status="pending",
        ),
    ]

    mock_req_result = MagicMock()
    mock_req_result.scalar_one_or_none.return_value = req
    mock_user = MagicMock()
    mock_user.scalar_one_or_none.return_value = bookkeeper
    mock_db.execute = AsyncMock(side_effect=[mock_req_result, mock_user])

    with pytest.raises(InsufficientRoleError):
        await ApprovalService.approve_step(mock_db, REQ_ID, bookkeeper.id)


@pytest.mark.asyncio
async def test_role_enforcement_l1_viewer(
    mock_db: AsyncMock,
    bookkeeper: User,
) -> None:
    """Viewer should NOT be able to approve any level."""
    REQ_ID = uuid.uuid4()
    viewer = User(
        id=uuid.uuid4(), email="v@x.com", hashed_password="h",
        display_name="V", role="viewer", is_active=True,
        created_at=NOW, updated_at=NOW,
    )

    req = ApprovalRequest(
        id=REQ_ID,
        status="pending",
        current_level=1,
        total_levels=2,
        requested_by=uuid.uuid4(),
        threshold_amount=100000,
        created_at=NOW,
        updated_at=NOW,
    )
    req.steps = [
        ApprovalStep(
            id=uuid.uuid4(), approval_request_id=REQ_ID,
            level=1, status="pending",
        ),
    ]

    mock_req_result = MagicMock()
    mock_req_result.scalar_one_or_none.return_value = req
    mock_user = MagicMock()
    mock_user.scalar_one_or_none.return_value = viewer
    mock_db.execute = AsyncMock(side_effect=[mock_req_result, mock_user])

    with pytest.raises(InsufficientRoleError):
        await ApprovalService.approve_step(mock_db, REQ_ID, viewer.id)
