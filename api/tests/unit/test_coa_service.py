"""Unit tests for CoaService with mocked DB session."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.account import Account
from src.services.coa_service import (
    AccountNotFoundError,
    CoaService,
    DuplicateCodeError,
    InvalidCodeRangeError,
    TemplateNotFoundError,
)
from src.validators.account import AccountCreate, AccountUpdate
from tests.conftest import NOW


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db() -> AsyncMock:
    """Return an AsyncMock that behaves like an async SQLAlchemy session.

    The refresh mock populates server-default fields (id, created_at, updated_at,
    is_active) that would normally be set by the database, so that Pydantic
    serialisation works correctly.
    """
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    async def _refresh(obj: object) -> None:
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid.uuid4()  # type: ignore[attr-defined]
        if hasattr(obj, "is_active") and obj.is_active is None:
            obj.is_active = True  # type: ignore[attr-defined]
        if hasattr(obj, "created_at") and obj.created_at is None:
            obj.created_at = NOW  # type: ignore[attr-defined]
        if hasattr(obj, "updated_at") and obj.updated_at is None:
            obj.updated_at = NOW  # type: ignore[attr-defined]

    db.refresh = _refresh
    return db


@pytest.fixture
def sample_account_obj() -> Account:
    """Create a fully-populated Account ORM instance."""
    return Account(
        id=uuid.uuid4(),
        code="1000",
        name="Bank Current Account",
        category="Asset",
        type="Bank",
        vat_rate=None,
        parent_id=None,
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )


# ---------------------------------------------------------------------------
# list_accounts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_accounts_active_only(mock_db: AsyncMock) -> None:
    """Should return only active accounts when include_inactive=False."""
    active = Account(id=uuid.uuid4(), code="1000", name="Bank", category="Asset", type="Bank", vat_rate=None, is_active=True, created_at=NOW, updated_at=NOW)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [active]
    mock_db.execute.return_value = mock_result

    result = await CoaService.list_accounts(mock_db, include_inactive=False)
    assert len(result) == 1
    assert result[0].code == "1000"


@pytest.mark.asyncio
async def test_list_accounts_include_inactive(mock_db: AsyncMock) -> None:
    """Should return ALL accounts when include_inactive=True."""
    acc1 = Account(id=uuid.uuid4(), code="1000", name="Bank", category="Asset", type="Bank", vat_rate=None, is_active=True, created_at=NOW, updated_at=NOW)
    acc2 = Account(id=uuid.uuid4(), code="2000", name="Loan", category="Liability", type="CurrentLiability", vat_rate=None, is_active=False, created_at=NOW, updated_at=NOW)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [acc1, acc2]
    mock_db.execute.return_value = mock_result

    result = await CoaService.list_accounts(mock_db, include_inactive=True)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# get_account
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_account_found(mock_db: AsyncMock, sample_account_obj: Account) -> None:
    """Should return account when found by ID."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_account_obj
    mock_db.execute.return_value = mock_result

    result = await CoaService.get_account(mock_db, sample_account_obj.id)
    assert result is not None
    assert result.code == "1000"


@pytest.mark.asyncio
async def test_get_account_not_found(mock_db: AsyncMock) -> None:
    """Should return None when account not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    result = await CoaService.get_account(mock_db, uuid.uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# get_account_by_code
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_account_by_code_found(mock_db: AsyncMock, sample_account_obj: Account) -> None:
    """Should return account when found by code."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_account_obj
    mock_db.execute.return_value = mock_result

    result = await CoaService.get_account_by_code(mock_db, "1000")
    assert result is not None
    assert result.code == "1000"


