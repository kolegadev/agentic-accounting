"""JWT authentication middleware and role-based access control."""

from __future__ import annotations

import uuid
from typing import Callable, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.models.user import User
from src.services.auth_service import decode_access_token

# ---------------------------------------------------------------------------
# Security scheme
# ---------------------------------------------------------------------------

_bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Role hierarchy (role → set of roles that can impersonate it)
# ---------------------------------------------------------------------------

ROLE_HIERARCHY: dict[str, int] = {
    "owner": 4,
    "admin": 3,
    "accountant": 2,
    "bookkeeper": 1,
    "viewer": 0,
}


def has_permission(user_role: str, required_role: str) -> bool:
    """Check if a user role meets or exceeds the required role level."""
    user_level = ROLE_HIERARCHY.get(user_role, -1)
    required_level = ROLE_HIERARCHY.get(required_role, 999)
    return user_level >= required_level


# ---------------------------------------------------------------------------
# Permission mapping per module
# ---------------------------------------------------------------------------

# Each module maps to a dict with "read" and "write" minimum roles.
# We use the permission mapping from the requirements spec.
MODULE_PERMISSIONS: dict[str, dict[str, str]] = {
    "coa":                {"read": "viewer",     "write": "accountant"},
    "transactions":       {"read": "viewer",     "write": "accountant"},
    "contacts":           {"read": "viewer",     "write": "accountant"},
    "bank":               {"read": "viewer",     "write": "bookkeeper"},
    "reconciliation":     {"read": "bookkeeper", "write": "bookkeeper"},  # no viewer read
    "invoices":           {"read": "bookkeeper", "write": "bookkeeper"},  # no viewer read
    "vat":                {"read": "viewer",     "write": "accountant"},
    "reports":            {"read": "viewer",     "write": "viewer"},      # all can read
    "admin":              {"read": "admin",      "write": "admin"},
}


def check_module_permission(user_role: str, module: str, action: str) -> bool:
    """Check if user_role can perform action on module.

    Args:
        user_role: The user's role string.
        module: Module name (coa, transactions, contacts, bank, etc.).
        action: "read" or "write".

    Returns:
        True if permitted, False otherwise.
    """
    perms = MODULE_PERMISSIONS.get(module)
    if perms is None:
        return False
    required = perms.get(action)
    if required is None:
        return False
    return has_permission(user_role, required)


# ---------------------------------------------------------------------------
# Dependency: get_current_user
# ---------------------------------------------------------------------------

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """FastAPI dependency that extracts and validates the current user from JWT.

    Raises 401 if the token is missing, expired, or invalid.
    Raises 401 if the user is no longer active.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject",
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identifier in token",
        )

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


# ---------------------------------------------------------------------------
# Role-based access control
# ---------------------------------------------------------------------------

def require_role(*allowed_roles: str) -> Callable:
    """Decorator / dependency-factory that restricts access by role.

    Usage:
        @router.get("/admin/endpoint")
        async def admin_endpoint(
            current_user: User = Depends(require_role("owner", "admin")),
        ):
            ...

    Args:
        *allowed_roles: One or more role strings that are permitted.

    Returns:
        A FastAPI dependency that checks the current user's role.
    """

    async def role_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: requires one of {allowed_roles}",
            )
        return current_user

    return role_checker


def require_module_access(module: str, action: str = "read") -> Callable:
    """Dependency-factory that restricts access to a specific module/action.

    Usage:
        @router.get("/api/v1/coa/")
        async def list_accounts(
            current_user: User = Depends(require_module_access("coa", "read")),
        ):
            ...

    Args:
        module: Module name (coa, transactions, contacts, etc.).
        action: "read" or "write".

    Returns:
        A FastAPI dependency that checks module-level permissions.
    """

    async def module_checker(
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not check_module_permission(current_user.role, module, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for {action} on {module}",
            )
        return current_user

    return module_checker
