"""FastAPI router for Open Banking Feed endpoints."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.services.bank_service import BankAccountNotFoundError
from src.services.open_banking_service import (
    AccountNotConnectedError,
    AlreadyConnectedError,
    OpenBankingError,
    OpenBankingService,
    ProviderNotFoundError,
)
from src.validators.open_banking import (
    ConnectAccountRequest,
    ConnectionResponse,
    ConnectionStatusResponse,
    ProviderResponse,
    SyncAllResponse,
    SyncResponse,
)

router = APIRouter(prefix="/api/v1/bank/feeds", tags=["Open Banking Feeds"])


# ---------------------------------------------------------------------------
# GET /providers — List available providers
# ---------------------------------------------------------------------------


@router.get(
    "/providers",
    response_model=list[ProviderResponse],
    summary="List available Open Banking providers",
    status_code=status.HTTP_200_OK,
)
async def list_providers() -> list[ProviderResponse]:
    """Return all available Open Banking providers (TrueLayer, Plaid, etc)."""
    return OpenBankingService.list_providers()


# ---------------------------------------------------------------------------
# POST /connect — Connect account to provider
# ---------------------------------------------------------------------------


@router.post(
    "/connect",
    response_model=ConnectionResponse,
    summary="Connect a bank account to an Open Banking provider",
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Bank account or provider not found"},
        409: {"description": "Account already connected"},
    },
)
async def connect_account(
    data: ConnectAccountRequest = Body(...),
    db: AsyncSession = Depends(get_db),
) -> ConnectionResponse:
    """Connect a bank account to an Open Banking provider for automated feeds.

    In test mode, creates a mock connection. In production, initiates
    OAuth/consent flow with the chosen provider.
    """
    try:
        return await OpenBankingService.connect_account(
            db,
            bank_account_id=data.bank_account_id,
            provider=data.provider,
            credentials=data.credentials,
        )
    except BankAccountNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except ProviderNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except AlreadyConnectedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# GET /{account_id}/status — Get connection status
# ---------------------------------------------------------------------------


@router.get(
    "/{account_id}/status",
    response_model=ConnectionStatusResponse,
    summary="Get Open Banking connection status",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Account not connected"}},
)
async def get_connection_status(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ConnectionStatusResponse:
    """Return the current connection status for a bank account's Open Banking feed."""
    try:
        return await OpenBankingService.get_connection_status(db, account_id)
    except AccountNotConnectedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /{account_id}/sync — Sync transactions
# ---------------------------------------------------------------------------


@router.post(
    "/{account_id}/sync",
    response_model=SyncResponse,
    summary="Sync transactions from Open Banking provider",
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Account not connected"},
        400: {"description": "Connection error"},
    },
)
async def sync_account(
    account_id: uuid.UUID,
    from_date: Optional[date] = Query(
        None,
        description="Start date for transaction fetch (default: 30 days ago)",
    ),
    to_date: Optional[date] = Query(
        None,
        description="End date for transaction fetch (default: today)",
    ),
    db: AsyncSession = Depends(get_db),
) -> SyncResponse:
    """Fetch and import new transactions from the connected Open Banking provider.

    In test mode, generates realistic mock UK bank transactions.
    """
    try:
        imported = await OpenBankingService.fetch_transactions(
            db,
            bank_account_id=account_id,
            from_date=from_date,
            to_date=to_date,
        )
        return SyncResponse(
            account_id=account_id,
            imported_count=imported,
            skipped_count=0,
            from_date=from_date,
            to_date=to_date,
        )
    except AccountNotConnectedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except OpenBankingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /sync-all — Sync all accounts
# ---------------------------------------------------------------------------


@router.post(
    "/sync-all",
    response_model=SyncAllResponse,
    summary="Sync all connected bank accounts",
    status_code=status.HTTP_200_OK,
)
async def sync_all_accounts(
    db: AsyncSession = Depends(get_db),
) -> SyncAllResponse:
    """Trigger a sync for all connected bank accounts.

    Returns per-account results with import counts.
    """
    return await OpenBankingService.sync_all(db)


# ---------------------------------------------------------------------------
# POST /{account_id}/disconnect — Disconnect account
# ---------------------------------------------------------------------------


@router.post(
    "/{account_id}/disconnect",
    response_model=ConnectionResponse,
    summary="Disconnect bank account from Open Banking provider",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Account not connected"}},
)
async def disconnect_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ConnectionResponse:
    """Disconnect a bank account from its Open Banking provider.

    Transactions already imported are preserved.
    """
    try:
        return await OpenBankingService.disconnect_account(db, account_id)
    except AccountNotConnectedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
