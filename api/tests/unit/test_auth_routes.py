"""Unit tests for Auth routes using FastAPI TestClient with mocked service layer."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.index import app
from src.services.auth_service import (
    DuplicateEmailError,
    InvalidCredentialsError,
    UserNotFoundError,
)
from src.validators.auth import UserResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_ID = uuid.uuid4()

SAMPLE_USER_RESPONSE: dict = {
    "id": str(USER_ID),
    "email": "test@example.com",
    "display_name": "Test User",
    "role": "viewer",
    "is_active": True,
    "created_at": "2026-06-27T12:00:00Z",
    "updated_at": "2026-06-27T12:00:00Z",
}

SAMPLE_TOKEN = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJyb2xlIjoidmlld2VyIn0.fake"


def make_user_response(**overrides) -> UserResponse:
    """Build a UserResponse with defaults overridden."""
    data = SAMPLE_USER_RESPONSE.copy()
    data.update(overrides)
    data["id"] = str(data.get("id", USER_ID))
    return UserResponse(**data)


# ---------------------------------------------------------------------------
# Mock helper: patch auth dependencies so routes work without real JWT
# ---------------------------------------------------------------------------

def setup_auth_mock(user_response: UserResponse | None = None) -> dict:
    """Return a dict of patches to mock get_current_user and require_role.

    Callers should use this with:
        with patch.multiple("src.routes.auth", **setup_auth_mock(...)):
    """
    if user_response is None:
        user_response = make_user_response(role="owner")

    from src.models.user import User

    mock_user = User(
        id=user_response.id,
        email=user_response.email,
        hashed_password="hashed",
        display_name=user_response.display_name,
        role=user_response.role,
        is_active=user_response.is_active,
        created_at=user_response.created_at,
        updated_at=user_response.updated_at,
    )

    return {
        "get_current_user": lambda: mock_user,
        "require_role": lambda *roles: (lambda: mock_user),
    }


@pytest.fixture
def client() -> TestClient:
    """Return a FastAPI TestClient."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /api/v1/auth/register
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_success(client: TestClient) -> None:
    """Should create a new user and return UserResponse."""
    mock_user = make_user_response(email="new@example.com", role="bookkeeper")

    with (
        patch.object(
            target=app,
            attribute="dependency_overrides",
            new={},
        ),
    ):
        from src.middleware.auth import get_current_user, require_role
        from src.models.user import User

        mock_owner = User(
            id=uuid.uuid4(), email="owner@x.com", hashed_password="h",
            display_name="Owner", role="owner", is_active=True,
            created_at=mock_user.created_at, updated_at=mock_user.updated_at,
        )

        app.dependency_overrides[get_current_user] = lambda: mock_owner
        app.dependency_overrides[require_role] = lambda *roles: (lambda: mock_owner)

        with patch("src.routes.auth.AuthService.create_user", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_user
            response = client.post("/api/v1/auth/register", json={
                "email": "new@example.com",
                "password": "password123",
                "display_name": "New User",
                "role": "bookkeeper",
            })

        app.dependency_overrides.clear()

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert data["role"] == "bookkeeper"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: TestClient) -> None:
    """Should return 409 for duplicate email."""
    from src.middleware.auth import get_current_user, require_role
    from src.models.user import User

    mock_admin = User(
        id=uuid.uuid4(), email="admin@x.com", hashed_password="h",
        display_name="Admin", role="admin", is_active=True,
        created_at=None, updated_at=None,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_admin
    app.dependency_overrides[require_role] = lambda *roles: (lambda: mock_admin)

    with patch("src.routes.auth.AuthService.create_user", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = DuplicateEmailError("test@example.com")
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "password123",
            "display_name": "Test",
            "role": "viewer",
        })

    app.dependency_overrides.clear()
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# POST /api/v1/auth/login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success(client: TestClient) -> None:
    """Should return JWT token on successful login."""
    mock_user = make_user_response(email="test@example.com", role="viewer")
    mock_orm_user = type("MockUser", (), {
        "id": mock_user.id, "email": mock_user.email,
        "hashed_password": "hashed", "display_name": mock_user.display_name,
        "role": mock_user.role, "is_active": mock_user.is_active,
        "created_at": mock_user.created_at, "updated_at": mock_user.updated_at,
    })()

    with patch("src.routes.auth.AuthService.authenticate", new_callable=AsyncMock) as mock_auth:
        mock_auth.return_value = mock_orm_user
        with patch("src.routes.auth.create_access_token", return_value=SAMPLE_TOKEN):
            response = client.post("/api/v1/auth/login", json={
                "email": "test@example.com",
                "password": "password123",
            })

    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == SAMPLE_TOKEN
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: TestClient) -> None:
    """Should return 401 for invalid credentials."""
    with patch("src.routes.auth.AuthService.authenticate", new_callable=AsyncMock) as mock_auth:
        mock_auth.side_effect = InvalidCredentialsError()
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrong",
        })

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_me_success(client: TestClient) -> None:
    """Should return current user info."""
    mock_user = make_user_response(email="me@example.com", role="viewer")

    from src.middleware.auth import get_current_user
    from src.models.user import User

    mock_orm = User(
        id=mock_user.id, email=mock_user.email, hashed_password="h",
        display_name=mock_user.display_name, role=mock_user.role,
        is_active=mock_user.is_active,
        created_at=mock_user.created_at, updated_at=mock_user.updated_at,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_orm

    response = client.get("/api/v1/auth/me")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["role"] == "viewer"


# ---------------------------------------------------------------------------
# GET /api/v1/auth/users
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_users_success(client: TestClient) -> None:
    """Should return list of users for Admin/Owner."""
    mock_user = make_user_response(email="admin@x.com", role="admin")

    from src.middleware.auth import get_current_user, require_role
    from src.models.user import User

    mock_admin = User(
        id=mock_user.id, email=mock_user.email, hashed_password="h",
        display_name=mock_user.display_name, role=mock_user.role,
        is_active=mock_user.is_active,
        created_at=mock_user.created_at, updated_at=mock_user.updated_at,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_admin
    app.dependency_overrides[require_role] = lambda *roles: (lambda: mock_admin)

    with patch("src.routes.auth.AuthService.list_users", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [mock_user]
        response = client.get("/api/v1/auth/users")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["users"]) == 1


# ---------------------------------------------------------------------------
# GET /api/v1/auth/users/{user_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_user_success(client: TestClient) -> None:
    """Should return a single user by ID."""
    mock_user = make_user_response(email="user@example.com", role="viewer")

    from src.middleware.auth import get_current_user, require_role
    from src.models.user import User

    mock_owner = User(
        id=uuid.uuid4(), email="owner@x.com", hashed_password="h",
        display_name="Owner", role="owner", is_active=True,
        created_at=mock_user.created_at, updated_at=mock_user.updated_at,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_owner
    app.dependency_overrides[require_role] = lambda *roles: (lambda: mock_owner)

    with patch("src.routes.auth.AuthService.get_user", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_user
        response = client.get(f"/api/v1/auth/users/{USER_ID}")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_get_user_not_found(client: TestClient) -> None:
    """Should return 404 for non-existent user."""
    from src.middleware.auth import get_current_user, require_role
    from src.models.user import User

    mock_admin = User(
        id=uuid.uuid4(), email="admin@x.com", hashed_password="h",
        display_name="Admin", role="admin", is_active=True,
        created_at=None, updated_at=None,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_admin
    app.dependency_overrides[require_role] = lambda *roles: (lambda: mock_admin)

    with patch("src.routes.auth.AuthService.get_user", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        response = client.get(f"/api/v1/auth/users/{USER_ID}")

    app.dependency_overrides.clear()
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/v1/auth/users/{user_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_user_success(client: TestClient) -> None:
    """Should update a user."""
    mock_user = make_user_response(
        email="updated@example.com",
        display_name="Updated Name",
        role="accountant",
    )

    from src.middleware.auth import get_current_user, require_role
    from src.models.user import User

    mock_owner = User(
        id=uuid.uuid4(), email="owner@x.com", hashed_password="h",
        display_name="Owner", role="owner", is_active=True,
        created_at=mock_user.created_at, updated_at=mock_user.updated_at,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_owner
    app.dependency_overrides[require_role] = lambda *roles: (lambda: mock_owner)

    with patch("src.routes.auth.AuthService.update_user", new_callable=AsyncMock) as mock_update:
        mock_update.return_value = mock_user
        response = client.patch(f"/api/v1/auth/users/{USER_ID}", json={
            "display_name": "Updated Name",
            "role": "accountant",
        })

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_user_not_found(client: TestClient) -> None:
    """Should return 404 for non-existent user."""
    from src.middleware.auth import get_current_user, require_role
    from src.models.user import User

    mock_admin = User(
        id=uuid.uuid4(), email="admin@x.com", hashed_password="h",
        display_name="Admin", role="admin", is_active=True,
        created_at=None, updated_at=None,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_admin
    app.dependency_overrides[require_role] = lambda *roles: (lambda: mock_admin)

    with patch("src.routes.auth.AuthService.update_user", new_callable=AsyncMock) as mock_update:
        mock_update.side_effect = UserNotFoundError(str(uuid.uuid4()))
        response = client.patch(f"/api/v1/auth/users/{USER_ID}", json={
            "display_name": "Ghost",
        })

    app.dependency_overrides.clear()
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/auth/users/{user_id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deactivate_user_success(client: TestClient) -> None:
    """Should deactivate a user (Owner only)."""
    mock_user = make_user_response(email="deactivated@example.com", is_active=False)

    from src.middleware.auth import get_current_user, require_role
    from src.models.user import User

    mock_owner = User(
        id=uuid.uuid4(), email="owner@x.com", hashed_password="h",
        display_name="Owner", role="owner", is_active=True,
        created_at=mock_user.created_at, updated_at=mock_user.updated_at,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_owner
    app.dependency_overrides[require_role] = lambda *roles: (lambda: mock_owner)

    with patch("src.routes.auth.AuthService.deactivate_user", new_callable=AsyncMock) as mock_deactivate:
        mock_deactivate.return_value = mock_user
        response = client.delete(f"/api/v1/auth/users/{USER_ID}")

    app.dependency_overrides.clear()
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False


# ---------------------------------------------------------------------------
# Permissions / RBAC tests (middleware)
# ---------------------------------------------------------------------------

def test_has_permission_owner() -> None:
    """Owner should have all permissions."""
    from src.middleware.auth import has_permission

    assert has_permission("owner", "owner") is True
    assert has_permission("owner", "admin") is True
    assert has_permission("owner", "accountant") is True
    assert has_permission("owner", "bookkeeper") is True
    assert has_permission("owner", "viewer") is True


def test_has_permission_admin() -> None:
    """Admin should have all except owner."""
    from src.middleware.auth import has_permission

    assert has_permission("admin", "owner") is False
    assert has_permission("admin", "admin") is True
    assert has_permission("admin", "accountant") is True
    assert has_permission("admin", "bookkeeper") is True
    assert has_permission("admin", "viewer") is True


def test_has_permission_viewer() -> None:
    """Viewer should only have viewer permissions."""
    from src.middleware.auth import has_permission

    assert has_permission("viewer", "viewer") is True
    assert has_permission("viewer", "bookkeeper") is False
    assert has_permission("viewer", "admin") is False
    assert has_permission("viewer", "owner") is False


def test_check_module_permission_coa() -> None:
    """Test module-level permissions for COA."""
    from src.middleware.auth import check_module_permission

    # Viewer can read COA
    assert check_module_permission("viewer", "coa", "read") is True
    # Viewer cannot write COA
    assert check_module_permission("viewer", "coa", "write") is False
    # Accountant can write COA
    assert check_module_permission("accountant", "coa", "write") is True
    # Bookkeeper can only read COA
    assert check_module_permission("bookkeeper", "coa", "read") is True
    assert check_module_permission("bookkeeper", "coa", "write") is False


def test_check_module_permission_bank() -> None:
    """Test module-level permissions for Bank."""
    from src.middleware.auth import check_module_permission

    # Bookkeeper can write bank
    assert check_module_permission("bookkeeper", "bank", "write") is True
    # Viewer can read but not write bank
    assert check_module_permission("viewer", "bank", "read") is True
    assert check_module_permission("viewer", "bank", "write") is False


def test_check_module_permission_vat() -> None:
    """Test module-level permissions for VAT."""
    from src.middleware.auth import check_module_permission

    # Accountant can write VAT
    assert check_module_permission("accountant", "vat", "write") is True
    # Bookkeeper can only read VAT
    assert check_module_permission("bookkeeper", "vat", "read") is True
    assert check_module_permission("bookkeeper", "vat", "write") is False


def test_check_module_permission_reports() -> None:
    """Test module-level permissions for Reports (all can read)."""
    from src.middleware.auth import check_module_permission

    # All roles can read reports
    assert check_module_permission("viewer", "reports", "read") is True
    # Viewer can write reports (per spec: "reports: read for viewer, write for viewer" i.e. all can)
    assert check_module_permission("viewer", "reports", "write") is True


def test_check_module_permission_admin() -> None:
    """Test that admin endpoints require admin role."""
    from src.middleware.auth import check_module_permission

    # Admin can access admin endpoints
    assert check_module_permission("admin", "admin", "write") is True
    # Accountant cannot access admin
    assert check_module_permission("accountant", "admin", "write") is False
    # Bookkeeper cannot access admin
    assert check_module_permission("bookkeeper", "admin", "read") is False
