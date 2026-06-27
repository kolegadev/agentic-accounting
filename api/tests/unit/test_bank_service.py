"""Unit tests for BankService with mocked DB session."""

from __future__ import annotations

import hashlib
import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from src.models.bank_account import BankAccount, BankTransaction
from src.services.bank_service import (
    BankAccountNotFoundError,
    BankService,
    BankServiceError,
    BankTransactionNotFoundError,
)
from src.validators.bank import BankAccountCreate, CategorizeTransaction


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
    """Create a fully-populated BankAccount ORM instance."""
    now = datetime(2026, 6, 27, 12, 0, 0)
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


@pytest.fixture
def sample_bank_transaction(sample_bank_account: BankAccount) -> BankTransaction:
    """Create a BankTransaction ORM instance."""
    now = datetime(2026, 6, 27, 12, 0, 0)
    return BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=sample_bank_account.id,
        date=date(2026, 6, 1),
        description="Test payment",
        amount=-5000,
        reference="REF001",
        type="DD",
        fitid=None,
        import_hash="abc123",
        status="imported",
        created_at=now,
    )


@pytest.fixture
def sample_bank_transaction_ofx(sample_bank_account: BankAccount) -> BankTransaction:
    """Create a BankTransaction ORM instance from OFX."""
    now = datetime(2026, 6, 27, 12, 0, 0)
    return BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=sample_bank_account.id,
        date=date(2026, 5, 15),
        description="OFX salary credit",
        amount=250000,
        reference="CHQ1001",
        type="CREDIT",
        fitid="FITID12345",
        import_hash=None,
        status="imported",
        created_at=now,
    )


# ---------------------------------------------------------------------------
# Helper: mock execute result
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


# ======================================================================
# create_account
# ======================================================================


@pytest.mark.asyncio
async def test_create_account_success(
    mock_db: AsyncMock,
) -> None:
    """Should create a bank account successfully."""
    now = datetime(2026, 6, 27, 12, 0, 0)

    async def mock_refresh(account: BankAccount) -> None:
        if account.id is None:
            account.id = uuid.uuid4()
        if account.is_active is None:
            account.is_active = True
        if account.created_at is None:
            account.created_at = now
        if account.updated_at is None:
            account.updated_at = now

    mock_db.refresh = mock_refresh

    data = BankAccountCreate(
        name="Barclays Business",
        sort_code="20-00-00",
        account_number="12345678",
        currency="GBP",
        opening_balance=50000,
    )
    result = await BankService.create_account(mock_db, data)

    assert result.name == "Barclays Business"
    assert result.opening_balance == 50000
    assert result.current_balance == 50000
    assert result.is_active is True
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


# ======================================================================
# list_accounts
# ======================================================================


