"""Dedicated invariant tests for Transaction and Posting validation.

Tests sum-to-zero, multi-line splits, zero/no-amount postings, and
transaction-level guardrails.
"""

from __future__ import annotations

import uuid

import pytest

from src.validators.transaction import PostingCreate, TransactionCreate


# ---------------------------------------------------------------------------
# PostingCreate — exactly one positive
# ---------------------------------------------------------------------------

class TestPostingCreateInvariants:
    """Per-posting invariants: exactly one of debit/credit must be positive."""

    def test_debit_only_valid(self) -> None:
        """Debit > 0, credit == 0 is valid."""
        p = PostingCreate(
            account_id=uuid.uuid4(),
            debit_amount=100,
            credit_amount=0,
        )
        assert p.debit_amount == 100
        assert p.credit_amount == 0

    def test_credit_only_valid(self) -> None:
        """Debit == 0, credit > 0 is valid."""
        p = PostingCreate(
            account_id=uuid.uuid4(),
            debit_amount=0,
            credit_amount=100,
        )
        assert p.debit_amount == 0
        assert p.credit_amount == 100

    def test_both_positive_fails(self) -> None:
        """Both debit > 0 AND credit > 0 fails."""
        with pytest.raises(ValueError, match="exactly one"):
            PostingCreate(
                account_id=uuid.uuid4(),
                debit_amount=100,
                credit_amount=50,
            )

    def test_both_zero_fails(self) -> None:
        """Both debit == 0 AND credit == 0 fails."""
        with pytest.raises(ValueError, match="exactly one"):
            PostingCreate(
                account_id=uuid.uuid4(),
                debit_amount=0,
                credit_amount=0,
            )

    def test_debit_negative_fails(self) -> None:
        """Negative debit_amount fails (ge=0 constraint)."""
        with pytest.raises(ValueError):
            PostingCreate(
                account_id=uuid.uuid4(),
                debit_amount=-1,
                credit_amount=0,
            )

    def test_credit_negative_fails(self) -> None:
        """Negative credit_amount fails (ge=0 constraint)."""
        with pytest.raises(ValueError):
            PostingCreate(
                account_id=uuid.uuid4(),
                debit_amount=0,
                credit_amount=-1,
            )


# ---------------------------------------------------------------------------
# TransactionCreate — sum-to-zero
# ---------------------------------------------------------------------------

class TestTransactionSumToZero:
    """Transaction-level invariant: total debits == total credits."""

    @staticmethod
    def _make_posting(
        account_id: uuid.UUID,
        debit: int = 0,
        credit: int = 0,
    ) -> PostingCreate:
        return PostingCreate(
            account_id=account_id,
            debit_amount=debit,
            credit_amount=credit,
        )

    def test_balanced_simple_passes(self) -> None:
        """Simple 2-line balanced entry: debit 100, credit 100."""
        tx = TransactionCreate(
            description="Balanced",
            idempotency_key=uuid.uuid4(),
            postings=[
                self._make_posting(uuid.uuid4(), debit=100, credit=0),
                self._make_posting(uuid.uuid4(), debit=0, credit=100),
            ],
        )
        assert tx.description == "Balanced"

    def test_unbalanced_debit_100_credit_99_fails(self) -> None:
        """Debit 100, credit 99 → fails sum-to-zero."""
        with pytest.raises(ValueError, match="unbalanced"):
            TransactionCreate(
                description="Unbalanced",
                idempotency_key=uuid.uuid4(),
                postings=[
                    self._make_posting(uuid.uuid4(), debit=100, credit=0),
                    self._make_posting(uuid.uuid4(), debit=0, credit=99),
                ],
            )

    def test_unbalanced_credit_100_debit_99_fails(self) -> None:
        """Debit 99, credit 100 → fails sum-to-zero."""
        with pytest.raises(ValueError, match="unbalanced"):
            TransactionCreate(
                description="Unbalanced",
                idempotency_key=uuid.uuid4(),
                postings=[
                    self._make_posting(uuid.uuid4(), debit=99, credit=0),
                    self._make_posting(uuid.uuid4(), debit=0, credit=100),
                ],
            )

    def test_multi_line_balanced_passes(self) -> None:
        """Multi-line split: 3 debits (10+20+70=100), 2 credits (30+70=100)."""
        tx = TransactionCreate(
            description="Multi-line balanced",
            idempotency_key=uuid.uuid4(),
            postings=[
                self._make_posting(uuid.uuid4(), debit=10, credit=0),
                self._make_posting(uuid.uuid4(), debit=20, credit=0),
                self._make_posting(uuid.uuid4(), debit=70, credit=0),
                self._make_posting(uuid.uuid4(), debit=0, credit=30),
                self._make_posting(uuid.uuid4(), debit=0, credit=70),
            ],
        )
        assert len(tx.postings) == 5

    def test_multi_line_unbalanced_fails(self) -> None:
        """3 debits sum 100, 2 credits sum 99 → fails."""
        with pytest.raises(ValueError, match="unbalanced"):
            TransactionCreate(
                description="Multi unbalanced",
                idempotency_key=uuid.uuid4(),
                postings=[
                    self._make_posting(uuid.uuid4(), debit=50, credit=0),
                    self._make_posting(uuid.uuid4(), debit=50, credit=0),
                    self._make_posting(uuid.uuid4(), debit=0, credit=50),
                    self._make_posting(uuid.uuid4(), debit=0, credit=49),
                ],
            )

    def test_all_zero_amounts_fails(self) -> None:
        """Transaction with all zero postings fails (caught by PostingCreate validator)."""
        with pytest.raises(ValueError, match="exactly one"):
            TransactionCreate(
                description="Zero amounts",
                idempotency_key=uuid.uuid4(),
                postings=[
                    self._make_posting(uuid.uuid4(), debit=0, credit=0),
                    self._make_posting(uuid.uuid4(), debit=0, credit=0),
                ],
            )


