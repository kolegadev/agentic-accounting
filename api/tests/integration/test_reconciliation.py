"""Integration tests for Manual Bank Reconciliation workflow.

Uses mocked DB (no real database required) but tests the full
start session → match → report → close workflow.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.bank_account import BankAccount, BankTransaction
from src.models.reconciliation import ReconciliationMatch, ReconciliationSession
from src.models.transaction import Transaction
from src.services.reconciliation_service import (
    ReconciliationService,
    ReconciliationServiceError,
    SessionNotFoundError,
)
from src.validators.reconciliation import (
    CreateAndMatchRequest,
    MatchRequest,
    StartReconciliation,
)

NOW = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_result(return_value):
    """Create a MagicMock that mimics an AsyncResult."""
    m = MagicMock()
    m.scalar_one_or_none.return_value = return_value
    m.scalars.return_value.all.return_value = (
        return_value if isinstance(return_value, list) else [return_value]
    )
    m.scalar_one.return_value = (
        1
        if return_value is None
        else (len(return_value) if isinstance(return_value, list) else 1)
    )
    return m


def _mock_count_result(count: int) -> MagicMock:
    """Create a result returning a scalar count."""
    m = MagicMock()
    m.scalar_one.return_value = count
    return m


# ---------------------------------------------------------------------------
# Full workflow: start → match 1:1 → match 1:many → create&match → report → close
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_reconciliation_workflow() -> None:
    """End-to-end reconciliation workflow: start, match, report, close."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    bank_account = BankAccount(
        id=uuid.uuid4(),
        name="Test Business",
        sort_code="20-00-00",
        account_number="12345678",
        currency="GBP",
        opening_balance=0,
        current_balance=0,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

    async def _mock_refresh_session(session: ReconciliationSession) -> None:
        if session.id is None:
            session.id = uuid.uuid4()
        if session.created_at is None:
            session.created_at = NOW

    async def _mock_refresh_match(match: ReconciliationMatch) -> None:
        pass

    # 1. START SESSION
    db.refresh = _mock_refresh_session

    db.execute.side_effect = [
        _mock_result(bank_account),  # bank account lookup
        _mock_count_result(10),      # total bank lines
        _mock_count_result(8),       # unmatched count
    ]

    data = StartReconciliation(
        bank_account_id=bank_account.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        opening_balance=0,
        closing_balance=500000,
    )

    session_res = await ReconciliationService.start_session(db, data)

    assert session_res.status == "open"
    assert session_res.total_bank_lines == 10
    assert session_res.unmatched_count == 8
    assert session_res.matched_count == 0

    session_id = session_res.id

    # 2. MATCH ONE-TO-ONE
    db.reset_mock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    _match_id_iter = iter([uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()])
    async def _refresh_match(obj) -> None:
        if isinstance(obj, ReconciliationMatch):
            if obj.id is None:
                obj.id = next(_match_id_iter)
            if obj.created_at is None:
                obj.created_at = NOW
    db.refresh = _refresh_match

    bank_tx1 = BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=bank_account.id,
        date=date(2026, 6, 15),
        description="Customer Payment",
        amount=250000,
        reference="REF001",
        type="CR",
        status="imported",
        created_at=NOW,
    )

    ledger_tx1 = Transaction(
        id=uuid.uuid4(),
        reference="JE-2026-0001",
        description="Invoice Payment",
        currency="GBP",
        status="posted",
        total_amount=250000,
        effective_date=date(2026, 6, 15),
        created_at=NOW,
        updated_at=NOW,
    )

    session = ReconciliationSession(
        id=session_id,
        bank_account_id=bank_account.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        opening_balance=0,
        closing_balance=500000,
        status="open",
        matched_count=0,
        unmatched_count=8,
        total_bank_lines=10,
        created_at=NOW,
    )

    # session; bank tx; ledger tx; + _update_session_counts: matched count; unmatched count
    db.execute.side_effect = [
        _mock_result(session),
        _mock_result(bank_tx1),
        _mock_result(ledger_tx1),
        _mock_count_result(1),
        _mock_count_result(7),
    ]

    match_res = await ReconciliationService.match_one_to_one(
        db,
        session_id=session_id,
        bank_transaction_id=bank_tx1.id,
        transaction_id=ledger_tx1.id,
    )

    assert match_res.match_type == "one_to_one"
    assert match_res.amount_difference == 0
    assert bank_tx1.status == "reconciled"

    # 3. MATCH ONE-TO-MANY
    db.reset_mock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    _match_id_iter2 = iter([uuid.uuid4(), uuid.uuid4()])
    async def _refresh_match2(obj) -> None:
        if isinstance(obj, ReconciliationMatch):
            if obj.id is None:
                obj.id = next(_match_id_iter2)
            if obj.created_at is None:
                obj.created_at = NOW
    db.refresh = _refresh_match2

    bank_tx2 = BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=bank_account.id,
        date=date(2026, 6, 20),
        description="Bulk Deposit",
        amount=200000,
        reference="REF002",
        type="CR",
        status="imported",
        created_at=NOW,
    )

    ledger_tx2 = Transaction(
        id=uuid.uuid4(),
        reference="JE-2026-0002",
        description="Invoice 1",
        currency="GBP",
        status="posted",
        total_amount=120000,
        effective_date=date(2026, 6, 20),
        created_at=NOW,
        updated_at=NOW,
    )

    ledger_tx3 = Transaction(
        id=uuid.uuid4(),
        reference="JE-2026-0003",
        description="Invoice 2",
        currency="GBP",
        status="posted",
        total_amount=80000,
        effective_date=date(2026, 6, 20),
        created_at=NOW,
        updated_at=NOW,
    )

    # session; bank tx; ledger txs; + _update_session_counts: matched count; unmatched count
    db.execute.side_effect = [
        _mock_result(session),
        _mock_result(bank_tx2),
        _mock_result([ledger_tx2, ledger_tx3]),
        _mock_count_result(3),
        _mock_count_result(5),
    ]

    many_results = await ReconciliationService.match_one_to_many(
        db,
        session_id=session_id,
        bank_transaction_id=bank_tx2.id,
        transaction_ids=[ledger_tx2.id, ledger_tx3.id],
    )

    assert len(many_results) == 2
    assert many_results[0].match_type == "one_to_many"
    assert many_results[1].match_type == "one_to_many"
    assert bank_tx2.status == "reconciled"

    # 4. CREATE AND MATCH
    db.reset_mock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    async def _refresh_match3(obj) -> None:
        if isinstance(obj, ReconciliationMatch):
            if obj.id is None:
                obj.id = uuid.uuid4()
            if obj.created_at is None:
                obj.created_at = NOW
    db.refresh = _refresh_match3

    bank_tx3 = BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=bank_account.id,
        date=date(2026, 6, 10),
        description="Office Supplies",
        amount=-5000,
        reference="REF003",
        type="DD",
        status="imported",
        created_at=NOW,
    )

    created_tx = Transaction(
        id=uuid.uuid4(),
        reference="JE-2026-0005",
        description="Office Supplies Payment",
        currency="GBP",
        status="posted",
        total_amount=5000,
        effective_date=date(2026, 6, 10),
        created_at=NOW,
        updated_at=NOW,
    )

    cam_data = CreateAndMatchRequest(
        bank_transaction_id=bank_tx3.id,
        description="Office Supplies Payment",
        debit_account_id=uuid.uuid4(),
        credit_account_id=uuid.uuid4(),
        amount=5000,
    )

    with patch(
        "src.services.reconciliation_service.TransactionService.create_transaction",
        new_callable=AsyncMock,
    ) as mock_create:
        mock_create.return_value = created_tx
        with patch(
            "src.services.reconciliation_service.TransactionService.post_transaction",
            new_callable=AsyncMock,
        ) as mock_post:
            mock_post.return_value = created_tx

            # session; bank tx; + _update_session_counts: matched count; unmatched count
            db.execute.side_effect = [
                _mock_result(session),
                _mock_result(bank_tx3),
                _mock_count_result(4),
                _mock_count_result(4),
            ]

            cam_res = await ReconciliationService.create_and_match(
                db,
                session_id=session_id,
                data=cam_data,
            )

            assert cam_res.match_type == "new_entry"
            assert cam_res.amount_difference == 0
            assert cam_res.transaction_id == created_tx.id
            assert bank_tx3.status == "reconciled"

    # 5. GENERATE REPORT
    db.reset_mock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    session_for_report = ReconciliationSession(
        id=session_id,
        bank_account_id=bank_account.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        opening_balance=0,
        closing_balance=500000,
        status="open",
        matched_count=4,
        unmatched_count=4,
        total_bank_lines=10,
        created_at=NOW,
    )

    # session; matched count; unmatched count; matches; matched amount
    db.execute.side_effect = [
        _mock_result(session_for_report),
        _mock_count_result(4),
        _mock_count_result(4),
        _mock_result([]),
        _mock_count_result(455000),  # 250000 + 200000 + 5000
    ]

    report = await ReconciliationService.generate_report(db, session_id)

    assert report.opening_balance == 0
    assert report.closing_balance == 500000
    assert report.matched_count == 4
    assert report.unmatched_count == 4
    assert report.matched_net_amount == 455000
    # difference = 0 + 455000 - 500000 = -45000
    assert report.difference == -45000

    # 6. CLOSE SESSION
    db.reset_mock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    session_for_close = ReconciliationSession(
        id=session_id,
        bank_account_id=bank_account.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        opening_balance=0,
        closing_balance=500000,
        status="open",
        matched_count=4,
        unmatched_count=4,
        total_bank_lines=10,
        created_at=NOW,
    )

    # session; matched count; unmatched count
    db.execute.side_effect = [
        _mock_result(session_for_close),
        _mock_count_result(4),
        _mock_count_result(4),
    ]

    closed_res = await ReconciliationService.close_session(db, session_id)

    assert closed_res.status == "closed"
    assert session_for_close.status == "closed"
    assert session_for_close.closed_at is not None

    # 7. VERIFY CAN'T MATCH ON CLOSED SESSION
    db.reset_mock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    # Just one call needed - _get_open_session will find the closed session
    db.execute.side_effect = [_mock_result(session_for_close)]

    from src.services.reconciliation_service import SessionClosedError

    with pytest.raises(SessionClosedError):
        await ReconciliationService.match_one_to_one(
            db,
            session_id=session_id,
            bank_transaction_id=bank_tx1.id,
            transaction_id=ledger_tx1.id,
        )


