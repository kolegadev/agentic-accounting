"""FastAPI router for Bank Statement Import endpoints."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.services.bank_service import (
    BankAccountNotFoundError,
    BankService,
    BankServiceError,
    BankTransactionNotFoundError,
)
from src.validators.bank import (
    BankAccountCreate,
    BankAccountResponse,
    BankImportResult,
    BankTransactionResponse,
    CategorizeTransaction,
)

router = APIRouter(prefix="/api/v1/bank", tags=["Bank Statement Import"])


# ---------------------------------------------------------------------------
# POST /accounts — Create bank account
# ---------------------------------------------------------------------------


@router.post(
    "/accounts",
    response_model=BankAccountResponse,
    summary="Create a new bank account",
    status_code=status.HTTP_201_CREATED,
)
async def create_account(
    data: BankAccountCreate,
    db: AsyncSession = Depends(get_db),
) -> BankAccountResponse:
    """Create a new bank account for statement import."""
    return await BankService.create_account(db, data)


# ---------------------------------------------------------------------------
# GET /accounts — List bank accounts
# ---------------------------------------------------------------------------


@router.get(
    "/accounts",
    response_model=list[BankAccountResponse],
    summary="List bank accounts",
    status_code=status.HTTP_200_OK,
)
async def list_accounts(
    include_inactive: bool = Query(
        False,
        description="Include inactive bank accounts",
    ),
    db: AsyncSession = Depends(get_db),
) -> list[BankAccountResponse]:
    """List bank accounts, optionally including inactive ones."""
    return await BankService.list_accounts(db, include_inactive=include_inactive)


# ---------------------------------------------------------------------------
# GET /accounts/{account_id} — Get bank account
# ---------------------------------------------------------------------------


@router.get(
    "/accounts/{account_id}",
    response_model=BankAccountResponse,
    summary="Get bank account by ID",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Bank account not found"}},
)
async def get_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> BankAccountResponse:
    """Return a single bank account by its UUID."""
    account = await BankService.get_account(db, account_id)
    if account is None:
        raise HTTPException(
            status_code=404,
            detail=f"Bank account '{account_id}' not found",
        )
    return account


# ---------------------------------------------------------------------------
# POST /import/csv — Import CSV statement
# ---------------------------------------------------------------------------


@router.post(
    "/import/csv",
    response_model=BankImportResult,
    summary="Import bank statement from CSV",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Bank account not found"},
        422: {"description": "CSV parsing error"},
    },
)
async def import_csv(
    file: UploadFile = File(..., description="CSV statement file"),
    account_id: uuid.UUID = Query(..., description="Bank account UUID"),
    template: Optional[str] = Query(
        None,
        description="Bank template name (barclays, hsbc, lloyds, natwest, monzo, starling, revolut)",
    ),
    db: AsyncSession = Depends(get_db),
) -> BankImportResult:
    """Import transactions from a CSV bank statement.

    Auto-detects columns if no template specified. Duplicates are detected
    via SHA-256 hash and skipped automatically.
    """
    file_content = await file.read()
    try:
        return await BankService.import_csv(
            db,
            account_id=account_id,
            file_content=file_content,
            template_name=template,
        )
    except BankAccountNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except BankServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /import/ofx — Import OFX statement
# ---------------------------------------------------------------------------


@router.post(
    "/import/ofx",
    response_model=BankImportResult,
    summary="Import bank statement from OFX",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Bank account not found"},
        422: {"description": "OFX parsing error"},
    },
)
async def import_ofx(
    file: UploadFile = File(..., description="OFX statement file"),
    account_id: uuid.UUID = Query(..., description="Bank account UUID"),
    db: AsyncSession = Depends(get_db),
) -> BankImportResult:
    """Import transactions from an OFX bank statement (versions 1.02, 2.1, 2.2).

    Duplicates are detected via FITID and skipped automatically.
    """
    file_content = await file.read()
    try:
        return await BankService.import_ofx(
            db,
            account_id=account_id,
            file_content=file_content,
        )
    except BankAccountNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except BankServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# GET /transactions — List bank transactions
# ---------------------------------------------------------------------------


@router.get(
    "/transactions",
    response_model=list[BankTransactionResponse],
    summary="List bank transactions",
    status_code=status.HTTP_200_OK,
)
async def list_transactions(
    account_id: uuid.UUID = Query(..., description="Bank account UUID"),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by status: imported, categorized, reconciled",
    ),
    date_from: Optional[date] = Query(
        None,
        description="Filter transactions from this date (inclusive)",
    ),
    date_to: Optional[date] = Query(
        None,
        description="Filter transactions to this date (inclusive)",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[BankTransactionResponse]:
    """List bank transactions for a specific bank account with optional filters."""
    items, _total = await BankService.list_transactions(
        db,
        account_id=account_id,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return items


# ---------------------------------------------------------------------------
# PATCH /transactions/{transaction_id}/categorize — Categorize transaction
# ---------------------------------------------------------------------------


@router.patch(
    "/transactions/{transaction_id}/categorize",
    response_model=BankTransactionResponse,
    summary="Categorize a bank transaction",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Bank transaction not found"}},
)
async def categorize_transaction(
    transaction_id: uuid.UUID,
    data: CategorizeTransaction,
    db: AsyncSession = Depends(get_db),
) -> BankTransactionResponse:
    """Assign a category and/or contact to a bank transaction.

    Automatically transitions status from 'imported' to 'categorized'.
    """
    try:
        return await BankService.categorize_transaction(
            db,
            transaction_id=transaction_id,
            contact_id=data.contact_id,
            category=data.category,
        )
    except BankTransactionNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
