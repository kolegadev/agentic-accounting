"""Integration tests for VAT return calculation, adjustment, and audit trail with mocked DB."""

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


def _make_transaction(
    txn_id: uuid.UUID,
    effective_date: date,
    output_vat: int = 2000,
    output_net: int = 10000,
    input_vat: int = 1000,
    input_net: int = 5000,
    reference: str = "JE-2026-0001",
    description: str = "Test transaction",
) -> Transaction:
    """Create a posted Transaction with output and input VAT lines."""
    out_vl = VATLine(
        id=uuid.uuid4(),
        posting_id=uuid.uuid4(),
        vat_rate="20%",
        vat_amount=output_vat,
        net_amount=output_net,
        vat_type="output",
    )
    out_posting = Posting(
        id=out_vl.posting_id,
        transaction_id=txn_id,
        account_id=uuid.uuid4(),
        debit_amount=output_net + output_vat,
        credit_amount=0,
        description="Sale",
        vat_lines=[out_vl],
    )

    in_vl = VATLine(
        id=uuid.uuid4(),
        posting_id=uuid.uuid4(),
        vat_rate="20%",
        vat_amount=input_vat,
        net_amount=input_net,
        vat_type="input",
    )
    in_posting = Posting(
        id=in_vl.posting_id,
        transaction_id=txn_id,
        account_id=uuid.uuid4(),
        debit_amount=0,
        credit_amount=input_net + input_vat,
        description="Purchase",
        vat_lines=[in_vl],
    )

    return Transaction(
        id=txn_id,
        reference=reference,
        description=description,
        status="posted",
        effective_date=effective_date,
        total_amount=(output_net + output_vat) - (input_net + input_vat),
        currency="GBP",
        contact_id=None,
        idempotency_key=None,
        recorded_at=None,
        created_at=NOW,
        updated_at=NOW,
        postings=[out_posting, in_posting],
    )


# ======================================================================
# Full VAT Lifecycle: create period → calculate → adjust → audit
# ======================================================================


