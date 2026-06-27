"""Unit tests for OpenBankingService with mocked DB session."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.bank_service import BankAccountNotFoundError
from src.services.open_banking_service import (
    PROVIDERS,
    AccountNotConnectedError,
    AlreadyConnectedError,
    MockOpenBankingProvider,
    OpenBankingError,
    OpenBankingService,
    ProviderNotFoundError,
    _connections,
)
from src.validators.open_banking import (
    ConnectionResponse,
    ConnectionStatusResponse,
    ProviderResponse,
    SyncAllResponse,
    SyncResponse,
)
from src.models.bank_account import BankAccount


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_connections() -> None:
    """Clear the in-memory connections store between tests."""
    _connections.clear()
    yield
    _connections.clear()


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
    """Create a fully-populated BankAccount ORM instance."""
    now = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)
    return BankAccount(
        id=uuid.uuid4(),
        name="Test Business Account",
        sort_code="20-00-00",
        account_number="12345678",
        iban=None,
        currency="GBP",
        opening_balance=100000,
        current_balance=100000,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


# Helper: mock execute result
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


# ======================================================================
# list_providers
# ======================================================================


def test_list_providers() -> None:
    """Should list all available providers."""
    providers = OpenBankingService.list_providers()
    assert len(providers) == len(PROVIDERS)
    assert all(isinstance(p, ProviderResponse) for p in providers)

    # Check test provider is marked
    test_prov = next(p for p in providers if p.name == "test")
    assert test_prov.is_test is True

    # Check non-test providers
    truelayer = next(p for p in providers if p.name == "truelayer")
    assert truelayer.is_test is False
    assert truelayer.display_name == "TrueLayer"


# ======================================================================
# MockOpenBankingProvider
# ======================================================================


def test_generate_transactions_correct_count() -> None:
    """Should generate the requested number of transactions."""
    account_id = uuid.uuid4()
    from_date = date(2026, 6, 1)
    to_date = date(2026, 6, 27)

    txns = MockOpenBankingProvider.generate_transactions(
        bank_account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        count=10,
        opening_balance=500000,
    )

    assert len(txns) == 10


def test_generate_transactions_date_range() -> None:
    """All transactions should fall within the specified date range."""
    account_id = uuid.uuid4()
    from_date = date(2026, 6, 1)
    to_date = date(2026, 6, 27)

    txns = MockOpenBankingProvider.generate_transactions(
        bank_account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        count=20,
    )

    for tx in txns:
        assert from_date <= tx["date"] <= to_date


def test_generate_transactions_sorted_by_date() -> None:
    """Transactions should be returned sorted by date."""
    account_id = uuid.uuid4()
    from_date = date(2026, 1, 1)
    to_date = date(2026, 12, 31)

    txns = MockOpenBankingProvider.generate_transactions(
        bank_account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        count=30,
    )

    for i in range(len(txns) - 1):
        assert txns[i]["date"] <= txns[i + 1]["date"]


def test_generate_transactions_has_required_fields() -> None:
    """Each transaction should have all required fields."""
    account_id = uuid.uuid4()
    from_date = date(2026, 6, 1)
    to_date = date(2026, 6, 27)

    txns = MockOpenBankingProvider.generate_transactions(
        bank_account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        count=5,
    )

    for tx in txns:
        assert "date" in tx
        assert isinstance(tx["date"], date)
        assert "description" in tx
        assert isinstance(tx["description"], str)
        assert len(tx["description"]) > 0
        assert "amount" in tx
        assert isinstance(tx["amount"], int)
        assert "reference" in tx
        assert isinstance(tx["reference"], str)
        assert len(tx["reference"]) > 0
        assert "type" in tx
        assert tx["type"] in ("DEBIT", "CREDIT", "DD", "SO", "CP", "TRANSFER")
        assert "bank_detail" in tx
        assert "sort_code" in tx["bank_detail"]
        assert "account_number" in tx["bank_detail"]


def test_generate_transactions_mix_of_debits_and_credits() -> None:
    """Should generate a mix of debits and credits."""
    account_id = uuid.uuid4()
    from_date = date(2026, 1, 1)
    to_date = date(2026, 12, 31)

    txns = MockOpenBankingProvider.generate_transactions(
        bank_account_id=account_id,
        from_date=from_date,
        to_date=to_date,
        count=50,
    )

    credits = [t for t in txns if t["amount"] > 0]
    debits = [t for t in txns if t["amount"] < 0]

    # Should have at least some credits (30% probability, 50 sample = ~15 credits)
    assert len(credits) > 0
    assert len(debits) > 0


def test_generate_transactions_single_day() -> None:
    """Should handle a single-day date range."""
    account_id = uuid.uuid4()
    single_date = date(2026, 6, 27)

    txns = MockOpenBankingProvider.generate_transactions(
        bank_account_id=account_id,
        from_date=single_date,
        to_date=single_date,
        count=5,
    )

    assert len(txns) == 5
    for tx in txns:
        assert tx["date"] == single_date


# ======================================================================
# connect_account
# ======================================================================


@pytest.mark.asyncio
async def test_connect_account_success(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should connect a bank account successfully."""
    mock_db.execute.return_value = _mock_result(sample_bank_account)

    result = await OpenBankingService.connect_account(
        mock_db,
        bank_account_id=sample_bank_account.id,
        provider="test",
        credentials={},
    )

    assert isinstance(result, ConnectionResponse)
    assert result.bank_account_id == sample_bank_account.id
    assert result.provider == "test"
    assert result.status == "connected"
    assert result.connection_id is not None


