"""Business logic for Chart of Accounts — CoaService."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.account import Account, CATEGORY_CODE_RANGES
from src.validators.account import AccountCreate, AccountResponse, AccountUpdate

COA_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "coa_templates"


class CoaServiceError(Exception):
    """Base exception for COA service errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class DuplicateCodeError(CoaServiceError):
    """Account code already exists."""

    def __init__(self, code: str) -> None:
        super().__init__(f"Account code '{code}' already exists", status_code=409)


class AccountNotFoundError(CoaServiceError):
    """Account not found."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"Account '{identifier}' not found", status_code=404)


class TemplateNotFoundError(CoaServiceError):
    """COA template not found."""

    def __init__(self, template_name: str) -> None:
        super().__init__(f"COA template '{template_name}' not found", status_code=404)


class InvalidCodeRangeError(CoaServiceError):
    """Account code not in valid range for its category."""

    def __init__(self, code: str, category: str) -> None:
        min_val, max_val = CATEGORY_CODE_RANGES.get(category, (0, 0))
        super().__init__(
            f"Code '{code}' is not in valid range {min_val}-{max_val} for category '{category}'",
            status_code=422,
        )


class CoaService:
    """Stateless service for Chart of Accounts CRUD operations."""

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _account_to_response(account: Account) -> AccountResponse:
        """Map an ORM Account instance to an AccountResponse Pydantic model."""
        return AccountResponse.model_validate(account)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    async def list_accounts(
        db: AsyncSession,
        *,
        include_inactive: bool = False,
    ) -> list[AccountResponse]:
        """Return all active (or all) accounts ordered by code."""
        stmt = select(Account)
        if not include_inactive:
            stmt = stmt.where(Account.is_active.is_(True))
        stmt = stmt.order_by(Account.code)
        result = await db.execute(stmt)
        accounts = result.scalars().all()
        return [CoaService._account_to_response(a) for a in accounts]

    @staticmethod
    async def get_account(
        db: AsyncSession,
        account_id: uuid.UUID,
    ) -> AccountResponse | None:
        """Return a single account by ID, or None if not found."""
        stmt = select(Account).where(Account.id == account_id)
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        return CoaService._account_to_response(account) if account else None

    @staticmethod
    async def get_account_by_code(
        db: AsyncSession,
        code: str,
    ) -> AccountResponse | None:
        """Return a single account by code, or None if not found."""
        stmt = select(Account).where(Account.code == code)
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        return CoaService._account_to_response(account) if account else None

    @staticmethod
    async def create_account(
        db: AsyncSession,
        data: AccountCreate,
    ) -> AccountResponse:
        """Create a new account after validating uniqueness and code range."""
        # Validate code uniqueness
        existing = await CoaService.get_account_by_code(db, data.code)
        if existing:
            raise DuplicateCodeError(data.code)

        # Validate code range for category
        if not Account.validate_code_for_category(data.code, data.category):
            raise InvalidCodeRangeError(data.code, data.category)

        account = Account(
            code=data.code,
            name=data.name,
            category=data.category,
            type=data.type,
            vat_rate=data.vat_rate,
            parent_id=data.parent_id,
        )
        db.add(account)
        await db.commit()
        await db.refresh(account)
        return CoaService._account_to_response(account)

    @staticmethod
    async def update_account(
        db: AsyncSession,
        account_id: uuid.UUID,
        data: AccountUpdate,
    ) -> AccountResponse:
        """Partially update an account. Returns updated account."""
        stmt = select(Account).where(Account.id == account_id)
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        if account is None:
            raise AccountNotFoundError(str(account_id))

        update_data = data.model_dump(exclude_unset=True)

        # If category changes, validate code range
        if "category" in update_data:
            new_category = update_data["category"]
            if not Account.validate_code_for_category(account.code, new_category):
                raise InvalidCodeRangeError(account.code, new_category)

        for field, value in update_data.items():
            setattr(account, field, value)

        await db.commit()
        await db.refresh(account)
        return CoaService._account_to_response(account)

    @staticmethod
    async def soft_delete_account(
        db: AsyncSession,
        account_id: uuid.UUID,
    ) -> AccountResponse:
        """Soft-delete an account by setting is_active=False."""
        stmt = select(Account).where(Account.id == account_id)
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        if account is None:
            raise AccountNotFoundError(str(account_id))

        account.is_active = False
        await db.commit()
        await db.refresh(account)
        return CoaService._account_to_response(account)

    @staticmethod
    async def set_vat_rate(
        db: AsyncSession,
        account_id: uuid.UUID,
        vat_rate: str,
    ) -> AccountResponse:
        """Set or update the VAT rate on an account."""
        stmt = select(Account).where(Account.id == account_id)
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        if account is None:
            raise AccountNotFoundError(str(account_id))

        account.vat_rate = vat_rate
        await db.commit()
        await db.refresh(account)
        return CoaService._account_to_response(account)

    @staticmethod
    async def load_template(
        db: AsyncSession,
        template_name: str,
    ) -> list[AccountResponse]:
        """Load a COA template from JSON and bulk insert accounts.

        The template file is expected at:
            api/src/coa_templates/{template_name}.json

        Does fuzzy matching: 'uk_sole_trader' matches
        'uk_sole_trader_vat.json' or 'uk_sole_trader_no_vat.json'.
        """
        # Direct match first
        template_path = COA_TEMPLATES_DIR / f"{template_name}.json"
        if not template_path.exists():
            # Fuzzy match: look for files starting with template_name
            candidates = sorted(COA_TEMPLATES_DIR.glob(f"{template_name}*.json"))
            if not candidates:
                # Try without VAT/no-VAT suffix
                for suffix in ("_vat", "_no_vat"):
                    alt = COA_TEMPLATES_DIR / f"{template_name}{suffix}.json"
                    if alt.exists():
                        candidates = [alt]
                        break
            if not candidates:
                raise TemplateNotFoundError(template_name)
            template_path = candidates[0]

        with open(template_path, encoding="utf-8") as fh:
            accounts_data = json.load(fh)

        created: list[Account] = []
        for item in accounts_data:
            # Check for existing account by code to avoid duplicates
            existing = await db.execute(
                select(Account).where(Account.code == item["code"])
            )
            if existing.scalar_one_or_none():
                # Skip if account already exists (idempotent template load)
                continue

            account = Account(
                code=item["code"],
                name=item["name"],
                category=item["category"],
                type=item["type"],
                vat_rate=item.get("vat_rate"),
            )
            db.add(account)
            created.append(account)

        if created:
            await db.commit()
            for acct in created:
                await db.refresh(acct)

        return [CoaService._account_to_response(a) for a in created]

    @staticmethod
    def validate_account_code(code: str, category: str) -> bool:
        """Validate that an account code is in the correct range for its category.

        Returns True if valid, False otherwise.
        """
        return Account.validate_code_for_category(code, category)

    @staticmethod
    def list_available_templates() -> list[str]:
        """Return the names of available COA template files."""
        if not COA_TEMPLATES_DIR.exists():
            return []
        return sorted(
            path.stem
            for path in COA_TEMPLATES_DIR.glob("*.json")
        )
