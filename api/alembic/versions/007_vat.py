"""007_vat — Create vat_periods, vat_returns, vat_adjustments tables.

Revision ID: 007
Revises: 006
Create Date: 2026-06-27

Creates tables for VAT Calculation & MTD Preview (Module 7):
- vat_periods: UK VAT return periods (quarterly)
- vat_returns: 9-box VAT return figures
- vat_adjustments: manual adjustments with audit trail
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VALID_SCHEMES = ("standard", "cash", "flat_rate")
VALID_STATUSES = ("open", "closed")


def upgrade() -> None:
    """Create vat_periods, vat_returns, vat_adjustments tables."""
    # ---- vat_periods -----------------------------------------------------------
    op.create_table(
        "vat_periods",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "start_date",
            sa.Date,
            nullable=False,
            comment="First day of the VAT period (inclusive)",
        ),
        sa.Column(
            "end_date",
            sa.Date,
            nullable=False,
            comment="Last day of the VAT period (inclusive)",
        ),
        sa.Column(
            "scheme",
            sa.String(20),
            nullable=False,
            comment="VAT scheme: standard|cash|flat_rate",
        ),
        sa.Column(
            "flat_rate_percentage",
            sa.Numeric(5, 2),
            nullable=True,
            comment="Flat rate percentage (e.g. 7.5). Only for flat_rate scheme.",
        ),
        sa.Column(
            "status",
            sa.String(10),
            nullable=False,
            server_default=sa.text("'open'"),
            comment="Period status: open|closed",
        ),
        sa.Column(
            "closed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the period was closed",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_check_constraint(
        "ck_vat_periods_scheme",
        "vat_periods",
        sa.text(
            f"scheme = ANY(ARRAY[{', '.join(repr(s) for s in VALID_SCHEMES)}])"
        ),
    )
    op.create_check_constraint(
        "ck_vat_periods_status",
        "vat_periods",
        sa.text(
            f"status = ANY(ARRAY[{', '.join(repr(s) for s in VALID_STATUSES)}])"
        ),
    )
    op.create_check_constraint(
        "ck_vat_periods_date_range",
        "vat_periods",
        sa.text("end_date >= start_date"),
    )

    op.create_index("ix_vat_periods_start_date", "vat_periods", ["start_date"])
    op.create_index("ix_vat_periods_end_date", "vat_periods", ["end_date"])
    op.create_index("ix_vat_periods_status", "vat_periods", ["status"])
    op.create_index("ix_vat_periods_scheme", "vat_periods", ["scheme"])

    # ---- vat_returns ------------------------------------------------------------
    op.create_table(
        "vat_returns",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "period_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vat_periods.id", ondelete="CASCADE"),
            nullable=False,
            comment="FK to vat_periods",
        ),
        sa.Column(
            "box1",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Box 1: VAT due on sales (output VAT) in pence",
        ),
        sa.Column(
            "box2",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Box 2: VAT due on EU acquisitions in pence (MVP: 0)",
        ),
        sa.Column(
            "box3",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Box 3: Total output VAT — Box 1 + Box 2",
        ),
        sa.Column(
            "box4",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Box 4: VAT reclaimed on purchases (input VAT) in pence",
        ),
        sa.Column(
            "box5",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Box 5: Net VAT — Box 3 - Box 4",
        ),
        sa.Column(
            "box6",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Box 6: Total sales excluding VAT in pence",
        ),
        sa.Column(
            "box7",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Box 7: Total purchases excluding VAT in pence",
        ),
        sa.Column(
            "box8",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Box 8: EU sales in pence (MVP: 0)",
        ),
        sa.Column(
            "box9",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Box 9: EU acquisitions in pence (MVP: 0)",
        ),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the return was submitted to HMRC (MVP: null)",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_check_constraint(
        "ck_vat_returns_box1_non_negative",
        "vat_returns",
        sa.text("box1 >= 0"),
    )
    op.create_check_constraint(
        "ck_vat_returns_box2_non_negative",
        "vat_returns",
        sa.text("box2 >= 0"),
    )
    op.create_check_constraint(
        "ck_vat_returns_box3_non_negative",
        "vat_returns",
        sa.text("box3 >= 0"),
    )
    op.create_check_constraint(
        "ck_vat_returns_box4_non_negative",
        "vat_returns",
        sa.text("box4 >= 0"),
    )
    op.create_check_constraint(
        "ck_vat_returns_box6_non_negative",
        "vat_returns",
        sa.text("box6 >= 0"),
    )
    op.create_check_constraint(
        "ck_vat_returns_box7_non_negative",
        "vat_returns",
        sa.text("box7 >= 0"),
    )
    op.create_check_constraint(
        "ck_vat_returns_box8_non_negative",
        "vat_returns",
        sa.text("box8 >= 0"),
    )
    op.create_check_constraint(
        "ck_vat_returns_box9_non_negative",
        "vat_returns",
        sa.text("box9 >= 0"),
    )

    op.create_index("ix_vat_returns_period_id", "vat_returns", ["period_id"])

    # ---- vat_adjustments --------------------------------------------------------
    op.create_table(
        "vat_adjustments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "vat_return_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vat_returns.id", ondelete="CASCADE"),
            nullable=False,
            comment="FK to vat_returns",
        ),
        sa.Column(
            "box_number",
            sa.Integer,
            nullable=False,
            comment="Box being adjusted (1-9)",
        ),
        sa.Column(
            "amount_before",
            sa.Integer,
            nullable=False,
            comment="Box value before adjustment in pence",
        ),
        sa.Column(
            "amount_after",
            sa.Integer,
            nullable=False,
            comment="Box value after adjustment in pence",
        ),
        sa.Column(
            "reason",
            sa.String(500),
            nullable=False,
            comment="Human-readable reason for the adjustment",
        ),
        sa.Column(
            "source_reference",
            sa.String(100),
            nullable=True,
            comment="Digital link: source transaction/posting reference",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_check_constraint(
        "ck_vat_adjustments_box_number",
        "vat_adjustments",
        sa.text("box_number >= 1 AND box_number <= 9"),
    )

    op.create_index("ix_vat_adjustments_vat_return_id", "vat_adjustments", ["vat_return_id"])
    op.create_index("ix_vat_adjustments_box_number", "vat_adjustments", ["box_number"])


def downgrade() -> None:
    """Drop vat_adjustments, vat_returns, then vat_periods."""
    op.drop_table("vat_adjustments")
    op.drop_table("vat_returns")
    op.drop_table("vat_periods")
