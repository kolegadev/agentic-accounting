"""Unit tests for ApprovalService with mocked DB session."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.approval import ApprovalRequest, ApprovalStep
from src.models.user import User
from src.services.approval_service import (
    AlreadyDecidedError,
    ApprovalNotFoundError,
    ApprovalService,
    ApprovalServiceError,
    InsufficientRoleError,
    RequestNotPendingError,
    StepNotFoundError,
    calculate_levels,
)
from src.validators.approval import ApprovalCreate
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
    db.flush = AsyncMock()

    async def _refresh(obj: object, **kwargs: object) -> None:
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid.uuid4()
        if hasattr(obj, "created_at") and obj.created_at is None:
            obj.created_at = NOW
        if hasattr(obj, "updated_at") and obj.updated_at is None:
            obj.updated_at = NOW
        # Populate steps for ApprovalRequest (created in create_request but
        # only "attached" via db.add — the mock can't track that).
        # Test callers should set steps manually before refresh if needed.

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


@pytest.fixture
def viewer() -> User:
    return User(
        id=uuid.uuid4(),
        email="viewer@example.com",
        hashed_password="hash",
        display_name="Viewer",
        role="viewer",
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )


# ---------------------------------------------------------------------------
# Helper: build a mock DB that returns a known request + user
# ---------------------------------------------------------------------------

def _setup_mock_db_for_workflow(
    mock_db: AsyncMock,
    req: ApprovalRequest,
    user: User,
) -> None:
    """Configure mock_db.execute to return req then user."""
    mock_req = MagicMock()
    mock_req.scalar_one_or_none.return_value = req
    mock_user = MagicMock()
    mock_user.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(side_effect=[mock_req, mock_user])


# ---------------------------------------------------------------------------
# calculate_levels
# ---------------------------------------------------------------------------

def test_calculate_levels_auto_approve() -> None:
    """Amount < £500 should return 1 level (auto-approve)."""
    assert calculate_levels(0) == 1
    assert calculate_levels(10000) == 1
    assert calculate_levels(49999) == 1


def test_calculate_levels_two_levels() -> None:
    """Amount between £500 and £2,000 should return 2 levels."""
    assert calculate_levels(50000) == 2
    assert calculate_levels(100000) == 2
    assert calculate_levels(200000) == 2


def test_calculate_levels_three_levels() -> None:
    """Amount > £2,000 should return 3 levels."""
    assert calculate_levels(200001) == 3
    assert calculate_levels(500000) == 3


# ---------------------------------------------------------------------------
# create_request — auto-approve (below £500)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_request_auto_approve_below_threshold(
    mock_db: AsyncMock,
    bookkeeper: User,
) -> None:
    """Amount < £500 should auto-approve.

    create_request calls auto_approve which calls execute to reload the
    request.  We must prime that execute to return the request.
    """
    REQ_ID = uuid.uuid4()

    # Build the request that auto_approve will "reload"
    req = ApprovalRequest(
        id=REQ_ID,
        transaction_id=uuid.uuid4(),
        status="pending",
        current_level=1,
        total_levels=1,
        requested_by=bookkeeper.id,
        threshold_amount=10000,
        reason="Auto test",
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

    # Monkey-patch refresh to populate steps
    orig_refresh = mock_db.refresh

    async def _refresh(obj: object, **kwargs: object) -> None:
        if isinstance(obj, ApprovalRequest):
            obj.id = REQ_ID
            obj.created_at = NOW
            obj.updated_at = NOW
            obj.steps = req.steps
        await orig_refresh(obj, **kwargs)

    mock_db.refresh = _refresh

    data = ApprovalCreate(
        transaction_id=req.transaction_id,
        threshold_amount=10000,
        reason="Auto test",
    )

    result = await ApprovalService.create_request(mock_db, data, bookkeeper.id)

    assert result.status == "approved"
    assert result.total_levels == 1
    assert result.current_level == 1
    assert len(result.steps) == 1
    assert result.steps[0].status == "approved"


# ---------------------------------------------------------------------------
# create_request — multi-level
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_request_two_levels(
    mock_db: AsyncMock,
    bookkeeper: User,
) -> None:
    """Amount between £500-£2,000 should create 2-level request.

    create_request does NOT call auto_approve for amounts >= 50000.
    It only does commit + refresh. The refresh must populate steps.
    """
    REQ_ID = uuid.uuid4()

    # Build the steps that should be "created" by the service
    s1 = ApprovalStep(
        id=uuid.uuid4(), approval_request_id=REQ_ID,
        level=1, status="pending",
    )
    s2 = ApprovalStep(
        id=uuid.uuid4(), approval_request_id=REQ_ID,
        level=2, status="pending",
    )

    # No execute call needed for create_request without auto_approve
    mock_db.execute = AsyncMock()

    async def _refresh(obj: object, **kwargs: object) -> None:
        if isinstance(obj, ApprovalRequest):
            obj.id = REQ_ID
            obj.created_at = NOW
            obj.updated_at = NOW
            obj.steps = [s1, s2]

    mock_db.refresh = _refresh

    data = ApprovalCreate(
        transaction_id=uuid.uuid4(),
        threshold_amount=100000,
        reason="Test 2-level",
    )

    result = await ApprovalService.create_request(mock_db, data, bookkeeper.id)

    assert result.status == "pending"
    assert result.total_levels == 2
    assert result.current_level == 1
    assert len(result.steps) == 2


@pytest.mark.asyncio
async def test_create_request_three_levels(
    mock_db: AsyncMock,
    bookkeeper: User,
) -> None:
    """Amount > £2,000 should create 3-level request."""
    REQ_ID = uuid.uuid4()

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

    mock_db.execute = AsyncMock()

    async def _refresh(obj: object, **kwargs: object) -> None:
        if isinstance(obj, ApprovalRequest):
            obj.id = REQ_ID
            obj.created_at = NOW
            obj.updated_at = NOW
            obj.steps = [s1, s2, s3]

    mock_db.refresh = _refresh

    data = ApprovalCreate(
        transaction_id=uuid.uuid4(),
        threshold_amount=500000,
        reason="Test 3-level",
    )

    result = await ApprovalService.create_request(mock_db, data, bookkeeper.id)

    assert result.status == "pending"
    assert result.total_levels == 3
    assert result.current_level == 1
    assert len(result.steps) == 3


# ---------------------------------------------------------------------------
# get_pending_approvals
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_pending_approvals(
    mock_db: AsyncMock,
    bookkeeper: User,
) -> None:
    """Should return pending requests where user's role can approve current level."""
    req = ApprovalRequest(
        id=uuid.uuid4(),
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
            id=uuid.uuid4(),
            approval_request_id=req.id,
            level=1,
            status="pending",
        ),
    ]

    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = bookkeeper
    mock_req_result = MagicMock()
    mock_req_result.scalars.return_value.all.return_value = [req]
    mock_db.execute = AsyncMock(side_effect=[mock_user_result, mock_req_result])

    results = await ApprovalService.get_pending_approvals(mock_db, bookkeeper.id)
    assert len(results) == 1
    assert results[0].status == "pending"

    # Viewer should get empty (not allowed for level 1)
    v = User(
        id=uuid.uuid4(), email="v@x.com", hashed_password="h",
        display_name="V", role="viewer", is_active=True,
        created_at=NOW, updated_at=NOW,
    )
    mock_user_result.scalar_one_or_none.return_value = v
    mock_db.execute = AsyncMock(side_effect=[mock_user_result, mock_req_result])
    results2 = await ApprovalService.get_pending_approvals(mock_db, uuid.uuid4())
    assert len(results2) == 0


