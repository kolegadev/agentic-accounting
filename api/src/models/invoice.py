"""SQLAlchemy models for Invoicing Module 6 — invoices, invoice_lines, credit_notes."""

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

VALID_INVOICE_STATUSES = ("draft", "sent", "viewed", "paid", "overdue", "cancelled")
VALID_VAT_RATES = ("20%", "5%", "0%", "exempt")


class Invoice(Base):
    """Sales invoice with status lifecycle and PDF generation support.

    Amounts stored in INTEGER pence. Immutable after Sent status.
    Reference format: INV-YYYY-NNNN (sequential per year).
    """

    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    reference: Mapped[Optional[str]] = mapped_column(
        String(14),
        nullable=True,
        unique=True,
        comment="Invoice reference: INV-YYYY-NNNN (set on send)",
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to contacts table",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        server_default=text("'draft'"),
        comment="Invoice status: draft|sent|viewed|paid|overdue|cancelled",
    )
    issue_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Date the invoice was issued",
    )
    due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Date payment is due",
    )
    subtotal: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Sum of line totals before VAT (pence)",
    )
    vat_total: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Total VAT amount (pence)",
    )
    total: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Grand total = subtotal + vat_total (pence)",
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="GBP",
        server_default=text("'GBP'"),
        comment="ISO 4217 currency code",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional invoice notes / payment instructions",
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the invoice was sent to the customer",
    )
    viewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the customer first viewed the invoice",
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the invoice was marked as paid",
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
    lines: Mapped[list["InvoiceLine"]] = relationship(
        "InvoiceLine",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLine.sort_order",
        lazy="selectin",
    )

    credit_notes: Mapped[list["CreditNote"]] = relationship(
        "CreditNote",
        back_populates="invoice",
        lazy="selectin",
    )

    contact: Mapped["Contact"] = relationship(  # noqa: F821
        "Contact",
        foreign_keys=[contact_id],
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            f"status = ANY(ARRAY[{', '.join(repr(s) for s in VALID_INVOICE_STATUSES)}])",
            name="ck_invoices_status",
        ),
        CheckConstraint("subtotal >= 0", name="ck_invoices_subtotal_non_negative"),
        CheckConstraint("vat_total >= 0", name="ck_invoices_vat_total_non_negative"),
        CheckConstraint("total >= 0", name="ck_invoices_total_non_negative"),
        CheckConstraint("due_date >= issue_date", name="ck_invoices_due_date"),
        Index("ix_invoices_contact_id", "contact_id"),
        Index("ix_invoices_status", "status"),
        Index("ix_invoices_issue_date", "issue_date"),
        Index("ix_invoices_due_date", "due_date"),
        Index("ix_invoices_reference", "reference", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<Invoice(id={self.id}, reference={self.reference!r}, "
            f"status={self.status!r}, total={self.total})>"
        )


class InvoiceLine(Base):
    """Line item on an invoice."""

    __tablename__ = "invoice_lines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Description of the line item",
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
        comment="Quantity (whole units)",
    )
    unit_price: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Unit price in pence",
    )
    vat_rate: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="VAT rate: 20%|5%|0%|exempt",
    )
    vat_amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="VAT amount for this line (pence)",
    )
    line_total: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Line total = quantity * unit_price + vat_amount (pence)",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    # Relationships
    invoice: Mapped["Invoice"] = relationship(
        "Invoice",
        back_populates="lines",
    )

    __table_args__ = (
        CheckConstraint(
            f"vat_rate = ANY(ARRAY[{', '.join(repr(r) for r in VALID_VAT_RATES)}])",
            name="ck_invoice_lines_vat_rate",
        ),
        CheckConstraint("quantity > 0", name="ck_invoice_lines_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_invoice_lines_unit_price_non_negative"),
        CheckConstraint("vat_amount >= 0", name="ck_invoice_lines_vat_amount_non_negative"),
        CheckConstraint("line_total >= 0", name="ck_invoice_lines_line_total_non_negative"),
        Index("ix_invoice_lines_invoice_id", "invoice_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<InvoiceLine(id={self.id}, invoice_id={self.invoice_id}, "
            f"description={self.description!r}, line_total={self.line_total})>"
        )


class CreditNote(Base):
    """Credit note offsetting an invoice (negative total)."""

    __tablename__ = "credit_notes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to original invoice",
    )
    reference: Mapped[Optional[str]] = mapped_column(
        String(14),
        nullable=True,
        unique=True,
        comment="Credit note reference: CN-YYYY-NNNN",
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to contacts table",
    )
    total: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Credit note total in pence (negative value)",
    )
    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for issuing credit note",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # Relationships
    invoice: Mapped["Invoice"] = relationship(
        "Invoice",
        back_populates="credit_notes",
    )

    __table_args__ = (
        CheckConstraint("total < 0", name="ck_credit_notes_total_negative"),
        Index("ix_credit_notes_invoice_id", "invoice_id"),
        Index("ix_credit_notes_contact_id", "contact_id"),
        Index("ix_credit_notes_reference", "reference", unique=True),
    )

    def __repr__(self) -> str:
        return (
            f"<CreditNote(id={self.id}, reference={self.reference!r}, "
            f"invoice_id={self.invoice_id}, total={self.total})>"
        )
