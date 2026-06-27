"""Integration tests for Bank Statement Import workflow.

Uses mocked DB (no real database required) but tests the full
create account → import CSV/OFX → list → categorize workflow.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.bank_account import BankAccount, BankTransaction
from src.services.bank_service import (
    BankAccountNotFoundError,
    BankService,
    BankServiceError,
)
from src.validators.bank import BankAccountCreate, CategorizeTransaction

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


async def _mock_refresh_account(account: BankAccount) -> None:
    """Populate server-defaults on a BankAccount."""
    if account.id is None:
        account.id = uuid.uuid4()
    if account.created_at is None:
        account.created_at = NOW
    if account.updated_at is None:
        account.updated_at = NOW
    if account.current_balance is None:
        account.current_balance = account.opening_balance


# ---------------------------------------------------------------------------
# Full workflow: Create account → Import CSV → List → Categorize
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_csv_import_workflow() -> None:
    """End-to-end CSV import workflow."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    # 1. Create bank account
    account = BankAccount(
        id=uuid.uuid4(),
        name="Test Account",
        sort_code="20-00-00",
        account_number="12345678",
        currency="GBP",
        opening_balance=0,
        current_balance=0,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

    db.refresh = _mock_refresh_account

    csv_content = (
        "Date,Description,Amount,Reference,Type\n"
        "01/06/2026,Office Supplies,-50.00,REF001,DD\n"
        "15/06/2026,Customer Payment,250.00,REF002,CR\n"
        "30/06/2026,Rent Payment,-1200.00,REF003,SO\n"
    ).encode("utf-8")

    db.execute.side_effect = [
        _mock_result(account),  # account lookup
        _mock_result([]),  # existing hashes
    ]

    result = await BankService.import_csv(
        db,
        account_id=account.id,
        file_content=csv_content,
    )

    assert result.imported_count == 3
    assert result.skipped_count == 0
    assert result.errors == []
    assert db.add.call_count == 3
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_csv_duplicate_detection_across_batches() -> None:
    """Should detect duplicates even across multiple import runs."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    account = BankAccount(
        id=uuid.uuid4(),
        name="Test Account",
        sort_code="20-00-00",
        account_number="12345678",
        currency="GBP",
        opening_balance=0,
        current_balance=0,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

    csv_content = (
        "Date,Description,Amount,Reference,Type\n"
        "01/06/2026,Office Supplies,-50.00,REF001,DD\n"
        "15/06/2026,Customer Payment,250.00,REF002,CR\n"
    ).encode("utf-8")

    # First import
    db.execute.side_effect = [
        _mock_result(account),
        _mock_result([]),
    ]
    result1 = await BankService.import_csv(
        db,
        account_id=account.id,
        file_content=csv_content,
    )
    assert result1.imported_count == 2

    # Reset mocks for second import
    db.reset_mock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    # Second import: hashes already exist
    expected_hash_1 = BankService._compute_import_hash(
        date(2026, 6, 1), -5000, "Office Supplies"
    )
    expected_hash_2 = BankService._compute_import_hash(
        date(2026, 6, 15), 25000, "Customer Payment"
    )

    db.execute.side_effect = [
        _mock_result(account),
        _mock_result([expected_hash_1, expected_hash_2]),
    ]
    result2 = await BankService.import_csv(
        db,
        account_id=account.id,
        file_content=csv_content,
    )
    assert result2.imported_count == 0
    assert result2.skipped_count == 2
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_ofx_duplicate_detection() -> None:
    """Should detect and skip OFX duplicates via FITID."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    account = BankAccount(
        id=uuid.uuid4(),
        name="Test Account",
        sort_code="20-00-00",
        account_number="12345678",
        currency="GBP",
        opening_balance=0,
        current_balance=0,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

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
<FITID>FITID001
<NAME>Office Supplies
<MEMO>Office Supplies June
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""

    # Second import attempt: FITID already exists
    db.execute.side_effect = [
        _mock_result(account),  # account lookup
        _mock_result(["FITID001"]),  # existing FITIDs
    ]

    result = await BankService.import_ofx(
        db,
        account_id=account.id,
        file_content=ofx_content,
    )

    assert result.imported_count == 0
    assert result.skipped_count == 1
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_csv_with_different_delimiters() -> None:
    """Should handle semicolon and tab delimiters."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    account = BankAccount(
        id=uuid.uuid4(),
        name="Test Account",
        sort_code="20-00-00",
        account_number="12345678",
        currency="GBP",
        opening_balance=0,
        current_balance=0,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

    # Semicolon-delimited
    semicolon_csv = (
        "Date;Description;Amount;Reference;Type\n"
        "01/06/2026;Test Payment;-100.00;REF001;DD\n"
    ).encode("utf-8")

    db.execute.side_effect = [
        _mock_result(account),
        _mock_result([]),
    ]

    result = await BankService.import_csv(
        db,
        account_id=account.id,
        file_content=semicolon_csv,
    )
    assert result.imported_count == 1

    # Tab-delimited
    db.reset_mock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    tab_csv = (
        "Date\tDescription\tAmount\tReference\tType\n"
        "01/06/2026\tTest Payment\t50.00\tREF002\tCR\n"
    ).encode("utf-8")

    db.execute.side_effect = [
        _mock_result(account),
        _mock_result([]),
    ]

    result = await BankService.import_csv(
        db,
        account_id=account.id,
        file_content=tab_csv,
    )
    assert result.imported_count == 1


@pytest.mark.asyncio
async def test_csv_debit_credit_split_columns() -> None:
    """Should correctly parse debit/credit split columns (Lloyds format)."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    account = BankAccount(
        id=uuid.uuid4(),
        name="Test Account",
        sort_code="30-00-00",
        account_number="87654321",
        currency="GBP",
        opening_balance=0,
        current_balance=0,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

    csv_content = (
        "Transaction Date,Transaction Description,Debit Amount,Credit Amount,Transaction Reference,Transaction Type\n"
        "01/06/2026,Debit Purchase,50.00,,REF001,DD\n"
        "15/06/2026,Credit Received,,100.00,REF002,CR\n"
        "30/06/2026,Zero Transaction,,,REF003,ZERO\n"
    ).encode("utf-8")

    db.execute.side_effect = [
        _mock_result(account),
        _mock_result([]),
    ]

    result = await BankService.import_csv(
        db,
        account_id=account.id,
        file_content=csv_content,
        template_name="lloyds",
    )

    assert result.imported_count == 3
    # Verify amounts: debit → negative, credit → positive, zero → 0
    calls = db.add.call_args_list
    assert calls[0].args[0].amount == -5000  # 50.00 debit
    assert calls[1].args[0].amount == 10000  # 100.00 credit
    assert calls[2].args[0].amount == 0  # zero


@pytest.mark.asyncio
async def test_csv_auto_detect_vs_template() -> None:
    """Auto-detect should work even without an explicit template."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    account = BankAccount(
        id=uuid.uuid4(),
        name="Test Account",
        sort_code="20-00-00",
        account_number="12345678",
        currency="GBP",
        opening_balance=0,
        current_balance=0,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

    # Standard headers - auto-detect should find them
    csv_content = (
        "Date,Description,Amount,Reference,Type\n"
        "01/06/2026,Auto Detected,-150.00,REF001,SO\n"
    ).encode("utf-8")

    db.execute.side_effect = [
        _mock_result(account),
        _mock_result([]),
    ]

    result = await BankService.import_csv(
        db,
        account_id=account.id,
        file_content=csv_content,
        # No template_name → auto-detect
    )

    assert result.imported_count == 1
    assert result.errors == []


@pytest.mark.asyncio
async def test_csv_missing_date_column() -> None:
    """Should raise error when date column cannot be identified."""
    db = AsyncMock()

    account = BankAccount(
        id=uuid.uuid4(),
        name="Test Account",
        sort_code="20-00-00",
        account_number="12345678",
        currency="GBP",
        opening_balance=0,
        current_balance=0,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

    csv_content = (
        "ColA,ColB,ColC\n"
        "value1,value2,value3\n"
    ).encode("utf-8")

    db.execute.return_value = _mock_result(account)

    with pytest.raises(BankServiceError) as exc_info:
        await BankService.import_csv(
            db,
            account_id=account.id,
            file_content=csv_content,
        )
    assert exc_info.value.status_code == 422
    assert "date" in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_csv_invalid_rows_get_errors() -> None:
    """Should collect errors for invalid rows but continue importing valid ones."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    account = BankAccount(
        id=uuid.uuid4(),
        name="Test Account",
        sort_code="20-00-00",
        account_number="12345678",
        currency="GBP",
        opening_balance=0,
        current_balance=0,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

    csv_content = (
        "Date,Description,Amount,Reference,Type\n"
        "01/06/2026,Valid Transaction,-100.00,REF001,DD\n"
        ",No Date Row,50.00,REF002,CR\n"
        "not-a-date,Bad Date Row,-200.00,REF003,SO\n"
        "15/06/2026,,250.00,REF004,CR\n"
        "30/06/2026,Invalid Amount,not-a-number,REF005,DD\n"
    ).encode("utf-8")

    db.execute.side_effect = [
        _mock_result(account),
        _mock_result([]),
    ]

    result = await BankService.import_csv(
        db,
        account_id=account.id,
        file_content=csv_content,
    )

    assert result.imported_count == 1  # Only the first valid row
    assert result.skipped_count == 4
    assert len(result.errors) == 4
    assert any("date" in e.lower() for e in result.errors)
    assert any("description" in e.lower() for e in result.errors)
    assert any("amount" in e.lower() for e in result.errors)


@pytest.mark.asyncio
async def test_status_flow_imported_to_categorized_to_reconciled() -> None:
    """Should follow the status flow: imported → categorized → reconciled."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    tx = BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=uuid.uuid4(),
        date=date(2026, 6, 1),
        description="Test payment",
        amount=-5000,
        status="imported",
        created_at=NOW,
    )
    tx.bank_account = BankAccount(
        id=tx.bank_account_id,
        name="Test Account",
        sort_code="20-00-00",
        account_number="12345678",
        currency="GBP",
        opening_balance=0,
        current_balance=0,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

    # Categorize → should change to 'categorized'
    db.execute.return_value = _mock_result(tx)
    result = await BankService.categorize_transaction(
        db,
        transaction_id=tx.id,
        category="Office Expenses",
    )
    assert result.status == "categorized"
    assert tx.status == "categorized"

    # Manually set to reconciled (this would be done by matching in production)
    tx.status = "reconciled"
    assert tx.status == "reconciled"


@pytest.mark.asyncio
async def test_multiple_bank_accounts_isolation() -> None:
    """Transactions from different bank accounts should be isolated."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    account1 = BankAccount(
        id=uuid.uuid4(),
        name="Account 1",
        sort_code="20-00-00",
        account_number="11111111",
        currency="GBP",
        opening_balance=0,
        current_balance=0,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

    account2 = BankAccount(
        id=uuid.uuid4(),
        name="Account 2",
        sort_code="30-00-00",
        account_number="22222222",
        currency="GBP",
        opening_balance=0,
        current_balance=0,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

    csv_content = (
        "Date,Description,Amount,Reference,Type\n"
        "01/06/2026,Same Description,-100.00,REF001,DD\n"
    ).encode("utf-8")

    # Import into account 1
    db.execute.side_effect = [
        _mock_result(account1),
        _mock_result([]),
    ]
    result1 = await BankService.import_csv(
        db, account_id=account1.id, file_content=csv_content
    )
    assert result1.imported_count == 1

    # Import same CSV into account 2 — should NOT be duplicate
    db.reset_mock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    db.execute.side_effect = [
        _mock_result(account2),
        _mock_result([]),  # Empty existing hashes for account 2
    ]
    result2 = await BankService.import_csv(
        db, account_id=account2.id, file_content=csv_content
    )
    assert result2.imported_count == 1
    assert result2.skipped_count == 0
