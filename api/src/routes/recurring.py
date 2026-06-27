"""FastAPI router for Recurring Transactions & Invoices — Module 7."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.services.recurring_service import (
    AccountNotFoundError,
    ContactNotFoundError,
    RecurringService,
    TemplateNotFoundError,
    TemplateNotActiveError,
)
from src.validators.recurring import (
    RecurringProcessResponse,
    RecurringTemplateCreate,
    RecurringTemplateListResponse,
    RecurringTemplateResponse,
)

router = APIRouter(prefix="/api/v1/recurring", tags=["Recurring"])


# ---------------------------------------------------------------------------
# POST /templates — Create template
# ---------------------------------------------------------------------------


@router.post(
    "/templates",
    response_model=RecurringTemplateResponse,
    summary="Create a recurring template",
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Account or contact not found"},
        422: {"description": "Validation error"},
    },
)
async def create_template(
    data: RecurringTemplateCreate,
    db: AsyncSession = Depends(get_db),
) -> RecurringTemplateResponse:
    """Create a new recurring template for transactions or invoices.

    Requires transaction_detail for transaction type, invoice_detail for invoice type.
    """
    try:
        return await RecurringService.create_template(db, data)
    except (AccountNotFoundError, ContactNotFoundError) as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# GET /templates — List templates
# ---------------------------------------------------------------------------


@router.get(
    "/templates",
    response_model=RecurringTemplateListResponse,
    summary="List recurring templates",
    status_code=status.HTTP_200_OK,
)
async def list_templates(
    template_type: Optional[str] = Query(
        None,
        description="Filter by template type: transaction or invoice",
        pattern=r"^(transaction|invoice)$",
    ),
    is_active: Optional[bool] = Query(
        None,
        description="Filter by active status",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> RecurringTemplateListResponse:
    """List recurring templates with optional type and active status filters."""
    items, total = await RecurringService.list_templates(
        db,
        template_type=template_type,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return RecurringTemplateListResponse(templates=items, total=total)


# ---------------------------------------------------------------------------
# GET /templates/{id} — Get template
# ---------------------------------------------------------------------------


@router.get(
    "/templates/{template_id}",
    response_model=RecurringTemplateResponse,
    summary="Get template details",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Template not found"}},
)
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RecurringTemplateResponse:
    """Get a single recurring template with its transaction or invoice detail."""
    template = await RecurringService.get_template(db, template_id)
    if template is None:
        raise HTTPException(
            status_code=404,
            detail=f"Recurring template '{template_id}' not found",
        )
    return template


# ---------------------------------------------------------------------------
# PATCH /templates/{id} — Update template
# ---------------------------------------------------------------------------


@router.patch(
    "/templates/{template_id}",
    response_model=RecurringTemplateResponse,
    summary="Update a recurring template",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Template not found"},
        422: {"description": "Validation error"},
    },
)
async def update_template(
    template_id: uuid.UUID,
    data: RecurringTemplateCreate,
    db: AsyncSession = Depends(get_db),
) -> RecurringTemplateResponse:
    """Update a recurring template and its detail record."""
    try:
        return await RecurringService.update_template(db, template_id, data)
    except TemplateNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# DELETE /templates/{id} — Delete template
# ---------------------------------------------------------------------------


@router.delete(
    "/templates/{template_id}",
    summary="Delete a recurring template",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Template not found"}},
)
async def delete_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a recurring template and its detail record."""
    try:
        await RecurringService.delete_template(db, template_id)
    except TemplateNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /templates/{id}/skip — Skip next occurrence
# ---------------------------------------------------------------------------


@router.post(
    "/templates/{template_id}/skip",
    response_model=RecurringTemplateResponse,
    summary="Skip the next occurrence",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Template not found"},
        422: {"description": "Template is not active"},
    },
)
async def skip_next(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RecurringTemplateResponse:
    """Skip one occurrence: advance next_run_date without creating a record."""
    try:
        return await RecurringService.skip_next(db, template_id)
    except TemplateNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except TemplateNotActiveError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /templates/{id}/pause — Pause template
# ---------------------------------------------------------------------------


@router.post(
    "/templates/{template_id}/pause",
    response_model=RecurringTemplateResponse,
    summary="Pause a recurring template",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Template not found"}},
)
async def pause_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RecurringTemplateResponse:
    """Pause a template (set is_active=False)."""
    try:
        return await RecurringService.pause_template(db, template_id)
    except TemplateNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /templates/{id}/resume — Resume template
# ---------------------------------------------------------------------------


@router.post(
    "/templates/{template_id}/resume",
    response_model=RecurringTemplateResponse,
    summary="Resume a paused template",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Template not found"}},
)
async def resume_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RecurringTemplateResponse:
    """Resume a paused template (set is_active=True).

    If next_run_date is in the past, it is set to today.
    """
    try:
        return await RecurringService.resume_template(db, template_id)
    except TemplateNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /process — Process all due templates
# ---------------------------------------------------------------------------


@router.post(
    "/process",
    response_model=RecurringProcessResponse,
    summary="Process all due recurring templates",
    status_code=status.HTTP_200_OK,
)
async def process_due(
    db: AsyncSession = Depends(get_db),
) -> RecurringProcessResponse:
    """Trigger processing of all due templates.

    Creates transactions or invoices for every active template with
    next_run_date <= today, then advances their schedule.
    """
    count = await RecurringService.process_due_templates(db)
    return RecurringProcessResponse(
        processed=count,
        message=f"Processed {count} due template(s)",
    )