@pytest.mark.asyncio
async def test_connect_account_provider_not_found(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should raise ProviderNotFoundError for invalid provider."""
    mock_db.execute.return_value = _mock_result(sample_bank_account)

    with pytest.raises(ProviderNotFoundError) as exc_info:
        await OpenBankingService.connect_account(
            mock_db,
            bank_account_id=sample_bank_account.id,
            provider="nonexistent",
            credentials={},
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_connect_account_bank_account_not_found(mock_db: AsyncMock) -> None:
    """Should raise BankAccountNotFoundError for missing account."""
    mock_db.execute.return_value = _mock_result(None)

    with pytest.raises(BankAccountNotFoundError) as exc_info:
        await OpenBankingService.connect_account(
            mock_db,
            bank_account_id=uuid.uuid4(),
            provider="test",
            credentials={},
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_connect_account_already_connected(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should raise AlreadyConnectedError if account is already connected."""
    mock_db.execute.return_value = _mock_result(sample_bank_account)

    # First connection
    await OpenBankingService.connect_account(
        mock_db,
        bank_account_id=sample_bank_account.id,
        provider="test",
        credentials={},
    )

    # Second connection should fail
    with pytest.raises(AlreadyConnectedError) as exc_info:
        await OpenBankingService.connect_account(
            mock_db,
            bank_account_id=sample_bank_account.id,
            provider="truelayer",
            credentials={},
        )
    assert exc_info.value.status_code == 409


# ======================================================================
# fetch_transactions
# ======================================================================


@pytest.mark.asyncio
async def test_fetch_transactions_success(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should fetch transactions successfully in test mode."""
    # Create connection first
    mock_db.execute.return_value = _mock_result(sample_bank_account)
    await OpenBankingService.connect_account(
        mock_db,
        bank_account_id=sample_bank_account.id,
        provider="test",
        credentials={},
    )

    # Now fetch - need account lookup + hash lookup
    mock_db.execute.side_effect = [
        _mock_result(sample_bank_account),  # account lookup
        _mock_result([]),  # existing hashes (empty)
    ]

    imported = await OpenBankingService.fetch_transactions(
        mock_db,
        bank_account_id=sample_bank_account.id,
        from_date=date(2026, 6, 1),
        to_date=date(2026, 6, 27),
    )

    assert imported > 0
    assert mock_db.add.call_count == imported
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_transactions_not_connected(
    mock_db: AsyncMock,
) -> None:
    """Should raise AccountNotConnectedError if not connected."""
    with pytest.raises(AccountNotConnectedError) as exc_info:
        await OpenBankingService.fetch_transactions(
            mock_db,
            bank_account_id=uuid.uuid4(),
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_fetch_transactions_default_date_range(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should default to last 30 days if no dates provided."""
    mock_db.execute.return_value = _mock_result(sample_bank_account)
    await OpenBankingService.connect_account(
        mock_db,
        bank_account_id=sample_bank_account.id,
        provider="test",
        credentials={},
    )

    mock_db.execute.side_effect = [
        _mock_result(sample_bank_account),
        _mock_result([]),
    ]

    imported = await OpenBankingService.fetch_transactions(
        mock_db,
        bank_account_id=sample_bank_account.id,
    )

    assert imported > 0


@pytest.mark.asyncio
async def test_fetch_transactions_updates_last_sync(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should update last_sync_at after fetch."""
    mock_db.execute.return_value = _mock_result(sample_bank_account)
    await OpenBankingService.connect_account(
        mock_db,
        bank_account_id=sample_bank_account.id,
        provider="test",
        credentials={},
    )

    mock_db.execute.side_effect = [
        _mock_result(sample_bank_account),
        _mock_result([]),
    ]

    await OpenBankingService.fetch_transactions(
        mock_db,
        bank_account_id=sample_bank_account.id,
    )

    conn = _connections[sample_bank_account.id]
    assert conn["last_sync_at"] is not None


# ======================================================================
# sync_all
# ======================================================================


@pytest.mark.asyncio
async def test_sync_all_multiple_accounts(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should sync all connected accounts."""
    # Create two separate bank accounts (use same fixture but different UUIDs)
    account1 = sample_bank_account
    account2 = BankAccount(
        id=uuid.uuid4(),
        name="Second Account",
        sort_code="40-00-00",
        account_number="87654321",
        iban=None,
        currency="GBP",
        opening_balance=200000,
        current_balance=200000,
        is_active=True,
        created_at=datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc),
    )

    # Connect both
    mock_db.execute.return_value = _mock_result(account1)
    await OpenBankingService.connect_account(
        mock_db,
        bank_account_id=account1.id,
        provider="test",
        credentials={},
    )

    # Need to handle different account lookups
    def side_effect(query):
        # This is tricky because of how execute returns. Use a simpler approach.
        pass

    # For sync_all: connect second, then fetch both
    mock_db.execute.reset_mock()
    mock_db.execute.side_effect = [
        _mock_result(account2),  # connect second account
        _mock_result(account1),  # fetch account1: account lookup
        _mock_result([]),        # fetch account1: hashes
        _mock_result(account2),  # fetch account2: account lookup
        _mock_result([]),        # fetch account2: hashes
    ]

    await OpenBankingService.connect_account(
        mock_db,
        bank_account_id=account2.id,
        provider="truelayer",
        credentials={},
    )

    mock_db.execute.reset_mock()
    mock_db.execute.side_effect = [
        _mock_result(account1),  # fetch account1: account lookup
        _mock_result([]),        # fetch account1: hashes
        _mock_result(account2),  # fetch account2: account lookup
        _mock_result([]),        # fetch account2: hashes
    ]

    result = await OpenBankingService.sync_all(mock_db)

    assert isinstance(result, SyncAllResponse)
    assert result.accounts_synced == 2
    assert result.total_imported > 0
    assert str(account1.id) in result.results
    assert str(account2.id) in result.results


# ======================================================================
# disconnect_account
# ======================================================================


@pytest.mark.asyncio
async def test_disconnect_account_success(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should disconnect a connected account."""
    mock_db.execute.return_value = _mock_result(sample_bank_account)
    await OpenBankingService.connect_account(
        mock_db,
        bank_account_id=sample_bank_account.id,
        provider="test",
        credentials={},
    )

    result = await OpenBankingService.disconnect_account(
        mock_db,
        bank_account_id=sample_bank_account.id,
    )

    assert result.status == "disconnected"
    assert _connections[sample_bank_account.id]["status"] == "disconnected"


@pytest.mark.asyncio
async def test_disconnect_account_not_connected(mock_db: AsyncMock) -> None:
    """Should raise AccountNotConnectedError if not connected."""
    with pytest.raises(AccountNotConnectedError) as exc_info:
        await OpenBankingService.disconnect_account(
            mock_db,
            bank_account_id=uuid.uuid4(),
        )
    assert exc_info.value.status_code == 404


# ======================================================================
# get_connection_status
# ======================================================================


@pytest.mark.asyncio
async def test_get_connection_status_success(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should return connection status."""
    mock_db.execute.return_value = _mock_result(sample_bank_account)
    await OpenBankingService.connect_account(
        mock_db,
        bank_account_id=sample_bank_account.id,
        provider="plaid",
        credentials={"client_id": "test_client"},
    )

    # Need to mock the count query too
    mock_db.execute.side_effect = [
        _mock_result(None),  # count returns scalar_one = 1
    ]

    result = await OpenBankingService.get_connection_status(
        mock_db,
        bank_account_id=sample_bank_account.id,
    )

    assert isinstance(result, ConnectionStatusResponse)
    assert result.bank_account_id == sample_bank_account.id
    assert result.provider == "plaid"
    assert result.status == "connected"
    assert result.connected_at is not None


@pytest.mark.asyncio
async def test_get_connection_status_not_connected(mock_db: AsyncMock) -> None:
    """Should raise AccountNotConnectedError if not connected."""
    with pytest.raises(AccountNotConnectedError):
        await OpenBankingService.get_connection_status(
            mock_db,
            bank_account_id=uuid.uuid4(),
        )


# ======================================================================
# Edge cases
# ======================================================================


@pytest.mark.asyncio
async def test_fetch_transactions_disconnected_account(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should raise error when trying to sync a disconnected account."""
    mock_db.execute.return_value = _mock_result(sample_bank_account)
    await OpenBankingService.connect_account(
        mock_db,
        bank_account_id=sample_bank_account.id,
        provider="test",
        credentials={},
    )

    await OpenBankingService.disconnect_account(mock_db, sample_bank_account.id)

    with pytest.raises(OpenBankingError) as exc_info:
        await OpenBankingService.fetch_transactions(
            mock_db,
            bank_account_id=sample_bank_account.id,
        )
    assert exc_info.value.status_code == 400


def test_generate_transactions_zero_count() -> None:
    """Should return empty list for zero count."""
    txns = MockOpenBankingProvider.generate_transactions(
        bank_account_id=uuid.uuid4(),
        from_date=date(2026, 6, 1),
        to_date=date(2026, 6, 27),
        count=0,
    )
    assert len(txns) == 0
    assert isinstance(txns, list)
