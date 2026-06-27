"""FastAPI router for authentication and user management endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.middleware.auth import get_current_user, require_role
from src.models.user import User
from src.services.auth_service import (
    AuthService,
    DuplicateEmailError,
    InvalidCredentialsError,
    UserNotFoundError,
)
from src.services.auth_service import create_access_token
from src.validators.auth import (
    TokenResponse,
    UserCreate,
    UserListResponse,
    UserLogin,
    UserResponse,
    UserUpdate,
    MessageResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# POST /register — Create a new user (Admin/Owner only)
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=UserResponse,
    summary="Register a new user",
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "Email already registered"}, 403: {"description": "Forbidden"}},
)
async def register(
    data: UserCreate,
    current_user: User = Depends(require_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user. Requires Owner or Admin role."""
    try:
        return await AuthService.create_user(db, data)
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /login — Authenticate and return JWT
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive JWT token",
    status_code=status.HTTP_200_OK,
    responses={401: {"description": "Invalid credentials"}},
)
async def login(
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate with email and password. Returns a JWT access token."""
    try:
        user = await AuthService.authenticate(db, data.email, data.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    token = create_access_token(user.id, user.role)
    user_response = AuthService._user_to_response(user)
    return TokenResponse(access_token=token, user=user_response)


# ---------------------------------------------------------------------------
# GET /me — Current user info
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    status_code=status.HTTP_200_OK,
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the currently authenticated user's information."""
    return AuthService._user_to_response(current_user)


# ---------------------------------------------------------------------------
# GET /users — List users (Admin/Owner only)
# ---------------------------------------------------------------------------

@router.get(
    "/users",
    response_model=UserListResponse,
    summary="List all users",
    status_code=status.HTTP_200_OK,
)
async def list_users(
    include_inactive: bool = False,
    current_user: User = Depends(require_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    """List all users. Requires Owner or Admin role."""
    users = await AuthService.list_users(db, include_inactive=include_inactive)
    return UserListResponse(users=users, total=len(users))


# ---------------------------------------------------------------------------
# GET /users/{user_id} — Get a single user (Admin/Owner only)
# ---------------------------------------------------------------------------

@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "User not found"}},
)
async def get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Return a single user by ID. Requires Owner or Admin role."""
    user = await AuthService.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    return user


# ---------------------------------------------------------------------------
# PATCH /users/{user_id} — Update user (Admin/Owner only)
# ---------------------------------------------------------------------------

@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update a user",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "User not found"}, 403: {"description": "Forbidden"}},
)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    current_user: User = Depends(require_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Partially update a user. Requires Owner or Admin role."""
    try:
        return await AuthService.update_user(db, user_id, data)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# DELETE /users/{user_id} — Deactivate user (Owner only)
# ---------------------------------------------------------------------------

@router.delete(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Deactivate a user",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "User not found"}, 403: {"description": "Forbidden"}},
)
async def deactivate_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role("owner")),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Deactivate a user (Owner only). Admins cannot delete users."""
    try:
        return await AuthService.deactivate_user(db, user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
