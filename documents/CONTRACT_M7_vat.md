# CONTRACT: Module 7 — VAT Calculation & MTD Preview

## Goal
Implement UK VAT 9-box return calculation, 3 VAT schemes (standard accrual, cash accounting, flat rate),
MTD-compliant preview with digital links, and VAT audit trail.

## Boundaries
- IN SCOPE: vat_periods DB model, 9-box calculation from transaction data,
  standard/cash/flat-rate schemes, MTD digital link compliance (no cut-and-paste),
  VAT audit trail, 4 SKILLs (preview_return, transaction_detail, adjustment, audit_trail)
- OUT OF SCOPE: HMRC MTD API submission (Phase 2), EU VAT OSS (Phase 3),
  multi-tax jurisdictions (Phase 3)

## Technical Specs
### DB Schema
**vat_periods**: id (UUID PK), start_date (date), end_date (date), scheme (standard/cash/flat_rate), 
flat_rate_percentage (Decimal nullable), status (open/closed), closed_at (datetime tz nullable), created_at

**vat_returns**: id (UUID PK), period_id (FK), box1-box9 (all int pence),
submitted_at (nullable — MVP sets null since no actual submission), created_at

### UK VAT 9-Box Calculation
- Box 1: VAT due on sales (output VAT)
- Box 2: VAT due on EU acquisitions (0 for MVP)
- Box 3: Total output VAT (Box 1 + Box 2)
- Box 4: VAT reclaimed on purchases (input VAT)
- Box 5: Net VAT (Box 3 - Box 4)
- Box 6: Total sales excluding VAT
- Box 7: Total purchases excluding VAT
- Box 8: EU sales (0 for MVP)
- Box 9: EU acquisitions (0 for MVP)

### VAT Schemes
- Standard: VAT recognised on invoice date
- Cash: VAT recognised on payment date
- Flat Rate: simplified % of gross turnover

### API Endpoints
- POST /api/v1/vat/periods — create period
- GET /api/v1/vat/periods — list periods
- POST /api/v1/vat/periods/{id}/calculate — calculate 9-box return
- GET /api/v1/vat/returns/{id} — get return
- GET /api/v1/vat/returns/{id}/audit — audit trail
- POST /api/v1/vat/returns/{id}/adjustment — manual adjustment

## Success Criteria
1. All 9 boxes calculated correctly from transaction data
2. 3 VAT schemes supported with correct calculations
3. MTD digital link traceable (source→return)
4. Audit trail links every box figure to transactions
5. 90%+ test coverage

## Files
api/src/{models/vat.py, routes/vat.py, services/vat_service.py, validators/vat.py}
api/alembic/versions/007_vat.py
api/tests/{unit/test_vat_service.py, unit/test_vat_routes.py, integration/test_vat_return.py}
