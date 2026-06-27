"""013_documents — Create documents table for Document OCR & Extraction.

Revision ID: 013
Revises: 012
Create Date: 2026-06-27

Creates the documents table for receipt/invoice document scanning and
data extraction. In MVP mode, extraction is simulated (template-based).
Phase 3 will add Tesseract/DocTR + GPT-4o Vision for real OCR.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create documents table."""
    op.create_table(
        "documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "filename",
            sa.String(255),
            nullable=False,
            comment="Original filename as uploaded",
        ),
        sa.Column(
            "content_type",
            sa.String(127),
            nullable=False,
            comment="MIME type (e.g., image/jpeg, application/pdf)",
        ),
        sa.Column(
            "file_size",
            sa.Integer,
            nullable=False,
            comment="File size in bytes",
        ),
        sa.Column(
            "minio_key",
            sa.String(512),
            nullable=False,
            comment="Storage path / object key in MinIO",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'uploaded'"),
            comment="Lifecycle: uploaded | extracting | extracted | reviewed | failed",
        ),
        sa.Column(
            "extraction_data",
            postgresql.JSONB,
            nullable=True,
            comment="Extracted invoice/receipt fields (supplier_name, invoice_date, due_date, total_amount, vat_amount, line_items, etc.)",
        ),
        sa.Column(
            "confidence_score",
            sa.Float,
            nullable=True,
            comment="OCR/extraction confidence score (0.0-1.0)",
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

    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_created_at", "documents", ["created_at"])


def downgrade() -> None:
    """Drop documents table."""
    op.drop_table("documents")
