"""Business logic for Manual Bank Reconciliation — ReconciliationService."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.bank_account import BankAccount, BankTransaction
from src.models.reconciliation import (
    ReconciliationMatch,
    ReconciliationSession,
)
from src.models.transaction import Transaction, Posting
from src.services.transaction_service import (
    AccountNotFoundError,
    TransactionService,
    TransactionServiceError,
)
from src.validators.reconciliation import (
    CreateAndMatchRequest,
    MatchRequest,
    ReconciliationMatchResponse,
    ReconciliationSessionResponse,
    ReconciliationReport,
    StartReconciliation,
)
from src.validators.transaction import PostingCreate, TransactionCreate


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class ReconciliationServiceError(Exception):
    """Base exception for reconciliation service errors."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class SessionNotFoundError(ReconciliationServiceError):
    """Reconciliation session not found."""

    def __init__(self, session_id: uuid.UUID) -> None:
        super().__init__(
            f"Reconciliation session '{session_id}' not found",
            status_code=404,
        )


class SessionClosedError(ReconciliationServiceError):
    """Session is already closed."""

    def __init__(self, session_id: uuid.UUID) -> None:
        super().__init__(
            f"Reconciliation session '{session_id}' is already closed",
            status_code=422,
        )


class BankAccountNotFoundError(ReconciliationServiceError):
    """Bank account not found."""

    def __init__(self, account_id: uuid.UUID) -> None:
        super().__init__(
            f"Bank account '{account_id}' not found",
            status_code=404,
        )


class BankTransactionNotFoundError(ReconciliationServiceError):
    """Bank transaction not found."""

    def __init__(self, transaction_id: uuid.UUID) -> None:
        super().__init__(
            f"Bank transaction '{transaction_id}' not found",
            status_code=404,
        )


class TransactionNotFoundError(ReconciliationServiceError):
    """Ledger transaction not found."""

    def __init__(self, transaction_id: uuid.UUID) -> None:
        super().__init__(
            f"Transaction '{transaction_id}' not found",
            status_code=404,
        )


class BankTransactionAlreadyMatchedError(ReconciliationServiceError):
    """Bank transaction is already reconciled."""

    def __init__(self, transaction_id: uuid.UUID) -> None:
        super().__init__(
            f"Bank transaction '{transaction_id}' is already reconciled",
            status_code=422,
        )


# ---------------------------------------------------------------------------
# ReconciliationService
# ---------------------------------------------------------------------------


