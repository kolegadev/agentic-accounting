# CONTRACT: Module 5 — Manual Bank Reconciliation

## Goal
Implement conversational bank reconciliation matching bank transactions to ledger entries
with one-to-one, one-to-many, and partial matching, plus reconciliation reports.

## Boundaries
- IN SCOPE: reconciliation_sessions DB model, matching engine (1:1, 1:many, partial),
  reconciliation report (opening balance → transactions → closing balance),
  5 SKILLs (recon.start, recon.match, recon.create_and_match, recon.status, recon.report)
- OUT OF SCOPE: ML-powered auto-reconciliation (Phase 4), Open Banking auto-feeds (Phase 2)

## Technical Specs
### DB Schema
**reconciliation_sessions**: id (UUID PK), bank_account_id (FK), start_date, end_date,
opening_balance (int pence), closing_balance (int pence), status (open/closed),
matched_count, unmatched_count, total_bank_lines, created_at, closed_at

**reconciliation_matches**: id (UUID PK), session_id (FK), bank_transaction_id (FK),
transaction_id (FK → transactions table, nullable if new entry created),
match_type (one_to_one/one_to_many/partial/new_entry), amount_difference (int pence default 0),
description (text), created_at

### API Endpoints
- POST /api/v1/reconciliation/start — start session for bank account
- POST /api/v1/reconciliation/{session_id}/match — match bank line to ledger entry
- POST /api/v1/reconciliation/{session_id}/match-many — match one bank line to multiple ledger entries
- POST /api/v1/reconciliation/{session_id}/create-and-match — create new transaction and match
- GET /api/v1/reconciliation/{session_id}/status — session status with unmatched count
- GET /api/v1/reconciliation/{session_id}/report — reconciliation report

### Key Features
- One-to-one: one bank transaction → one ledger entry
- One-to-many: one bank deposit → multiple invoice payments
- Partial: bank amount differs from ledger amount (e.g., bank fees deducted)
- Report: opening_balance + matched_items = closing_balance verified

## Success Criteria
1. All matching patterns work (1:1, 1:many, partial)
2. Reconciliation report balances (opening + matched = closing)
3. Status tracking (open/closed with counts)
4. 90%+ test coverage

## Files
api/src/{models/reconciliation.py, routes/reconciliation.py, services/reconciliation_service.py, validators/reconciliation.py}
api/alembic/versions/005_reconciliation.py
api/tests/{unit/test_reconciliation_service.py, unit/test_reconciliation_routes.py, integration/test_reconciliation.py}
