"""Unit tests for BankRuleService with mocked DB session."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.bank_rule import BankRule
from src.models.bank_account import BankAccount, BankTransaction
from src.services.bank_rule_service import (
    BankRuleNotFoundError,
    BankRuleService,
    BankRuleServiceError,
)
from src.validators.bank_rule import (
    BankRuleCreate,
    BankRuleUpdate,
)


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
    db.delete = AsyncMock()
    return db


@pytest.fixture
def sample_bank_account() -> BankAccount:
    """Create a BankAccount ORM instance."""
    now = datetime(2026, 6, 27, 12, 0, 0)
    return BankAccount(
        id=uuid.uuid4(),
        name="Test Business Account",
        sort_code="20-00-00",
        account_number="12345678",
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
    tx = BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=sample_bank_account.id,
        date=date(2026, 6, 1),
        description="TESCO STORE 1234",
        amount=-5000,
        reference="REF001",
        status="imported",
        created_at=now,
    )
    tx.bank_account = sample_bank_account
    return tx


@pytest.fixture
def sample_rule() -> BankRule:
    """Create a BankRule ORM instance."""
    now = datetime(2026, 6, 27, 12, 0, 0)
    return BankRule(
        id=uuid.uuid4(),
        name="TESCO → Groceries",
        condition_field="description",
        condition_operator="contains",
        condition_value="TESCO",
        action_type="set_category",
        action_value="Groceries",
        priority=100,
        is_active=True,
        created_at=now,
        updated_at=now,
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
# _evaluate_condition
# ======================================================================


def test_evaluate_contains_match(
    sample_rule: BankRule,
    sample_bank_transaction: BankTransaction,
) -> None:
    """Should match when description contains the condition value."""
    assert BankRuleService._evaluate_condition(sample_rule, sample_bank_transaction) is True


def test_evaluate_contains_no_match(
    sample_rule: BankRule,
    sample_bank_transaction: BankTransaction,
) -> None:
    """Should not match when description does not contain condition value."""
    sample_bank_transaction.description = "SAINSBURY'S STORE"
    assert BankRuleService._evaluate_condition(sample_rule, sample_bank_transaction) is False


def test_evaluate_contains_case_insensitive(
    sample_rule: BankRule,
    sample_bank_transaction: BankTransaction,
) -> None:
    """Should match case-insensitively."""
    sample_bank_transaction.description = "tesco store"
    assert BankRuleService._evaluate_condition(sample_rule, sample_bank_transaction) is True


def test_evaluate_equals_match() -> None:
    """Should match exact equals."""
    rule = BankRule(
        condition_field="description",
        condition_operator="equals",
        condition_value="Office Supplies Ltd",
        action_type="set_category",
        action_value="Test",
        priority=100,
        is_active=True,
    )
    tx = BankTransaction(
        description="Office Supplies Ltd",
        amount=0,
        date=date(2026, 6, 1),
        bank_account_id=uuid.uuid4(),
        status="imported",
    )
    assert BankRuleService._evaluate_condition(rule, tx) is True


def test_evaluate_equals_no_match() -> None:
    """Should not match when not exact equals."""
    rule = BankRule(
        condition_field="description",
        condition_operator="equals",
        condition_value="Office Supplies",
        action_type="set_category",
        action_value="Test",
        priority=100,
        is_active=True,
    )
    tx = BankTransaction(
        description="Office Supplies Ltd",
        amount=0,
        date=date(2026, 6, 1),
        bank_account_id=uuid.uuid4(),
        status="imported",
    )
    assert BankRuleService._evaluate_condition(rule, tx) is False


def test_evaluate_starts_with() -> None:
    """Should match when description starts with value."""
    rule = BankRule(
        condition_field="description",
        condition_operator="starts_with",
        condition_value="TESCO",
        action_type="set_category",
        action_value="Test",
        priority=100,
        is_active=True,
    )
    tx = BankTransaction(
        description="TESCO STORE 1234",
        amount=0,
        date=date(2026, 6, 1),
        bank_account_id=uuid.uuid4(),
        status="imported",
    )
    assert BankRuleService._evaluate_condition(rule, tx) is True


def test_evaluate_starts_with_no_match() -> None:
    """Should not match when description doesn't start with value."""
    rule = BankRule(
        condition_field="description",
        condition_operator="starts_with",
        condition_value="TESCO",
        action_type="set_category",
        action_value="Test",
        priority=100,
        is_active=True,
    )
    tx = BankTransaction(
        description="STORE TESCO",
        amount=0,
        date=date(2026, 6, 1),
        bank_account_id=uuid.uuid4(),
        status="imported",
    )
    assert BankRuleService._evaluate_condition(rule, tx) is False


