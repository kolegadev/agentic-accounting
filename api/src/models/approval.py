"""SQLAlchemy models for Approval Workflows — Phase 2.

Supports multi-level approval for transactions, invoices, and VAT returns.
Threshold-based level calculation: 0-£500 (1 level auto-approve),
£500-£2,000 (2 levels), >£2,000 (3 levels).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
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

VALID_STATUSES = ("pending", "approved", "rejected", "cancelled")
VALID_STEP_STATUSES = ("pending", "approved", "rejected")


class ApprovalRequest(Base):
    """Multi-level approval request for transactions, invoices, or VAT returns.

    Auto-calculates approval levels based on threshold_amount.
    Tracks which level is currently pending (current_level).
    """

    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    transaction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK to transactions — nullable, can approve other entities",
    )
    invoice_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK to invoices — nullable",
    )
    vat_return_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vat_returns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK to vat_returns — nullable",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
        comment="Approval status: pending|approved|rejected|cancelled",
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="User who requested this approval",
    )
    current_level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
        comment="Current approval level being processed (1-based)",
    )
    total_levels: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
        comment="Total number of approval levels required",
    )
    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional reason / description for this approval request",
    )
    threshold_amount: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Monetary threshold that triggered this approval, in pence",
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
    steps: Mapped[list["ApprovalStep"]] = relationship(
        "ApprovalStep",
        back_populates="approval_request",
        cascade="all, delete-orphan",
        order_by="ApprovalStep.level",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            f"status = ANY(ARRAY[{', '.join(repr(s) for s in VALID_STATUSES)}])",
            name="ck_approval_requests_status",
        ),
        CheckConstraint(
            "current_level >= 1",
            name="ck_approval_requests_current_level_positive",
        ),
        CheckConstraint(
            "total_levels >= 1",
            name="ck_approval_requests_total_levels_positive",
        ),
        CheckConstraint(
            "current_level <= total_levels",
            name="ck_approval_requests_current_level_valid",
        ),
        Index("ix_approval_requests_status", "status"),
        Index("ix_approval_requests_requested_by", "requested_by"),
        Index("ix_approval_requests_transaction_id", "transaction_id"),
        Index("ix_approval_requests_invoice_id", "invoice_id"),
        Index("ix_approval_requests_vat_return_id", "vat_return_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ApprovalRequest(id={self.id}, status={self.status!r}, "
            f"level={self.current_level}/{self.total_levels})>"
        )


class ApprovalStep(Base):
    """A single approval step within a multi-level approval request.

    Each step is assigned to a specific level and optionally a specific
    approver (user).  Status tracks whether this step has been decided.
    """

    __tablename__ = "approval_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    approval_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approval_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approver_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who approved/rejected this step, NULL if pending",
    )
    level: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Approval level this step belongs to (1-based)",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
        comment="Step status: pending|approved|rejected",
    )
    comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional comment from approver",
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this step was decided (approved or rejected)",
    )

    # Relationships
    approval_request: Mapped["ApprovalRequest"] = relationship(
        "ApprovalRequest",
        back_populates="steps",
    )

    __table_args__ = (
        CheckConstraint(
            f"status = ANY(ARRAY[{', '.join(repr(s) for s in VALID_STEP_STATUSES)}])",
            name="ck_approval_steps_status",
        ),
        CheckConstraint(
            "level >= 1",
            name="ck_approval_steps_level_positive",
        ),
        Index("ix_approval_steps_approval_request_id", "approval_request_id"),
        Index("ix_approval_steps_approver_id", "approver_id"),
        Index("ix_approval_steps_level", "level"),
    )

    def __repr__(self) -> str:
        return (
            f"<ApprovalStep(id={self.id}, level={self.level}, "
            f"status={self.status!r}, approver_id={self.approver_id})>"
        )
