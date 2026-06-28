"""004_bank — Create bank_accounts and bank_transactions tables.

Revision ID: 004
Revises: 003
Create Date: 2026-06-27

Creates the bank_accounts and bank_transactions tables for
Bank Statement Import (Module 4) with constraints, indexes, and FKs.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VALID_BANK_STATUSES = ("imported", "categorized", "reconciled")


def upgrade() -> None:
    """Create bank_accounts and bank_transactions tables."""
    # ---- bank_accounts -------------------------------------------------------
    op.create_table(
        "bank_accounts",
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
            comment="Human-readable bank account name",
        ),
        sa.Column(
            "sort_code",
            sa.String(10),
            nullable=True,
            comment="UK sort code (XX-XX-XX format)",
        ),
        sa.Column(
            "account_number",
            sa.String(20),
            nullable=True,
            comment="Bank account number",
        ),
        sa.Column(
            "iban",
            sa.String(34),
            nullable=True,
            comment="International Bank Account Number",
        ),
        sa.Column(
            "currency",
            sa.String(3),
            nullable=False,
            server_default=sa.text("'GBP'"),
            comment="ISO 4217 currency code",
        ),
        sa.Column(
            "opening_balance",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Opening balance in pence",
        ),
        sa.Column(
            "current_balance",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Current balance in pence (updated on import)",
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
            comment="Soft-delete flag",
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

    op.create_index("ix_bank_accounts_is_active", "bank_accounts", ["is_active"])
    op.create_index("ix_bank_accounts_name", "bank_accounts", ["name"])

    # ---- bank_transactions ---------------------------------------------------
    op.create_table(
        "bank_transactions",
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
            "date",
            sa.Date,
            nullable=False,
            comment="Transaction date",
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=False,
            comment="Transaction description / narrative",
        ),
        sa.Column(
            "amount",
            sa.Integer,
            nullable=False,
            comment="Signed amount in pence: positive=credit, negative=debit",
        ),
        sa.Column(
            "reference",
            sa.String(255),
            nullable=True,
            comment="Bank reference number",
        ),
        sa.Column(
            "type",
            sa.String(50),
            nullable=True,
            comment="Transaction type (e.g., BACS, CHAPS, DD, SO)",
        ),
        sa.Column(
            "fitid",
            sa.String(255),
            nullable=True,
            comment="Financial Transaction ID from OFX (unique per account)",
        ),
        sa.Column(
            "import_hash",
            sa.String(64),
            nullable=True,
            comment="SHA-256 hash of (date, amount, description) for CSV dedup",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'imported'"),
            comment="Lifecycle: imported | categorized | reconciled",
        ),
        sa.Column(
            "matched_transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id", ondelete="SET NULL"),
            nullable=True,
            comment="FK to GL transaction when matched/reconciled",
        ),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id", ondelete="SET NULL"),
            nullable=True,
            comment="FK to contact when categorized",
        ),
        sa.Column(
            "category",
            sa.String(100),
            nullable=True,
            comment="User-assigned category label",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Check constraint for status
    op.create_check_constraint(
        "ck_bank_transactions_status",
        "bank_transactions",
        sa.text(
            f"status = ANY(ARRAY[{', '.join(repr(s) for s in VALID_BANK_STATUSES)}])"
        ),
    )

    # Unique constraint: (bank_account_id, fitid) for OFX dedup
    op.create_unique_constraint(
        "uq_bank_transactions_account_fitid",
        "bank_transactions",
        ["bank_account_id", "fitid"],
    )

    # Indexes
    op.create_index(
        "ix_bank_transactions_account_import_hash",
        "bank_transactions",
        ["bank_account_id", "import_hash"],
    )
    op.create_index(
        "ix_bank_transactions_date",
        "bank_transactions",
        ["date"],
    )
    op.create_index(
        "ix_bank_transactions_status",
        "bank_transactions",
        ["status"],
    )
    op.create_index(
        "ix_bank_transactions_contact_id",
        "bank_transactions",
        ["contact_id"],
    )
    op.create_index(
        "ix_bank_transactions_matched_transaction_id",
        "bank_transactions",
        ["matched_transaction_id"],
    )


def downgrade() -> None:
    """Drop bank_transactions then bank_accounts."""
    op.drop_table("bank_transactions")
    op.drop_table("bank_accounts")
