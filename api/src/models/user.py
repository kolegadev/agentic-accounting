"""SQLAlchemy model for User — Multi-user authentication & authorization."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base

VALID_ROLES = ("owner", "admin", "bookkeeper", "accountant", "viewer")


class User(Base):
    """User entity with role-based access control.

    Roles (in descending privilege):
      - owner:     full system access, can delete users
      - admin:     all access except delete users
      - accountant: transactions, reports, VAT, reconciliation, contacts
      - bookkeeper: transactions, reconciliation, bank, contacts
      - viewer:    read-only access across all modules
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        comment="User email address (used as login identifier)",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="bcrypt-hashed password",
    )
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable display name",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="viewer",
        server_default=text("'viewer'"),
        comment="User role: owner|admin|bookkeeper|accountant|viewer",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="Whether the user account is active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=datetime.now(timezone.utc),
    )

    __table_args__ = (
        CheckConstraint(
            f"role = ANY(ARRAY[{', '.join(repr(r) for r in VALID_ROLES)}])",
            name="ck_users_role",
        ),
        Index("ix_users_email", "email", unique=True),
        Index("ix_users_role", "role"),
        Index("ix_users_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email!r}, role={self.role!r})>"
