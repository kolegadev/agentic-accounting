"""005_reconciliation — Create reconciliation_sessions and reconciliation_matches tables.

Revision ID: 005
Revises: 004
Create Date: 2026-06-27

Creates the reconciliation_sessions and reconciliation_matches tables for
Manual Bank Reconciliation (Module 5) with constraints, indexes, and FKs.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VALID_SESSION_STATUSES = ("open", "closed")
VALID_MATCH_TYPES = ("one_to_one", "one_to_many", "partial", "new_entry")


def upgrade() -> None:
    """Create reconciliation_sessions and reconciliation_matches tables."""
    # ---- reconciliation_sessions --------------------------------------------
    op.create_table(
        "reconciliation_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "bank_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bank_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "start_date",
            sa.Date,
            nullable=False,
            comment="Start date of the reconciliation period",
        ),
        sa.Column(
            "end_date",
            sa.Date,
            nullable=False,
            comment="End date of the reconciliation period",
        ),
        sa.Column(
            "opening_balance",
            sa.Integer,
            nullable=False,
            comment="Opening balance in pence at start_date",
        ),
        sa.Column(
            "closing_balance",
            sa.Integer,
            nullable=False,
            comment="Expected closing balance in pence at end_date",
        ),
        sa.Column(
            "status",
            sa.String(10),
            nullable=False,
            server_default=sa.text("'open'"),
            comment="Session status: open | closed",
        ),
        sa.Column(
            "matched_count",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Number of matched bank lines",
        ),
        sa.Column(
            "unmatched_count",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Number of unmatched bank lines",
        ),
        sa.Column(
            "total_bank_lines",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Total bank lines in the session period",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "closed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the session was closed",
        ),
    )

    # Check constraint for status
    op.create_check_constraint(
        "ck_reconciliation_sessions_status",
        "reconciliation_sessions",
        sa.text(
            f"status = ANY(ARRAY[{', '.join(repr(s) for s in VALID_SESSION_STATUSES)}])"
        ),
    )

    # Check constraint for dates
    op.create_check_constraint(
        "ck_reconciliation_sessions_dates",
        "reconciliation_sessions",
        sa.text("end_date >= start_date"),
    )

    # Indexes
    op.create_index(
        "ix_reconciliation_sessions_bank_account_id",
        "reconciliation_sessions",
        ["bank_account_id"],
    )
    op.create_index(
        "ix_reconciliation_sessions_status",
        "reconciliation_sessions",
        ["status"],
    )
    op.create_index(
        "ix_reconciliation_sessions_dates",
        "reconciliation_sessions",
        ["start_date", "end_date"],
    )

    # ---- reconciliation_matches ---------------------------------------------
    op.create_table(
        "reconciliation_matches",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("reconciliation_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "bank_transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bank_transactions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id", ondelete="SET NULL"),
            nullable=True,
            comment="FK to GL transaction — null if new entry created via create-and-match",
        ),
        sa.Column(
            "match_type",
            sa.String(20),
            nullable=False,
            comment="Match type: one_to_one | one_to_many | partial | new_entry",
        ),
        sa.Column(
            "amount_difference",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Difference between bank amount and matched ledger amount in pence",
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
            comment="Optional note about the match",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Check constraint for match_type
    op.create_check_constraint(
        "ck_reconciliation_matches_type",
        "reconciliation_matches",
        sa.text(
            f"match_type = ANY(ARRAY[{', '.join(repr(m) for m in VALID_MATCH_TYPES)}])"
        ),
    )

    # Indexes
    op.create_index(
        "ix_reconciliation_matches_session_id",
        "reconciliation_matches",
        ["session_id"],
    )
    op.create_index(
        "ix_reconciliation_matches_bank_transaction_id",
        "reconciliation_matches",
        ["bank_transaction_id"],
    )
    op.create_index(
        "ix_reconciliation_matches_transaction_id",
        "reconciliation_matches",
        ["transaction_id"],
    )


def downgrade() -> None:
    """Drop reconciliation_matches then reconciliation_sessions."""
    op.drop_table("reconciliation_matches")
    op.drop_table("reconciliation_sessions")