@pytest.mark.asyncio
async def test_get_account_by_code_not_found(mock_db: AsyncMock) -> None:
    """Should return None when code not found."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    result = await CoaService.get_account_by_code(mock_db, "9999")
    assert result is None


# ---------------------------------------------------------------------------
# create_account
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_account_success(mock_db: AsyncMock) -> None:
    """Should create account successfully."""
    data = AccountCreate(code="5210", name="Marketing", category="Expense", type="Expense", vat_rate="20%")

    # Simulate no existing account by code
    mock_result_check = MagicMock()
    mock_result_check.scalar_one_or_none.return_value = None

    mock_db.execute.return_value = mock_result_check
    mock_db.commit = AsyncMock()

    result = await CoaService.create_account(mock_db, data)
    assert result.code == "5210"
    assert result.name == "Marketing"
    mock_db.add.assert_called_once()


@pytest.mark.asyncio
async def test_create_account_duplicate_code(mock_db: AsyncMock) -> None:
    """Should raise DuplicateCodeError for duplicate code."""
    data = AccountCreate(code="1000", name="Bank", category="Asset", type="Bank", vat_rate=None)

    existing = Account(id=uuid.uuid4(), code="1000", name="Existing", category="Asset", type="Bank", is_active=True, created_at=NOW, updated_at=NOW)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing
    mock_db.execute.return_value = mock_result

    with pytest.raises(DuplicateCodeError) as exc_info:
        await CoaService.create_account(mock_db, data)
    assert exc_info.value.status_code == 409
    assert "1000" in exc_info.value.message


@pytest.mark.asyncio
async def test_create_account_invalid_code_range(mock_db: AsyncMock) -> None:
    """Should reject code outside category range (Pydantic validation)."""
    # Pydantic model_validator catches this before it reaches the service.
    # The code 9999 is not in the Asset range (1000-1999).
    with pytest.raises(Exception) as exc_info:
        AccountCreate(code="9999", name="Invalid", category="Asset", type="Bank", vat_rate=None)
    assert "9999" in str(exc_info.value) or "valid range" in str(exc_info.value)


# ---------------------------------------------------------------------------
# update_account
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_account_success(mock_db: AsyncMock, sample_account_obj: Account) -> None:
    """Should update account fields."""
    data = AccountUpdate(name="Updated Bank Account")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_account_obj
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()

    result = await CoaService.update_account(mock_db, sample_account_obj.id, data)
    assert result.name == "Updated Bank Account"


@pytest.mark.asyncio
async def test_update_account_not_found(mock_db: AsyncMock) -> None:
    """Should raise AccountNotFoundError for non-existent account."""
    data = AccountUpdate(name="Does Not Exist")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    with pytest.raises(AccountNotFoundError) as exc_info:
        await CoaService.update_account(mock_db, uuid.uuid4(), data)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_account_code_range_violation(mock_db: AsyncMock) -> None:
    """Should raise InvalidCodeRangeError when new category conflicts with code."""
    acc = Account(id=uuid.uuid4(), code="1000", name="Bank", category="Asset", type="Bank", is_active=True, created_at=NOW, updated_at=NOW)
    data = AccountUpdate(category="Liability")  # 1000 is NOT in Liability range

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = acc
    mock_db.execute.return_value = mock_result

    with pytest.raises(InvalidCodeRangeError) as exc_info:
        await CoaService.update_account(mock_db, acc.id, data)
    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# soft_delete_account
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_soft_delete_account_success(mock_db: AsyncMock, sample_account_obj: Account) -> None:
    """Should set is_active=False."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_account_obj
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()

    result = await CoaService.soft_delete_account(mock_db, sample_account_obj.id)
    assert result.is_active is False


@pytest.mark.asyncio
async def test_soft_delete_account_not_found(mock_db: AsyncMock) -> None:
    """Should raise AccountNotFoundError."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    with pytest.raises(AccountNotFoundError):
        await CoaService.soft_delete_account(mock_db, uuid.uuid4())


# ---------------------------------------------------------------------------
# set_vat_rate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_set_vat_rate_success(mock_db: AsyncMock, sample_account_obj: Account) -> None:
    """Should update VAT rate."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_account_obj
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()

    result = await CoaService.set_vat_rate(mock_db, sample_account_obj.id, "20%")
    assert result.vat_rate == "20%"


# ---------------------------------------------------------------------------
# validate_account_code
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "code,category,expected",
    [
        ("1000", "Asset", True),
        ("1999", "Asset", True),
        ("2000", "Liability", True),
        ("2999", "Liability", True),
        ("3000", "Equity", True),
        ("4000", "Revenue", True),
        ("5000", "Expense", True),
        ("6999", "Expense", True),
        ("0999", "Asset", False),
        ("2000", "Asset", False),
        ("1000", "Liability", False),
        ("9999", "Expense", False),
        ("abcd", "Asset", False),
    ],
)
def test_validate_account_code(code: str, category: str, expected: bool) -> None:
    """Test code range validation for all categories."""
    assert CoaService.validate_account_code(code, category) == expected


# ---------------------------------------------------------------------------
# load_template
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_load_template_success(mock_db: AsyncMock) -> None:
    """Should load template and insert accounts."""
    template_data = [
        {"code": "1000", "name": "Bank", "category": "Asset", "type": "Bank", "vat_rate": None},
        {"code": "1010", "name": "Petty Cash", "category": "Asset", "type": "CurrentAsset", "vat_rate": None},
    ]

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()

    with (
        patch("src.services.coa_service.Path.exists", return_value=True),
        patch("builtins.open", MagicMock()),
        patch.object(json, "load", return_value=template_data),
    ):
        result = await CoaService.load_template(mock_db, "test_template")
        assert len(result) == 2
        mock_db.add.call_count == 2


@pytest.mark.asyncio
async def test_load_template_not_found(mock_db: AsyncMock) -> None:
    """Should raise TemplateNotFoundError for missing template."""
    with patch("src.services.coa_service.Path.exists", return_value=False):
        with pytest.raises(TemplateNotFoundError):
            await CoaService.load_template(mock_db, "nonexistent")


# ---------------------------------------------------------------------------
# list_available_templates
# ---------------------------------------------------------------------------

def test_list_available_templates() -> None:
    """Should return template names."""
    templates = CoaService.list_available_templates()
    # The directory should contain 8 template files
    assert len(templates) == 8
    assert "uk_sole_trader_no_vat" in templates
    assert "uk_limited_company_vat" in templates


# ---------------------------------------------------------------------------
# Account model validate_code_for_category
# ---------------------------------------------------------------------------

def test_account_model_validate_code() -> None:
    """Test the class method on Account model directly."""
    assert Account.validate_code_for_category("1000", "Asset") is True
    assert Account.validate_code_for_category("6000", "Expense") is True
    assert Account.validate_code_for_category("100", "Asset") is False
    assert Account.validate_code_for_category("5000", "Revenue") is False
