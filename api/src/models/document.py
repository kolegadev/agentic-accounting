"""SQLAlchemy model for Document — Document OCR Module."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base

VALID_DOCUMENT_STATUSES = ("uploaded", "extracting", "extracted", "reviewed", "failed")


class Document(Base):
    """A receipt or invoice document uploaded for OCR extraction.

    Files are stored in MinIO; this table tracks metadata and extraction results.
    In MVP mode, extraction is simulated via filename patterns.
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original filename as uploaded",
    )
    content_type: Mapped[str] = mapped_column(
        String(127),
        nullable=False,
        comment="MIME type (e.g., image/jpeg, application/pdf)",
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="File size in bytes",
    )
    minio_key: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        comment="Storage path / object key in MinIO",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="uploaded",
        server_default=text("'uploaded'"),
        comment="Lifecycle: uploaded | extracting | extracted | reviewed | failed",
    )
    extraction_data: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Extracted invoice/receipt fields (supplier_name, invoice_date, due_date, total_amount, vat_amount, line_items, etc.)",
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="OCR/extraction confidence score (0.0-1.0)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_documents_status", "status"),
        Index("ix_documents_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Document(id={self.id}, filename={self.filename!r}, "
            f"status={self.status!r})>"
        )
