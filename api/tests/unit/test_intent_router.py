"""Unit tests for IntentRouter — keyword matching, entity extraction, date parsing."""

from __future__ import annotations

import re
from unittest.mock import patch

import pytest

from src.services.intent_router import (
    IntentRouter,
    _TODAY,
    extract_amount,
    parse_natural_date,
)


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------
class TestParseNaturalDate:
    """Tests for the natural-language date parser."""

    def test_today(self) -> None:
        assert parse_natural_date("today") == _TODAY

    def test_yesterday(self) -> None:
        from datetime import timedelta
        assert parse_natural_date("yesterday") == _TODAY - timedelta(days=1)

    def test_tomorrow(self) -> None:
        from datetime import timedelta
        assert parse_natural_date("tomorrow") == _TODAY + timedelta(days=1)

    def test_last_month(self) -> None:
        from datetime import date
        result = parse_natural_date("last month")
        if _TODAY.month == 1:
            assert result == date(_TODAY.year - 1, 12, 1)
        else:
            assert result == date(_TODAY.year, _TODAY.month - 1, 1)

    def test_this_month(self) -> None:
        from datetime import date
        assert parse_natural_date("this month") == date(_TODAY.year, _TODAY.month, 1)

    def test_q2_2025(self) -> None:
        from datetime import date
        assert parse_natural_date("Q2 2025") == date(2025, 4, 1)

    def test_q3_no_year(self) -> None:
        # Should default to current year
        from datetime import date
        result = parse_natural_date("Q3")
        assert result is not None
        assert result.year == _TODAY.year
        assert result.month == 7
        assert result.day == 1

    def test_this_financial_year(self) -> None:
        from datetime import date
        result = parse_natural_date("this financial year")
        assert result is not None
        # Should return April 6 of appropriate year
        if (_TODAY.month, _TODAY.day) >= (4, 6):
            assert result == date(_TODAY.year, 4, 6)
        else:
            assert result == date(_TODAY.year - 1, 4, 6)

    def test_last_financial_year(self) -> None:
        from datetime import date
        result = parse_natural_date("last financial year")
        assert result is not None
        if (_TODAY.month, _TODAY.day) >= (4, 6):
            assert result == date(_TODAY.year - 1, 4, 6)
        else:
            assert result == date(_TODAY.year - 2, 4, 6)

    def test_iso_date(self) -> None:
        from datetime import date
        assert parse_natural_date("2025-06-27") == date(2025, 6, 27)

    def test_slash_date(self) -> None:
        from datetime import date
        result = parse_natural_date("2025/06/27")
        assert result == date(2025, 6, 27)

    def test_invalid_date_returns_none(self) -> None:
        assert parse_natural_date("not a date") is None


# ---------------------------------------------------------------------------
# Amount extraction
# ---------------------------------------------------------------------------
class TestExtractAmount:
    """Tests for currency amount extraction."""

    def test_simple_pounds(self) -> None:
        assert extract_amount("Paid £50 for supplies") == 5000

    def test_pounds_with_pence(self) -> None:
        assert extract_amount("Received £120.50 from client") == 12050

    def test_with_comma(self) -> None:
        assert extract_amount("Paid £1,200 for rent") == 120000

    def test_no_amount(self) -> None:
        assert extract_amount("Show me my accounts") is None

    def test_amount_with_quid(self) -> None:
        assert extract_amount("Spent 20 quid on lunch") == 2000

    def test_amount_with_pounds_word(self) -> None:
        assert extract_amount("Cost me 99.99 pounds") == 9999


