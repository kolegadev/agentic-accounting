"""Unit tests for ReconciliationService with mocked DB session."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.bank_account import BankAccount, BankTransaction
from src.models.reconciliation import ReconciliationMatch, ReconciliationSession
from src.models.transaction import Transaction
from src.services.reconciliation_service import (
    BankAccountNotFoundError,
    BankTransactionAlreadyMatchedError,
    BankTransactionNotFoundError,
    ReconciliationService,
    ReconciliationServiceError,
    SessionClosedError,
    SessionNotFoundError,
    TransactionNotFoundError,
)
from src.validators.reconciliation import (
    CreateAndMatchRequest,
    MatchRequest,
    StartReconciliation,
)

NOW = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_db() -> AsyncMock:
    """Return an AsyncMock that behaves like an async SQLAlchemy session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def sample_bank_account() -> BankAccount:
    """Create a BankAccount ORM instance."""
    return BankAccount(
        id=uuid.uuid4(),
        name="Test Business Account",
        sort_code="20-00-00",
        account_number="12345678",
        currency="GBP",
        opening_balance=100000,
        current_balance=100000,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def sample_bank_transaction(sample_bank_account: BankAccount) -> BankTransaction:
    """Create an unreconciled BankTransaction."""
    return BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=sample_bank_account.id,
        date=date(2026, 6, 15),
        description="Customer Payment",
        amount=250000,  # £2,500 credit
        reference="REF001",
        type="CR",
        status="imported",
        created_at=NOW,
    )


@pytest.fixture
def sample_bank_transaction_debit(sample_bank_account: BankAccount) -> BankTransaction:
    """Create an unreconciled debit BankTransaction."""
    return BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=sample_bank_account.id,
        date=date(2026, 6, 10),
        description="Office Supplies",
        amount=-5000,  # £50 debit
        reference="REF002",
        type="DD",
        status="imported",
        created_at=NOW,
    )


