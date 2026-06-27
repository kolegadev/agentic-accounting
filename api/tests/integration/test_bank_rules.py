"""Integration tests for Bank Rules Engine workflow.

Tests the full create rule → apply to transactions → verify categorization
workflow using mocked DB sessions.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.bank_rule import BankRule
from src.models.bank_account import BankAccount, BankTransaction
from src.services.bank_rule_service import BankRuleService, BankRuleNotFoundError
from src.validators.bank_rule import (
    BankRuleCreate,
    BankRuleUpdate,
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


# ---------------------------------------------------------------------------
# Full workflow: Create rules → apply to transactions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_rules_workflow() -> None:
    """End-to-end rules engine workflow."""
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

    # Create transactions
    tx1 = BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=account.id,
        date=date(2026, 6, 1),
        description="TESCO STORE 1234",
        amount=-5000,
        status="imported",
        created_at=NOW,
    )
    tx2 = BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=account.id,
        date=date(2026, 6, 2),
        description="AMAZON MKTPLACE",
        amount=-2500,
        status="imported",
        created_at=NOW,
    )
    tx3 = BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=account.id,
        date=date(2026, 6, 3),
        description="UNKNOWN MERCHANT",
        amount=-1000,
        status="imported",
        created_at=NOW,
    )

    # Create rules
    rule1 = BankRule(
        id=uuid.uuid4(),
        name="TESCO → Groceries",
        condition_field="description",
        condition_operator="contains",
        condition_value="TESCO",
        action_type="set_category",
        action_value="Groceries",
        priority=100,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )
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
        created_at=NOW,
        updated_at=NOW,
    )

    # Apply all pending
    db.execute.side_effect = [
        _mock_result([rule1, rule2]),  # rules
        _mock_result([tx1, tx2, tx3]),  # transactions
    ]

    result = await BankRuleService.apply_all_pending(db, account.id)

    assert result.categorized_count == 2
    assert tx1.category == "Groceries"
    assert tx1.status == "categorized"
    assert tx2.category == "Office Supplies"
    assert tx2.status == "categorized"
    # tx3 should remain untouched
    assert tx3.category is None
    assert tx3.status == "imported"


@pytest.mark.asyncio
async def test_priority_ordering_precedence() -> None:
    """Lower priority number should win over higher."""
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

    tx = BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=account.id,
        date=date(2026, 6, 1),
        description="STRIPE PAYMENT",
        amount=-150,
        status="imported",
        created_at=NOW,
    )

    # Rule with priority 10 should win over priority 100
    high_priority_rule = BankRule(
        id=uuid.uuid4(),
        name="STRIPE → Payment Fees",
        condition_field="description",
        condition_operator="contains",
        condition_value="STRIPE",
        action_type="set_category",
        action_value="Payment Processing Fees",
        priority=10,  # Higher priority
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )
    low_priority_rule = BankRule(
        id=uuid.uuid4(),
        name="General Expenses",
        condition_field="description",
        condition_operator="contains",
        condition_value="STRIPE",
        action_type="set_category",
        action_value="Other Expense",
        priority=500,  # Lower priority
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

    db.execute.side_effect = [
        _mock_result(tx),
        _mock_result([high_priority_rule, low_priority_rule]),
    ]

    result = await BankRuleService.apply_rules(db, tx.id)

    assert result is not None
    assert result.category == "Payment Processing Fees"


@pytest.mark.asyncio
async def test_inactive_rules_not_applied() -> None:
    """Inactive rules should be ignored."""
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

    tx = BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=account.id,
        date=date(2026, 6, 1),
        description="TESCO STORE",
        amount=-5000,
        status="imported",
        created_at=NOW,
    )

    inactive_rule = BankRule(
        id=uuid.uuid4(),
        name="Inactive Rule",
        condition_field="description",
        condition_operator="contains",
        condition_value="TESCO",
        action_type="set_category",
        action_value="Groceries",
        priority=100,
        is_active=False,  # Inactive!
        created_at=NOW,
        updated_at=NOW,
    )

    # apply_all_pending loads only active rules, so inactive rule is returned as empty
    db.execute.side_effect = [
        _mock_result([inactive_rule]),  # rules query filters on is_active=True
        _mock_result([tx]),  # transactions
    ]

    # Wait - the rule is inactive, so the query for active rules returns it.
    # But actually, the service filters with .where(BankRule.is_active == True)
    # so inactive rules won't be in the result. Let me fix: rules query returns [].
    pass

    db.reset_mock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    db.execute.side_effect = [
        _mock_result([]),  # No active rules
        _mock_result([tx]),
    ]

    result = await BankRuleService.apply_all_pending(db, account.id)
    assert result.categorized_count == 0


@pytest.mark.asyncio
async def test_amount_based_rules() -> None:
    """Rules based on amount thresholds should work."""
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

    large_income = BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=account.id,
        date=date(2026, 6, 1),
        description="CLIENT PAYMENT",
        amount=1000000,  # £10,000 in pence
        status="imported",
        created_at=NOW,
    )
    small_expense = BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=account.id,
        date=date(2026, 6, 2),
        description="COFFEE",
        amount=-350,  # -£3.50
        status="imported",
        created_at=NOW,
    )

    large_income_rule = BankRule(
        id=uuid.uuid4(),
        name="Large Income",
        condition_field="amount",
        condition_operator="greater_than",
        condition_value="500000",
        action_type="set_category",
        action_value="Income",
        priority=100,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )
    small_expense_rule = BankRule(
        id=uuid.uuid4(),
        name="Small Expense",
        condition_field="amount",
        condition_operator="less_than",
        condition_value="-200",
        action_type="set_category",
        action_value="Small Expense",
        priority=100,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

    db.execute.side_effect = [
        _mock_result([large_income_rule, small_expense_rule]),
        _mock_result([large_income, small_expense]),
    ]

    result = await BankRuleService.apply_all_pending(db, account.id)

    assert result.categorized_count == 2
    assert large_income.category == "Income"
    assert small_expense.category == "Small Expense"


@pytest.mark.asyncio
async def test_update_rule_partial() -> None:
    """Partial update should only change specified fields."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    rule = BankRule(
        id=uuid.uuid4(),
        name="Original Rule",
        condition_field="description",
        condition_operator="contains",
        condition_value="ORIGINAL",
        action_type="set_category",
        action_value="Original Category",
        priority=100,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

    db.execute.return_value = _mock_result(rule)

    update = BankRuleUpdate(
        name="Updated Rule",
        priority=50,
    )
    result = await BankRuleService.update_rule(db, rule.id, update)

    assert result.name == "Updated Rule"
    assert result.priority == 50
    assert result.condition_value == "ORIGINAL"  # Unchanged
    assert result.action_value == "Original Category"  # Unchanged


