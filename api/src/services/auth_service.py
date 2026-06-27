"""Authentication & Authorization service — password hashing, JWT, user CRUD."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.validators.auth import UserCreate, UserResponse, UserUpdate

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the given plain-text password."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against its bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

# RSA key pair from environment (generated once, shared across instances)
JWT_PRIVATE_KEY = os.getenv("JWT_PRIVATE_KEY", "").replace("\\n", "\n")
JWT_PUBLIC_KEY = os.getenv("JWT_PUBLIC_KEY", "").replace("\\n", "\n")
ACCESS_TOKEN_TTL = int(os.getenv("ACCESS_TOKEN_TTL", "900"))
ALGORITHM = "RS256"


def create_access_token(user_id: uuid.UUID, role: str) -> str:
    """Create a signed JWT access token for the given user.

    The token includes sub (user_id as string) and role claims.
    Expiration is controlled by the ACCESS_TOKEN_TTL environment variable
    (default 900 seconds = 15 minutes).
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(seconds=ACCESS_TOKEN_TTL),
    }
    return jwt.encode(payload, JWT_PRIVATE_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token.

    Returns the payload dict on success, or None if the token is
    expired, malformed, or has an invalid signature.
    """
    try:
        return jwt.decode(token, JWT_PUBLIC_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# AuthService — stateless async service
# ---------------------------------------------------------------------------

class AuthServiceError(Exception):
    """Base exception for auth service errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class InvalidCredentialsError(AuthServiceError):
    """Wrong email or password."""

    def __init__(self) -> None:
        super().__init__("Invalid email or password", status_code=401)


class DuplicateEmailError(AuthServiceError):
    """Email already registered."""

    def __init__(self, email: str) -> None:
        super().__init__(f"Email '{email}' is already registered", status_code=409)


class UserNotFoundError(AuthServiceError):
    """User not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"User '{identifier}' not found", status_code=404)


class InsufficientPermissionsError(AuthServiceError):
    """Caller lacks required role."""

    def __init__(self, required: str, actual: str) -> None:
        super().__init__(
            f"Insufficient permissions: {required} required, {actual} granted",
            status_code=403,
        )


class AuthService:
    """Stateless service for user authentication and management."""

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _user_to_response(user: User) -> UserResponse:
        """Map an ORM User instance to a UserResponse Pydantic model."""
        return UserResponse.model_validate(user)

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    @staticmethod
    async def authenticate(
        db: AsyncSession,
        email: str,
        password: str,
    ) -> User:
        """Validate credentials and return the User on success.

        Raises:
            InvalidCredentialsError: if email not found or password wrong.
        """
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            raise InvalidCredentialsError()

        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()

        if not user.is_active:
            raise InvalidCredentialsError()

        return user

    # ------------------------------------------------------------------
    # User CRUD
    # ------------------------------------------------------------------

    @staticmethod
    async def create_user(
        db: AsyncSession,
        data: UserCreate,
    ) -> UserResponse:
        """Create a new user with hashed password.

        Raises:
            DuplicateEmailError: if the email is already in use.
        """
        # Check for duplicate email
        stmt = select(User).where(User.email == data.email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is not None:
            raise DuplicateEmailError(data.email)

        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            display_name=data.display_name,
            role=data.role,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return AuthService._user_to_response(user)

    @staticmethod
    async def list_users(
        db: AsyncSession,
        *,
        include_inactive: bool = False,
    ) -> list[UserResponse]:
        """Return all active (or all) users ordered by email."""
        stmt = select(User)
        if not include_inactive:
            stmt = stmt.where(User.is_active.is_(True))
        stmt = stmt.order_by(User.email)
        result = await db.execute(stmt)
        users = result.scalars().all()
        return [AuthService._user_to_response(u) for u in users]

    @staticmethod
    async def get_user(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> UserResponse | None:
        """Return a single user by ID, or None if not found."""
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        return AuthService._user_to_response(user) if user else None

    @staticmethod
    async def get_user_by_email(
        db: AsyncSession,
        email: str,
    ) -> UserResponse | None:
        """Return a single user by email, or None if not found."""
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        return AuthService._user_to_response(user) if user else None

    @staticmethod
    async def update_user(
        db: AsyncSession,
        user_id: uuid.UUID,
        data: UserUpdate,
    ) -> UserResponse:
        """Partially update a user. Returns updated user.

        Raises:
            UserNotFoundError: if user does not exist.
        """
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise UserNotFoundError(str(user_id))

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        await db.commit()
        await db.refresh(user)
        return AuthService._user_to_response(user)

    @staticmethod
    async def deactivate_user(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> UserResponse:
        """Deactivate a user by setting is_active=False.

        Raises:
            UserNotFoundError: if user does not exist.
        """
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            raise UserNotFoundError(str(user_id))

        user.is_active = False
        await db.commit()
        await db.refresh(user)
        return AuthService._user_to_response(user)
