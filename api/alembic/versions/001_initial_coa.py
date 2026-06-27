"""001_initial_coa — Create accounts table with all columns, constraints, and indexes.

Revision ID: 001
Revises: None
Create Date: 2026-06-27

This migration creates the foundational 'accounts' table for the Chart of Accounts module.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Valid values for check constraints
VALID_CATEGORIES = ("Asset", "Liability", "Equity", "Revenue", "Expense")
VALID_TYPES = (
    "Bank",
    "CurrentAsset",
    "FixedAsset",
    "CurrentLiability",
    "LongTermLiability",
    "Equity",
    "Revenue",
    "DirectCost",
    "Expense",
)
VALID_VAT_RATES = ("20%", "5%", "0%", "exempt")


def upgrade() -> None:
    """Create the accounts table."""
    op.create_table(
        "accounts",
        # Primary key
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # Core fields
        sa.Column(
            "code",
            sa.String(10),
            unique=True,
            nullable=False,
            index=True,
            comment="4-digit account code (e.g., 1000, 5210). Must be in valid range for category.",
        ),
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Human-readable account name.",
        ),
        sa.Column(
            "category",
            sa.String(20),
            nullable=False,
            comment=f"One of: {', '.join(VALID_CATEGORIES)}",
        ),
        sa.Column(
            "type",
            sa.String(30),
            nullable=False,
            comment=f"One of: {', '.join(VALID_TYPES)}",
        ),
        # Self-referencing foreign key (max 2 levels deep)
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
            comment="Self-referencing FK for parent account (hierarchy max 2 levels).",
        ),
        # VAT rate
        sa.Column(
            "vat_rate",
            sa.String(10),
            nullable=True,
            comment=f"Default VAT rate: {', '.join(VALID_VAT_RATES)}",
        ),
        # Soft delete flag
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Soft delete flag. Inactive accounts remain in historical transactions but can't be selected for new entries.",
        ),
        # Timestamps
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

    # ---- Check constraints ----
    op.create_check_constraint(
        "ck_accounts_category",
        "accounts",
        sa.text(
            f"category = ANY(ARRAY[{', '.join(repr(c) for c in VALID_CATEGORIES)}])"
        ),
    )
    op.create_check_constraint(
        "ck_accounts_type",
        "accounts",
        sa.text(
            f"type = ANY(ARRAY[{', '.join(repr(t) for t in VALID_TYPES)}])"
        ),
    )
    op.create_check_constraint(
        "ck_accounts_vat_rate",
        "accounts",
        sa.text(
            f"vat_rate IS NULL OR vat_rate = ANY(ARRAY[{', '.join(repr(v) for v in VALID_VAT_RATES)}])"
        ),
    )

    # ---- Indexes ----
    op.create_index("ix_accounts_code_unique", "accounts", ["code"], unique=True)
    op.create_index("ix_accounts_is_active", "accounts", ["is_active"])
    op.create_index("ix_accounts_parent_id", "accounts", ["parent_id"])


def downgrade() -> None:
    """Drop the accounts table."""
    op.drop_table("accounts")
