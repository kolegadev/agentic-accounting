"""Business logic for Document OCR & Extraction — DocumentService.

In MVP mode, uses template-based extraction (simulated OCR).
Phase 3 will add Tesseract/DocTR + GPT-4o Vision for real extraction.
"""

from __future__ import annotations

import hashlib
import random
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.document import Document
from src.validators.document import (
    ConfirmExtractionRequest,
    DocumentResponse,
    DocumentUploadResponse,
    ExtractionLineItem,
    ExtractionResult,
)

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class DocumentServiceError(Exception):
    """Base exception for document service errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class DocumentNotFoundError(DocumentServiceError):
    """Document not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Document '{identifier}' not found", status_code=404)


class InvalidDocumentTypeError(DocumentServiceError):
    """Unsupported content type."""

    def __init__(self, content_type: str) -> None:
        super().__init__(
            f"Unsupported content type '{content_type}'. "
            f"Supported types: image/jpeg, image/png, application/pdf",
            status_code=422,
        )


class ExtractionAlreadyConfirmedError(DocumentServiceError):
    """Extraction has already been reviewed."""

    def __init__(self, document_id: str) -> None:
        super().__init__(
            f"Document '{document_id}' has already been reviewed",
            status_code=409,
        )


# ---------------------------------------------------------------------------
# DocumentService
# ---------------------------------------------------------------------------


