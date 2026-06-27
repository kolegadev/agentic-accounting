"""SQLAlchemy models for Bank Account and Bank Transaction — Module 4."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import Base

# Ensure referenced models are registered with Base for relationship resolution
import src.models.contact as _contact_mod  # noqa: F401
import src.models.transaction as _transaction_mod  # noqa: F401

VALID_BANK_STATUSES = ("imported", "categorized", "reconciled")


class BankAccount(Base):
    """A bank account that can receive statement imports."""

    __tablename__ = "bank_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable bank account name",
    )
    sort_code: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="UK sort code (XX-XX-XX format)",
    )
    account_number: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Bank account number",
    )
    iban: Mapped[Optional[str]] = mapped_column(
        String(34),
        nullable=True,
        comment="International Bank Account Number",
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="GBP",
        server_default=text("'GBP'"),
        comment="ISO 4217 currency code",
    )
    opening_balance: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Opening balance in pence",
    )
    current_balance: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Current balance in pence (updated on import)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="Soft-delete flag",
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

    # Relationships
    transactions: Mapped[list["BankTransaction"]] = relationship(
        "BankTransaction",
        back_populates="bank_account",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_bank_accounts_is_active", "is_active"),
        Index("ix_bank_accounts_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<BankAccount(id={self.id}, name={self.name!r})>"


class BankTransaction(Base):
    """A single bank transaction imported from CSV or OFX statement.

    Amount is signed: positive = credit (money in), negative = debit (money out).
    """

    __tablename__ = "bank_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bank_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Transaction date",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Transaction description / narrative",
    )
    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Signed amount in pence: positive=credit, negative=debit",
    )
    reference: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Bank reference number",
    )
    type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Transaction type (e.g., BACS, CHAPS, DD, SO)",
    )
    fitid: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Financial Transaction ID from OFX (unique per account)",
    )
    import_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA-256 hash of (date, amount, description) for CSV dedup",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="imported",
        server_default=text("'imported'"),
        comment="Lifecycle: imported | categorized | reconciled",
    )
    matched_transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to GL transaction when matched/reconciled",
    )
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to contact when categorized",
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="User-assigned category label",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # Relationships
    bank_account: Mapped["BankAccount"] = relationship(
        "BankAccount",
        back_populates="transactions",
    )
    matched_transaction: Mapped[Optional["Transaction"]] = relationship(
        "Transaction",
        foreign_keys=[matched_transaction_id],
        lazy="selectin",
    )
    contact: Mapped[Optional["Contact"]] = relationship(
        "Contact",
        foreign_keys=[contact_id],
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            f"status = ANY(ARRAY[{', '.join(repr(s) for s in VALID_BANK_STATUSES)}])",
            name="ck_bank_transactions_status",
        ),
        UniqueConstraint(
            "bank_account_id",
            "fitid",
            name="uq_bank_transactions_account_fitid",
        ),
        Index(
            "ix_bank_transactions_account_import_hash",
            "bank_account_id",
            "import_hash",
        ),
        Index("ix_bank_transactions_date", "date"),
        Index("ix_bank_transactions_status", "status"),
        Index("ix_bank_transactions_contact_id", "contact_id"),
        Index("ix_bank_transactions_matched_transaction_id", "matched_transaction_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<BankTransaction(id={self.id}, date={self.date!r}, "
            f"amount={self.amount}, status={self.status!r})>"
        )
