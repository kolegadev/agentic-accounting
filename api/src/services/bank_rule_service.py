"""Business logic for Bank Rules Engine — BankRuleService."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.bank_rule import BankRule
from src.models.bank_account import BankTransaction
from src.validators.bank_rule import (
    BankRuleCreate,
    BankRuleUpdate,
    BankRuleResponse,
    BankRuleApplyResponse,
    BankRuleLoadDefaultsResponse,
)
from src.validators.bank import BankTransactionResponse


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class BankRuleServiceError(Exception):
    """Base exception for bank rule service errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class BankRuleNotFoundError(BankRuleServiceError):
    """Bank rule not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Bank rule '{identifier}' not found", status_code=404)


# ---------------------------------------------------------------------------
# BankRuleService
# ---------------------------------------------------------------------------


class BankRuleService:
    """Stateless service for bank rule CRUD and auto-categorization."""

    # ------------------------------------------------------------------
    # Response mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _rule_to_response(rule: BankRule) -> BankRuleResponse:
        """Map a BankRule ORM instance to a response schema."""
        return BankRuleResponse.model_validate(rule)

    @staticmethod
    def _transaction_to_response(tx: BankTransaction) -> BankTransactionResponse:
        """Map a BankTransaction ORM instance to a response schema."""
        data = {
            "id": tx.id,
            "bank_account_id": tx.bank_account_id,
            "bank_account_name": tx.bank_account.name if tx.bank_account else None,
            "date": tx.date,
            "description": tx.description,
            "amount": tx.amount,
            "reference": tx.reference,
            "type": tx.type,
            "fitid": tx.fitid,
            "import_hash": tx.import_hash,
            "status": tx.status,
            "matched_transaction_id": tx.matched_transaction_id,
            "contact_id": tx.contact_id,
            "category": tx.category,
            "created_at": tx.created_at,
        }
        return BankTransactionResponse(**data)

    # ------------------------------------------------------------------
    # Condition evaluation
    # ------------------------------------------------------------------

    @staticmethod
    def _evaluate_condition(rule: BankRule, transaction: BankTransaction) -> bool:
        """Check whether a transaction matches the rule's condition."""
        # Get the field value from the transaction
        if rule.condition_field == "description":
            field_value = transaction.description or ""
        elif rule.condition_field == "amount":
            field_value = transaction.amount
        elif rule.condition_field == "reference":
            field_value = transaction.reference or ""
        else:
            return False

        operator = rule.condition_operator
        cond_value = rule.condition_value

        if operator == "contains":
            return cond_value.lower() in str(field_value).lower()
        elif operator == "equals":
            if rule.condition_field == "amount":
                try:
                    return field_value == int(cond_value)
                except (ValueError, TypeError):
                    return False
            return str(field_value).strip().lower() == cond_value.strip().lower()
        elif operator == "starts_with":
            return str(field_value).lower().startswith(cond_value.lower())
        elif operator == "regex":
            try:
                return bool(re.search(cond_value, str(field_value), re.IGNORECASE))
            except re.error:
                return False
        elif operator == "greater_than":
            try:
                if rule.condition_field == "amount":
                    return field_value > int(cond_value)
                return float(field_value) > float(cond_value)
            except (ValueError, TypeError):
                return False
        elif operator == "less_than":
            try:
                if rule.condition_field == "amount":
                    return field_value < int(cond_value)
                return float(field_value) < float(cond_value)
            except (ValueError, TypeError):
                return False

        return False

    # ------------------------------------------------------------------
    # Apply rules to a single transaction
    # ------------------------------------------------------------------

    @staticmethod
    async def apply_rules(
        db: AsyncSession,
        bank_transaction_id: uuid.UUID,
    ) -> Optional[BankTransactionResponse]:
        """Apply matching rules to a single bank transaction.

        Loads all active rules ordered by priority, applies the first match
        (by priority), and updates the transaction status from 'imported' to
        'categorized'.

        Returns the updated transaction, or None if not found.
        """
        # Load the transaction
        stmt = select(BankTransaction).where(BankTransaction.id == bank_transaction_id)
        result = await db.execute(stmt)
        tx = result.scalar_one_or_none()

        if tx is None:
            raise BankRuleServiceError(
                f"Bank transaction '{bank_transaction_id}' not found", status_code=404
            )

        # Only apply rules to imported transactions
        if tx.status != "imported":
            return BankRuleService._transaction_to_response(tx)

        # Load all active rules ordered by priority (lowest first = highest priority)
        rules_stmt = (
            select(BankRule)
            .where(BankRule.is_active == True)  # noqa: E712
            .order_by(BankRule.priority.asc())
        )
        rules_result = await db.execute(rules_stmt)
        rules = list(rules_result.scalars().all())

        # Find first matching rule
        matched = False
        for rule in rules:
            if BankRuleService._evaluate_condition(rule, tx):
                # Apply the action
                if rule.action_type == "set_category":
                    tx.category = rule.action_value
                elif rule.action_type == "set_contact":
                    # We store the contact name in category for now;
                    # matching by contact UUID requires a lookup service
                    # which is outside the scope of this simple rules engine
                    tx.category = rule.action_value
                    # Note: contact_id would need a lookup by name
                elif rule.action_type == "set_account":
                    # Store account code suggestion in category
                    tx.category = rule.action_value

                matched = True
                break  # First match wins

        if matched:
            tx.status = "categorized"

        await db.commit()
        await db.refresh(tx)
        return BankRuleService._transaction_to_response(tx)

    # ------------------------------------------------------------------
    # Apply rules to all pending transactions for an account
    # ------------------------------------------------------------------

    @staticmethod
    async def apply_all_pending(
        db: AsyncSession,
        bank_account_id: uuid.UUID,
    ) -> BankRuleApplyResponse:
        """Apply rules to all uncategorized ('imported') transactions
        for a given bank account.

        Returns the count of transactions categorized.
        """
        # Load all active rules ordered by priority
        rules_stmt = (
            select(BankRule)
            .where(BankRule.is_active == True)  # noqa: E712
            .order_by(BankRule.priority.asc())
        )
        rules_result = await db.execute(rules_stmt)
        rules = list(rules_result.scalars().all())

        if not rules:
            return BankRuleApplyResponse(categorized_count=0)

        # Load all imported transactions for this account
        tx_stmt = (
            select(BankTransaction)
            .where(
                and_(
                    BankTransaction.bank_account_id == bank_account_id,
                    BankTransaction.status == "imported",
                )
            )
            .order_by(BankTransaction.date.asc())
        )
        tx_result = await db.execute(tx_stmt)
        transactions = list(tx_result.scalars().all())

        categorized_count = 0

        for tx in transactions:
            for rule in rules:
                if BankRuleService._evaluate_condition(rule, tx):
                    if rule.action_type == "set_category":
                        tx.category = rule.action_value
                    elif rule.action_type == "set_contact":
                        tx.category = rule.action_value
                    elif rule.action_type == "set_account":
                        tx.category = rule.action_value

                    tx.status = "categorized"
                    categorized_count += 1
                    break  # First match wins

        if categorized_count > 0:
            await db.commit()

        return BankRuleApplyResponse(categorized_count=categorized_count)

    # ------------------------------------------------------------------
    # Rule CRUD
    # ------------------------------------------------------------------

    @staticmethod
    async def create_rule(
        db: AsyncSession,
        data: BankRuleCreate,
    ) -> BankRuleResponse:
        """Create a new bank rule."""
        rule = BankRule(
            name=data.name,
            condition_field=data.condition_field,
            condition_operator=data.condition_operator,
            condition_value=data.condition_value,
            action_type=data.action_type,
            action_value=data.action_value,
            priority=data.priority,
            is_active=data.is_active,
        )
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
        return BankRuleService._rule_to_response(rule)

    @staticmethod
    async def list_rules(
        db: AsyncSession,
        include_inactive: bool = False,
    ) -> list[BankRuleResponse]:
        """List all bank rules ordered by priority."""
        stmt = select(BankRule).order_by(BankRule.priority.asc(), BankRule.name.asc())
        if not include_inactive:
            stmt = stmt.where(BankRule.is_active == True)  # noqa: E712
        result = await db.execute(stmt)
        rules = list(result.scalars().all())
        return [BankRuleService._rule_to_response(r) for r in rules]

    @staticmethod
    async def update_rule(
        db: AsyncSession,
        rule_id: uuid.UUID,
        data: BankRuleUpdate,
    ) -> BankRuleResponse:
        """Update an existing bank rule (partial update)."""
        stmt = select(BankRule).where(BankRule.id == rule_id)
        result = await db.execute(stmt)
        rule = result.scalar_one_or_none()

        if rule is None:
            raise BankRuleNotFoundError(str(rule_id))

        # Apply partial updates
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(rule, key, value)

        await db.commit()
        await db.refresh(rule)
        return BankRuleService._rule_to_response(rule)

    @staticmethod
    async def delete_rule(
        db: AsyncSession,
        rule_id: uuid.UUID,
    ) -> None:
        """Delete a bank rule by ID."""
        stmt = select(BankRule).where(BankRule.id == rule_id)
        result = await db.execute(stmt)
        rule = result.scalar_one_or_none()

        if rule is None:
            raise BankRuleNotFoundError(str(rule_id))

        await db.delete(rule)
        await db.commit()

    # ------------------------------------------------------------------
    # Load default rules from JSON template
    # ------------------------------------------------------------------

    @staticmethod
    def _load_rules_json() -> list[dict]:
        """Load rules from the rules.json template file."""
        template_path = Path(__file__).parent.parent / "bank_templates" / "rules.json"
        if not template_path.exists():
            raise BankRuleServiceError(
                "Default rules template not found at bank_templates/rules.json",
                status_code=500,
            )
        with open(template_path, "r") as f:
            data = json.load(f)
        return data.get("rules", [])

    @staticmethod
    async def load_default_rules(
        db: AsyncSession,
    ) -> BankRuleLoadDefaultsResponse:
        """Load pre-built rules from rules.json into the database.

        Skips rules that already exist (matched by name).
        """
        rules_data = BankRuleService._load_rules_json()

        # Get existing rule names for dedup
        existing_stmt = select(BankRule.name)
        existing_result = await db.execute(existing_stmt)
        existing_names: set[str] = set(existing_result.scalars().all())

        created_count = 0
        skipped_count = 0

        for rule_data in rules_data:
            if rule_data["name"] in existing_names:
                skipped_count += 1
                continue

            rule = BankRule(
                name=rule_data["name"],
                condition_field=rule_data["condition_field"],
                condition_operator=rule_data["condition_operator"],
                condition_value=rule_data["condition_value"],
                action_type=rule_data["action_type"],
                action_value=rule_data["action_value"],
                priority=rule_data.get("priority", 1000),
                is_active=rule_data.get("is_active", True),
            )
            db.add(rule)
            existing_names.add(rule_data["name"])
            created_count += 1

        if created_count > 0:
            await db.commit()

        return BankRuleLoadDefaultsResponse(
            created_count=created_count,
            skipped_count=skipped_count,
        )
