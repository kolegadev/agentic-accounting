"""SQLAlchemy models for Recurring Transactions & Invoices — Module 7."""

from __future__ import annotations

import uuid
from datetime import date, datetime
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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import Base

VALID_FREQUENCIES = ("daily", "weekly", "bi_weekly", "monthly", "quarterly", "annual")
VALID_TEMPLATE_TYPES = ("transaction", "invoice")
VALID_END_TYPES = ("never", "after_count", "until_date")
VALID_VAT_RATES = ("20%", "5%", "0%", "exempt")


class RecurringTemplate(Base):
    """Template for recurring transactions or invoices.

    Each template defines the schedule, end conditions, and is linked
    to either a RecurringTransaction or RecurringInvoice detail record.
    """

    __tablename__ = "recurring_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable template name (e.g., 'Monthly Rent')",
    )
    template_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Template type: transaction | invoice",
    )
    frequency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Recurrence frequency: daily|weekly|bi_weekly|monthly|quarterly|annual",
    )
    next_run_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Next scheduled run date",
    )
    end_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="never",
        server_default=text("'never'"),
        comment="End condition: never | after_count | until_date",
    )
    end_after_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Stop after this many occurrences (used with after_count)",
    )
    end_until_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Stop after this date (used with until_date)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="Whether this template is currently active",
    )
    last_run_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Date of the last successful run",
    )
    run_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Number of times this template has been processed",
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
    recurring_transaction: Mapped[Optional["RecurringTransaction"]] = relationship(
        "RecurringTransaction",
        back_populates="template",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    recurring_invoice: Mapped[Optional["RecurringInvoice"]] = relationship(
        "RecurringInvoice",
        back_populates="template",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            f"template_type = ANY(ARRAY[{', '.join(repr(t) for t in VALID_TEMPLATE_TYPES)}])",
            name="ck_templates_type",
        ),
        CheckConstraint(
            f"frequency = ANY(ARRAY[{', '.join(repr(f) for f in VALID_FREQUENCIES)}])",
            name="ck_templates_frequency",
        ),
        CheckConstraint(
            f"end_type = ANY(ARRAY[{', '.join(repr(e) for e in VALID_END_TYPES)}])",
            name="ck_templates_end_type",
        ),
        CheckConstraint("run_count >= 0", name="ck_templates_run_count"),
        Index("ix_templates_template_type", "template_type"),
        Index("ix_templates_is_active", "is_active"),
        Index("ix_templates_next_run_date", "next_run_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<RecurringTemplate(id={self.id}, name={self.name!r}, "
            f"type={self.template_type!r}, frequency={self.frequency!r})>"
        )


class RecurringTransaction(Base):
    """Detail model for recurring templates of type 'transaction'.

    Defines the double-entry transaction to be created on each recurrence.
    """

    __tablename__ = "recurring_transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recurring_templates.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Transaction description applied on each recurrence",
    )
    debit_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Account to debit",
    )
    credit_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Account to credit",
    )
    amount_pence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Transaction amount in pence (always positive)",
    )
    vat_rate: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="VAT rate: 20%|5%|0%|exempt",
    )
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional FK to contacts",
    )

    # Relationship
    template: Mapped["RecurringTemplate"] = relationship(
        "RecurringTemplate",
        back_populates="recurring_transaction",
    )

    __table_args__ = (
        CheckConstraint("amount_pence > 0", name="ck_rt_amount_positive"),
        CheckConstraint(
            f"vat_rate IS NULL OR vat_rate = ANY(ARRAY[{', '.join(repr(v) for v in VALID_VAT_RATES)}])",
            name="ck_rt_vat_rate",
        ),
        Index("ix_rt_template_id", "template_id", unique=True),
        Index("ix_rt_debit_account_id", "debit_account_id"),
        Index("ix_rt_credit_account_id", "credit_account_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<RecurringTransaction(id={self.id}, template_id={self.template_id}, "
            f"amount={self.amount_pence})>"
        )


class RecurringInvoice(Base):
    """Detail model for recurring templates of type 'invoice'.

    Defines the invoice to be created on each recurrence with line items
    stored as JSONB.
    """

    __tablename__ = "recurring_invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recurring_templates.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Customer to invoice",
    )
    items: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
        comment="Array of {description, quantity, unit_price, vat_rate}",
    )
    payment_terms: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Net 30",
        server_default=text("'Net 30'"),
        comment="Payment terms (e.g., 'Net 30', 'Net 7', 'Due on receipt')",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional notes applied to each invoice",
    )

    # Relationship
    template: Mapped["RecurringTemplate"] = relationship(
        "RecurringTemplate",
        back_populates="recurring_invoice",
    )

    __table_args__ = (
        Index("ix_ri_template_id", "template_id", unique=True),
        Index("ix_ri_contact_id", "contact_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<RecurringInvoice(id={self.id}, template_id={self.template_id}, "
            f"contact_id={self.contact_id})>"
        )
