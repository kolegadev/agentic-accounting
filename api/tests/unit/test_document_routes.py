"""Unit tests for Document routes using FastAPI TestClient with mocked service.

Tests all document OCR endpoints including upload, list, get, download, extract,
and confirm.
"""

from __future__ import annotations

import os
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure DATABASE_URL is set before src.config.database is imported
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test_db"

from src.index import app
from src.services.document_service import (
    DocumentNotFoundError,
    ExtractionAlreadyConfirmedError,
    InvalidDocumentTypeError,
)
from src.validators.document import (
    DocumentResponse,
    DocumentUploadResponse,
    ExtractionResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DOCUMENT_ID = uuid.uuid4()
NOW = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)


def make_document_response(**overrides) -> DocumentResponse:
    """Build a DocumentResponse with defaults overridden."""
    defaults = {
        "id": DOCUMENT_ID,
        "filename": "amazon_invoice.pdf",
        "content_type": "application/pdf",
        "file_size": 102400,
        "minio_key": "documents/12345_amazon_invoice.pdf",
        "status": "extracted",
        "extraction_data": ExtractionResult(
            supplier_name="Amazon Business",
            invoice_date=date(2026, 6, 15),
            due_date=date(2026, 7, 15),
            invoice_number="INV-20260615-1234",
            total_amount_pence=25000,
            vat_amount_pence=4167,
            currency="GBP",
            line_items=[],
            confidence_score=0.95,
        ),
        "confidence_score": 0.95,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(overrides)
    return DocumentResponse(**defaults)


def make_upload_response(**overrides) -> DocumentUploadResponse:
    """Build a DocumentUploadResponse with defaults overridden."""
    defaults = {
        "document": make_document_response(),
        "message": "Document uploaded and extraction triggered successfully",
    }
    defaults.update(overrides)
    return DocumentUploadResponse(**defaults)


@pytest.fixture
def client() -> TestClient:
    """Return a FastAPI TestClient."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /upload tests
# ---------------------------------------------------------------------------


class TestUploadDocument:
    """Tests for the document upload endpoint."""

    def test_upload_success(self, client: TestClient) -> None:
        """Should upload a valid document and return 201."""
        with patch(
            "src.routes.documents.DocumentService.upload_document",
            new_callable=AsyncMock,
        ) as mock_upload:
            mock_upload.return_value = make_upload_response()

            response = client.post(
                "/api/v1/documents/upload",
                files={
                    "file": (
                        "receipt.jpg",
                        b"fake-jpeg-data",
                        "image/jpeg",
                    )
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert "document" in data
        assert data["document"]["filename"] == "amazon_invoice.pdf"
        assert "triggered successfully" in data["message"]

    def test_upload_no_content_type(self, client: TestClient) -> None:
        """Should return 422 when Content-Type is empty."""
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", b"data", "")},
        )
        assert response.status_code == 422

    def test_upload_unsupported_type(self, client: TestClient) -> None:
        """Should return 422 for unsupported content types."""
        with patch(
            "src.routes.documents.DocumentService.upload_document",
            new_callable=AsyncMock,
        ) as mock_upload:
            mock_upload.side_effect = InvalidDocumentTypeError("text/plain")

            response = client.post(
                "/api/v1/documents/upload",
                files={
                    "file": ("notes.txt", b"text", "text/plain")
                },
            )

        assert response.status_code == 422

    def test_upload_empty_file(self, client: TestClient) -> None:
        """Should return 422 for empty file."""
        response = client.post(
            "/api/v1/documents/upload",
            files={
                "file": ("empty.pdf", b"", "application/pdf")
            },
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET / tests
# ---------------------------------------------------------------------------


class TestListDocuments:
    """Tests for listing documents."""

    def test_list_empty(self, client: TestClient) -> None:
        """Should return empty list when no documents exist."""
        with patch(
            "src.routes.documents.DocumentService.list_documents",
            new_callable=AsyncMock,
        ) as mock_list:
            mock_list.return_value = ([], 0)

            response = client.get("/api/v1/documents/")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_with_items(self, client: TestClient) -> None:
        """Should return paginated document list."""
        doc = make_document_response()
        with patch(
            "src.routes.documents.DocumentService.list_documents",
            new_callable=AsyncMock,
        ) as mock_list:
            mock_list.return_value = ([doc], 1)

            response = client.get("/api/v1/documents/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["items"][0]["filename"] == "amazon_invoice.pdf"

    def test_list_with_status_filter(self, client: TestClient) -> None:
        """Should filter by status."""
        with patch(
            "src.routes.documents.DocumentService.list_documents",
            new_callable=AsyncMock,
        ) as mock_list:
            mock_list.return_value = ([], 0)

            response = client.get(
                "/api/v1/documents/?status=reviewed"
            )

        assert response.status_code == 200
        mock_list.assert_called_once()
        call_kwargs = mock_list.call_args.kwargs
        assert call_kwargs["status_filter"] == "reviewed"

    def test_list_with_pagination(self, client: TestClient) -> None:
        """Should pass pagination parameters."""
        with patch(
            "src.routes.documents.DocumentService.list_documents",
            new_callable=AsyncMock,
        ) as mock_list:
            mock_list.return_value = ([], 0)

            response = client.get(
                "/api/v1/documents/?limit=10&offset=20"
            )

        assert response.status_code == 200
        mock_list.assert_called_once()
        call_kwargs = mock_list.call_args.kwargs
        assert call_kwargs["limit"] == 10
        assert call_kwargs["offset"] == 20


# ---------------------------------------------------------------------------
# GET /{id} tests
# ---------------------------------------------------------------------------


class TestGetDocument:
    """Tests for getting a single document."""

    def test_get_document_found(self, client: TestClient) -> None:
        """Should return document when found."""
        with patch(
            "src.routes.documents.DocumentService.get_document",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = make_document_response()

            response = client.get(f"/api/v1/documents/{DOCUMENT_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(DOCUMENT_ID)
        assert data["filename"] == "amazon_invoice.pdf"
        assert data["status"] == "extracted"
        assert data["extraction_data"] is not None
        assert data["extraction_data"]["supplier_name"] == "Amazon Business"

    def test_get_document_not_found(self, client: TestClient) -> None:
        """Should return 404 when document not found."""
        with patch(
            "src.routes.documents.DocumentService.get_document",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = None

            response = client.get(f"/api/v1/documents/{DOCUMENT_ID}")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /{id}/download tests
# ---------------------------------------------------------------------------


class TestDownloadDocument:
    """Tests for downloading original document file."""

    def test_download_found(self, client: TestClient) -> None:
        """Should return file bytes and headers when document found."""
        from unittest.mock import MagicMock
        doc = MagicMock()
        doc.file_size = 1024
        doc.filename = "receipt.jpg"
        doc.content_type = "image/jpeg"
        doc.status = "uploaded"

        with patch(
            "src.routes.documents.DocumentService.get_document_raw",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = doc

            response = client.get(
                f"/api/v1/documents/{DOCUMENT_ID}/download"
            )

        assert response.status_code == 200
        assert response.headers["Content-Disposition"] == (
            'attachment; filename="receipt.jpg"'
        )
        assert response.headers["X-MVP-Placeholder"] == "true"

    def test_download_not_found(self, client: TestClient) -> None:
        """Should return 404 when document not found."""
        with patch(
            "src.routes.documents.DocumentService.get_document_raw",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = None

            response = client.get(
                f"/api/v1/documents/{DOCUMENT_ID}/download"
            )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# POST /{id}/extract tests
# ---------------------------------------------------------------------------


class TestExtractDocument:
    """Tests for triggering extraction."""

    def test_extract_success(self, client: TestClient) -> None:
        """Should trigger extraction and return updated document."""
        with patch(
            "src.routes.documents.DocumentService.extract_data",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.return_value = make_document_response(
                status="extracted",
            )

            response = client.post(
                f"/api/v1/documents/{DOCUMENT_ID}/extract"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "extracted"

    def test_extract_not_found(self, client: TestClient) -> None:
        """Should return 404 when document not found."""
        with patch(
            "src.routes.documents.DocumentService.extract_data",
            new_callable=AsyncMock,
        ) as mock_extract:
            mock_extract.side_effect = DocumentNotFoundError(
                str(DOCUMENT_ID)
            )

            response = client.post(
                f"/api/v1/documents/{DOCUMENT_ID}/extract"
            )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /{id}/confirm tests
# ---------------------------------------------------------------------------


class TestConfirmExtraction:
    """Tests for confirming/correcting extraction."""

    def test_confirm_success(self, client: TestClient) -> None:
        """Should confirm extraction and transition to reviewed."""
        with patch(
            "src.routes.documents.DocumentService.confirm_extraction",
            new_callable=AsyncMock,
        ) as mock_confirm:
            mock_confirm.return_value = make_document_response(
                status="reviewed",
                confidence_score=1.0,
            )

            response = client.post(
                f"/api/v1/documents/{DOCUMENT_ID}/confirm",
                json={},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "reviewed"
        assert data["confidence_score"] == 1.0

    def test_confirm_with_corrections(self, client: TestClient) -> None:
        """Should accept corrected data in confirm request."""
        with patch(
            "src.routes.documents.DocumentService.confirm_extraction",
            new_callable=AsyncMock,
        ) as mock_confirm:
            mock_confirm.return_value = make_document_response(
                status="reviewed",
                extraction_data=ExtractionResult(
                    supplier_name="Corrected Supplier Ltd",
                    total_amount_pence=50000,
                    vat_amount_pence=8333,
                    currency="GBP",
                    line_items=[],
                    confidence_score=1.0,
                ),
                confidence_score=1.0,
            )

            payload = {
                "corrected_data": {
                    "supplier_name": "Corrected Supplier Ltd",
                    "total_amount_pence": 50000,
                    "vat_amount_pence": 8333,
                    "currency": "GBP",
                    "line_items": [],
                    "confidence_score": 1.0,
                },
                "review_notes": "Amount corrected per physical receipt",
            }

            response = client.post(
                f"/api/v1/documents/{DOCUMENT_ID}/confirm",
                json=payload,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "reviewed"
        mock_confirm.assert_called_once()

    def test_confirm_already_reviewed(self, client: TestClient) -> None:
        """Should return 409 when already reviewed."""
        with patch(
            "src.routes.documents.DocumentService.confirm_extraction",
            new_callable=AsyncMock,
        ) as mock_confirm:
            mock_confirm.side_effect = ExtractionAlreadyConfirmedError(
                str(DOCUMENT_ID)
            )

            response = client.post(
                f"/api/v1/documents/{DOCUMENT_ID}/confirm",
                json={},
            )

        assert response.status_code == 409

    def test_confirm_not_found(self, client: TestClient) -> None:
        """Should return 404 when document not found."""
        with patch(
            "src.routes.documents.DocumentService.confirm_extraction",
            new_callable=AsyncMock,
        ) as mock_confirm:
            mock_confirm.side_effect = DocumentNotFoundError(
                str(DOCUMENT_ID)
            )

            response = client.post(
                f"/api/v1/documents/{DOCUMENT_ID}/confirm",
                json={},
            )

        assert response.status_code == 404
