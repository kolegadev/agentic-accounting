"""Unit tests for DocumentService with mocked DB session."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.document import Document
from src.services.document_service import (
    DocumentNotFoundError,
    DocumentService,
    DocumentServiceError,
    ExtractionAlreadyConfirmedError,
    InvalidDocumentTypeError,
)
from src.validators.document import (
    ConfirmExtractionRequest,
    ExtractionLineItem,
    ExtractionResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db() -> AsyncMock:
    """Return an AsyncMock that behaves like an async SQLAlchemy session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def sample_document() -> Document:
    """Create a fully-populated Document ORM instance."""
    now = datetime(2026, 6, 27, 12, 0, 0)
    return Document(
        id=uuid.uuid4(),
        filename="amazon_invoice.pdf",
        content_type="application/pdf",
        file_size=102400,
        minio_key="documents/12345_amazon_invoice.pdf",
        status="uploaded",
        extraction_data=None,
        confidence_score=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_extraction_result() -> ExtractionResult:
    """Return a sample ExtractionResult."""
    return ExtractionResult(
        supplier_name="Amazon Business",
        invoice_date=date(2026, 6, 15),
        due_date=date(2026, 7, 15),
        invoice_number="INV-20260615-1234",
        total_amount_pence=25000,
        vat_amount_pence=4167,
        currency="GBP",
        line_items=[
            ExtractionLineItem(
                description="Office Supplies - A4 Paper (5 reams)",
                quantity=2,
                unit_price_pence=6250,
                total_price_pence=12500,
                vat_rate="20%",
            ),
            ExtractionLineItem(
                description="Ergonomic Mouse",
                quantity=1,
                unit_price_pence=12500,
                total_price_pence=12500,
                vat_rate="20%",
            ),
        ],
        confidence_score=0.95,
    )


@pytest.fixture
def sample_document_extracted(sample_document: Document) -> Document:
    """Create a Document that has been extracted."""
    doc = Document(
        id=sample_document.id,
        filename=sample_document.filename,
        content_type=sample_document.content_type,
        file_size=sample_document.file_size,
        minio_key=sample_document.minio_key,
        status="extracted",
        extraction_data={
            "supplier_name": "Amazon Business",
            "invoice_date": "2026-06-15",
            "due_date": "2026-07-15",
            "invoice_number": "INV-20260615-1234",
            "total_amount_pence": 25000,
            "vat_amount_pence": 4167,
            "currency": "GBP",
            "line_items": [
                {
                    "description": "Office Supplies - A4 Paper (5 reams)",
                    "quantity": 2,
                    "unit_price_pence": 6250,
                    "total_price_pence": 12500,
                    "vat_rate": "20%",
                }
            ],
            "confidence_score": 0.95,
        },
        confidence_score=0.95,
        created_at=sample_document.created_at,
        updated_at=sample_document.updated_at,
    )
    return doc


# ---------------------------------------------------------------------------
# Upload tests
# ---------------------------------------------------------------------------


class TestUploadDocument:
    """Tests for uploading documents."""

    @pytest.mark.asyncio
    async def test_upload_jpeg(
        self, mock_db: AsyncMock, sample_document: Document
    ) -> None:
        """Should upload a JPEG document successfully."""
        sample_document.filename = "receipt.jpg"
        mock_db.refresh.side_effect = [
            None,  # After initial commit (upload)
            None,  # After status update (extracting)
            None,  # After extraction
        ]

        with patch.object(
            DocumentService, "extract_data", new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = (
                DocumentService._document_to_response(sample_document)
            )

            result = await DocumentService.upload_document(
                mock_db,
                file_content=b"fake-jpeg-data",
                filename="receipt.jpg",
                content_type="image/jpeg",
            )

        assert result.document.filename == "receipt.jpg"
        assert "triggered successfully" in result.message

    @pytest.mark.asyncio
    async def test_upload_unsupported_type(self, mock_db: AsyncMock) -> None:
        """Should raise InvalidDocumentTypeError for unsupported types."""
        with pytest.raises(InvalidDocumentTypeError) as exc:
            await DocumentService.upload_document(
                mock_db,
                file_content=b"fake-data",
                filename="document.docx",
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        assert "Unsupported" in exc.value.message

    @pytest.mark.asyncio
    async def test_upload_generates_minio_key(
        self, mock_db: AsyncMock, sample_document: Document
    ) -> None:
        """Should generate a valid MinIO key during upload."""
        mock_db.refresh.return_value = None

        with patch.object(
            DocumentService, "extract_data", new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = (
                DocumentService._document_to_response(sample_document)
            )

            result = await DocumentService.upload_document(
                mock_db,
                file_content=b"test-content",
                filename="amazon_invoice.pdf",
                content_type="application/pdf",
            )

        assert result.document.minio_key.startswith("documents/")
        assert "amazon_invoice.pdf" in result.document.minio_key


# ---------------------------------------------------------------------------
# Extract tests
# ---------------------------------------------------------------------------


class TestExtractData:
    """Tests for data extraction."""

    @pytest.mark.asyncio
    async def test_extract_not_found(self, mock_db: AsyncMock) -> None:
        """Should raise DocumentNotFoundError for unknown ID."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(DocumentNotFoundError):
            await DocumentService.extract_data(mock_db, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_extract_transitions_status(
        self, mock_db: AsyncMock, sample_document: Document
    ) -> None:
        """Should transition document through extracting → extracted."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_document
        mock_db.execute.return_value = mock_result

        with patch.object(
            DocumentService, "_simulate_extraction"
        ) as mock_simulate:
            mock_simulate.return_value = ExtractionResult(
                supplier_name="Amazon Business",
                invoice_date=date(2026, 6, 15),
                due_date=date(2026, 7, 15),
                invoice_number="INV-20260615-9999",
                total_amount_pence=35000,
                vat_amount_pence=5833,
                currency="GBP",
                line_items=[],
                confidence_score=0.92,
            )

            result = await DocumentService.extract_data(
                mock_db, sample_document.id
            )

        assert sample_document.status == "extracted"
        assert sample_document.extraction_data is not None
        assert result.status == "extracted"

    @pytest.mark.asyncio
    async def test_extract_stores_confidence(
        self, mock_db: AsyncMock, sample_document: Document
    ) -> None:
        """Should store confidence score on the document."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_document
        mock_db.execute.return_value = mock_result

        with patch.object(
            DocumentService, "_simulate_extraction"
        ) as mock_simulate:
            mock_simulate.return_value = ExtractionResult(
                supplier_name="Tesco Stores Ltd",
                invoice_date=date(2026, 6, 20),
                due_date=date(2026, 6, 20),
                invoice_number="INV-20260620-5555",
                total_amount_pence=8500,
                vat_amount_pence=0,
                currency="GBP",
                line_items=[],
                confidence_score=0.88,
            )

            result = await DocumentService.extract_data(
                mock_db, sample_document.id
            )

        assert sample_document.confidence_score == 0.88
        assert result.confidence_score == 0.88


# ---------------------------------------------------------------------------
# Get / List tests
# ---------------------------------------------------------------------------


class TestGetDocument:
    """Tests for getting documents."""

    @pytest.mark.asyncio
    async def test_get_document_found(
        self, mock_db: AsyncMock, sample_document_extracted: Document
    ) -> None:
        """Should return document when found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_document_extracted
        mock_db.execute.return_value = mock_result

        result = await DocumentService.get_document(
            mock_db, sample_document_extracted.id
        )

        assert result is not None
        assert result.filename == "amazon_invoice.pdf"
        assert result.status == "extracted"
        assert result.extraction_data is not None
        assert result.extraction_data.supplier_name == "Amazon Business"

    @pytest.mark.asyncio
    async def test_get_document_not_found(self, mock_db: AsyncMock) -> None:
        """Should return None when document not found."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await DocumentService.get_document(mock_db, uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_get_document_no_extraction(
        self, mock_db: AsyncMock, sample_document: Document
    ) -> None:
        """Should return document without extraction data for uploaded docs."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_document
        mock_db.execute.return_value = mock_result

        result = await DocumentService.get_document(
            mock_db, sample_document.id
        )

        assert result is not None
        assert result.extraction_data is None
        assert result.status == "uploaded"


class TestListDocuments:
    """Tests for listing documents."""

    @pytest.mark.asyncio
    async def test_list_empty(self, mock_db: AsyncMock) -> None:
        """Should return empty list when no documents."""
        # Mock count
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        # Mock items
        mock_items_result = MagicMock()
        mock_items_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[mock_count_result, mock_items_result]
        )

        items, total = await DocumentService.list_documents(mock_db)
        assert items == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_with_items(
        self, mock_db: AsyncMock, sample_document: Document
    ) -> None:
        """Should return documents in the list."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_items_result = MagicMock()
        mock_items_result.scalars.return_value.all.return_value = [
            sample_document
        ]

        mock_db.execute = AsyncMock(
            side_effect=[mock_count_result, mock_items_result]
        )

        items, total = await DocumentService.list_documents(mock_db)
        assert len(items) == 1
        assert total == 1
        assert items[0].filename == "amazon_invoice.pdf"


# ---------------------------------------------------------------------------
# Confirm tests
# ---------------------------------------------------------------------------


class TestConfirmExtraction:
    """Tests for confirming/correcting extraction."""

    @pytest.mark.asyncio
    async def test_confirm_not_found(self, mock_db: AsyncMock) -> None:
        """Should raise DocumentNotFoundError for unknown ID."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(DocumentNotFoundError):
            await DocumentService.confirm_extraction(mock_db, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_confirm_already_reviewed(
        self, mock_db: AsyncMock, sample_document_extracted: Document
    ) -> None:
        """Should raise error if already reviewed."""
        sample_document_extracted.status = "reviewed"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_document_extracted
        mock_db.execute.return_value = mock_result

        with pytest.raises(ExtractionAlreadyConfirmedError):
            await DocumentService.confirm_extraction(
                mock_db, sample_document_extracted.id
            )

    @pytest.mark.asyncio
    async def test_confirm_success(
        self, mock_db: AsyncMock, sample_document_extracted: Document
    ) -> None:
        """Should transition to reviewed status."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_document_extracted
        mock_db.execute.return_value = mock_result

        result = await DocumentService.confirm_extraction(
            mock_db, sample_document_extracted.id
        )

        assert sample_document_extracted.status == "reviewed"
        assert result.status == "reviewed"

    @pytest.mark.asyncio
    async def test_confirm_with_corrections(
        self, mock_db: AsyncMock, sample_document_extracted: Document,
        sample_extraction_result: ExtractionResult,
    ) -> None:
        """Should replace extraction data with corrected version."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_document_extracted
        mock_db.execute.return_value = mock_result

        corrected = ExtractionResult(
            supplier_name="Amazon Business UK Ltd",
            invoice_date=date(2026, 6, 15),
            due_date=date(2026, 7, 15),
            invoice_number="INV-20260615-1234",
            total_amount_pence=30000,
            vat_amount_pence=5000,
            currency="GBP",
            line_items=[],
            confidence_score=1.0,
        )

        result = await DocumentService.confirm_extraction(
            mock_db,
            sample_document_extracted.id,
            corrected_data=corrected,
        )

        assert sample_document_extracted.confidence_score == 1.0
        assert sample_document_extracted.extraction_data["supplier_name"] == "Amazon Business UK Ltd"
        assert sample_document_extracted.extraction_data["total_amount_pence"] == 30000
        assert result.confidence_score == 1.0


# ---------------------------------------------------------------------------
# Simulate extraction tests
# ---------------------------------------------------------------------------


class TestSimulateExtraction:
    """Tests for the _simulate_extraction method."""

    def test_amazon_invoice_extraction(self) -> None:
        """Should detect Amazon from filename."""
        result = DocumentService._simulate_extraction("amazon_invoice.pdf")

        assert result.supplier_name == "Amazon Business"
        assert result.currency == "GBP"
        assert result.total_amount_pence > 0
        assert result.confidence_score >= 0.85
        assert len(result.line_items) > 0

    def test_tesco_receipt_extraction(self) -> None:
        """Should detect Tesco from filename."""
        result = DocumentService._simulate_extraction("tesco_receipt.png")

        assert result.supplier_name == "Tesco Stores Ltd"
        assert result.confidence_score >= 0.85

    def test_unknown_supplier_extraction(self) -> None:
        """Should return Unknown Supplier for unrecognised filenames."""
        result = DocumentService._simulate_extraction("random_scan.jpeg")

        assert result.supplier_name == "Unknown Supplier"
        assert result.confidence_score < 0.85  # Lower confidence for unknown

    def test_extraction_is_deterministic(self) -> None:
        """Same filename should produce identical extraction results."""
        result1 = DocumentService._simulate_extraction("amazon_invoice.pdf")
        result2 = DocumentService._simulate_extraction("amazon_invoice.pdf")

        assert result1.supplier_name == result2.supplier_name
        assert result1.total_amount_pence == result2.total_amount_pence
        assert result1.confidence_score == result2.confidence_score

    def test_line_items_sum_to_total(self) -> None:
        """Line items should sum to total_amount_pence (within rounding)."""
        result = DocumentService._simulate_extraction("amazon_invoice.pdf")

        line_sum = sum(item.total_price_pence for item in result.line_items)
        assert line_sum == result.total_amount_pence

    def test_vat_calculation_consistent(self) -> None:
        """VAT amount should be consistent with total and line items."""
        result = DocumentService._simulate_extraction("amazon_invoice.pdf")

        if result.vat_amount_pence is not None and result.vat_amount_pence > 0:
            # VAT should be less than total
            assert result.vat_amount_pence < result.total_amount_pence

    def test_all_supported_suppliers(self) -> None:
        """Each known supplier keyword should produce a named supplier."""
        test_files = [
            "amazon_order.pdf",
            "tesco_weekly.jpg",
            "sainsbury_shop.png",
            "trainline_tickets.pdf",
            "uber_ride.jpg",
            "deliveroo_lunch.png",
            "apple_purchase.pdf",
            "google_workspace.jpg",
            "microsoft_365.png",
            "dropbox_sub.pdf",
            "slack_sub.jpg",
            "github_plan.png",
            "aws_bill.pdf",
            "office_supplies.jpg",
            "stationery_order.png",
            "travelodge_stay.pdf",
            "premier_inn_booking.jpg",
        ]

        for f in test_files:
            result = DocumentService._simulate_extraction(f)
            assert result.supplier_name != "Unknown Supplier", (
                f"File '{f}' should produce a known supplier, "
                f"got '{result.supplier_name}'"
            )
