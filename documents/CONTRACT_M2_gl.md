# CONTRACT: Module 2 — Core General Ledger

## Goal
Implement the Core General Ledger: convert NL utterances into validated double-entry transactions 
with sum-to-zero enforcement, append-only postings, and 7 LLM SKILLs.

## Boundaries
- **IN SCOPE**: Transaction + Posting + VATLine DB models, Alembic migration, 
  FastAPI CRUD endpoints, NL-to-transaction parsing, double-entry validation (debits==credits),
  multi-line splits, VAT-inclusive/exclusive, JE-YYYY-NNNN numbering, Draft/Posted/Reversed status,
  append-only postings (no UPDATE/DELETE — corrections via reversing entries),
  idempotency keys (UUID), bi-temporal timestamps (effective_date + recorded_at),
  7 GL SKILLs (record_expense, record_income, record_transfer, journal_entry, list_transactions, 
  transaction_detail, undo_transaction)
- **OUT OF SCOPE**: Formance Ledger integration (deferred), bank feed auto-categorization,
  approval workflows, LLM integration (the SKILLs are API endpoints, LLM comes in Module 9)

## Technical Specifications

### Database Schema
1. **transactions**: id (UUID PK), reference (VARCHAR unique, JE-YYYY-NNNN format), 
   description (TEXT), contact_id (UUID FK nullable), total_amount (INTEGER in pence),
   currency (VARCHAR default 'GBP'), status (VARCHAR: draft/posted/reversed),
   effective_date (DATE), recorded_at (TIMESTAMPTZ), idempotency_key (UUID unique),
   created_at, updated_at
2. **postings**: id (UUID PK), transaction_id (UUID FK NOT NULL), 
   account_id (UUID FK NOT NULL — references accounts table from Module 1),
   debit_amount (INTEGER pence, default 0), credit_amount (INTEGER pence, default 0),
   description (TEXT), created_at
   - DB constraint: either debit_amount > 0 OR credit_amount > 0 (not both, not neither)
3. **vat_lines**: id (UUID PK), posting_id (UUID FK), vat_rate (VARCHAR: 20%/5%/0%/exempt),
   vat_amount (INTEGER pence), net_amount (INTEGER pence), vat_type (VARCHAR: input/output)

### API Endpoints
- POST /api/v1/transactions — create transaction (Draft)
- POST /api/v1/transactions/{id}/post — post transaction (Draft → Posted, runs validation)
- GET /api/v1/transactions — list transactions (filter by: status, date_from, date_to, contact_id)
- GET /api/v1/transactions/{id} — get transaction with postings
- POST /api/v1/transactions/{id}/reverse — create reversing entry (Posted → Reversed)
- GET /api/v1/transactions/{id}/audit — get full audit trail

### Double-Entry Validation (CRITICAL)
- **Sum-to-zero**: SUM(debit_amount) == SUM(credit_amount) for all postings in a transaction
- **No zero postings**: Every posting must have debit > 0 OR credit > 0
- **Account existence**: Every account_id must reference an active account in COA
- **Period check**: effective_date must be after the entity's period start
- Validation runs at POST time (post endpoint); Draft can be saved with partial data

### Journal Entry Numbering
- Format: JE-YYYY-NNNN (e.g., JE-2026-0001)
- Auto-incrementing per year, NNNN resets each year
- Generated when transaction is first posted, stored in reference field

### Idempotency
- Every transaction write requires client-generated UUID as idempotency_key
- Duplicate idempotency_key → return existing transaction (201 with existing data)
- No duplicate postings permitted

## Success Criteria (Must Pass Verifier)
1. All 4 DB tables created with proper constraints
2. Double-entry validation: sum_to_zero enforced, rejects unbalanced transactions with 422
3. Rejects postings with both debit and credit zero
4. Rejects postings with both debit and credit non-zero
5. Rejects references to non-existent or inactive accounts
6. JE numbering is sequential, resets per year, and unique
7. Idempotency: duplicate idempotency_key returns same transaction (no duplicate)
8. Soft-deleted transactions not returned in list by default
9. Reversing creates a compensating entry with opposite debits/credits
10. Unit tests: 90%+ coverage on models, validation, and routes
11. Integration tests: full CRUD cycle, validation errors, reversal

## Files to Create
```
api/src/
  models/transaction.py      # Transaction, Posting, VATLine models
  routes/transactions.py     # FastAPI router
  services/transaction_service.py
  validators/transaction.py  # Pydantic schemas
api/alembic/versions/002_transactions.py  # Migration
api/tests/
  unit/test_transaction_service.py
  unit/test_transaction_routes.py
  unit/test_transaction_validation.py  # Debits==Credits invariant tests
  integration/test_transaction_crud.py
```

## Completion Signal
All double-entry invariants pass, 90%+ test coverage, Verifier confirms.
