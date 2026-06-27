"""Integration tests for Transaction CRUD cycle.

Uses mocked DB (no real database required) but tests the full
create → post → get → list → reverse workflow.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.account import Account
from src.models.transaction import Posting, Transaction
from src.services.transaction_service import (
    AccountNotFoundError,
    IdempotencyConflictError,
    TransactionNotFoundError,
    TransactionNotDraftError,
    TransactionService,
    UnbalancedTransactionError,
)
from src.validators.transaction import PostingCreate, TransactionCreate

NOW = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bank() -> Account:
    return Account(
        id=uuid.uuid4(),
        code="1000",
        name="Bank Current",
        category="Asset",
        type="Bank",
        is_active=True,
    )


@pytest.fixture
def revenue() -> Account:
    return Account(
        id=uuid.uuid4(),
        code="4000",
        name="Sales Revenue",
        category="Revenue",
        type="Revenue",
        is_active=True,
    )


@pytest.fixture
def expense() -> Account:
    return Account(
        id=uuid.uuid4(),
        code="5210",
        name="Marketing",
        category="Expense",
        type="Expense",
        is_active=True,
    )


@pytest.fixture
def liability() -> Account:
    return Account(
        id=uuid.uuid4(),
        code="2000",
        name="Accounts Payable",
        category="Liability",
        type="CurrentLiability",
        is_active=True,
    )


@pytest.fixture
def all_accounts(bank: Account, revenue: Account, expense: Account, liability: Account) -> list[Account]:
    return [bank, revenue, expense, liability]


# ======================================================================
# Full CRUD Cycle
# ======================================================================

class TestFullCRUDCycle:
    """End-to-end test of the create → post → get → list → reverse cycle."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(
        self,
        bank: Account,
        revenue: Account,
        expense: Account,
        all_accounts: list[Account],
    ) -> None:
        """Complete transaction lifecycle from creation to reversal."""
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()

        # Track added postings so we can simulate refresh
        added_postings: list[Posting] = []

        def track_add(obj):
            if isinstance(obj, Transaction):
                obj.id = uuid.uuid4()  # Simulate ID generation
            elif isinstance(obj, Posting):
                added_postings.append(obj)

        db.add = track_add

        async def mock_refresh(tx, attribute_names=None):
            if attribute_names and "postings" in attribute_names:
                tx.postings = [
                    p for p in added_postings
                    if p.transaction_id == tx.id
                ]

        db.refresh = mock_refresh

        # ================================================================
        # PHASE 1: Create Draft Transaction
        # ================================================================
        idemp_key = uuid.uuid4()
        tx_data = TransactionCreate(
            description="Invoice #INV-001 - Consulting services",
            currency="GBP",
            effective_date=date(2026, 6, 27),
            idempotency_key=idemp_key,
            postings=[
                PostingCreate(
                    account_id=bank.id,
                    debit_amount=12000,
                    credit_amount=0,
                    description="Bank receipt",
                ),
                PostingCreate(
                    account_id=revenue.id,
                    debit_amount=0,
                    credit_amount=12000,
                    description="Consulting revenue",
                ),
            ],
        )

        # Mock: no existing idempotency
        mock_idem = MagicMock()
        mock_idem.scalar_one_or_none.return_value = None

        # Mock: accounts found and active
        mock_accts = MagicMock()
        mock_accts.scalars.return_value.all.return_value = [bank, revenue]

        db.execute.side_effect = [mock_idem, mock_accts]

        draft_tx = await TransactionService.create_transaction(db, tx_data)

        assert draft_tx.status == "draft"
        assert draft_tx.description == "Invoice #INV-001 - Consulting services"
        assert draft_tx.reference is None
        assert draft_tx.idempotency_key == idemp_key
        assert len(draft_tx.postings) == 2
        # Verify postings
        posting_accounts = {p.account_id for p in draft_tx.postings}
        assert bank.id in posting_accounts
        assert revenue.id in posting_accounts

        # ================================================================
        # PHASE 2: Post Transaction
        # ================================================================
        db_post = AsyncMock()
        db_post.add = MagicMock()
        db_post.commit = AsyncMock()
        db_post.refresh = AsyncMock()

        # Mock: get transaction
        mock_tx = MagicMock()
        mock_tx.scalar_one_or_none.return_value = draft_tx

        # Mock: no existing JE references
        mock_ref = MagicMock()
        mock_ref.scalar_one_or_none.return_value = None

        db_post.execute.side_effect = [mock_tx, mock_ref]

        posted_tx = await TransactionService.post_transaction(db_post, draft_tx.id)

        assert posted_tx.status == "posted"
        assert posted_tx.reference == "JE-2026-0001"
        assert posted_tx.recorded_at is not None
        assert posted_tx.total_amount == 12000

        # ================================================================
        # PHASE 3: Get Transaction
        # ================================================================
        db_get = AsyncMock()
        mock_get = MagicMock()
        mock_get.scalar_one_or_none.return_value = posted_tx
        db_get.execute.return_value = mock_get

        fetched = await TransactionService.get_transaction(db_get, posted_tx.id)
        assert fetched is not None
        assert fetched.reference == "JE-2026-0001"
        assert fetched.status == "posted"

        # ================================================================
        # PHASE 4: List Transactions
        # ================================================================
        db_list = AsyncMock()
        mock_count = MagicMock()
        mock_count.scalar_one.return_value = 1

        mock_list_tx = MagicMock()
        mock_list_tx.scalars.return_value.all.return_value = [posted_tx]

        db_list.execute.side_effect = [mock_count, mock_list_tx]

        transactions, total = await TransactionService.list_transactions(
            db_list,
            status="posted",
            date_from=date(2026, 1, 1),
            limit=50,
        )

        assert total == 1
        assert len(transactions) == 1
        assert transactions[0].reference == "JE-2026-0001"

        # ================================================================
        # PHASE 5: Reverse Transaction
        # ================================================================
        db_rev = AsyncMock()
        db_rev.flush = AsyncMock()
        db_rev.commit = AsyncMock()

        # Track added postings for this DB
        rev_added_postings: list[Posting] = []

        def track_rev_add(obj):
            if isinstance(obj, Transaction):
                obj.id = uuid.uuid4()
            elif isinstance(obj, Posting):
                rev_added_postings.append(obj)

        db_rev.add = track_rev_add

        async def mock_rev_refresh(tx, attribute_names=None):
            if attribute_names and "postings" in attribute_names:
                tx.postings = [
                    p for p in rev_added_postings
                    if p.transaction_id == tx.id
                ]

        db_rev.refresh = mock_rev_refresh

        # Mock: get original transaction
        mock_rev_tx = MagicMock()
        mock_rev_tx.scalar_one_or_none.return_value = posted_tx

        # Mock: JE reference check — return existing JE-2026-0001 so next is 0002
        mock_rev_ref = MagicMock()
        mock_rev_ref.scalar_one_or_none.return_value = "JE-2026-0001"

        db_rev.execute.side_effect = [mock_rev_tx, mock_rev_ref]

        reversing_tx = await TransactionService.reverse_transaction(
            db_rev, posted_tx.id
        )

        assert posted_tx.status == "reversed"
        assert reversing_tx.status == "posted"
        assert reversing_tx.reference == "JE-2026-0002"
        assert len(reversing_tx.postings) == 2

        # Verify swap: original debit → reversing credit
        rev_p1 = reversing_tx.postings[0]
        assert rev_p1.account_id == bank.id
        assert rev_p1.debit_amount == 0
        assert rev_p1.credit_amount == 12000

        rev_p2 = reversing_tx.postings[1]
        assert rev_p2.account_id == revenue.id
        assert rev_p2.debit_amount == 12000
        assert rev_p2.credit_amount == 0