class TestFullVatLifecycle:
    """Test the complete VAT lifecycle: period → calculation → adjustment → audit."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_standard_scheme(self) -> None:
        """Complete flow for standard scheme: create, calculate, adjust, audit."""
        # ================================================================
        # PHASE 1: Create VAT period
        # ================================================================
        db_create = AsyncMock()
        db_create.add = MagicMock()
        db_create.commit = AsyncMock()
        db_create.refresh = _make_refresh()

        data = VatPeriodCreate(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 6, 30),
            scheme="standard",
        )

        period_resp = await VatService.create_period(db_create, data)
        assert period_resp.scheme == "standard"
        assert period_resp.status == "open"

        period_id = period_resp.id
        period = _make_period(id=period_id, scheme="standard")

        # ================================================================
        # PHASE 2: Calculate return with multiple transactions
        # ================================================================
        txn1 = _make_transaction(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 4, 15),
            output_vat=4000,
            output_net=20000,
            input_vat=1500,
            input_net=7500,
            reference="JE-2026-0010",
            description="April sale + purchase",
        )
        txn2 = _make_transaction(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 5, 20),
            output_vat=6000,
            output_net=30000,
            input_vat=2500,
            input_net=12500,
            reference="JE-2026-0011",
            description="May sale + purchase",
        )

        db_calc = AsyncMock()
        db_calc.add = MagicMock()
        db_calc.commit = AsyncMock()
        db_calc.refresh = _make_refresh()

        async def mock_get_calc(model, pk, **kwargs):
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_periods":
                return period
            return None

        db_calc.get = mock_get_calc
        db_calc.execute = AsyncMock(return_value=_mock_result([txn1, txn2]))

        calc_result = await VatService.calculate_return(db_calc, period_id)

        vr = calc_result.vat_return
        # box1 = 4000 + 6000 = 10000
        assert vr.box1 == 10000
        # box4 = 1500 + 2500 = 4000
        assert vr.box4 == 4000
        # box3 = box1 + box2 = 10000
        assert vr.box3 == 10000
        # box5 = box3 - box4 = 6000 (payable)
        assert vr.box5 == 6000
        # box6 = 20000 + 30000 = 50000
        assert vr.box6 == 50000
        # box7 = 7500 + 12500 = 20000
        assert vr.box7 == 20000

        # Audit entries
        assert len(calc_result.audit.entries) == 4  # 2 output + 2 input
        assert calc_result.audit.summary["box5"] == 6000

        return_id = vr.id

        # ================================================================
        # PHASE 3: Add adjustment
        # ================================================================
        vat_return_orm = VatReturn(
            id=return_id,
            period_id=period_id,
            box1=10000,
            box2=0,
            box3=10000,
            box4=4000,
            box5=6000,
            box6=50000,
            box7=20000,
            box8=0,
            box9=0,
            created_at=NOW,
        )
        vat_return_orm.period = period
        vat_return_orm.adjustments = []

        db_adj = AsyncMock()
        db_adj.add = MagicMock()
        db_adj.commit = AsyncMock()
        db_adj.refresh = _make_refresh()

        async def mock_get_adj(model, pk, **kwargs):
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_returns":
                return vat_return_orm
            return None

        db_adj.get = mock_get_adj

        adj_data = VatAdjustmentCreate(
            box_number=1,
            amount=2000,
            reason="Additional output VAT from late invoice",
            source_reference="INV-2026-0099",
        )

        adj_resp = await VatService.add_adjustment(db_adj, return_id, adj_data)
        assert adj_resp.box_number == 1
        assert adj_resp.amount_before == 10000
        assert adj_resp.amount_after == 12000

        # Verify box and dependent recalc
        assert vat_return_orm.box1 == 12000
        assert vat_return_orm.box3 == 12000  # recalculated
        assert vat_return_orm.box5 == 8000  # recalculated: 12000 - 4000

        # ================================================================
        # PHASE 4: Get audit trail
        # ================================================================
        adj_orm = VatAdjustment(
            id=uuid.uuid4(),
            vat_return_id=return_id,
            box_number=1,
            amount_before=10000,
            amount_after=12000,
            reason="Additional output VAT from late invoice",
            source_reference="INV-2026-0099",
            created_at=NOW,
        )
        vat_return_orm.adjustments = [adj_orm]

        db_audit = AsyncMock()

        async def mock_get_audit(model, pk, **kwargs):
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_returns":
                return vat_return_orm
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_periods":
                return period
            return None

        db_audit.get = mock_get_audit

        audit_result = await VatService.get_audit_trail(db_audit, return_id)
        assert audit_result.vat_return_id == return_id
        assert len(audit_result.entries) == 1
        assert audit_result.entries[0].source_type == "adjustment"
        assert audit_result.entries[0].amount == 2000
        assert audit_result.summary["box5"] == 8000


# ======================================================================
# Three VAT Schemes
# ======================================================================


class TestThreeVatSchemes:
    """Test standard, cash, and flat_rate schemes with same data produce correct results."""

    @pytest.mark.asyncio
    async def test_standard_scheme_uses_effective_date(self) -> None:
        """Standard scheme: transaction within period by effective_date is included."""
        period = _make_period(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 6, 30),
            scheme="standard",
        )

        txn_in = _make_transaction(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 5, 15),  # within period
            output_vat=3000,
            output_net=15000,
            input_vat=1000,
            input_net=5000,
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
        db.execute = AsyncMock(return_value=_mock_result([txn_in]))

        result = await VatService.calculate_return(db, period.id)
        assert result.vat_return.box1 == 3000
        assert result.vat_return.box4 == 1000
        assert result.vat_return.box5 == 2000

    @pytest.mark.asyncio
    async def test_cash_scheme_uses_recorded_date(self) -> None:
        """Cash scheme: transaction included only if recorded_at within period."""
        period = _make_period(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 6, 30),
            scheme="cash",
        )

        # Transaction with effective_date before period but recorded_at within
        txn = _make_transaction(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 3, 15),  # before period
            output_vat=2000,
            input_vat=800,
        )
        txn.recorded_at = datetime(2026, 5, 10, tzinfo=timezone.utc)  # within period

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
        assert result.vat_return.box4 == 800
        assert result.vat_return.box5 == 1200

    @pytest.mark.asyncio
    async def test_flat_rate_scheme_calculation(self) -> None:
        """Flat rate: box1 = 7.5% of gross turnover, box4 = 0."""
        period = _make_period(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 6, 30),
            scheme="flat_rate",
            flat_rate_percentage=7.5,
        )

        # Gross turnover = net + VAT = 10000 + 2000 = 12000
        txn = _make_transaction(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 5, 15),
            output_vat=2000,
            output_net=10000,
            input_vat=1000,
            input_net=5000,
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
        # gross_turnover = 12000, 7.5% = 900
        assert vr.box1 == 900
        assert vr.box4 == 0  # no input VAT reclaim in flat rate
        assert vr.box6 == 12000  # gross turnover
        assert vr.box7 == 5000  # net purchases

    @pytest.mark.asyncio
    async def test_flat_rate_different_percentages(self) -> None:
        """Different flat rate percentages produce proportional output VAT."""
        # 10% flat rate
        period_10 = _make_period(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 6, 30),
            scheme="flat_rate",
            flat_rate_percentage=10.0,
        )

        txn = _make_transaction(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 5, 15),
            output_vat=2000,
            output_net=10000,
        )

        db10 = AsyncMock()
        db10.add = MagicMock()
        db10.commit = AsyncMock()
        db10.refresh = _make_refresh()

        async def mock_get_10(model, pk, **kwargs):
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_periods":
                return period_10
            return None

        db10.get = mock_get_10
        db10.execute = AsyncMock(return_value=_mock_result([txn]))

        result10 = await VatService.calculate_return(db10, period_10.id)
        assert result10.vat_return.box1 == 1200  # 10% of 12000

        # 15% flat rate
        period_15 = _make_period(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 6, 30),
            scheme="flat_rate",
            flat_rate_percentage=15.0,
        )

        db15 = AsyncMock()
        db15.add = MagicMock()
        db15.commit = AsyncMock()
        db15.refresh = _make_refresh()

        async def mock_get_15(model, pk, **kwargs):
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_periods":
                return period_15
            return None

        db15.get = mock_get_15
        db15.execute = AsyncMock(return_value=_mock_result([txn]))

        result15 = await VatService.calculate_return(db15, period_15.id)
        assert result15.vat_return.box1 == 1800  # 15% of 12000


# ======================================================================
# Box 5 edge cases
# ======================================================================


class TestBox5EdgeCases:
    """Test edge cases for Box 5 (Net VAT) calculation."""

    @pytest.mark.asyncio
    async def test_net_zero(self) -> None:
        """Box 5 = 0 when output equals input."""
        period = _make_period(scheme="standard")

        txn = _make_transaction(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 5, 15),
            output_vat=5000,
            output_net=25000,
            input_vat=5000,
            input_net=25000,
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
        assert result.vat_return.box5 == 0
        assert result.vat_return.box3 == 5000
        assert result.vat_return.box4 == 5000

    @pytest.mark.asyncio
    async def test_output_only(self) -> None:
        """Only output VAT, no input VAT."""
        period = _make_period(scheme="standard")

        txn = _make_transaction(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 5, 15),
            output_vat=8000,
            output_net=40000,
            input_vat=0,
            input_net=0,
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
        assert result.vat_return.box1 == 8000
        assert result.vat_return.box4 == 0
        assert result.vat_return.box5 == 8000  # payable

    @pytest.mark.asyncio
    async def test_input_only(self) -> None:
        """Only input VAT, no output VAT — reclaimable."""
        period = _make_period(scheme="standard")

        txn = _make_transaction(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 5, 15),
            output_vat=0,
            output_net=0,
            input_vat=5000,
            input_net=25000,
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
        assert result.vat_return.box1 == 0
        assert result.vat_return.box4 == 5000
        assert result.vat_return.box5 == -5000  # reclaimable
        assert result.vat_return.box6 == 0
        assert result.vat_return.box7 == 25000


# ======================================================================
# Adjustment — dependent box recalculation
# ======================================================================


class TestDependentBoxRecalculation:
    """Test that adjusting one box recalculates dependent boxes."""

    @pytest.mark.asyncio
    async def test_adjusting_box4_recalculates_box5(self) -> None:
        """Adjusting box4 should recalculate box5 (box3 - box4)."""
        period = _make_period()
        vr_orm = VatReturn(
            id=uuid.uuid4(),
            period_id=period.id,
            box1=10000,
            box2=500,
            box3=10500,  # box1 + box2
            box4=3000,
            box5=7500,  # box3 - box4
            box6=50000,
            box7=15000,
            box8=0,
            box9=0,
            created_at=NOW,
            adjustments=[],
        )
        vr_orm.period = period

        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = _make_refresh()
        db.get = AsyncMock(return_value=vr_orm)

        # Increase box4 by 1500
        adj_data = VatAdjustmentCreate(
            box_number=4,
            amount=1500,
            reason="Missed purchase VAT",
        )

        result = await VatService.add_adjustment(db, vr_orm.id, adj_data)
        assert result.amount_after == 4500
        assert vr_orm.box4 == 4500
        assert vr_orm.box3 == 10500  # unchanged
        assert vr_orm.box5 == 6000  # 10500 - 4500

    @pytest.mark.asyncio
    async def test_adjusting_box2_recalculates_box3_and_box5(self) -> None:
        """Adjusting box2 should recalculate box3 and box5."""
        period = _make_period()
        vr_orm = VatReturn(
            id=uuid.uuid4(),
            period_id=period.id,
            box1=10000,
            box2=1000,
            box3=11000,
            box4=3000,
            box5=8000,
            box6=50000,
            box7=15000,
            box8=0,
            box9=0,
            created_at=NOW,
            adjustments=[],
        )
        vr_orm.period = period

        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = _make_refresh()
        db.get = AsyncMock(return_value=vr_orm)

        adj_data = VatAdjustmentCreate(
            box_number=2,
            amount=500,
            reason="EU acquisition VAT",
        )

        result = await VatService.add_adjustment(db, vr_orm.id, adj_data)
        assert vr_orm.box2 == 1500
        assert vr_orm.box3 == 11500  # 10000 + 1500
        assert vr_orm.box5 == 8500  # 11500 - 3000


# ======================================================================
# Error Scenarios
# ======================================================================


class TestErrorScenarios:
    """Integration-level error scenarios."""

    @pytest.mark.asyncio
    async def test_calculate_closed_period(self) -> None:
        """Should raise VatPeriodClosedError for closed period."""
        period = _make_period(status="closed")
        db = AsyncMock()
        db.get = AsyncMock(return_value=period)

        with pytest.raises(VatPeriodClosedError) as exc_info:
            await VatService.calculate_return(db, period.id)
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_calculate_nonexistent_period(self) -> None:
        """Should raise VatPeriodNotFoundError."""
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        with pytest.raises(VatPeriodNotFoundError) as exc_info:
            await VatService.calculate_return(db, uuid.uuid4())
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_adjust_nonexistent_return(self) -> None:
        """Should raise VatReturnNotFoundError."""
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)
        data = VatAdjustmentCreate(box_number=1, amount=1000, reason="Test")

        with pytest.raises(VatReturnNotFoundError) as exc_info:
            await VatService.add_adjustment(db, uuid.uuid4(), data)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_audit_nonexistent_return(self) -> None:
        """Should raise VatReturnNotFoundError."""
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        with pytest.raises(VatReturnNotFoundError) as exc_info:
            await VatService.get_audit_trail(db, uuid.uuid4())
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_flat_rate_missing_percentage(self) -> None:
        """Should raise VatFlatRateMissingError."""
        db = AsyncMock()

        with pytest.raises(VatFlatRateMissingError) as exc_info:
            await VatService.create_period(
                db,
                VatPeriodCreate(
                    start_date=date(2026, 4, 1),
                    end_date=date(2026, 6, 30),
                    scheme="flat_rate",
                ),
            )
        assert exc_info.value.status_code == 422


# ======================================================================
# Multiple transactions with VAT rates
# ======================================================================


class TestMultipleTransactions:
    """Test aggregation of multiple transactions with different VAT rates."""

    @pytest.mark.asyncio
    async def test_mixed_vat_rates(self) -> None:
        """Transactions with 20%, 5%, 0%, and exempt VAT should be handled correctly."""
        period = _make_period(scheme="standard")

        # 20% output
        txn1 = _make_transaction(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 5, 1),
            output_vat=4000,
            output_net=20000,
            input_vat=0,
            input_net=0,
            reference="JE-2026-0020",
            description="20% sale",
        )
        txn1.postings[0].vat_lines[0].vat_rate = "20%"

        # 5% output
        txn2 = _make_transaction(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 5, 10),
            output_vat=500,
            output_net=10000,
            input_vat=0,
            input_net=0,
            reference="JE-2026-0021",
            description="5% sale",
        )
        txn2.postings[0].vat_lines[0].vat_rate = "5%"

        # 20% input
        txn3 = _make_transaction(
            txn_id=uuid.uuid4(),
            effective_date=date(2026, 5, 15),
            output_vat=0,
            output_net=0,
            input_vat=2000,
            input_net=10000,
            reference="JE-2026-0022",
            description="20% purchase",
        )
        # Remove output posting, keep only input
        txn3.postings = [txn3.postings[1]]
        txn3.postings[0].vat_lines[0].vat_rate = "20%"

        all_txns = [txn1, txn2, txn3]

        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = _make_refresh()

        async def mock_get(model, pk, **kwargs):
            if hasattr(model, "__tablename__") and model.__tablename__ == "vat_periods":
                return period
            return None

        db.get = mock_get
        db.execute = AsyncMock(return_value=_mock_result(all_txns))

        result = await VatService.calculate_return(db, period.id)
        vr = result.vat_return

        # Output VAT: 4000 (20%) + 500 (5%) = 4500
        assert vr.box1 == 4500
        # Input VAT: 2000
        assert vr.box4 == 2000
        # Net output sales: 20000 + 10000 = 30000
        assert vr.box6 == 30000
        # Net input purchases: 10000
        assert vr.box7 == 10000
        # Box 5: 4500 - 2000 = 2500
        assert vr.box5 == 2500
