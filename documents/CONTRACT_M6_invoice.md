# CONTRACT: Module 6 — Basic Invoicing

## Goal
Implement sales invoice creation, lifecycle management (Draft→Sent→Viewed→Paid→Overdue→Cancelled),
PDF generation, credit notes, and email delivery tracking.

## Boundaries
- IN SCOPE: invoices DB model with line items, status lifecycle, immutability after Sent,
  credit notes (negative invoices), PDF generation (WeasyPrint), email tracking,
  6 SKILLs (create, send, list, mark_paid, credit_note, overdue)
- OUT OF SCOPE: Stripe/GoCardless integration (Phase 2), recurring invoices (Phase 2),
  purchase orders/bills (Phase 3), actual SMTP sending (use file output for MVP)

## Technical Specs
### DB Schema
**invoices**: id (UUID PK), reference (str unique, INV-YYYY-NNNN), contact_id (UUID FK not null),
status (str: draft/sent/viewed/paid/overdue/cancelled), issue_date (date), due_date (date),
subtotal (int pence), vat_total (int pence), total (int pence), currency (str default 'GBP'),
notes (text), sent_at (datetime tz nullable), viewed_at (datetime tz nullable),
paid_at (datetime tz nullable), created_at, updated_at

**invoice_lines**: id (UUID PK), invoice_id (FK not null), description (str),
quantity (int default 1), unit_price (int pence), vat_rate (str: 20%/5%/0%/exempt),
vat_amount (int pence), line_total (int pence), sort_order (int)

**credit_notes**: id (UUID PK), invoice_id (FK not null — original invoice ref),
reference (str unique, CN-YYYY-NNNN), contact_id (FK), total (int pence, negative),
reason (text), created_at

### Key Rules
- After Sent: core fields immutable (contact, line items, amounts, VAT)
- Corrections require credit note + re-issue
- INV-YYYY-NNNN numbering, sequential per year
- PDF generation via WeasyPrint with Jinja2 template
- Overdue: auto-detect invoices past due_date not in paid/cancelled status

### API Endpoints
- POST /api/v1/invoices — create (Draft)
- POST /api/v1/invoices/{id}/send — send to customer (immutability enforced)
- GET /api/v1/invoices — list (filter: status, contact_id, date range)
- GET /api/v1/invoices/{id} — detail with lines
- POST /api/v1/invoices/{id}/mark-paid — mark as paid
- POST /api/v1/invoices/{id}/cancel — cancel
- GET /api/v1/invoices/overdue — check overdue
- POST /api/v1/invoices/{id}/credit-note — create credit note
- GET /api/v1/invoices/{id}/pdf — download PDF

## Success Criteria
1. Full lifecycle works (draft→sent→viewed→paid)
2. Immutability after Sent enforced
3. Credit notes correctly offset original
4. INV numbering sequential
5. PDF generation produces valid output
6. 90%+ test coverage

## Files
api/src/{models/invoice.py, routes/invoices.py, services/invoice_service.py, validators/invoice.py}
api/src/templates/invoice_template.html
api/alembic/versions/006_invoicing.py
api/tests/{unit/test_invoice_service.py, unit/test_invoice_routes.py, integration/test_invoice_crud.py}
