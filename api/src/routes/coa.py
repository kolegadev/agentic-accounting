"""FastAPI router for Chart of Accounts endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.services.coa_service import (
    AccountNotFoundError,
    CoaService,
    DuplicateCodeError,
    InvalidCodeRangeError,
    TemplateNotFoundError,
)
from src.validators.account import (
    AccountCreate,
    AccountListResponse,
    AccountResponse,
    AccountUpdate,
    VatRateUpdate,
)

router = APIRouter(prefix="/api/v1/coa", tags=["Chart of Accounts"])


# ---------------------------------------------------------------------------
# GET / — List accounts
# ---------------------------------------------------------------------------
@router.get(
    "/",
    response_model=AccountListResponse,
    summary="List all accounts",
    status_code=status.HTTP_200_OK,
)
async def list_accounts(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db),
) -> AccountListResponse:
    """Return all active accounts, or all accounts if include_inactive=true."""
    accounts = await CoaService.list_accounts(db, include_inactive=include_inactive)
    return AccountListResponse(accounts=accounts, total=len(accounts))


# ---------------------------------------------------------------------------
# GET /{account_id} — Get account by ID
# ---------------------------------------------------------------------------
@router.get(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Get account by ID",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Account not found"}},
)
async def get_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AccountResponse:
    """Return a single account by its UUID."""
    account = await CoaService.get_account(db, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found")
    return account


# ---------------------------------------------------------------------------
# POST / — Create account
# ---------------------------------------------------------------------------
@router.post(
    "/",
    response_model=AccountResponse,
    summary="Create a new account",
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "Account code already exists"}, 422: {"description": "Validation error"}},
)
async def create_account(
    data: AccountCreate,
    db: AsyncSession = Depends(get_db),
) -> AccountResponse:
    """Create a new account. Code must be unique and in valid range for category."""
    try:
        return await CoaService.create_account(db, data)
    except DuplicateCodeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except InvalidCodeRangeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# PATCH /{account_id} — Update account
# ---------------------------------------------------------------------------
@router.patch(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Partially update an account",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Account not found"}, 422: {"description": "Validation error"}},
)
async def update_account(
    account_id: uuid.UUID,
    data: AccountUpdate,
    db: AsyncSession = Depends(get_db),
) -> AccountResponse:
    """Update one or more fields on an existing account."""
    try:
        return await CoaService.update_account(db, account_id, data)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    except InvalidCodeRangeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# DELETE /{account_id} — Soft delete account
# ---------------------------------------------------------------------------
@router.delete(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Soft-delete an account",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Account not found"}},
)
async def soft_delete_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AccountResponse:
    """Soft-delete an account by setting is_active=False."""
    try:
        return await CoaService.soft_delete_account(db, account_id)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# PUT /{account_id}/vat-rate — Set VAT rate
# ---------------------------------------------------------------------------
@router.put(
    "/{account_id}/vat-rate",
    response_model=AccountResponse,
    summary="Set VAT rate on an account",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Account not found"}, 422: {"description": "Invalid VAT rate"}},
)
async def set_vat_rate(
    account_id: uuid.UUID,
    data: VatRateUpdate,
    db: AsyncSession = Depends(get_db),
) -> AccountResponse:
    """Set or update the default VAT rate for an account."""
    try:
        return await CoaService.set_vat_rate(db, account_id, data.vat_rate)
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /templates/{template_name}/load — Load a COA template
# ---------------------------------------------------------------------------
@router.post(
    "/templates/{template_name}/load",
    response_model=AccountListResponse,
    summary="Load a COA template",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Template not found"}},
)
async def load_template(
    template_name: str,
    db: AsyncSession = Depends(get_db),
) -> AccountListResponse:
    """Load accounts from a COA template JSON file into the database.

    Template names correspond to files in api/src/coa_templates/.
    Available: uk_sole_trader_no_vat, uk_sole_trader_vat, uk_limited_company_no_vat,
    uk_limited_company_vat, uk_partnership_no_vat, uk_partnership_vat,
    micro_entity_simplified, property_landlord_vat
    """
    try:
        accounts = await CoaService.load_template(db, template_name)
    except TemplateNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    return AccountListResponse(accounts=accounts, total=len(accounts))