@pytest.fixture
def sample_transaction() -> Transaction:
    """Create a ledger Transaction."""
    return Transaction(
        id=uuid.uuid4(),
        reference="JE-2026-0001",
        description="Customer Invoice Payment",
        currency="GBP",
        status="posted",
        total_amount=250000,
        effective_date=date(2026, 6, 15),
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def sample_transaction2() -> Transaction:
    """Create a second ledger Transaction."""
    return Transaction(
        id=uuid.uuid4(),
        reference="JE-2026-0002",
        description="Another Payment",
        currency="GBP",
        status="posted",
        total_amount=100000,
        effective_date=date(2026, 6, 15),
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture
def sample_session(sample_bank_account: BankAccount) -> ReconciliationSession:
    """Create an open ReconciliationSession."""
    return ReconciliationSession(
        id=uuid.uuid4(),
        bank_account_id=sample_bank_account.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        opening_balance=100000,
        closing_balance=350000,
        status="open",
        matched_count=0,
        unmatched_count=5,
        total_bank_lines=5,
        created_at=NOW,
    )


# ---------------------------------------------------------------------------
# Helper: mock result
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


# ======================================================================
# start_session
# ======================================================================


@pytest.mark.asyncio
async def test_start_session_success(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should start a new reconciliation session successfully."""
    now = datetime(2026, 6, 27, 12, 0, 0)

    async def mock_refresh(obj) -> None:
        if isinstance(obj, ReconciliationSession):
            if obj.id is None:
                obj.id = uuid.uuid4()
            if obj.created_at is None:
                obj.created_at = now

    mock_db.refresh = mock_refresh

    # bank account lookup → count total → count unmatched
    mock_db.execute.side_effect = [
        _mock_result(sample_bank_account),
        _mock_count_result(10),
        _mock_count_result(8),
    ]

    data = StartReconciliation(
        bank_account_id=sample_bank_account.id,
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        opening_balance=100000,
        closing_balance=350000,
    )

    result = await ReconciliationService.start_session(mock_db, data)

    assert result.bank_account_id == sample_bank_account.id
    assert result.status == "open"
    assert result.total_bank_lines == 10
    assert result.unmatched_count == 8
    assert result.matched_count == 0
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_start_session_bank_account_not_found(mock_db: AsyncMock) -> None:
    """Should raise BankAccountNotFoundError."""
    mock_db.execute.return_value = _mock_result(None)

    data = StartReconciliation(
        bank_account_id=uuid.uuid4(),
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        opening_balance=0,
        closing_balance=0,
    )

    with pytest.raises(BankAccountNotFoundError) as exc_info:
        await ReconciliationService.start_session(mock_db, data)
    assert exc_info.value.status_code == 404


# ======================================================================
# match_one_to_one
# ======================================================================


@pytest.mark.asyncio
async def test_match_one_to_one_success(
    mock_db: AsyncMock,
    sample_session: ReconciliationSession,
    sample_bank_transaction: BankTransaction,
    sample_transaction: Transaction,
) -> None:
    """Should create a one-to-one match successfully."""
    match_id = uuid.uuid4()

    async def mock_refresh(obj) -> None:
        if isinstance(obj, ReconciliationMatch):
            if obj.id is None:
                obj.id = match_id
            if obj.created_at is None:
                obj.created_at = NOW

    mock_db.refresh = mock_refresh

    # 1. load session; 2. load bank tx; 3. load ledger tx
    # + _update_session_counts: 4. matched count; 5. unmatched count
    mock_db.execute.side_effect = [
        _mock_result(sample_session),
        _mock_result(sample_bank_transaction),
        _mock_result(sample_transaction),
        _mock_count_result(1),
        _mock_count_result(0),
    ]

    result = await ReconciliationService.match_one_to_one(
        mock_db,
        session_id=sample_session.id,
        bank_transaction_id=sample_bank_transaction.id,
        transaction_id=sample_transaction.id,
    )

    assert result.match_type == "one_to_one"
    assert result.amount_difference == 0
    assert result.bank_transaction_id == sample_bank_transaction.id
    assert result.transaction_id == sample_transaction.id
    assert sample_bank_transaction.status == "reconciled"
    mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_match_one_to_one_partial_amount_difference(
    mock_db: AsyncMock,
    sample_session: ReconciliationSession,
    sample_bank_transaction: BankTransaction,
    sample_transaction: Transaction,
) -> None:
    """Should detect amount difference and mark as partial match."""
    sample_transaction.total_amount = 240000  # £2,400 vs £2,500

    match_id = uuid.uuid4()
    async def mock_refresh(obj) -> None:
        if isinstance(obj, ReconciliationMatch):
            if obj.id is None:
                obj.id = match_id
            if obj.created_at is None:
                obj.created_at = NOW
    mock_db.refresh = mock_refresh

    mock_db.execute.side_effect = [
        _mock_result(sample_session),
        _mock_result(sample_bank_transaction),
        _mock_result(sample_transaction),
        _mock_count_result(1),
        _mock_count_result(0),
    ]

    result = await ReconciliationService.match_one_to_one(
        mock_db,
        session_id=sample_session.id,
        bank_transaction_id=sample_bank_transaction.id,
        transaction_id=sample_transaction.id,
    )

    assert result.match_type == "partial"
    assert result.amount_difference == 10000  # £100 difference


@pytest.mark.asyncio
async def test_match_one_to_one_session_not_found(mock_db: AsyncMock) -> None:
    """Should raise SessionNotFoundError."""
    mock_db.execute.return_value = _mock_result(None)

    with pytest.raises(SessionNotFoundError):
        await ReconciliationService.match_one_to_one(
            mock_db,
            session_id=uuid.uuid4(),
            bank_transaction_id=uuid.uuid4(),
            transaction_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_match_one_to_one_session_closed(
    mock_db: AsyncMock,
    sample_session: ReconciliationSession,
) -> None:
    """Should raise SessionClosedError."""
    sample_session.status = "closed"
    mock_db.execute.return_value = _mock_result(sample_session)

    with pytest.raises(SessionClosedError):
        await ReconciliationService.match_one_to_one(
            mock_db,
            session_id=sample_session.id,
            bank_transaction_id=uuid.uuid4(),
            transaction_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_match_one_to_one_bank_tx_already_reconciled(
    mock_db: AsyncMock,
    sample_session: ReconciliationSession,
    sample_bank_transaction: BankTransaction,
) -> None:
    """Should raise BankTransactionAlreadyMatchedError."""
    sample_bank_transaction.status = "reconciled"

    mock_db.execute.side_effect = [
        _mock_result(sample_session),
        _mock_result(sample_bank_transaction),
    ]

    with pytest.raises(BankTransactionAlreadyMatchedError):
        await ReconciliationService.match_one_to_one(
            mock_db,
            session_id=sample_session.id,
            bank_transaction_id=sample_bank_transaction.id,
            transaction_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_match_one_to_one_ledger_tx_not_found(
    mock_db: AsyncMock,
    sample_session: ReconciliationSession,
    sample_bank_transaction: BankTransaction,
) -> None:
    """Should raise TransactionNotFoundError."""
    mock_db.execute.side_effect = [
        _mock_result(sample_session),
        _mock_result(sample_bank_transaction),
        _mock_result(None),
    ]

    with pytest.raises(TransactionNotFoundError):
        await ReconciliationService.match_one_to_one(
            mock_db,
            session_id=sample_session.id,
            bank_transaction_id=sample_bank_transaction.id,
            transaction_id=uuid.uuid4(),
        )


# ======================================================================
# match_one_to_many
# ======================================================================


@pytest.mark.asyncio
async def test_match_one_to_many_success(
    mock_db: AsyncMock,
    sample_session: ReconciliationSession,
    sample_bank_transaction: BankTransaction,
    sample_transaction: Transaction,
    sample_transaction2: Transaction,
) -> None:
    """Should create one-to-many match with multiple ledger transactions."""
    # Total: 250000 + 100000 = 350000, bank has 350000 → exact match
    sample_bank_transaction.amount = 350000

    ids = [uuid.uuid4(), uuid.uuid4()]
    _id_iter = iter(ids)
    async def mock_refresh(obj) -> None:
        if isinstance(obj, ReconciliationMatch):
            if obj.id is None:
                obj.id = next(_id_iter)
            if obj.created_at is None:
                obj.created_at = NOW
    mock_db.refresh = mock_refresh

    # 1. session; 2. bank tx; 3. ledger txs
    # + _update_session_counts: 4. matched count; 5. unmatched count
    mock_db.execute.side_effect = [
        _mock_result(sample_session),
        _mock_result(sample_bank_transaction),
        _mock_result([sample_transaction, sample_transaction2]),
        _mock_count_result(2),
        _mock_count_result(0),
    ]

    results = await ReconciliationService.match_one_to_many(
        mock_db,
        session_id=sample_session.id,
        bank_transaction_id=sample_bank_transaction.id,
        transaction_ids=[sample_transaction.id, sample_transaction2.id],
    )

    assert len(results) == 2
    assert results[0].match_type == "one_to_many"
    assert results[0].amount_difference == 0
    assert results[1].match_type == "one_to_many"
    assert sample_bank_transaction.status == "reconciled"


@pytest.mark.asyncio
async def test_match_one_to_many_partial_amount_diff(
    mock_db: AsyncMock,
    sample_session: ReconciliationSession,
    sample_bank_transaction: BankTransaction,
    sample_transaction: Transaction,
    sample_transaction2: Transaction,
) -> None:
    """Should detect partial when total doesn't match bank amount."""
    # Bank: £2,500 but ledger total: £2,500 + £1,000 = £3,500
    sample_bank_transaction.amount = 250000

    ids = [uuid.uuid4(), uuid.uuid4()]
    _id_iter = iter(ids)
    async def mock_refresh(obj) -> None:
        if isinstance(obj, ReconciliationMatch):
            if obj.id is None:
                obj.id = next(_id_iter)
            if obj.created_at is None:
                obj.created_at = NOW
    mock_db.refresh = mock_refresh

    mock_db.execute.side_effect = [
        _mock_result(sample_session),
        _mock_result(sample_bank_transaction),
        _mock_result([sample_transaction, sample_transaction2]),
        _mock_count_result(2),
        _mock_count_result(0),
    ]

    results = await ReconciliationService.match_one_to_many(
        mock_db,
        session_id=sample_session.id,
        bank_transaction_id=sample_bank_transaction.id,
        transaction_ids=[sample_transaction.id, sample_transaction2.id],
    )

    assert len(results) == 2
    assert results[0].match_type == "partial"
    assert results[0].amount_difference == 100000  # £1,000 difference


@pytest.mark.asyncio
async def test_match_one_to_many_ledger_tx_not_found(
    mock_db: AsyncMock,
    sample_session: ReconciliationSession,
    sample_bank_transaction: BankTransaction,
) -> None:
    """Should raise TransactionNotFoundError for missing ledger tx."""
    bad_id = uuid.uuid4()

    mock_db.execute.side_effect = [
        _mock_result(sample_session),
        _mock_result(sample_bank_transaction),
        _mock_result([]),  # No matching transactions
    ]

    with pytest.raises(TransactionNotFoundError):
        await ReconciliationService.match_one_to_many(
            mock_db,
            session_id=sample_session.id,
            bank_transaction_id=sample_bank_transaction.id,
            transaction_ids=[bad_id],
        )


# ======================================================================
# create_and_match
# ======================================================================


@pytest.mark.asyncio
async def test_create_and_match_success(
    mock_db: AsyncMock,
    sample_session: ReconciliationSession,
    sample_bank_transaction_debit: BankTransaction,
) -> None:
    """Should create a new transaction and match it."""
    now = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)
    match_id = uuid.uuid4()

    async def mock_refresh(obj) -> None:
        if isinstance(obj, ReconciliationMatch):
            if obj.id is None:
                obj.id = match_id
            if obj.created_at is None:
                obj.created_at = now

    mock_db.refresh = mock_refresh

    data = CreateAndMatchRequest(
        bank_transaction_id=sample_bank_transaction_debit.id,
        description="Office Supplies Payment",
        debit_account_id=uuid.uuid4(),
        credit_account_id=uuid.uuid4(),
        amount=5000,
    )

    # Mock TransactionService.create_transaction and post_transaction
    created_tx = Transaction(
        id=uuid.uuid4(),
        reference="JE-2026-0005",
        description="Office Supplies Payment",
        currency="GBP",
        status="posted",
        total_amount=5000,
        effective_date=date(2026, 6, 10),
        created_at=now,
        updated_at=now,
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
            mock_db.execute.side_effect = [
                _mock_result(sample_session),
                _mock_result(sample_bank_transaction_debit),
                _mock_count_result(1),
                _mock_count_result(0),
            ]

            result = await ReconciliationService.create_and_match(
                mock_db,
                session_id=sample_session.id,
                data=data,
            )

            assert result.match_type == "new_entry"
            assert result.amount_difference == 0
            assert result.transaction_id == created_tx.id
            assert mock_create.called
            assert mock_post.called
            assert sample_bank_transaction_debit.status == "reconciled"


@pytest.mark.asyncio
async def test_create_and_match_bank_tx_already_reconciled(
    mock_db: AsyncMock,
    sample_session: ReconciliationSession,
    sample_bank_transaction_debit: BankTransaction,
) -> None:
    """Should raise when bank tx already reconciled."""
    sample_bank_transaction_debit.status = "reconciled"

    mock_db.execute.side_effect = [
        _mock_result(sample_session),
        _mock_result(sample_bank_transaction_debit),
    ]

    data = CreateAndMatchRequest(
        bank_transaction_id=sample_bank_transaction_debit.id,
        description="Test",
        debit_account_id=uuid.uuid4(),
        credit_account_id=uuid.uuid4(),
        amount=5000,
    )

    with pytest.raises(BankTransactionAlreadyMatchedError):
        await ReconciliationService.create_and_match(mock_db, sample_session.id, data)


# ======================================================================
# get_session_status
# ======================================================================


@pytest.mark.asyncio
async def test_get_session_status_success(
    mock_db: AsyncMock,
    sample_session: ReconciliationSession,
) -> None:
    """Should return session status with updated counts."""
    # session lookup; matched count; unmatched count
    mock_db.execute.side_effect = [
        _mock_result(sample_session),
        _mock_count_result(3),
        _mock_count_result(2),
    ]

    result = await ReconciliationService.get_session_status(mock_db, sample_session.id)

    assert result.id == sample_session.id
    assert result.status == "open"


@pytest.mark.asyncio
async def test_get_session_status_not_found(mock_db: AsyncMock) -> None:
    """Should raise SessionNotFoundError."""
    mock_db.execute.return_value = _mock_result(None)

    with pytest.raises(SessionNotFoundError):
        await ReconciliationService.get_session_status(mock_db, uuid.uuid4())


# ======================================================================
# generate_report
# ======================================================================


@pytest.mark.asyncio
async def test_generate_report_success(
    mock_db: AsyncMock,
    sample_session: ReconciliationSession,
) -> None:
    """Should generate a reconciliation report."""
    # session; matched count; unmatched count; matches; matched amount
    mock_db.execute.side_effect = [
        _mock_result(sample_session),
        _mock_count_result(3),
        _mock_count_result(2),
        _mock_result([]),
        _mock_count_result(250000),
    ]

    report = await ReconciliationService.generate_report(mock_db, sample_session.id)

    assert report.opening_balance == 100000
    assert report.closing_balance == 350000
    assert report.matched_count == 3
    assert report.unmatched_count == 2
    assert report.total_bank_lines == 5
    assert report.matched_net_amount == 250000
    # difference = opening + matched_net - closing = 100000 + 250000 - 350000 = 0
    assert report.difference == 0


@pytest.mark.asyncio
async def test_generate_report_with_difference(
    mock_db: AsyncMock,
    sample_session: ReconciliationSession,
) -> None:
    """Should show difference when bank amounts don't reconcile."""
    # opening=100000, matched_net=200000, closing=350000 → diff = -50000
    mock_db.execute.side_effect = [
        _mock_result(sample_session),
        _mock_count_result(3),
        _mock_count_result(2),
        _mock_result([]),
        _mock_count_result(200000),
    ]

    report = await ReconciliationService.generate_report(mock_db, sample_session.id)

    assert report.matched_net_amount == 200000
    assert report.difference == -50000


@pytest.mark.asyncio
async def test_generate_report_session_not_found(mock_db: AsyncMock) -> None:
    """Should raise SessionNotFoundError."""
    mock_db.execute.return_value = _mock_result(None)

    with pytest.raises(SessionNotFoundError):
        await ReconciliationService.generate_report(mock_db, uuid.uuid4())


# ======================================================================
# close_session
# ======================================================================


@pytest.mark.asyncio
async def test_close_session_success(
    mock_db: AsyncMock,
    sample_session: ReconciliationSession,
) -> None:
    """Should close a session successfully."""
    # session; matched count; unmatched count
    mock_db.execute.side_effect = [
        _mock_result(sample_session),
        _mock_count_result(3),
        _mock_count_result(2),
    ]

    result = await ReconciliationService.close_session(mock_db, sample_session.id)

    assert result.status == "closed"
    assert sample_session.status == "closed"
    assert sample_session.closed_at is not None
    mock_db.commit.assert_called()


@pytest.mark.asyncio
async def test_close_session_already_closed(
    mock_db: AsyncMock,
    sample_session: ReconciliationSession,
) -> None:
    """Should raise SessionClosedError if already closed."""
    sample_session.status = "closed"
    mock_db.execute.return_value = _mock_result(sample_session)

    with pytest.raises(SessionClosedError):
        await ReconciliationService.close_session(mock_db, sample_session.id)


# ======================================================================
# Edge cases
# ======================================================================


@pytest.mark.asyncio
async def test_match_debit_bank_transaction(
    mock_db: AsyncMock,
    sample_session: ReconciliationSession,
    sample_bank_transaction_debit: BankTransaction,
    sample_transaction: Transaction,
) -> None:
    """Should handle matching a debit (negative amount) bank transaction."""
    sample_transaction.total_amount = 5000
    match_id = uuid.uuid4()

    async def mock_refresh(obj) -> None:
        if isinstance(obj, ReconciliationMatch):
            if obj.id is None:
                obj.id = match_id
            if obj.created_at is None:
                obj.created_at = NOW

    mock_db.refresh = mock_refresh

    mock_db.execute.side_effect = [
        _mock_result(sample_session),
        _mock_result(sample_bank_transaction_debit),
        _mock_result(sample_transaction),
        _mock_count_result(1),
        _mock_count_result(0),
    ]

    result = await ReconciliationService.match_one_to_one(
        mock_db,
        session_id=sample_session.id,
        bank_transaction_id=sample_bank_transaction_debit.id,
        transaction_id=sample_transaction.id,
    )

    assert result.match_type == "one_to_one"
    assert result.amount_difference == 0


@pytest.mark.asyncio
async def test_start_session_zero_unmatched(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should handle a date range with no bank transactions."""
    async def mock_refresh(obj) -> None:
        if isinstance(obj, ReconciliationSession):
            obj.id = obj.id or uuid.uuid4()
            obj.created_at = obj.created_at or NOW

    mock_db.refresh = mock_refresh

    mock_db.execute.side_effect = [
        _mock_result(sample_bank_account),
        _mock_count_result(0),
        _mock_count_result(0),
    ]

    data = StartReconciliation(
        bank_account_id=sample_bank_account.id,
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 31),
        opening_balance=100000,
        closing_balance=100000,
    )

    result = await ReconciliationService.start_session(mock_db, data)

    assert result.total_bank_lines == 0
    assert result.unmatched_count == 0
    assert result.matched_count == 0
