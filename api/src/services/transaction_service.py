"""Business logic for Core General Ledger — TransactionService."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.account import Account
from src.models.transaction import Posting, Transaction, VATLine
from src.validators.transaction import (
    PostingCreate,
    PostingResponse,
    TransactionCreate,
    TransactionResponse,
    VATLineResponse,
)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class TransactionServiceError(Exception):
    """Base exception for transaction service errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class UnbalancedTransactionError(TransactionServiceError):
    """Debits do not equal credits."""

    def __init__(self, total_debits: int = 0, total_credits: int = 0) -> None:
        super().__init__(
            f"Transaction unbalanced: total debits {total_debits} != "
            f"total credits {total_credits} (in pence)",
            status_code=422,
        )


class AccountNotFoundError(TransactionServiceError):
    """Referenced account does not exist."""

    def __init__(self, account_id: uuid.UUID) -> None:
        super().__init__(
            f"Account '{account_id}' not found or is inactive",
            status_code=404,
        )


class TransactionNotFoundError(TransactionServiceError):
    """Referenced transaction does not exist."""

    def __init__(self, transaction_id: uuid.UUID) -> None:
        super().__init__(
            f"Transaction '{transaction_id}' not found",
            status_code=404,
        )


class TransactionNotDraftError(TransactionServiceError):
    """Transaction is not in draft status — cannot be modified."""

    def __init__(self, transaction_id: uuid.UUID, current_status: str) -> None:
        super().__init__(
            f"Transaction '{transaction_id}' has status '{current_status}', "
            f"expected 'draft'",
            status_code=422,
        )


class IdempotencyConflictError(TransactionServiceError):
    """Duplicate idempotency key detected."""

    def __init__(self, idempotency_key: uuid.UUID, existing_transaction_id: uuid.UUID) -> None:
        self.existing_transaction_id = existing_transaction_id
        super().__init__(
            f"Idempotency key '{idempotency_key}' already used by "
            f"transaction '{existing_transaction_id}'",
            status_code=409,
        )


# ---------------------------------------------------------------------------
# TransactionService
# ---------------------------------------------------------------------------

