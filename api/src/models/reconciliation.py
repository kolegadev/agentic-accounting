"""SQLAlchemy models for Reconciliation Session and Match — Module 5."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import Base

# Ensure referenced models are registered with Base for relationship resolution
import src.models.bank_account as _bank_mod  # noqa: F401
import src.models.transaction as _transaction_mod  # noqa: F401

VALID_SESSION_STATUSES = ("open", "closed")
VALID_MATCH_TYPES = ("one_to_one", "one_to_many", "partial", "new_entry")


class ReconciliationSession(Base):
    """A manual reconciliation session for a bank account within a date range."""

    __tablename__ = "reconciliation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Start date of the reconciliation period",
    )
    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="End date of the reconciliation period",
    )
    opening_balance: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Opening balance in pence at start_date",
    )
    closing_balance: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Expected closing balance in pence at end_date",
    )
    status: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="open",
        server_default=text("'open'"),
        comment="Session status: open | closed",
    )
    matched_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Number of matched bank lines",
    )
    unmatched_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Number of unmatched bank lines",
    )
    total_bank_lines: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Total bank lines in the session period",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the session was closed",
    )

    # Relationships
    matches: Mapped[list["ReconciliationMatch"]] = relationship(
        "ReconciliationMatch",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            f"status = ANY(ARRAY[{', '.join(repr(s) for s in VALID_SESSION_STATUSES)}])",
            name="ck_reconciliation_sessions_status",
        ),
        CheckConstraint(
            "end_date >= start_date",
            name="ck_reconciliation_sessions_dates",
        ),
        Index("ix_reconciliation_sessions_bank_account_id", "bank_account_id"),
        Index("ix_reconciliation_sessions_status", "status"),
        Index("ix_reconciliation_sessions_dates", "start_date", "end_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<ReconciliationSession(id={self.id}, bank_account_id={self.bank_account_id}, "
            f"status={self.status!r})>"
        )


class ReconciliationMatch(Base):
    """A single match between a bank transaction and one or more ledger entries."""

    __tablename__ = "reconciliation_matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reconciliation_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    bank_transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_transactions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to GL transaction — null if new entry created via create-and-match",
    )
    match_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Match type: one_to_one | one_to_many | partial | new_entry",
    )
    amount_difference: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Difference between bank amount and matched ledger amount in pence",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional note about the match",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # Relationships
    session: Mapped["ReconciliationSession"] = relationship(
        "ReconciliationSession",
        back_populates="matches",
    )
    bank_transaction: Mapped["BankTransaction"] = relationship(
        "BankTransaction",
        foreign_keys=[bank_transaction_id],
        lazy="selectin",
    )
    transaction: Mapped[Optional["Transaction"]] = relationship(
        "Transaction",
        foreign_keys=[transaction_id],
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            f"match_type = ANY(ARRAY[{', '.join(repr(m) for m in VALID_MATCH_TYPES)}])",
            name="ck_reconciliation_matches_type",
        ),
        Index("ix_reconciliation_matches_session_id", "session_id"),
        Index("ix_reconciliation_matches_bank_transaction_id", "bank_transaction_id"),
        Index("ix_reconciliation_matches_transaction_id", "transaction_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ReconciliationMatch(id={self.id}, session_id={self.session_id}, "
            f"match_type={self.match_type!r}, amount_difference={self.amount_difference})>"
        )