class DocumentService:
    """Stateless service for document ingestion and simulated OCR extraction."""

    SUPPORTED_TYPES = {"image/jpeg", "image/png", "application/pdf"}

    # ------------------------------------------------------------------
    # Response mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _document_to_response(document: Document) -> DocumentResponse:
        """Map a Document ORM instance to a response schema.

        Converts extraction_data dict into ExtractionResult if present.
        """
        extraction_result: Optional[ExtractionResult] = None
        if document.extraction_data:
            extraction_result = ExtractionResult(**document.extraction_data)

        return DocumentResponse(
            id=document.id,
            filename=document.filename,
            content_type=document.content_type,
            file_size=document.file_size,
            minio_key=document.minio_key,
            status=document.status,
            extraction_data=extraction_result,
            confidence_score=document.confidence_score,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    @staticmethod
    async def upload_document(
        db: AsyncSession,
        file_content: bytes,
        filename: str,
        content_type: str,
    ) -> DocumentUploadResponse:
        """Save a document, create its record, and trigger extraction.

        In MVP mode, we simulate MinIO storage by computing a fake key
        and storing the file size. The actual file is not persisted to
        an external object store in MVP.
        """
        if content_type not in DocumentService.SUPPORTED_TYPES:
            raise InvalidDocumentTypeError(content_type)

        file_size = len(file_content)

        # Fake MinIO key — in production this would be the actual object path
        timestamp = int(time.time())
        safe_filename = "".join(
            c if c.isalnum() or c in "._-" else "_" for c in filename
        )
        minio_key = f"documents/{timestamp}_{safe_filename}"

        document = Document(
            filename=filename,
            content_type=content_type,
            file_size=file_size,
            minio_key=minio_key,
            status="uploaded",
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)

        # Trigger extraction immediately (MVP: synchronous call)
        doc_response = await DocumentService.extract_data(db, document.id)

        return DocumentUploadResponse(
            document=doc_response,
            message="Document uploaded and extraction triggered successfully",
        )

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    @staticmethod
    async def extract_data(
        db: AsyncSession,
        document_id: uuid.UUID,
    ) -> DocumentResponse:
        """Run simulated OCR extraction on a document.

        For MVP, uses _simulate_extraction which generates realistic mock
        data based on filename patterns. Updates the document with extracted
        fields and confidence score.
        """
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        document = result.scalar_one_or_none()
        if document is None:
            raise DocumentNotFoundError(str(document_id))

        # Transition to extracting
        document.status = "extracting"
        await db.commit()
        await db.refresh(document)

        # Run simulated extraction
        extraction = DocumentService._simulate_extraction(document.filename)

        # Update document with extraction results
        document.extraction_data = extraction.model_dump()
        document.confidence_score = extraction.confidence_score
        document.status = "extracted"
        await db.commit()
        await db.refresh(document)

        return DocumentService._document_to_response(document)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @staticmethod
    async def get_document(
        db: AsyncSession,
        document_id: uuid.UUID,
    ) -> Optional[DocumentResponse]:
        """Return a single document by ID, or None."""
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        document = result.scalar_one_or_none()
        return (
            DocumentService._document_to_response(document) if document else None
        )

    @staticmethod
    async def list_documents(
        db: AsyncSession,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DocumentResponse], int]:
        """List documents with optional status filter."""
        # Build query
        stmt = select(Document)
        count_stmt = select(func.count(Document.id))

        if status_filter:
            stmt = stmt.where(Document.status == status_filter)
            count_stmt = count_stmt.where(Document.status == status_filter)

        # Get total count
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Get paginated items
        stmt = (
            stmt.order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        documents = list(result.scalars().all())

        items = [DocumentService._document_to_response(d) for d in documents]
        return items, total

    @staticmethod
    async def get_document_raw(
        db: AsyncSession,
        document_id: uuid.UUID,
    ) -> Optional[Document]:
        """Return a raw Document ORM instance (used for file download metadata)."""
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Confirm / Review
    # ------------------------------------------------------------------

    @staticmethod
    async def confirm_extraction(
        db: AsyncSession,
        document_id: uuid.UUID,
        corrected_data: Optional[ExtractionResult] = None,
    ) -> DocumentResponse:
        """Mark an extraction as reviewed by a human.

        Optionally applies corrected data, which replaces the original
        extraction_data and sets confidence_score to 1.0 (human-verified).
        """
        stmt = select(Document).where(Document.id == document_id)
        result = await db.execute(stmt)
        document = result.scalar_one_or_none()
        if document is None:
            raise DocumentNotFoundError(str(document_id))

        if document.status == "reviewed":
            raise ExtractionAlreadyConfirmedError(str(document_id))

        if corrected_data:
            document.extraction_data = corrected_data.model_dump()
            document.confidence_score = 1.0  # Human-verified

        document.status = "reviewed"
        await db.commit()
        await db.refresh(document)

        return DocumentService._document_to_response(document)

    # ------------------------------------------------------------------
    # Simulated Extraction (MVP)
    # ------------------------------------------------------------------

    @staticmethod
    def _simulate_extraction(filename: str) -> ExtractionResult:
        """Generate realistic mock extraction data based on filename patterns.

        The simulation uses a deterministic seed derived from the filename
        so that repeated calls for the same file produce consistent results.
        Detection logic looks for known supplier keywords and document type
        patterns embedded in the filename.

        Examples:
            "amazon_invoice.pdf" → supplier: Amazon Business, items: Office Supplies
            "tesco_receipt.png" → supplier: Tesco, items: Groceries
            "trainline_receipt.jpg" → supplier: Trainline, items: Travel
        """
        # Use filename hash as seed for reproducibility
        seed = int(hashlib.sha256(filename.encode("utf-8")).hexdigest()[:8], 16)
        rng = random.Random(seed)

        filename_lower = filename.lower()

        # ---- Supplier detection from filename keywords -----------------
        supplier_patterns = {
            "amazon": "Amazon Business",
            "tesco": "Tesco Stores Ltd",
            "sainsbury": "Sainsbury's Supermarkets Ltd",
            "trainline": "Trainline.com Ltd",
            "uber": "Uber BV",
            "deliveroo": "Deliveroo UK Ltd",
            "apple": "Apple Distribution International",
            "google": "Google Ireland Ltd",
            "microsoft": "Microsoft Ireland Operations Ltd",
            "dropbox": "Dropbox International Ltd",
            "slack": "Slack Technologies Ltd",
            "github": "GitHub Inc.",
            "aws": "Amazon Web Services Ltd",
            "office": "Office Supplies Co",
            "stationery": "Stationery World Ltd",
            "travelodge": "Travelodge Hotels Ltd",
            "premier_inn": "Premier Inn Hotels Ltd",
        }

        supplier_name = "Unknown Supplier"
        for keyword, supplier in supplier_patterns.items():
            if keyword in filename_lower:
                supplier_name = supplier
                break

        # ---- Date generation ------------------------------------------
        today = date.today()
        invoice_date = today - timedelta(days=rng.randint(0, 90))
        due_date = invoice_date + timedelta(days=rng.choice([0, 7, 14, 30]))

        invoice_number = f"INV-{invoice_date.strftime('%Y%m%d')}-{rng.randint(1000, 9999)}"

        # ---- Amount generation ----------------------------------------
        # Different suppliers have different typical amounts
        supplier_amount_ranges: dict[str, tuple[int, int]] = {
            "Amazon Business": (5000, 50000),    # £50–£500
            "Tesco Stores Ltd": (2000, 15000),    # £20–£150
            "Sainsbury's Supermarkets Ltd": (2000, 12000),
            "Trainline.com Ltd": (3000, 25000),   # £30–£250
            "Uber BV": (800, 5000),               # £8–£50
            "Deliveroo UK Ltd": (1500, 6000),     # £15–£60
            "Apple Distribution International": (500, 100000),
            "Google Ireland Ltd": (500, 50000),
            "Microsoft Ireland Operations Ltd": (500, 50000),
            "Dropbox International Ltd": (500, 2000),
            "Slack Technologies Ltd": (500, 2000),
            "GitHub Inc.": (500, 2000),
            "Amazon Web Services Ltd": (5000, 100000),
            "Office Supplies Co": (1000, 30000),
            "Stationery World Ltd": (1000, 20000),
            "Travelodge Hotels Ltd": (5000, 20000),
            "Premier Inn Hotels Ltd": (5000, 20000),
        }

        min_amount, max_amount = supplier_amount_ranges.get(
            supplier_name, (1000, 50000)
        )
        total_amount_pence = rng.randint(min_amount, max_amount)

        # ---- VAT calculation ------------------------------------------
        vat_rates = [0, 5, 20]  # exempt, 5%, 20%
        vat_weights = [0.1, 0.05, 0.85]  # Most items are standard-rated
        chosen_vat_rate = rng.choices(vat_rates, weights=vat_weights, k=1)[0]

        if chosen_vat_rate > 0:
            # VAT amount = total * (rate / (100 + rate))
            vat_amount_pence = round(
                total_amount_pence * chosen_vat_rate / (100 + chosen_vat_rate)
            )
        else:
            vat_amount_pence = 0

        # ---- Line items -----------------------------------------------
        # Generate 1-5 line items that sum to total_amount_pence
        supplier_items: dict[str, list[str]] = {
            "Amazon Business": [
                "Office Supplies - A4 Paper (5 reams)",
                "Standing Desk Converter",
                "Ergonomic Mouse",
                "USB-C Hub",
                "Monitor Stand",
            ],
            "Tesco Stores Ltd": [
                "Groceries - Weekly Shop",
                "Fresh Produce",
                "Dairy & Eggs",
                "Bakery Items",
                "Household Supplies",
            ],
            "Sainsbury's Supermarkets Ltd": [
                "Groceries - Weekly Shop",
                "Fresh Fruit & Vegetables",
                "Meat & Poultry",
                "Cleaning Products",
                "Pet Food",
            ],
            "Trainline.com Ltd": [
                "London to Manchester Return",
                "Railcard - Annual",
                "First Class Upgrade",
                "Season Ticket",
            ],
            "Uber BV": [
                "Trip - Home to Office",
                "Trip - Airport Transfer",
                "Trip - Client Meeting",
            ],
            "Deliveroo UK Ltd": [
                "Team Lunch - Pizza",
                "Working Lunch - Sushi",
                "Dinner - Indian Takeaway",
            ],
            "Apple Distribution International": [
                "MacBook Pro 14-inch",
                "iPhone Accessories",
                "AppleCare+ Protection Plan",
                "Magic Keyboard",
            ],
            "Google Ireland Ltd": [
                "Google Workspace Business Plus",
                "Google Cloud Storage",
            ],
            "Microsoft Ireland Operations Ltd": [
                "Microsoft 365 Business Premium",
                "Azure Cloud Services",
            ],
            "Dropbox International Ltd": [
                "Dropbox Business Standard",
            ],
            "Slack Technologies Ltd": [
                "Slack Business+",
            ],
            "GitHub Inc.": [
                "GitHub Team Plan",
            ],
            "Amazon Web Services Ltd": [
                "AWS EC2 t3.medium (720 hours)",
                "AWS S3 Standard Storage (500 GB)",
                "AWS RDS db.t3.micro (720 hours)",
                "AWS Lambda Requests",
            ],
            "Office Supplies Co": [
                "Printer Paper A4 - 10 Reams",
                "Ballpoint Pens - Box of 50",
                "Whiteboard Markers",
                "Filing Cabinet",
            ],
            "Stationery World Ltd": [
                "Envelopes DL - 500 Pack",
                "Notebooks A5 - Pack of 10",
                "Sticky Notes - Assorted",
            ],
            "Travelodge Hotels Ltd": [
                "Single Room - 2 Nights",
                "Breakfast x2",
                "WiFi Premium",
            ],
            "Premier Inn Hotels Ltd": [
                "Double Room - 1 Night",
                "Meal Deal x1",
                "Late Checkout",
            ],
        }

        available_items = supplier_items.get(
            supplier_name,
            [
                "General Supplies",
                "Office Expenses",
                "Miscellaneous Purchase",
            ],
        )

        num_items = rng.randint(1, min(len(available_items), 5))
        selected_items = rng.sample(available_items, num_items)

        # Distribute total across line items using random weights
        weights = [rng.randint(1, 10) for _ in range(num_items)]
        weight_total = sum(weights)
        allocated = 0

        line_items: list[ExtractionLineItem] = []
        for i, item_desc in enumerate(selected_items):
            if i == num_items - 1:
                line_total = total_amount_pence - allocated
            else:
                line_total = round(total_amount_pence * weights[i] / weight_total)
                allocated += line_total

            quantity = rng.randint(1, 10)
            unit_price = round(line_total / quantity)

            line_items.append(
                ExtractionLineItem(
                    description=item_desc,
                    quantity=quantity,
                    unit_price_pence=unit_price,
                    total_price_pence=line_total,
                    vat_rate=f"{chosen_vat_rate}%" if chosen_vat_rate > 0 else "exempt",
                )
            )

        # ---- Confidence score ----------------------------------------
        # Recognised suppliers get higher confidence
        if supplier_name == "Unknown Supplier":
            confidence = round(rng.uniform(0.50, 0.70), 2)
        else:
            confidence = round(rng.uniform(0.85, 0.98), 2)

        return ExtractionResult(
            supplier_name=supplier_name,
            invoice_date=invoice_date,
            due_date=due_date,
            invoice_number=invoice_number,
            total_amount_pence=total_amount_pence,
            vat_amount_pence=vat_amount_pence,
            currency="GBP",
            line_items=line_items,
            confidence_score=confidence,
        )