# ---------------------------------------------------------------------------
# Keyword routing
# ---------------------------------------------------------------------------
class TestKeywordRouting:
    """Tests for keyword → skill mapping."""

    def setup_method(self) -> None:
        self.router = IntentRouter()

    def test_paid_routes_to_expense(self) -> None:
        skill_id, params, conf = self.router.route("I paid £50 for office supplies")
        assert skill_id == "gl.record_expense"
        assert params.get("amount") == 5000
        assert conf > 0.5

    def test_bought_routes_to_expense(self) -> None:
        skill_id, _, _ = self.router.route("Bought a new laptop for £800")
        assert skill_id == "gl.record_expense"

    def test_received_routes_to_income(self) -> None:
        skill_id, params, _ = self.router.route("Received £1,200 from Acme Ltd")
        assert skill_id == "gl.record_income"
        assert params.get("amount") == 120000

    def test_client_paid_routes_to_income(self) -> None:
        skill_id, _, _ = self.router.route("Client paid invoice INV-001")
        assert skill_id == "gl.record_income"

    def test_invoice_routes_to_create(self) -> None:
        skill_id, _, _ = self.router.route("Create an invoice for Acme")
        assert skill_id == "invoice.create"

    def test_vat_return_routes_to_vat(self) -> None:
        skill_id, _, _ = self.router.route("Show me my VAT return for Q2")
        assert skill_id == "vat.preview_return"

    def test_profit_loss_routes_to_report(self) -> None:
        skill_id, params, _ = self.router.route("Run a Profit & Loss for last month")
        assert skill_id == "report.run"
        assert params.get("report_type") == "profit_and_loss"

    def test_balance_sheet_routes_to_report(self) -> None:
        skill_id, params, _ = self.router.route("Show balance sheet")
        assert skill_id == "report.run"
        assert params.get("report_type") == "balance_sheet"

    def test_reconcile_routes_to_recon(self) -> None:
        skill_id, _, _ = self.router.route("Start a bank reconciliation")
        assert skill_id == "recon.start"

    def test_bank_statement_routes_to_import(self) -> None:
        skill_id, _, _ = self.router.route("Import my bank statement CSV")
        assert skill_id == "bank.import_csv"

    def test_chart_of_accounts_routes_to_coa(self) -> None:
        skill_id, _, _ = self.router.route("Show me my chart of accounts")
        assert skill_id == "coa.list"

    def test_add_account_routes_to_coa(self) -> None:
        skill_id, _, _ = self.router.route("Add a new expense account")
        assert skill_id == "coa.add_account"

    def test_unknown_falls_back_to_coa_list(self) -> None:
        skill_id, _, conf = self.router.route("Hello how are you")
        assert skill_id == "coa.list"
        assert conf == 0.1

    def test_transfer_routes_correctly(self) -> None:
        skill_id, _, _ = self.router.route("Transfer £500 from current to savings")
        assert skill_id == "gl.record_transfer"

    def test_send_invoice_routes_correctly(self) -> None:
        skill_id, _, _ = self.router.route("Send invoice INV-001 to customer")
        assert skill_id == "invoice.send"

    def test_overdue_routes_correctly(self) -> None:
        skill_id, _, _ = self.router.route("Which invoices are overdue?")
        assert skill_id == "invoice.overdue"

    def test_journal_entry_routes_correctly(self) -> None:
        skill_id, _, _ = self.router.route("Create a journal entry for depreciation")
        assert skill_id == "gl.journal_entry"

    def test_undo_routes_correctly(self) -> None:
        skill_id, _, _ = self.router.route("Undo the last transaction")
        assert skill_id == "gl.undo_transaction"


# ---------------------------------------------------------------------------
# Context injection
# ---------------------------------------------------------------------------
class TestContextInjection:
    """Tests that context values are injected into params."""

    def setup_method(self) -> None:
        self.router = IntentRouter()

    def test_contact_id_injected(self) -> None:
        ctx = {"contact_id": "abc-123"}
        _, params, _ = self.router.route("Create invoice", ctx)
        assert params.get("contact_id") == "abc-123"

    def test_bank_account_id_injected(self) -> None:
        ctx = {"bank_account_id": "bank-456"}
        _, params, _ = self.router.route("reconciliation", ctx)
        assert params.get("bank_account_id") == "bank-456"
