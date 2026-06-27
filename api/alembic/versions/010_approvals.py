"""010_approvals — Create approval_requests and approval_steps tables.

Revision ID: 010
Revises: 009
Create Date: 2026-06-27

Multi-level approval workflow for transactions, invoices, and VAT returns.
Supports threshold-based level calculation:
  0-£500      = 1 level  (auto-approve)
  £500-£2,000 = 2 levels
  >£2,000     = 3 levels
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VALID_STATUSES = ("pending", "approved", "rejected", "cancelled")
VALID_STEP_STATUSES = ("pending", "approved", "rejected")


def upgrade() -> None:
    """Create approval_requests and approval_steps tables."""
    op.create_table(
        "approval_requests",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id", ondelete="SET NULL"),
            nullable=True,
            comment="FK to transactions — nullable, can approve other entities",
        ),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="SET NULL"),
            nullable=True,
            comment="FK to invoices — nullable",
        ),
        sa.Column(
            "vat_return_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vat_returns.id", ondelete="SET NULL"),
            nullable=True,
            comment="FK to vat_returns — nullable",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
            comment="Approval status: pending|approved|rejected|cancelled",
        ),
        sa.Column(
            "requested_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            comment="User who requested this approval",
        ),
        sa.Column(
            "current_level",
            sa.Integer,
            nullable=False,
            server_default=sa.text("1"),
            comment="Current approval level being processed (1-based)",
        ),
        sa.Column(
            "total_levels",
            sa.Integer,
            nullable=False,
            server_default=sa.text("1"),
            comment="Total number of approval levels required",
        ),
        sa.Column(
            "reason",
            sa.Text,
            nullable=True,
            comment="Optional reason / description for this approval request",
        ),
        sa.Column(
            "threshold_amount",
            sa.Integer,
            nullable=True,
            comment="Monetary threshold that triggered this approval, in pence",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_check_constraint(
        "ck_approval_requests_status",
        "approval_requests",
        sa.text(
            f"status = ANY(ARRAY[{', '.join(repr(s) for s in VALID_STATUSES)}])"
        ),
    )
    op.create_check_constraint(
        "ck_approval_requests_current_level_positive",
        "approval_requests",
        sa.text("current_level >= 1"),
    )
    op.create_check_constraint(
        "ck_approval_requests_total_levels_positive",
        "approval_requests",
        sa.text("total_levels >= 1"),
    )
    op.create_check_constraint(
        "ck_approval_requests_current_level_valid",
        "approval_requests",
        sa.text("current_level <= total_levels"),
    )

    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])
    op.create_index("ix_approval_requests_requested_by", "approval_requests", ["requested_by"])
    op.create_index("ix_approval_requests_transaction_id", "approval_requests", ["transaction_id"])
    op.create_index("ix_approval_requests_invoice_id", "approval_requests", ["invoice_id"])
    op.create_index("ix_approval_requests_vat_return_id", "approval_requests", ["vat_return_id"])

    # ---- approval_steps ----
    op.create_table(
        "approval_steps",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "approval_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("approval_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "approver_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="User who approved/rejected this step, NULL if pending",
        ),
        sa.Column(
            "level",
            sa.Integer,
            nullable=False,
            comment="Approval level this step belongs to (1-based)",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
            comment="Step status: pending|approved|rejected",
        ),
        sa.Column(
            "comment",
            sa.Text,
            nullable=True,
            comment="Optional comment from approver",
        ),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When this step was decided (approved or rejected)",
        ),
    )

    op.create_check_constraint(
        "ck_approval_steps_status",
        "approval_steps",
        sa.text(
            f"status = ANY(ARRAY[{', '.join(repr(s) for s in VALID_STEP_STATUSES)}])"
        ),
    )
    op.create_check_constraint(
        "ck_approval_steps_level_positive",
        "approval_steps",
        sa.text("level >= 1"),
    )

    op.create_index("ix_approval_steps_approval_request_id", "approval_steps", ["approval_request_id"])
    op.create_index("ix_approval_steps_approver_id", "approval_steps", ["approver_id"])
    op.create_index("ix_approval_steps_level", "approval_steps", ["level"])


def downgrade() -> None:
    """Drop approval_steps and approval_requests tables."""
    op.drop_table("approval_steps")
    op.drop_table("approval_requests")