# ---------------------------------------------------------------------------
# TransactionCreate — minimum postings
# ---------------------------------------------------------------------------

class TestTransactionMinPostings:
    """Transaction must have at least 2 postings."""

    def test_zero_postings_fails(self) -> None:
        """Empty postings list fails."""
        with pytest.raises(ValueError):
            TransactionCreate(
                description="No postings",
                idempotency_key=uuid.uuid4(),
                postings=[],
            )

    def test_one_posting_fails(self) -> None:
        """Single posting fails."""
        with pytest.raises(ValueError):
            TransactionCreate(
                description="One posting",
                idempotency_key=uuid.uuid4(),
                postings=[
                    PostingCreate(
                        account_id=uuid.uuid4(),
                        debit_amount=100,
                        credit_amount=0,
                    ),
                ],
            )

    def test_two_postings_passes(self) -> None:
        """Two balanced postings passes minimum."""
        tx = TransactionCreate(
            description="Two postings",
            idempotency_key=uuid.uuid4(),
            postings=[
                PostingCreate(
                    account_id=uuid.uuid4(),
                    debit_amount=100,
                    credit_amount=0,
                ),
                PostingCreate(
                    account_id=uuid.uuid4(),
                    debit_amount=0,
                    credit_amount=100,
                ),
            ],
        )
        assert len(tx.postings) == 2


# ---------------------------------------------------------------------------
# Edge cases — large amounts
# ---------------------------------------------------------------------------

class TestAmountEdgeCases:
    """Edge cases for large and boundary amounts."""

    def test_large_amounts_balanced(self) -> None:
        """Large pence amounts (e.g., £1M = 100,000,000p) should still balance."""
        large = 100_000_000  # £1,000,000.00
        tx = TransactionCreate(
            description="Large amounts",
            idempotency_key=uuid.uuid4(),
            postings=[
                PostingCreate(account_id=uuid.uuid4(), debit_amount=large, credit_amount=0),
                PostingCreate(account_id=uuid.uuid4(), debit_amount=0, credit_amount=large),
            ],
        )
        assert tx.postings[0].debit_amount == large
        assert tx.postings[1].credit_amount == large

    def test_one_pence_balanced(self) -> None:
        """1p transaction should work."""
        tx = TransactionCreate(
            description="One pence",
            idempotency_key=uuid.uuid4(),
            postings=[
                PostingCreate(account_id=uuid.uuid4(), debit_amount=1, credit_amount=0),
                PostingCreate(account_id=uuid.uuid4(), debit_amount=0, credit_amount=1),
            ],
        )
        assert tx.postings[0].debit_amount == 1


# ---------------------------------------------------------------------------
# Edge cases — many lines
# ---------------------------------------------------------------------------

class TestManyLines:
    """Complex multi-line splits with many postings."""

    def test_ten_line_split_balanced(self) -> None:
        """10-line transaction with 5 debits and 5 credits balancing."""
        postings = []
        for i in range(5):
            postings.append(
                PostingCreate(account_id=uuid.uuid4(), debit_amount=200, credit_amount=0)
            )
        for i in range(5):
            postings.append(
                PostingCreate(account_id=uuid.uuid4(), debit_amount=0, credit_amount=200)
            )

        tx = TransactionCreate(
            description="10-line split",
            idempotency_key=uuid.uuid4(),
            postings=postings,
        )
        assert len(tx.postings) == 10

    def test_uneven_split_balanced(self) -> None:
        """3 debits (10+30+60=100) and 1 credit (100) — uneven but balanced."""
        tx = TransactionCreate(
            description="Uneven split",
            idempotency_key=uuid.uuid4(),
            postings=[
                PostingCreate(account_id=uuid.uuid4(), debit_amount=10, credit_amount=0),
                PostingCreate(account_id=uuid.uuid4(), debit_amount=30, credit_amount=0),
                PostingCreate(account_id=uuid.uuid4(), debit_amount=60, credit_amount=0),
                PostingCreate(account_id=uuid.uuid4(), debit_amount=0, credit_amount=100),
            ],
        )
        assert len(tx.postings) == 4
