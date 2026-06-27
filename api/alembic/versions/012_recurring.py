"""012_recurring — Create recurring_templates, recurring_transactions, recurring_invoices.

Revision ID: 012
Revises: 011
Create Date: 2026-06-27

Creates three tables for the Recurring Transactions & Invoices module:
  - recurring_templates: Schedule and end conditions for recurring records
  - recurring_transactions: Transaction detail (for transaction type templates)
  - recurring_invoices: Invoice detail (for invoice type templates)
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create recurring tables."""

    # ---- recurring_templates ----
    op.create_table(
        "recurring_templates",
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
            comment="Human-readable template name (e.g., 'Monthly Rent')",
        ),
        sa.Column(
            "template_type",
            sa.String(20),
            nullable=False,
            comment="Template type: transaction | invoice",
        ),
        sa.Column(
            "frequency",
            sa.String(20),
            nullable=False,
            comment="Recurrence frequency: daily|weekly|bi_weekly|monthly|quarterly|annual",
        ),
        sa.Column(
            "next_run_date",
            sa.Date,
            nullable=False,
            comment="Next scheduled run date",
        ),
        sa.Column(
            "end_type",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'never'"),
            comment="End condition: never | after_count | until_date",
        ),
        sa.Column(
            "end_after_count",
            sa.Integer,
            nullable=True,
            comment="Stop after this many occurrences (used with after_count)",
        ),
        sa.Column(
            "end_until_date",
            sa.Date,
            nullable=True,
            comment="Stop after this date (used with until_date)",
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
            comment="Whether this template is currently active",
        ),
        sa.Column(
            "last_run_date",
            sa.Date,
            nullable=True,
            comment="Date of the last successful run",
        ),
        sa.Column(
            "run_count",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Number of times this template has been processed",
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

    op.create_index("ix_templates_template_type", "recurring_templates", ["template_type"])
    op.create_index("ix_templates_is_active", "recurring_templates", ["is_active"])
    op.create_index("ix_templates_next_run_date", "recurring_templates", ["next_run_date"])

    # ---- recurring_transactions ----
    op.create_table(
        "recurring_transactions",
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
            sa.ForeignKey("recurring_templates.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            comment="FK to recurring_templates",
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=False,
            comment="Transaction description applied on each recurrence",
        ),
        sa.Column(
            "debit_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="RESTRICT"),
            nullable=False,
            comment="Account to debit",
        ),
        sa.Column(
            "credit_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="RESTRICT"),
            nullable=False,
            comment="Account to credit",
        ),
        sa.Column(
            "amount_pence",
            sa.Integer,
            nullable=False,
            comment="Transaction amount in pence (always positive)",
        ),
        sa.Column(
            "vat_rate",
            sa.String(10),
            nullable=True,
            comment="VAT rate: 20%|5%|0%|exempt",
        ),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id", ondelete="SET NULL"),
            nullable=True,
            comment="Optional FK to contacts",
        ),
    )

    op.create_index("ix_rt_template_id", "recurring_transactions", ["template_id"], unique=True)
    op.create_index("ix_rt_debit_account_id", "recurring_transactions", ["debit_account_id"])
    op.create_index("ix_rt_credit_account_id", "recurring_transactions", ["credit_account_id"])

    # ---- recurring_invoices ----
    op.create_table(
        "recurring_invoices",
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
            sa.ForeignKey("recurring_templates.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            comment="FK to recurring_templates",
        ),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id", ondelete="RESTRICT"),
            nullable=False,
            comment="Customer to invoice",
        ),
        sa.Column(
            "items",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="Array of {description, quantity, unit_price, vat_rate}",
        ),
        sa.Column(
            "payment_terms",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'Net 30'"),
            comment="Payment terms (e.g., 'Net 30', 'Net 7', 'Due on receipt')",
        ),
        sa.Column(
            "notes",
            sa.Text,
            nullable=True,
            comment="Optional notes applied to each invoice",
        ),
    )

    op.create_index("ix_ri_template_id", "recurring_invoices", ["template_id"], unique=True)
    op.create_index("ix_ri_contact_id", "recurring_invoices", ["contact_id"])


def downgrade() -> None:
    """Drop recurring tables."""
    op.drop_table("recurring_invoices")
    op.drop_table("recurring_transactions")
    op.drop_table("recurring_templates")