class ReconciliationService:
    """Stateless service for reconciliation session and match operations."""

    # ------------------------------------------------------------------
    # Response mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _session_to_response(session: ReconciliationSession) -> ReconciliationSessionResponse:
        """Map a ReconciliationSession ORM instance to a response schema."""
        return ReconciliationSessionResponse.model_validate(session)

    @staticmethod
    def _match_to_response(match: ReconciliationMatch) -> ReconciliationMatchResponse:
        """Map a ReconciliationMatch ORM instance to a response schema."""
        return ReconciliationMatchResponse.model_validate(match)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    @staticmethod
    async def start_session(
        db: AsyncSession,
        data: StartReconciliation,
    ) -> ReconciliationSessionResponse:
        """Create a new reconciliation session.

        Verifies the bank account exists and counts unmatched bank lines
        within the date range.
        """
        # Verify bank account exists
        stmt = select(BankAccount).where(BankAccount.id == data.bank_account_id)
        result = await db.execute(stmt)
        account = result.scalar_one_or_none()
        if account is None:
            raise BankAccountNotFoundError(data.bank_account_id)

        # Count total bank lines in date range
        count_stmt = select(func.count()).where(
            BankTransaction.bank_account_id == data.bank_account_id,
            BankTransaction.date >= data.start_date,
            BankTransaction.date <= data.end_date,
        )
        count_result = await db.execute(count_stmt)
        total_bank_lines = count_result.scalar_one()

        # Count unmatched bank lines
        unmatched_stmt = select(func.count()).where(
            BankTransaction.bank_account_id == data.bank_account_id,
            BankTransaction.date >= data.start_date,
            BankTransaction.date <= data.end_date,
            BankTransaction.status != "reconciled",
        )
        unmatched_result = await db.execute(unmatched_stmt)
        unmatched_count = unmatched_result.scalar_one()

        session = ReconciliationSession(
            bank_account_id=data.bank_account_id,
            start_date=data.start_date,
            end_date=data.end_date,
            opening_balance=data.opening_balance,
            closing_balance=data.closing_balance,
            total_bank_lines=total_bank_lines,
            unmatched_count=unmatched_count,
            matched_count=0,
            status="open",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return ReconciliationService._session_to_response(session)

    # ------------------------------------------------------------------
    # Matching operations
    # ------------------------------------------------------------------

    @staticmethod
    async def _get_open_session(
        db: AsyncSession,
        session_id: uuid.UUID,
    ) -> ReconciliationSession:
        """Load a session, raising if not found or closed."""
        stmt = select(ReconciliationSession).where(
            ReconciliationSession.id == session_id
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        if session is None:
            raise SessionNotFoundError(session_id)
        if session.status == "closed":
            raise SessionClosedError(session_id)
        return session

    @staticmethod
    async def _get_bank_transaction(
        db: AsyncSession,
        bank_transaction_id: uuid.UUID,
    ) -> BankTransaction:
        """Load a bank transaction, raising if not found or already reconciled."""
        stmt = select(BankTransaction).where(
            BankTransaction.id == bank_transaction_id
        )
        result = await db.execute(stmt)
        bt = result.scalar_one_or_none()
        if bt is None:
            raise BankTransactionNotFoundError(bank_transaction_id)
        if bt.status == "reconciled":
            raise BankTransactionAlreadyMatchedError(bank_transaction_id)
        return bt

    @staticmethod
    async def _update_session_counts(
        db: AsyncSession,
        session: ReconciliationSession,
    ) -> None:
        """Recalculate matched/unmatched counts for the session."""
        # Count matches in this session
        matched_stmt = select(func.count()).where(
            ReconciliationMatch.session_id == session.id
        )
        matched_result = await db.execute(matched_stmt)
        matched_count = matched_result.scalar_one()

        # Count unmatched bank lines remaining
        unmatched_stmt = select(func.count()).where(
            BankTransaction.bank_account_id == session.bank_account_id,
            BankTransaction.date >= session.start_date,
            BankTransaction.date <= session.end_date,
            BankTransaction.status != "reconciled",
        )
        unmatched_result = await db.execute(unmatched_stmt)
        unmatched_count = unmatched_result.scalar_one()

        session.matched_count = matched_count
        session.unmatched_count = unmatched_count
        await db.commit()

    @staticmethod
    async def match_one_to_one(
        db: AsyncSession,
        session_id: uuid.UUID,
        bank_transaction_id: uuid.UUID,
        transaction_id: uuid.UUID,
    ) -> ReconciliationMatchResponse:
        """Match one bank transaction to exactly one ledger transaction.

        Verifies both exist, creates the match record, and marks the
        bank transaction as reconciled.
        """
        session = await ReconciliationService._get_open_session(db, session_id)
        bt = await ReconciliationService._get_bank_transaction(db, bank_transaction_id)

        # Verify ledger transaction exists
        stmt = select(Transaction).where(Transaction.id == transaction_id)
        result = await db.execute(stmt)
        tx = result.scalar_one_or_none()
        if tx is None:
            raise TransactionNotFoundError(transaction_id)

        # Calculate amount difference
        # Bank amount: negative = debit/out, positive = credit/in
        # For match comparison, use absolute values
        bank_abs = abs(bt.amount)
        ledger_abs = abs(tx.total_amount or 0)
        amount_difference = abs(bank_abs - ledger_abs)

        match_type = "one_to_one" if amount_difference == 0 else "partial"

        match = ReconciliationMatch(
            session_id=session.id,
            bank_transaction_id=bank_transaction_id,
            transaction_id=transaction_id,
            match_type=match_type,
            amount_difference=amount_difference,
        )
        db.add(match)

        # Mark bank transaction as reconciled
        bt.status = "reconciled"
        bt.matched_transaction_id = transaction_id

        await db.commit()
        await db.refresh(match)

        # Update session counts
        await ReconciliationService._update_session_counts(db, session)

        return ReconciliationService._match_to_response(match)

    @staticmethod
    async def match_one_to_many(
        db: AsyncSession,
        session_id: uuid.UUID,
        bank_transaction_id: uuid.UUID,
        transaction_ids: list[uuid.UUID],
    ) -> list[ReconciliationMatchResponse]:
        """Match one bank transaction to multiple ledger transactions.

        Creates a match record for each ledger transaction and tracks the
        total amount difference.
        """
        session = await ReconciliationService._get_open_session(db, session_id)
        bt = await ReconciliationService._get_bank_transaction(db, bank_transaction_id)

        # Verify all ledger transactions exist
        stmt = select(Transaction).where(Transaction.id.in_(transaction_ids))
        result = await db.execute(stmt)
        transactions = {t.id: t for t in result.scalars().all()}
        for tid in transaction_ids:
            if tid not in transactions:
                raise TransactionNotFoundError(tid)

        # Calculate total matched amount
        total_ledger_amount = sum(
            abs(t.total_amount or 0) for t in transactions.values()
        )
        bank_abs = abs(bt.amount)
        amount_difference = abs(bank_abs - total_ledger_amount)

        matches = []
        for i, tid in enumerate(transaction_ids):
            tx = transactions[tid]
            # First match gets the overall type, subsequent get one_to_many
            if i == 0:
                match_type = "one_to_many" if amount_difference == 0 else "partial"
            else:
                match_type = "one_to_many"

            match = ReconciliationMatch(
                session_id=session.id,
                bank_transaction_id=bank_transaction_id,
                transaction_id=tid,
                match_type=match_type,
                amount_difference=amount_difference if i == 0 else 0,
            )
            db.add(match)
            matches.append(match)

        # Mark bank transaction as reconciled
        bt.status = "reconciled"
        bt.matched_transaction_id = transaction_ids[0] if transaction_ids else None

        await db.commit()
        for m in matches:
            await db.refresh(m)

        # Update session counts
        await ReconciliationService._update_session_counts(db, session)

        return [ReconciliationService._match_to_response(m) for m in matches]

    @staticmethod
    async def create_and_match(
        db: AsyncSession,
        session_id: uuid.UUID,
        data: CreateAndMatchRequest,
    ) -> ReconciliationMatchResponse:
        """Create a new GL transaction via TransactionService and match it to a bank line.

        The bank_transaction_id must be a bank line that is not yet reconciled.
        The system creates a new double-entry transaction, posts it, and creates
        a match record.
        """
        session = await ReconciliationService._get_open_session(db, session_id)
        bt = await ReconciliationService._get_bank_transaction(db, data.bank_transaction_id)

        # Build TransactionCreate with debit/credit postings
        # The bank amount indicates direction: negative = money out (debit), positive = money in (credit)
        # Debit posting → debit_account_id, Credit posting → credit_account_id
        posting1 = PostingCreate(
            account_id=data.debit_account_id,
            debit_amount=data.amount,
            credit_amount=0,
            description=data.description,
        )
        posting2 = PostingCreate(
            account_id=data.credit_account_id,
            debit_amount=0,
            credit_amount=data.amount,
            description=data.description,
        )

        txn_data = TransactionCreate(
            description=data.description,
            currency="GBP",
            effective_date=bt.date,
            postings=[posting1, posting2],
            idempotency_key=uuid.uuid4(),
        )

        try:
            transaction = await TransactionService.create_transaction(db, txn_data)
            # Post the transaction
            transaction = await TransactionService.post_transaction(db, transaction.id)
        except AccountNotFoundError as exc:
            raise ReconciliationServiceError(exc.message, status_code=exc.status_code)
        except TransactionServiceError as exc:
            raise ReconciliationServiceError(exc.message, status_code=exc.status_code)

        # Calculate amount difference
        bank_abs = abs(bt.amount)
        ledger_abs = abs(transaction.total_amount or 0)
        amount_difference = abs(bank_abs - ledger_abs)

        match_type = "new_entry" if amount_difference == 0 else "partial"

        match = ReconciliationMatch(
            session_id=session.id,
            bank_transaction_id=data.bank_transaction_id,
            transaction_id=transaction.id,
            match_type=match_type,
            amount_difference=amount_difference,
            description=data.description,
        )
        db.add(match)

        # Mark bank transaction as reconciled
        bt.status = "reconciled"
        bt.matched_transaction_id = transaction.id

        await db.commit()
        await db.refresh(match)

        # Update session counts
        await ReconciliationService._update_session_counts(db, session)

        return ReconciliationService._match_to_response(match)

    # ------------------------------------------------------------------
    # Status & reporting
    # ------------------------------------------------------------------

    @staticmethod
    async def get_session_status(
        db: AsyncSession,
        session_id: uuid.UUID,
    ) -> ReconciliationSessionResponse:
        """Return the current status of a reconciliation session.

        Refreshes counts before returning.
        """
        stmt = select(ReconciliationSession).where(
            ReconciliationSession.id == session_id
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        if session is None:
            raise SessionNotFoundError(session_id)

        # Refresh counts
        await ReconciliationService._update_session_counts(db, session)
        await db.refresh(session)

        return ReconciliationService._session_to_response(session)

    @staticmethod
    async def generate_report(
        db: AsyncSession,
        session_id: uuid.UUID,
    ) -> ReconciliationReport:
        """Generate a reconciliation report for the session.

        Includes opening/closing balances, matched net amount, difference,
        and all match details.
        """
        stmt = select(ReconciliationSession).where(
            ReconciliationSession.id == session_id
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        if session is None:
            raise SessionNotFoundError(session_id)

        # Refresh counts
        await ReconciliationService._update_session_counts(db, session)

        # Get all matches
        matches_stmt = select(ReconciliationMatch).where(
            ReconciliationMatch.session_id == session.id
        ).order_by(ReconciliationMatch.created_at)
        matches_result = await db.execute(matches_stmt)
        matches = list(matches_result.scalars().all())

        # Calculate net matched amount from bank transactions
        matched_amount_stmt = select(func.coalesce(func.sum(BankTransaction.amount), 0)).where(
            BankTransaction.bank_account_id == session.bank_account_id,
            BankTransaction.date >= session.start_date,
            BankTransaction.date <= session.end_date,
            BankTransaction.status == "reconciled",
        )
        matched_result = await db.execute(matched_amount_stmt)
        matched_net_amount = matched_result.scalar_one()

        # Difference = opening_balance + matched_net_amount - closing_balance
        difference = session.opening_balance + matched_net_amount - session.closing_balance

        return ReconciliationReport(
            session_id=session.id,
            bank_account_id=session.bank_account_id,
            start_date=session.start_date,
            end_date=session.end_date,
            opening_balance=session.opening_balance,
            closing_balance=session.closing_balance,
            total_bank_lines=session.total_bank_lines,
            matched_count=session.matched_count,
            unmatched_count=session.unmatched_count,
            matched_net_amount=matched_net_amount,
            difference=difference,
            matches=[ReconciliationService._match_to_response(m) for m in matches],
        )

    @staticmethod
    async def close_session(
        db: AsyncSession,
        session_id: uuid.UUID,
    ) -> ReconciliationSessionResponse:
        """Close a reconciliation session.

        Sets status to 'closed' and records closed_at timestamp.
        """
        stmt = select(ReconciliationSession).where(
            ReconciliationSession.id == session_id
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        if session is None:
            raise SessionNotFoundError(session_id)

        if session.status == "closed":
            raise SessionClosedError(session_id)

        # Final count refresh
        await ReconciliationService._update_session_counts(db, session)

        session.status = "closed"
        session.closed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(session)

        return ReconciliationService._session_to_response(session)