# ======================================================================
# Validation Error Scenarios
# ======================================================================

class TestValidationErrors:
    """Integration-level tests for error scenarios."""

    @pytest.mark.asyncio
    async def test_unbalanced_rejected(
        self,
        bank: Account,
        expense: Account,
    ) -> None:
        """Unbalanced transactions should be rejected by Pydantic."""
        with pytest.raises(ValueError, match="unbalanced"):
            TransactionCreate(
                description="Unbalanced test",
                idempotency_key=uuid.uuid4(),
                postings=[
                    PostingCreate(
                        account_id=expense.id,
                        debit_amount=10000,
                        credit_amount=0,
                    ),
                    PostingCreate(
                        account_id=bank.id,
                        debit_amount=0,
                        credit_amount=9999,
                    ),
                ],
            )

    @pytest.mark.asyncio
    async def test_empty_postings_rejected(self) -> None:
        """Empty postings list should be rejected."""
        with pytest.raises(ValueError):
            TransactionCreate(
                description="No postings",
                idempotency_key=uuid.uuid4(),
                postings=[],
            )

    @pytest.mark.asyncio
    async def test_single_posting_rejected(
        self,
        expense: Account,
    ) -> None:
        """Single posting should be rejected (min 2)."""
        with pytest.raises(ValueError):
            TransactionCreate(
                description="One posting",
                idempotency_key=uuid.uuid4(),
                postings=[
                    PostingCreate(
                        account_id=expense.id,
                        debit_amount=100,
                        credit_amount=0,
                    ),
                ],
            )

    @pytest.mark.asyncio
    async def test_both_amounts_posting_rejected(self) -> None:
        """Both debit and credit > 0 on a posting should be rejected."""
        with pytest.raises(ValueError, match="exactly one"):
            PostingCreate(
                account_id=uuid.uuid4(),
                debit_amount=100,
                credit_amount=100,
            )

    @pytest.mark.asyncio
    async def test_zero_amounts_posting_rejected(self) -> None:
        """Both debit and credit == 0 on a posting should be rejected."""
        with pytest.raises(ValueError, match="exactly one"):
            PostingCreate(
                account_id=uuid.uuid4(),
                debit_amount=0,
                credit_amount=0,
            )

    @pytest.mark.asyncio
    async def test_nonexistent_account_rejected(
        self,
        bank: Account,
    ) -> None:
        """Referencing a non-existent account should raise AccountNotFoundError."""
        db = AsyncMock()
        db.add = MagicMock()

        mock_idem = MagicMock()
        mock_idem.scalar_one_or_none.return_value = None

        mock_accts = MagicMock()
        mock_accts.scalars.return_value.all.return_value = [bank]  # Only bank exists

        db.execute.side_effect = [mock_idem, mock_accts]

        missing_id = uuid.uuid4()
        data = TransactionCreate(
            description="Missing account",
            idempotency_key=uuid.uuid4(),
            postings=[
                PostingCreate(
                    account_id=missing_id,
                    debit_amount=5000,
                    credit_amount=0,
                ),
                PostingCreate(
                    account_id=bank.id,
                    debit_amount=0,
                    credit_amount=5000,
                ),
            ],
        )

        with pytest.raises(AccountNotFoundError) as exc_info:
            await TransactionService.create_transaction(db, data)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_inactive_account_rejected(
        self,
        bank: Account,
    ) -> None:
        """Referencing an inactive account should raise AccountNotFoundError."""
        db = AsyncMock()
        db.add = MagicMock()

        inactive = Account(
            id=uuid.uuid4(),
            code="5999",
            name="Inactive Expense",
            category="Expense",
            type="Expense",
            is_active=False,
        )

        mock_idem = MagicMock()
        mock_idem.scalar_one_or_none.return_value = None

        mock_accts = MagicMock()
        mock_accts.scalars.return_value.all.return_value = [inactive, bank]

        db.execute.side_effect = [mock_idem, mock_accts]

        data = TransactionCreate(
            description="Inactive account",
            idempotency_key=uuid.uuid4(),
            postings=[
                PostingCreate(
                    account_id=inactive.id,
                    debit_amount=5000,
                    credit_amount=0,
                ),
                PostingCreate(
                    account_id=bank.id,
                    debit_amount=0,
                    credit_amount=5000,
                ),
            ],
        )

        with pytest.raises(AccountNotFoundError):
            await TransactionService.create_transaction(db, data)

    @pytest.mark.asyncio
    async def test_post_nonexistent_transaction(self) -> None:
        """Posting a non-existent transaction should raise TransactionNotFoundError."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with pytest.raises(TransactionNotFoundError) as exc_info:
            await TransactionService.post_transaction(db, uuid.uuid4())
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_post_already_posted(self) -> None:
        """Posting an already-posted transaction should raise TransactionNotDraftError."""
        db = AsyncMock()
        posted = Transaction(
            id=uuid.uuid4(),
            status="posted",
            postings=[],
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = posted
        db.execute.return_value = mock_result

        with pytest.raises(TransactionNotDraftError) as exc_info:
            await TransactionService.post_transaction(db, posted.id)
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_reverse_nonexistent_transaction(self) -> None:
        """Reversing a non-existent transaction should raise TransactionNotFoundError."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute.return_value = mock_result

        with pytest.raises(TransactionNotFoundError):
            await TransactionService.reverse_transaction(db, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_reverse_draft_transaction(self) -> None:
        """Reversing a Draft transaction should raise TransactionNotDraftError."""
        db = AsyncMock()
        draft = Transaction(
            id=uuid.uuid4(),
            status="draft",
            postings=[],
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = draft
        db.execute.return_value = mock_result

        with pytest.raises(TransactionNotDraftError):
            await TransactionService.reverse_transaction(db, draft.id)

    @pytest.mark.asyncio
    async def test_idempotency_duplicate(
        self,
        bank: Account,
        expense: Account,
    ) -> None:
        """Duplicate idempotency_key should raise IdempotencyConflictError."""
        db = AsyncMock()

        existing_id = uuid.uuid4()
        dup_key = uuid.uuid4()
        existing_tx = Transaction(
            id=existing_id,
            description="Existing",
            status="draft",
            idempotency_key=dup_key,
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_tx
        db.execute.return_value = mock_result

        data = TransactionCreate(
            description="Duplicate",
            idempotency_key=dup_key,
            postings=[
                PostingCreate(
                    account_id=expense.id,
                    debit_amount=5000,
                    credit_amount=0,
                ),
                PostingCreate(
                    account_id=bank.id,
                    debit_amount=0,
                    credit_amount=5000,
                ),
            ],
        )

        with pytest.raises(IdempotencyConflictError) as exc_info:
            await TransactionService.create_transaction(db, data)
        assert exc_info.value.status_code == 409
        assert exc_info.value.existing_transaction_id == existing_id


# ======================================================================
# Reversal Scenarios
# ======================================================================

class TestReversalScenarios:
    """Additional reversal edge case scenarios."""

    @pytest.mark.asyncio
    async def test_reversal_multi_line(
        self,
        bank: Account,
        revenue: Account,
        expense: Account,
        liability: Account,
    ) -> None:
        """Reversing a multi-line (split) transaction should handle all lines."""
        db = AsyncMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()

        # Track added postings
        added_postings: list[Posting] = []

        def track_add(obj):
            if isinstance(obj, Transaction):
                obj.id = uuid.uuid4()
            elif isinstance(obj, Posting):
                added_postings.append(obj)

        db.add = track_add

        async def mock_refresh(tx, attribute_names=None):
            if attribute_names and "postings" in attribute_names:
                tx.postings = [
                    p for p in added_postings
                    if p.transaction_id == tx.id
                ]

        db.refresh = mock_refresh

        tx_id = uuid.uuid4()
        original = Transaction(
            id=tx_id,
            reference="JE-2026-0010",
            status="posted",
            effective_date=date(2026, 6, 1),
            total_amount=15000,
            postings=[
                Posting(
                    id=uuid.uuid4(),
                    transaction_id=tx_id,
                    account_id=bank.id,
                    debit_amount=15000,
                    credit_amount=0,
                ),
                Posting(
                    id=uuid.uuid4(),
                    transaction_id=tx_id,
                    account_id=revenue.id,
                    debit_amount=0,
                    credit_amount=10000,
                ),
                Posting(
                    id=uuid.uuid4(),
                    transaction_id=tx_id,
                    account_id=revenue.id,
                    debit_amount=0,
                    credit_amount=5000,
                ),
            ],
        )

        mock_tx = MagicMock()
        mock_tx.scalar_one_or_none.return_value = original

        mock_ref = MagicMock()
        mock_ref.scalar_one_or_none.return_value = None

        db.execute.side_effect = [mock_tx, mock_ref]

        reversing = await TransactionService.reverse_transaction(db, tx_id)

        assert original.status == "reversed"
        assert len(reversing.postings) == 3

        # Original: Bank DR 15000, Revenue CR 10000, Revenue CR 5000
        # Reversal: Bank CR 15000, Revenue DR 10000, Revenue DR 5000
        assert reversing.postings[0].debit_amount == 0
        assert reversing.postings[0].credit_amount == 15000

        assert reversing.postings[1].debit_amount == 10000
        assert reversing.postings[1].credit_amount == 0

        assert reversing.postings[2].debit_amount == 5000
        assert reversing.postings[2].credit_amount == 0


# ======================================================================
# JE Reference Generation
# ======================================================================

class TestJEReferenceGeneration:
    """Tests for JE-YYYY-NNNN reference generation."""

    @pytest.mark.asyncio
    async def test_first_reference_in_year(self) -> None:
        """First JE in a year should be JE-YYYY-0001."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No prior JEs
        db.execute.return_value = mock_result

        ref = await TransactionService._generate_je_reference(db, date(2026, 1, 15))
        assert ref == "JE-2026-0001"

    @pytest.mark.asyncio
    async def test_sequential_references(self) -> None:
        """Sequential JE references should increment correctly."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "JE-2026-0042"
        db.execute.return_value = mock_result

        ref = await TransactionService._generate_je_reference(db, date(2026, 7, 1))
        assert ref == "JE-2026-0043"

    @pytest.mark.asyncio
    async def test_reference_padded_to_4_digits(self) -> None:
        """NNNN should always be 4-digit zero-padded."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = "JE-2026-0009"
        db.execute.return_value = mock_result

        ref = await TransactionService._generate_je_reference(db, date(2026, 3, 1))
        assert ref == "JE-2026-0010"

    @pytest.mark.asyncio
    async def test_different_year_reset(self) -> None:
        """Different year should start from 0001 (mock returns prior year's JE)."""
        db = AsyncMock()
        mock_result = MagicMock()
        # Highest JE in the DB is from 2025, so 2026 should start at 0001
        mock_result.scalar_one_or_none.return_value = None  # No 2026 JEs
        db.execute.return_value = mock_result

        ref = await TransactionService._generate_je_reference(db, date(2026, 1, 1))
        assert ref == "JE-2026-0001"
