"""Business logic for Core Financial Reports — ReportService — Module 8.

Implements a 5-stage report engine:
  1. Validate parameters (period, format, comparison)
  2. Query transactions/postings for the date range
  3. Group by account category, compute totals, period comparison
  4. Apply accounting rules (subtotals, P&L structure, BS equation)
  5. Format output (JSON dict with sections)

Reports:
  - run_pl: Profit & Loss (Revenue - Direct Costs = Gross Profit - Expenses = Net Profit)
  - run_bs: Balance Sheet (Current Assets + Fixed Assets = Current Liab + LT Liab + Equity)
  - run_tb: Trial Balance (total debits == total credits)
  - run_ar_aging: Aged AR by 30-60-90-90+ buckets from unpaid invoices
  - run_ap_aging: Aged AP by 30-60-90-90+ buckets from unpaid expense transactions
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.account import Account
from src.models.invoice import Invoice
from src.models.report import ReportTemplate, ScheduledReport
from src.models.transaction import Posting, Transaction
from src.validators.report import (
    AgedAPLine,
    AgedAPReport,
    AgedARLine,
    AgedARReport,
    AgingBucket,
    BSAccountLine,
    BalanceSheetReport,
    BSSection,
    PnLAccountLine,
    PnLSection,
    ProfitAndLossReport,
    ReportRunRequest,
    ReportRunResponse,
    ReportTemplateListResponse,
    ReportTemplateResponse,
    ScheduleReportCreate,
    ScheduledReportListResponse,
    ScheduledReportResponse,
    TrialBalanceLine,
    TrialBalanceReport,
)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class ReportServiceError(Exception):
    """Base exception for report service errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ReportTemplateNotFoundError(ReportServiceError):
    """Report template not found."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Report template '{name}' not found", status_code=404)


class ScheduledReportNotFoundError(ReportServiceError):
    """Scheduled report not found."""

    def __init__(self, schedule_id: uuid.UUID) -> None:
        super().__init__(f"Scheduled report '{schedule_id}' not found", status_code=404)


class InvalidReportParameterError(ReportServiceError):
    """Invalid parameter for a report."""

    def __init__(self, detail: str) -> None:
        super().__init__(f"Invalid report parameter: {detail}", status_code=422)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _template_to_response(tmpl: ReportTemplate) -> ReportTemplateResponse:
    """Map an ORM ReportTemplate to a ReportTemplateResponse."""
    return ReportTemplateResponse.model_validate(tmpl)


def _schedule_to_response(sched: ScheduledReport) -> ScheduledReportResponse:
    """Map an ORM ScheduledReport to a ScheduledReportResponse."""
    return ScheduledReportResponse.model_validate(sched)


def _now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# ReportService
# ---------------------------------------------------------------------------


class ReportService:
    """Stateless 5-stage report engine for core financial reports.

    STAGE 1: Validate parameters (period, format, comparison)
    STAGE 2: Query transactions/postings for the date range
    STAGE 3: Group by account category, compute totals, period comparison
    STAGE 4: Apply accounting rules (subtotals, P&L structure, BS equation)
    STAGE 5: Format output (JSON dict with sections)
    """

    # ------------------------------------------------------------------
    # Stage 1: Validate parameters
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_params(
        data: ReportRunRequest,
    ) -> None:
        """Validate report run parameters.

        Raises:
            InvalidReportParameterError if any parameter is invalid.
        """
        if data.start_date > data.end_date:
            raise InvalidReportParameterError(
                "start_date must be before or equal to end_date"
            )

        valid_templates = {
            "profit_and_loss",
            "balance_sheet",
            "trial_balance",
            "aged_ar",
            "aged_ap",
        }
        if data.template_name not in valid_templates:
            raise InvalidReportParameterError(
                f"Unknown template: {data.template_name}. "
                f"Must be one of: {', '.join(sorted(valid_templates))}"
            )

        valid_formats = {"json", "csv", "html", "pdf"}
        if data.format not in valid_formats:
            raise InvalidReportParameterError(
                f"Unknown format: {data.format}. Must be one of: {', '.join(sorted(valid_formats))}"
            )

    # ------------------------------------------------------------------
    # Stage 2: Query transactions/postings for the date range
    # ------------------------------------------------------------------

    @staticmethod
    async def _query_transactions(
        db: AsyncSession,
        start_date: date,
        end_date: date,
    ) -> list[Transaction]:
        """Fetch all posted transactions with postings, accounts, and VAT lines
        within the given date range.
        """
        stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.postings)
                .selectinload(Posting.account),
                selectinload(Transaction.postings)
                .selectinload(Posting.vat_lines),
            )
            .where(
                Transaction.status == "posted",
                Transaction.effective_date >= start_date,
                Transaction.effective_date <= end_date,
            )
            .order_by(Transaction.effective_date)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def _query_transactions_for_balance(
        db: AsyncSession,
        as_of_date: date,
    ) -> list[Transaction]:
        """Fetch all posted transactions up to the given date for balance sheet."""
        stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.postings)
                .selectinload(Posting.account),
            )
            .where(
                Transaction.status == "posted",
                Transaction.effective_date <= as_of_date,
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Stage 3 & 4: Group by category + apply accounting rules
    # ------------------------------------------------------------------

    @staticmethod
    def _group_postings_by_category(
        transactions: list[Transaction],
    ) -> dict[str, list[Posting]]:
        """Group all postings by their account category."""
        groups: dict[str, list[Posting]] = {}
        for txn in transactions:
            for posting in txn.postings:
                if posting.account is None:
                    continue
                cat = posting.account.category
                groups.setdefault(cat, []).append(posting)
        return groups

    @staticmethod
    def _group_postings_by_account(
        transactions: list[Transaction],
    ) -> dict[uuid.UUID, dict[str, Any]]:
        """Group postings by account_id, returning debit/credit sums."""
        accounts: dict[uuid.UUID, dict[str, Any]] = {}
        for txn in transactions:
            for posting in txn.postings:
                if posting.account is None:
                    continue
                aid = posting.account_id
                if aid not in accounts:
                    accounts[aid] = {
                        "account": posting.account,
                        "debit_total": 0,
                        "credit_total": 0,
                    }
                accounts[aid]["debit_total"] += posting.debit_amount
                accounts[aid]["credit_total"] += posting.credit_amount
        return accounts

    @staticmethod
    def _group_filtered_postings_by_account(
        postings: list[Posting],
    ) -> dict[uuid.UUID, dict[str, Any]]:
        """Group a list of postings by account_id, returning debit/credit sums."""
        accounts: dict[uuid.UUID, dict[str, Any]] = {}
        for p in postings:
            if p.account is None:
                continue
            aid = p.account_id
            if aid not in accounts:
                accounts[aid] = {
                    "account": p.account,
                    "debit_total": 0,
                    "credit_total": 0,
                }
            accounts[aid]["debit_total"] += p.debit_amount
            accounts[aid]["credit_total"] += p.credit_amount
        return accounts

    # ------------------------------------------------------------------
    # run_pl — Profit & Loss
    # ------------------------------------------------------------------

    @staticmethod
    async def run_pl(
        db: AsyncSession,
        data: ReportRunRequest,
    ) -> ProfitAndLossReport:
        """Generate a Profit & Loss (Income Statement) report.

        Structure:
          Revenue - Direct Costs = Gross Profit
          Gross Profit - Expenses = Net Profit
        """
        # Stage 1: validate
        ReportService._validate_params(data)

        # Stage 2: query
        transactions = await ReportService._query_transactions(
            db, data.start_date, data.end_date
        )

        # Previous period for comparison
        prev_transactions: list[Transaction] = []
        if data.comparison:
            delta = data.end_date - data.start_date
            prev_start = data.start_date - delta - timedelta(days=1)
            prev_end = data.start_date - timedelta(days=1)
            prev_transactions = await ReportService._query_transactions(
                db, prev_start, prev_end
            )

        # Stage 3: group by category
        groups = ReportService._group_postings_by_category(transactions)
        prev_groups = ReportService._group_postings_by_category(prev_transactions)

        # Revenue section — only Revenue category accounts
        revenue_postings = groups.get("Revenue", [])
        revenue_accounts = ReportService._group_filtered_postings_by_account(revenue_postings)
        prev_revenue_accounts = (
            ReportService._group_filtered_postings_by_account(prev_groups.get("Revenue", []))
            if prev_transactions else {}
        )

        revenue_lines: list[PnLAccountLine] = []
        for aid, info in sorted(revenue_accounts.items(), key=lambda x: x[1]["account"].code):
            amt = info["credit_total"] - info["debit_total"]
            prev_amt = None
            if aid in prev_revenue_accounts:
                pi = prev_revenue_accounts[aid]
                prev_amt = pi["credit_total"] - pi["debit_total"]
            revenue_lines.append(PnLAccountLine(
                account_id=aid,
                account_code=info["account"].code,
                account_name=info["account"].name,
                amount=amt,
                previous_amount=prev_amt,
            ))
        revenue_total = sum(l.amount for l in revenue_lines)
        prev_revenue_total = sum(l.previous_amount for l in revenue_lines if l.previous_amount is not None) if data.comparison else None

        revenue_section = PnLSection(
            section_name="Revenue",
            accounts=revenue_lines,
            subtotal=revenue_total,
            previous_subtotal=prev_revenue_total,
        )

        # Direct Costs section (Expense category, DirectCost type only)
        direct_cost_postings = [
            p for p in groups.get("Expense", [])
            if p.account and p.account.type == "DirectCost"
        ]
        dc_accounts = ReportService._group_filtered_postings_by_account(direct_cost_postings)
        prev_dc_accounts = (
            ReportService._group_filtered_postings_by_account([
                p for p in prev_groups.get("Expense", [])
                if p.account and p.account.type == "DirectCost"
            ])
            if prev_transactions else {}
        )

        dc_lines: list[PnLAccountLine] = []
        for aid, info in sorted(dc_accounts.items(), key=lambda x: x[1]["account"].code):
            amt = info["debit_total"] - info["credit_total"]
            prev_amt = None
            if aid in prev_dc_accounts:
                pi = prev_dc_accounts[aid]
                prev_amt = pi["debit_total"] - pi["credit_total"]
            dc_lines.append(PnLAccountLine(
                account_id=aid,
                account_code=info["account"].code,
                account_name=info["account"].name,
                amount=amt,
                previous_amount=prev_amt,
            ))
        dc_total = sum(l.amount for l in dc_lines)
        prev_dc_total = sum(l.previous_amount for l in dc_lines if l.previous_amount is not None) if data.comparison else None

        direct_costs_section = PnLSection(
            section_name="Direct Costs",
            accounts=dc_lines,
            subtotal=dc_total,
            previous_subtotal=prev_dc_total,
        )

        # Stage 4: Gross Profit = Revenue - Direct Costs
        gross_profit = revenue_total - dc_total
        prev_gross_profit = (
            (prev_revenue_total - prev_dc_total)
            if prev_revenue_total is not None and prev_dc_total is not None
            else None
        )

        # Expenses section (Expense category, Expense type — not DirectCost)
        expense_postings = [
            p for p in groups.get("Expense", [])
            if p.account and p.account.type not in ("DirectCost",)
        ]
        exp_accounts = ReportService._group_filtered_postings_by_account(expense_postings)
        prev_exp_accounts = (
            ReportService._group_filtered_postings_by_account([
                p for p in prev_groups.get("Expense", [])
                if p.account and p.account.type not in ("DirectCost",)
            ])
            if prev_transactions else {}
        )

        exp_lines: list[PnLAccountLine] = []
        for aid, info in sorted(exp_accounts.items(), key=lambda x: x[1]["account"].code):
            amt = info["debit_total"] - info["credit_total"]
            prev_amt = None
            if aid in prev_exp_accounts:
                pi = prev_exp_accounts[aid]
                prev_amt = pi["debit_total"] - pi["credit_total"]
            exp_lines.append(PnLAccountLine(
                account_id=aid,
                account_code=info["account"].code,
                account_name=info["account"].name,
                amount=amt,
                previous_amount=prev_amt,
            ))
        exp_total = sum(l.amount for l in exp_lines)
        prev_exp_total = sum(l.previous_amount for l in exp_lines if l.previous_amount is not None) if data.comparison else None

        expenses_section = PnLSection(
            section_name="Expenses",
            accounts=exp_lines,
            subtotal=exp_total,
            previous_subtotal=prev_exp_total,
        )

        # Net Profit = Gross Profit - Expenses
        net_profit = gross_profit - exp_total
        prev_net_profit = (
            (prev_gross_profit - prev_exp_total)
            if prev_gross_profit is not None and prev_exp_total is not None
            else None
        )

        # Stage 5: format output
        return ProfitAndLossReport(
            report_type="profit_and_loss",
            start_date=data.start_date,
            end_date=data.end_date,
            comparison=data.comparison,
            revenue=revenue_section,
            direct_costs=direct_costs_section,
            gross_profit=gross_profit,
            previous_gross_profit=prev_gross_profit,
            expenses=expenses_section,
            net_profit=net_profit,
            previous_net_profit=prev_net_profit,
            generated_at=_now(),
        )

    # ------------------------------------------------------------------
    # run_bs — Balance Sheet
    # ------------------------------------------------------------------

    @staticmethod
    async def run_bs(
        db: AsyncSession,
        data: ReportRunRequest,
    ) -> BalanceSheetReport:
        """Generate a Balance Sheet (Statement of Financial Position).

        Structure:
          Current Assets + Fixed Assets = Total Assets
          Current Liabilities + Long-term Liabilities + Equity = Total L+E
          Must balance: Total Assets == Total Liabilities + Equity
        """
        # Stage 1: validate
        ReportService._validate_params(data)

        # Use end_date as the as_of_date for balance sheet
        as_of_date = data.end_date

        # Stage 2: query all transactions up to as_of_date
        transactions = await ReportService._query_transactions_for_balance(
            db, as_of_date
        )

        # Stage 3: group by account
        accounts = ReportService._group_postings_by_account(transactions)

        # For balance sheet:
        # Assets: normal debit balance (debit - credit)
        # Liabilities: normal credit balance (credit - debit)
        # Equity: normal credit balance (credit - debit)

        def _net_balance(info: dict[str, Any], is_asset: bool) -> int:
            """Compute balance based on normal balance side."""
            if is_asset:
                return info["debit_total"] - info["credit_total"]
            else:
                return info["credit_total"] - info["debit_total"]

        # Current Assets: Asset category with type Bank or CurrentAsset
        ca_accounts = {
            aid: info for aid, info in accounts.items()
            if info["account"].category == "Asset"
            and info["account"].type in ("Bank", "CurrentAsset")
        }
        ca_lines: list[BSAccountLine] = []
        for aid, info in sorted(ca_accounts.items(), key=lambda x: x[1]["account"].code):
            ca_lines.append(BSAccountLine(
                account_id=aid,
                account_code=info["account"].code,
                account_name=info["account"].name,
                amount=_net_balance(info, is_asset=True),
            ))
        ca_total = sum(l.amount for l in ca_lines)

        current_assets = BSSection(
            section_name="Current Assets",
            accounts=ca_lines,
            subtotal=ca_total,
        )

        # Fixed Assets: Asset category with type FixedAsset
        fa_accounts = {
            aid: info for aid, info in accounts.items()
            if info["account"].category == "Asset"
            and info["account"].type == "FixedAsset"
        }
        fa_lines: list[BSAccountLine] = []
        for aid, info in sorted(fa_accounts.items(), key=lambda x: x[1]["account"].code):
            fa_lines.append(BSAccountLine(
                account_id=aid,
                account_code=info["account"].code,
                account_name=info["account"].name,
                amount=_net_balance(info, is_asset=True),
            ))
        fa_total = sum(l.amount for l in fa_lines)

        fixed_assets = BSSection(
            section_name="Fixed Assets",
            accounts=fa_lines,
            subtotal=fa_total,
        )

        # Stage 4: Total Assets
        total_assets = ca_total + fa_total

        # Current Liabilities
        cl_accounts = {
            aid: info for aid, info in accounts.items()
            if info["account"].category == "Liability"
            and info["account"].type == "CurrentLiability"
        }
        cl_lines: list[BSAccountLine] = []
        for aid, info in sorted(cl_accounts.items(), key=lambda x: x[1]["account"].code):
            cl_lines.append(BSAccountLine(
                account_id=aid,
                account_code=info["account"].code,
                account_name=info["account"].name,
                amount=_net_balance(info, is_asset=False),
            ))
        cl_total = sum(l.amount for l in cl_lines)

        current_liabilities = BSSection(
            section_name="Current Liabilities",
            accounts=cl_lines,
            subtotal=cl_total,
        )

        # Long-term Liabilities
        ll_accounts = {
            aid: info for aid, info in accounts.items()
            if info["account"].category == "Liability"
            and info["account"].type == "LongTermLiability"
        }
        ll_lines: list[BSAccountLine] = []
        for aid, info in sorted(ll_accounts.items(), key=lambda x: x[1]["account"].code):
            ll_lines.append(BSAccountLine(
                account_id=aid,
                account_code=info["account"].code,
                account_name=info["account"].name,
                amount=_net_balance(info, is_asset=False),
            ))
        ll_total = sum(l.amount for l in ll_lines)

        long_term_liabilities = BSSection(
            section_name="Long-term Liabilities",
            accounts=ll_lines,
            subtotal=ll_total,
        )

        total_liabilities = cl_total + ll_total

        # Equity
        eq_accounts = {
            aid: info for aid, info in accounts.items()
            if info["account"].category == "Equity"
        }
        eq_lines: list[BSAccountLine] = []
        for aid, info in sorted(eq_accounts.items(), key=lambda x: x[1]["account"].code):
            eq_lines.append(BSAccountLine(
                account_id=aid,
                account_code=info["account"].code,
                account_name=info["account"].name,
                amount=_net_balance(info, is_asset=False),
            ))
        eq_total = sum(l.amount for l in eq_lines)

        equity = BSSection(
            section_name="Equity",
            accounts=eq_lines,
            subtotal=eq_total,
        )

        total_liabilities_and_equity = total_liabilities + eq_total
        balanced = total_assets == total_liabilities_and_equity

        # Stage 5: format output
        return BalanceSheetReport(
            report_type="balance_sheet",
            as_of_date=as_of_date,
            current_assets=current_assets,
            fixed_assets=fixed_assets,
            total_assets=total_assets,
            current_liabilities=current_liabilities,
            long_term_liabilities=long_term_liabilities,
            total_liabilities=total_liabilities,
            equity=equity,
            total_equity=eq_total,
            total_liabilities_and_equity=total_liabilities_and_equity,
            balanced=balanced,
            generated_at=_now(),
        )

    # ------------------------------------------------------------------
    # run_tb — Trial Balance
    # ------------------------------------------------------------------

    @staticmethod
    async def run_tb(
        db: AsyncSession,
        data: ReportRunRequest,
    ) -> TrialBalanceReport:
        """Generate a Trial Balance report.

        Lists every account with debit/credit totals and verifies
        total debits == total credits.
        """
        # Stage 1: validate
        ReportService._validate_params(data)

        # Stage 2: query
        transactions = await ReportService._query_transactions(
            db, data.start_date, data.end_date
        )

        # Stage 3: group by account
        accounts = ReportService._group_postings_by_account(transactions)

        # Stage 3 continued: build lines
        tb_lines: list[TrialBalanceLine] = []
        total_debits = 0
        total_credits = 0

        for aid, info in sorted(accounts.items(), key=lambda x: x[1]["account"].code):
            dr = info["debit_total"]
            cr = info["credit_total"]
            net = dr - cr
            total_debits += dr
            total_credits += cr
            tb_lines.append(TrialBalanceLine(
                account_id=aid,
                account_code=info["account"].code,
                account_name=info["account"].name,
                category=info["account"].category,
                debit_amount=dr,
                credit_amount=cr,
                net_amount=net,
            ))

        # Stage 4: verify balance
        difference = total_debits - total_credits
        balanced = difference == 0

        # Stage 5: format output
        return TrialBalanceReport(
            report_type="trial_balance",
            start_date=data.start_date,
            end_date=data.end_date,
            accounts=tb_lines,
            total_debits=total_debits,
            total_credits=total_credits,
            difference=difference,
            balanced=balanced,
            generated_at=_now(),
        )

    # ------------------------------------------------------------------
    # run_ar_aging — Aged Accounts Receivable
    # ------------------------------------------------------------------

    @staticmethod
    async def run_ar_aging(
        db: AsyncSession,
        data: ReportRunRequest,
    ) -> AgedARReport:
        """Generate an Aged Accounts Receivable report from unpaid invoices.

        Buckets: 0-30, 31-60, 61-90, 90+ days past due.
        """
        # Stage 1: validate
        ReportService._validate_params(data)

        as_of_date = data.end_date

        # Stage 2: query unpaid invoices
        stmt = (
            select(Invoice)
            .options(selectinload(Invoice.contact))
            .where(
                Invoice.status.notin_(["paid", "cancelled", "draft"]),
                Invoice.due_date <= as_of_date,
            )
            .order_by(Invoice.due_date)
        )
        result = await db.execute(stmt)
        invoices = list(result.scalars().all())

        # Stage 3: group by age bucket
        lines: list[AgedARLine] = []
        buckets_data: dict[str, dict[str, Any]] = {
            "0-30": {"count": 0, "total": 0},
            "31-60": {"count": 0, "total": 0},
            "61-90": {"count": 0, "total": 0},
            "90+": {"count": 0, "total": 0},
        }
        total_outstanding = 0

        for inv in invoices:
            days_overdue = (as_of_date - inv.due_date).days
            if days_overdue <= 30:
                bucket = "0-30"
            elif days_overdue <= 60:
                bucket = "31-60"
            elif days_overdue <= 90:
                bucket = "61-90"
            else:
                bucket = "90+"

            outstanding = inv.total
            # Subtract credit notes
            for cn in inv.credit_notes:
                outstanding += cn.total  # Credit note totals are negative

            if outstanding <= 0:
                continue

            contact_name = inv.contact.name if inv.contact else "Unknown"
            lines.append(AgedARLine(
                invoice_id=inv.id,
                invoice_reference=inv.reference,
                contact_name=contact_name,
                due_date=inv.due_date,
                days_overdue=days_overdue,
                bucket=bucket,
                outstanding=outstanding,
            ))
            buckets_data[bucket]["count"] += 1
            buckets_data[bucket]["total"] += outstanding
            total_outstanding += outstanding

        # Stage 4: buckets summary
        buckets = [
            AgingBucket(bucket=k, count=v["count"], total=v["total"])
            for k, v in buckets_data.items()
        ]

        # Stage 5: format output
        return AgedARReport(
            report_type="aged_ar",
            as_of_date=as_of_date,
            lines=lines,
            buckets=buckets,
            total_outstanding=total_outstanding,
            generated_at=_now(),
        )

    # ------------------------------------------------------------------
    # run_ap_aging — Aged Accounts Payable
    # ------------------------------------------------------------------

    @staticmethod
    async def run_ap_aging(
        db: AsyncSession,
        data: ReportRunRequest,
    ) -> AgedAPReport:
        """Generate an Aged Accounts Payable report from unpaid expense transactions.

        Since there is no dedicated AP/bills table, this report identifies
        unpaid bills by looking at transactions with postings to Expense
        or DirectCost accounts that have not been matched to payments.

        Buckets: 0-30, 31-60, 61-90, 90+ days past due.
        """
        # Stage 1: validate
        ReportService._validate_params(data)

        as_of_date = data.end_date

        # Stage 2: query all posted transactions with Expense/DirectCost postings
        stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.postings)
                .selectinload(Posting.account),
            )
            .where(
                Transaction.status == "posted",
                Transaction.effective_date <= as_of_date,
            )
            .order_by(Transaction.effective_date)
        )
        result = await db.execute(stmt)
        transactions = list(result.scalars().all())

        # Stage 3: identify expense postings and group by age
        lines: list[AgedAPLine] = []
        buckets_data: dict[str, dict[str, Any]] = {
            "0-30": {"count": 0, "total": 0},
            "31-60": {"count": 0, "total": 0},
            "61-90": {"count": 0, "total": 0},
            "90+": {"count": 0, "total": 0},
        }
        total_outstanding = 0

        for txn in transactions:
            for posting in txn.postings:
                if posting.account is None:
                    continue
                cat = posting.account.category
                if cat != "Expense":
                    continue
                # Outstanding amount = debit (purchase) - credit (payment/offset)
                outstanding = posting.debit_amount - posting.credit_amount
                if outstanding <= 0:
                    continue

                effective_date = txn.effective_date or txn.created_at.date()
                if effective_date > as_of_date:
                    continue

                days_overdue = (as_of_date - effective_date).days
                if days_overdue <= 30:
                    bucket = "0-30"
                elif days_overdue <= 60:
                    bucket = "31-60"
                elif days_overdue <= 90:
                    bucket = "61-90"
                else:
                    bucket = "90+"

                lines.append(AgedAPLine(
                    transaction_id=txn.id,
                    transaction_reference=txn.reference,
                    account_name=posting.account.name,
                    effective_date=effective_date,
                    days_overdue=days_overdue,
                    bucket=bucket,
                    outstanding=outstanding,
                ))
                buckets_data[bucket]["count"] += 1
                buckets_data[bucket]["total"] += outstanding
                total_outstanding += outstanding

        # Stage 4: buckets summary
        buckets = [
            AgingBucket(bucket=k, count=v["count"], total=v["total"])
            for k, v in buckets_data.items()
        ]

        # Stage 5: format output
        return AgedAPReport(
            report_type="aged_ap",
            as_of_date=as_of_date,
            lines=lines,
            buckets=buckets,
            total_outstanding=total_outstanding,
            generated_at=_now(),
        )

    # ------------------------------------------------------------------
    # run — main entry point, dispatches to specific report type
    # ------------------------------------------------------------------

    @staticmethod
    async def run(
        db: AsyncSession,
        data: ReportRunRequest,
    ) -> ReportRunResponse:
        """Run any report by template_name.

        Dispatches to the appropriate sub-method based on template_name.
        """
        # Stage 1: validate
        ReportService._validate_params(data)

        template_name = data.template_name

        if template_name == "profit_and_loss":
            report = await ReportService.run_pl(db, data)
        elif template_name == "balance_sheet":
            report = await ReportService.run_bs(db, data)
        elif template_name == "trial_balance":
            report = await ReportService.run_tb(db, data)
        elif template_name == "aged_ar":
            report = await ReportService.run_ar_aging(db, data)
        elif template_name == "aged_ap":
            report = await ReportService.run_ap_aging(db, data)
        else:
            raise ReportTemplateNotFoundError(template_name)

        return ReportRunResponse(
            report_type=template_name,
            report=report.model_dump(),
            format=data.format,
        )

    # ------------------------------------------------------------------
    # Templates management
    # ------------------------------------------------------------------

    @staticmethod
    async def list_templates(
        db: AsyncSession,
        *,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ReportTemplateResponse], int]:
        """List report templates with optional category filter."""
        stmt = select(ReportTemplate)

        if category:
            stmt = stmt.where(ReportTemplate.category == category)

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # Fetch
        stmt = stmt.order_by(ReportTemplate.name).offset(offset).limit(limit)
        result = await db.execute(stmt)
        templates = list(result.scalars().all())

        return [_template_to_response(t) for t in templates], total

    @staticmethod
    async def get_template(
        db: AsyncSession,
        template_id: uuid.UUID,
    ) -> Optional[ReportTemplateResponse]:
        """Get a single report template by ID."""
        tmpl = await db.get(ReportTemplate, template_id)
        if tmpl is None:
            return None
        return _template_to_response(tmpl)

    # ------------------------------------------------------------------
    # Scheduled reports management
    # ------------------------------------------------------------------

    @staticmethod
    async def create_schedule(
        db: AsyncSession,
        data: ScheduleReportCreate,
    ) -> ScheduledReportResponse:
        """Create a new scheduled report."""
        # Verify template exists
        tmpl = await db.get(ReportTemplate, data.template_id)
        if tmpl is None:
            raise InvalidReportParameterError(
                f"Template with id '{data.template_id}' not found"
            )

        schedule = ScheduledReport(
            template_id=data.template_id,
            schedule=data.schedule,
            next_run=data.next_run,
            recipient_email=data.recipient_email,
            format=data.format,
        )
        db.add(schedule)
        await db.commit()
        await db.refresh(schedule)
        return _schedule_to_response(schedule)

    @staticmethod
    async def list_schedules(
        db: AsyncSession,
        *,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ScheduledReportResponse], int]:
        """List scheduled reports with optional active filter."""
        stmt = select(ScheduledReport)

        if is_active is not None:
            stmt = stmt.where(ScheduledReport.is_active == is_active)

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # Fetch
        stmt = stmt.order_by(ScheduledReport.next_run).offset(offset).limit(limit)
        result = await db.execute(stmt)
        schedules = list(result.scalars().all())

        return [_schedule_to_response(s) for s in schedules], total

    @staticmethod
    async def get_schedule(
        db: AsyncSession,
        schedule_id: uuid.UUID,
    ) -> Optional[ScheduledReportResponse]:
        """Get a single scheduled report by ID."""
        sched = await db.get(ScheduledReport, schedule_id)
        if sched is None:
            return None
        return _schedule_to_response(sched)

    @staticmethod
    async def delete_schedule(
        db: AsyncSession,
        schedule_id: uuid.UUID,
    ) -> bool:
        """Delete a scheduled report. Returns True if deleted, False if not found."""
        sched = await db.get(ScheduledReport, schedule_id)
        if sched is None:
            return False
        await db.delete(sched)
        await db.commit()
        return True
