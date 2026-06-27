"""SQLAlchemy models for Core Financial Reports — Module 8."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import Base

VALID_SCHEDULES = ("daily", "weekly", "monthly", "quarterly")
VALID_FORMATS = ("json", "csv", "html", "pdf")
VALID_CATEGORIES = ("financial", "tax", "management", "other")


class ReportTemplate(Base):
    """Template definition for a report type (P&L, Balance Sheet, Trial Balance, etc.).

    The parameters_schema JSONB column defines which parameters the report accepts
    (e.g., date ranges, comparison options, format).
    """

    __tablename__ = "report_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique machine name (e.g., profit_and_loss, balance_sheet)",
    )
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable name (e.g., Profit & Loss Statement)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Brief description of the report template",
    )
    category: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="financial",
        server_default=text("'financial'"),
        comment="Report category: financial|tax|management|other",
    )
    parameters_schema: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="JSON Schema describing accepted parameters for this report",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # Relationships
    schedules: Mapped[list["ScheduledReport"]] = relationship(
        "ScheduledReport",
        back_populates="template",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            f"category = ANY(ARRAY[{', '.join(repr(c) for c in VALID_CATEGORIES)}])",
            name="ck_report_templates_category",
        ),
        Index("ix_report_templates_name", "name", unique=True),
        Index("ix_report_templates_category", "category"),
    )

    def __repr__(self) -> str:
        return (
            f"<ReportTemplate(id={self.id}, name={self.name!r}, "
            f"display_name={self.display_name!r})>"
        )


class ScheduledReport(Base):
    """Scheduled report configuration — when and how to auto-generate a report."""

    __tablename__ = "scheduled_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to report_templates",
    )
    schedule: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Recurrence: daily|weekly|monthly|quarterly",
    )
    next_run: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Next scheduled run timestamp",
    )
    recipient_email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Email address to send the report to",
    )
    format: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="json",
        server_default=text("'json'"),
        comment="Output format: json|csv|html|pdf",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="Whether this schedule is active",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # Relationships
    template: Mapped["ReportTemplate"] = relationship(
        "ReportTemplate",
        back_populates="schedules",
    )

    __table_args__ = (
        CheckConstraint(
            f"schedule = ANY(ARRAY[{', '.join(repr(s) for s in VALID_SCHEDULES)}])",
            name="ck_scheduled_reports_schedule",
        ),
        CheckConstraint(
            f"format = ANY(ARRAY[{', '.join(repr(f) for f in VALID_FORMATS)}])",
            name="ck_scheduled_reports_format",
        ),
        Index("ix_scheduled_reports_template_id", "template_id"),
        Index("ix_scheduled_reports_next_run", "next_run"),
        Index("ix_scheduled_reports_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return (
            f"<ScheduledReport(id={self.id}, template_id={self.template_id}, "
            f"schedule={self.schedule!r}, format={self.format!r})>"
        )
