"""Unit tests for ReportService with mocked DB session."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.account import Account
from src.models.invoice import Invoice
from src.models.transaction import Posting, Transaction
from src.services.report_service import (
    InvalidReportParameterError,
    ReportService,
    ReportTemplateNotFoundError,
)
from src.validators.report import ReportRunRequest, ScheduleReportCreate

NOW = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)
TODAY = date(2026, 6, 27)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_result(return_value, scalar_one_value=None):
    """Create a MagicMock that mimics an AsyncResult."""
    m = MagicMock()
    m.scalar_one_or_none.return_value = return_value
    m.scalars.return_value.all.return_value = (
        return_value if isinstance(return_value, list) else [return_value]
    )
    if scalar_one_value is not None:
        m.scalar_one.return_value = scalar_one_value
    elif return_value is None:
        m.scalar_one.return_value = 0
    elif isinstance(return_value, list):
        m.scalar_one.return_value = len(return_value)
    else:
        m.scalar_one.return_value = 1
    return m


def _make_refresh():
    """Return an async refresh mock that populates server defaults."""

    async def mock_refresh(obj: object) -> None:
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid.uuid4()
        if hasattr(obj, "created_at") and obj.created_at is None:
            obj.created_at = NOW

    return mock_refresh


def _make_account(**overrides) -> Account:
    """Create an Account ORM instance."""
    defaults = {
        "id": uuid.uuid4(),
        "code": "4000",
        "name": "Sales Revenue",
        "category": "Revenue",
        "type": "Revenue",
        "parent_id": None,
        "vat_rate": "20%",
        "is_active": True,
    }
    defaults.update(overrides)
    return Account(**defaults)


def _make_transaction(
    txn_id: uuid.UUID,
    postings: list[Posting],
    effective_date: date = TODAY,
) -> Transaction:
    """Create a Transaction ORM instance."""
    txn = Transaction(
        id=txn_id,
        reference=f"JE-2026-{str(txn_id)[:4]}",
        description="Test transaction",
        status="posted",
        effective_date=effective_date,
        created_at=NOW,
        updated_at=NOW,
    )
    for p in postings:
        p.transaction_id = txn_id
        txn.postings.append(p)
    return txn


def _make_posting(
    posting_id: uuid.UUID,
    account: Account,
    debit: int = 0,
    credit: int = 0,
) -> Posting:
    """Create a Posting ORM instance."""
    p = Posting(
        id=posting_id,
        account_id=account.id,
        debit_amount=debit,
        credit_amount=credit,
        created_at=NOW,
    )
    p.account = account
    return p


# ---------------------------------------------------------------------------
# Stage 1: Parameter Validation
# ---------------------------------------------------------------------------


class TestValidateParams:
    """Tests for parameter validation (Stage 1)."""

    def test_valid_params(self):
        """Should accept valid parameters."""
        data = ReportRunRequest(
            template_name="profit_and_loss",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )
        # Should not raise
        ReportService._validate_params(data)

    def test_start_after_end_raises(self):
        """Should raise if start > end."""
        data = ReportRunRequest(
            template_name="profit_and_loss",
            start_date=date(2026, 6, 30),
            end_date=date(2026, 1, 1),
        )
        with pytest.raises(InvalidReportParameterError, match="start_date must be before"):
            ReportService._validate_params(data)

    def test_unknown_template_raises(self):
        """Should raise for unknown template name."""
        data = ReportRunRequest(
            template_name="unknown_report",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )
        with pytest.raises(InvalidReportParameterError, match="Unknown template"):
            ReportService._validate_params(data)

    def test_unknown_format_raises(self):
        """Should raise for unknown format."""
        data = ReportRunRequest(
            template_name="profit_and_loss",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
            format="xml",
        )
        with pytest.raises(InvalidReportParameterError, match="Unknown format"):
            ReportService._validate_params(data)

    def test_all_templates_accepted(self):
        """All valid templates should be accepted."""
        valid = [
            "profit_and_loss",
            "balance_sheet",
            "trial_balance",
            "aged_ar",
            "aged_ap",
        ]
        for name in valid:
            data = ReportRunRequest(
                template_name=name,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 6, 30),
            )
            ReportService._validate_params(data)  # Should not raise


# ---------------------------------------------------------------------------
# Profit & Loss Tests
# ---------------------------------------------------------------------------


class TestRunPL:
    """Tests for run_pl — Profit & Loss report."""

    @pytest.mark.asyncio
    async def test_empty_period_returns_zeroes(self):
        """Empty period should return zero sections."""
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_mock_result([]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="profit_and_loss",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )

        result = await ReportService.run_pl(db, data)

        assert result.report_type == "profit_and_loss"
        assert result.revenue.subtotal == 0
        assert result.direct_costs.subtotal == 0
        assert result.gross_profit == 0
        assert result.expenses.subtotal == 0
        assert result.net_profit == 0

    @pytest.mark.asyncio
    async def test_revenue_minus_direct_costs_equals_gross_profit(self):
        """Revenue - Direct Costs = Gross Profit."""
        db = AsyncMock()

        rev_account = _make_account(
            id=uuid.uuid4(),
            code="4000",
            name="Sales Revenue",
            category="Revenue",
            type="Revenue",
        )
        dc_account = _make_account(
            id=uuid.uuid4(),
            code="5000",
            name="Cost of Sales",
            category="Expense",
            type="DirectCost",
        )

        # £10,000 revenue (credit)
        rev_posting = _make_posting(uuid.uuid4(), rev_account, debit=0, credit=10_000_00)
        txn1 = _make_transaction(uuid.uuid4(), [rev_posting])

        # £4,000 direct costs (debit)
        dc_posting = _make_posting(uuid.uuid4(), dc_account, debit=4_000_00, credit=0)
        txn2 = _make_transaction(uuid.uuid4(), [dc_posting])

        db.execute = AsyncMock(return_value=_mock_result([txn1, txn2]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="profit_and_loss",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
            comparison=False,
        )

        result = await ReportService.run_pl(db, data)

        assert result.revenue.subtotal == 10_000_00
        assert result.direct_costs.subtotal == 4_000_00
        assert result.gross_profit == 6_000_00
        assert result.expenses.subtotal == 0
        assert result.net_profit == 6_000_00

    @pytest.mark.asyncio
    async def test_gross_profit_minus_expenses_equals_net_profit(self):
        """Gross Profit - Expenses = Net Profit."""
        db = AsyncMock()

        rev_account = _make_account(
            id=uuid.uuid4(),
            code="4000",
            name="Sales",
            category="Revenue",
            type="Revenue",
        )
        exp_account = _make_account(
            id=uuid.uuid4(),
            code="5210",
            name="Marketing",
            category="Expense",
            type="Expense",
        )

        # £50,000 revenue (credit)
        rev_posting = _make_posting(uuid.uuid4(), rev_account, debit=0, credit=50_000_00)
        txn1 = _make_transaction(uuid.uuid4(), [rev_posting])

        # £15,000 expenses (debit)
        exp_posting = _make_posting(uuid.uuid4(), exp_account, debit=15_000_00, credit=0)
        txn2 = _make_transaction(uuid.uuid4(), [exp_posting])

        db.execute = AsyncMock(return_value=_mock_result([txn1, txn2]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="profit_and_loss",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )

        result = await ReportService.run_pl(db, data)

        assert result.revenue.subtotal == 50_000_00
        assert result.direct_costs.subtotal == 0
        assert result.gross_profit == 50_000_00
        assert result.expenses.subtotal == 15_000_00
        assert result.net_profit == 35_000_00

    @pytest.mark.asyncio
    async def test_full_pl_structure(self):
        """Complete P&L with Revenue, Direct Costs, Expenses."""
        db = AsyncMock()

        rev_account = _make_account(
            id=uuid.uuid4(),
            code="4000",
            name="Sales",
            category="Revenue",
            type="Revenue",
        )
        dc_account = _make_account(
            id=uuid.uuid4(),
            code="5000",
            name="COGS",
            category="Expense",
            type="DirectCost",
        )
        exp_account = _make_account(
            id=uuid.uuid4(),
            code="5210",
            name="Rent",
            category="Expense",
            type="Expense",
        )

        rev_posting = _make_posting(uuid.uuid4(), rev_account, debit=0, credit=100_000_00)
        dc_posting = _make_posting(uuid.uuid4(), dc_account, debit=40_000_00, credit=0)
        exp_posting = _make_posting(uuid.uuid4(), exp_account, debit=20_000_00, credit=0)

        txn = _make_transaction(uuid.uuid4(), [rev_posting, dc_posting, exp_posting])

        db.execute = AsyncMock(return_value=_mock_result([txn]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="profit_and_loss",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )

        result = await ReportService.run_pl(db, data)

        assert result.revenue.subtotal == 100_000_00
        assert len(result.revenue.accounts) == 1
        assert result.revenue.accounts[0].account_name == "Sales"
        assert result.direct_costs.subtotal == 40_000_00
        assert result.gross_profit == 60_000_00
        assert result.expenses.subtotal == 20_000_00
        assert result.net_profit == 40_000_00


# ---------------------------------------------------------------------------
# Balance Sheet Tests
# ---------------------------------------------------------------------------


class TestRunBS:
    """Tests for run_bs — Balance Sheet report."""

    @pytest.mark.asyncio
    async def test_empty_balance_sheet(self):
        """Empty data should return zero balance sheet."""
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_mock_result([]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="balance_sheet",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )

        result = await ReportService.run_bs(db, data)

        assert result.total_assets == 0
        assert result.total_liabilities == 0
        assert result.total_equity == 0
        assert result.balanced is True

    @pytest.mark.asyncio
    async def test_assets_equal_liabilities_plus_equity(self):
        """Assets = Liabilities + Equity must balance."""
        db = AsyncMock()

        bank = _make_account(
            id=uuid.uuid4(),
            code="1000",
            name="Bank",
            category="Asset",
            type="Bank",
        )
        capital = _make_account(
            id=uuid.uuid4(),
            code="3000",
            name="Share Capital",
            category="Equity",
            type="Equity",
        )

        # Debit bank £10,000, Credit equity £10,000
        bank_posting = _make_posting(uuid.uuid4(), bank, debit=10_000_00, credit=0)
        capital_posting = _make_posting(uuid.uuid4(), capital, debit=0, credit=10_000_00)
        txn = _make_transaction(uuid.uuid4(), [bank_posting, capital_posting])

        db.execute = AsyncMock(return_value=_mock_result([txn]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="balance_sheet",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )

        result = await ReportService.run_bs(db, data)

        assert result.total_assets == 10_000_00
        assert result.total_equity == 10_000_00
        assert result.total_liabilities == 0
        assert result.total_liabilities_and_equity == 10_000_00
        assert result.balanced is True

    @pytest.mark.asyncio
    async def test_balance_sheet_sections(self):
        """Balance sheet should have all sections."""
        db = AsyncMock()

        bank = _make_account(
            id=uuid.uuid4(),
            code="1000",
            name="Bank",
            category="Asset",
            type="Bank",
        )
        equipment = _make_account(
            id=uuid.uuid4(),
            code="1500",
            name="Equipment",
            category="Asset",
            type="FixedAsset",
        )
        payables = _make_account(
            id=uuid.uuid4(),
            code="2000",
            name="Trade Payables",
            category="Liability",
            type="CurrentLiability",
        )
        loan = _make_account(
            id=uuid.uuid4(),
            code="2500",
            name="Bank Loan",
            category="Liability",
            type="LongTermLiability",
        )
        capital = _make_account(
            id=uuid.uuid4(),
            code="3000",
            name="Capital",
            category="Equity",
            type="Equity",
        )

        bank_p = _make_posting(uuid.uuid4(), bank, debit=50_000_00, credit=0)
        equip_p = _make_posting(uuid.uuid4(), equipment, debit=20_000_00, credit=0)
        payables_p = _make_posting(uuid.uuid4(), payables, debit=0, credit=10_000_00)
        loan_p = _make_posting(uuid.uuid4(), loan, debit=0, credit=30_000_00)
        capital_p = _make_posting(uuid.uuid4(), capital, debit=0, credit=30_000_00)

        txn = _make_transaction(
            uuid.uuid4(), [bank_p, equip_p, payables_p, loan_p, capital_p]
        )

        db.execute = AsyncMock(return_value=_mock_result([txn]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="balance_sheet",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )

        result = await ReportService.run_bs(db, data)

        assert result.current_assets.subtotal == 50_000_00
        assert result.fixed_assets.subtotal == 20_000_00
        assert result.total_assets == 70_000_00
        assert result.current_liabilities.subtotal == 10_000_00
        assert result.long_term_liabilities.subtotal == 30_000_00
        assert result.total_liabilities == 40_000_00
        assert result.equity.subtotal == 30_000_00
        assert result.total_liabilities_and_equity == 70_000_00
        assert result.balanced is True


# ---------------------------------------------------------------------------
# Trial Balance Tests
# ---------------------------------------------------------------------------


class TestRunTB:
    """Tests for run_tb — Trial Balance report."""

    @pytest.mark.asyncio
    async def test_trial_balance_balanced(self):
        """Trial balance should have equal debits and credits."""
        db = AsyncMock()

        rev = _make_account(
            id=uuid.uuid4(),
            code="4000",
            name="Revenue",
            category="Revenue",
            type="Revenue",
        )
        bank = _make_account(
            id=uuid.uuid4(),
            code="1000",
            name="Bank",
            category="Asset",
            type="Bank",
        )

        bank_p = _make_posting(uuid.uuid4(), bank, debit=50_000_00, credit=0)
        rev_p = _make_posting(uuid.uuid4(), rev, debit=0, credit=50_000_00)
        txn = _make_transaction(uuid.uuid4(), [bank_p, rev_p])

        db.execute = AsyncMock(return_value=_mock_result([txn]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="trial_balance",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )

        result = await ReportService.run_tb(db, data)

        assert result.total_debits == 50_000_00
        assert result.total_credits == 50_000_00
        assert result.difference == 0
        assert result.balanced is True
        assert len(result.accounts) == 2

    @pytest.mark.asyncio
    async def test_trial_balance_imbalanced(self):
        """Unbalanced trial balance should be detected."""
        db = AsyncMock()

        bank = _make_account(
            id=uuid.uuid4(),
            code="1000",
            name="Bank",
            category="Asset",
            type="Bank",
        )
        exp = _make_account(
            id=uuid.uuid4(),
            code="5210",
            name="Expense",
            category="Expense",
            type="Expense",
        )

        # £100 debit, £90 credit → imbalanced
        bank_p = _make_posting(uuid.uuid4(), bank, debit=100_00, credit=0)
        exp_p = _make_posting(uuid.uuid4(), exp, debit=0, credit=90_00)
        txn = _make_transaction(uuid.uuid4(), [bank_p, exp_p])

        db.execute = AsyncMock(return_value=_mock_result([txn]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="trial_balance",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )

        result = await ReportService.run_tb(db, data)

        assert result.total_debits == 100_00
        assert result.total_credits == 90_00
        assert result.difference == 10_00
        assert result.balanced is False


# ---------------------------------------------------------------------------
# Aged AR Tests
# ---------------------------------------------------------------------------


class TestRunAR:
    """Tests for run_ar_aging — Aged Accounts Receivable."""

    @pytest.mark.asyncio
    async def test_empty_ar(self):
        """No unpaid invoices should return empty AR."""
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_mock_result([]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="aged_ar",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )

        result = await ReportService.run_ar_aging(db, data)

        assert result.total_outstanding == 0
        assert len(result.buckets) == 4
        for bucket in result.buckets:
            assert bucket.count == 0
            assert bucket.total == 0

    @pytest.mark.asyncio
    async def test_ar_aging_buckets(self):
        """Invoices should be grouped into correct aging buckets."""
        db = AsyncMock()

        # Create overdue invoices at different ages
        today = TODAY
        inv_15 = MagicMock(spec=Invoice)
        inv_15.id = uuid.uuid4()
        inv_15.reference = "INV-001"
        inv_15.due_date = today - timedelta(days=15)
        inv_15.total = 1_000_00
        inv_15.credit_notes = []
        inv_15.contact = MagicMock()
        inv_15.contact.name = "Customer A"

        inv_45 = MagicMock(spec=Invoice)
        inv_45.id = uuid.uuid4()
        inv_45.reference = "INV-002"
        inv_45.due_date = today - timedelta(days=45)
        inv_45.total = 2_000_00
        inv_45.credit_notes = []
        inv_45.contact = MagicMock()
        inv_45.contact.name = "Customer B"

        inv_75 = MagicMock(spec=Invoice)
        inv_75.id = uuid.uuid4()
        inv_75.reference = "INV-003"
        inv_75.due_date = today - timedelta(days=75)
        inv_75.total = 3_000_00
        inv_75.credit_notes = []
        inv_75.contact = MagicMock()
        inv_75.contact.name = "Customer C"

        inv_120 = MagicMock(spec=Invoice)
        inv_120.id = uuid.uuid4()
        inv_120.reference = "INV-004"
        inv_120.due_date = today - timedelta(days=120)
        inv_120.total = 4_000_00
        inv_120.credit_notes = []
        inv_120.contact = MagicMock()
        inv_120.contact.name = "Customer D"

        db.execute = AsyncMock(return_value=_mock_result([inv_15, inv_45, inv_75, inv_120]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="aged_ar",
            start_date=date(2026, 1, 1),
            end_date=TODAY,
        )

        result = await ReportService.run_ar_aging(db, data)

        assert result.total_outstanding == 10_000_00
        assert len(result.buckets) == 4
        bucket_map = {b.bucket: b for b in result.buckets}
        assert bucket_map["0-30"].total == 1_000_00
        assert bucket_map["31-60"].total == 2_000_00
        assert bucket_map["61-90"].total == 3_000_00
        assert bucket_map["90+"].total == 4_000_00


# ---------------------------------------------------------------------------
# Aged AP Tests
# ---------------------------------------------------------------------------


class TestRunAP:
    """Tests for run_ap_aging — Aged Accounts Payable."""

    @pytest.mark.asyncio
    async def test_empty_ap(self):
        """No unpaid expense transactions should return empty AP."""
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_mock_result([]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="aged_ap",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )

        result = await ReportService.run_ap_aging(db, data)

        assert result.total_outstanding == 0
        assert len(result.buckets) == 4

    @pytest.mark.asyncio
    async def test_ap_aging_buckets(self):
        """Expense transactions should be grouped into aging buckets."""
        db = AsyncMock()

        exp_account = _make_account(
            id=uuid.uuid4(),
            code="5210",
            name="Rent",
            category="Expense",
            type="Expense",
        )

        # Rent bill from 45 days ago, unpaid
        exp_posting = _make_posting(uuid.uuid4(), exp_account, debit=5_000_00, credit=0)
        txn = _make_transaction(
            uuid.uuid4(),
            [exp_posting],
            effective_date=TODAY - timedelta(days=45),
        )

        db.execute = AsyncMock(return_value=_mock_result([txn]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="aged_ap",
            start_date=date(2026, 1, 1),
            end_date=TODAY,
        )

        result = await ReportService.run_ap_aging(db, data)

        assert result.total_outstanding == 5_000_00
        bucket_map = {b.bucket: b for b in result.buckets}
        assert bucket_map["31-60"].total == 5_000_00
        assert bucket_map["0-30"].total == 0
        assert bucket_map["61-90"].total == 0
        assert bucket_map["90+"].total == 0


# ---------------------------------------------------------------------------
# Run dispatch tests
# ---------------------------------------------------------------------------


class TestRunDispatch:
    """Tests for the main run() dispatcher."""

    @pytest.mark.asyncio
    async def test_run_dispatches_to_pl(self):
        """run() should dispatch profit_and_loss to run_pl()."""
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_mock_result([]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="profit_and_loss",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )

        result = await ReportService.run(db, data)

        assert result.report_type == "profit_and_loss"
        assert "report" in result.model_dump()

    @pytest.mark.asyncio
    async def test_run_dispatches_to_bs(self):
        """run() should dispatch balance_sheet to run_bs()."""
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_mock_result([]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="balance_sheet",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )

        result = await ReportService.run(db, data)

        assert result.report_type == "balance_sheet"

    @pytest.mark.asyncio
    async def test_run_dispatches_to_tb(self):
        """run() should dispatch trial_balance to run_tb()."""
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_mock_result([]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="trial_balance",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )

        result = await ReportService.run(db, data)

        assert result.report_type == "trial_balance"

    @pytest.mark.asyncio
    async def test_run_dispatches_to_ar(self):
        """run() should dispatch aged_ar to run_ar_aging()."""
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_mock_result([]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="aged_ar",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )

        result = await ReportService.run(db, data)

        assert result.report_type == "aged_ar"

    @pytest.mark.asyncio
    async def test_run_dispatches_to_ap(self):
        """run() should dispatch aged_ap to run_ap_aging()."""
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_mock_result([]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="aged_ap",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )

        result = await ReportService.run(db, data)

        assert result.report_type == "aged_ap"
