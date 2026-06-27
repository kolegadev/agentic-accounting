# CONTRACT: Module 8 — Core Financial Reports

## Goal
Implement 5-stage report engine generating P&L, Balance Sheet, Trial Balance, Aged AR, and Aged AP.

## Boundaries
- IN SCOPE: report engine (parameter ingestion → query → transform → rules → format),
  5 reports: P&L (revenue-costs=profit), Balance Sheet (Assets=Liabilities+Equity),
  Trial Balance (debits==credits), Aged AR (30-60-90-90+), Aged AP,
  multiple output formats (JSON, CSV, HTML, PDF via WeasyPrint),
  3 SKILLs (report.run, report.list, report.schedule)
- OUT OF SCOPE: IFRS 18 5-category P&L (Phase 3), XBRL/iXBRL (Phase 4),
  custom report builder (Phase 3)

## Technical Specs
### DB Schema
**report_templates**: id (UUID PK), name (str unique), display_name, description, 
category (str), parameters_schema (JSONB), created_at
**scheduled_reports**: id (UUID PK), template_id (FK), schedule (str: daily/weekly/monthly/quarterly),
next_run (datetime), recipient_email, format (str: json/csv/html/pdf), is_active (bool), created_at

### Five-Stage Report Engine
1. Parameter Ingestion: validate period, comparison, format, number_format
2. Query Execution: aggregate from transactions+postings
3. Data Transformation: account grouping, period comparison
4. Rule Application: accounting rules, subtotals
5. Output Formatting: JSON, CSV, HTML, PDF

### Reports
- P&L: Revenue - Direct Costs = Gross Profit - Expenses = Net Profit
- Balance Sheet: Current Assets + Fixed Assets = Current Liabilities + Long-term Liabilities + Equity
- Trial Balance: every account with debit/credit totals, verified zero
- Aged AR: outstanding invoices by age bucket
- Aged AP: outstanding bills by age bucket

### API Endpoints
- GET /api/v1/reports/templates — list available reports
- POST /api/v1/reports/run — run report (body: template_name, start_date, end_date, format, comparison)
- GET /api/v1/reports/schedules — list scheduled reports
- POST /api/v1/reports/schedules — create schedule

## Files
api/src/{models/report.py, routes/reports.py, services/report_service.py, validators/report.py}
api/alembic/versions/008_reports.py
api/tests/{unit/test_report_service.py, unit/test_report_routes.py, integration/test_reports.py}
