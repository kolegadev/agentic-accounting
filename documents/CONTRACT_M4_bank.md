# CONTRACT: Module 4 — Bank Statement Import

## Goal
Implement bank statement import from CSV and OFX formats with flexible column mapping, 
7 pre-built UK bank templates, duplicate detection, and bank account management.

## Boundaries
- IN SCOPE: bank_accounts DB model, CSV import with auto-detection and flexible mapping,
  OFX parsing (1.02, 2.1, 2.2), 7 bank templates (Barclays, HSBC, Lloyds, NatWest, Monzo, 
  Starling, Revolut), duplicate detection (FITID for OFX, SHA-256 hash for CSV),
  imported transaction status flow (Imported → Categorized → Reconciled),
  6 SKILLs (import_csv, import_ofx, list_accounts, add_account, transactions, categorize)
- OUT OF SCOPE: Open Banking API feeds (Phase 2), auto-categorization rules (Phase 2),
  bank feed webhooks, Xero/QBO sync

## Technical Specs

### DB Schema
**bank_accounts**: id (UUID PK), name (str), sort_code (str), account_number (str),
iban (str nullable), currency (str default 'GBP'), opening_balance (int pence),
current_balance (int pence), is_active (bool), created_at, updated_at

**bank_transactions**: id (UUID PK), bank_account_id (FK), date (date), description (text),
amount (int pence, signed: positive=credit, negative=debit), reference (str nullable),
type (str nullable), fitid (str nullable for OFX dedup), import_hash (str SHA-256 for CSV dedup),
status (str: imported/categorized/reconciled), matched_transaction_id (UUID FK → transactions, nullable),
contact_id (UUID FK → contacts, nullable), category (str nullable), created_at

### File Parsing
- CSV: auto-detect columns (date/description/amount/debit/credit/reference/type);
  flexible delimiter detection (, ; \t)
- OFX: support versions 1.02, 2.1, 2.2 using ofxparse library

### Bank Templates (JSON files in api/src/bank_templates/)
Each template: {name, date_format, column_mappings: {date, description, amount, debit, credit, reference, type}}
- barclays.json, hsbc.json, lloyds.json, natwest.json, monzo.json, starling.json, revolut.json

### Duplicate Detection
- OFX: check FITID exists for bank_account
- CSV: SHA-256(date + amount + description) == import_hash

### API Endpoints
- POST /api/v1/bank/accounts — create bank account
- GET /api/v1/bank/accounts — list accounts
- GET /api/v1/bank/accounts/{id} — account details
- POST /api/v1/bank/import/csv — import CSV (multipart file upload)
- POST /api/v1/bank/import/ofx — import OFX (multipart file upload)
- GET /api/v1/bank/transactions — list transactions (filter: account_id, status, date range)
- PATCH /api/v1/bank/transactions/{id}/categorize — categorize transaction

## Success Criteria
1. CSV import with auto-detection works for all 7 bank formats
2. OFX import works for all three versions
3. Duplicate transactions detected and skipped
4. Bank account CRUD works
5. Transaction status flow correct
6. 90%+ test coverage

## Files
api/src/{models/bank_account.py, routes/bank.py, services/bank_service.py, validators/bank.py}
api/src/bank_templates/ (7 JSON files)
api/alembic/versions/004_bank.py
api/tests/{unit/test_bank_service.py, unit/test_bank_routes.py, integration/test_bank_import.py}
