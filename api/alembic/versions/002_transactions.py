"""002_transactions — Create transactions, postings, and vat_lines tables.

Revision ID: 002
Revises: 001
Create Date: 2026-06-27

Creates the core General Ledger tables with all constraints:
- transactions: JE headers with Draft/Posted/Reversed lifecycle
- postings: double-entry legs with exactly-one-positive enforcement
- vat_lines: VAT breakdown per posting
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VALID_STATUSES = ("draft", "posted", "reversed")
VALID_VAT_RATES = ("20%", "5%", "0%", "exempt")
VALID_VAT_TYPES = ("input", "output")


def upgrade() -> None:
    """Create transactions, postings, and vat_lines tables."""

    # ======================================================================
    # 1. transactions
    # ======================================================================
    op.create_table(
        "transactions",
        # Primary key
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # Reference (assigned on posting)
        sa.Column(
            "reference",
            sa.String(14),
            unique=True,
            nullable=True,
            comment="JE-YYYY-NNNN format, assigned on posting",
        ),
        # Description
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
            comment="Human-readable transaction description",
        ),
        # Contact (Module 6)
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Optional FK to contacts (Module 6)",
        ),
        # Amount
        sa.Column(
            "total_amount",
            sa.Integer,
            nullable=True,
            comment="Total transaction amount in pence (signed: positive=net debit)",
        ),
        # Currency
        sa.Column(
            "currency",
            sa.String(3),
            nullable=False,
            server_default=sa.text("'GBP'"),
            comment="ISO 4217 currency code",
        ),
        # Status
        sa.Column(
            "status",
            sa.String(10),
            nullable=False,
            server_default=sa.text("'draft'"),
            comment="Transaction lifecycle: draft | posted | reversed",
        ),
        # Effective date
        sa.Column(
            "effective_date",
            sa.Date,
            nullable=True,
            comment="Business date this transaction relates to",
        ),
        # Idempotency key
        sa.Column(
            "idempotency_key",
            postgresql.UUID(as_uuid=True),
            unique=True,
            nullable=True,
            comment="Client-supplied UUID for safe retry",
        ),
        # Recorded at (posted timestamp)
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
            comment="When the transaction was posted",
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

    # Check constraints for transactions
    op.create_check_constraint(
        "ck_transactions_status",
        "transactions",
        sa.text(
            f"status = ANY(ARRAY[{', '.join(repr(s) for s in VALID_STATUSES)}])"
        ),
    )

    # Indexes for transactions
    op.create_index(
        "ix_transactions_reference",
        "transactions",
        ["reference"],
        unique=True,
    )
    op.create_index(
        "ix_transactions_idempotency_key",
        "transactions",
        ["idempotency_key"],
        unique=True,
    )
    op.create_index("ix_transactions_status", "transactions", ["status"])
    op.create_index("ix_transactions_effective_date", "transactions", ["effective_date"])
    op.create_index("ix_transactions_contact_id", "transactions", ["contact_id"])

    # ======================================================================
    # 2. postings
    # ======================================================================
    op.create_table(
        "postings",
        # Primary key
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # FK to transactions
        sa.Column(
            "transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("transactions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # FK to accounts
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        # Debit amount
        sa.Column(
            "debit_amount",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Debit amount in pence (always >= 0)",
        ),
        # Credit amount
        sa.Column(
            "credit_amount",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Credit amount in pence (always >= 0)",
        ),
        # Line description
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
            comment="Line-level narrative",
        ),
        # Timestamp
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Check constraints for postings
    op.create_check_constraint(
        "ck_postings_debit_non_negative",
        "postings",
        sa.text("debit_amount >= 0"),
    )
    op.create_check_constraint(
        "ck_postings_credit_non_negative",
        "postings",
        sa.text("credit_amount >= 0"),
    )
    op.create_check_constraint(
        "ck_postings_exactly_one_non_zero",
        "postings",
        sa.text(
            "(debit_amount > 0 AND credit_amount = 0) OR "
            "(debit_amount = 0 AND credit_amount > 0)"
        ),
    )

    # Indexes
    op.create_index("ix_postings_transaction_id", "postings", ["transaction_id"])
    op.create_index("ix_postings_account_id", "postings", ["account_id"])

    # ======================================================================
    # 3. vat_lines
    # ======================================================================
    op.create_table(
        "vat_lines",
        # Primary key
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # FK to postings
        sa.Column(
            "posting_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("postings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # VAT rate
        sa.Column(
            "vat_rate",
            sa.String(10),
            nullable=False,
            comment="VAT rate: 20%, 5%, 0%, or exempt",
        ),
        # VAT amount
        sa.Column(
            "vat_amount",
            sa.Integer,
            nullable=False,
            comment="VAT amount in pence",
        ),
        # Net amount
        sa.Column(
            "net_amount",
            sa.Integer,
            nullable=False,
            comment="Net (pre-VAT) amount in pence",
        ),
        # VAT type
        sa.Column(
            "vat_type",
            sa.String(6),
            nullable=False,
            comment="VAT direction: input (purchase) or output (sale)",
        ),
    )

    # Check constraints for vat_lines
    op.create_check_constraint(
        "ck_vat_lines_rate",
        "vat_lines",
        sa.text(
            f"vat_rate = ANY(ARRAY[{', '.join(repr(v) for v in VALID_VAT_RATES)}])"
        ),
    )
    op.create_check_constraint(
        "ck_vat_lines_type",
        "vat_lines",
        sa.text(
            f"vat_type = ANY(ARRAY[{', '.join(repr(v) for v in VALID_VAT_TYPES)}])"
        ),
    )

    # Indexes
    op.create_index("ix_vat_lines_posting_id", "vat_lines", ["posting_id"])


def downgrade() -> None:
    """Drop vat_lines, postings, and transactions tables."""
    op.drop_table("vat_lines")
    op.drop_table("postings")
    op.drop_table("transactions")
