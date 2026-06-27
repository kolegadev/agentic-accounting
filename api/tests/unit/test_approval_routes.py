"""Unit tests for Approval routes using FastAPI TestClient with mocked service layer."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.index import app
from src.validators.approval import ApprovalResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REQ_ID = uuid.uuid4()
STEP_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
NOW_ISO = "2026-06-27T12:00:00Z"

SAMPLE_STEP_RESPONSE: dict = {
    "id": str(STEP_ID),
    "approval_request_id": str(REQ_ID),
    "approver_id": None,
    "level": 1,
    "status": "pending",
    "comment": None,
    "decided_at": None,
}

SAMPLE_RESPONSE: dict = {
    "id": str(REQ_ID),
    "transaction_id": str(uuid.uuid4()),
    "invoice_id": None,
    "vat_return_id": None,
    "status": "pending",
    "requested_by": str(USER_ID),
    "current_level": 1,
    "total_levels": 2,
    "reason": "Test approval",
    "threshold_amount": 100000,
    "steps": [SAMPLE_STEP_RESPONSE],
    "created_at": NOW_ISO,
    "updated_at": NOW_ISO,
}


def make_approval_response(**overrides: object) -> ApprovalResponse:
    """Build an ApprovalResponse with defaults overridden."""
    data: dict = SAMPLE_RESPONSE.copy()
    data.update(overrides)  # type: ignore[arg-type]
    data["id"] = str(data.get("id", REQ_ID))
    return ApprovalResponse(**data)  # type: ignore[arg-type]


@pytest.fixture
def client() -> TestClient:
    """Return a FastAPI TestClient."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST / — Create approval request
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_approval_success(client: TestClient) -> None:
    """Should create approval request and return 201."""
    from src.middleware.auth import get_current_user, require_role
    from src.models.user import User

    mock_user = User(
        id=USER_ID, email="bk@x.com", hashed_password="h",
        display_name="BK", role="bookkeeper", is_active=True,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_role] = lambda *roles: (lambda: mock_user)

    mock_response = make_approval_response()
    with patch(
        "src.routes.approvals.ApprovalService.create_request",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = mock_response
        payload = {
            "transaction_id": str(uuid.uuid4()),
            "threshold_amount": 100000,
            "reason": "Test approval",
        }
        resp = client.post("/api/v1/approvals/", json=payload)

    app.dependency_overrides.clear()

    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["total_levels"] == 2


# ---------------------------------------------------------------------------
# GET /pending — My pending approvals
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pending_approvals(client: TestClient) -> None:
    """Should return pending approvals for current user."""
    from src.middleware.auth import get_current_user, require_role
    from src.models.user import User

    mock_user = User(
        id=USER_ID, email="acc@x.com", hashed_password="h",
        display_name="Acc", role="accountant", is_active=True,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_role] = lambda *roles: (lambda: mock_user)

    mock_response = make_approval_response()
    with patch(
        "src.routes.approvals.ApprovalService.get_pending_approvals",
        new_callable=AsyncMock,
    ) as mock_pending:
        mock_pending.return_value = [mock_response]
        resp = client.get("/api/v1/approvals/pending")

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["approvals"]) == 1


# ---------------------------------------------------------------------------
# POST /{id}/approve — Approve step
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_approve_step_success(client: TestClient) -> None:
    """Should approve current level."""
    from src.middleware.auth import get_current_user, require_role
    from src.models.user import User

    mock_user = User(
        id=USER_ID, email="acc@x.com", hashed_password="h",
        display_name="Acc", role="accountant", is_active=True,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_role] = lambda *roles: (lambda: mock_user)

    mock_response = make_approval_response(current_level=2, status="pending")
    with patch(
        "src.routes.approvals.ApprovalService.approve_step",
        new_callable=AsyncMock,
    ) as mock_approve:
        mock_approve.return_value = mock_response
        resp = client.post(
            f"/api/v1/approvals/{REQ_ID}/approve",
            json={"comment": "LGTM"},
        )

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["current_level"] == 2


@pytest.mark.asyncio
async def test_approve_final_level(client: TestClient) -> None:
    """Approving last level should mark as fully approved."""
    from src.middleware.auth import get_current_user, require_role
    from src.models.user import User

    mock_user = User(
        id=USER_ID, email="admin@x.com", hashed_password="h",
        display_name="Admin", role="admin", is_active=True,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_role] = lambda *roles: (lambda: mock_user)

    mock_response = make_approval_response(
        current_level=2, total_levels=2, status="approved",
    )
    with patch(
        "src.routes.approvals.ApprovalService.approve_step",
        new_callable=AsyncMock,
    ) as mock_approve:
        mock_approve.return_value = mock_response
        resp = client.post(
            f"/api/v1/approvals/{REQ_ID}/approve",
            json={"comment": "Approved"},
        )

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


# ---------------------------------------------------------------------------
# POST /{id}/reject — Reject step
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reject_step_success(client: TestClient) -> None:
    """Should reject current level and cancel request."""
    from src.middleware.auth import get_current_user, require_role
    from src.models.user import User

    mock_user = User(
        id=USER_ID, email="acc@x.com", hashed_password="h",
        display_name="Acc", role="accountant", is_active=True,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_role] = lambda *roles: (lambda: mock_user)

    mock_response = make_approval_response(status="rejected")
    with patch(
        "src.routes.approvals.ApprovalService.reject_step",
        new_callable=AsyncMock,
    ) as mock_reject:
        mock_reject.return_value = mock_response
        resp = client.post(
            f"/api/v1/approvals/{REQ_ID}/reject",
            json={"comment": "Invalid"},
        )

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


# ---------------------------------------------------------------------------
# GET /{id} — Get approval detail
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_approval_found(client: TestClient) -> None:
    """Should return approval with steps."""
    from src.middleware.auth import get_current_user, require_role
    from src.models.user import User

    mock_user = User(
        id=USER_ID, email="viewer@x.com", hashed_password="h",
        display_name="V", role="viewer", is_active=True,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_role] = lambda *roles: (lambda: mock_user)

    mock_response = make_approval_response()
    with patch(
        "src.routes.approvals.ApprovalService.get_request",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = mock_response
        resp = client.get(f"/api/v1/approvals/{REQ_ID}")

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(REQ_ID)
    assert len(data["steps"]) == 1


@pytest.mark.asyncio
async def test_get_approval_not_found(client: TestClient) -> None:
    """Should return 404 for non-existent approval."""
    from src.middleware.auth import get_current_user, require_role
    from src.models.user import User

    mock_user = User(
        id=USER_ID, email="viewer@x.com", hashed_password="h",
        display_name="V", role="viewer", is_active=True,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_role] = lambda *roles: (lambda: mock_user)

    with patch(
        "src.routes.approvals.ApprovalService.get_request",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = None
        resp = client.get(f"/api/v1/approvals/{uuid.uuid4()}")

    app.dependency_overrides.clear()

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET / — List all approvals (Admin/Owner)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_approvals(client: TestClient) -> None:
    """Should list all approvals (admin/owner only)."""
    from src.middleware.auth import get_current_user, require_role
    from src.models.user import User

    mock_user = User(
        id=USER_ID, email="admin@x.com", hashed_password="h",
        display_name="Admin", role="admin", is_active=True,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[require_role] = lambda *roles: (lambda: mock_user)

    mock_response = make_approval_response()
    with patch(
        "src.routes.approvals.ApprovalService.list_requests",
        new_callable=AsyncMock,
    ) as mock_list:
        mock_list.return_value = ([mock_response], 1)
        resp = client.get("/api/v1/approvals/")

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