def test_evaluate_regex_match() -> None:
    """Should match regex pattern."""
    rule = BankRule(
        condition_field="description",
        condition_operator="regex",
        condition_value=r"TESCO|SAINSBURY",
        action_type="set_category",
        action_value="Test",
        priority=100,
        is_active=True,
    )
    tx = BankTransaction(
        description="SAINSBURY'S STORE",
        amount=0,
        date=date(2026, 6, 1),
        bank_account_id=uuid.uuid4(),
        status="imported",
    )
    assert BankRuleService._evaluate_condition(rule, tx) is True


def test_evaluate_regex_no_match() -> None:
    """Should not match when regex doesn't match."""
    rule = BankRule(
        condition_field="description",
        condition_operator="regex",
        condition_value=r"TESCO|SAINSBURY",
        action_type="set_category",
        action_value="Test",
        priority=100,
        is_active=True,
    )
    tx = BankTransaction(
        description="ALDI STORE",
        amount=0,
        date=date(2026, 6, 1),
        bank_account_id=uuid.uuid4(),
        status="imported",
    )
    assert BankRuleService._evaluate_condition(rule, tx) is False


def test_evaluate_greater_than_amount() -> None:
    """Should match when amount is greater than condition value."""
    rule = BankRule(
        condition_field="amount",
        condition_operator="greater_than",
        condition_value="5000",
        action_type="set_category",
        action_value="Test",
        priority=100,
        is_active=True,
    )
    tx = BankTransaction(
        description="Test",
        amount=10000,
        date=date(2026, 6, 1),
        bank_account_id=uuid.uuid4(),
        status="imported",
    )
    assert BankRuleService._evaluate_condition(rule, tx) is True


def test_evaluate_greater_than_no_match() -> None:
    """Should not match when amount is less than condition value."""
    rule = BankRule(
        condition_field="amount",
        condition_operator="greater_than",
        condition_value="5000",
        action_type="set_category",
        action_value="Test",
        priority=100,
        is_active=True,
    )
    tx = BankTransaction(
        description="Test",
        amount=1000,
        date=date(2026, 6, 1),
        bank_account_id=uuid.uuid4(),
        status="imported",
    )
    assert BankRuleService._evaluate_condition(rule, tx) is False


def test_evaluate_less_than_amount() -> None:
    """Should match when amount is less than condition value."""
    rule = BankRule(
        condition_field="amount",
        condition_operator="less_than",
        condition_value="-5000",
        action_type="set_category",
        action_value="Test",
        priority=100,
        is_active=True,
    )
    tx = BankTransaction(
        description="Test",
        amount=-10000,
        date=date(2026, 6, 1),
        bank_account_id=uuid.uuid4(),
        status="imported",
    )
    assert BankRuleService._evaluate_condition(rule, tx) is True


def test_evaluate_reference_contains() -> None:
    """Should match reference field."""
    rule = BankRule(
        condition_field="reference",
        condition_operator="contains",
        condition_value="INV",
        action_type="set_category",
        action_value="Test",
        priority=100,
        is_active=True,
    )
    tx = BankTransaction(
        description="Test",
        amount=0,
        reference="INV-1234",
        date=date(2026, 6, 1),
        bank_account_id=uuid.uuid4(),
        status="imported",
    )
    assert BankRuleService._evaluate_condition(rule, tx) is True


# ======================================================================
# apply_rules
# ======================================================================


@pytest.mark.asyncio
async def test_apply_rules_success(
    mock_db: AsyncMock,
    sample_bank_transaction: BankTransaction,
    sample_rule: BankRule,
) -> None:
    """Should apply a matching rule and set category."""
    mock_db.execute.side_effect = [
        _mock_result(sample_bank_transaction),  # transaction lookup
        _mock_result([sample_rule]),  # rules query
    ]

    result = await BankRuleService.apply_rules(mock_db, sample_bank_transaction.id)

    assert result is not None
    assert result.category == "Groceries"
    assert result.status == "categorized"
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_apply_rules_no_match(
    mock_db: AsyncMock,
    sample_bank_transaction: BankTransaction,
    sample_rule: BankRule,
) -> None:
    """Should not change transaction when no rule matches."""
    sample_bank_transaction.description = "UNKNOWN MERCHANT"
    mock_db.execute.side_effect = [
        _mock_result(sample_bank_transaction),
        _mock_result([sample_rule]),
    ]

    result = await BankRuleService.apply_rules(mock_db, sample_bank_transaction.id)

    assert result is not None
    assert result.status == "imported"  # Status unchanged
    assert result.category is None


