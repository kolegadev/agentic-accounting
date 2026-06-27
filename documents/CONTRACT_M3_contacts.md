# CONTRACT: Module 3 — Contact Management

## Goal
Implement Contact Management with CRUD API, auto-creation from transaction descriptions,
duplicate detection, and AR/AP balance tracking.

## Boundaries
- IN SCOPE: contacts DB model, Pydantic schemas, FastAPI CRUD endpoints,
  auto-creation from transaction, duplicate detection (name/email/VAT number),
  AR/AP balance tracking (total_invoiced, total_paid, total_owing),
  Active/Archived status lifecycle, 5 SKILLs (create, edit, list, detail, archive)
- OUT OF SCOPE: payment processing, invoice integration (Module 6), 
  multi-entity contact sharing

## Technical Specs
### DB Schema: contacts table
id (UUID PK), type (VARCHAR: customer/supplier/both), name (VARCHAR not null),
company (VARCHAR nullable), email (VARCHAR nullable), phone (VARCHAR nullable),
address_line1/2 (VARCHAR nullable), city (VARCHAR nullable), postcode (VARCHAR nullable),
country (VARCHAR default 'GB'), vat_number (VARCHAR nullable, UK/EU format),
payment_terms (VARCHAR default 'Net 30'), default_gl_account_id (UUID FK nullable),
currency (VARCHAR default 'GBP'), status (VARCHAR: active/archived),
total_invoiced (INTEGER pence default 0), total_paid (INTEGER pence default 0),
total_owing (INTEGER pence default 0), created_at, updated_at

### API Endpoints
- POST /api/v1/contacts — create
- GET /api/v1/contacts — list (filter: type, status, search)
- GET /api/v1/contacts/{id} — detail
- PATCH /api/v1/contacts/{id} — update
- POST /api/v1/contacts/{id}/archive — archive
- POST /api/v1/contacts/find-or-create — find by name/email/VAT or auto-create

### Key Features
- Duplicate detection: check name (fuzzy), email (exact), VAT number (exact)
- Auto-create: if transaction references unknown contact, create with type=supplier
- Balance tracking: total_invoiced - total_paid = total_owing
- Archived contacts hidden from list by default, not deletable

## Success Criteria
1. All CRUD operations work correctly
2. Duplicate detection prevents duplicate names/emails/VAT numbers
3. Auto-create from transaction references works
4. AR/AP balances calculated correctly
5. 90%+ test coverage

## Files
api/src/{models/contact.py, routes/contacts.py, services/contact_service.py, validators/contact.py}
api/alembic/versions/003_contacts.py
api/tests/{unit/test_contact_service.py, unit/test_contact_routes.py, integration/test_contact_crud.py}
