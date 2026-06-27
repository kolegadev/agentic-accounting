# Dimension 12: MVP Definition & Phased Roadmap

## Executive Summary

This document defines the complete Minimum Viable Product (MVP) scope and phased implementation roadmap for a headless, LLM-first accounting system designed to evolve from a foundational 8-week MVP to a full Xero-class platform over 15 months. The system is architected API-first with no traditional UI -- all interaction occurs via LLM chat interface and agent workflows.

**Key Design Principles:**
- **Headless architecture**: No traditional web UI; all user interaction via LLM natural language chat
- **API-first**: Every feature exposed via RESTful API with webhook support
- **Ledger-centric**: Formance-style programmable double-entry ledger with Numscript transaction modeling [^45^][^213^]
- **Compliance-native**: HMRC MTD VAT compliance built-in from day one [^124^][^583^]
- **SKILL-based**: All capabilities (reports, transactions, reconciliation) implemented as registered, schema-validated LLM skills

---

## Table of Contents

1. [MVP Scope (Weeks 1-8)](#1-mvp-scope-weeks-1-8)
2. [Phase 2: Automation (Months 3-5)](#2-phase-2-automation-months-3-5)
3. [Phase 3: Scale (Months 6-9)](#3-phase-3-scale-months-6-9)
4. [Phase 4: Enterprise (Months 10-15)](#4-phase-4-enterprise-months-10-15)
5. [Technical Architecture Decisions](#5-technical-architecture-decisions)
6. [Compliance Roadmap](#6-compliance-roadmap)
7. [Risk Register](#7-risk-register)

---

## 1. MVP Scope (Weeks 1-8)

### 1.1 Overview

The MVP delivers a functional single-entity accounting system for a UK VAT-registered small business, operated entirely through natural language conversation with an LLM. A solo founder, freelancer, or micro-business can record transactions, create invoices, reconcile bank statements, and generate core financial reports through chat.

**Target User**: UK-based freelancer, sole trader, or limited company director with 0-10 employees, VAT registered, single currency (GBP).

**Success Criteria**:
- User can complete full bookkeeping cycle via chat: record transactions → create invoice → import bank statement → reconcile → run VAT return → generate P&L and Balance Sheet
- All data passes double-entry validation (debits = credits on every transaction)
- HMRC MTD VAT nine-box return can be calculated and previewed
- End-to-end workflow completed without writing any code or opening a spreadsheet

---

### 1.2 Feature Specification: 10 Core Modules

#### Module 1: Chart of Accounts (Week 1)

**Purpose**: Hierarchical account structure forming the backbone of the general ledger.

**Features**:
- Pre-loaded COA templates (8 variants):
  - UK Sole Trader -- No VAT (40 accounts)
  - UK Sole Trader -- VAT Registered (55 accounts)
  - UK Limited Company -- No VAT (50 accounts)
  - UK Limited Company -- VAT Registered (65 accounts)
  - UK Partnership -- No VAT (45 accounts)
  - UK Partnership -- VAT Registered (60 accounts)
  - Micro-Entity Simplified (30 accounts)
  - Property/Landlord -- VAT Registered (45 accounts)
- Standard five-category numbering: Assets (1000-1999), Liabilities (2000-2999), Equity (3000-3999), Revenue (4000-4999), Expenses (5000-6999) [^264^][^405^]
- Account types: Bank, Current Asset, Fixed Asset, Current Liability, Long-term Liability, Equity, Revenue, Direct Cost, Expense
- VAT rate assignment per account (20% standard, 5% reduced, 0% zero-rated, exempt)
- Account enabling/disabling (soft delete)
- LLM SKILL: `coa.list`, `coa.add_account`, `coa.edit_account`, `coa.set_vat_rate`

**Technical Decisions**:
- Gaps of 10 between account codes for future insertion (1010, 1020, 1030...) [^264^]
- Each account maps to a Formance ledger account address: `gl:{account_code}:{entity_id}` [^213^]
- VAT rate stored as account metadata, applied automatically on transaction entry

**Complexity**: Low | **Effort**: 3 days

---

#### Module 2: Core General Ledger / Transaction Entry (Week 1-2)

**Purpose**: Double-entry transaction recording via natural language, backed by Formance-style programmable ledger.

**Features**:
- Natural language → structured transaction parsing via LLM
  - "Paid £120 to Acme Consulting for marketing services plus VAT" → parsed transaction with accounts, amounts, VAT split
  - "Received £2,400 from client ABC Ltd for website project invoice" → creates GL entry + marks invoice paid
- Numscript-style transaction modeling with sum-to-zero enforcement [^45^][^213^]
- Each transaction enforces: total debits = total credits at database constraint level
- Transaction metadata: date, description, reference, contact, attachments (placeholder)
- Support for: simple two-sided entries, multi-line splits, VAT-inclusive and VAT-exclusive amounts
- Journal entry numbering: auto-sequential (JE-YYYY-NNNN)
- Transaction status: Draft → Posted → Reversed
- Full audit trail: created_at, created_by, ip_address

**LLM SKILLs**:
| Skill ID | Description | Example Query |
|----------|-------------|---------------|
| `gl.record_expense` | Record expense payment | "Paid £50 for office stationery at Tesco" |
| `gl.record_income` | Record income receipt | "Received £500 from client for consulting" |
| `gl.record_transfer` | Bank-to-bank transfer | "Transferred £1,000 from current to savings" |
| `gl.journal_entry` | Manual journal entry | "Journal: Debit Rent £500, Credit Bank £500" |
| `gl.list_transactions` | List/filter transactions | "Show me all transactions last month" |
| `gl.transaction_detail` | View specific transaction | "Show me transaction JE-2025-0042" |
| `gl.undo_transaction` | Reverse transaction | "Undo that last entry, I made a mistake" |

**Data Model**:
```
transaction: id, date, description, reference, contact_id, total_amount, currency, status, metadata, created_at
posting: id, transaction_id, account_id, debit_amount, credit_amount, description
vat_line: id, posting_id, vat_rate, vat_amount, net_amount, vat_type (input/output)
```

**Technical Decisions**:
- Formance Ledger or equivalent self-hosted double-entry engine enforcing sum-to-zero at storage level [^45^]
- Append-only postings table -- no UPDATE/DELETE, corrections via reversing entries [^45^]
- Idempotency key on every transaction write (client-generated UUID) [^45^]
- Bi-temporal timestamps: `effective_date` (when event occurred) and `recorded_at` (when system recorded it) [^45^]

**Complexity**: High | **Effort**: 10 days

---

#### Module 3: Contact Management (Week 2)

**Purpose**: Customer and supplier directory for invoicing, purchases, and transaction attribution.

**Features**:
- Contact types: Customer, Supplier, Both
- Fields: name, company name, email, phone, billing address, shipping address, VAT number (EU/UK), payment terms (Net 30 default), default account, currency
- Contact status: Active / Archived
- Auto-creation from transaction descriptions (LLM extracts "Paid Spotify" → creates Spotify supplier if not exists)
- Duplicate detection by name/email/VAT number
- Contact balance tracking: total invoiced, total paid, total owing (AR/AP)

**LLM SKILLs**: `contact.create`, `contact.edit`, `contact.list`, `contact.detail`, `contact.archive`

**Complexity**: Low | **Effort**: 3 days

---

#### Module 4: Bank Statement Import (Week 2-3)

**Purpose**: Manual import of bank transactions from CSV/OFX files.

**Features**:
- CSV import with column mapping (date, description, amount/debit/credit, reference, type)
- OFX file parsing (standard financial data format) [^276^][^284^]
- Pre-built bank templates: Barclays, HSBC, Lloyds, NatWest, Monzo, Starling, Revolut
- Automatic duplicate detection using FITID (OFX) or hash of date+amount+description (CSV) [^276^]
- Bank account entity: account name, sort code, account number, IBAN, currency, opening balance, current balance
- Transaction status flow: Imported → Categorized → Reconciled
- Support for multiple bank accounts

**File Format Support**:
| Format | Version | Priority |
|--------|---------|----------|
| CSV | Any (flexible mapping) | P0 |
| OFX | 1.02, 2.1, 2.2 | P0 |
| QIF | Quicken Interchange | P1 (post-MVP) |

**LLM SKILLs**: `bank.import_csv`, `bank.import_ofx`, `bank.list_accounts`, `bank.add_account`, `bank.transactions`, `bank.categorize`

**Complexity**: Medium | **Effort**: 5 days

---

#### Module 5: Manual Bank Reconciliation (Week 3)

**Purpose**: Match imported bank transactions to ledger entries (invoices, bills, manual transactions).

**Features**:
- Side-by-side view: bank transactions on left, unmatched ledger entries on right (presented via LLM)
- Manual matching: user selects bank line + ledger entry → confirm match
- One-to-many matching: single bank deposit matching multiple invoice payments
- Partial matching: bank amount differs from invoice (e.g., bank fees deducted)
- Match criteria displayed: amount difference, date difference, reference similarity
- Reconciliation report: opening balance + bank transactions - reconciled = closing balance

**Reconciliation Workflow** [^220^][^338^]:
```
Step 1: Import bank statement (CSV/OFX)
Step 2: Review unmatched bank lines
Step 3: Match to existing invoices/bills/entries
Step 4: Create new ledger entries for unmatched items
Step 5: Confirm reconciliation balance
Step 6: Generate reconciliation report
```

**LLM SKILLs**:
| Skill ID | Description |
|----------|-------------|
| `recon.start` | "Start reconciliation for Barclays current account" |
| `recon.match` | "Match this £240 bank line to invoice INV-0012" |
| `recon.create_and_match` | "This £50 is for office supplies -- categorize and match" |
| `recon.status` | "Show me my reconciliation progress" |
| `recon.report` | "Generate reconciliation report for June" |

**Complexity**: Medium | **Effort**: 5 days

---

#### Module 6: Basic Invoicing (Week 3-4)

**Purpose**: Create, send, and manage sales invoices to customers.

**Features**:
- Invoice creation with line items (description, quantity, unit price, VAT rate, line total)
- Invoice status: Draft → Sent → Viewed → Paid → Overdue → Cancelled [^268^][^267^]
- Automatic invoice numbering (INV-YYYY-NNNN)
- VAT calculation per line and summary (UK 20% standard, 5% reduced, 0% zero-rated)
- Payment terms: Due on receipt, Net 7, Net 14, Net 30, Net 60
- Credit notes (negative invoice referencing original)
- Invoice totals: subtotal, VAT total, grand total
- PDF generation (printable invoice document)
- Email delivery tracking (viewed status)
- Overdue detection (time-based auto-transition)

**Invoice Lifecycle Protection** [^264^]:
- After invoice is SENT, core fields (customer, line items, amounts, VAT) become immutable
- Corrections require credit note + re-issue workflow
- Payment reconciliation is a safe post-send operation

**LLM SKILLs**:
| Skill ID | Example Query |
|----------|---------------|
| `invoice.create` | "Create invoice for ABC Ltd: 10 hours consulting at £80/hr plus VAT" |
| `invoice.send` | "Send invoice INV-2025-0012 to john@abcltd.com" |
| `invoice.list` | "Show me all unpaid invoices" |
| `invoice.mark_paid` | "Mark invoice INV-2025-0012 as paid -- £960 received today" |
| `invoice.credit_note` | "Create a credit note for £200 against invoice 0012" |
| `invoice.overdue` | "Which invoices are overdue?" |

**Complexity**: Medium | **Effort**: 6 days

---

#### Module 7: VAT Calculation & MTD Preview (Week 4-5)

**Purpose**: Calculate UK VAT Return figures and preview the nine-box return.

**Features**:
- Automatic VAT tracking on every transaction (input VAT on purchases, output VAT on sales)
- UK nine-box VAT return calculation [^79^][^85^]:
  - Box 1: VAT due on sales (output VAT)
  - Box 2: VAT due on acquisitions from EU (post-MVP)
  - Box 3: Total output VAT (Box 1 + Box 2)
  - Box 4: VAT reclaimed on purchases (input VAT)
  - Box 5: Net VAT position (Box 3 - Box 4)
  - Box 6: Total value of sales ex-VAT
  - Box 7: Total value of purchases ex-VAT
  - Box 8: EU sales (post-MVP)
  - Box 9: EU acquisitions (post-MVP)
- VAT audit trail: every transaction contributing to each box is traceable
- Flat Rate Scheme support (optional toggle)
- Cash vs. Accrual VAT scheme support
- VAT period configuration (monthly, quarterly, annual)
- MTD VAT return preview (not yet submitted -- preview only in MVP)

**Digital Link Compliance** [^124^][^583^]:
- All data flows from source (transaction entry) → VAT calculation → return preview via automated digital links
- No copy-paste or manual re-keying at any step
- Digital records preserved for 6 years as required by HMRC [^124^]

**LLM SKILLs**: `vat.preview_return`, `vat.transaction_detail`, `vat.adjustment`, `vat.audit_trail`

**Complexity**: Medium | **Effort**: 5 days

---

#### Module 8: Core Financial Reports (Week 5-6)

**Purpose**: Generate the four essential financial reports every business needs.

**Report SKILLs Implemented**:

| Report | SKILL ID | Description | Key Sections |
|--------|----------|-------------|-------------|
| Profit & Loss | `report.pl` | Revenue minus expenses over period | Revenue, Direct Costs, Gross Profit, Operating Expenses, Net Profit [^43^] |
| Balance Sheet | `report.bs` | Assets, liabilities, equity at point in time | Current Assets, Fixed Assets, Current Liabilities, Long-term Liabilities, Equity [^41^] |
| Trial Balance | `report.tb` | All account balances verifying debits=credits | Account, Debit, Credit, YTD Debit, YTD Credit [^137^][^142^] |
| Aged Receivables | `report.ar_aging` | Outstanding customer balances by bucket | Current, 1-30, 31-60, 61-90, 91+ days [^81^] |
| Aged Payables | `report.ap_aging` | Outstanding supplier balances by bucket | Current, 1-30, 31-60, 61-90, 91+ days [^81^] |

**Report Parameters**:
- Period: start_date, end_date
- Comparison: prior period, prior year
- Accounting basis: Accrual (default) / Cash
- Output: JSON (API), HTML (readable), PDF (document), CSV (spreadsheet)
- Number format: GBP with pence

**Report Engine Architecture**:
- 5-stage pipeline: Parameter Ingestion → Query Execution → Data Transformation → Rule Application → Output Formatting
- All reports are deterministic, cacheable SKILLs with JSON schemas
- IFRS 18 five-category P&L structure reserved for Phase 3 [^301^]

**LLM SKILLs**: `report.run`, `report.list`, `report.schedule`

**Example Queries**:
- "Show me my P&L for last quarter"
- "Generate a Balance Sheet as of June 30th"
- "Run aged receivables -- who owes me money?"
- "Trial balance for May 2025"

**Complexity**: Medium | **Effort**: 5 days

---

#### Module 9: LLM Chat Interface (Week 6-8)

**Purpose**: The sole user interface -- natural language conversation that orchestrates all accounting functions.

**Features**:
- Conversational transaction entry (multi-turn dialogue for complex transactions)
- Context memory: system remembers entity state (current VAT period, recent transactions, open invoices)
- Intent routing: LLM selects correct SKILL based on user intent, populates parameters
- Multi-turn workflows: "Create an invoice" → "Who for?" → "What items?" → "What terms?" → Confirm
- Error handling: if SKILL execution fails, LLM explains problem and suggests fix
- Confirmation gates: destructive actions (deletion, reversal) require explicit confirmation
- Natural date parsing: "last month", "yesterday", "Q2 2025", "this financial year"
- Ambiguity resolution: "You mentioned two invoices for ABC Ltd -- did you mean INV-0012 or INV-0015?"

**Architecture**:
```
User Message → Intent Classification → Skill Selection → Parameter Extraction 
    → Skill Execution (API call) → Result Interpretation → Natural Language Response
```

**Key Components**:
- **Skill Registry**: JSON schema definitions for all 25+ MVP skills with descriptions written from LLM perspective [^115^][^112^]
- **Context Manager**: Maintains conversation state, entity references, pending confirmations
- **Safety Layer**: `max_iterations` guards, permission checks, confirmation requirements [^112^]
- **Error Translator**: Converts API errors into user-friendly explanations

**Persona Options**:
- Professional Accountant (formal, precise)
- Friendly Advisor (conversational, proactive suggestions)
- Minimal (terse, data-focused)

**Complexity**: High | **Effort**: 10 days

---

#### Module 10: Authentication & Security (Week 2, ongoing)

**Features**:
- JWT-based API authentication
- Single user (MVP constraint)
- API key for programmatic access
- HTTPS/TLS for all communications
- Database encryption at rest
- Row-level audit logging on all financial transactions
- GDPR-compliant data handling (UK/EU basis)

**Complexity**: Low-Medium | **Effort**: 3 days

---

### 1.3 MVP Technical Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Ledger Engine** | Formance Ledger or custom double-entry PostgreSQL | Sum-to-zero enforcement, append-only, audit trail [^45^][^213^] |
| **API Framework** | FastAPI (Python) or NestJS (Node.js) | Rapid development, OpenAPI spec, async support |
| **Database** | PostgreSQL 16+ | ACID compliance, JSONB for metadata, window functions for reports |
| **LLM Orchestration** | OpenAI GPT-4o / Claude Sonnet via function calling | Function calling for SKILL routing, 128K context [^116^] |
| **Message Queue** | Redis or RabbitMQ | Async transaction processing, report generation |
| **Document Storage** | S3-compatible (MinIO) | PDF invoices, imported statements, attachments |
| **PDF Generation** | WeasyPrint or Playwright | Invoice PDFs, report PDFs |
| **Background Jobs** | Celery + Redis or BullMQ | Scheduled reports, VAT calculations, email sending |
| **Container** | Docker + Docker Compose | Consistent dev/prod environment |

---

### 1.4 MVP Data Model (Simplified)

```
[Entity] 1--* [Accounts] 1--* [Postings] *--1 [Transactions]
[Entity] 1--* [Contacts] 1--* [Invoices] 1--* [InvoiceLines]
[Entity] 1--* [BankAccounts] 1--* [BankTransactions]
[Entity] 1--* [VatReturns]
[Transactions] *--* [BankTransactions] (reconciliation_matches)
[Invoices] *--* [BankTransactions] (payment_matches)
```

---

### 1.5 MVP User Flows

#### Flow 1: First-Time Setup (Day 1)
```
User: "Set up my business"
System: "Great! What's your business name and type?"
User: "Acme Consulting Ltd, limited company"
System: "Are you VAT registered?"
User: "Yes, standard rate"
System: "What's your VAT number?"
User: "GB123456789"
System: "What's your financial year end?"
User: "March 31st"
→ System creates entity, loads "UK Limited Company -- VAT" COA template,
  sets VAT scheme, sets first VAT period
System: "You're all set! Your chart of accounts has been created with 65
  accounts pre-configured for a VAT-registered limited company.
  Your current VAT period is Q1 2025 (Jan-Mar). What would you like to do next?"
```

#### Flow 2: Daily Bookkeeping (Ongoing)
```
User: "Paid £156 to HMRC for corporation tax"
System: "Recorded: £156 payment to HMRC for Corporation Tax.
  Debit: Corporation Tax Expense (5200) £156
  Credit: Business Bank Account (1200) £156
  Reference: HMRC-CT-2025. Is this correct?"
User: "Yes"
→ Transaction posted, balances updated

User: "Received £2,400 from Smith & Co for the website project"
System: "I see invoice INV-2025-0003 for Smith & Co for £2,400.
  Should I mark this as paid?"
User: "Yes"
→ Invoice marked paid, bank account balance updated, VAT recorded
```

#### Flow 3: Month-End Reconciliation
```
User: "Import my bank statement"
System: "Which account and what format?"
User: "Barclays current account, CSV file"
→ User uploads file, system parses 47 transactions
System: "Imported 47 transactions. 12 already matched to existing entries.
  35 need categorization. Shall we go through them?"
User: "Yes"
→ System presents unmatched items one by one, user categorizes via chat

User: "Show me my reconciliation status"
System: "Barclays Current Account (****1234): 42 of 47 reconciled.
  Balance per bank: £12,456.78
  Balance per books: £12,456.78
  Status: RECONCILED"
```

#### Flow 4: VAT Return
```
User: "Show me my VAT return for this quarter"
System: "Here's your VAT return for Q1 2025 (Jan 1 -- Mar 31):
  Box 1 (VAT due on sales): £3,240.00
  Box 4 (VAT reclaimed): £1,856.40
  Box 5 (Net VAT due): £1,383.60
  Box 6 (Total sales ex-VAT): £16,200.00
  Box 7 (Total purchases ex-VAT): £9,282.00
  
  You owe HMRC £1,383.60, due by May 7th, 2025.
  
  Note: VAT submission to HMRC will be available in Phase 2.
  For now, you can use these figures with your existing MTD software."
```

---

### 1.6 MVP Timeline

| Week | Deliverables |
|------|-------------|
| **Week 1** | Project scaffolding, database schema, COA templates, GL engine core |
| **Week 2** | Contact management, bank account management, CSV/OFX import, auth |
| **Week 3** | Bank reconciliation engine, invoice creation/sending, PDF generation |
| **Week 4** | VAT calculation engine, nine-box return preview, credit notes |
| **Week 5** | Core report engine: P&L, Balance Sheet, Trial Balance |
| **Week 6** | Aged AR/AP reports, LLM skill registry, basic chat interface |
| **Week 7** | Multi-turn conversation flows, context management, error handling |
| **Week 8** | End-to-end testing, user acceptance testing, bug fixes, documentation |

**Total Effort**: ~48 engineering days (6 weeks at 100% velocity, 8 weeks at 75% velocity)
**Team**: 2-3 engineers (1 backend/ledger, 1 API/skills, 1 LLM/chat)

---

## 2. Phase 2: Automation (Months 3-5)

### 2.1 Overview

Phase 2 transforms the manual MVP into an automated system that reduces data entry effort by 70%+. The focus is on automatic data ingestion (bank feeds, document upload), intelligent categorization (rules engine), and collaboration features (multi-user, approvals).

**Target Outcome**: A business can operate with minimal manual data entry -- bank transactions flow in automatically, invoices and receipts are extracted from documents, and recurring transactions are handled without human intervention.

---

### 2.2 Feature List

#### 2.2.1 Bank Feed Integration (Month 3)

**Description**: Direct automated bank transaction import via Open Banking APIs.

**Aggregator Strategy** [^258^][^261^][^265^][^254^]:
| Provider | Region | Institutions | Priority |
|----------|--------|-------------|----------|
| **TrueLayer** | UK/EU | 1,000s | Primary for UK (PSD2, FCA-regulated) [^261^] |
| **Plaid** | UK/EU/US | 12,000+ | Secondary, broader coverage [^258^] |
| **Salt Edge** | 60+ countries | 3,000+ | Tertiary for EU multi-country [^265^] |
| **Yodlee** | Global | 17,000+ | Fallback for smaller institutions [^254^] |

**Features**:
- Open Banking connection via PSD2 APIs with Strong Customer Authentication (SCA) [^261^]
- Automatic daily polling for new transactions (configurable: hourly, daily, weekly)
- Historical backfill: up to 12-24 months on initial connection [^352^]
- Multi-bank support: unlimited connected accounts
- Automatic deduplication using persistent transaction IDs from aggregator [^348^]
- Real-time webhook support for instant transaction notification
- Connection health monitoring with automatic retry and alerting

**Ingestion Pipeline** [^221^][^222^]:
```
POLL (from aggregator API) → NORMALIZE (to canonical schema) → DEDUPLICATE 
  → QUEUE (message broker) → PROCESS (store + trigger matching)
```

**Canonical Transaction Schema** (normalized across all aggregators):
| Field | Type | Source Mapping |
|-------|------|---------------|
| `transaction_id` | string | Aggregator persistent ID |
| `account_id` | UUID | Internal bank account reference |
| `amount` | decimal | Normalized (positive=credit, negative=debit) |
| `currency` | string | ISO 4217 code |
| `transaction_date` | date | Posted date |
| `description` | string | Raw bank description |
| `merchant_name` | string | Cleaned merchant name (97% fill rate) [^348^] |
| `reference` | string | Transaction reference number |
| `transaction_type` | enum | debit, credit, transfer, fee, interest |
| `status` | enum | pending, posted, cancelled |
| `raw_data` | jsonb | Original aggregator response for audit |

**Technical Dependencies**: Open Banking aggregator account, FCA AISP registration (or partner with regulated entity)
**Complexity**: High | **Effort**: 15 days

---

#### 2.2.2 Bank Rules Engine (Month 3)

**Description**: Xero-style automatic categorization rules that match bank transactions and assign GL accounts, contacts, and VAT rates.

**Rule Structure** [^277^][^279^][^281^]:
```json
{
  "rule_id": "uuid",
  "rule_name": "Spotify Subscription",
  "bank_account_id": "uuid-or-all",
  "rule_type": "spend_money | receive_money | transfer",
  "conditions": [
    { "field": "description", "operator": "contains", "value": "SPOTIFY" },
    { "field": "amount", "operator": "between", "min": 5.00, "max": 20.00 }
  ],
  "condition_logic": "AND | OR",
  "actions": {
    "contact_id": "uuid",
    "account_id": "uuid",
    "tax_rate_id": "vat-20-expense",
    "tracking_category": "optional"
  },
  "auto_apply": false,
  "priority": 10,
  "active": true
}
```

**Condition Operators** [^277^]:
| Field | Operators |
|-------|-----------|
| Description | equals, contains, starts_with, ends_with, regex |
| Amount | equals, between, greater_than, less_than |
| Reference | equals, contains, regex |
| Bank Account | equals, in |
| Direction | is (spend/receive/transfer) |

**Execution Modes** [^277^]:
| Mode | Description | Risk |
|------|-------------|------|
| **Suggest** | Pre-fills categorization, user confirms | Low -- recommended default |
| **Auto-apply** | Automatically categorizes and posts | Medium -- only after proven reliable |
| **Disabled** | Rule stored but not evaluated | None |

**Features**:
- Visual rule builder (API-configurable)
- Rule priority ordering (first match wins)
- Conflict detection when multiple rules match
- Rule effectiveness analytics (% auto-matched vs. suggested vs. missed)
- Import/export rules as JSON
- Pre-built rule library: 50+ common patterns (Stripe payouts, AWS charges, council tax, etc.)

**LLM SKILLs**: `rule.create`, `rule.list`, `rule.edit`, `rule.reorder`, `rule.test`, `rule.analytics`

**Technical Dependencies**: Bank feed ingestion pipeline operational
**Complexity**: Medium | **Effort**: 8 days

---

#### 2.2.3 Recurring Transactions & Invoices (Month 3-4)

**Description**: Automated generation of recurring journals, invoices, and bills.

**Recurring Transactions**:
- Template-based with schedule: Weekly, Bi-weekly, Monthly, Quarterly, Annual
- End conditions: never, after N occurrences, until date
- Auto-post or draft-for-review mode
- Supports all transaction types: expense, income, transfer, journal
- Pre-built templates: rent, insurance, subscriptions, loan repayments, depreciation

**Recurring Invoices** [^220^][^349^][^350^]:
- Template + schedule architecture
- Auto-send via email or draft-for-review mode
- Automatic payment collection via Stripe/GoCardless integration (optional)
- Failed payment handling: retry logic, notification, manual retry
- Pull unbilled time/expenses onto generated invoices
- Series tracking: view all instances of a recurring invoice

**LLM SKILLs**: `recurring.create`, `recurring.list`, `recurring.edit`, `recurring.pause`, `recurring.delete`

**Complexity**: Medium | **Effort**: 8 days

---

#### 2.2.4 Document Upload & Data Extraction (Month 4)

**Description**: Upload receipt, invoice, and bill images/PDFs for automatic data extraction using OCR + LLM.

**Document Types Supported**:
| Type | Formats | Extraction Fields |
|------|---------|-------------------|
| Supplier invoices (bills) | PDF, JPG, PNG | Vendor, date, due date, line items, subtotal, VAT, total |
| Receipts | JPG, PNG, PDF | Vendor, date, items, total, payment method |
| Bank statements | PDF | Transactions for import (fallback to manual CSV) |
| Credit notes | PDF | Same as invoices |

**Extraction Pipeline** [^62^][^602^]:
```
Document Upload → Preprocessing (deskew, enhance) → OCR (Tesseract/DocTR) 
  → LLM Extraction (GPT-4o Vision / Claude) → Validation Rules 
  → Structured Output → Draft Transaction/Bill
```

**Key Metrics** [^602^]:
- OCR accuracy: 92-95% character level
- End-to-end extraction accuracy: 95-97% with validation rules
- Human intervention reduction: 80% vs. manual entry
- Processing time: seconds per document vs. minutes manually

**Validation Rules**:
- Amount consistency: sum of line items = subtotal = total - VAT
- Date validation: invoice date <= due date
- VAT calculation verification: VAT amount = net * rate
- Duplicate detection: same vendor + number + amount flagged

**Human-in-the-Loop** [^62^]:
- Low-confidence extractions (<90%) flagged for review
- Side-by-side: extracted data + original document shown together
- One-click correction: edit any field, system learns from correction

**LLM SKILLs**: `document.upload`, `document.extract`, `document.review`, `document.create_bill`, `document.create_expense`

**Technical Dependencies**: OCR engine (Tesseract/DocTR), LLM with vision (GPT-4o/Claude), document storage
**Complexity**: High | **Effort**: 12 days

---

#### 2.2.5 Multi-User Support & Permissions (Month 4)

**Description**: Multiple users can access the system with role-based permissions.

**Roles**:
| Role | Permissions |
|------|------------|
| **Owner** | Full access, can delete entity, manage users, billing |
| **Admin** | Full access except deletion, can manage users |
| **Bookkeeper** | Can record transactions, reconcile, run reports |
| **Accountant** | Read-only access to all data, can run reports, view VAT |
| **Viewer** | Read-only, no transaction details |

**Features**:
- User invitation via email
- Role assignment per user
- Activity logging: who did what, when
- Concurrent editing protection on transactions
- User-specific preferences (date format, currency display, timezone)

**LLM SKILLs**: `user.invite`, `user.list`, `user.edit_role`, `user.remove`, `user.activity`

**Complexity**: Low-Medium | **Effort**: 5 days

---

#### 2.2.6 Approval Workflows (Month 5)

**Description**: Multi-step approval chains for invoices, bills, and journal entries.

**Workflow Configuration**:
- Approval steps: 1-3 levels
- Threshold-based: different approvers for different amounts
  - e.g., < GBP 500: auto-approved; 500-2000: manager; >2000: director
- Approval types: invoice approval, bill payment approval, journal entry approval
- Delegate: approver can delegate during absence
- Reminder: automatic escalation after N days
- Approval via chat: "Approve invoice INV-2025-0024" or email approval link

**Status Flow**:
```
DRAFT → SUBMITTED_FOR_APPROVAL → APPROVED → POSTED/SENT
              |
              v
           REJECTED (with reason, back to draft)
```

**Notification**: Email + in-chat notification to approver when item pending

**LLM SKILLs**: `approval.submit`, `approval.approve`, `approval.reject`, `approval.list_pending`, `approval.configure`

**Technical Dependencies**: Multi-user support, email service
**Complexity**: Medium | **Effort**: 7 days

---

#### 2.2.7 HMRC MTD VAT Submission (Month 5)

**Description**: Direct digital submission of VAT returns to HMRC via MTD API.

**Requirements** [^124^][^579^][^583^]:
- HMRC Developer account registration
- VAT registration number linked to MTD
- Digital records maintained in functional compatible software
- Digital links from source data to return (no manual re-keying)
- OAuth2 authentication with HMRC
- Nine-box VAT return submitted via HMRC VAT API
- Submission confirmation and IR mark receipt
- View VAT obligations (periods due) from HMRC
- View VAT liabilities and payments from HMRC

**Features**:
- One-click VAT submission: "Submit my VAT return to HMRC"
- Pre-submission validation: all 9 boxes checked, no anomalies flagged
- HMRC obligation sync: system knows which periods are due
- Submission status tracking: Submitted → Acknowledged → Accepted
- Error handling: HMRC rejection reasons parsed and explained
- Correction workflow: Additional VAT return for amendments

**Compliance Checklist**:
- [x] Digital record keeping (all transactions digital from entry)
- [x] Digital links (automated flow from transactions → VAT calculation → return)
- [x] API submission to HMRC
- [x] 6-year digital record retention [^124^]
- [x] Audit trail of all submissions

**LLM SKILLs**: `vat.submit`, `vat.view_obligations`, `vat.view_payments`, `vat.correction`

**Technical Dependencies**: HMRC Developer account, VAT API credentials, OAuth2 flow
**Complexity**: High | **Effort**: 10 days

---

### 2.3 Phase 2 Technical Dependencies

| Feature | Depends On | Blocker Risk |
|---------|-----------|-------------|
| Bank feeds | Aggregator partnership/contract | Medium -- TrueLayer/Plaid have self-serve signup |
| Rules engine | Bank feeds pipeline | Low -- can build in parallel |
| Recurring | GL engine, invoicing | Low -- extends existing systems |
| Document extraction | OCR + LLM vision | Low -- GPT-4o vision API available |
| Multi-user | Auth system (MVP) | Low -- extends existing auth |
| Approvals | Multi-user, email | Low -- moderate complexity |
| MTD submission | HMRC dev account | Medium -- requires HMRC approval process |

### 2.4 Phase 2 Timeline

| Month | Deliverables |
|-------|-------------|
| **Month 3** | Bank feed integration (TrueLayer + Plaid), rules engine, recurring transactions |
| **Month 4** | Recurring invoices, document upload + OCR extraction, multi-user support |
| **Month 5** | Approval workflows, HMRC MTD VAT submission, Phase 2 testing & release |

**Total Effort**: ~65 engineering days
**Team**: 3-4 engineers

---

## 3. Phase 3: Scale (Months 6-9)

### 3.1 Overview

Phase 3 transforms the single-entity UK GBP system into a multi-currency, multi-jurisdiction platform suitable for growing businesses, e-commerce operations, and product-based companies. This phase adds inventory, fixed assets, UK payroll, and advanced reporting.

---

### 3.2 Feature List

#### 3.2.1 Multi-Currency Support (Month 6)

**Description**: Record and report transactions in multiple currencies with automatic exchange rate handling.

**Features**:
- 150+ currencies supported (ISO 4217)
- Exchange rate sources: ECB (EUR-based), XE.com, Open Exchange Rates
- Daily automatic rate updates
- Transaction-level currency recording
- Realized FX gain/loss calculation on payment
- Unrealized FX gain/loss for revaluation at period end
- Reporting in base currency (GBP) with original currency displayed
- Bank accounts in foreign currencies
- Invoice in customer's currency, convert to base currency for GL

**Exchange Rate Handling**:
| Transaction Type | Rate Applied | FX Treatment |
|-----------------|-------------|-------------|
| Invoice issued (foreign currency) | Spot rate at invoice date | Recorded at transaction rate |
| Payment received (foreign currency) | Spot rate at payment date | Realized gain/loss calculated |
| Period-end revaluation | Period-end closing rate | Unrealized gain/loss posted |

**Compliance**: ASC 830 (US GAAP) and IAS 21 (IFRS) multi-currency requirements [^585^]
**Complexity**: High | **Effort**: 10 days

---

#### 3.2.2 Multi-Tax Jurisdictions (Month 6)

**Description**: Expand beyond UK VAT to support multiple tax systems.

**Tax Types Supported** (from Dimension 05 research):
| Tax Type | Jurisdictions | Mechanism |
|----------|-------------|-----------|
| **VAT** | UK, EU (Germany, France, etc.) | Credit-invoice, input tax deduction [^257^] |
| **GST** | Australia, NZ, Singapore, Canada | Credit-invoice, input tax credits |
| **Sales Tax** | US (45 states) | Retail single-stage, no input credit [^234^][^236^] |
| **Digital Services Tax** | UK, France, Italy, Spain, etc. | Revenue-based [^235^] |

**Features**:
- Tax rule engine: jurisdiction-specific rates, thresholds, exemptions
- Place of supply determination (B2B vs. B2C) [^257^]
- Reverse charge handling for EU cross-border B2B
- US sales tax: economic nexus tracking, destination-based sourcing
- OSS (One-Stop Shop) EU reporting
- Tax registration threshold monitoring
- Multiple tax rates per invoice line (compound taxes)

**LLM SKILLs**: `tax.configure`, `tax.calculate`, `tax.return_preview`, `tax.threshold_check`

**Complexity**: Very High | **Effort**: 15 days

---

#### 3.2.3 Inventory / Stock Tracking (Month 7)

**Description**: Track stock quantities, values, and cost of goods sold.

**Features**:
- Product catalog: SKU, name, description, category, unit of measure
- Inventory tracking: quantity on hand, quantity committed, quantity available
- Cost methods: FIFO (default), Average Cost
- Stock adjustments: write-offs, damage, count adjustments
- Purchase orders: create, send to supplier, receive stock, match to bill
- Cost of Goods Sold (COGS) automatic calculation on sale
- Low stock alerts: configurable reorder points per product
- Stock valuation report at period end
- Integration with invoicing: invoice line linked to product, auto-reduces stock

**Inventory Transaction Flow**:
```
Purchase Order → Receive Stock (inventory increases, liability recorded)
    → Bill Received (matches PO, updates accounts payable)
Sales Invoice → Stock Allocated → Shipped (inventory decreases, COGS recorded)
    → Payment Received
```

**Complexity**: High | **Effort**: 12 days

---

#### 3.2.4 Fixed Asset Register (Month 7)

**Description**: Track fixed assets, calculate depreciation, and post depreciation journals.

**Features** [^586^][^591^]:
- Asset register: asset name, category, acquisition date, cost, useful life, residual value
- Asset categories with default settings: Buildings (50y), Vehicles (4y), IT Equipment (3y), Furniture (5y), Machinery (10y)
- Depreciation methods: Straight-line (default), Diminishing Value (reducing balance) [^591^]
- Automatic monthly depreciation calculation and journal posting
- Full depreciation on purchase option (immediate write-off)
- Asset disposal: calculate gain/loss, remove from register
- Asset reports: Depreciation Schedule, Asset Register, Asset Reconciliation
- Bulk import/export via CSV

**Depreciation Journal Entry**:
```
Debit: Depreciation Expense (5200) £XXX
Credit: Accumulated Depreciation -- {Category} (1510) £XXX
```

**Xero-style approach**: integrated asset register with depreciation journals posted to GL automatically [^591^]. No multi-book capability in this phase -- tax depreciation differences handled via manual adjustment.

**Complexity**: Medium | **Effort**: 8 days

---

#### 3.2.5 UK Payroll -- RTI Integration (Month 8)

**Description**: Full UK payroll processing with HMRC Real Time Information (RTI) submission.

**Payroll Features**:
- Employee records: personal details, NI number, tax code, salary/hourly rate, start date
- Pay elements: basic pay, overtime, bonuses, commissions
- Deductions: PAYE income tax, employee NICs, student loan, pension contributions
- Employer costs: employer NICs, pension contributions, apprenticeship levy
- Payslip generation (PDF)
- Pay runs: monthly, weekly, fortnightly, four-weekly
- FPS (Full Payment Submission): submitted to HMRC on or before payday [^592^][^593^]
- EPS (Employer Payment Summary): monthly adjustments, statutory payment reclaims [^598^]
- Starters and leavers processing (P45, starter checklist) [^600^]
- Statutory payments: SMP, SPP, SAP, SSP calculation and reclaim
- Employment Allowance claim
- P60 generation (year-end)
- Auto-enrolment pension compliance

**RTI Submissions** [^592^][^593^][^600^]:
| Submission | Frequency | Purpose |
|-----------|-----------|---------|
| FPS | Every pay run | Employee payments, tax, NICs, deductions |
| EPS | Monthly (by 19th) | Adjustments, reclaims, no-payment periods |
| EYU | As needed | Correct previous tax year errors |

**Penalties for Late Submission** [^593^]:
| Employees | Monthly Penalty |
|-----------|----------------|
| 1-9 | £100 |
| 10-49 | £200 |
| 50-249 | £300 |
| 250+ | £400 |

**Technical Dependencies**: HMRC PAYE API credentials, BACS payment integration (optional)
**Compliance**: UK Employment Law, Auto-enrolment regulations, HMRC RTI requirements
**Complexity**: Very High | **Effort**: 20 days

---

#### 3.2.6 Advanced Reporting & Custom Report Builder (Month 8-9)

**Description**: Expanded report library and custom report creation.

**Additional Reports**:
| Category | Report | SKILL ID |
|----------|--------|----------|
| Core | Cash Flow Statement | `core.cf` |
| Core | Statement of Changes in Equity | `core.sce` |
| Management | General Ledger Detail | `mgmt.gl_detail` |
| Management | Executive Summary | `mgmt.executive` |
| Management | Cash Summary | `mgmt.cash_summary` |
| Tax | Corporation Tax Computation | `tax.corporation_tax` |
| Variance | Budget vs Actual | `var.budget` |
| Variance | Period-over-Period Comparison | `var.period` |
| KPI | Profitability Ratios | `kpi.profitability` |
| KPI | Liquidity Ratios | `kpi.liquidity` |
| KPI | Burn Rate & Runway | `kpi.startup` |
| Audit | Audit Trail | `audit.audit_trail` |
| Audit | Journal Entry Report | `audit.journal_entries` |

**Custom Report Builder**:
- Drag-and-drop (API-configurable) report design
- Add/remove/reorder columns
- Filter by any field with conditions (equals, contains, greater than, between)
- Group by account, contact, date period, tracking category
- Sort by any column
- Save custom reports as templates
- Schedule reports: daily, weekly, monthly with email delivery
- Export: PDF, CSV, Excel, JSON

**Report Scheduling** [^139^][^114^]:
- Automatic generation at scheduled times
- Email delivery to configured recipients
- Date formulas: "LastMonth", "CurrentQuarter", "YearToDate", "Trailing12Months"
- Output formats: PDF attachment, CSV attachment, inline HTML

**LLM SKILLs**: `report.custom.create`, `report.custom.edit`, `report.schedule.create`, `report.schedule.list`

**Complexity**: High | **Effort**: 12 days

---

#### 3.2.7 Purchase Orders & Supplier Bills (Month 9)

**Description**: Full purchase-to-pay workflow from PO creation to payment.

**Features**:
- Purchase order creation with line items, quantities, prices, expected delivery
- PO status: Draft → Sent → Partially Received → Received → Billed → Closed
- Goods receipt: record partial or full delivery, updates inventory
- Bill creation from PO: auto-populates line items from received goods
- Three-way matching: PO → Goods Receipt → Bill [^220^]
- Bill approval workflow (leverages Phase 2 approvals)
- Bill payment scheduling: pay now or schedule for later
- A/P aging and payment forecasting

**LLM SKILLs**: `po.create`, `po.receive`, `po.convert_to_bill`, `bill.list_unpaid`, `bill.schedule_payment`

**Complexity**: Medium | **Effort**: 8 days

---

#### 3.2.8 Tracking Categories / Dimensions (Month 9)

**Description**: Dimensional analysis for segmenting transactions by department, region, project, or custom category.

**Features** (Xero-style tracking categories):
- Two tracking categories active at a time (e.g., "Department" and "Region")
- Unlimited options per category (e.g., Sales, Marketing, Operations)
- Applied to transactions, invoice lines, journal entries
- Filtering on all reports by tracking category
- Budgets per tracking category option
- P&L by tracking category report

**Example Categories**:
| Category | Options |
|----------|---------|
| Department | Sales, Marketing, Operations, Finance, HR, Engineering |
| Region | UK North, UK South, Europe, Americas, APAC |
| Project | Alpha, Beta, Gamma, Overhead |
| Cost Centre | CC001, CC002, CC003 |

**Complexity**: Low-Medium | **Effort**: 5 days

---

### 3.3 Phase 3 Technical Dependencies

| Feature | Depends On | Blocker Risk |
|---------|-----------|-------------|
| Multi-currency | GL engine (exchange rate fields) | Low |
| Multi-tax | Tax rule engine (Phase 3) | Medium -- requires tax research per jurisdiction |
| Inventory | GL engine, invoicing, PO module | Medium |
| Fixed assets | GL engine, depreciation calculation | Low |
| Payroll | HMRC PAYE API, employee module | High -- complex compliance requirements |
| Advanced reporting | Report engine (MVP) | Low -- extends existing system |
| PO/Bills | Inventory, approval workflows | Low -- builds on existing modules |
| Tracking categories | GL engine, all reports | Low |

### 3.4 Phase 3 Timeline

| Month | Deliverables |
|-------|-------------|
| **Month 6** | Multi-currency, multi-tax jurisdiction engine |
| **Month 7** | Inventory/stock tracking, fixed asset register |
| **Month 8** | UK payroll with RTI integration, advanced report library |
| **Month 9** | Custom report builder, purchase orders, tracking categories |

**Total Effort**: ~80 engineering days
**Team**: 4-5 engineers (add payroll specialist)

---

## 4. Phase 4: Enterprise (Months 10-15)

### 4.1 Overview

Phase 4 transforms the platform into a multi-entity, API-first accounting infrastructure suitable for accounting practices, multi-company groups, and enterprise deployment. This phase includes project tracking, expense claims, a full developer API platform, app marketplace, and white-label capabilities.

---

### 4.2 Feature List

#### 4.2.1 Multi-Entity Management (Month 10-11)

**Description**: Manage multiple legal entities (companies, subsidiaries) within a single account.

**Features** [^585^][^588^]:
- Entity creation: each entity has own COA, bank accounts, tax settings
- Entity switch: "Switch to Acme UK Ltd" or "Switch to Acme EU GmbH"
- Shared chart of accounts template across entities
- Intercompany transactions: automated double-entry across entities
- Entity-level user permissions: user can access subset of entities
- Consolidated reporting: roll up P&L, Balance Sheet across selected entities
- Automated intercompany elimination: intercompany sales/purchases netted to zero [^585^]
- Cross-entity dashboards: financial summary across all entities

**Intercompany Transaction Flow**:
```
Entity A: Invoice to Entity B
→ Creates payable in Entity A, receivable in Entity B
→ Auto-matched as intercompany pair
→ Eliminated in consolidated reports
```

**Non-Negotiable Capabilities** [^585^]:
- Automated intercompany elimination (no manual journals)
- Entity-level AND consolidated reporting from same data
- Shared services allocation (central costs allocated to entities)
- Multi-currency per entity with cumulative translation adjustments
- Audit trail and access controls by entity

**Complexity**: Very High | **Effort**: 18 days

---

#### 4.2.2 Project Tracking & Job Costing (Month 11)

**Description**: Track income, expenses, and profitability by project or job.

**Features**:
- Project creation: name, client, start/end dates, budget, status
- Time tracking: log hours by project, task, user
- Expense allocation: assign expenses (receipts, bills) to projects
- Invoice linking: invoices linked to projects for revenue tracking
- Project P&L: income vs. costs per project
- Budget vs. actual per project with variance alerts
- Project status: Planning → Active → On Hold → Completed → Archived
- Utilization reports: billable vs. non-billable hours
- Margin analysis: gross profit margin per project

**LLM SKILLs**: `project.create`, `project.log_time`, `project.allocate_expense`, `project.profitability`, `project.list`

**Complexity**: Medium | **Effort**: 10 days

---

#### 4.2.3 Expense Claims (Month 11-12)

**Description**: Employee expense submission, approval, and reimbursement.

**Features**:
- Expense claim creation: date, category, amount, description, receipt attachment
- Receipt capture: photo upload with OCR extraction
- Mileage tracking: rate per mile (HMRC approved rates: 45p/mile first 10,000, 25p thereafter)
- Per diem / subsistence claims
- Multi-level approval workflow (submitter → manager → finance)
- Reimbursement tracking: scheduled payment, marked paid
- Policy enforcement: category limits, daily limits, receipt requirements
- Integration with payroll: expense reimbursements on payslip
- Expense reports: by employee, by category, by period

**LLM SKILLs**: `expense.create`, `expense.submit`, `expense.approve`, `expense.list`, `expense.reimburse`

**Complexity**: Medium | **Effort**: 8 days

---

#### 4.2.4 API Platform & Developer Ecosystem (Month 12-13)

**Description**: Full public API with webhooks, SDKs, and developer documentation.

**API Features**:
- RESTful API for all operations (CRUD on all entities)
- OpenAPI 3.0 specification with auto-generated documentation
- Webhook system: subscribe to events (invoice.created, transaction.posted, bank.reconciled) [^603^]
- Rate limiting: tiered limits (free: 100/hr, pro: 10,000/hr, enterprise: unlimited)
- API versioning: URL-based versioning (/v1/, /v2/)
- OAuth2 authentication: client credentials and authorization code flows
- Pagination, filtering, sorting on all list endpoints
- Bulk operations: batch create transactions, batch update contacts
- SDKs: JavaScript/TypeScript, Python, PHP, Java, Go

**Webhook Events**:
| Event | Description |
|-------|-------------|
| `entity.created` | New entity created |
| `transaction.posted` | GL transaction posted |
| `invoice.created` | New invoice created |
| `invoice.paid` | Invoice marked paid |
| `invoice.overdue` | Invoice became overdue |
| `bank.transaction.imported` | Bank transaction imported |
| `bank.reconciled` | Account reconciliation completed |
| `vat.return.submitted` | VAT return submitted to HMRC |
| `contact.created` | New contact created |
| `report.generated` | Report generation completed |

**Developer Portal**:
- Interactive API explorer (Swagger UI)
- Code examples in all SDK languages
- Webhook testing endpoint
- Sandbox environment with test data
- App management: register, configure, monitor apps

**Complexity**: High | **Effort**: 15 days

---

#### 4.2.5 App Marketplace (Month 13-14)

**Description**: Third-party app integration marketplace similar to Xero App Store.

**Features**:
- App directory: browse, search, filter integrations by category
- App categories: Banking, CRM, E-commerce, Payroll, Inventory, Analytics, Tax, Time Tracking
- OAuth2 app installation: one-click connect with permission scopes
- App review process: submission, review, approval workflow
- App analytics: installs, active users, API calls for developers
- Featured / verified apps badge
- User reviews and ratings
- Billing integration: subscription management for paid apps

**Pre-built Integrations**:
| Category | Integration | Purpose |
|----------|------------|---------|
| Banking | TrueLayer, Plaid, Yodlee | Bank feeds |
| Payments | Stripe, GoCardless, PayPal | Invoice payment collection |
| E-commerce | Shopify, WooCommerce, Square | Sales import |
| CRM | HubSpot, Salesforce | Contact sync |
| Time Tracking | Toggl, Harvest | Time entry sync |
| Expenses | Pleo, Soldo | Business expense cards |
| Document | Dext, Hubdoc | Receipt capture |
| Analytics | Syft, Fathom | Advanced reporting |

**Technical Dependencies**: API platform (Phase 4), OAuth2, webhook infrastructure
**Complexity**: High | **Effort**: 12 days

---

#### 4.2.6 ML-Powered Reconciliation (JAX-Style) (Month 14)

**Description**: Machine learning matching engine that learns from user behavior to improve reconciliation accuracy.

**Architecture** (inspired by Xero JAX) [^345^][^346^][^349^][^351^]:
- **Rule layer**: User-defined bank rules (Phase 2)
- **Match layer**: Transaction matches existing documents (invoices, bills)
- **Memory layer**: Learns from user's historical reconciliation patterns
- **Prediction layer**: Suggests based on aggregate user behavior (anonymized)

**Features**:
- Per-organization model: separate ML model trained per entity [^345^]
- Training data: 12 months of historical reconciliation data [^352^]
- Feature vector: amount, day_of_week, hour, merchant_name, description keywords, historical category distribution
- Auto-reconcile target: 80%+ of bank lines in real-time [^347^]
- Confidence scoring: only auto-reconciles above threshold, flags lower for review [^351^]
- Continuous learning: model retrained periodically with new data
- Accuracy target: 97%+ on suggested matches [^349^]

**Model Architecture**:
- Classifier: Random Forest for mixed feature types [^280^]
- String similarity: FuzzyWuzzy for vendor name variations [^280^]
- Confidence calibration: probability output calibrated per organization

**Complexity**: Very High | **Effort**: 15 days

---

#### 4.2.7 White-Label / Embedded Accounting (Month 14-15)

**Description**: Rebrandable accounting platform for banks, fintechs, and vertical SaaS companies.

**Features**:
- White-label branding: custom logo, colors, domain
- Embedded UI components (chat widget, dashboard, report viewer)
- Multi-tenant architecture: separate data per deployment
- Partner portal: manage multiple white-label deployments
- Revenue sharing: usage-based billing for partners
- Custom onboarding flows per deployment
- Regulatory compliance per deployment region
- Single Sign-On (SSO) integration for partner platforms

**Target Partners**:
- Challenger banks (Monzo, Starling style) wanting built-in bookkeeping
- Vertical SaaS (property management, hospitality, retail)
- Fintech platforms (lending, payments, banking-as-a-service)
- Accounting practices wanting branded client portal

**Complexity**: High | **Effort**: 12 days

---

#### 4.2.8 Industry-Specific Modules (Month 15)

**Description**: Specialized features for specific industries.

**Modules**:

**Construction Industry Scheme (CIS)**:
- CIS contractor registration
- CIS deductions on subcontractor payments (20% registered, 30% unregistered)
- Monthly CIS300 return to HMRC
- CIS deduction statements to subcontractors
- CIS suffered reclaim via EPS [^598^]

**Property / Landlord**:
- Property portfolio tracking (per-property P&L)
- Rent roll management
- Tenant deposit handling
- Service charge apportionment
- Mortgage interest tracking

**SaaS / Subscription Business**:
- MRR/ARR tracking
- Churn analysis
- Customer cohort reporting
- Revenue recognition (IFRS 15 / ASC 606)
- Burn rate and runway calculation [^156^][^157^]

**Practice Management (for Accountants)**:
- Client management: multiple entities per client
- Bulk operations across client entities
- Practice-level reporting and analytics
- Time tracking and WIP (work in progress)
- Client billing and invoicing
- AML (Anti-Money Laundering) compliance checks

**Complexity**: Medium-High | **Effort**: 15 days (total across all modules)

---

### 4.3 Phase 4 Technical Dependencies

| Feature | Depends On | Blocker Risk |
|---------|-----------|-------------|
| Multi-entity | GL engine (entity isolation) | Medium -- requires data model changes |
| Project tracking | Invoicing, time tracking module | Low |
| Expense claims | Document OCR, approval workflows | Low -- builds on Phase 2/3 |
| API platform | All existing APIs | Low -- formalizes and extends |
| Marketplace | API platform, OAuth2 | Low |
| ML reconciliation | Bank feeds, rules engine, historical data | Medium -- requires ML expertise |
| White-label | Multi-tenant architecture | Medium |
| Industry modules | Phase 2/3 features | Low |

### 4.4 Phase 4 Timeline

| Month | Deliverables |
|-------|-------------|
| **Month 10-11** | Multi-entity management, intercompany transactions, consolidated reporting |
| **Month 11-12** | Project tracking, expense claims with receipt capture |
| **Month 12-13** | Public API platform, webhooks, SDKs, developer portal |
| **Month 13-14** | App marketplace, ML-powered reconciliation engine |
| **Month 14-15** | White-label platform, industry-specific modules |

**Total Effort**: ~105 engineering days
**Team**: 5-7 engineers (add ML engineer, DevOps, integrations specialist)

---

## 5. Technical Architecture Decisions

### 5.1 Ledger Engine Decision

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Formance Ledger** (open source) | Battle-tested, sum-to-zero enforcement, Numscript, multi-ledger isolation [^45^][^213^] | Newer project, smaller community | **Selected for MVP** |
| Custom PostgreSQL | Full control, no external dependency | Must build all ledger invariants ourselves | Fallback option |
| Apache BookKeeper | Mature, high throughput | Overkill for MVP, complex setup | Rejected |

### 5.2 LLM Provider Decision

| Provider | Strengths | Cost | Verdict |
|----------|-----------|------|---------|
| **OpenAI GPT-4o** | Best function calling, 128K context, vision support [^116^] | $$$ | **Primary for MVP** |
| **Claude Sonnet 3.5** | Excellent reasoning, long context, high invoice extraction accuracy [^72^] | $$ | **Secondary / extraction tasks** |
| **Local LLM** (Llama 3) | Privacy, no API costs | Infrastructure cost | Future option for sensitive data |

### 5.3 Database Decision

| Option | Verdict |
|--------|---------|
| **PostgreSQL 16+** | **Selected** -- ACID, JSONB, window functions, mature, managed options everywhere |
| TimescaleDB | Add-on for time-series if needed for high-volume bank transactions |
| Read replicas | For report queries to avoid impacting transaction processing |

### 5.4 Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CDN (CloudFront/Cloudflare)          │
├─────────────────────────────────────────────────────────────┤
│                    API Gateway (Rate Limiting)               │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   API Layer   │  │  LLM Chat     │  │  Webhook Service  │  │
│  │   (FastAPI)   │  │  Orchestrator │  │  (Event Delivery) │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │                  │                    │            │
│  ┌──────┴──────────────────┴────────────────────┴─────────┐  │
│  │              Application Services                        │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │  Ledger   │ │ Invoice  │ │   VAT    │ │  Report  │  │  │
│  │  │  Engine   │ │ Service  │ │  Engine  │ │  Engine  │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │  │
│  └────────────────────────┬───────────────────────────────┘  │
│                           │                                   │
│  ┌────────────────────────┼───────────────────────────────┐  │
│  │              Data Layer  │                               │  │
│  │  ┌──────────┐ ┌─────────┴─┐ ┌──────────┐ ┌──────────┐ │  │
│  │  │PostgreSQL│ │   Redis   │ │  MinIO   │ │Elasticsearch│ │  │
│  │  │ (Primary)│ │  (Cache/  │ │ (Object  │ │ (Search/  │ │  │
│  │  │          │ │   Queue)  │ │ Storage) │ │  Logs)   │ │  │
│  │  └──────────┘ └───────────┘ └──────────┘ └──────────┘ │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Compliance Roadmap

### 6.1 UK Regulatory Compliance

| Regulation | MVP | Phase 2 | Phase 3 | Phase 4 |
|-----------|-----|---------|---------|---------|
| **HMRC MTD VAT** | Digital records, 9-box calculation, preview only [^124^][^583^] | Full API submission to HMRC [^579^] | Multi-scheme (cash/accrual/flat rate) | Group VAT, partial exemption |
| **HMRC RTI Payroll** | -- | -- | FPS + EPS submission [^592^][^593^] | Full PAYE, auto-enrolment |
| **Companies House** | -- | -- | iXBRL preview | Full iXBRL filing (mandatory April 2027) [^159^] |
| **GDPR** | Basic data handling consent | Full GDPR compliance, data export, deletion | DPO workflow | Cross-border data transfer |
| **UK GAAP/FRS 102** | -- | -- | FRS 102 reporting templates | Full FRS 102 support |
| **IFRS 18** | -- | -- | -- | P&L restructuring (effective Jan 2027) [^301^] |
| **AML (Accountants)** | -- | -- | -- | Client verification, risk assessment |
| **CIS** | -- | -- | -- | CIS300 monthly returns [^598^] |

### 6.2 International Compliance

| Jurisdiction | Phase 3 | Phase 4 |
|-------------|---------|---------|
| **EU VAT** | OSS registration, intra-community supplies [^257^] | Local VAT filings per country |
| **US Sales Tax** | Economic nexus tracking, destination sourcing [^234^] | Full multi-state filing |
| **Australia GST** | BAS reporting | Full ATO integration |
| **Canada GST/HST** | GST34 calculation | CRA integration |

---

## 7. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R1 | HMRC API changes break MTD submission | Medium | High | Abstract HMRC API layer; monitor HMRC developer updates |
| R2 | LLM hallucination causes incorrect transaction recording | Medium | High | Confirmation gates for all transactions; full audit trail; undo capability |
| R3 | Open Banking aggregator downtime | Medium | Medium | Multi-aggregator failover chain; manual import fallback |
| R4 | Exchange rate API failure | Low | Medium | Cached rates; manual override; fallback providers |
| R5 | Payroll calculation errors | Low | Very High | Extensive testing against HMRC calculators; beta with volunteer users |
| R6 | Multi-entity consolidation errors | Medium | High | Automated elimination checks; reconciliation reports; audit trail |
| R7 | LLM context window exceeded for large reports | Medium | Medium | Streaming reports; pagination; summary-first approach |
| R8 | Regulatory deadline changes (IFRS 18, Companies House) | Medium | Medium | Modular report architecture; configurable templates |
| R9 | Data loss / corruption | Low | Very High | Daily backups; append-only ledger; point-in-time recovery |
| R10 | Scaling bottleneck on transaction volume | Low | High | Read replicas; caching; async processing; horizontal scaling |

---

## 8. Summary: Complete Feature Roadmap

### Feature Count by Phase

| Phase | Duration | New Features | Cumulative Features |
|-------|----------|-------------|-------------------|
| **MVP** | 8 weeks | 10 modules, 25+ LLM skills | 25+ skills |
| **Phase 2** | 3 months | 7 major features, 40+ skills | 65+ skills |
| **Phase 3** | 4 months | 8 major features, 55+ skills | 120+ skills |
| **Phase 4** | 6 months | 8 major features, 70+ skills | 190+ skills |

### Engineering Effort Summary

| Phase | Effort (days) | Team Size | Calendar Time |
|-------|--------------|-----------|---------------|
| MVP | 48 | 2-3 | 8 weeks |
| Phase 2 | 65 | 3-4 | 3 months |
| Phase 3 | 80 | 4-5 | 4 months |
| Phase 4 | 105 | 5-7 | 6 months |
| **Total** | **298** | **5-7 (peak)** | **15 months** |

### Xero Feature Parity Progression

| Capability | Xero Features | Our Timeline | Parity |
|-----------|--------------|-------------|--------|
| Core accounting (GL, invoicing, bank, VAT, reports) | ~30 | MVP (8 wks) | 60% |
| + Automation (feeds, rules, recurring, MTD) | ~25 | Phase 2 (M3-5) | 75% |
| + Scale (multi-currency, payroll, inventory, assets) | ~35 | Phase 3 (M6-9) | 88% |
| + Enterprise (multi-entity, projects, marketplace) | ~30 | Phase 4 (M10-15) | 95%+ |

---

## Citations

[^45^] Formance, "Double-Entry Accounting for Engineers: A Practical Guide," 2026. https://www.formance.com/blog/engineering/double-entry-accounting-for-engineers-building-financial-products

[^213^] Formance Documentation, "Ledger - Programmable, double-entry accounting database." https://docs.formance.com/modules/ledger

[^124^] BRIGHT, "How do I submit a Making Tax Digital VAT return to HMRC?" 2026. https://brightsg.com/blog/how-to-submit-a-making-tax-digital-vat-return-to-hmrc/

[^583^] HMRC, "VAT Notice 700/22: Making Tax Digital for VAT," 2018. https://www.gov.uk/government/publications/vat-notice-70022-making-tax-digital-for-vat/vat-notice-70022-making-tax-digital-for-vat

[^579^] Capium, "MTD VAT software: what HMRC requires vs what businesses actually need," 2026. https://www.capium.com/mtd-vat-software-what-hmrc-requires-vs-what-businesses-actually-need/

[^264^] Ramp, "Free Chart of Accounts Template & Guide," 2026. https://ramp.com/blog/chart-of-accounts-template

[^405^] NetSuite, "Chart of Accounts: Definition, Best Practices, and Examples," 2025. https://www.netsuite.com/portal/resource/articles/accounting/chart-of-accounts.shtml

[^584^] Xero Blog, "New chart of accounts templates in Xero HQ for UK partners," 2023. https://blog.xero.com/accountants-bookkeepers/new-chart-of-account-templates-in-xero-hq-for-uk-partners/

[^592^] BrightPay, "Full Payment Submission (FPS)," 2026. https://payrollsupport.uk.brightsg.com/hc/en-gb/articles/35961189400849-Full-Payment-Submission-FPS

[^593^] Cintra, "What is Real Time Information?" 2026. https://cintra.co.uk/blog/real-time-information/

[^598^] Mercans, "Employer Payment Summary Submission - EPS," 2025. https://mercans.com/glossary/employer-payment-summary/

[^600^] HMRC, "Background: real time information (RTI): submission types," 2016. https://www.gov.uk/hmrc-internal-manuals/paye-manual/paye5025

[^586^] House Blend, "Fixed Asset Software Compared: NetSuite, Sage, Xero, QB," 2026. https://www.houseblend.io/articles/fixed-asset-management-software-comparison

[^591^] Xero, "Automated Asset Depreciation Software." https://www.xero.com/us/accounting-software/asset-depreciation-software/

[^585^] Wiss, "Multi-Entity Accounting Software: A CFO's Guide," 2026. https://wiss.com/multi-entity-accounting-software-cfo-guide/

[^588^] Avantiico, "The Best Multi-Entity Accounting Software Platforms in 2025," 2025. https://avantiico.com/best-multi-entity-accounting-platforms-2025/

[^62^] Invoice Data Extraction, "Invoice Extraction Using LLMs: How It Works and What to Expect," 2026. https://invoicedataextraction.com/blog/invoice-extraction-using-llm

[^602^] Shetty et al., "Automated Invoice Data Extraction: Using LLM and OCR," arXiv, 2025. https://arxiv.org/pdf/2511.05547

[^604^] Bardvall, "Automating Invoice Recognition," DiVA Portal, 2024. https://www.diva-portal.org/smash/get/diva2:1886537/FULLTEXT01.pdf

[^594^] Xero, "AI for small business: practical tools to save time," 2026. https://www.xero.com/hk/guides/why-ai-is-essential-for-business/

[^599^] Coefficient, "Latest Xero AI Features - 2025," 2025. https://coefficient.io/saas-ai-tools/xero-ai-features

[^603^] MetaDesign Solutions, "Xero Integration Company | Hire Xero API Developers," 2026. https://metadesignsolutions.com/services/enterprise-software/accounting-saas/xero

[^258^] Plaid, product documentation and coverage data. Referenced in Dimension 06 research.

[^261^] TrueLayer, product documentation and PSD2 coverage. Referenced in Dimension 06 research.

[^265^] Salt Edge, product documentation. Referenced in Dimension 06 research.

[^254^] Yodlee (Envestnet), product documentation. Referenced in Dimension 06 research.

[^348^] Plaid, /transactions/sync API documentation. Referenced in Dimension 06 research.

[^352^] Plaid, historical backfill documentation. Referenced in Dimension 06 research.

[^221^] Data pipeline architecture references. Referenced in Dimension 06 research.

[^222^] Enterprise data pipeline patterns. Referenced in Dimension 06 research.

[^276^] OFX FITID-based duplicate prevention. Referenced in Dimension 06 research.

[^284^] QBO FITID deduplication. Referenced in Dimension 06 research.

[^277^] Xero Bank Rules documentation. Referenced in Dimension 06 research.

[^279^] Xero Bank Rules condition operators. Referenced in Dimension 06 research.

[^281^] Xero Bank Rules types (spend/receive/transfer). Referenced in Dimension 06 research.

[^280^] Enterprise reconciliation matching systems. Referenced in Dimension 06 research.

[^282^] Multi-stage matching architecture patterns. Referenced in Dimension 06 research.

[^345^] Xero JAX per-organization ML model. Referenced in Dimension 06 research.

[^346^] Xero JAX four-layer intelligence. Referenced in Dimension 06 research.

[^349^] Xero JAX 97%+ accuracy claim. Referenced in Dimension 06 research.

[^351^] Xero JAX auto-reconcile confidence threshold. Referenced in Dimension 06 research.

[^347^] Xero JAX 80%+ auto-reconcile target. Referenced in Dimension 06 research.

[^220^] QuickBooks Online / FreshBooks recurring invoice implementations. Referenced in Dimension 07 research.

[^268^] PayPal / Stripe invoice status flow patterns. Referenced in Dimension 07 research.

[^267^] OpenMeter / Monite invoice lifecycle patterns. Referenced in Dimension 07 research.

[^266^] Standard invoice status definitions. Referenced in Dimension 07 research.

[^350^] FreshBooks AutoPay/AutoCollect patterns. Referenced in Dimension 07 research.

[^349^] FreshBooks recurring template + schedule architecture. Referenced in Dimension 07 research.

[^353^] FreshBooks payment schedules (up to 12 installments). Referenced in Dimension 07 research.

[^72^] AIMultiple, "Invoice OCR Benchmark: Extraction Accuracy of LLMs vs OCRs," 2026. https://aimultiple.com/invoice-ocr

[^116^] Function calling / tool calling architecture patterns. Referenced in Dimension 08 research.

[^115^] Tool description best practices for LLM agents. Referenced in Dimension 08 research.

[^112^] Agent architecture: Agent, Registry, LLM components. Referenced in Dimension 08 research.

[^43^] IFRS financial statement line item requirements. Referenced in Dimension 06 (wide) research.

[^41^] IFRS Balance Sheet minimum line items. Referenced in Dimension 06 (wide) research.

[^137^] Trial Balance types and structure. Referenced in Dimension 06 (wide) research.

[^142^] Trial Balance three-column layout. Referenced in Dimension 06 (wide) research.

[^81^] Aged Receivables/Payables time bucket structure. Referenced in Dimension 06 (wide) research.

[^301^] IFRS 18 effective January 2027. Referenced in Dimension 08 research.

[^257^] OECD VAT/GST Guidelines for place of supply. Referenced in Dimension 05 research.

[^234^] Economic nexus thresholds post-Wayfair. Referenced in Dimension 05 research.

[^236^] Texas $500K economic nexus threshold. Referenced in Dimension 05 research.

[^235^] Digital Services Tax implementation by country. Referenced in Dimension 05 research.

[^139^] Automated report distribution systems. Referenced in Dimension 06 (wide) research.

[^114^] Xero scheduled reports with recurring emails. Referenced in Dimension 06 (wide) research.

[^159^] HMRC iXBRL requirements and Companies House digital filing mandate. Referenced in Dimension 06 (wide) research.

[^156^] Burn rate and runway metrics for startups. Referenced in Dimension 06 (wide) research.

[^157^] Burn multiple calculation for SaaS startups. Referenced in Dimension 06 (wide) research.

[^338^] Bank reconciliation best practices. Referenced in Dimension 06 research.

[^339^] Fuzzy date tolerance for matching. Referenced in Dimension 06 research.

[^340^] Timing differences in reconciliation. Referenced in Dimension 06 research.

[^342^] Correcting journal entries for discrepancies. Referenced in Dimension 06 research.

[^344^] Items outstanding >30-60 days investigation. Referenced in Dimension 06 research.

[^580^] Trueman Brown, "Making Tax Digital Software Guide 2025/26," 2025. https://truemanbrown.co.uk/making-tax-digital-software-guide-2025/

[^581^] ATT, "Making Tax Digital for VAT," 2025. https://www.att.org.uk/making-tax-digital-vat

[^582^] Censis, "VAT - Making Tax Digital," 2019. https://www.censis.co.uk/factsheets/vat/vat-making-tax-digital

[^595^] Employment Hero, "RTI Submission Guide: FPS vs EPS in UK Payroll," 2025. https://employmenthero.com/uk/resources/rti-submissions-guide/

[^596^] Shape Payroll, "What are RTI submissions?" https://www.shapepayroll.com/help/rti-submissions/

[^597^] Case Solved, "ERPNext: PAYE Real Time Information Feature." https://www.casesolved.co.uk/erpnext-features/UK-PAYE-RTI

[^587^] PMVA, "Top 12 Best Fixed Asset Accounting Software Tools for 2026," 2026. https://www.pmva.com.au/best-fixed-asset-accounting-software/

[^590^] AccountsIQ, "Finance Consolidation Reporting." https://www.accountsiq.com/features/consolidate

[^589^] DualEntry, "Multi Entity Accounting Software." https://www.dualentry.com/scale/multi-entity-accounting-software

[^139^] Automated report distribution scheduling. Referenced in Dimension 06 (wide) research.

[^106^] Xero P&L "More" menu options. Referenced in Dimension 06 (wide) research.

[^107^] Xero 50+ native reports. Referenced in Dimension 06 (wide) research.

[^109^] Xero API exposed report endpoints. Referenced in Dimension 06 (wide) research.

[^110^] Xero Management Report Pack. Referenced in Dimension 06 (wide) research.

[^158^] UK SaaS board pack structure. Referenced in Dimension 06 (wide) research.

[^587^] PMVA, "Top 12 Best Fixed Asset Accounting Software Tools for 2026." https://www.pmva.com.au/best-fixed-asset-accounting-software/

[^605^] elDoc, "Extract Invoice Data Using LLMs and Export Instantly to CSV or JSON," 2026. https://eldoc.online/blog/extract-invoice-data-using-llms-and-export-to-csv-or-json/

[^606^] LlamaIndex, "Best AI for Invoice Processing." https://www.llamaindex.ai/insights/best-ai-for-invoice-processing

[^61^] Koncile AI, "Claude, GPT or Gemini - Which AI Wins at Invoice Extraction?" https://www.koncile.ai/en/ressources/claude-gpt-or-gemini-which-is-the-best-llm-for-invoice-extraction