# ---------------------------------------------------------------------------
# approve_step
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_approve_step_success(
    mock_db: AsyncMock,
    accountant: User,
) -> None:
    """Should approve current level and advance."""
    req = ApprovalRequest(
        id=uuid.uuid4(),
        status="pending",
        current_level=1,
        total_levels=2,
        requested_by=uuid.uuid4(),
        threshold_amount=100000,
        created_at=NOW,
        updated_at=NOW,
    )
    step = ApprovalStep(
        id=uuid.uuid4(), approval_request_id=req.id,
        level=1, status="pending",
    )
    req.steps = [
        step,
        ApprovalStep(
            id=uuid.uuid4(), approval_request_id=req.id,
            level=2, status="pending",
        ),
    ]

    _setup_mock_db_for_workflow(mock_db, req, accountant)

    result = await ApprovalService.approve_step(
        mock_db, req.id, accountant.id, "LGTM"
    )

    assert result.status == "pending"
    assert result.current_level == 2
    assert step.status == "approved"
    assert step.approver_id == accountant.id


@pytest.mark.asyncio
async def test_approve_step_final_level(
    mock_db: AsyncMock,
    admin: User,
) -> None:
    """Approving the last level should mark request as fully approved."""
    req = ApprovalRequest(
        id=uuid.uuid4(),
        status="pending",
        current_level=2,
        total_levels=2,
        requested_by=uuid.uuid4(),
        threshold_amount=100000,
        created_at=NOW,
        updated_at=NOW,
    )
    step2 = ApprovalStep(
        id=uuid.uuid4(), approval_request_id=req.id,
        level=2, status="pending",
    )
    req.steps = [
        ApprovalStep(
            id=uuid.uuid4(), approval_request_id=req.id,
            level=1, status="approved", approver_id=uuid.uuid4(),
        ),
        step2,
    ]

    _setup_mock_db_for_workflow(mock_db, req, admin)

    result = await ApprovalService.approve_step(
        mock_db, req.id, admin.id, "Approved"
    )
    assert result.status == "approved"