@pytest.mark.asyncio
async def test_list_accounts_active_only(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should return only active bank accounts."""
    mock_db.execute.return_value = _mock_result([sample_bank_account])

    accounts = await BankService.list_accounts(mock_db, include_inactive=False)
    assert len(accounts) == 1
    assert accounts[0].name == "Test Business Account"


@pytest.mark.asyncio
async def test_list_accounts_empty(mock_db: AsyncMock) -> None:
    """Should return empty list when no accounts."""
    mock_db.execute.return_value = _mock_result([])

    accounts = await BankService.list_accounts(mock_db)
    assert len(accounts) == 0


# ======================================================================
# get_account
# ======================================================================


@pytest.mark.asyncio
async def test_get_account_found(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should return account when found."""
    mock_db.execute.return_value = _mock_result(sample_bank_account)

    result = await BankService.get_account(mock_db, sample_bank_account.id)
    assert result is not None
    assert result.name == "Test Business Account"


@pytest.mark.asyncio
async def test_get_account_not_found(mock_db: AsyncMock) -> None:
    """Should return None when not found."""
    mock_db.execute.return_value = _mock_result(None)

    result = await BankService.get_account(mock_db, uuid.uuid4())
    assert result is None


# ======================================================================
# _compute_import_hash
# ======================================================================


def test_compute_import_hash() -> None:
    """Should produce a deterministic SHA-256 hash."""
    d = date(2026, 6, 1)
    amount = -5000
    desc = "Test payment"

    h1 = BankService._compute_import_hash(d, amount, desc)
    h2 = BankService._compute_import_hash(d, amount, desc)
    h3 = BankService._compute_import_hash(date(2026, 6, 2), amount, desc)

    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64
    # Verify it's valid hex
    int(h1, 16)


# ======================================================================
# _auto_detect_csv_columns
# ======================================================================


def test_auto_detect_standard_headers() -> None:
    """Should detect standard UK bank CSV headers."""
    headers = ["Date", "Description", "Amount", "Reference", "Type"]
    mapping = BankService._auto_detect_csv_columns(headers)

    assert mapping["date"] == "Date"
    assert mapping["description"] == "Description"
    assert mapping["amount"] == "Amount"
    assert mapping["reference"] == "Reference"
    assert mapping["type"] == "Type"


def test_auto_detect_debit_credit_headers() -> None:
    """Should detect debit/credit split columns."""
    headers = ["Transaction Date", "Transaction Description", "Debit Amount", "Credit Amount", "Transaction Reference", "Transaction Type"]
    mapping = BankService._auto_detect_csv_columns(headers)

    assert mapping["date"] == "Transaction Date"
    assert mapping["description"] == "Transaction Description"
    assert mapping["debit"] == "Debit Amount"
    assert mapping["credit"] == "Credit Amount"
    assert mapping["reference"] == "Transaction Reference"
    assert mapping["type"] == "Transaction Type"
    assert "amount" not in mapping


def test_auto_detect_hsbc_headers() -> None:
    """Should detect HSBC-specific headers."""
    headers = ["Date", "Description", "Amount", "Reference", "Money out / Money in"]
    mapping = BankService._auto_detect_csv_columns(headers)

    assert mapping["date"] == "Date"
    assert mapping["description"] == "Description"
    assert mapping["amount"] == "Amount"
    assert mapping["type"] == "Money out / Money in"


def test_auto_detect_natwest_headers() -> None:
    """Should detect NatWest-specific headers."""
    headers = ["Date", "Narrative", "Value", "Reference", "Type"]
    mapping = BankService._auto_detect_csv_columns(headers)

    assert mapping["description"] == "Narrative"
    assert mapping["amount"] == "Value"


def test_auto_detect_minimal_headers() -> None:
    """Should return empty mapping for unknown headers."""
    headers = ["Col1", "Col2", "Col3"]
    mapping = BankService._auto_detect_csv_columns(headers)

    assert len(mapping) == 0


# ======================================================================
# import_csv
# ======================================================================


@pytest.mark.asyncio
async def test_import_csv_success(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should import CSV successfully with auto-detection."""
    csv_content = (
        "Date,Description,Amount,Reference,Type\n"
        "01/06/2026,Office Supplies,-5000,REF001,DD\n"
        "15/06/2026,Customer Payment,250000,REF002,CR\n"
    ).encode("utf-8")

    # First call: verify account exists
    # Second call: get existing hashes
    mock_db.execute.side_effect = [
        _mock_result(sample_bank_account),  # account lookup
        _mock_result([]),  # existing hashes
    ]

    result = await BankService.import_csv(
        mock_db,
        account_id=sample_bank_account.id,
        file_content=csv_content,
    )

    assert result.imported_count == 2
    assert result.skipped_count == 0
    assert len(result.errors) == 0
    assert mock_db.add.call_count == 2
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_import_csv_with_template(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should import CSV using a bank template."""
    csv_content = (
        "Date,Description,Amount,Reference,Type\n"
        "01/06/2026,Test Payment,-10000,TEST001,DD\n"
    ).encode("utf-8")

    mock_db.execute.side_effect = [
        _mock_result(sample_bank_account),  # account lookup
        _mock_result([]),  # existing hashes
    ]

    result = await BankService.import_csv(
        mock_db,
        account_id=sample_bank_account.id,
        file_content=csv_content,
        template_name="barclays",
    )

    assert result.imported_count == 1
    assert result.skipped_count == 0


@pytest.mark.asyncio
async def test_import_csv_duplicate_detection(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should skip duplicate transactions based on SHA-256 hash."""
    csv_content = (
        "Date,Description,Amount,Reference,Type\n"
        "01/06/2026,Office Supplies,-5000,REF001,DD\n"
    ).encode("utf-8")

    # Pre-compute the hash that would be generated
    expected_hash = BankService._compute_import_hash(
        date(2026, 6, 1), -500000, "Office Supplies"
    )

    mock_db.execute.side_effect = [
        _mock_result(sample_bank_account),  # account lookup
        _mock_result([expected_hash]),  # existing hashes (duplicate!)
    ]

    result = await BankService.import_csv(
        mock_db,
        account_id=sample_bank_account.id,
        file_content=csv_content,
    )

    assert result.imported_count == 0
    assert result.skipped_count == 1
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_import_csv_account_not_found(mock_db: AsyncMock) -> None:
    """Should raise BankAccountNotFoundError."""
    mock_db.execute.return_value = _mock_result(None)

    with pytest.raises(BankAccountNotFoundError) as exc_info:
        await BankService.import_csv(
            mock_db,
            account_id=uuid.uuid4(),
            file_content=b"Date,Desc,Amount\n01/06/2026,Test,100\n",
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_import_csv_semicolon_delimiter(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should handle semicolon-delimited CSV."""
    csv_content = (
        "Date;Description;Amount;Reference;Type\n"
        "01/06/2026;Office Supplies;-5000;REF001;DD\n"
    ).encode("utf-8")

    mock_db.execute.side_effect = [
        _mock_result(sample_bank_account),
        _mock_result([]),
    ]

    result = await BankService.import_csv(
        mock_db,
        account_id=sample_bank_account.id,
        file_content=csv_content,
    )

    assert result.imported_count == 1


@pytest.mark.asyncio
async def test_import_csv_debit_credit_columns(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should handle separate debit/credit columns."""
    csv_content = (
        "Transaction Date,Transaction Description,Debit Amount,Credit Amount,Reference\n"
        "01/06/2026,Test Debit,50.00,,REF001\n"
        "15/06/2026,Test Credit,,30.00,REF002\n"
    ).encode("utf-8")

    mock_db.execute.side_effect = [
        _mock_result(sample_bank_account),
        _mock_result([]),
    ]

    result = await BankService.import_csv(
        mock_db,
        account_id=sample_bank_account.id,
        file_content=csv_content,
        template_name="lloyds",
    )

    assert result.imported_count == 2
    assert result.errors == []


# ======================================================================
# import_ofx
# ======================================================================


@pytest.mark.asyncio
async def test_import_ofx_success(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should import OFX successfully."""
    ofx_content = b"""OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<CURDEF>GBP
<BANKACCTFROM>
<BANKID>200000
<ACCTID>12345678
<ACCTTYPE>CHECKING
</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>20260101
<DTEND>20260627
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20260601000000
<TRNAMT>-50.00
<FITID>OFXFIT001
<NAME>Office Supplies Ltd
<MEMO>Office Supplies June
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20260615000000
<TRNAMT>2500.00
<FITID>OFXFIT002
<NAME>Client Payment
<MEMO>Invoice #1234
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""

    mock_db.execute.side_effect = [
        _mock_result(sample_bank_account),  # account lookup
        _mock_result([]),  # existing FITIDs
    ]

    result = await BankService.import_ofx(
        mock_db,
        account_id=sample_bank_account.id,
        file_content=ofx_content,
    )

    assert result.imported_count == 2
    assert result.skipped_count == 0
    assert len(result.errors) == 0
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_import_ofx_duplicate_fitid(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should skip duplicate FITIDs in OFX import."""
    ofx_content = b"""OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<STMTRS>
<CURDEF>GBP
<BANKACCTFROM>
<BANKID>200000
<ACCTID>12345678
<ACCTTYPE>CHECKING
</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>20260101
<DTEND>20260627
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20260601000000
<TRNAMT>-50.00
<FITID>OFXFIT001
<NAME>Office Supplies Ltd
<MEMO>Office Supplies June
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""

    mock_db.execute.side_effect = [
        _mock_result(sample_bank_account),  # account lookup
        _mock_result(["OFXFIT001"]),  # existing FITIDs (duplicate!)
    ]

    result = await BankService.import_ofx(
        mock_db,
        account_id=sample_bank_account.id,
        file_content=ofx_content,
    )

    assert result.imported_count == 0
    assert result.skipped_count == 1
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_import_ofx_account_not_found(mock_db: AsyncMock) -> None:
    """Should raise BankAccountNotFoundError."""
    mock_db.execute.return_value = _mock_result(None)

    with pytest.raises(BankAccountNotFoundError):
        await BankService.import_ofx(
            mock_db,
            account_id=uuid.uuid4(),
            file_content=b"",
        )


@pytest.mark.asyncio
async def test_import_ofx_invalid_content(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should raise BankServiceError for invalid OFX content."""
    mock_db.execute.return_value = _mock_result(sample_bank_account)

    with pytest.raises(BankServiceError) as exc_info:
        await BankService.import_ofx(
            mock_db,
            account_id=sample_bank_account.id,
            file_content=b"not a valid OFX file",
        )
    assert exc_info.value.status_code == 422


# ======================================================================
# list_transactions
# ======================================================================


@pytest.mark.asyncio
async def test_list_transactions_success(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
    sample_bank_transaction: BankTransaction,
) -> None:
    """Should list transactions for a bank account."""
    sample_bank_transaction.bank_account = sample_bank_account

    mock_db.execute.side_effect = [
        _mock_result(None),  # count
        _mock_result([sample_bank_transaction]),  # fetch
    ]

    items, total = await BankService.list_transactions(
        mock_db,
        account_id=sample_bank_account.id,
    )

    assert total == 1
    assert len(items) == 1
    assert items[0].amount == -5000


@pytest.mark.asyncio
async def test_list_transactions_with_filters(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
    sample_bank_transaction: BankTransaction,
) -> None:
    """Should filter transactions by status and date range."""
    sample_bank_transaction.bank_account = sample_bank_account

    mock_db.execute.side_effect = [
        _mock_result(None),  # count
        _mock_result([sample_bank_transaction]),  # fetch
    ]

    items, total = await BankService.list_transactions(
        mock_db,
        account_id=sample_bank_account.id,
        status="imported",
        date_from=date(2026, 1, 1),
        date_to=date(2026, 12, 31),
        limit=10,
        offset=0,
    )

    assert total == 1
    assert len(items) == 1


# ======================================================================
# categorize_transaction
# ======================================================================


@pytest.mark.asyncio
async def test_categorize_transaction_success(
    mock_db: AsyncMock,
    sample_bank_transaction: BankTransaction,
) -> None:
    """Should categorize a transaction and transition status."""
    mock_db.execute.return_value = _mock_result(sample_bank_transaction)

    result = await BankService.categorize_transaction(
        mock_db,
        transaction_id=sample_bank_transaction.id,
        contact_id=uuid.uuid4(),
        category="Office Expenses",
    )

    assert result.category == "Office Expenses"
    assert sample_bank_transaction.status == "categorized"
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_categorize_transaction_contact_only(
    mock_db: AsyncMock,
    sample_bank_transaction: BankTransaction,
) -> None:
    """Should transition to categorized with just a contact."""
    mock_db.execute.return_value = _mock_result(sample_bank_transaction)

    contact_id = uuid.uuid4()
    result = await BankService.categorize_transaction(
        mock_db,
        transaction_id=sample_bank_transaction.id,
        contact_id=contact_id,
    )

    assert result.status == "categorized"
    assert result.contact_id == contact_id


@pytest.mark.asyncio
async def test_categorize_transaction_not_found(mock_db: AsyncMock) -> None:
    """Should raise BankTransactionNotFoundError."""
    mock_db.execute.return_value = _mock_result(None)

    with pytest.raises(BankTransactionNotFoundError) as exc_info:
        await BankService.categorize_transaction(
            mock_db,
            transaction_id=uuid.uuid4(),
            category="Test",
        )
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_categorize_transaction_no_status_change_if_not_imported(
    mock_db: AsyncMock,
    sample_bank_transaction: BankTransaction,
) -> None:
    """Should not change status if already categorized."""
    sample_bank_transaction.status = "categorized"
    sample_bank_transaction.category = "Existing"
    mock_db.execute.return_value = _mock_result(sample_bank_transaction)

    result = await BankService.categorize_transaction(
        mock_db,
        transaction_id=sample_bank_transaction.id,
        category="Updated Category",
    )

    assert result.status == "categorized"
    assert result.category == "Updated Category"


# ======================================================================
# _compute_import_hash edge cases
# ======================================================================


def test_compute_import_hash_different_dates_different() -> None:
    """Different dates should produce different hashes."""
    h1 = BankService._compute_import_hash(date(2026, 1, 1), 100, "Test")
    h2 = BankService._compute_import_hash(date(2026, 1, 2), 100, "Test")
    assert h1 != h2


def test_compute_import_hash_different_amounts_different() -> None:
    """Different amounts should produce different hashes."""
    h1 = BankService._compute_import_hash(date(2026, 1, 1), 100, "Test")
    h2 = BankService._compute_import_hash(date(2026, 1, 1), 200, "Test")
    assert h1 != h2


def test_compute_import_hash_different_descriptions_different() -> None:
    """Different descriptions should produce different hashes."""
    h1 = BankService._compute_import_hash(date(2026, 1, 1), 100, "Test A")
    h2 = BankService._compute_import_hash(date(2026, 1, 1), 100, "Test B")
    assert h1 != h2
