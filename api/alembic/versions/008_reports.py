"""008_reports — Create report_templates and scheduled_reports tables.

Revision ID: 008
Revises: 007
Create Date: 2026-06-27

Creates tables for Core Financial Reports (Module 8):
- report_templates: report template definitions
- scheduled_reports: scheduled report configurations
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VALID_SCHEDULES = ("daily", "weekly", "monthly", "quarterly")
VALID_FORMATS = ("json", "csv", "html", "pdf")
VALID_CATEGORIES = ("financial", "tax", "management", "other")


def upgrade() -> None:
    """Create report_templates and scheduled_reports tables."""
    # ---- report_templates -----------------------------------------------------
    op.create_table(
        "report_templates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(100),
            unique=True,
            nullable=False,
            comment="Unique machine name (e.g., profit_and_loss, balance_sheet)",
        ),
        sa.Column(
            "display_name",
            sa.String(255),
            nullable=False,
            comment="Human-readable name (e.g., Profit & Loss Statement)",
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
            comment="Brief description of the report template",
        ),
        sa.Column(
            "category",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'financial'"),
            comment="Report category: financial|tax|management|other",
        ),
        sa.Column(
            "parameters_schema",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
            comment="JSON Schema describing accepted parameters for this report",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_check_constraint(
        "ck_report_templates_category",
        "report_templates",
        sa.text(
            f"category = ANY(ARRAY[{', '.join(repr(c) for c in VALID_CATEGORIES)}])"
        ),
    )

    op.create_index("ix_report_templates_name", "report_templates", ["name"], unique=True)
    op.create_index("ix_report_templates_category", "report_templates", ["category"])

    # ---- scheduled_reports ----------------------------------------------------
    op.create_table(
        "scheduled_reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("report_templates.id", ondelete="CASCADE"),
            nullable=False,
            comment="FK to report_templates",
        ),
        sa.Column(
            "schedule",
            sa.String(20),
            nullable=False,
            comment="Recurrence: daily|weekly|monthly|quarterly",
        ),
        sa.Column(
            "next_run",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Next scheduled run timestamp",
        ),
        sa.Column(
            "recipient_email",
            sa.String(255),
            nullable=True,
            comment="Email address to send the report to",
        ),
        sa.Column(
            "format",
            sa.String(10),
            nullable=False,
            server_default=sa.text("'json'"),
            comment="Output format: json|csv|html|pdf",
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
            comment="Whether this schedule is active",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_check_constraint(
        "ck_scheduled_reports_schedule",
        "scheduled_reports",
        sa.text(
            f"schedule = ANY(ARRAY[{', '.join(repr(s) for s in VALID_SCHEDULES)}])"
        ),
    )
    op.create_check_constraint(
        "ck_scheduled_reports_format",
        "scheduled_reports",
        sa.text(
            f"format = ANY(ARRAY[{', '.join(repr(f) for f in VALID_FORMATS)}])"
        ),
    )

    op.create_index("ix_scheduled_reports_template_id", "scheduled_reports", ["template_id"])
    op.create_index("ix_scheduled_reports_next_run", "scheduled_reports", ["next_run"])
    op.create_index("ix_scheduled_reports_is_active", "scheduled_reports", ["is_active"])


def downgrade() -> None:
    """Drop scheduled_reports, then report_templates."""
    op.drop_table("scheduled_reports")
    op.drop_table("report_templates")