@pytest.mark.asyncio
async def test_approve_step_not_found(
    mock_db: AsyncMock,
    bookkeeper: User,
) -> None:
    """Should raise ApprovalNotFoundError."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(ApprovalNotFoundError):
        await ApprovalService.approve_step(mock_db, uuid.uuid4(), bookkeeper.id)


@pytest.mark.asyncio
async def test_approve_step_not_pending(
    mock_db: AsyncMock,
    bookkeeper: User,
) -> None:
    """Should raise RequestNotPendingError if already approved/rejected."""
    req = ApprovalRequest(
        id=uuid.uuid4(),
        status="approved",
        current_level=1,
        total_levels=1,
        requested_by=uuid.uuid4(),
        threshold_amount=10000,
        created_at=NOW,
        updated_at=NOW,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = req
    mock_db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(RequestNotPendingError) as exc:
        await ApprovalService.approve_step(mock_db, req.id, bookkeeper.id)
    assert exc.value.status_code == 422


@pytest.mark.asyncio
async def test_approve_step_insufficient_role(
    mock_db: AsyncMock,
    viewer: User,
) -> None:
    """Viewer should not be able to approve level 1."""
    req = ApprovalRequest(
        id=uuid.uuid4(),
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
            id=uuid.uuid4(), approval_request_id=req.id,
            level=1, status="pending",
        ),
    ]

    _setup_mock_db_for_workflow(mock_db, req, viewer)

    with pytest.raises(InsufficientRoleError) as exc:
        await ApprovalService.approve_step(mock_db, req.id, viewer.id)
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# reject_step
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reject_step_success(
    mock_db: AsyncMock,
    accountant: User,
) -> None:
    """Should reject current level and cancel request."""
    req = ApprovalRequest(
        id=uuid.uuid4(),
        status="pending",
        current_level=1,
        total_levels=2,
        requested_by=uuid.uuid4(),
        threshold_amount=100000,
        created_at=NOW,
        updated_at=NOW,
    )
    step1 = ApprovalStep(
        id=uuid.uuid4(), approval_request_id=req.id,
        level=1, status="pending",
    )
    step2 = ApprovalStep(
        id=uuid.uuid4(), approval_request_id=req.id,
        level=2, status="pending",
    )
    req.steps = [step1, step2]

    _setup_mock_db_for_workflow(mock_db, req, accountant)

    result = await ApprovalService.reject_step(
        mock_db, req.id, accountant.id, "Not valid"
    )

    assert result.status == "rejected"
    assert step1.status == "rejected"
    assert step2.status == "cancelled"


# ---------------------------------------------------------------------------
# auto_approve
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_auto_approve(mock_db: AsyncMock) -> None:
    """Should mark request and all steps as approved."""
    req = ApprovalRequest(
        id=uuid.uuid4(),
        status="pending",
        current_level=1,
        total_levels=1,
        requested_by=uuid.uuid4(),
        threshold_amount=10000,
        created_at=NOW,
        updated_at=NOW,
    )
    step = ApprovalStep(
        id=uuid.uuid4(), approval_request_id=req.id,
        level=1, status="pending",
    )
    req.steps = [step]

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = req
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await ApprovalService.auto_approve(mock_db, req.id)

    assert result.status == "approved"
    assert step.status == "approved"
    assert step.comment == "Auto-approved — below £500 threshold"


# ---------------------------------------------------------------------------
# get_request
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_request_found(mock_db: AsyncMock) -> None:
    """Should return approval request when found."""
    req = ApprovalRequest(
        id=uuid.uuid4(),
        status="pending",
        current_level=1,
        total_levels=2,
        requested_by=uuid.uuid4(),
        threshold_amount=100000,
        created_at=NOW,
        updated_at=NOW,
    )
    req.steps = []

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = req
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await ApprovalService.get_request(mock_db, req.id)
    assert result is not None
    assert result.status == "pending"


@pytest.mark.asyncio
async def test_get_request_not_found(mock_db: AsyncMock) -> None:
    """Should return None for non-existent request."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await ApprovalService.get_request(mock_db, uuid.uuid4())
    assert result is None
