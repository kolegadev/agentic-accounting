"""SQLAlchemy model for Bank Rules Engine — Module 5."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


VALID_CONDITION_FIELDS = ("description", "amount", "reference")
VALID_CONDITION_OPERATORS = ("contains", "equals", "starts_with", "regex", "greater_than", "less_than")
VALID_ACTION_TYPES = ("set_category", "set_contact", "set_account")


class BankRule(Base):
    """A rule for auto-categorizing imported bank transactions."""

    __tablename__ = "bank_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable rule name",
    )
    condition_field: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Field to test: description, amount, reference",
    )
    condition_operator: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Operator: contains, equals, starts_with, regex, greater_than, less_than",
    )
    condition_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Value to compare against (string or numeric)",
    )
    action_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Action: set_category, set_contact, set_account",
    )
    action_value: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Target value (category name, contact name, or account code)",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1000,
        server_default=text("1000"),
        comment="Lower = higher priority",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="Whether this rule is currently active",
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
        Index("ix_bank_rules_is_active", "is_active"),
        Index("ix_bank_rules_priority", "priority"),
    )

    def __repr__(self) -> str:
        return (
            f"<BankRule(id={self.id}, name={self.name!r}, "
            f"priority={self.priority}, is_active={self.is_active})>"
        )
