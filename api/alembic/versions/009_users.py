"""009_users — Create users table for multi-user auth.

Revision ID: 009
Revises: 008
Create Date: 2026-06-27

Creates the users table with role-based access control for:
- Owner, Admin, Bookkeeper, Accountant, Viewer
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

VALID_ROLES = ("owner", "admin", "bookkeeper", "accountant", "viewer")


def upgrade() -> None:
    """Create users table."""
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "email",
            sa.String(255),
            unique=True,
            nullable=False,
            comment="User email address (used as login identifier)",
        ),
        sa.Column(
            "hashed_password",
            sa.String(255),
            nullable=False,
            comment="bcrypt-hashed password",
        ),
        sa.Column(
            "display_name",
            sa.String(255),
            nullable=False,
            comment="Human-readable display name",
        ),
        sa.Column(
            "role",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'viewer'"),
            comment="User role: owner|admin|bookkeeper|accountant|viewer",
        ),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
            comment="Whether the user account is active",
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
        "ck_users_role",
        "users",
        sa.text(
            f"role = ANY(ARRAY[{', '.join(repr(r) for r in VALID_ROLES)}])"
        ),
    )

    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_is_active", "users", ["is_active"])


def downgrade() -> None:
    """Drop users table."""
    op.drop_table("users")
