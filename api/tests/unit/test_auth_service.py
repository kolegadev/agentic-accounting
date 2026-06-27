"""Unit tests for AuthService with mocked DB session."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.user import User
from src.services.auth_service import (
    AuthService,
    AuthServiceError,
    DuplicateEmailError,
    InvalidCredentialsError,
    UserNotFoundError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from src.validators.auth import UserCreate, UserUpdate
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

    async def _refresh(obj: object) -> None:
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid.uuid4()
        if hasattr(obj, "is_active") and obj.is_active is None:
            obj.is_active = True
        if hasattr(obj, "created_at") and obj.created_at is None:
            obj.created_at = NOW
        if hasattr(obj, "updated_at") and obj.updated_at is None:
            obj.updated_at = NOW

    db.refresh = _refresh
    return db


@pytest.fixture
def sample_user() -> User:
    """Create a fully-populated User ORM instance with hashed password."""
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password=hash_password("password123"),
        display_name="Test User",
        role="viewer",
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def test_hash_password() -> None:
    """Should return a bcrypt hash string."""
    hashed = hash_password("mypassword")
    assert hashed != "mypassword"
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")


def test_verify_password_success() -> None:
    """Should return True for correct password."""
    hashed = hash_password("correct")
    assert verify_password("correct", hashed) is True


def test_verify_password_failure() -> None:
    """Should return False for wrong password."""
    hashed = hash_password("correct")
    assert verify_password("wrong", hashed) is False


# ---------------------------------------------------------------------------
# JWT token helpers
# ---------------------------------------------------------------------------

def test_create_and_decode_token() -> None:
    """Should create a token that decodes back to the same claims."""
    from src.services.auth_service import JWT_PRIVATE_KEY, JWT_PUBLIC_KEY

    if not JWT_PRIVATE_KEY or not JWT_PUBLIC_KEY:
        pytest.skip("JWT_PRIVATE_KEY / JWT_PUBLIC_KEY env vars not set")

    user_id = uuid.uuid4()
    token = create_access_token(user_id, "viewer")
    assert token is not None

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "viewer"


def test_decode_invalid_token() -> None:
    """Should return None for an invalid/random token."""
    result = decode_access_token("not.a.valid.token")
    assert result is None


def test_decode_expired_token() -> None:
    """Should return None for a token with an expiration in the past."""
    from src.services.auth_service import JWT_PRIVATE_KEY, JWT_PUBLIC_KEY

    if not JWT_PRIVATE_KEY or not JWT_PUBLIC_KEY:
        pytest.skip("JWT_PRIVATE_KEY / JWT_PUBLIC_KEY env vars not set")

    from datetime import datetime, timezone

    payload = {
        "sub": str(uuid.uuid4()),
        "role": "viewer",
        "iat": datetime(2020, 1, 1, tzinfo=timezone.utc),
        "exp": datetime(2020, 1, 1, tzinfo=timezone.utc),
    }
    from jose import jwt as jose_jwt

    token = jose_jwt.encode(payload, JWT_PRIVATE_KEY, algorithm="RS256")
    result = decode_access_token(token)
    assert result is None


# ---------------------------------------------------------------------------
# authenticate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_authenticate_success(mock_db: AsyncMock, sample_user: User) -> None:
    """Should return user on correct credentials."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_user
    mock_db.execute.return_value = mock_result

    user = await AuthService.authenticate(mock_db, "test@example.com", "password123")
    assert user is not None
    assert user.email == "test@example.com"


