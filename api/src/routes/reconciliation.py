"""FastAPI router for Manual Bank Reconciliation endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.services.reconciliation_service import (
    BankAccountNotFoundError,
    BankTransactionAlreadyMatchedError,
    BankTransactionNotFoundError,
    ReconciliationService,
    ReconciliationServiceError,
    SessionClosedError,
    SessionNotFoundError,
    TransactionNotFoundError,
)
from src.validators.reconciliation import (
    CreateAndMatchRequest,
    MatchRequest,
    ReconciliationMatchResponse,
    ReconciliationReport,
    ReconciliationSessionResponse,
    StartReconciliation,
)

router = APIRouter(prefix="/api/v1/reconciliation", tags=["Reconciliation"])


# ---------------------------------------------------------------------------
# POST /start — Start reconciliation session
# ---------------------------------------------------------------------------


@router.post(
    "/start",
    response_model=ReconciliationSessionResponse,
    summary="Start a new reconciliation session",
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Bank account not found"},
        422: {"description": "Validation error"},
    },
)
async def start_session(
    data: StartReconciliation,
    db: AsyncSession = Depends(get_db),
) -> ReconciliationSessionResponse:
    """Start a reconciliation session for a bank account within a date range."""
    try:
        return await ReconciliationService.start_session(db, data)
    except BankAccountNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except ReconciliationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /{session_id}/match — One-to-one match
# ---------------------------------------------------------------------------


@router.post(
    "/{session_id}/match",
    response_model=ReconciliationMatchResponse,
    summary="Match one bank transaction to one ledger transaction",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Session, bank transaction, or ledger transaction not found"},
        422: {"description": "Session closed or bank transaction already reconciled"},
    },
)
async def match_one_to_one(
    session_id: uuid.UUID,
    data: MatchRequest,
    db: AsyncSession = Depends(get_db),
) -> ReconciliationMatchResponse:
    """Match a single bank transaction to a single ledger transaction.

    Returns 422 if the amount differs (partial match). The match is still created.
    """
    if len(data.transaction_ids) != 1:
        raise HTTPException(
            status_code=422,
            detail="match endpoint requires exactly one transaction_id. Use match-many for multiple.",
        )

    try:
        return await ReconciliationService.match_one_to_one(
            db,
            session_id=session_id,
            bank_transaction_id=data.bank_transaction_id,
            transaction_id=data.transaction_ids[0],
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except SessionClosedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except BankTransactionNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except BankTransactionAlreadyMatchedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except TransactionNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except ReconciliationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /{session_id}/match-many — One-to-many match
# ---------------------------------------------------------------------------


@router.post(
    "/{session_id}/match-many",
    response_model=list[ReconciliationMatchResponse],
    summary="Match one bank transaction to multiple ledger transactions",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Session, bank transaction, or ledger transaction not found"},
        422: {"description": "Session closed or bank transaction already reconciled"},
    },
)
async def match_one_to_many(
    session_id: uuid.UUID,
    data: MatchRequest,
    db: AsyncSession = Depends(get_db),
) -> list[ReconciliationMatchResponse]:
    """Match a single bank transaction to one or more ledger transactions.

    Use this when a single bank deposit covers multiple invoices, for example.
    """
    try:
        return await ReconciliationService.match_one_to_many(
            db,
            session_id=session_id,
            bank_transaction_id=data.bank_transaction_id,
            transaction_ids=data.transaction_ids,
        )
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except SessionClosedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except BankTransactionNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except BankTransactionAlreadyMatchedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except TransactionNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except ReconciliationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /{session_id}/create-and-match — Create GL transaction + match
# ---------------------------------------------------------------------------


@router.post(
    "/{session_id}/create-and-match",
    response_model=ReconciliationMatchResponse,
    summary="Create a new ledger transaction and match it to a bank line",
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Session or bank transaction not found"},
        422: {"description": "Session closed or validation error"},
    },
)
async def create_and_match(
    session_id: uuid.UUID,
    data: CreateAndMatchRequest,
    db: AsyncSession = Depends(get_db),
) -> ReconciliationMatchResponse:
    """Create a new double-entry transaction and immediately match it to a bank line.

    The bank transaction must not already be reconciled.
    """
    try:
        return await ReconciliationService.create_and_match(db, session_id, data)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except SessionClosedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except BankTransactionNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except BankTransactionAlreadyMatchedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except ReconciliationServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# GET /{session_id}/status — Session status
# ---------------------------------------------------------------------------


@router.get(
    "/{session_id}/status",
    response_model=ReconciliationSessionResponse,
    summary="Get reconciliation session status",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Session not found"}},
)
async def get_session_status(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ReconciliationSessionResponse:
    """Return the current status of a reconciliation session with updated counts."""
    try:
        return await ReconciliationService.get_session_status(db, session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /{session_id}/close — Close session
# ---------------------------------------------------------------------------


@router.post(
    "/{session_id}/close",
    response_model=ReconciliationSessionResponse,
    summary="Close a reconciliation session",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Session not found"},
        422: {"description": "Session already closed"},
    },
)
async def close_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ReconciliationSessionResponse:
    """Close a reconciliation session. No further matches can be added."""
    try:
        return await ReconciliationService.close_session(db, session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except SessionClosedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# GET /{session_id}/report — Reconciliation report
# ---------------------------------------------------------------------------


@router.get(
    "/{session_id}/report",
    response_model=ReconciliationReport,
    summary="Generate reconciliation report",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Session not found"}},
)
async def get_report(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ReconciliationReport:
    """Generate a full reconciliation report for the session.

    Includes opening/closing balances, matched net amount, difference,
    and all match details.
    """
    try:
        return await ReconciliationService.generate_report(db, session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
