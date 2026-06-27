"""006_invoicing — Create invoices, invoice_lines, credit_notes tables.

Revision ID: 006
Revises: 005
Create Date: 2026-06-27

Creates tables for Basic Invoicing (Module 6):
- invoices: sales invoices with status lifecycle
- invoice_lines: line items for invoices
- credit_notes: credit notes offsetting invoices
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VALID_INVOICE_STATUSES = ("draft", "sent", "viewed", "paid", "overdue", "cancelled")
VALID_VAT_RATES = ("20%", "5%", "0%", "exempt")


def upgrade() -> None:
    """Create invoices, invoice_lines, and credit_notes tables."""
    # ---- invoices -----------------------------------------------------------
    op.create_table(
        "invoices",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "reference",
            sa.String(14),
            nullable=True,
            unique=True,
            comment="Invoice reference: INV-YYYY-NNNN (set on send)",
        ),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id", ondelete="RESTRICT"),
            nullable=False,
            comment="FK to contacts table",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'draft'"),
            comment="Invoice status: draft|sent|viewed|paid|overdue|cancelled",
        ),
        sa.Column(
            "issue_date",
            sa.Date,
            nullable=False,
            comment="Date the invoice was issued",
        ),
        sa.Column(
            "due_date",
            sa.Date,
            nullable=False,
            comment="Date payment is due",
        ),
        sa.Column(
            "subtotal",
            sa.Integer,
            nullable=False,
            comment="Sum of line totals before VAT (pence)",
        ),
        sa.Column(
            "vat_total",
            sa.Integer,
            nullable=False,
            comment="Total VAT amount (pence)",
        ),
        sa.Column(
            "total",
            sa.Integer,
            nullable=False,
            comment="Grand total = subtotal + vat_total (pence)",
        ),
        sa.Column(
            "currency",
            sa.String(3),
            nullable=False,
            server_default=sa.text("'GBP'"),
            comment="ISO 4217 currency code",
        ),
        sa.Column(
            "notes",
            sa.Text,
            nullable=True,
            comment="Optional invoice notes / payment instructions",
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the invoice was sent to the customer",
        ),
        sa.Column(
            "viewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the customer first viewed the invoice",
        ),
        sa.Column(
            "paid_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the invoice was marked as paid",
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

    # Check constraints for invoices
    op.create_check_constraint(
        "ck_invoices_status",
        "invoices",
        sa.text(
            f"status = ANY(ARRAY[{', '.join(repr(s) for s in VALID_INVOICE_STATUSES)}])"
        ),
    )
    op.create_check_constraint(
        "ck_invoices_subtotal_non_negative",
        "invoices",
        sa.text("subtotal >= 0"),
    )
    op.create_check_constraint(
        "ck_invoices_vat_total_non_negative",
        "invoices",
        sa.text("vat_total >= 0"),
    )
    op.create_check_constraint(
        "ck_invoices_total_non_negative",
        "invoices",
        sa.text("total >= 0"),
    )
    op.create_check_constraint(
        "ck_invoices_due_date",
        "invoices",
        sa.text("due_date >= issue_date"),
    )

    # Indexes for invoices
    op.create_index("ix_invoices_contact_id", "invoices", ["contact_id"])
    op.create_index("ix_invoices_status", "invoices", ["status"])
    op.create_index("ix_invoices_issue_date", "invoices", ["issue_date"])
    op.create_index("ix_invoices_due_date", "invoices", ["due_date"])
    op.create_index("ix_invoices_reference", "invoices", ["reference"], unique=True)

    # ---- invoice_lines ------------------------------------------------------
    op.create_table(
        "invoice_lines",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
            comment="FK to invoices table",
        ),
        sa.Column(
            "description",
            sa.String(500),
            nullable=False,
            comment="Description of the line item",
        ),
        sa.Column(
            "quantity",
            sa.Integer,
            nullable=False,
            server_default=sa.text("1"),
            comment="Quantity (whole units)",
        ),
        sa.Column(
            "unit_price",
            sa.Integer,
            nullable=False,
            comment="Unit price in pence",
        ),
        sa.Column(
            "vat_rate",
            sa.String(10),
            nullable=False,
            comment="VAT rate: 20%|5%|0%|exempt",
        ),
        sa.Column(
            "vat_amount",
            sa.Integer,
            nullable=False,
            comment="VAT amount for this line (pence)",
        ),
        sa.Column(
            "line_total",
            sa.Integer,
            nullable=False,
            comment="Line total = quantity * unit_price + vat_amount (pence)",
        ),
        sa.Column(
            "sort_order",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    # Check constraints for invoice_lines
    op.create_check_constraint(
        "ck_invoice_lines_vat_rate",
        "invoice_lines",
        sa.text(
            f"vat_rate = ANY(ARRAY[{', '.join(repr(r) for r in VALID_VAT_RATES)}])"
        ),
    )
    op.create_check_constraint(
        "ck_invoice_lines_quantity_positive",
        "invoice_lines",
        sa.text("quantity > 0"),
    )
    op.create_check_constraint(
        "ck_invoice_lines_unit_price_non_negative",
        "invoice_lines",
        sa.text("unit_price >= 0"),
    )
    op.create_check_constraint(
        "ck_invoice_lines_vat_amount_non_negative",
        "invoice_lines",
        sa.text("vat_amount >= 0"),
    )
    op.create_check_constraint(
        "ck_invoice_lines_line_total_non_negative",
        "invoice_lines",
        sa.text("line_total >= 0"),
    )

    # Index for invoice_lines
    op.create_index("ix_invoice_lines_invoice_id", "invoice_lines", ["invoice_id"])

    # ---- credit_notes -------------------------------------------------------
    op.create_table(
        "credit_notes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="RESTRICT"),
            nullable=False,
            comment="FK to original invoice",
        ),
        sa.Column(
            "reference",
            sa.String(14),
            nullable=True,
            unique=True,
            comment="Credit note reference: CN-YYYY-NNNN",
        ),
        sa.Column(
            "contact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("contacts.id", ondelete="RESTRICT"),
            nullable=False,
            comment="FK to contacts table",
        ),
        sa.Column(
            "total",
            sa.Integer,
            nullable=False,
            comment="Credit note total in pence (negative value)",
        ),
        sa.Column(
            "reason",
            sa.Text,
            nullable=True,
            comment="Reason for issuing credit note",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Check constraint for credit_notes
    op.create_check_constraint(
        "ck_credit_notes_total_negative",
        "credit_notes",
        sa.text("total < 0"),
    )

    # Indexes for credit_notes
    op.create_index("ix_credit_notes_invoice_id", "credit_notes", ["invoice_id"])
    op.create_index("ix_credit_notes_contact_id", "credit_notes", ["contact_id"])
    op.create_index("ix_credit_notes_reference", "credit_notes", ["reference"], unique=True)


def downgrade() -> None:
    """Drop credit_notes, invoice_lines, then invoices."""
    op.drop_table("credit_notes")
    op.drop_table("invoice_lines")
    op.drop_table("invoices")
