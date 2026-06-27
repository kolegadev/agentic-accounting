"""FastAPI router for Core Financial Reports — Module 8."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.services.report_service import (
    InvalidReportParameterError,
    ReportService,
    ReportServiceError,
    ReportTemplateNotFoundError,
    ScheduledReportNotFoundError,
)
from src.validators.report import (
    ReportRunRequest,
    ReportRunResponse,
    ReportTemplateListResponse,
    ReportTemplateResponse,
    ScheduleReportCreate,
    ScheduledReportListResponse,
    ScheduledReportResponse,
)

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


# ---------------------------------------------------------------------------
# GET /templates — List report templates
# ---------------------------------------------------------------------------


@router.get(
    "/templates",
    response_model=ReportTemplateListResponse,
    summary="List available report templates",
    status_code=status.HTTP_200_OK,
)
async def list_templates(
    category: Optional[str] = Query(
        None,
        description="Filter by category (financial|tax|management|other)",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> ReportTemplateListResponse:
    """Return all available report templates with optional category filter."""
    items, total = await ReportService.list_templates(
        db,
        category=category,
        limit=limit,
        offset=offset,
    )
    return ReportTemplateListResponse(templates=items, total=total)


# ---------------------------------------------------------------------------
# GET /templates/{template_id} — Get report template
# ---------------------------------------------------------------------------


@router.get(
    "/templates/{template_id}",
    response_model=ReportTemplateResponse,
    summary="Get a report template by ID",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Template not found"}},
)
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ReportTemplateResponse:
    """Return a single report template by ID."""
    tmpl = await ReportService.get_template(db, template_id)
    if tmpl is None:
        raise HTTPException(
            status_code=404,
            detail=f"Report template '{template_id}' not found",
        )
    return tmpl


# ---------------------------------------------------------------------------
# POST /run — Run a report
# ---------------------------------------------------------------------------


@router.post(
    "/run",
    response_model=ReportRunResponse,
    summary="Run a financial report",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Report template not found"},
        422: {"description": "Invalid parameters"},
    },
)
async def run_report(
    data: ReportRunRequest,
    db: AsyncSession = Depends(get_db),
) -> ReportRunResponse:
    """Run any supported financial report by template_name.

    Supported templates:
    - profit_and_loss: Revenue - Direct Costs = Gross Profit - Expenses = Net Profit
    - balance_sheet: Assets = Liabilities + Equity
    - trial_balance: All accounts with debit/credit totals, verified zero difference
    - aged_ar: Aged Accounts Receivable (0-30, 31-60, 61-90, 90+ days)
    - aged_ap: Aged Accounts Payable (0-30, 31-60, 61-90, 90+ days)

    Parameters:
    - start_date / end_date: reporting period
    - format: json (default), csv, html, pdf
    - comparison: include prior period comparison (P&L only)
    - parameters: additional report-specific parameters
    """
    try:
        return await ReportService.run(db, data)
    except ReportTemplateNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except InvalidReportParameterError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# GET /schedules — List scheduled reports
# ---------------------------------------------------------------------------


@router.get(
    "/schedules",
    response_model=ScheduledReportListResponse,
    summary="List scheduled reports",
    status_code=status.HTTP_200_OK,
)
async def list_schedules(
    is_active: Optional[bool] = Query(
        None,
        description="Filter by active status",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> ScheduledReportListResponse:
    """Return all scheduled reports with optional active filter."""
    items, total = await ReportService.list_schedules(
        db,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return ScheduledReportListResponse(schedules=items, total=total)


# ---------------------------------------------------------------------------
# POST /schedules — Create scheduled report
# ---------------------------------------------------------------------------


@router.post(
    "/schedules",
    response_model=ScheduledReportResponse,
    summary="Create a scheduled report",
    status_code=status.HTTP_201_CREATED,
    responses={422: {"description": "Invalid parameters or template not found"}},
)
async def create_schedule(
    data: ScheduleReportCreate,
    db: AsyncSession = Depends(get_db),
) -> ScheduledReportResponse:
    """Schedule a report for recurring generation.

    Supported schedules: daily, weekly, monthly, quarterly.
    The report will be generated and sent to recipient_email at each scheduled run.
    """
    try:
        return await ReportService.create_schedule(db, data)
    except InvalidReportParameterError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except ReportServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# GET /schedules/{schedule_id} — Get scheduled report
# ---------------------------------------------------------------------------


@router.get(
    "/schedules/{schedule_id}",
    response_model=ScheduledReportResponse,
    summary="Get a scheduled report by ID",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Schedule not found"}},
)
async def get_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ScheduledReportResponse:
    """Return a single scheduled report by ID."""
    sched = await ReportService.get_schedule(db, schedule_id)
    if sched is None:
        raise HTTPException(
            status_code=404,
            detail=f"Scheduled report '{schedule_id}' not found",
        )
    return sched


# ---------------------------------------------------------------------------
# DELETE /schedules/{schedule_id} — Delete scheduled report
# ---------------------------------------------------------------------------


@router.delete(
    "/schedules/{schedule_id}",
    summary="Delete a scheduled report",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Schedule not found"}},
)
async def delete_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a scheduled report configuration."""
    deleted = await ReportService.delete_schedule(db, schedule_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"Scheduled report '{schedule_id}' not found",
        )
