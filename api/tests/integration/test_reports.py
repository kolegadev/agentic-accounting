"""Integration tests for the full report engine pipeline with mocked DB."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.account import Account
from src.models.transaction import Posting, Transaction
from src.services.report_service import (
    InvalidReportParameterError,
    ReportService,
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
    """Return an async refresh mock."""

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
# Full P&L integration
# ---------------------------------------------------------------------------


class TestFullPnL:
    """End-to-end P&L report generation."""

    @pytest.mark.asyncio
    async def test_complete_pl_with_comparison(self):
        """Generate a full P&L with period comparison."""
        db = AsyncMock()

        # --- Accounts ---
        rev = _make_account(
            id=uuid.uuid4(),
            code="4000",
            name="Sales",
            category="Revenue",
            type="Revenue",
        )
        dc = _make_account(
            id=uuid.uuid4(),
            code="5000",
            name="COGS",
            category="Expense",
            type="DirectCost",
        )
        exp1 = _make_account(
            id=uuid.uuid4(),
            code="5210",
            name="Rent",
            category="Expense",
            type="Expense",
        )
        exp2 = _make_account(
            id=uuid.uuid4(),
            code="5220",
            name="Marketing",
            category="Expense",
            type="Expense",
        )

        # --- Current period: £200k revenue, £80k COGS, £50k expenses ---
        current_txn = _make_transaction(
            uuid.uuid4(),
            [
                _make_posting(uuid.uuid4(), rev, debit=0, credit=200_000_00),
                _make_posting(uuid.uuid4(), dc, debit=80_000_00, credit=0),
                _make_posting(uuid.uuid4(), exp1, debit=30_000_00, credit=0),
                _make_posting(uuid.uuid4(), exp2, debit=20_000_00, credit=0),
            ],
        )

        # Simulate two separate execute calls: current period, then comparison
        call_count = 0
        async def execute_side_effect(stmt, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _mock_result([current_txn])
            else:
                return _mock_result([])  # No previous period data

        db.execute = AsyncMock(side_effect=execute_side_effect)
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="profit_and_loss",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
            comparison=True,
        )

        result = await ReportService.run_pl(db, data)

        # Assert structure
        assert result.report_type == "profit_and_loss"
        assert result.start_date == date(2026, 1, 1)
        assert result.end_date == date(2026, 6, 30)
        assert result.comparison is True

        # Assert figures
        assert result.revenue.subtotal == 200_000_00
        assert result.direct_costs.subtotal == 80_000_00
        assert result.gross_profit == 120_000_00
        assert result.expenses.subtotal == 50_000_00
        assert result.net_profit == 70_000_00

    @pytest.mark.asyncio
    async def test_pl_loss_scenario(self):
        """Revenue < Expenses should produce negative net profit (loss)."""
        db = AsyncMock()

        rev = _make_account(
            id=uuid.uuid4(),
            code="4000",
            name="Sales",
            category="Revenue",
            type="Revenue",
        )
        exp = _make_account(
            id=uuid.uuid4(),
            code="5210",
            name="Rent",
            category="Expense",
            type="Expense",
        )

        # Revenue £5k, Expenses £8k → Net Loss £3k
        txn = _make_transaction(
            uuid.uuid4(),
            [
                _make_posting(uuid.uuid4(), rev, debit=0, credit=5_000_00),
                _make_posting(uuid.uuid4(), exp, debit=8_000_00, credit=0),
            ],
        )

        db.execute = AsyncMock(return_value=_mock_result([txn]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="profit_and_loss",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )

        result = await ReportService.run_pl(db, data)

        assert result.net_profit == -3_000_00
        assert result.gross_profit == 5_000_00  # Revenue (no DC)


# ---------------------------------------------------------------------------
# Full Balance Sheet integration
# ---------------------------------------------------------------------------


class TestFullBS:
    """End-to-end Balance Sheet generation."""

    @pytest.mark.asyncio
    async def test_full_balance_sheet_with_all_categories(self):
        """BS with assets, liabilities, equity across all types."""
        db = AsyncMock()

        # Assets
        bank = _make_account(
            id=uuid.uuid4(),
            code="1000",
            name="Bank Current",
            category="Asset",
            type="Bank",
        )
        receivables = _make_account(
            id=uuid.uuid4(),
            code="1100",
            name="Trade Receivables",
            category="Asset",
            type="CurrentAsset",
        )
        equipment = _make_account(
            id=uuid.uuid4(),
            code="1500",
            name="Equipment",
            category="Asset",
            type="FixedAsset",
        )

        # Liabilities
        payables = _make_account(
            id=uuid.uuid4(),
            code="2000",
            name="Trade Payables",
            category="Liability",
            type="CurrentLiability",
        )
        mortgage = _make_account(
            id=uuid.uuid4(),
            code="2500",
            name="Mortgage",
            category="Liability",
            type="LongTermLiability",
        )

        # Equity
        capital = _make_account(
            id=uuid.uuid4(),
            code="3000",
            name="Share Capital",
            category="Equity",
            type="Equity",
        )
        retained = _make_account(
            id=uuid.uuid4(),
            code="3100",
            name="Retained Earnings",
            category="Equity",
            type="Equity",
        )

        # £100k assets, £60k liabilities, £40k equity
        txn = _make_transaction(
            uuid.uuid4(),
            [
                _make_posting(uuid.uuid4(), bank, debit=60_000_00, credit=0),
                _make_posting(uuid.uuid4(), receivables, debit=20_000_00, credit=0),
                _make_posting(uuid.uuid4(), equipment, debit=20_000_00, credit=0),
                _make_posting(uuid.uuid4(), payables, debit=0, credit=30_000_00),
                _make_posting(uuid.uuid4(), mortgage, debit=0, credit=30_000_00),
                _make_posting(uuid.uuid4(), capital, debit=0, credit=30_000_00),
                _make_posting(uuid.uuid4(), retained, debit=0, credit=10_000_00),
            ],
        )

        db.execute = AsyncMock(return_value=_mock_result([txn]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="balance_sheet",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 27),
        )

        result = await ReportService.run_bs(db, data)

        # Assert sections
        assert result.current_assets.subtotal == 80_000_00  # Bank + Receivables
        assert result.fixed_assets.subtotal == 20_000_00  # Equipment
        assert result.total_assets == 100_000_00

        assert result.current_liabilities.subtotal == 30_000_00
        assert result.long_term_liabilities.subtotal == 30_000_00
        assert result.total_liabilities == 60_000_00

        assert result.equity.subtotal == 40_000_00
        assert result.total_equity == 40_000_00

        assert result.total_liabilities_and_equity == 100_000_00
        assert result.balanced is True

    @pytest.mark.asyncio
    async def test_balance_sheet_must_balance(self):
        """Assets = Liabilities + Equity is enforced."""
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
            name="Capital",
            category="Equity",
            type="Equity",
        )

        txn = _make_transaction(
            uuid.uuid4(),
            [
                _make_posting(uuid.uuid4(), bank, debit=150_000_00, credit=0),
                _make_posting(uuid.uuid4(), capital, debit=0, credit=150_000_00),
            ],
        )

        db.execute = AsyncMock(return_value=_mock_result([txn]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="balance_sheet",
            start_date=date(2026, 1, 1),
            end_date=TODAY,
        )

        result = await ReportService.run_bs(db, data)

        assert result.total_assets == 150_000_00
        assert result.total_liabilities_and_equity == 150_000_00
        assert result.balanced is True


# ---------------------------------------------------------------------------
# Full Trial Balance integration
# ---------------------------------------------------------------------------


class TestFullTB:
    """End-to-end Trial Balance generation."""

    @pytest.mark.asyncio
    async def test_tb_multiple_transactions(self):
        """Trial Balance should aggregate across multiple transactions."""
        db = AsyncMock()

        bank = _make_account(
            id=uuid.uuid4(),
            code="1000",
            name="Bank",
            category="Asset",
            type="Bank",
        )
        revenue = _make_account(
            id=uuid.uuid4(),
            code="4000",
            name="Sales",
            category="Revenue",
            type="Revenue",
        )
        expense = _make_account(
            id=uuid.uuid4(),
            code="5210",
            name="Rent",
            category="Expense",
            type="Expense",
        )

        # Transaction 1: Revenue £10,000
        txn1 = _make_transaction(
            uuid.uuid4(),
            [
                _make_posting(uuid.uuid4(), bank, debit=10_000_00, credit=0),
                _make_posting(uuid.uuid4(), revenue, debit=0, credit=10_000_00),
            ],
        )

        # Transaction 2: Expense £2,000
        txn2 = _make_transaction(
            uuid.uuid4(),
            [
                _make_posting(uuid.uuid4(), expense, debit=2_000_00, credit=0),
                _make_posting(uuid.uuid4(), bank, debit=0, credit=2_000_00),
            ],
        )

        db.execute = AsyncMock(return_value=_mock_result([txn1, txn2]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="trial_balance",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 6, 30),
        )

        result = await ReportService.run_tb(db, data)

        assert result.total_debits == 12_000_00  # 10k bank + 2k expense
        assert result.total_credits == 12_000_00  # 10k revenue + 2k bank
        assert result.difference == 0
        assert result.balanced is True
        assert len(result.accounts) == 3

        # Verify account-level values
        account_map = {a.account_code: a for a in result.accounts}
        assert account_map["1000"].debit_amount == 10_000_00
        assert account_map["1000"].credit_amount == 2_000_00
        assert account_map["1000"].net_amount == 8_000_00  # Debit balance
        assert account_map["4000"].credit_amount == 10_000_00
        assert account_map["5210"].debit_amount == 2_000_00


# ---------------------------------------------------------------------------
# Aged AR integration
# ---------------------------------------------------------------------------


class TestFullAR:
    """End-to-end Aged AR generation."""

    @pytest.mark.asyncio
    async def test_ar_with_mixed_ages(self):
        """AR should handle invoices at various ages correctly."""
        from src.models.invoice import Invoice

        db = AsyncMock()

        today = TODAY
        inv_recent = MagicMock(spec=Invoice)
        inv_recent.id = uuid.uuid4()
        inv_recent.reference = "INV-001"
        inv_recent.due_date = today - timedelta(days=10)
        inv_recent.total = 500_00
        inv_recent.credit_notes = []
        inv_recent.contact = MagicMock()
        inv_recent.contact.name = "Customer A"

        inv_old = MagicMock(spec=Invoice)
        inv_old.id = uuid.uuid4()
        inv_old.reference = "INV-002"
        inv_old.due_date = today - timedelta(days=100)
        inv_old.total = 2_500_00
        inv_old.credit_notes = []
        inv_old.contact = MagicMock()
        inv_old.contact.name = "Customer B"

        # Only include overdue (not current) per the default query
        db.execute = AsyncMock(return_value=_mock_result([inv_recent, inv_old]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="aged_ar",
            start_date=date(2026, 1, 1),
            end_date=TODAY,
        )

        result = await ReportService.run_ar_aging(db, data)

        assert result.total_outstanding == 3_000_00
        bucket_map = {b.bucket: b for b in result.buckets}
        assert bucket_map["0-30"].total == 500_00
        assert bucket_map["90+"].total == 2_500_00
        assert bucket_map["31-60"].total == 0
        assert bucket_map["61-90"].total == 0


# ---------------------------------------------------------------------------
# Aged AP integration
# ---------------------------------------------------------------------------


class TestFullAP:
    """End-to-end Aged AP generation."""

    @pytest.mark.asyncio
    async def test_ap_with_expense_transactions(self):
        """AP should aggregate unpaid expense postings by age."""
        db = AsyncMock()

        rent = _make_account(
            id=uuid.uuid4(),
            code="5210",
            name="Rent",
            category="Expense",
            type="Expense",
        )
        supplies = _make_account(
            id=uuid.uuid4(),
            code="5220",
            name="Supplies",
            category="Expense",
            type="Expense",
        )

        # Rent from 45 days ago
        txn1 = _make_transaction(
            uuid.uuid4(),
            [_make_posting(uuid.uuid4(), rent, debit=3_000_00, credit=0)],
            effective_date=TODAY - timedelta(days=45),
        )

        # Supplies from 10 days ago
        txn2 = _make_transaction(
            uuid.uuid4(),
            [_make_posting(uuid.uuid4(), supplies, debit=1_500_00, credit=0)],
            effective_date=TODAY - timedelta(days=10),
        )

        db.execute = AsyncMock(return_value=_mock_result([txn1, txn2]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        data = ReportRunRequest(
            template_name="aged_ap",
            start_date=date(2026, 1, 1),
            end_date=TODAY,
        )

        result = await ReportService.run_ap_aging(db, data)

        assert result.total_outstanding == 4_500_00
        bucket_map = {b.bucket: b for b in result.buckets}
        assert bucket_map["0-30"].total == 1_500_00
        assert bucket_map["31-60"].total == 3_000_00


# ---------------------------------------------------------------------------
# Report dispatch integration
# ---------------------------------------------------------------------------


class TestReportDispatch:
    """Tests for the report dispatch mechanism."""

    @pytest.mark.asyncio
    async def test_all_report_types_run(self):
        """All five report types should be dispatchable."""
        db = AsyncMock()
        db.execute = AsyncMock(return_value=_mock_result([]))
        db.commit = AsyncMock()
        db.refresh = AsyncMock(side_effect=_make_refresh())

        types = [
            "profit_and_loss",
            "balance_sheet",
            "trial_balance",
            "aged_ar",
            "aged_ap",
        ]

        for report_type in types:
            data = ReportRunRequest(
                template_name=report_type,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 6, 30),
            )
            result = await ReportService.run(db, data)
            assert result.report_type == report_type
            assert result.format == "json"


# ---------------------------------------------------------------------------
# Parameter validation integration
# ---------------------------------------------------------------------------


class TestParameterValidation:
    """Integration-level validation tests."""

    def test_date_validation(self):
        """start_date must be <= end_date."""
        with pytest.raises(InvalidReportParameterError):
            ReportService._validate_params(
                ReportRunRequest(
                    template_name="profit_and_loss",
                    start_date=date(2026, 12, 31),
                    end_date=date(2026, 1, 1),
                )
            )

    def test_equal_dates_accepted(self):
        """start_date == end_date should be valid (single-day report)."""
        ReportService._validate_params(
            ReportRunRequest(
                template_name="profit_and_loss",
                start_date=date(2026, 6, 30),
                end_date=date(2026, 6, 30),
            )
        )  # Should not raise

    def test_format_validation(self):
        """Only json, csv, html, pdf should be accepted as formats."""
        valid = ["json", "csv", "html", "pdf"]
        for fmt in valid:
            ReportService._validate_params(
                ReportRunRequest(
                    template_name="profit_and_loss",
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 6, 30),
                    format=fmt,
                )
            )

        with pytest.raises(InvalidReportParameterError):
            ReportService._validate_params(
                ReportRunRequest(
                    template_name="profit_and_loss",
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 6, 30),
                    format="xlsx",
                )
            )
