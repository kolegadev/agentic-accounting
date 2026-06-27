"""FastAPI router for Core General Ledger — Transaction endpoints."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.services.transaction_service import (
    AccountNotFoundError,
    IdempotencyConflictError,
    TransactionNotFoundError,
    TransactionNotDraftError,
    TransactionService,
    UnbalancedTransactionError,
)
from src.validators.transaction import (
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
)

router = APIRouter(prefix="/api/v1/transactions", tags=["Transactions"])


# ---------------------------------------------------------------------------
# POST / — Create transaction (Draft)
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=TransactionResponse,
    summary="Create a new transaction (Draft)",
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Duplicate idempotency key"},
        422: {"description": "Unbalanced transaction or validation error"},
        404: {"description": "Referenced account not found"},
    },
)
async def create_transaction(
    data: TransactionCreate,
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """Create a transaction in Draft status. Requires idempotency_key."""
    try:
        transaction = await TransactionService.create_transaction(db, data)
        return TransactionService._transaction_to_response(transaction)
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except UnbalancedTransactionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /{transaction_id}/post — Post transaction
# ---------------------------------------------------------------------------

@router.post(
    "/{transaction_id}/post",
    response_model=TransactionResponse,
    summary="Post a Draft transaction",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Transaction not found"},
        422: {"description": "Transaction not in Draft or unbalanced"},
    },
)
async def post_transaction(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """Post a Draft transaction — validates double-entry and assigns JE reference."""
    try:
        transaction = await TransactionService.post_transaction(db, transaction_id)
        return TransactionService._transaction_to_response(transaction)
    except TransactionNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except TransactionNotDraftError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except UnbalancedTransactionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# GET / — List transactions
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=TransactionListResponse,
    summary="List transactions with optional filters",
    status_code=status.HTTP_200_OK,
)
async def list_transactions(
    status_filter: Optional[str] = Query(None, alias="status"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    contact_id: Optional[uuid.UUID] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> TransactionListResponse:
    """List transactions, optionally filtered by status, date range, or contact."""
    transactions, total = await TransactionService.list_transactions(
        db,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        contact_id=contact_id,
        limit=limit,
        offset=offset,
    )
    return TransactionListResponse(
        transactions=[
            TransactionService._transaction_to_response(t)
            for t in transactions
        ],
        total=total,
    )


# ---------------------------------------------------------------------------
# GET /{transaction_id} — Get transaction with postings
# ---------------------------------------------------------------------------

@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Get transaction by ID with all postings",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Transaction not found"}},
)
async def get_transaction(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """Return a single transaction with its postings and account details."""
    transaction = await TransactionService.get_transaction(db, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail=f"Transaction '{transaction_id}' not found")
    return TransactionService._transaction_to_response(transaction)


# ---------------------------------------------------------------------------
# POST /{transaction_id}/reverse — Reverse transaction
# ---------------------------------------------------------------------------

@router.post(
    "/{transaction_id}/reverse",
    response_model=TransactionResponse,
    summary="Reverse a Posted transaction",
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Transaction not found"},
        422: {"description": "Transaction not in Posted status"},
    },
)
async def reverse_transaction(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """Reverse a Posted transaction — creates a compensating entry and marks original as reversed."""
    try:
        reversing = await TransactionService.reverse_transaction(db, transaction_id)
        return TransactionService._transaction_to_response(reversing)
    except TransactionNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except TransactionNotDraftError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# GET /{transaction_id}/audit — Audit trail
# ---------------------------------------------------------------------------

@router.get(
    "/{transaction_id}/audit",
    summary="Get audit trail for a transaction",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Transaction not found"}},
)
async def get_audit_trail(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the full audit trail for a transaction (creation, posting, any reversals)."""
    transaction = await TransactionService.get_transaction(db, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail=f"Transaction '{transaction_id}' not found")

    audit_entries = [
        {
            "event": "created",
            "timestamp": transaction.created_at.isoformat(),
            "status": "draft",
        }
    ]

    if transaction.status in ("posted", "reversed") and transaction.recorded_at:
        audit_entries.append(
            {
                "event": "posted",
                "timestamp": transaction.recorded_at.isoformat(),
                "reference": transaction.reference,
                "status": "posted",
            }
        )

    if transaction.status == "reversed":
        audit_entries.append(
            {
                "event": "reversed",
                "timestamp": transaction.updated_at.isoformat(),
                "status": "reversed",
            }
        )

    return {
        "transaction_id": str(transaction.id),
        "audit_trail": audit_entries,
    }
