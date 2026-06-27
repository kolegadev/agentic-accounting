"""Pydantic models for report request/response validation — Module 8."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

VALID_SCHEDULES = ("daily", "weekly", "monthly", "quarterly")
VALID_FORMATS = ("json", "csv", "html", "pdf")
VALID_CATEGORIES = ("financial", "tax", "management", "other")
VALID_REPORT_TYPES = ("profit_and_loss", "balance_sheet", "trial_balance", "aged_ar", "aged_ap")


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ReportRunRequest(BaseModel):
    """Schema for running an on-demand report."""

    template_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Machine name of the report template (e.g. profit_and_loss, balance_sheet)",
    )
    start_date: date = Field(
        ...,
        description="Start date of the reporting period (inclusive)",
    )
    end_date: date = Field(
        ...,
        description="End date of the reporting period (inclusive). Must be >= start_date.",
    )
    format: str = Field(
        "json",
        description="Output format: json, csv, html, or pdf",
    )
    comparison: bool = Field(
        False,
        description="Include prior period comparison if True",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional report-specific parameters",
    )


class ScheduleReportCreate(BaseModel):
    """Schema for creating a scheduled report."""

    template_id: uuid.UUID = Field(
        ...,
        description="FK to report_templates",
    )
    schedule: str = Field(
        ...,
        pattern=r"^(daily|weekly|monthly|quarterly)$",
        description="Recurrence: daily, weekly, monthly, or quarterly",
    )
    next_run: datetime = Field(
        ...,
        description="Next scheduled run timestamp (must be in the future)",
    )
    recipient_email: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Email address to send the report to",
    )
    format: str = Field(
        "json",
        description="Output format: json, csv, html, or pdf",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ReportTemplateResponse(BaseModel):
    """Schema for report template responses."""

    id: uuid.UUID
    name: str
    display_name: str
    description: Optional[str] = None
    category: str
    parameters_schema: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportTemplateListResponse(BaseModel):
    """Wrapper for listing report templates."""

    templates: list[ReportTemplateResponse]
    total: int


class ScheduledReportResponse(BaseModel):
    """Schema for scheduled report responses."""

    id: uuid.UUID
    template_id: uuid.UUID
    schedule: str
    next_run: datetime
    recipient_email: Optional[str] = None
    format: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ScheduledReportListResponse(BaseModel):
    """Wrapper for listing scheduled reports."""

    schedules: list[ScheduledReportResponse]
    total: int


# ---------------------------------------------------------------------------
# Report output schemas
# ---------------------------------------------------------------------------

# --- P&L ---


class PnLAccountLine(BaseModel):
    """A single account line in a P&L report."""

    account_id: uuid.UUID
    account_code: str
    account_name: str
    amount: int = Field(description="Amount in pence for the period")
    previous_amount: Optional[int] = Field(
        default=None,
        description="Amount in pence for the comparison period",
    )


class PnLSection(BaseModel):
    """A section within the P&L report."""

    section_name: str = Field(description="Section label (e.g. Revenue, Direct Costs, Expenses)")
    accounts: list[PnLAccountLine] = Field(default_factory=list)
    subtotal: int = Field(description="Subtotal for this section in pence")
    previous_subtotal: Optional[int] = Field(default=None)


class ProfitAndLossReport(BaseModel):
    """Full Profit & Loss (Income Statement) report."""

    report_type: str = Field("profit_and_loss")
    start_date: date
    end_date: date
    comparison: bool = False
    revenue: PnLSection
    direct_costs: PnLSection
    gross_profit: int = Field(description="Revenue - Direct Costs in pence")
    previous_gross_profit: Optional[int] = None
    expenses: PnLSection
    net_profit: int = Field(description="Gross Profit - Expenses in pence")
    previous_net_profit: Optional[int] = None
    generated_at: datetime


# --- Balance Sheet ---


class BSAccountLine(BaseModel):
    """A single account line in a Balance Sheet report."""

    account_id: uuid.UUID
    account_code: str
    account_name: str
    amount: int = Field(description="Amount in pence")


class BSSection(BaseModel):
    """A section within the Balance Sheet report."""

    section_name: str = Field(description="Section label (e.g. Current Assets, Fixed Assets)")
    accounts: list[BSAccountLine] = Field(default_factory=list)
    subtotal: int = Field(description="Subtotal for this section in pence")


class BalanceSheetReport(BaseModel):
    """Full Balance Sheet (Statement of Financial Position) report."""

    report_type: str = Field("balance_sheet")
    as_of_date: date
    current_assets: BSSection
    fixed_assets: BSSection
    total_assets: int = Field(description="Current Assets + Fixed Assets in pence")
    current_liabilities: BSSection
    long_term_liabilities: BSSection
    total_liabilities: int = Field(description="Current Liabilities + Long-term Liabilities in pence")
    equity: BSSection
    total_equity: int = Field(description="Total Equity in pence")
    total_liabilities_and_equity: int = Field(
        description="Total Liabilities + Total Equity. Must equal Total Assets.",
    )
    balanced: bool = Field(description="True if Total Assets == Total Liabilities + Equity")
    generated_at: datetime


# --- Trial Balance ---


class TrialBalanceLine(BaseModel):
    """A single line in a Trial Balance report."""

    account_id: uuid.UUID
    account_code: str
    account_name: str
    category: str
    debit_amount: int = Field(description="Total debits in pence")
    credit_amount: int = Field(description="Total credits in pence")
    net_amount: int = Field(description="Net amount (debit - credit) in pence")


class TrialBalanceReport(BaseModel):
    """Full Trial Balance report — validates that total debits equal total credits."""

    report_type: str = Field("trial_balance")
    start_date: date
    end_date: date
    accounts: list[TrialBalanceLine]
    total_debits: int = Field(description="Sum of all debit amounts in pence")
    total_credits: int = Field(description="Sum of all credit amounts in pence")
    difference: int = Field(description="Total Debits - Total Credits. Must be 0.", default=0)
    balanced: bool = Field(description="True if difference is 0")
    generated_at: datetime


# --- Aged AR ---


class AgingBucket(BaseModel):
    """An aging bucket with total and line items."""

    bucket: str = Field(description="Bucket label (e.g. 0-30, 31-60, 61-90, 90+)")
    count: int = Field(description="Number of items in this bucket")
    total: int = Field(description="Total amount in pence for this bucket")


class AgedARLine(BaseModel):
    """A single outstanding invoice line in the Aged AR report."""

    invoice_id: uuid.UUID
    invoice_reference: Optional[str] = None
    contact_name: str
    due_date: date
    days_overdue: int = Field(description="Number of days past due")
    bucket: str = Field(description="Aging bucket: 0-30|31-60|61-90|90+")
    outstanding: int = Field(description="Outstanding amount in pence")


class AgedARReport(BaseModel):
    """Aged Accounts Receivable report."""

    report_type: str = Field("aged_ar")
    as_of_date: date
    lines: list[AgedARLine]
    buckets: list[AgingBucket] = Field(
        description="Summary by aging bucket: 0-30, 31-60, 61-90, 90+"
    )
    total_outstanding: int = Field(description="Total outstanding AR in pence")
    generated_at: datetime


# --- Aged AP ---


class AgedAPLine(BaseModel):
    """A single outstanding bill in the Aged AP report."""

    transaction_id: uuid.UUID
    transaction_reference: Optional[str] = None
    account_name: str
    effective_date: date
    days_overdue: int = Field(description="Number of days past due")
    bucket: str = Field(description="Aging bucket: 0-30|31-60|61-90|90+")
    outstanding: int = Field(description="Outstanding amount in pence")


class AgedAPReport(BaseModel):
    """Aged Accounts Payable report."""

    report_type: str = Field("aged_ap")
    as_of_date: date
    lines: list[AgedAPLine]
    buckets: list[AgingBucket] = Field(
        description="Summary by aging bucket: 0-30, 31-60, 61-90, 90+"
    )
    total_outstanding: int = Field(description="Total outstanding AP in pence")
    generated_at: datetime


# ---------------------------------------------------------------------------
# Union response for run endpoint
# ---------------------------------------------------------------------------


class ReportRunResponse(BaseModel):
    """Wrapper for any report run result."""

    report_type: str
    report: Any = Field(description="The report data (P&L, BS, TB, Aged AR, or Aged AP)")
    format: str = Field(default="json")
