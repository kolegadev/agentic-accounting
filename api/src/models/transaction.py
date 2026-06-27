"""SQLAlchemy models for Transaction, Posting, and VATLine — Core General Ledger Module 2."""

from __future__ import annotations

import uuid
from datetime import datetime, date
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

VALID_STATUSES = ("draft", "posted", "reversed")
VALID_VAT_RATES = ("20%", "5%", "0%", "exempt")
VALID_VAT_TYPES = ("input", "output")


class Transaction(Base):
    """A double-entry journal entry with 2+ postings.

    Created in Draft status.  Must be validated and posted before it
    appears in the General Ledger.
    """

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    reference: Mapped[Optional[str]] = mapped_column(
        String(14),
        unique=True,
        nullable=True,
        comment="JE-YYYY-NNNN format, assigned on posting",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable transaction description",
    )
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="Optional FK to contacts (Module 6)",
    )
    total_amount: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Total transaction amount in pence (signed: positive=net debit)",
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="GBP",
        server_default=text("'GBP'"),
        comment="ISO 4217 currency code",
    )
    status: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="draft",
        server_default=text("'draft'"),
        comment="Transaction lifecycle: draft | posted | reversed",
    )
    effective_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Business date this transaction relates to",
    )
    idempotency_key: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        unique=True,
        nullable=True,
        comment="Client-supplied UUID for safe retry",
    )
    recorded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        server_default=text("now()"),
        comment="When the transaction was posted (set at posting time)",
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
        onupdate=datetime.utcnow,
    )

    # Relationships
    postings: Mapped[list["Posting"]] = relationship(
        "Posting",
        back_populates="transaction",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            f"status = ANY(ARRAY[{', '.join(repr(s) for s in VALID_STATUSES)}])",
            name="ck_transactions_status",
        ),
        Index("ix_transactions_reference", "reference", unique=True),
        Index("ix_transactions_idempotency_key", "idempotency_key", unique=True),
        Index("ix_transactions_status", "status"),
        Index("ix_transactions_effective_date", "effective_date"),
        Index("ix_transactions_contact_id", "contact_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, reference={self.reference!r}, "
            f"status={self.status!r})>"
        )


class Posting(Base):
    """A single leg of a double-entry transaction.

    Each posting must have exactly one of debit_amount or credit_amount > 0.
    Enforced at both the application and database level.
    """

    __tablename__ = "postings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    debit_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Debit amount in pence (always >= 0)",
    )
    credit_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Credit amount in pence (always >= 0)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Line-level narrative",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # Relationships
    transaction: Mapped["Transaction"] = relationship(
        "Transaction",
        back_populates="postings",
    )
    account: Mapped["Account"] = relationship(
        "Account",
        lazy="selectin",
    )
    vat_lines: Mapped[list["VATLine"]] = relationship(
        "VATLine",
        back_populates="posting",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("debit_amount >= 0", name="ck_postings_debit_non_negative"),
        CheckConstraint("credit_amount >= 0", name="ck_postings_credit_non_negative"),
        CheckConstraint(
            "(debit_amount > 0 AND credit_amount = 0) OR (debit_amount = 0 AND credit_amount > 0)",
            name="ck_postings_exactly_one_non_zero",
        ),
        Index("ix_postings_transaction_id", "transaction_id"),
        Index("ix_postings_account_id", "account_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Posting(id={self.id}, account_id={self.account_id}, "
            f"dr={self.debit_amount}, cr={self.credit_amount})>"
        )


class VATLine(Base):
    """VAT breakdown for a single posting line.

    Captures the VAT rate, gross/net/VAT amounts, and direction (input/output).
    """

    __tablename__ = "vat_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("postings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vat_rate: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="VAT rate: 20%, 5%, 0%, or exempt",
    )
    vat_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="VAT amount in pence",
    )
    net_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Net (pre-VAT) amount in pence",
    )
    vat_type: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
        comment="VAT direction: input (purchase) or output (sale)",
    )

    # Relationships
    posting: Mapped["Posting"] = relationship(
        "Posting",
        back_populates="vat_lines",
    )

    __table_args__ = (
        CheckConstraint(
            f"vat_rate = ANY(ARRAY[{', '.join(repr(v) for v in VALID_VAT_RATES)}])",
            name="ck_vat_lines_rate",
        ),
        CheckConstraint(
            f"vat_type = ANY(ARRAY[{', '.join(repr(v) for v in VALID_VAT_TYPES)}])",
            name="ck_vat_lines_type",
        ),
        Index("ix_vat_lines_posting_id", "posting_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<VATLine(id={self.id}, rate={self.vat_rate!r}, "
            f"vat={self.vat_amount}, net={self.net_amount}, type={self.vat_type!r})>"
        )
