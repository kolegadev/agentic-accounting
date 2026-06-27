"""Unit tests for report routes with mocked service layer."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.index import app
from src.validators.report import (
    ProfitAndLossReport,
    PnLSection,
    PnLAccountLine,
    BalanceSheetReport,
    BSSection,
    BSAccountLine,
    TrialBalanceReport,
    TrialBalanceLine,
    AgedARReport,
    AgedARLine,
    AgingBucket,
    AgedAPReport,
    AgedAPLine,
    ReportRunRequest,
    ReportRunResponse,
    ReportTemplateResponse,
    ReportTemplateListResponse,
    ScheduledReportResponse,
    ScheduledReportListResponse,
)

NOW = datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)
TODAY = date(2026, 6, 27)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _client() -> AsyncClient:
    """Return an AsyncClient using ASGI transport."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


def _sample_pl_report() -> ProfitAndLossReport:
    """Build a sample P&L report."""
    return ProfitAndLossReport(
        report_type="profit_and_loss",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
        comparison=False,
        revenue=PnLSection(
            section_name="Revenue",
            accounts=[
                PnLAccountLine(
                    account_id=uuid.uuid4(),
                    account_code="4000",
                    account_name="Sales",
                    amount=100_000_00,
                )
            ],
            subtotal=100_000_00,
        ),
        direct_costs=PnLSection(
            section_name="Direct Costs",
            accounts=[],
            subtotal=0,
        ),
        gross_profit=100_000_00,
        expenses=PnLSection(
            section_name="Expenses",
            accounts=[
                PnLAccountLine(
                    account_id=uuid.uuid4(),
                    account_code="5210",
                    account_name="Marketing",
                    amount=20_000_00,
                )
            ],
            subtotal=20_000_00,
        ),
        net_profit=80_000_00,
        generated_at=NOW,
    )


def _sample_bs_report() -> BalanceSheetReport:
    """Build a sample Balance Sheet report."""
    return BalanceSheetReport(
        report_type="balance_sheet",
        as_of_date=TODAY,
        current_assets=BSSection(
            section_name="Current Assets",
            accounts=[
                BSAccountLine(
                    account_id=uuid.uuid4(),
                    account_code="1000",
                    account_name="Bank",
                    amount=50_000_00,
                )
            ],
            subtotal=50_000_00,
        ),
        fixed_assets=BSSection(
            section_name="Fixed Assets",
            accounts=[],
            subtotal=0,
        ),
        total_assets=50_000_00,
        current_liabilities=BSSection(
            section_name="Current Liabilities",
            accounts=[],
            subtotal=0,
        ),
        long_term_liabilities=BSSection(
            section_name="Long-term Liabilities",
            accounts=[],
            subtotal=0,
        ),
        total_liabilities=0,
        equity=BSSection(
            section_name="Equity",
            accounts=[
                BSAccountLine(
                    account_id=uuid.uuid4(),
                    account_code="3000",
                    account_name="Capital",
                    amount=50_000_00,
                )
            ],
            subtotal=50_000_00,
        ),
        total_equity=50_000_00,
        total_liabilities_and_equity=50_000_00,
        balanced=True,
        generated_at=NOW,
    )


# ---------------------------------------------------------------------------
# Template listing
# ---------------------------------------------------------------------------


