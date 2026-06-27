"""FastAPI router for Document OCR & Extraction endpoints."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.services.document_service import (
    DocumentNotFoundError,
    DocumentService,
    DocumentServiceError,
    ExtractionAlreadyConfirmedError,
    InvalidDocumentTypeError,
)
from src.validators.document import (
    ConfirmExtractionRequest,
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)

router = APIRouter(prefix="/api/v1/documents", tags=["Document OCR"])


# ---------------------------------------------------------------------------
# POST /upload — Upload document
# ---------------------------------------------------------------------------


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    summary="Upload a document for OCR extraction",
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {"description": "Unsupported content type"},
    },
)
async def upload_document(
    file: UploadFile = File(..., description="Receipt or invoice document (JPEG, PNG, PDF)"),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    """Upload a receipt or invoice document for OCR data extraction.

    Supported formats: image/jpeg, image/png, application/pdf.
    Extraction is triggered automatically after upload.
    In MVP mode, extraction is simulated based on filename patterns.
    """
    if not file.content_type:
        raise HTTPException(
            status_code=422,
            detail="Content-Type header is required",
        )

    file_content = await file.read()
    if not file_content:
        raise HTTPException(
            status_code=422,
            detail="Empty file uploaded",
        )

    try:
        return await DocumentService.upload_document(
            db,
            file_content=file_content,
            filename=file.filename or "unnamed",
            content_type=file.content_type,
        )
    except InvalidDocumentTypeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# GET / — List documents
# ---------------------------------------------------------------------------


@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="List documents",
    status_code=status.HTTP_200_OK,
)
async def list_documents(
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status: uploaded, extracting, extracted, reviewed, failed",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """List all uploaded documents with optional status filter and pagination."""
    items, total = await DocumentService.list_documents(
        db,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    return DocumentListResponse(items=items, total=total)


# ---------------------------------------------------------------------------
# GET /{document_id} — Get document with extraction
# ---------------------------------------------------------------------------


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document with extraction data",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Document not found"}},
)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Return a single document by its UUID, including any extraction data."""
    document = await DocumentService.get_document(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{document_id}' not found",
        )
    return document


# ---------------------------------------------------------------------------
# GET /{document_id}/download — Download original file
# ---------------------------------------------------------------------------


@router.get(
    "/{document_id}/download",
    summary="Download original document file",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Document not found"},
    },
)
async def download_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download the original uploaded document file.

    In MVP mode, returns a placeholder since files are not actually stored
    in an external object store. The response includes the original filename
    and content type so consumers can adapt when MinIO is integrated.
    """
    document = await DocumentService.get_document_raw(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=404,
            detail=f"Document '{document_id}' not found",
        )

    # In MVP mode, return an empty body with correct headers
    # This signals to the client that the download endpoint is wired up
    return Response(
        content=bytes(document.file_size),
        media_type=document.content_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{document.filename}"'
            ),
            "X-Document-Status": document.status,
            "X-MVP-Placeholder": "true",
        },
    )


# ---------------------------------------------------------------------------
# POST /{document_id}/extract — Trigger extraction
# ---------------------------------------------------------------------------


@router.post(
    "/{document_id}/extract",
    response_model=DocumentResponse,
    summary="Trigger OCR extraction on a document",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Document not found"},
    },
)
async def extract_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Explicitly trigger extraction on a previously uploaded document.

    Re-runs extraction even if the document was already extracted,
    overwriting the previous extraction data.
    Useful for retrying a failed extraction or re-extracting with
    an updated engine.
    """
    try:
        return await DocumentService.extract_data(db, document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /{document_id}/confirm — Confirm/review extraction
# ---------------------------------------------------------------------------


@router.post(
    "/{document_id}/confirm",
    response_model=DocumentResponse,
    summary="Confirm or correct extracted data",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Document not found"},
        409: {"description": "Extraction already reviewed"},
    },
)
async def confirm_extraction(
    document_id: uuid.UUID,
    data: ConfirmExtractionRequest,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Mark a document's extraction as reviewed by a human.

    Optionally provide corrected data, which replaces the original
    extraction_data and sets confidence_score to 1.0 (human-verified).
    """
    try:
        return await DocumentService.confirm_extraction(
            db,
            document_id=document_id,
            corrected_data=data.corrected_data,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except ExtractionAlreadyConfirmedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
