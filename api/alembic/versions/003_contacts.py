"""003_contacts — Create contacts table with all columns, constraints, and indexes.

Revision ID: 003
Revises: 002
Create Date: 2026-06-27

Creates the contacts table for Contact Management (Module 3) with
duplicate detection on email and VAT number, plus AR/AP balance tracking.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VALID_TYPES = ("customer", "supplier", "both")
VALID_STATUSES = ("active", "archived")


def upgrade() -> None:
    """Create the contacts table."""
    op.create_table(
        "contacts",
        # Primary key
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        # Type
        sa.Column(
            "type",
            sa.String(10),
            nullable=False,
            comment="Contact type: customer, supplier, or both",
        ),
        # Core identity fields
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Contact display name (individual or organisation)",
        ),
        sa.Column(
            "company",
            sa.String(255),
            nullable=True,
            comment="Company / trading name if different from contact name",
        ),
        sa.Column(
            "email",
            sa.String(255),
            nullable=True,
            comment="Primary email address (unique)",
        ),
        sa.Column(
            "phone",
            sa.String(50),
            nullable=True,
            comment="Primary phone number",
        ),
        # Address fields
        sa.Column(
            "address_line1",
            sa.String(255),
            nullable=True,
            comment="Address line 1",
        ),
        sa.Column(
            "address_line2",
            sa.String(255),
            nullable=True,
            comment="Address line 2",
        ),
        sa.Column(
            "city",
            sa.String(100),
            nullable=True,
            comment="Town / city",
        ),
        sa.Column(
            "postcode",
            sa.String(10),
            nullable=True,
            comment="Postcode / ZIP",
        ),
        sa.Column(
            "country",
            sa.String(2),
            nullable=False,
            server_default=sa.text("'GB'"),
            comment="ISO 3166-1 alpha-2 country code",
        ),
        # VAT and payment
        sa.Column(
            "vat_number",
            sa.String(20),
            nullable=True,
            comment="UK/EU VAT registration number (unique)",
        ),
        sa.Column(
            "payment_terms",
            sa.String(50),
            nullable=False,
            server_default=sa.text("'Net 30'"),
            comment="Default payment terms (e.g., Net 30, Due on Receipt)",
        ),
        # FK to accounts
        sa.Column(
            "default_gl_account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="SET NULL"),
            nullable=True,
            comment="Default GL account for transactions with this contact",
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
            server_default=sa.text("'active'"),
            comment="Contact status: active or archived",
        ),
        # Balance tracking (all in INTEGER pence)
        sa.Column(
            "total_invoiced",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Total amount invoiced to/from this contact (pence)",
        ),
        sa.Column(
            "total_paid",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Total amount paid by/to this contact (pence)",
        ),
        sa.Column(
            "total_owing",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
            comment="Outstanding balance: total_invoiced - total_paid (pence)",
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
        "ck_contacts_type",
        "contacts",
        sa.text(
            f"type = ANY(ARRAY[{', '.join(repr(t) for t in VALID_TYPES)}])"
        ),
    )
    op.create_check_constraint(
        "ck_contacts_status",
        "contacts",
        sa.text(
            f"status = ANY(ARRAY[{', '.join(repr(s) for s in VALID_STATUSES)}])"
        ),
    )

    # ---- Indexes ----
    op.create_index("ix_contacts_email", "contacts", ["email"], unique=True)
    op.create_index("ix_contacts_vat_number", "contacts", ["vat_number"], unique=True)
    op.create_index("ix_contacts_status", "contacts", ["status"])
    op.create_index("ix_contacts_type", "contacts", ["type"])
    op.create_index("ix_contacts_name", "contacts", ["name"])
    op.create_index("ix_contacts_default_gl_account_id", "contacts", ["default_gl_account_id"])


def downgrade() -> None:
    """Drop the contacts table."""
    op.drop_table("contacts")
