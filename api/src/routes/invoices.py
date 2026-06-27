"""FastAPI router for Invoice Management endpoints — Module 6."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.services.invoice_service import (
    ContactNotFoundError,
    InvoiceLifecycleError,
    InvoiceNotFoundError,
    InvoiceService,
)
from src.validators.invoice import (
    CreditNoteResponse,
    InvoiceCreate,
    InvoiceListResponse,
    InvoiceResponse,
)

router = APIRouter(prefix="/api/v1/invoices", tags=["Invoices"])


# ---------------------------------------------------------------------------
# POST / — Create invoice (Draft)
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=InvoiceResponse,
    summary="Create a new draft invoice",
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Contact not found"},
        422: {"description": "Validation error"},
    },
)
async def create_invoice(
    data: InvoiceCreate,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """Create a new draft invoice with line items.

    VAT and totals are calculated automatically.
    """
    try:
        return await InvoiceService.create_invoice(db, data)
    except ContactNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /{invoice_id}/send — Send invoice
# ---------------------------------------------------------------------------


@router.post(
    "/{invoice_id}/send",
    response_model=InvoiceResponse,
    summary="Send a draft invoice to the customer",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Invoice not found"},
        422: {"description": "Invoice cannot be sent"},
    },
)
async def send_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """Send a draft invoice: Draft → Sent.

    Generates INV-YYYY-NNNN reference and enforces immutability.
    """
    try:
        return await InvoiceService.send_invoice(db, invoice_id)
    except InvoiceNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except InvoiceLifecycleError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# GET / — List invoices (must be before /{invoice_id})
# ---------------------------------------------------------------------------


@router.get(
    "/",
    response_model=InvoiceListResponse,
    summary="List invoices with optional filters",
    status_code=status.HTTP_200_OK,
)
async def list_invoices(
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by invoice status",
    ),
    contact_id: Optional[uuid.UUID] = Query(
        None,
        description="Filter by contact ID",
    ),
    date_from: Optional[date] = Query(
        None,
        description="Filter from issue date (inclusive)",
    ),
    date_to: Optional[date] = Query(
        None,
        description="Filter to issue date (inclusive)",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> InvoiceListResponse:
    """List invoices with optional status, contact, and date range filters."""
    items, total = await InvoiceService.list_invoices(
        db,
        status=status_filter,
        contact_id=contact_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return InvoiceListResponse(invoices=items, total=total)


# ---------------------------------------------------------------------------
# GET /overdue — Check for overdue invoices (must be before /{invoice_id})
# ---------------------------------------------------------------------------


@router.get(
    "/overdue",
    response_model=list[InvoiceResponse],
    summary="Check and mark overdue invoices",
    status_code=status.HTTP_200_OK,
)
async def check_overdue(
    db: AsyncSession = Depends(get_db),
) -> list[InvoiceResponse]:
    """Auto-detect and mark invoices past their due date as overdue.

    Returns the list of newly overdue invoices.
    """
    return await InvoiceService.check_overdue(db)


# ---------------------------------------------------------------------------
# GET /{invoice_id} — Get invoice by ID
# ---------------------------------------------------------------------------


@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Get invoice by ID with line items",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Invoice not found"}},
)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """Return a single invoice with its line items."""
    invoice = await InvoiceService.get_invoice(db, invoice_id)
    if invoice is None:
        raise HTTPException(
            status_code=404,
            detail=f"Invoice '{invoice_id}' not found",
        )
    return invoice


# ---------------------------------------------------------------------------
# PATCH /{invoice_id}/viewed — Mark invoice as viewed
# ---------------------------------------------------------------------------


@router.patch(
    "/{invoice_id}/viewed",
    response_model=InvoiceResponse,
    summary="Mark an invoice as viewed by the customer",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Invoice not found"},
        422: {"description": "Invalid status transition"},
    },
)
async def mark_as_viewed(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """Mark invoice as viewed: Sent → Viewed."""
    try:
        return await InvoiceService.mark_as_viewed(db, invoice_id)
    except InvoiceNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except InvoiceLifecycleError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /{invoice_id}/mark-paid — Mark invoice as paid
# ---------------------------------------------------------------------------


@router.post(
    "/{invoice_id}/mark-paid",
    response_model=InvoiceResponse,
    summary="Mark an invoice as paid",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Invoice not found"},
        422: {"description": "Invalid status transition"},
    },
)
async def mark_as_paid(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """Mark invoice as paid: Sent/Viewed/Overdue → Paid."""
    try:
        return await InvoiceService.mark_as_paid(db, invoice_id)
    except InvoiceNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except InvoiceLifecycleError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /{invoice_id}/cancel — Cancel invoice
# ---------------------------------------------------------------------------


@router.post(
    "/{invoice_id}/cancel",
    response_model=InvoiceResponse,
    summary="Cancel a draft invoice",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Invoice not found"},
        422: {"description": "Cannot cancel non-draft invoice"},
    },
)
async def cancel_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """Cancel a draft invoice. Sent invoices require a credit note instead."""
    try:
        return await InvoiceService.cancel_invoice(db, invoice_id)
    except InvoiceNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except InvoiceLifecycleError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /{invoice_id}/credit-note — Create credit note
# ---------------------------------------------------------------------------


@router.post(
    "/{invoice_id}/credit-note",
    response_model=CreditNoteResponse,
    summary="Create a credit note for an invoice",
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Invoice not found"},
        422: {"description": "Invoice cannot be credited"},
    },
)
async def create_credit_note(
    invoice_id: uuid.UUID,
    reason: Optional[str] = Query(
        None,
        description="Reason for issuing credit note",
    ),
    db: AsyncSession = Depends(get_db),
) -> CreditNoteResponse:
    """Create a credit note for a sent/viewed/paid/overdue invoice.

    Marks the original invoice as cancelled.
    """
    try:
        return await InvoiceService.create_credit_note(
            db,
            invoice_id,
            reason=reason,
        )
    except InvoiceNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except InvoiceLifecycleError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# GET /{invoice_id}/pdf — Generate PDF
# ---------------------------------------------------------------------------


@router.get(
    "/{invoice_id}/pdf",
    summary="Download invoice as PDF",
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Invoice PDF",
        },
        404: {"description": "Invoice not found"},
    },
)
async def generate_pdf(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Generate and download the invoice as a PDF."""
    try:
        pdf_bytes = await InvoiceService.generate_pdf(db, invoice_id)
    except InvoiceNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    # Get invoice for filename
    invoice = await InvoiceService.get_invoice(db, invoice_id)
    ref = invoice.reference if invoice and invoice.reference else str(invoice_id)

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="invoice-{ref}.pdf"',
        },
    )