class TransactionService:
    """Stateless service for Transaction CRUD and lifecycle operations."""

    # ------------------------------------------------------------------
    # Response mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _posting_to_response(posting: Posting) -> PostingResponse:
        """Map an ORM Posting to a PostingResponse."""
        return PostingResponse(
            id=posting.id,
            transaction_id=posting.transaction_id,
            account_id=posting.account_id,
            account_code=posting.account.code if posting.account else None,
            account_name=posting.account.name if posting.account else None,
            debit_amount=posting.debit_amount,
            credit_amount=posting.credit_amount,
            description=posting.description,
            vat_lines=[
                VATLineResponse(
                    id=vl.id,
                    posting_id=vl.posting_id,
                    vat_rate=vl.vat_rate,
                    vat_amount=vl.vat_amount,
                    net_amount=vl.net_amount,
                    vat_type=vl.vat_type,
                )
                for vl in (posting.vat_lines or [])
            ],
            created_at=posting.created_at,
        )

    @staticmethod
    def _transaction_to_response(transaction: Transaction) -> TransactionResponse:
        """Map an ORM Transaction to a TransactionResponse."""
        return TransactionResponse(
            id=transaction.id,
            reference=transaction.reference,
            description=transaction.description,
            contact_id=transaction.contact_id,
            total_amount=transaction.total_amount,
            currency=transaction.currency,
            status=transaction.status,
            effective_date=transaction.effective_date,
            idempotency_key=transaction.idempotency_key,
            recorded_at=transaction.recorded_at,
            postings=[
                TransactionService._posting_to_response(p)
                for p in (transaction.postings or [])
            ],
            created_at=transaction.created_at,
            updated_at=transaction.updated_at,
        )

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_postings(postings: list[PostingCreate]) -> None:
        """Validate double-entry: sum(debits) == sum(credits) and > 0.

        Raises ValueError if validation fails.
        """
        total_debits = sum(p.debit_amount for p in postings)
        total_credits = sum(p.credit_amount for p in postings)

        if total_debits == 0 and total_credits == 0:
            raise ValueError("Transaction must have at least one positive amount")

        if total_debits != total_credits:
            raise ValueError(
                f"Transaction unbalanced: debits {total_debits} != credits {total_credits}"
            )

    @staticmethod
    async def _validate_accounts(
        db: AsyncSession,
        account_ids: set[uuid.UUID],
    ) -> None:
        """Verify all referenced accounts exist and are active.

        Raises AccountNotFoundError if any account is missing or inactive.
        """
        if not account_ids:
            return

        stmt = select(Account).where(Account.id.in_(account_ids))
        result = await db.execute(stmt)
        found = {a.id: a for a in result.scalars().all()}

        for account_id in account_ids:
            account = found.get(account_id)
            if account is None:
                raise AccountNotFoundError(account_id)
            if not account.is_active:
                raise AccountNotFoundError(account_id)

    @staticmethod
    async def _generate_je_reference(
        db: AsyncSession,
        effective_date: date,
    ) -> str:
        """Generate next JE-YYYY-NNNN reference for the given year.

        Sequential numbers reset each calendar year.  Uses a SELECT FOR
        UPDATE-style approach with advisory locks left to the DB.
        """
        year = effective_date.year if effective_date else date.today().year

        # Find the highest existing NNNN for this year
        prefix = f"JE-{year}-"
        stmt = (
            select(Transaction.reference)
            .where(
                Transaction.reference.like(f"{prefix}%"),
            )
            .order_by(Transaction.reference.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        last_ref = result.scalar_one_or_none()

        if last_ref:
            try:
                last_seq = int(last_ref[len(prefix):])
                next_seq = last_seq + 1
            except (ValueError, IndexError):
                next_seq = 1
        else:
            next_seq = 1

        return f"{prefix}{next_seq:04d}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    async def create_transaction(
        db: AsyncSession,
        data: TransactionCreate,
    ) -> Transaction:
        """Create a new transaction in Draft status.

        Checks idempotency — if the idempotency_key already exists,
        returns the existing transaction (or raises if the caller prefers
        to handle it differently).
        """
        # ---- Idempotency check ----
        existing = await db.execute(
            select(Transaction).where(
                Transaction.idempotency_key == data.idempotency_key
            )
        )
        existing_tx = existing.scalar_one_or_none()
        if existing_tx is not None:
            raise IdempotencyConflictError(
                data.idempotency_key,
                existing_tx.id,
            )

        # ---- Validate accounts ----
        account_ids = {p.account_id for p in data.postings}
        await TransactionService._validate_accounts(db, account_ids)

        # ---- Create transaction ----
        total_amount = sum(
            p.debit_amount for p in data.postings
        )  # debits == credits at this point

        transaction = Transaction(
            description=data.description,
            contact_id=data.contact_id,
            currency=data.currency,
            status="draft",
            effective_date=data.effective_date,
            idempotency_key=data.idempotency_key,
            total_amount=total_amount,
        )
        db.add(transaction)
        await db.flush()  # Get transaction.id for postings

        # ---- Create postings ----
        for p_data in data.postings:
            posting = Posting(
                transaction_id=transaction.id,
                account_id=p_data.account_id,
                debit_amount=p_data.debit_amount,
                credit_amount=p_data.credit_amount,
                description=p_data.description,
            )
            db.add(posting)

        await db.commit()
        await db.refresh(transaction, attribute_names=["postings"])
        return transaction

    @staticmethod
    async def post_transaction(
        db: AsyncSession,
        transaction_id: uuid.UUID,
    ) -> Transaction:
        """Post a Draft transaction — validates, assigns JE ref, sets status.

        Raises TransactionNotFoundError, TransactionNotDraftError,
        or UnbalancedTransactionError.
        """
        # ---- Load transaction with postings ----
        stmt = (
            select(Transaction)
            .where(Transaction.id == transaction_id)
            .options(selectinload(Transaction.postings))
        )
        result = await db.execute(stmt)
        transaction = result.scalar_one_or_none()

        if transaction is None:
            raise TransactionNotFoundError(transaction_id)

        if transaction.status != "draft":
            raise TransactionNotDraftError(transaction_id, transaction.status)

        # ---- Validate postings ----
        total_debits = sum(p.debit_amount for p in transaction.postings)
        total_credits = sum(p.credit_amount for p in transaction.postings)

        if total_debits == 0 and total_credits == 0:
            raise UnbalancedTransactionError(total_debits, total_credits)
        if total_debits != total_credits:
            raise UnbalancedTransactionError(total_debits, total_credits)

        # ---- Assign JE reference ----
        effective = transaction.effective_date or date.today()
        reference = await TransactionService._generate_je_reference(db, effective)

        transaction.reference = reference
        transaction.status = "posted"
        transaction.recorded_at = datetime.now(timezone.utc)
        transaction.total_amount = total_debits

        await db.commit()
        await db.refresh(transaction, attribute_names=["postings"])
        return transaction

    @staticmethod
    async def get_transaction(
        db: AsyncSession,
        transaction_id: uuid.UUID,
    ) -> Optional[Transaction]:
        """Get a transaction by ID, including postings and their account details."""
        stmt = (
            select(Transaction)
            .where(Transaction.id == transaction_id)
            .options(
                selectinload(Transaction.postings)
                .selectinload(Posting.account),
            )
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_transactions(
        db: AsyncSession,
        *,
        status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        contact_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Transaction], int]:
        """List transactions with optional filters. Returns (items, total_count)."""
        stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.postings)
                .selectinload(Posting.account),
            )
        )

        # ---- Filters ----
        if status:
            stmt = stmt.where(Transaction.status == status)
        if date_from:
            stmt = stmt.where(Transaction.effective_date >= date_from)
        if date_to:
            stmt = stmt.where(Transaction.effective_date <= date_to)
        if contact_id:
            stmt = stmt.where(Transaction.contact_id == contact_id)

        # ---- Count ----
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        # ---- Fetch ----
        stmt = stmt.order_by(Transaction.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        transactions = list(result.scalars().all())

        return transactions, total

    @staticmethod
    async def reverse_transaction(
        db: AsyncSession,
        transaction_id: uuid.UUID,
    ) -> Transaction:
        """Create a reversing (compensating) entry for a Posted transaction.

        The original transaction is set to 'reversed' status, and a new
        transaction is created with debits/credits swapped.  The new
        transaction is automatically posted.
        """
        # ---- Load original ----
        stmt = (
            select(Transaction)
            .where(Transaction.id == transaction_id)
            .options(selectinload(Transaction.postings))
        )
        result = await db.execute(stmt)
        original = result.scalar_one_or_none()

        if original is None:
            raise TransactionNotFoundError(transaction_id)

        if original.status != "posted":
            raise TransactionNotDraftError(transaction_id, original.status)

        # ---- Build compensating postings ----
        reversed_postings: list[PostingCreate] = []
        for p in original.postings:
            reversed_postings.append(
                PostingCreate(
                    account_id=p.account_id,
                    debit_amount=p.credit_amount,  # swapped
                    credit_amount=p.debit_amount,  # swapped
                    description=f"Reversal of {p.description or 'posting'}",
                )
            )

        # ---- Create new reversing transaction ----
        total = sum(pp.debit_amount for pp in reversed_postings)
        reversing_tx = Transaction(
            description=f"Reversal of {original.reference or original.id}",
            contact_id=original.contact_id,
            currency=original.currency,
            status="posted",
            effective_date=date.today(),
            total_amount=total,
            reference=None,
        )
        db.add(reversing_tx)
        await db.flush()

        # Generate JE reference for the reversing entry
        effective = reversing_tx.effective_date or date.today()
        reference = await TransactionService._generate_je_reference(db, effective)
        reversing_tx.reference = reference
        reversing_tx.recorded_at = datetime.now(timezone.utc)

        # Add postings
        for rp in reversed_postings:
            posting = Posting(
                transaction_id=reversing_tx.id,
                account_id=rp.account_id,
                debit_amount=rp.debit_amount,
                credit_amount=rp.credit_amount,
                description=rp.description,
            )
            db.add(posting)

        # ---- Update original ----
        original.status = "reversed"

        await db.commit()
        await db.refresh(reversing_tx, attribute_names=["postings"])
        return reversing_tx
