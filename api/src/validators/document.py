"""Pydantic schemas for Document OCR request/response validation."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class ExtractionLineItem(BaseModel):
    """A single line item extracted from a document."""

    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Line item description",
        examples=["Office Supplies - A4 Paper (5 reams)"],
    )
    quantity: int = Field(
        default=1,
        ge=1,
        description="Quantity of items",
    )
    unit_price_pence: int = Field(
        ...,
        ge=0,
        description="Unit price in pence (GBP)",
    )
    total_price_pence: int = Field(
        ...,
        ge=0,
        description="Line total in pence (GBP)",
    )
    vat_rate: Optional[str] = Field(
        default="20%",
        description="VAT rate applied to this line",
        examples=["20%", "5%", "0%", "exempt"],
    )


class ExtractionResult(BaseModel):
    """Extracted data from a document (simulated OCR output)."""

    supplier_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Supplier/vendor name",
        examples=["Amazon Business"],
    )
    invoice_date: Optional[date] = Field(
        default=None,
        description="Invoice/receipt date",
    )
    due_date: Optional[date] = Field(
        default=None,
        description="Payment due date",
    )
    invoice_number: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Invoice or receipt number",
    )
    total_amount_pence: int = Field(
        ...,
        ge=0,
        description="Total amount in pence (GBP)",
    )
    vat_amount_pence: Optional[int] = Field(
        default=None,
        ge=0,
        description="VAT amount in pence (GBP)",
    )
    currency: str = Field(
        default="GBP",
        min_length=3,
        max_length=3,
        description="ISO 4217 currency code",
    )
    line_items: list[ExtractionLineItem] = Field(
        default_factory=list,
        description="Extracted line items",
    )
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall extraction confidence (0.0-1.0)",
    )


class DocumentResponse(BaseModel):
    """Schema for document responses (all fields)."""

    id: uuid.UUID
    filename: str
    content_type: str
    file_size: int
    minio_key: str
    status: str
    extraction_data: Optional[ExtractionResult] = None
    confidence_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    """Schema for listing documents."""

    items: list[DocumentResponse]
    total: int


class ConfirmExtractionRequest(BaseModel):
    """Schema for confirming/correcting extracted data."""

    corrected_data: Optional[ExtractionResult] = Field(
        default=None,
        description="Corrected extraction data (if any fields need fixing)",
    )
    review_notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Optional review notes from the human reviewer",
    )


class DocumentUploadResponse(BaseModel):
    """Response returned after successful document upload."""

    document: DocumentResponse
    message: str = Field(
        default="Document uploaded successfully",
        description="Status message",
    )