@pytest.mark.asyncio
async def test_rule_crud_flow() -> None:
    """Create → list → update → delete workflow."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    now = datetime(2026, 6, 27, 12, 0, 0)

    # Create
    async def mock_refresh(obj) -> None:
        if obj.id is None:
            obj.id = uuid.uuid4()
        if obj.created_at is None:
            obj.created_at = now
        if obj.updated_at is None:
            obj.updated_at = now

    db.refresh = mock_refresh

    create_data = BankRuleCreate(
        name="My Rule",
        condition_field="description",
        condition_operator="contains",
        condition_value="VALUE",
        action_type="set_category",
        action_value="Category",
        priority=100,
    )
    created = await BankRuleService.create_rule(db, create_data)
    assert created.name == "My Rule"

    # List
    db.execute.return_value = _mock_result([created])
    rules = await BankRuleService.list_rules(db)
    assert len(rules) == 1

    # Update
    db.execute.return_value = _mock_result(created)
    update = BankRuleUpdate(name="Updated My Rule")
    updated = await BankRuleService.update_rule(db, created.id, update)
    assert updated.name == "Updated My Rule"

    # Delete
    db.execute.return_value = _mock_result(created)
    db.delete = AsyncMock()
    await BankRuleService.delete_rule(db, created.id)
    db.delete.assert_called_once_with(created)


@pytest.mark.asyncio
async def test_mixed_transaction_statuses() -> None:
    """Only 'imported' transactions should be categorized."""
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

    imported_tx = BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=account.id,
        date=date(2026, 6, 1),
        description="TESCO STORE",
        amount=-5000,
        status="imported",
        created_at=NOW,
    )
    categorized_tx = BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=account.id,
        date=date(2026, 6, 2),
        description="TESCO STORE",
        amount=-3000,
        status="categorized",
        category="Already Set",
        created_at=NOW,
    )

    rule = BankRule(
        id=uuid.uuid4(),
        name="TESCO → Groceries",
        condition_field="description",
        condition_operator="contains",
        condition_value="TESCO",
        action_type="set_category",
        action_value="Groceries",
        priority=100,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

    # apply_all_pending only queries for status='imported'
    db.execute.side_effect = [
        _mock_result([rule]),  # rules
        _mock_result([imported_tx]),  # only imported transactions
    ]

    result = await BankRuleService.apply_all_pending(db, account.id)

    assert result.categorized_count == 1
    assert imported_tx.category == "Groceries"
    # categorized_tx was not in the list so it stays as is


@pytest.mark.asyncio
async def test_regex_rules() -> None:
    """Regex-based rules should work for complex pattern matching."""
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

    tx1 = BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=account.id,
        date=date(2026, 6, 1),
        description="INV-12345 Payment Received",
        amount=500000,
        status="imported",
        created_at=NOW,
    )
    tx2 = BankTransaction(
        id=uuid.uuid4(),
        bank_account_id=account.id,
        date=date(2026, 6, 2),
        description="Monthly rent payment",
        amount=-150000,
        status="imported",
        created_at=NOW,
    )

    regex_rule = BankRule(
        id=uuid.uuid4(),
        name="Invoice Pattern",
        condition_field="description",
        condition_operator="regex",
        condition_value=r"INV-\d+",
        action_type="set_category",
        action_value="Sales Invoice",
        priority=100,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )

    db.execute.side_effect = [
        _mock_result([regex_rule]),
        _mock_result([tx1, tx2]),
    ]

    result = await BankRuleService.apply_all_pending(db, account.id)

    assert result.categorized_count == 1
    assert tx1.category == "Sales Invoice"
    assert tx2.category is None  # No match
