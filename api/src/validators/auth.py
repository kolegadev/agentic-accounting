"""Pydantic models for authentication request/response validation."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field

Role = Literal["owner", "admin", "bookkeeper", "accountant", "viewer"]


class UserCreate(BaseModel):
    """Schema for creating a new user (register)."""

    email: EmailStr = Field(
        ...,
        description="User email address (used as login identifier)",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 characters)",
    )
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable display name",
    )
    role: Role = Field(
        default="viewer",
        description="User role: owner, admin, bookkeeper, accountant, or viewer",
    )


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr = Field(
        ...,
        description="User email address",
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="User password",
    )


class UserUpdate(BaseModel):
    """Schema for partially updating a user. All fields optional."""

    display_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated display name",
    )
    role: Optional[Role] = Field(
        default=None,
        description="Updated role",
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Enable or disable user account",
    )


class UserResponse(BaseModel):
    """Schema for user responses (excludes hashed_password)."""

    id: uuid.UUID
    email: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    """Wrapper for listing multiple users."""

    users: list[UserResponse]
    total: int


class TokenResponse(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
