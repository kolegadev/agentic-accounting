# CONTRACT: Module 1 — Chart of Accounts

## Goal
Implement a complete Chart of Accounts (COA) module with 8 pre-loaded UK-specific templates, 
5-category 4-digit numbering, and CRUD API endpoints.

## Boundaries
- **IN SCOPE**: Database schema for accounts, 8 COA JSON templates, FastAPI CRUD endpoints 
  (`GET /coa`, `POST /coa`, `PATCH /coa/{id}`, `GET /coa/{id}`, `DELETE /coa/{id}`),
  `PUT /coa/{id}/vat-rate`), account validation (code uniqueness, valid category/type),
  soft-delete support, VAT rate metadata per account
- **OUT OF SCOPE**: Formance ledger integration (Module 2), transaction posting, 
  multi-entity support, user authentication, frontend UI

## Technical Specifications
1. **DB Schema**: `accounts` table with fields: id (UUID PK), code (VARCHAR unique), name (VARCHAR), 
   category (ENUM: Asset/Liability/Equity/Revenue/Expense), type (ENUM: Bank/CurrentAsset/FixedAsset/
   CurrentLiability/LongTermLiability/Equity/Revenue/DirectCost/Expense), parent_id (FK self-ref, nullable),
   vat_rate (VARCHAR: '20%'/'5%'/'0%'/'exempt'), is_active (BOOLEAN default true),
   created_at, updated_at
2. **8 COA Templates** (JSON files in `coa_templates/`):
   - uk_sole_trader_no_vat.json (40 accounts)
   - uk_sole_trader_vat.json (55 accounts)
   - uk_limited_company_no_vat.json (50 accounts)
   - uk_limited_company_vat.json (65 accounts)
   - uk_partnership_no_vat.json (45 accounts)
   - uk_partnership_vat.json (60 accounts)
   - micro_entity_simplified.json (30 accounts)
   - property_landlord_vat.json (45 accounts)
3. **Numbering**: Assets 1000-1999, Liabilities 2000-2999, Equity 3000-3999, Revenue 4000-4999, 
   Expenses 5000-6999; intervals of 10 (1010, 1020, 1030...)
4. **API**: FastAPI routes with Pydantic schemas for request/response validation
5. **Database**: PostgreSQL via SQLAlchemy async; Alembic for migrations

## Success Criteria (Must Pass Verifier)
1. All 8 templates load correctly (exact account count per template)
2. Account code uniqueness enforced at DB level
3. Category validation rejects invalid categories
4. VAT rate validation (only 20%, 5%, 0%, exempt allowed)
5. Soft delete (is_active=false) hides from list but preserves in DB
6. API responses include correct HTTP status codes (201 created, 404 not found, 409 duplicate)
7. Unit tests: 90%+ coverage on models and routes
8. Integration tests: all CRUD operations, template loading, validation errors

## Files to Create
```
api/src/
  models/account.py          # SQLAlchemy model
  routes/coa.py              # FastAPI router
  services/coa_service.py    # Business logic
  validators/account.py      # Validation
  coa_templates/             # 8 JSON template files
api/tests/
  unit/test_coa_routes.py
  unit/test_coa_service.py
  integration/test_coa_templates.py
api/alembic/versions/001_initial_schema.py  # Migration
```

## Completion Signal
All tests pass, Verifier confirms, merge to main.