@pytest.mark.asyncio
async def test_authenticate_user_not_found(mock_db: AsyncMock) -> None:
    """Should raise InvalidCredentialsError for unknown email."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    with pytest.raises(InvalidCredentialsError) as exc:
        await AuthService.authenticate(mock_db, "nobody@example.com", "any")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_authenticate_wrong_password(mock_db: AsyncMock, sample_user: User) -> None:
    """Should raise InvalidCredentialsError for wrong password."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_user
    mock_db.execute.return_value = mock_result

    with pytest.raises(InvalidCredentialsError) as exc:
        await AuthService.authenticate(mock_db, "test@example.com", "wrongpassword")
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_authenticate_inactive_user(mock_db: AsyncMock, sample_user: User) -> None:
    """Should raise InvalidCredentialsError for inactive user."""
    sample_user.is_active = False
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_user
    mock_db.execute.return_value = mock_result

    with pytest.raises(InvalidCredentialsError):
        await AuthService.authenticate(mock_db, "test@example.com", "password123")


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_user_success(mock_db: AsyncMock) -> None:
    """Should create a user and return UserResponse."""
    data = UserCreate(
        email="new@example.com",
        password="newpassword",
        display_name="New User",
        role="bookkeeper",
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    result = await AuthService.create_user(mock_db, data)
    assert result.email == "new@example.com"
    assert result.role == "bookkeeper"
    assert result.display_name == "New User"
    mock_db.add.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_duplicate_email(mock_db: AsyncMock, sample_user: User) -> None:
    """Should raise DuplicateEmailError for duplicate email."""
    data = UserCreate(
        email="test@example.com",
        password="password123",
        display_name="Test User",
        role="viewer",
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_user
    mock_db.execute.return_value = mock_result

    with pytest.raises(DuplicateEmailError) as exc:
        await AuthService.create_user(mock_db, data)
    assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# list_users
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_users_active_only(mock_db: AsyncMock, sample_user: User) -> None:
    """Should return only active users."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [sample_user]
    mock_db.execute.return_value = mock_result

    result = await AuthService.list_users(mock_db, include_inactive=False)
    assert len(result) == 1
    assert result[0].email == "test@example.com"


@pytest.mark.asyncio
async def test_list_users_include_inactive(mock_db: AsyncMock) -> None:
    """Should return all users when include_inactive=True."""
    u1 = User(id=uuid.uuid4(), email="active@x.com", hashed_password="h", display_name="A", role="viewer", is_active=True, created_at=NOW, updated_at=NOW)
    u2 = User(id=uuid.uuid4(), email="inactive@x.com", hashed_password="h", display_name="B", role="viewer", is_active=False, created_at=NOW, updated_at=NOW)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [u1, u2]
    mock_db.execute.return_value = mock_result

    result = await AuthService.list_users(mock_db, include_inactive=True)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# get_user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_user_found(mock_db: AsyncMock, sample_user: User) -> None:
    """Should return user when found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_user
    mock_db.execute.return_value = mock_result

    result = await AuthService.get_user(mock_db, sample_user.id)
    assert result is not None
    assert result.email == "test@example.com"


@pytest.mark.asyncio
async def test_get_user_not_found(mock_db: AsyncMock) -> None:
    """Should return None for non-existent user."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    result = await AuthService.get_user(mock_db, uuid.uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_user_success(mock_db: AsyncMock, sample_user: User) -> None:
    """Should update user fields."""
    data = UserUpdate(display_name="Updated Name", role="admin")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_user
    mock_db.execute.return_value = mock_result

    result = await AuthService.update_user(mock_db, sample_user.id, data)
    assert result.display_name == "Updated Name"
    assert result.role == "admin"


@pytest.mark.asyncio
async def test_update_user_not_found(mock_db: AsyncMock) -> None:
    """Should raise UserNotFoundError."""
    data = UserUpdate(display_name="Ghost")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    with pytest.raises(UserNotFoundError) as exc:
        await AuthService.update_user(mock_db, uuid.uuid4(), data)
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# deactivate_user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deactivate_user_success(mock_db: AsyncMock, sample_user: User) -> None:
    """Should set is_active=False."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_user
    mock_db.execute.return_value = mock_result

    result = await AuthService.deactivate_user(mock_db, sample_user.id)
    assert result.is_active is False


@pytest.mark.asyncio
async def test_deactivate_user_not_found(mock_db: AsyncMock) -> None:
    """Should raise UserNotFoundError."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    with pytest.raises(UserNotFoundError):
        await AuthService.deactivate_user(mock_db, uuid.uuid4())


# ---------------------------------------------------------------------------
# _user_to_response
# ---------------------------------------------------------------------------

def test_user_to_response(sample_user: User) -> None:
    """Should map ORM object to UserResponse Pydantic model."""
    response = AuthService._user_to_response(sample_user)
    assert response.id == sample_user.id
    assert response.email == "test@example.com"
    assert response.role == "viewer"
    assert not hasattr(response, "hashed_password")
