"""011_bank_rules — Create bank_rules table for Bank Rules Engine.

Revision ID: 011
Revises: 010
Create Date: 2026-06-27

Creates the bank_rules table for auto-categorizing imported bank transactions
using condition-based rules with priority ordering.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create bank_rules table."""
    op.create_table(
        "bank_rules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Human-readable rule name",
        ),
        sa.Column(
            "condition_field",
            sa.String(50),
            nullable=False,
            comment="Field to test: description, amount, reference",
        ),
        sa.Column(
            "condition_operator",
            sa.String(50),
            nullable=False,
            comment="Operator: contains, equals, starts_with, regex, greater_than, less_than",
        ),
        sa.Column(
            "condition_value",
            sa.Text,
            nullable=False,
            comment="Value to compare against (string or numeric)",
        ),
        sa.Column(
            "action_type",
            sa.String(50),
            nullable=False,
            comment="Action: set_category, set_contact, set_account",
        ),
        sa.Column(
            "action_value",
            sa.String(255),
            nullable=False,
            comment="Target value (category name, contact name, or account code)",
        ),
        sa.Column(
            "priority",
            sa.Integer,
            nullable=False,
            server_default=sa.text("1000"),
            comment="Lower = higher priority",
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
            comment="Whether this rule is currently active",
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

    op.create_index("ix_bank_rules_is_active", "bank_rules", ["is_active"])
    op.create_index("ix_bank_rules_priority", "bank_rules", ["priority"])


def downgrade() -> None:
    """Drop bank_rules table."""
    op.drop_table("bank_rules")
