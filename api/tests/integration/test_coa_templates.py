"""Integration tests that verify all 8 COA templates can be loaded and contain expected account counts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

COA_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "coa_templates"

# Expected account counts per template (from the CONTRACT)
EXPECTED_COUNTS: dict[str, int] = {
    "uk_sole_trader_no_vat": 40,
    "uk_sole_trader_vat": 55,
    "uk_limited_company_no_vat": 50,
    "uk_limited_company_vat": 65,
    "uk_partnership_no_vat": 45,
    "uk_partnership_vat": 60,
    "micro_entity_simplified": 30,
    "property_landlord_vat": 45,
}

VALID_CATEGORIES = {"Asset", "Liability", "Equity", "Revenue", "Expense"}
VALID_TYPES = {
    "Bank",
    "CurrentAsset",
    "FixedAsset",
    "CurrentLiability",
    "LongTermLiability",
    "Equity",
    "Revenue",
    "DirectCost",
    "Expense",
}
VALID_VAT_RATES = {"20%", "5%", "0%", "exempt", None}


def _load_template(name: str) -> list[dict]:
    """Load a template JSON file and return its account list."""
    path = COA_TEMPLATES_DIR / f"{name}.json"
    assert path.exists(), f"Template file {path} not found"
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _all_templates_exist() -> bool:
    """All 8 template files must be present."""
    for name in EXPECTED_COUNTS:
        path = COA_TEMPLATES_DIR / f"{name}.json"
        assert path.exists(), f"Missing template: {name}.json"
    return True


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_all_templates_exist() -> None:
    """Verify all 8 COA template files are present."""
    assert _all_templates_exist()


@pytest.mark.parametrize(
    "template_name,expected_count",
    list(EXPECTED_COUNTS.items()),
)
def test_template_account_count(template_name: str, expected_count: int) -> None:
    """Verify each template has the expected number of accounts."""
    accounts = _load_template(template_name)
    assert len(accounts) == expected_count, (
        f"Template '{template_name}' has {len(accounts)} accounts, expected {expected_count}"
    )


@pytest.mark.parametrize("template_name", list(EXPECTED_COUNTS.keys()))
def test_template_account_codes_unique(template_name: str) -> None:
    """Verify that account codes are unique within each template."""
    accounts = _load_template(template_name)
    codes = [a["code"] for a in accounts]
    assert len(codes) == len(set(codes)), f"Duplicate codes in template '{template_name}'"


@pytest.mark.parametrize("template_name", list(EXPECTED_COUNTS.keys()))
def test_template_account_codes_numeric(template_name: str) -> None:
    """Verify that all account codes are numeric strings."""
    accounts = _load_template(template_name)
    for account in accounts:
        code = account["code"]
        assert code.isdigit(), f"Non-numeric code '{code}' in template '{template_name}'"
        assert 1000 <= int(code) <= 6999, f"Code '{code}' out of valid range in template '{template_name}'"


@pytest.mark.parametrize("template_name", list(EXPECTED_COUNTS.keys()))
def test_template_valid_categories(template_name: str) -> None:
    """Verify that all accounts have valid categories."""
    accounts = _load_template(template_name)
    for account in accounts:
        assert account["category"] in VALID_CATEGORIES, (
            f"Invalid category '{account['category']}' in template '{template_name}'"
        )


@pytest.mark.parametrize("template_name", list(EXPECTED_COUNTS.keys()))
def test_template_valid_types(template_name: str) -> None:
    """Verify that all accounts have valid types."""
    accounts = _load_template(template_name)
    for account in accounts:
        assert account["type"] in VALID_TYPES, (
            f"Invalid type '{account['type']}' in template '{template_name}'"
        )


@pytest.mark.parametrize("template_name", list(EXPECTED_COUNTS.keys()))
def test_template_valid_vat_rates(template_name: str) -> None:
    """Verify that all accounts have valid VAT rates (or null)."""
    accounts = _load_template(template_name)
    for account in accounts:
        vat = account.get("vat_rate")
        assert vat in VALID_VAT_RATES, (
            f"Invalid vat_rate '{vat}' in template '{template_name}'"
        )


@pytest.mark.parametrize("template_name", list(EXPECTED_COUNTS.keys()))
def test_template_code_in_category_range(template_name: str) -> None:
    """Verify each account code falls in the correct range for its category."""
    category_ranges = {
        "Asset": (1000, 1999),
        "Liability": (2000, 2999),
        "Equity": (3000, 3999),
        "Revenue": (4000, 4999),
        "Expense": (5000, 6999),
    }
    accounts = _load_template(template_name)
    for account in accounts:
        code_int = int(account["code"])
        min_val, max_val = category_ranges[account["category"]]
        assert min_val <= code_int <= max_val, (
            f"Code {account['code']} ({account['category']}) out of range "
            f"{min_val}-{max_val} in template '{template_name}'"
        )


@pytest.mark.parametrize("template_name", list(EXPECTED_COUNTS.keys()))
def test_template_required_fields(template_name: str) -> None:
    """Verify that all accounts have the required fields."""
    accounts = _load_template(template_name)
    required_fields = {"code", "name", "category", "type"}
    for account in accounts:
        missing = required_fields - set(account.keys())
        assert not missing, (
            f"Account in template '{template_name}' missing fields: {missing}"
        )
