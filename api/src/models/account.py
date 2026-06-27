"""SQLAlchemy model for accounts table — Chart of Accounts Module 1."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import Base


VALID_CATEGORIES = ("Asset", "Liability", "Equity", "Revenue", "Expense")
VALID_TYPES = (
    "Bank",
    "CurrentAsset",
    "FixedAsset",
    "CurrentLiability",
    "LongTermLiability",
    "Equity",
    "Revenue",
    "DirectCost",
    "Expense",
)
VALID_VAT_RATES = ("20%", "5%", "0%", "exempt")

# Category → code range mapping
CATEGORY_CODE_RANGES: dict[str, tuple[int, int]] = {
    "Asset": (1000, 1999),
    "Liability": (2000, 2999),
    "Equity": (3000, 3999),
    "Revenue": (4000, 4999),
    "Expense": (5000, 6999),
}


class Account(Base):
    """Chart of Accounts account entity.

    Follows a standard 5-category, 4-digit numbering scheme with
    intentional gaps (intervals of 10) to allow future insertion
    without renumbering.
    """

    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    code: Mapped[str] = mapped_column(
        String(10),
        unique=True,
        nullable=False,
        index=True,
        comment="4-digit account code (e.g., 1000, 5210). Must be in valid range for category.",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable account name.",
    )
    category: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment=f"One of: {', '.join(VALID_CATEGORIES)}",
    )
    type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment=f"One of: {', '.join(VALID_TYPES)}",
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Self-referencing FK for parent account (hierarchy max 2 levels).",
    )
    vat_rate: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment=f"Default VAT rate: {', '.join(VALID_VAT_RATES)}",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        comment="Soft delete flag. Inactive accounts remain in historical transactions but can't be selected for new entries.",
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

    # Self-referencing relationship
    parent: Mapped[Optional["Account"]] = relationship(
        "Account",
        remote_side="Account.id",
        back_populates="children",
    )
    children: Mapped[list["Account"]] = relationship(
        "Account",
        back_populates="parent",
    )

    __table_args__ = (
        CheckConstraint(
            f"category = ANY(ARRAY[{', '.join(repr(c) for c in VALID_CATEGORIES)}])",
            name="ck_accounts_category",
        ),
        CheckConstraint(
            f"type = ANY(ARRAY[{', '.join(repr(t) for t in VALID_TYPES)}])",
            name="ck_accounts_type",
        ),
        CheckConstraint(
            f"vat_rate IS NULL OR vat_rate = ANY(ARRAY[{', '.join(repr(v) for v in VALID_VAT_RATES)}])",
            name="ck_accounts_vat_rate",
        ),
        Index("ix_accounts_code_unique", "code", unique=True),
        Index("ix_accounts_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, code={self.code!r}, name={self.name!r})>"

    @classmethod
    def validate_code_for_category(cls, code: str, category: str) -> bool:
        """Check that a code falls within the valid range for its category."""
        try:
            code_int = int(code)
        except (ValueError, TypeError):
            return False
        min_val, max_val = CATEGORY_CODE_RANGES.get(category, (0, 0))
        return min_val <= code_int <= max_val
