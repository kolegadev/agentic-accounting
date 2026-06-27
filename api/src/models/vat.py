"""SQLAlchemy models for VAT Calculation & MTD Preview — Module 7."""

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
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import Base

VALID_SCHEMES = ("standard", "cash", "flat_rate")
VALID_STATUSES = ("open", "closed")


class VatPeriod(Base):
    """A UK VAT return period (typically quarterly).

    Supports three schemes: standard (accrual), cash (payment-based),
    and flat_rate (simplified percentage of gross turnover).
    """

    __tablename__ = "vat_periods"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="First day of the VAT period (inclusive)",
    )
    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Last day of the VAT period (inclusive)",
    )
    scheme: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="VAT scheme: standard|cash|flat_rate",
    )
    flat_rate_percentage: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Flat rate percentage (e.g. 7.5). Only for flat_rate scheme.",
    )
    status: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="open",
        server_default=text("'open'"),
        comment="Period status: open|closed",
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the period was closed",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # Relationships
    returns: Mapped[list["VatReturn"]] = relationship(
        "VatReturn",
        back_populates="period",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            f"scheme = ANY(ARRAY[{', '.join(repr(s) for s in VALID_SCHEMES)}])",
            name="ck_vat_periods_scheme",
        ),
        CheckConstraint(
            f"status = ANY(ARRAY[{', '.join(repr(s) for s in VALID_STATUSES)}])",
            name="ck_vat_periods_status",
        ),
        CheckConstraint(
            "end_date >= start_date",
            name="ck_vat_periods_date_range",
        ),
        Index("ix_vat_periods_start_date", "start_date"),
        Index("ix_vat_periods_end_date", "end_date"),
        Index("ix_vat_periods_status", "status"),
        Index("ix_vat_periods_scheme", "scheme"),
    )

    def __repr__(self) -> str:
        return (
            f"<VatPeriod(id={self.id}, {self.start_date}→{self.end_date}, "
            f"scheme={self.scheme!r}, status={self.status!r})>"
        )


class VatReturn(Base):
    """A 9-box UK VAT return for a given period.

    All monetary amounts stored in INTEGER PENCE.
    Box 5 = Box 3 - Box 4.
    Box 5 > 0 → amount payable to HMRC.
    Box 5 < 0 → amount reclaimable from HMRC.
    """

    __tablename__ = "vat_returns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    period_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vat_periods.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to vat_periods",
    )
    box1: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Box 1: VAT due on sales (output VAT) in pence",
    )
    box2: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Box 2: VAT due on EU acquisitions in pence (MVP: 0)",
    )
    box3: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Box 3: Total output VAT — Box 1 + Box 2",
    )
    box4: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Box 4: VAT reclaimed on purchases (input VAT) in pence",
    )
    box5: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Box 5: Net VAT — Box 3 - Box 4 (positive = payable, negative = reclaimable)",
    )
    box6: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Box 6: Total sales excluding VAT in pence",
    )
    box7: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Box 7: Total purchases excluding VAT in pence",
    )
    box8: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Box 8: EU sales in pence (MVP: 0)",
    )
    box9: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
        comment="Box 9: EU acquisitions in pence (MVP: 0)",
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the return was submitted to HMRC (MVP: null)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # Relationships
    period: Mapped["VatPeriod"] = relationship(
        "VatPeriod",
        back_populates="returns",
    )
    adjustments: Mapped[list["VatAdjustment"]] = relationship(
        "VatAdjustment",
        back_populates="vat_return",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint("box1 >= 0", name="ck_vat_returns_box1_non_negative"),
        CheckConstraint("box2 >= 0", name="ck_vat_returns_box2_non_negative"),
        CheckConstraint("box3 >= 0", name="ck_vat_returns_box3_non_negative"),
        CheckConstraint("box4 >= 0", name="ck_vat_returns_box4_non_negative"),
        CheckConstraint("box6 >= 0", name="ck_vat_returns_box6_non_negative"),
        CheckConstraint("box7 >= 0", name="ck_vat_returns_box7_non_negative"),
        CheckConstraint("box8 >= 0", name="ck_vat_returns_box8_non_negative"),
        CheckConstraint("box9 >= 0", name="ck_vat_returns_box9_non_negative"),
        Index("ix_vat_returns_period_id", "period_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<VatReturn(id={self.id}, period_id={self.period_id}, "
            f"box3={self.box3}, box4={self.box4}, box5={self.box5})>"
        )


class VatAdjustment(Base):
    """Manual adjustment to a VAT return box figure.

    Tracks changes to any box with reason and digital link to original source.
    Each adjustment creates an audit trail entry.
    """

    __tablename__ = "vat_adjustments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    vat_return_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vat_returns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to vat_returns",
    )
    box_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Box being adjusted (1-9)",
    )
    amount_before: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Box value before adjustment in pence",
    )
    amount_after: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Box value after adjustment in pence",
    )
    reason: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Human-readable reason for the adjustment",
    )
    source_reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Digital link: source transaction/posting reference",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # Relationships
    vat_return: Mapped["VatReturn"] = relationship(
        "VatReturn",
        back_populates="adjustments",
    )

    __table_args__ = (
        CheckConstraint(
            "box_number >= 1 AND box_number <= 9",
            name="ck_vat_adjustments_box_number",
        ),
        Index("ix_vat_adjustments_vat_return_id", "vat_return_id"),
        Index("ix_vat_adjustments_box_number", "box_number"),
    )

    def __repr__(self) -> str:
        return (
            f"<VatAdjustment(id={self.id}, vat_return_id={self.vat_return_id}, "
            f"box{self.box_number}: {self.amount_before}→{self.amount_after})>"
        )
