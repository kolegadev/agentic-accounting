"""SQLAlchemy model for contacts table — Contact Management Module 3."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import Base

VALID_TYPES = ("customer", "supplier", "both")
VALID_STATUSES = ("active", "archived")


class Contact(Base):
    """Contact entity representing customers, suppliers, or both.

    Tracks AR/AP balances via total_invoiced, total_paid, and total_owing
    (all in INTEGER pence). Supports duplicate detection on name, email,
    and VAT number.
    """

    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Contact type: customer, supplier, or both",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Contact display name (individual or organisation)",
    )
    company: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Company / trading name if different from contact name",
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        comment="Primary email address (unique)",
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Primary phone number",
    )
    address_line1: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Address line 1",
    )
    address_line2: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Address line 2",
    )
    city: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Town / city",
    )
    postcode: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Postcode / ZIP",
    )
    country: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        default="GB",
        server_default=text("'GB'"),
        comment="ISO 3166-1 alpha-2 country code",
    )
    vat_number: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        unique=True,
        comment="UK/EU VAT registration number (unique)",
    )
    payment_terms: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Net 30",
        server_default=text("'Net 30'"),
        comment="Default payment terms (e.g., Net 30, Due on Receipt)",
    )
    default_gl_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Default GL account for transactions with this contact",
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
        default="active",
        server_default=text("'active'"),
        comment="Contact status: active or archived",
    )
    total_invoiced: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Total amount invoiced to/from this contact (pence)",
    )
    total_paid: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Total amount paid by/to this contact (pence)",
    )
    total_owing: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Outstanding balance: total_invoiced - total_paid (pence)",
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
    default_gl_account: Mapped[Optional["Account"]] = relationship(
        "Account",
        foreign_keys=[default_gl_account_id],
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            f"type = ANY(ARRAY[{', '.join(repr(t) for t in VALID_TYPES)}])",
            name="ck_contacts_type",
        ),
        CheckConstraint(
            f"status = ANY(ARRAY[{', '.join(repr(s) for s in VALID_STATUSES)}])",
            name="ck_contacts_status",
        ),
        Index("ix_contacts_email", "email", unique=True),
        Index("ix_contacts_vat_number", "vat_number", unique=True),
        Index("ix_contacts_status", "status"),
        Index("ix_contacts_type", "type"),
        Index("ix_contacts_name", "name"),
        Index("ix_contacts_default_gl_account_id", "default_gl_account_id"),
    )

    def __repr__(self) -> str:
        return f"<Contact(id={self.id}, name={self.name!r}, type={self.type!r}, status={self.status!r})>"
