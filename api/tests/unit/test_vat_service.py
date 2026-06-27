"""Unit tests for VatService with mocked DB session."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.account import Account
from src.models.transaction import Posting, Transaction, VATLine
from src.models.vat import VatAdjustment, VatPeriod, VatReturn
from src.services.vat_service import (
    VatFlatRateMissingError,
    VatPeriodClosedError,
    VatPeriodNotFoundError,
    VatReturnNotFoundError,
    VatService,
    VatServiceError,
)
from src.validators.vat import VatAdjustmentCreate, VatPeriodCreate

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
        # Set server-default fields for VatPeriod
        if hasattr(obj, "status") and obj.status is None:
            obj.status = "open"
        if hasattr(obj, "closed_at") and hasattr(obj, "closed_at") and obj.closed_at is None:
            pass
    return mock_refresh


def _make_period(**overrides) -> VatPeriod:
    """Create a VatPeriod ORM instance."""
    defaults = {
        "id": uuid.uuid4(),
        "start_date": date(2026, 4, 1),
        "end_date": date(2026, 6, 30),
        "scheme": "standard",
        "flat_rate_percentage": None,
        "status": "open",
        "closed_at": None,
        "created_at": NOW,
    }
    defaults.update(overrides)
    return VatPeriod(**defaults)


def _make_return(**overrides) -> VatReturn:
    """Create a VatReturn ORM instance."""
    ret_id = overrides.pop("id", uuid.uuid4())
    defaults = {
        "id": ret_id,
        "period_id": uuid.uuid4(),
        "box1": 10000,
        "box2": 0,
        "box3": 10000,
        "box4": 5000,
        "box5": 5000,
        "box6": 50000,
        "box7": 25000,
        "box8": 0,
        "box9": 0,
        "submitted_at": None,
        "created_at": NOW,
        "adjustments": [],
    }
    defaults.update(overrides)
    vr = VatReturn(**defaults)
    vr.adjustments = defaults["adjustments"]
    return vr


def _make_transaction_with_vat_lines(
    txn_id: uuid.UUID,
    effective_date: date,
    reference: str = "JE-2026-0001",
    description: str = "Test sale",
) -> Transaction:
    """Create a posted Transaction with postings and VAT lines."""
    account = Account(
        id=uuid.uuid4(),
        code="4000",
        name="Sales",
        category="Income",
        type="Income",
        vat_rate="20%",
        is_active=True,
    )
    expense_account = Account(
        id=uuid.uuid4(),
        code="5000",
        name="Purchases",
        category="Expense",
        type="Expense",
        vat_rate="20%",
        is_active=True,
    )

    # Output VAT posting (sale)
    out_vl = VATLine(
        id=uuid.uuid4(),
        posting_id=uuid.uuid4(),
        vat_rate="20%",
        vat_amount=2000,
        net_amount=10000,
        vat_type="output",
    )
    out_posting = Posting(
        id=out_vl.posting_id,
        transaction_id=txn_id,
        account_id=account.id,
        debit_amount=12000,
        credit_amount=0,
        description="Sale revenue",
        vat_lines=[out_vl],
    )

    # Input VAT posting (purchase)
    in_vl = VATLine(
        id=uuid.uuid4(),
        posting_id=uuid.uuid4(),
        vat_rate="20%",
        vat_amount=1000,
        net_amount=5000,
        vat_type="input",
    )
    in_posting = Posting(
        id=in_vl.posting_id,
        transaction_id=txn_id,
        account_id=expense_account.id,
        debit_amount=0,
        credit_amount=6000,
        description="Purchase expense",
        vat_lines=[in_vl],
    )

    txn = Transaction(
        id=txn_id,
        reference=reference,
        description=description,
        status="posted",
        effective_date=effective_date,
        total_amount=6000,
        currency="GBP",
        contact_id=None,
        idempotency_key=None,
        recorded_at=None,
        created_at=NOW,
        updated_at=NOW,
        postings=[out_posting, in_posting],
    )
    return txn


# ======================================================================
# create_period
# ======================================================================


class TestCreatePeriod:
    """Unit tests for create_period."""

    @pytest.mark.asyncio
    async def test_create_standard_period(self) -> None:
        """Should create a standard scheme period."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = _make_refresh()

        data = VatPeriodCreate(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 6, 30),
            scheme="standard",
        )

        result = await VatService.create_period(db, data)
        assert result.scheme == "standard"
        assert result.start_date == date(2026, 4, 1)
        assert result.end_date == date(2026, 6, 30)
        assert result.status == "open"
        db.add.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_cash_period(self) -> None:
        """Should create a cash scheme period."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = _make_refresh()

        data = VatPeriodCreate(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 3, 31),
            scheme="cash",
        )

        result = await VatService.create_period(db, data)
        assert result.scheme == "cash"

    @pytest.mark.asyncio
    async def test_create_flat_rate_period(self) -> None:
        """Should create a flat_rate scheme period with percentage."""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = _make_refresh()

        data = VatPeriodCreate(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 6, 30),
            scheme="flat_rate",
            flat_rate_percentage=7.5,
        )

        result = await VatService.create_period(db, data)
        assert result.scheme == "flat_rate"
        assert result.flat_rate_percentage == 7.5

    @pytest.mark.asyncio
    async def test_create_flat_rate_missing_percentage(self) -> None:
        """Should raise VatFlatRateMissingError when flat_rate without percentage."""
        db = AsyncMock()
        db.add = MagicMock()
        data = VatPeriodCreate(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 6, 30),
            scheme="flat_rate",
        )

        with pytest.raises(VatFlatRateMissingError) as exc_info:
            await VatService.create_period(db, data)
        assert exc_info.value.status_code == 422


# ======================================================================
# list_periods
# ======================================================================


class TestListPeriods:
    """Unit tests for list_periods."""

    @pytest.mark.asyncio
    async def test_list_periods_empty(self) -> None:
        """Should return empty list."""
        db = AsyncMock()
        count_mock = MagicMock()
        count_mock.scalar_one.return_value = 0
        fetch_mock = MagicMock()
        fetch_mock.scalars.return_value.all.return_value = []
        db.execute.side_effect = [count_mock, fetch_mock]

        items, total = await VatService.list_periods(db)
        assert total == 0
        assert len(items) == 0

    @pytest.mark.asyncio
    async def test_list_periods_with_filters(self) -> None:
        """Should filter by status and scheme."""
        db = AsyncMock()
        period = _make_period()
        count_mock = MagicMock()
        count_mock.scalar_one.return_value = 1
        fetch_mock = MagicMock()
        fetch_mock.scalars.return_value.all.return_value = [period]
        db.execute.side_effect = [count_mock, fetch_mock]

        items, total = await VatService.list_periods(
            db, status="open", scheme="standard"
        )
        assert total == 1
        assert len(items) == 1
        assert items[0].status == "open"

    @pytest.mark.asyncio
    async def test_list_periods_multiple(self) -> None:
        """Should return multiple periods."""
        db = AsyncMock()
        periods = [
            _make_period(id=uuid.uuid4()),
            _make_period(id=uuid.uuid4(), scheme="cash"),
        ]
        count_mock = MagicMock()
        count_mock.scalar_one.return_value = 2
        fetch_mock = MagicMock()
        fetch_mock.scalars.return_value.all.return_value = periods
        db.execute.side_effect = [count_mock, fetch_mock]

        items, total = await VatService.list_periods(db)
        assert total == 2
        assert len(items) == 2


# ======================================================================
# calculate_return
# ======================================================================


class TestCalculateReturn:
    """Unit tests for calculate_return."""

    @pytest.mark.asyncio
    async def test_calculate_standard_scheme_success(self) -> None:
        """Should calculate 9-box return from VAT lines for standard scheme."""
        period = _make_period(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 6, 30),
            scheme="standard",
        )

        txn = _make_transaction_with_vat_lines(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 5, 15),
        )

        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = _make_refresh()

        # get for period
        async def mock_get(model, pk, **kwargs):
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_periods":
                return period
            return None

        db.get = mock_get

        # execute for transactions query
        db.execute = AsyncMock(return_value=_mock_result([txn]))

        result = await VatService.calculate_return(db, period.id)

        vr = result.vat_return
        assert vr.box1 == 2000  # output VAT
        assert vr.box2 == 0
        assert vr.box3 == 2000  # box1 + box2
        assert vr.box4 == 1000  # input VAT
        assert vr.box5 == 1000  # box3 - box4 (positive = payable)
        assert vr.box6 == 10000  # net sales
        assert vr.box7 == 5000  # net purchases
        assert vr.box8 == 0
        assert vr.box9 == 0

        # Verify audit
        assert result.audit is not None
        assert len(result.audit.entries) == 2
        assert result.audit.summary["box5"] == 1000

    @pytest.mark.asyncio
    async def test_calculate_cash_scheme(self) -> None:
        """Should use recorded_at for cash scheme."""
        period = _make_period(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 6, 30),
            scheme="cash",
        )

        txn = _make_transaction_with_vat_lines(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 3, 15),  # before period
        )
        txn.recorded_at = datetime(2026, 5, 15, tzinfo=timezone.utc)  # within period

        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = _make_refresh()

        async def mock_get(model, pk, **kwargs):
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_periods":
                return period
            return None

        db.get = mock_get
        db.execute = AsyncMock(return_value=_mock_result([txn]))

        result = await VatService.calculate_return(db, period.id)
        # Transaction should be found because recorded_at is within period
        assert result.vat_return.box1 == 2000
        assert result.vat_return.box4 == 1000

    @pytest.mark.asyncio
    async def test_calculate_flat_rate_scheme(self) -> None:
        """Should calculate using flat rate percentage."""
        period = _make_period(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 6, 30),
            scheme="flat_rate",
            flat_rate_percentage=7.5,
        )

        txn = _make_transaction_with_vat_lines(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 5, 15),
        )

        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = _make_refresh()

        async def mock_get(model, pk, **kwargs):
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_periods":
                return period
            return None

        db.get = mock_get
        db.execute = AsyncMock(return_value=_mock_result([txn]))

        result = await VatService.calculate_return(db, period.id)
        vr = result.vat_return
        # Gross turnover = 12000 (net 10000 + VAT 2000)
        # box1 = 7.5% of 12000 = 900
        assert vr.box1 == 900
        assert vr.box4 == 0  # no input VAT reclaim
        assert vr.box3 == 900
        assert vr.box5 == 900
        assert vr.box6 == 12000  # gross turnover
        assert vr.box7 == 5000  # net purchases

    @pytest.mark.asyncio
    async def test_calculate_period_not_found(self) -> None:
        """Should raise VatPeriodNotFoundError."""
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        with pytest.raises(VatPeriodNotFoundError) as exc_info:
            await VatService.calculate_return(db, uuid.uuid4())
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_calculate_period_closed(self) -> None:
        """Should raise VatPeriodClosedError for closed period."""
        period = _make_period(status="closed")
        db = AsyncMock()
        db.get = AsyncMock(return_value=period)

        with pytest.raises(VatPeriodClosedError) as exc_info:
            await VatService.calculate_return(db, period.id)
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_box5_positive_payable(self) -> None:
        """Box 5 > 0 means amount payable to HMRC."""
        period = _make_period(scheme="standard")

        # Create transaction where output > input
        txn = _make_transaction_with_vat_lines(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 5, 15),
        )
        # Modify vat lines: output=5000, input=1000
        txn.postings[0].vat_lines[0].vat_amount = 5000
        txn.postings[1].vat_lines[0].vat_amount = 1000

        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = _make_refresh()

        async def mock_get(model, pk, **kwargs):
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_periods":
                return period
            return None

        db.get = mock_get
        db.execute = AsyncMock(return_value=_mock_result([txn]))

        result = await VatService.calculate_return(db, period.id)
        assert result.vat_return.box1 == 5000
        assert result.vat_return.box4 == 1000
        assert result.vat_return.box3 == 5000
        assert result.vat_return.box5 == 4000  # positive = payable

    @pytest.mark.asyncio
    async def test_box5_negative_reclaimable(self) -> None:
        """Box 5 < 0 means amount reclaimable from HMRC."""
        period = _make_period(scheme="standard")

        # Create transaction where input > output
        txn = _make_transaction_with_vat_lines(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 5, 15),
        )
        txn.postings[0].vat_lines[0].vat_amount = 1000  # output
        txn.postings[0].vat_lines[0].net_amount = 5000
        txn.postings[1].vat_lines[0].vat_amount = 3000  # input
        txn.postings[1].vat_lines[0].net_amount = 15000

        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = _make_refresh()

        async def mock_get(model, pk, **kwargs):
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_periods":
                return period
            return None

        db.get = mock_get
        db.execute = AsyncMock(return_value=_mock_result([txn]))

        result = await VatService.calculate_return(db, period.id)
        assert result.vat_return.box1 == 1000
        assert result.vat_return.box4 == 3000
        assert result.vat_return.box3 == 1000
        assert result.vat_return.box5 == -2000  # negative = reclaimable
        assert result.vat_return.box6 == 5000
        assert result.vat_return.box7 == 15000

    @pytest.mark.asyncio
    async def test_calculate_no_transactions(self) -> None:
        """Should return zero-filled return when no transactions in period."""
        period = _make_period(scheme="standard")
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = _make_refresh()

        async def mock_get(model, pk, **kwargs):
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_periods":
                return period
            return None

        db.get = mock_get
        db.execute = AsyncMock(return_value=_mock_result([]))

        result = await VatService.calculate_return(db, period.id)
        vr = result.vat_return
        assert vr.box1 == 0
        assert vr.box2 == 0
        assert vr.box3 == 0
        assert vr.box4 == 0
        assert vr.box5 == 0
        assert vr.box6 == 0
        assert vr.box7 == 0
        assert vr.box8 == 0
        assert vr.box9 == 0


# ======================================================================
# get_return
# ======================================================================


class TestGetReturn:
    """Unit tests for get_return."""

    @pytest.mark.asyncio
    async def test_get_return_found(self) -> None:
        """Should return VAT return when found."""
        vr = _make_return()
        db = AsyncMock()
        db.get = AsyncMock(return_value=vr)

        result = await VatService.get_return(db, vr.id)
        assert result is not None
        assert result.box1 == 10000
        assert result.box5 == 5000

    @pytest.mark.asyncio
    async def test_get_return_not_found(self) -> None:
        """Should return None when not found."""
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        result = await VatService.get_return(db, uuid.uuid4())
        assert result is None


# ======================================================================
# add_adjustment
# ======================================================================


class TestAddAdjustment:
    """Unit tests for add_adjustment."""

    @pytest.mark.asyncio
    async def test_add_adjustment_success(self) -> None:
        """Should add adjustment and update box value."""
        period = _make_period()
        vr = _make_return(box1=10000, box4=5000, box3=10000, box5=5000)
        vr.period = period

        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = _make_refresh()
        db.get = AsyncMock(return_value=vr)

        data = VatAdjustmentCreate(
            box_number=4,
            amount=2000,
            reason="Additional purchase VAT discovered",
            source_reference="INV-2026-0042",
        )

        result = await VatService.add_adjustment(db, vr.id, data)
        assert result.box_number == 4
        assert result.amount_before == 5000
        assert result.amount_after == 7000
        assert result.reason == "Additional purchase VAT discovered"

        # Box values should be updated
        assert vr.box4 == 7000
        assert vr.box3 == 10000
        assert vr.box5 == 3000  # box3 - box4

    @pytest.mark.asyncio
    async def test_add_adjustment_negative(self) -> None:
        """Should handle negative adjustment (decrease box value)."""
        period = _make_period()
        vr = _make_return(box1=10000, box4=5000, box3=10000, box5=5000)
        vr.period = period

        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = _make_refresh()
        db.get = AsyncMock(return_value=vr)

        data = VatAdjustmentCreate(
            box_number=1,
            amount=-3000,
            reason="Corrected output VAT",
        )

        result = await VatService.add_adjustment(db, vr.id, data)
        assert result.amount_before == 10000
        assert result.amount_after == 7000
        assert vr.box1 == 7000
        assert vr.box3 == 7000
        assert vr.box5 == 2000  # 7000 - 5000

    @pytest.mark.asyncio
    async def test_add_adjustment_return_not_found(self) -> None:
        """Should raise VatReturnNotFoundError."""
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)
        data = VatAdjustmentCreate(
            box_number=1, amount=1000, reason="Test"
        )

        with pytest.raises(VatReturnNotFoundError) as exc_info:
            await VatService.add_adjustment(db, uuid.uuid4(), data)
        assert exc_info.value.status_code == 404


# ======================================================================
# get_audit_trail
# ======================================================================


class TestGetAuditTrail:
    """Unit tests for get_audit_trail."""

    @pytest.mark.asyncio
    async def test_get_audit_trail_success(self) -> None:
        """Should return audit trail with adjustments."""
        period = _make_period()
        adj = VatAdjustment(
            id=uuid.uuid4(),
            vat_return_id=uuid.uuid4(),
            box_number=4,
            amount_before=5000,
            amount_after=7000,
            reason="Additional VAT",
            source_reference="INV-2026-0042",
            created_at=NOW,
        )
        vr = _make_return(adjustments=[adj])
        vr.period = period

        db = AsyncMock()

        async def mock_get(model, pk, **kwargs):
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_returns":
                return vr
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_periods":
                return period
            return None

        db.get = mock_get

        result = await VatService.get_audit_trail(db, vr.id)
        assert result.vat_return_id == vr.id
        assert result.summary["box5"] == 5000
        assert len(result.entries) == 1
        assert result.entries[0].source_type == "adjustment"
        assert result.entries[0].amount == 2000  # after - before

    @pytest.mark.asyncio
    async def test_get_audit_trail_no_adjustments(self) -> None:
        """Should return empty entries when no adjustments."""
        period = _make_period()
        vr = _make_return(adjustments=[])
        vr.period = period

        db = AsyncMock()

        async def mock_get(model, pk, **kwargs):
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_returns":
                return vr
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_periods":
                return period
            return None

        db.get = mock_get

        result = await VatService.get_audit_trail(db, vr.id)
        assert result.vat_return_id == vr.id
        assert len(result.entries) == 0

    @pytest.mark.asyncio
    async def test_get_audit_trail_return_not_found(self) -> None:
        """Should raise VatReturnNotFoundError."""
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        with pytest.raises(VatReturnNotFoundError) as exc_info:
            await VatService.get_audit_trail(db, uuid.uuid4())
        assert exc_info.value.status_code == 404


# ======================================================================
# Box 5 correctness
# ======================================================================


class TestBox5Correctness:
    """Tests verifying the CRITICAL Box 5 calculation."""

    @pytest.mark.asyncio
    async def test_box5_equals_box3_minus_box4(self) -> None:
        """Box 5 must always equal Box 3 - Box 4."""
        period = _make_period(scheme="standard")

        txn = _make_transaction_with_vat_lines(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 5, 15),
        )

        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = _make_refresh()

        async def mock_get(model, pk, **kwargs):
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_periods":
                return period
            return None

        db.get = mock_get
        db.execute = AsyncMock(return_value=_mock_result([txn]))

        result = await VatService.calculate_return(db, period.id)
        assert result.vat_return.box5 == result.vat_return.box3 - result.vat_return.box4

    @pytest.mark.asyncio
    async def test_box5_positive_is_payable(self) -> None:
        """When Box 5 > 0, the business pays HMRC."""
        period = _make_period(scheme="standard")

        txn = _make_transaction_with_vat_lines(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 5, 15),
        )
        txn.postings[0].vat_lines[0].vat_amount = 10000  # large output
        txn.postings[1].vat_lines[0].vat_amount = 2000  # small input

        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = _make_refresh()

        async def mock_get(model, pk, **kwargs):
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_periods":
                return period
            return None

        db.get = mock_get
        db.execute = AsyncMock(return_value=_mock_result([txn]))

        result = await VatService.calculate_return(db, period.id)
        assert result.vat_return.box5 > 0
        assert result.vat_return.box5 == 8000  # 10000 - 2000

    @pytest.mark.asyncio
    async def test_box5_negative_is_reclaimable(self) -> None:
        """When Box 5 < 0, HMRC owes the business."""
        period = _make_period(scheme="standard")

        txn = _make_transaction_with_vat_lines(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 5, 15),
        )
        txn.postings[0].vat_lines[0].vat_amount = 500  # small output
        txn.postings[0].vat_lines[0].net_amount = 2500
        txn.postings[1].vat_lines[0].vat_amount = 3000  # large input
        txn.postings[1].vat_lines[0].net_amount = 15000

        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = _make_refresh()

        async def mock_get(model, pk, **kwargs):
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_periods":
                return period
            return None

        db.get = mock_get
        db.execute = AsyncMock(return_value=_mock_result([txn]))

        result = await VatService.calculate_return(db, period.id)
        assert result.vat_return.box5 < 0
        assert result.vat_return.box5 == -2500  # 500 - 3000