# ---------------------------------------------------------------------------
# Partial match flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_partial_match_with_amount_difference() -> None:
    """Should handle partial matches where bank and ledger amounts differ."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    session = ReconciliationSession(
        id=uuid.uuid4(),
        bank_account_id=uuid.uuid4(),
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        opening_balance=0,
        closing_balance=0,
        status="open",
        matched_count=0,
        unmatched_count=5,
        total_bank_lines=5,
        created_at=NOW,
    )

    # Bank shows £100 but ledger only has £95 (e.g., bank fees deducted)
    bank_tx = BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=session.bank_account_id,
        date=date(2026, 6, 15),
        description="Payment with Fees",
        amount=10000,  # £100
        reference="REF001",
        type="CR",
        status="imported",
        created_at=NOW,
    )

    ledger_tx = Transaction(
        id=uuid.uuid4(),
        reference="JE-2026-0100",
        description="Payment",
        currency="GBP",
        status="posted",
        total_amount=9500,  # £95
        effective_date=date(2026, 6, 15),
        created_at=NOW,
        updated_at=NOW,
    )

    # session; bank tx; ledger tx; + _update_session_counts: matched count; unmatched count
    db.execute.side_effect = [
        _mock_result(session),
        _mock_result(bank_tx),
        _mock_result(ledger_tx),
        _mock_count_result(1),
        _mock_count_result(4),
    ]

    match_id = uuid.uuid4()

    async def _refresh_match(obj) -> None:
        if isinstance(obj, ReconciliationMatch):
            if obj.id is None:
                obj.id = match_id
            if obj.created_at is None:
                obj.created_at = NOW

    db.refresh = _refresh_match

    result = await ReconciliationService.match_one_to_one(
        db,
        session_id=session.id,
        bank_transaction_id=bank_tx.id,
        transaction_id=ledger_tx.id,
    )

    assert result.match_type == "partial"
    assert result.amount_difference == 500  # £5 difference in pence
    assert bank_tx.status == "reconciled"


# ---------------------------------------------------------------------------
# Multiple sessions isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_sessions_isolation() -> None:
    """Transactions matched in one session should not affect another."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    account = BankAccount(
        id=uuid.uuid4(),
        name="Test Business",
        sort_code="20-00-00",
        account_number="12345678",
        currency="GBP",
        opening_balance=0,
        current_balance=0,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

    # Create two sessions for the same account
    async def _mock_refresh_session(rs: ReconciliationSession) -> None:
        if rs.id is None:
            rs.id = uuid.uuid4()
        if rs.created_at is None:
            rs.created_at = NOW

    db.refresh = _mock_refresh_session

    # Session 1: June
    db.execute.side_effect = [
        _mock_result(account),
        _mock_count_result(5),
        _mock_count_result(5),
    ]
    s1_data = StartReconciliation(
        bank_account_id=account.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        opening_balance=0,
        closing_balance=100000,
    )
    s1 = await ReconciliationService.start_session(db, s1_data)
    s1_id = s1.id

    # Session 2: July
    db.reset_mock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = _mock_refresh_session

    db.execute.side_effect = [
        _mock_result(account),
        _mock_count_result(3),
        _mock_count_result(3),
    ]
    s2_data = StartReconciliation(
        bank_account_id=account.id,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        opening_balance=100000,
        closing_balance=200000,
    )
    s2 = await ReconciliationService.start_session(db, s2_data)
    s2_id = s2.id

    assert s1_id != s2_id
    assert s1.opening_balance == 0
    assert s2.opening_balance == 100000


# ---------------------------------------------------------------------------
# Edge case: Zero balance reconciliation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_zero_balance_reconciliation() -> None:
    """Should handle reconciliation where all balances are zero."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    account = BankAccount(
        id=uuid.uuid4(),
        name="Dormant Account",
        sort_code="20-00-00",
        account_number="99999999",
        currency="GBP",
        opening_balance=0,
        current_balance=0,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

    async def _mock_refresh_session(rs: ReconciliationSession) -> None:
        if rs.id is None:
            rs.id = uuid.uuid4()
        if rs.created_at is None:
            rs.created_at = NOW

    db.refresh = _mock_refresh_session

    db.execute.side_effect = [
        _mock_result(account),
        _mock_count_result(0),
        _mock_count_result(0),
    ]

    data = StartReconciliation(
        bank_account_id=account.id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        opening_balance=0,
        closing_balance=0,
    )

    result = await ReconciliationService.start_session(db, data)

    assert result.status == "open"
    assert result.total_bank_lines == 0
    assert result.unmatched_count == 0
    assert result.opening_balance == 0
    assert result.closing_balance == 0
