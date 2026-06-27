"""FastAPI router for Bank Rules Engine endpoints."""

from __future__ import annotations

import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_db
from src.services.bank_rule_service import (
    BankRuleNotFoundError,
    BankRuleService,
    BankRuleServiceError,
)
from src.validators.bank_rule import (
    BankRuleApplyResponse,
    BankRuleCreate,
    BankRuleLoadDefaultsResponse,
    BankRuleResponse,
    BankRuleUpdate,
)

router = APIRouter(prefix="/api/v1/bank/rules", tags=["Bank Rules Engine"])


# ---------------------------------------------------------------------------
# POST / — Create a new bank rule
# ---------------------------------------------------------------------------


@router.post(
    "/",
    response_model=BankRuleResponse,
    summary="Create a new bank rule",
    status_code=status.HTTP_201_CREATED,
)
async def create_rule(
    data: BankRuleCreate,
    db: AsyncSession = Depends(get_db),
) -> BankRuleResponse:
    """Create a new bank rule for auto-categorization."""
    return await BankRuleService.create_rule(db, data)


# ---------------------------------------------------------------------------
# GET / — List all bank rules
# ---------------------------------------------------------------------------


@router.get(
    "/",
    response_model=list[BankRuleResponse],
    summary="List bank rules",
    status_code=status.HTTP_200_OK,
)
async def list_rules(
    include_inactive: bool = Query(
        False,
        description="Include inactive rules",
    ),
    db: AsyncSession = Depends(get_db),
) -> list[BankRuleResponse]:
    """List all bank rules ordered by priority."""
    return await BankRuleService.list_rules(db, include_inactive=include_inactive)


# ---------------------------------------------------------------------------
# PATCH /{rule_id} — Update a bank rule
# ---------------------------------------------------------------------------


@router.patch(
    "/{rule_id}",
    response_model=BankRuleResponse,
    summary="Update a bank rule",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Bank rule not found"}},
)
async def update_rule(
    rule_id: uuid.UUID,
    data: BankRuleUpdate,
    db: AsyncSession = Depends(get_db),
) -> BankRuleResponse:
    """Update an existing bank rule (partial update)."""
    try:
        return await BankRuleService.update_rule(db, rule_id, data)
    except BankRuleNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# DELETE /{rule_id} — Delete a bank rule
# ---------------------------------------------------------------------------


@router.delete(
    "/{rule_id}",
    summary="Delete a bank rule",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Bank rule not found"}},
)
async def delete_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a bank rule by ID."""
    try:
        await BankRuleService.delete_rule(db, rule_id)
    except BankRuleNotFoundError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /apply — Apply rules to all pending transactions
# ---------------------------------------------------------------------------


class ApplyRulesRequest(BaseModel):
    """Request body for applying rules to pending transactions."""

    bank_account_id: uuid.UUID = Field(
        ...,
        description="Bank account UUID to apply rules to",
    )


@router.post(
    "/apply",
    response_model=BankRuleApplyResponse,
    summary="Apply rules to all pending transactions",
    status_code=status.HTTP_200_OK,
)
async def apply_rules_to_pending(
    data: ApplyRulesRequest,
    db: AsyncSession = Depends(get_db),
) -> BankRuleApplyResponse:
    """Apply all active rules to uncategorized transactions for a bank account."""
    return await BankRuleService.apply_all_pending(db, data.bank_account_id)


# ---------------------------------------------------------------------------
# POST /apply/{transaction_id} — Apply rules to a specific transaction
# ---------------------------------------------------------------------------


@router.post(
    "/apply/{transaction_id}",
    response_model=dict,
    summary="Apply rules to a specific transaction",
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "Bank transaction not found"}},
)
async def apply_rules_to_transaction(
    transaction_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Apply matching rules to a single bank transaction."""
    try:
        result = await BankRuleService.apply_rules(db, transaction_id)
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Bank transaction '{transaction_id}' not found",
            )
        return result.model_dump()
    except BankRuleServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)


# ---------------------------------------------------------------------------
# POST /load-defaults — Load pre-built rules from JSON template
# ---------------------------------------------------------------------------


@router.post(
    "/load-defaults",
    response_model=BankRuleLoadDefaultsResponse,
    summary="Load pre-built default rules",
    status_code=status.HTTP_200_OK,
)
async def load_default_rules(
    db: AsyncSession = Depends(get_db),
) -> BankRuleLoadDefaultsResponse:
    """Load 50+ pre-built categorization rules from the default template."""
    try:
        return await BankRuleService.load_default_rules(db)
    except BankRuleServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