@pytest.mark.asyncio
async def test_apply_rules_first_match_wins(
    mock_db: AsyncMock,
    sample_bank_transaction: BankTransaction,
) -> None:
    """Should apply only the first matching rule by priority."""
    now = datetime(2026, 6, 27, 12, 0, 0)
    rule1 = BankRule(
        id=uuid.uuid4(),
        name="High Priority",
        condition_field="description",
        condition_operator="contains",
        condition_value="TESCO",
        action_type="set_category",
        action_value="Groceries",
        priority=10,  # Higher priority (lower number)
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    rule2 = BankRule(
        id=uuid.uuid4(),
        name="Low Priority",
        condition_field="description",
        condition_operator="contains",
        condition_value="TESCO",
        action_type="set_category",
        action_value="Other",
        priority=100,  # Lower priority
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    mock_db.execute.side_effect = [
        _mock_result(sample_bank_transaction),
        _mock_result([rule1, rule2]),  # Ordered by priority
    ]

    result = await BankRuleService.apply_rules(mock_db, sample_bank_transaction.id)

    assert result is not None
    assert result.category == "Groceries"  # High priority won


@pytest.mark.asyncio
async def test_apply_rules_transaction_not_found(mock_db: AsyncMock) -> None:
    """Should raise error when transaction not found."""
    mock_db.execute.return_value = _mock_result(None)

    with pytest.raises(BankRuleServiceError) as exc_info:
        await BankRuleService.apply_rules(mock_db, uuid.uuid4())
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_apply_rules_already_categorized(
    mock_db: AsyncMock,
    sample_bank_transaction: BankTransaction,
) -> None:
    """Should not re-apply rules to already categorized transactions."""
    sample_bank_transaction.status = "categorized"
    sample_bank_transaction.category = "Existing"
    mock_db.execute.return_value = _mock_result(sample_bank_transaction)

    result = await BankRuleService.apply_rules(mock_db, sample_bank_transaction.id)

    assert result is not None
    assert result.status == "categorized"
    assert result.category == "Existing"
    # No commit: early return before any changes
    mock_db.commit.assert_not_called()


# ======================================================================
# apply_all_pending
# ======================================================================


@pytest.mark.asyncio
async def test_apply_all_pending_success(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
    sample_rule: BankRule,
) -> None:
    """Should categorize all imported transactions for an account."""
    now = datetime(2026, 6, 27, 12, 0, 0)
    tx1 = BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=sample_bank_account.id,
        date=date(2026, 6, 1),
        description="TESCO STORE",
        amount=-5000,
        status="imported",
        created_at=now,
    )
    tx2 = BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=sample_bank_account.id,
        date=date(2026, 6, 2),
        description="AMAZON MKTPLACE",
        amount=-2500,
        status="imported",
        created_at=now,
    )

    # Second rule for AMAZON
    rule2 = BankRule(
        id=uuid.uuid4(),
        name="AMAZON → Office Supplies",
        condition_field="description",
        condition_operator="contains",
        condition_value="AMAZON",
        action_type="set_category",
        action_value="Office Supplies",
        priority=100,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    mock_db.execute.side_effect = [
        _mock_result([sample_rule, rule2]),  # rules
        _mock_result([tx1, tx2]),  # transactions
    ]

    result = await BankRuleService.apply_all_pending(mock_db, sample_bank_account.id)

    assert result.categorized_count == 2
    assert tx1.category == "Groceries"
    assert tx1.status == "categorized"
    assert tx2.category == "Office Supplies"
    assert tx2.status == "categorized"


@pytest.mark.asyncio
async def test_apply_all_pending_no_rules(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
) -> None:
    """Should return 0 when no rules are active."""
    mock_db.execute.return_value = _mock_result([])

    result = await BankRuleService.apply_all_pending(mock_db, sample_bank_account.id)

    assert result.categorized_count == 0


@pytest.mark.asyncio
async def test_apply_all_pending_no_transactions(
    mock_db: AsyncMock,
    sample_bank_account: BankAccount,
    sample_rule: BankRule,
) -> None:
    """Should return 0 when there are no imported transactions."""
    mock_db.execute.side_effect = [
        _mock_result([sample_rule]),  # rules
        _mock_result([]),  # no transactions
    ]

    result = await BankRuleService.apply_all_pending(mock_db, sample_bank_account.id)

    assert result.categorized_count == 0


# ======================================================================
# create_rule
# ======================================================================


@pytest.mark.asyncio
async def test_create_rule_success(mock_db: AsyncMock) -> None:
    """Should create a new bank rule."""
    now = datetime(2026, 6, 27, 12, 0, 0)

    async def mock_refresh(rule: BankRule) -> None:
        if rule.id is None:
            rule.id = uuid.uuid4()
        if rule.created_at is None:
            rule.created_at = now
        if rule.updated_at is None:
            rule.updated_at = now

    mock_db.refresh = mock_refresh

    data = BankRuleCreate(
        name="Test Rule",
        condition_field="description",
        condition_operator="contains",
        condition_value="TEST",
        action_type="set_category",
        action_value="Test Category",
        priority=100,
        is_active=True,
    )
    result = await BankRuleService.create_rule(mock_db, data)

    assert result.name == "Test Rule"
    assert result.action_value == "Test Category"
    assert result.priority == 100
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


# ======================================================================
# list_rules
# ======================================================================


@pytest.mark.asyncio
async def test_list_rules_active_only(
    mock_db: AsyncMock,
    sample_rule: BankRule,
) -> None:
    """Should return only active rules."""
    mock_db.execute.return_value = _mock_result([sample_rule])

    rules = await BankRuleService.list_rules(mock_db, include_inactive=False)
    assert len(rules) == 1
    assert rules[0].name == "TESCO → Groceries"


@pytest.mark.asyncio
async def test_list_rules_empty(mock_db: AsyncMock) -> None:
    """Should return empty list when no rules exist."""
    mock_db.execute.return_value = _mock_result([])

    rules = await BankRuleService.list_rules(mock_db)
    assert len(rules) == 0


# ======================================================================
# update_rule
# ======================================================================


@pytest.mark.asyncio
async def test_update_rule_success(
    mock_db: AsyncMock,
    sample_rule: BankRule,
) -> None:
    """Should update an existing bank rule."""
    mock_db.execute.return_value = _mock_result(sample_rule)

    data = BankRuleUpdate(
        name="Updated Rule",
        priority=50,
    )
    result = await BankRuleService.update_rule(mock_db, sample_rule.id, data)

    assert result.name == "Updated Rule"
    assert result.priority == 50
    assert sample_rule.name == "Updated Rule"
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_rule_not_found(mock_db: AsyncMock) -> None:
    """Should raise BankRuleNotFoundError."""
    mock_db.execute.return_value = _mock_result(None)

    with pytest.raises(BankRuleNotFoundError) as exc_info:
        await BankRuleService.update_rule(mock_db, uuid.uuid4(), BankRuleUpdate())
    assert exc_info.value.status_code == 404


# ======================================================================
# delete_rule
# ======================================================================


@pytest.mark.asyncio
async def test_delete_rule_success(
    mock_db: AsyncMock,
    sample_rule: BankRule,
) -> None:
    """Should delete a bank rule."""
    mock_db.execute.return_value = _mock_result(sample_rule)

    await BankRuleService.delete_rule(mock_db, sample_rule.id)

    mock_db.delete.assert_called_once_with(sample_rule)
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_rule_not_found(mock_db: AsyncMock) -> None:
    """Should raise BankRuleNotFoundError."""
    mock_db.execute.return_value = _mock_result(None)

    with pytest.raises(BankRuleNotFoundError) as exc_info:
        await BankRuleService.delete_rule(mock_db, uuid.uuid4())
    assert exc_info.value.status_code == 404


# ======================================================================
# load_default_rules
# ======================================================================


@pytest.mark.asyncio
async def test_load_default_rules_success(mock_db: AsyncMock) -> None:
    """Should load rules from JSON template."""
    mock_db.execute.return_value = _mock_result([])  # No existing rules

    with patch(
        "src.services.bank_rule_service.BankRuleService._load_rules_json",
        return_value=[
            {
                "name": "Test Rule 1",
                "condition_field": "description",
                "condition_operator": "contains",
                "condition_value": "TEST1",
                "action_type": "set_category",
                "action_value": "Cat1",
                "priority": 100,
                "is_active": True,
            },
            {
                "name": "Test Rule 2",
                "condition_field": "description",
                "condition_operator": "contains",
                "condition_value": "TEST2",
                "action_type": "set_category",
                "action_value": "Cat2",
                "priority": 200,
                "is_active": True,
            },
        ],
    ):
        result = await BankRuleService.load_default_rules(mock_db)

    assert result.created_count == 2
    assert result.skipped_count == 0
    assert mock_db.add.call_count == 2
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_load_default_rules_skip_duplicates(mock_db: AsyncMock) -> None:
    """Should skip rules that already exist by name."""
    mock_db.execute.return_value = _mock_result(["Test Rule 1"])  # Already exists

    with patch(
        "src.services.bank_rule_service.BankRuleService._load_rules_json",
        return_value=[
            {"name": "Test Rule 1", "condition_field": "description", "condition_operator": "contains",
             "condition_value": "TEST1", "action_type": "set_category", "action_value": "Cat1",
             "priority": 100, "is_active": True},
            {"name": "Test Rule 2", "condition_field": "description", "condition_operator": "contains",
             "condition_value": "TEST2", "action_type": "set_category", "action_value": "Cat2",
             "priority": 200, "is_active": True},
        ],
    ):
        result = await BankRuleService.load_default_rules(mock_db)

    assert result.created_count == 1
    assert result.skipped_count == 1
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