class TestTemplateRoutes:
    """Tests for GET /api/v1/reports/templates and GET /.../templates/{id}."""

    @pytest.mark.asyncio
    async def test_list_templates_empty(self):
        """Listing templates when none exist returns empty list."""
        mock_templates = ([], 0)

        with patch(
            "src.routes.reports.ReportService.list_templates",
            new_callable=AsyncMock,
            return_value=mock_templates,
        ):
            async with await _client() as client:
                response = await client.get("/api/v1/reports/templates")

        assert response.status_code == 200
        data = response.json()
        assert data["templates"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_templates_with_results(self):
        """Listing templates returns populated list."""
        tmpl_resp = ReportTemplateResponse(
            id=uuid.uuid4(),
            name="profit_and_loss",
            display_name="Profit & Loss",
            description="Income statement",
            category="financial",
            parameters_schema={},
            created_at=NOW,
        )
        mock_templates = ([tmpl_resp], 1)

        with patch(
            "src.routes.reports.ReportService.list_templates",
            new_callable=AsyncMock,
            return_value=mock_templates,
        ):
            async with await _client() as client:
                response = await client.get("/api/v1/reports/templates")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["templates"][0]["name"] == "profit_and_loss"

    @pytest.mark.asyncio
    async def test_get_template_not_found(self):
        """Getting a non-existent template returns 404."""
        with patch(
            "src.routes.reports.ReportService.get_template",
            new_callable=AsyncMock,
            return_value=None,
        ):
            async with await _client() as client:
                response = await client.get(
                    f"/api/v1/reports/templates/{uuid.uuid4()}"
                )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_template_found(self):
        """Getting an existing template returns it."""
        tmpl_resp = ReportTemplateResponse(
            id=uuid.uuid4(),
            name="balance_sheet",
            display_name="Balance Sheet",
            description=None,
            category="financial",
            parameters_schema={},
            created_at=NOW,
        )

        with patch(
            "src.routes.reports.ReportService.get_template",
            new_callable=AsyncMock,
            return_value=tmpl_resp,
        ):
            async with await _client() as client:
                response = await client.get(
                    f"/api/v1/reports/templates/{tmpl_resp.id}"
                )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "balance_sheet"


# ---------------------------------------------------------------------------
# Report run
# ---------------------------------------------------------------------------


class TestReportRunRoutes:
    """Tests for POST /api/v1/reports/run."""

    @pytest.mark.asyncio
    async def test_run_pl_report(self):
        """Running a P&L report returns the report data."""
        pl = _sample_pl_report()
        mock_response = ReportRunResponse(
            report_type="profit_and_loss",
            report=pl.model_dump(),
            format="json",
        )

        with patch(
            "src.routes.reports.ReportService.run",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            async with await _client() as client:
                response = await client.post(
                    "/api/v1/reports/run",
                    json={
                        "template_name": "profit_and_loss",
                        "start_date": "2026-01-01",
                        "end_date": "2026-06-30",
                        "format": "json",
                        "comparison": False,
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["report_type"] == "profit_and_loss"
        assert data["format"] == "json"
        assert data["report"]["gross_profit"] == 100_000_00
        assert data["report"]["net_profit"] == 80_000_00

    @pytest.mark.asyncio
    async def test_run_bs_report(self):
        """Running a Balance Sheet report returns the report data."""
        bs = _sample_bs_report()
        mock_response = ReportRunResponse(
            report_type="balance_sheet",
            report=bs.model_dump(),
            format="json",
        )

        with patch(
            "src.routes.reports.ReportService.run",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            async with await _client() as client:
                response = await client.post(
                    "/api/v1/reports/run",
                    json={
                        "template_name": "balance_sheet",
                        "start_date": "2026-01-01",
                        "end_date": "2026-06-27",
                    },
                )

        assert response.status_code == 200
        data = response.json()
        assert data["report_type"] == "balance_sheet"
        assert data["report"]["balanced"] is True

    @pytest.mark.asyncio
    async def test_run_with_invalid_params(self):
        """Running with invalid parameters returns 422."""
        from src.services.report_service import InvalidReportParameterError

        with patch(
            "src.routes.reports.ReportService.run",
            new_callable=AsyncMock,
            side_effect=InvalidReportParameterError("start_date must be before end_date"),
        ):
            async with await _client() as client:
                response = await client.post(
                    "/api/v1/reports/run",
                    json={
                        "template_name": "profit_and_loss",
                        "start_date": "2026-06-30",
                        "end_date": "2026-01-01",  # start > end
                    },
                )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_run_missing_required_fields(self):
        """Missing required fields returns 422."""
        async with await _client() as client:
            response = await client.post(
                "/api/v1/reports/run",
                json={},  # empty body
            )

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Scheduled reports
# ---------------------------------------------------------------------------


class TestScheduleRoutes:
    """Tests for /api/v1/reports/schedules endpoints."""

    @pytest.mark.asyncio
    async def test_list_schedules_empty(self):
        """Listing schedules when none exist."""
        mock_schedules = ([], 0)

        with patch(
            "src.routes.reports.ReportService.list_schedules",
            new_callable=AsyncMock,
            return_value=mock_schedules,
        ):
            async with await _client() as client:
                response = await client.get("/api/v1/reports/schedules")

        assert response.status_code == 200
        data = response.json()
        assert data["schedules"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_schedules_with_results(self):
        """Listing schedules returns populated results."""
        sched_resp = ScheduledReportResponse(
            id=uuid.uuid4(),
            template_id=uuid.uuid4(),
            schedule="monthly",
            next_run=datetime(2026, 7, 1, tzinfo=timezone.utc),
            recipient_email="test@example.com",
            format="pdf",
            is_active=True,
            created_at=NOW,
        )
        mock_schedules = ([sched_resp], 1)

        with patch(
            "src.routes.reports.ReportService.list_schedules",
            new_callable=AsyncMock,
            return_value=mock_schedules,
        ):
            async with await _client() as client:
                response = await client.get("/api/v1/reports/schedules")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["schedules"][0]["schedule"] == "monthly"

    @pytest.mark.asyncio
    async def test_create_schedule(self):
        """Creating a schedule returns 201."""
        sched_resp = ScheduledReportResponse(
            id=uuid.uuid4(),
            template_id=uuid.uuid4(),
            schedule="monthly",
            next_run=datetime(2026, 7, 1, tzinfo=timezone.utc),
            recipient_email="cfo@example.com",
            format="pdf",
            is_active=True,
            created_at=NOW,
        )

        with patch(
            "src.routes.reports.ReportService.create_schedule",
            new_callable=AsyncMock,
            return_value=sched_resp,
        ):
            async with await _client() as client:
                response = await client.post(
                    "/api/v1/reports/schedules",
                    json={
                        "template_id": str(sched_resp.template_id),
                        "schedule": "monthly",
                        "next_run": "2026-07-01T00:00:00Z",
                        "recipient_email": "cfo@example.com",
                        "format": "pdf",
                    },
                )

        assert response.status_code == 201
        data = response.json()
        assert data["schedule"] == "monthly"

    @pytest.mark.asyncio
    async def test_create_schedule_invalid_schedule(self):
        """Invalid schedule value returns 422."""
        async with await _client() as client:
            response = await client.post(
                "/api/v1/reports/schedules",
                json={
                    "template_id": str(uuid.uuid4()),
                    "schedule": "yearly",  # invalid
                    "next_run": "2026-07-01T00:00:00Z",
                },
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_schedule_not_found(self):
        """Getting non-existent schedule returns 404."""
        with patch(
            "src.routes.reports.ReportService.get_schedule",
            new_callable=AsyncMock,
            return_value=None,
        ):
            async with await _client() as client:
                response = await client.get(
                    f"/api/v1/reports/schedules/{uuid.uuid4()}"
                )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_schedule_success(self):
        """Deleting an existing schedule returns 204."""
        with patch(
            "src.routes.reports.ReportService.delete_schedule",
            new_callable=AsyncMock,
            return_value=True,
        ):
            async with await _client() as client:
                response = await client.delete(
                    f"/api/v1/reports/schedules/{uuid.uuid4()}"
                )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_schedule_not_found(self):
        """Deleting non-existent schedule returns 404."""
        with patch(
            "src.routes.reports.ReportService.delete_schedule",
            new_callable=AsyncMock,
            return_value=False,
        ):
            async with await _client() as client:
                response = await client.delete(
                    f"/api/v1/reports/schedules/{uuid.uuid4()}"
                )

        assert response.status_code == 404
