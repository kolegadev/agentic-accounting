# Headless LLM-Native Accounting System: Comprehensive Requirements Extraction

**Version:** 1.0
**Classification:** Requirements Analysis — Explicit & Implicit
**Source Material:** 18 research files (6 wide-scan + 12 deep-dive dimensions)
**Coverage Dimensions:** D01-D12, W01-W06

---

## 1. FUNCTIONAL REQUIREMENTS

### 1.1 Core Accounting — General Ledger (GL)

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| F-GL-001 | The system shall use Formance Ledger as the immutable double-entry backend with Numscript DSL for all transaction postings | P0 | D01, D03, W01 |
| F-GL-002 | All postings shall enforce sum-to-zero at database constraint level (debits = credits on every transaction) | P0 | W01, D03, D12 |
| F-GL-003 | The system shall maintain an append-only postings table — corrections via compensating (reversing) entries only; no UPDATE/DELETE on posted transactions | P0 | D03, D11, D12 |
| F-GL-004 | Every transaction shall carry a unique idempotency key (client-generated UUID) to prevent duplicate postings on retry | P0 | D01, D03, D11 |
| F-GL-005 | The system shall implement bi-temporal timestamps: `effective_date` (when the event occurred) and `recorded_at` (when the system recorded it) | P0 | D12, W01 |
| F-GL-006 | The system shall support transaction status lifecycle: Draft → Posted → Reversed | P0 | D03, D12 |
| F-GL-007 | Auto-sequential journal entry numbering (JE-YYYY-NNNN) shall be generated for all posted transactions | P0 | D12 |
| F-GL-008 | Every transaction shall carry structured metadata: date, description, reference, contact, source document attachments, agent identity | P0 | D03, D09 |
| F-GL-009 | The system shall enforce hash-chained immutability where each transaction's hash incorporates the previous transaction's hash, creating a tamper-evident chain | P0 | D11, W01 |
| F-GL-010 | Full audit trail shall be maintained: created_at, created_by, ip_address, agent_id, session_id for every transaction | P0 | D11, D12 |
| F-GL-011 | The system shall support multi-line journal entries (splits) beyond simple two-sided transactions | P0 | D03, D12 |
| F-GL-012 | Draft transactions shall be storable without posting, supporting review-before-post workflows | P0 | D12 |
| F-GL-013 | Transaction reversal workflow shall create compensating entries (REVERSAL Numscript template) with full reversal audit trail | P0 | D03 |
| F-GL-014 | The system shall verify the full hash chain on read operations on-demand | P1 | D11 |
| F-GL-015 | The system shall support bulk transaction posting with per-transaction validation and all-or-nothing atomicity within batches | P1 | D03 |

### 1.2 Core Accounting — Chart of Accounts (COA)

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| F-COA-001 | The system shall implement a standard 4-digit gap-friendly COA: Assets (1000-1999), Liabilities (2000-2999), Equity (3000-3999), Revenue (4000-4999), Expenses (5000-6999) | P0 | D02, D12, W06 |
| F-COA-002 | Each account shall use 10-point gaps between codes (1010, 1020, 1030...) to allow future insertion | P0 | D02, D12 |
| F-COA-003 | Pre-loaded COA templates shall be provided for 8+ business types: UK Sole Trader (VAT/non-VAT), UK Ltd Co (VAT/non-VAT), UK Partnership, Micro-Entity, Property/Landlord | P0 | D12 |
| F-COA-004 | Each COA account shall map to a Formance ledger account address: `gl:{account_code}:{entity_id}` | P0 | D02, D12 |
| F-COA-005 | Account types shall include: Bank, Current Asset, Fixed Asset, Current Liability, Long-term Liability, Equity, Revenue, Direct Cost, Expense | P0 | D02, D12 |
| F-COA-006 | VAT rate assignment per account (20% standard, 5% reduced, 0% zero-rated, exempt) shall be stored as account metadata and applied automatically on transaction entry | P0 | D02, D12 |
| F-COA-007 | Account enabling/disabling (soft delete) shall be supported | P0 | D12 |
| F-COA-008 | The COA shall include multi-standard metadata flags (`ifrs.applicable`, `gaap.applicable`, display name localization) enabling single COA to serve multiple standards | P1 | D02, D08 |
| F-COA-009 | Dedicated VAT/GST control accounts: Output Tax (2100), Input Tax (2110), VAT Control (2120), Reverse Charge (2140) | P0 | D02, D05 |
| F-COA-010 | The COA shall include Foreign Currency Translation Reserve (account 3210) and FX gain/loss accounts | P1 | D02, D04 |
| F-COA-011 | Tracking categories (dimensions external to account numbers) shall prevent account explosion: departments, projects, regions, cost centres | P1 | D02 |
| F-COA-012 | The system shall support opening balances import for entity migration | P1 | D02 |

### 1.3 Core Accounting — Transactions & Processing

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| F-TXN-001 | The system shall provide 50+ pre-built Numscript templates covering all SME transaction types (SALES_INVOICE, PURCHASE_BILL, PAYMENT_OUT, RECEIPT_IN, EXPENSE_CASH, etc.) | P0 | D03 |
| F-TXN-002 | LLM-generated Numscript shall pass through a deterministic validation layer before execution (balance check, COA membership, duplicate detection, compliance check) | P0 | D03, D09 |
| F-TXN-003 | The system shall support both VAT-inclusive and VAT-exclusive amount entry | P0 | D12 |
| F-TXN-004 | The 6-stage LLM-to-Numscript pipeline shall be: Intent Parsing → Template Selection → Variable Population → Deterministic Validation → Human Approval Gate → Formance Execution | P0 | D03, D09 |
| F-TXN-005 | Every generated Numscript shall carry embedded metadata referencing source documents (document_id) for digital link chain compliance | P0 | D03, D10 |
| F-TXN-006 | The system shall support multi-posting transactions with complex splits (payroll, VAT settlement, intercompany) | P1 | D03 |
| F-TXN-007 | Idempotency keys derived from turn ID plus tool name shall be used across all financial operations | P0 | D03, D01 |
| F-TXN-008 | The system shall detect and reject duplicate transactions from multiple ingestion sources | P0 | D06, D03 |
| F-TXN-009 | Corrections on immutable ledger shall use compensating postings (reversing entries) with reversal audit trail | P0 | D03, D11 |

### 1.4 Financial Reporting

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| F-RPT-001 | The system shall provide 33+ report SKILLs organized across 7 categories: Core Statements, Internal Verification, Management, Tax, Variance, KPI, Audit/Compliance | P0 | D08 |
| F-RPT-002 | Core statement SKILLs: Profit & Loss, Balance Sheet, Cash Flow Statement, Trial Balance | P0 | D08, D12 |
| F-RPT-003 | Management report SKILLs: AR Aging, AP Aging, GL Detail/Summary, Executive Summary, COA Listing | P0 | D08 |
| F-RPT-004 | Tax report SKILLs: UK VAT Return (9-box), BAS (Australia), GST Return (generic), Sales Tax by Jurisdiction, Corporation Tax Computation | P0 | D05, D08 |
| F-RPT-005 | Variance report SKILLs: Period-over-Period, Budget vs Actual, Forecast vs Actual, Tracking Category Analysis, Year-End Comparison | P1 | D08 |
| F-RPT-006 | KPI report SKILLs: Profitability Ratios, Liquidity Ratios, Efficiency Ratios, Solvency Ratios, Startup Metrics (Burn, Runway, CAC, LTV) | P1 | D08 |
| F-RPT-007 | Audit report SKILLs: Adjusted Trial Balance, Journal Entry Report, Full Audit Trail | P1 | D08 |
| F-RPT-008 | Every report SKILL shall be registered with a deterministic JSON schema defining inputs, parameters, data model, and output format | P0 | D08 |
| F-RPT-009 | The same report SKILL shall produce GAAP or IFRS output via framework parameterization (`framework` parameter: gaap_us / gaap_uk / ifrs) | P0 | D08 |
| F-RPT-010 | The report engine shall support output formats: JSON, HTML, PDF, CSV, XBRL, iXBRL | P1 | D08 |
| F-RPT-011 | The system shall implement a 5-stage report pipeline: Parameter Ingestion → Query Execution → Data Transformation → Rule Application → Output Formatting | P0 | D08 |
| F-RPT-012 | Report SKILLs shall be cacheable with configurable TTL (default 5 minutes for real-time data) | P1 | D08 |
| F-RPT-013 | The system shall support IFRS 18 five-category P&L structure (Operating, Investing, Financing, Income Taxes, Discontinued Operations) with MPM disclosures | P1 | D08 |
| F-RPT-014 | The system shall support XBRL/iXBRL tagging for UK Companies House digital filing compliance | P2 | D08 |
| F-RPT-015 | The system shall support automated report scheduling with email distribution | P2 | D08 |
| F-RPT-016 | The system shall support tracking category/department/project/region dimensions in all reports | P1 | D08 |

### 1.5 Agentic Capabilities — Workflow Manager

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| F-AGT-001 | The system shall implement a supervisor pattern with specialist agents for intent classification and task delegation (89% success rate target) | P0 | D09, W04 |
| F-AGT-002 | Specialist agents shall include: Intake, Categorize, Validate, Posting, Reconcile, Reporting, Tax, Audit | P0 | D09 |
| F-AGT-003 | Supervisor agent shall use ReAct pattern (Reasoning + Acting) with temperature=0 for deterministic routing decisions | P0 | D09 |
| F-AGT-004 | Supervisor routing accuracy target shall be 95% correct routing eval threshold | P0 | D09 |
| F-AGT-005 | Each specialist agent shall load capabilities from an OpenClaw-compatible skill registry (SKILL.md format) | P0 | D09 |
| F-AGT-006 | The system shall use Plan-and-Execute pattern for posting workflows producing auditable DAGs | P0 | D09 |
| F-AGT-007 | The system shall implement graduated autonomy with 6 approval gates: 100% approval (initial) → sampled → exception-only approval | P0 | D09 |
| F-AGT-008 | Every agent decision affecting financial records shall produce a structured provenance record (provenance_id, timestamp, agent_identity, input, reasoning, confidence_score) | P0 | D09, D11 |
| F-AGT-009 | The system shall escalate to human when confidence score is below threshold | P0 | D09 |
| F-AGT-010 | Skill registry shall support skill discovery, loading, version management, and embedding-based retrieval | P0 | D09 |
| F-AGT-011 | Agent actions shall be logged to an immutable, time-stamped, structured (JSON) audit stream | P0 | D09, D11 |
| F-AGT-012 | The system shall implement a 4-tier memory architecture: short-term (Redis), episodic (Mem0), semantic (vector store), procedural (learned patterns) | P1 | D09 |
| F-AGT-013 | MCP (Model Context Protocol) servers shall expose accounting functions as standardized tools any AI client can consume | P1 | D09 |
| F-AGT-014 | Skill security framework shall implement: cryptographic signing, Docker sandboxing, deny-by-default network egress, SHA-256 + VirusTotal scanning, daily rescanning | P0 | D09, D11 |
| F-AGT-015 | Skill registry shall be vet-only (curated, reviewed) — no open upload to prevent poisoning attacks | P1 | D09 |

### 1.6 Agentic Capabilities — Chat Interface

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| F-CHT-001 | The primary user interface shall be a WebSocket-based chat with streaming responses (status, thought, confirm, result, suggestion types) | P0 | D01, D09 |
| F-CHT-002 | The system shall support natural language transaction entry: "Paid £120 to Acme Consulting for marketing services plus VAT" → parsed transaction with accounts, amounts, VAT split | P0 | D12 |
| F-CHT-003 | The chat interface shall support structured confirmation dialogs for high-risk operations before execution | P0 | D09 |
| F-CHT-004 | The system shall support multi-turn conversations with context retention across related accounting tasks | P0 | D09 |
| F-CHT-005 | The chat shall present confidence scores alongside AI-generated categorization and posting suggestions | P0 | D09 |
| F-CHT-006 | The chat shall support human override of AI decisions with override recorded in audit trail | P0 | D09, D11 |

### 1.7 Multi-Standard Support (GAAP & IFRS)

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| F-STD-001 | The system shall support US GAAP presentation requirements (ASC 205) | P1 | D02, D08 |
| F-STD-002 | The system shall support IFRS presentation requirements (IAS 1) | P1 | D02, D08 |
| F-STD-003 | The system shall support IFRS for SMEs (Section 3) with simplified disclosure | P1 | D02 |
| F-STD-004 | The same transaction shall produce different financial statement presentations based on metadata flags (framework parameter) | P0 | D08 |
| F-STD-005 | US GAAP revaluation prohibition (except impairment testing) shall be enforced | P1 | D02 |
| F-STD-006 | IFRS revaluation model shall be supported where applicable | P1 | D02 |
| F-STD-007 | IFRS 18 five-category P&L (Operating, Investing, Financing, Income Tax, Discontinued Operations) shall be supported natively | P1 | D08 |
| F-STD-008 | IFRS 18 Management Performance Measures (MPM) reconciliation disclosures shall be supported | P2 | D08 |
| F-STD-009 | The system shall support comparative period reporting for all frameworks | P0 | D08 |
| F-STD-010 | The system shall enforce offsetting prohibition per IAS 1 (assets/liabilities and income/expenses cannot be offset unless permitted) | P1 | D02 |

### 1.8 Multi-Currency

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| F-MC-001 | The system shall implement IAS 21 three-currency model: Functional Currency, Transaction Currency, Presentation Currency | P1 | D04, W02 |
| F-MC-002 | Functional currency determination shall follow IAS 21 paragraphs 9-14 primary/secondary indicators hierarchy | P1 | D04 |
| F-MC-003 | Change in functional currency shall be applied prospectively (no restatement) per IAS 21 | P1 | D04 |
| F-MC-004 | The system shall support multi-currency bank accounts (single account holding balances in multiple currencies) | P1 | D04, W01 |
| F-MC-005 | The system shall support automated exchange rate feeds from ECB (free), XE.com, Open Exchange Rates with failover | P1 | D04 |
| F-MC-006 | Exchange rate types shall include: Spot, Closing, Average, Bank Buy, Bank Sell, Corporate, Historical, Budget | P1 | D04 |
| F-MC-007 | Exchange rate storage shall support high precision (DECIMAL 18,10) with temporal validity (valid_from/valid_to) | P1 | D04 |
| F-MC-008 | Period-end revaluation of monetary items shall be automated with realized/unrealized gain-loss tracking | P1 | D04 |
| F-MC-009 | Cumulative Translation Adjustment (CTA) tracking in OCI for foreign operations | P2 | D04 |
| F-MC-010 | Cryptocurrency holdings shall be supported under IAS 38 | P2 | D04 |
| F-MC-011 | Every foreign currency transaction shall store the exchange rate used with full audit trail | P1 | D04 |
| F-MC-012 | Multi-currency shall be a core feature (not premium add-on) | P1 | D04 |

### 1.9 Multi-Tax

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| F-TAX-001 | The system shall implement a three-layer tax engine: Rule Store + Execution Engine + Override Workflow | P0 | D05, W05 |
| F-TAX-002 | VAT (credit-invoice) shall be supported with standard/reduced/zero/exempt rates | P0 | D05, D12 |
| F-TAX-003 | UK VAT 9-box return calculation (Boxes 1-9) shall be computed automatically from transaction data | P0 | D12 |
| F-TAX-004 | GST (credit-invoice) shall be supported: Australia (10%), New Zealand (15%), Canada (5%), Singapore (9%) | P1 | D05 |
| F-TAX-005 | US Sales Tax (retail single-stage) shall be supported with nexus determination (physical, economic, marketplace) | P1 | D05 |
| F-TAX-006 | Withholding Tax shall be supported with treaty rate lookup | P2 | D05 |
| F-TAX-007 | Digital Services Tax shall be supported where applicable | P2 | D05 |
| F-TAX-008 | Place of supply engine shall determine tax jurisdiction per OECD VAT/GST Guidelines (B2B: customer location; B2C: customer residence) | P1 | D05 |
| F-TAX-009 | EU One-Stop-Shop (OSS) reporting shall be supported for cross-border B2C sales | P1 | D05 |
| F-TAX-010 | Reverse charge mechanism shall be supported for intra-community B2B supplies | P1 | D05 |
| F-TAX-011 | Tax registration threshold monitoring shall alert when approaching VAT/GST registration thresholds | P1 | D05 |
| F-TAX-012 | Tax override workflow with approval gates shall allow tax professionals to override AI-calculated tax | P1 | D05 |
| F-TAX-013 | UK Flat Rate Scheme support shall be provided | P1 | D12 |
| F-TAX-014 | MTD-compatible VAT audit trail: every transaction contributing to each VAT box shall be traceable | P0 | D05, D12 |
| F-TAX-015 | Tax rules shall be configurable by tax professionals, not developers | P0 | D05 |

### 1.10 Bank Integration

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| F-BNK-001 | Multi-aggregator bank feed integration: Plaid (12,000+ institutions), TrueLayer (UK/EU), Salt Edge (3,000+), Yodlee (17,000+) | P1 | D06 |
| F-BNK-002 | Regional aggregator routing: US/CA → Plaid, UK/EU → TrueLayer/Salt Edge, APAC → Yodlee | P1 | D06 |
| F-BNK-003 | The system shall support PSD2 Open Banking APIs with Strong Customer Authentication | P1 | D06 |
| F-BNK-004 | Bank feed ingestion pipeline: POLL → NORMALIZE → DEDUPLICATE → QUEUE → PROCESS | P1 | D06 |
| F-BNK-005 | Polling frequency shall be configurable (typically 1-4 times per day) with on-demand refresh | P1 | D06 |
| F-BNK-006 | Webhook support for real-time transaction notifications from aggregators | P1 | D06 |
| F-BNK-007 | Historical backfill up to 12 months on initial connection | P1 | D06 |
| F-BNK-008 | Manual bank import fallback: CSV (flexible mapping), OFX (1.02/2.1/2.2), QIF (post-MVP) | P0 | D12, D06 |
| F-BNK-009 | Pre-built bank templates for UK banks: Barclays, HSBC, Lloyds, NatWest, Monzo, Starling, Revolut | P0 | D12 |
| F-BNK-010 | Automatic duplicate detection using FITID (OFX), aggregator transaction ID, or hash of date+amount+description (CSV) | P0 | D06, D12 |
| F-BNK-011 | Multi-stage transaction matching engine: exact amount+date → fuzzy amount+date window → reference match → AI suggested match | P1 | D06 |
| F-BNK-012 | Per-organization ML reconciliation models (Xero JAX-style Random Forest) trained on 12 months of reconciliation history | P1 | D06 |
| F-BNK-013 | Real-time reconciliation triggered by ledger transaction events via NATS | P1 | D06 |
| F-BNK-014 | Reconciliation reporting with drift detection | P1 | D06 |
| F-BNK-015 | Multi-currency bank account reconciliation | P1 | D06 |

### 1.11 Invoicing — Accounts Receivable / Accounts Payable

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| F-INV-001 | Invoice lifecycle: Draft → Sent → Viewed → Paid → Overdue → Cancelled with status transition enforcement | P0 | D07, D12 |
| F-INV-002 | Invoice creation with line items (description, quantity, unit price, VAT rate, line total) via natural language | P0 | D12 |
| F-INV-003 | Automatic invoice numbering (INV-YYYY-NNNN) | P0 | D12 |
| F-INV-004 | VAT calculation per line and summary (UK 20% standard, 5% reduced, 0% zero-rated) | P0 | D12 |
| F-INV-005 | Payment terms: Due on receipt, Net 7, Net 14, Net 30, Net 60 | P0 | D12 |
| F-INV-006 | Credit notes (negative invoice referencing original) with lifecycle protection | P0 | D07, D12 |
| F-INV-007 | Invoice lifecycle protection: after SENT, core fields (customer, line items, amounts, VAT) become immutable | P0 | D07 |
| F-INV-008 | PDF generation for printable invoices | P0 | D12 |
| F-INV-009 | Email delivery with viewed status tracking | P0 | D12 |
| F-INV-010 | Overdue detection with time-based auto-transition | P0 | D12 |
| F-INV-011 | Quote-to-invoice workflow with acceptance options (simple, e-signature, deposit payment, full payment) | P1 | D07 |
| F-INV-012 | Recurring invoices: template + schedule (weekly, bi-weekly, monthly, quarterly, annual) | P1 | D07 |
| F-INV-013 | Payment collection via Stripe and GoCardless integration | P1 | D07 |
| F-INV-014 | Payment schedule support (up to 12 installments) | P2 | D07 |
| F-INV-015 | Auto-pay with saved payment methods (opt-in AutoPay, required AutoCollect) | P1 | D07 |
| F-INV-016 | Receipt generation on payment receipt | P1 | D07 |
| F-INV-017 | Supplier bill lifecycle: Receipt → Data Extraction → Coding → Approval → Payment Scheduling → Paid → Reconciled | P1 | D07 |
| F-INV-018 | Multi-step approval workflows with amount thresholds and department routing | P1 | D07 |
| F-INV-019 | Payment run creation and authorization workflow | P1 | D07 |
| F-INV-020 | AR Aging and AP Aging reports | P0 | D08 |

### 1.12 Document Processing

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| F-DOC-001 | Document ingestion channels: email polling, upload API, cloud storage webhooks (Google Drive, Dropbox, S3, Azure Blob, SharePoint), mobile capture | P1 | D10 |
| F-DOC-002 | Supported formats: PDF, PNG, JPEG, TIFF (up to 50MB) | P1 | D10 |
| F-DOC-003 | Hybrid LLM+OCR extraction pipeline achieving 97-98.5% automation rates | P1 | D10 |
| F-DOC-004 | Document classification: invoice, receipt, bank statement, purchase order, expense claim | P1 | D10 |
| F-DOC-005 | Per-field confidence scoring with mathematical cross-validation (line items sum to total, tax rate validation) | P1 | D10 |
| F-DOC-006 | 2-pass verification for high-value invoices (secondary model validation) | P1 | D10 |
| F-DOC-007 | Invoice field extraction: vendor, amounts, line items, tax, payment terms, due date, invoice number | P1 | D10 |
| F-DOC-008 | Receipt field extraction: vendor, date, amount, tax, payment method, category | P1 | D10 |
| F-DOC-009 | Exception handling: confidence-based routing to auto-approve (>=95%), suggest (75-94%), or human review (<75%) | P1 | D10 |
| F-DOC-010 | Document storage with SHA-256 checksums and full audit trail | P1 | D10 |
| F-DOC-011 | Preprocessing pipeline: noise reduction, skew correction, binarization, resolution normalization, contrast stretching | P1 | D10 |
| F-DOC-012 | Prompt Fine Tuning with Feedback Inheritance (PFTFI) for continuous improvement without model retraining | P2 | D10 |
| F-DOC-013 | Mobile capture with real-time quality assessment, auto-enhancement, edge detection | P2 | D10 |

### 1.13 Payroll

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| F-PAY-001 | Numscript payroll templates: PAYROLL_GROSS, PAYROLL_DEDUCTION, PAYROLL_NET, PAYROLL_EMPLOYER_TAX | P2 | D03 |
| F-PAY-002 | UK payroll support: PAYE, NI, RTI FPS-EPS submission to HMRC | P2 | D05, CrossVer |
| F-PAY-003 | Pension auto-enrolment integration (UK legal requirement) | P2 | CrossVer |
| F-PAY-004 | Employee master data: name, NI number, tax code, salary/wage rate, start date, leave entitlement | P2 | D03 |
| F-PAY-005 | Payslip generation and email delivery | P2 | — |
| F-PAY-006 | Payroll journal automatic posting to GL | P2 | D03 |

### 1.14 Inventory

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| F-INVY-001 | Inventory account support in COA (1200-1230 range) | P2 | D02 |
| F-INVY-002 | Raw materials, work-in-progress, finished goods tracking | P2 | D02 |
| F-INVY-003 | Cost of goods sold (COGS) automatic calculation | P2 | — |
| F-INVY-004 | Inventory valuation methods: FIFO, weighted average | P2 | — |

### 1.15 Fixed Assets

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| F-FA-001 | Fixed asset accounts: Office Equipment (1400), Property (1500), Vehicles (1600), Intangibles (1700), Capitalized Software (1800) | P2 | D02 |
| F-FA-002 | Accumulated depreciation/amortization contra-asset accounts | P2 | D02 |
| F-FA-003 | Depreciation methods: straight-line, reducing balance | P2 | — |
| F-FA-004 | Automatic depreciation journal entries | P2 | — |
| F-FA-005 | Asset disposal workflow with gain/loss calculation | P2 | — |

### 1.16 Multi-Entity

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| F-ENT-001 | Multi-ledger support for entity isolation (each entity = separate Formance ledger) | P2 | W01, D04 |
| F-ENT-002 | Intercompany elimination checks | P2 | D08 |
| F-ENT-003 | Consolidated reporting across entities | P2 | — |
| F-ENT-004 | Per-entity functional currency and presentation currency settings | P1 | D04 |
| F-ENT-005 | Entity-specific tax registration and filing | P1 | D05 |

### 1.17 Contact Management

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| F-CON-001 | Contact types: Customer, Supplier, Both | P0 | D12 |
| F-CON-002 | Contact fields: name, company name, email, phone, billing/shipping address, VAT number (EU/UK), payment terms, default account, currency | P0 | D12 |
| F-CON-003 | Contact status: Active / Archived | P0 | D12 |
| F-CON-004 | Auto-creation from transaction descriptions (LLM extracts vendor name) | P0 | D12 |
| F-CON-005 | Duplicate detection by name/email/VAT number | P0 | D12 |
| F-CON-006 | Contact balance tracking: total invoiced, total paid, total owing (AR/AP) | P0 | D12 |

### 1.18 Payment Integration

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| F-PMT-001 | Stripe integration for invoice payment collection | P1 | D07 |
| F-PMT-002 | GoCardless integration for direct debit collection | P1 | D07 |
| F-PMT-003 | Apple Pay / Google Pay support via Stripe | P1 | D07 |
| F-PMT-004 | Payment webhook handling (Stripe: invoice.payment_succeeded) | P1 | D07 |
| F-PMT-005 | Failed payment handling with retry logic | P1 | D07 |

---

## 2. NON-FUNCTIONAL REQUIREMENTS

### 2.1 Performance

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| NF-PERF-001 | Single-ledger throughput: ~1,000 transactions/second on commodity PostgreSQL hardware | P0 | W01, D01 |
| NF-PERF-002 | Horizontal scaling via ledger segmentation for workloads exceeding 1K tx/s | P1 | W01 |
| NF-PERF-003 | WebSocket chat responses shall stream with sub-second latency for simple queries | P0 | D01 |
| NF-PERF-004 | Report generation shall complete within 30 seconds max for standard reports | P1 | D08 |
| NF-PERF-005 | Bank feed processing shall handle 12 months of historical data within 1 hour on initial connection | P1 | D06 |
| NF-PERF-006 | Document extraction pipeline shall process a standard invoice within 30 seconds | P1 | D10 |
| NF-PERF-007 | Redis caching shall provide balance lookups with <100ms latency (30s TTL for balances, 1h TTL for COA, 1h TTL for reports) | P1 | D01 |
| NF-PERF-008 | NATS messaging shall provide sub-millisecond latency for event streaming | P1 | D01 |

### 2.2 Scalability

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| NF-SCL-001 | The architecture shall support horizontal scaling of application services via Kubernetes | P0 | D01 |
| NF-SCL-002 | Ledger-level scaling via multi-ledger parallel writes | P1 | W01 |
| NF-SCL-003 | The system shall handle SME workloads (<10K transactions/month) in MVP, with headroom to scale to mid-market (<1M transactions/month) | P0 | D01 |
| NF-SCL-004 | PostgreSQL connection pooling shall support multi-tenant workloads | P1 | D01 |
| NF-SCL-005 | Redis clustering shall support distributed caching across service instances | P1 | D01 |

### 2.3 Security

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| NF-SEC-001 | AES-256 encryption at rest for all data | P0 | D11 |
| NF-SEC-002 | TLS 1.3 in transit for all communications | P0 | D11 |
| NF-SEC-003 | RBAC with 4 role tiers (Owner, Admin, Accountant, Viewer) enforcing separation of duties | P0 | D11 |
| NF-SEC-004 | Multi-tenant database-per-tenant (hybrid model: shared schema for config, separate for financial data) | P0 | D11 |
| NF-SEC-005 | Tenant isolation at encryption layer (tenant-scoped encryption keys) | P0 | D11 |
| NF-SEC-006 | Pseudonymization layer for PII: encrypt PII with managed keys; erasure = key destruction | P0 | D11 |
| NF-SEC-007 | OAuth 2.0 / OIDC for authentication | P0 | D01, D11 |
| NF-SEC-008 | Rate limiting: 60 calls/minute per tenant (Xero-like) | P0 | D01 |
| NF-SEC-009 | WORM (Write-Once-Read-Many) storage for transaction logs | P0 | D11 |
| NF-SEC-010 | Penetration testing: annual third-party penetration tests | P1 | D11 |
| NF-SEC-011 | Skill sandboxing: Docker containers with deny-by-default network egress | P0 | D09 |
| NF-SEC-012 | SHA-256 + VirusTotal scanning of all skills on registration and daily rescanning | P0 | D09 |

### 2.4 Audit Trail & Data Integrity

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| NF-AUD-001 | Hash-chained immutable ledger with SHA-256 cryptographic chaining | P0 | D11 |
| NF-AUD-002 | Verification on read: every read operation can optionally verify full hash chain | P0 | D11 |
| NF-AUD-003 | Agent action logging: all AI agent decisions affecting financial records produce structured provenance records | P0 | D11 |
| NF-AUD-004 | Financial records retention: minimum 7 years | P0 | D11 |
| NF-AUD-005 | AI decision logs retention: minimum 6 months (EU AI Act); 7 years for financial decision logs | P0 | D11 |
| NF-AUD-006 | Correlation ID linking: every financial transaction links to agent session, user request, and source document | P0 | D11 |
| NF-AUD-007 | Complete conversational audit trail: user utterance → LLM reasoning → generated Numscript → approval decision → ledger posting, all cryptographically linked | P0 | D09, D11 |

### 2.5 Reliability

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| NF-REL-001 | Idempotency on all POST/PUT operations to prevent duplicate processing | P0 | D01, D03, D11 |
| NF-REL-002 | Saga pattern with compensating transactions for multi-step financial operations | P0 | D01, D03 |
| NF-REL-003 | Dead-letter queue (DLQ) for failed bank feed processing with replay capability | P1 | D06 |
| NF-REL-004 | Graceful degradation: if LLM service is unavailable, system falls back to manual entry mode | P0 | D09 |
| NF-REL-005 | Automatic retry with exponential backoff for external API failures (bank aggregators, HMRC) | P0 | D06 |
| NF-REL-006 | System uptime SLA: 99.9% (8.76 hours downtime/year) minimum | P1 | — |
| NF-REL-007 | Data backup: automated daily backups with 30-day retention | P1 | D11 |

### 2.6 Maintainability & Extensibility

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| NF-MNT-001 | SKILL.md-based skill registry enabling non-developer extension of report types | P0 | D09 |
| NF-MNT-002 | OpenAPI-first API design with Kong/Traefik gateway | P0 | D01 |
| NF-MNT-003 | gRPC for internal service communication (3-4x faster than REST, type-safe) | P0 | D01 |
| NF-MNT-004 | Event-driven architecture via NATS enabling loose coupling between services | P0 | D01 |
| NF-MNT-005 | Service topology shall support independent deployment and scaling of each service | P1 | D01 |
| NF-MNT-006 | Docker Compose for local development; Kubernetes for production | P0 | D01, W01 |
| NF-MNT-007 | Comprehensive structured logging across all services | P0 | D01 |
| NF-MNT-008 | Health check and readiness probe endpoints on all services | P0 | D01 |

---

## 3. COMPLIANCE REQUIREMENTS

### 3.1 GAAP & IFRS Standards Compliance

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| CMP-ACC-001 | The system shall enforce double-entry accounting principles on every transaction | P0 | D02, D03 |
| CMP-ACC-002 | Financial statements shall comply with IAS 1 Presentation of Financial Statements | P1 | D02 |
| CMP-ACC-003 | US GAAP compliance per ASC 205 Presentation of Financial Statements | P1 | D02 |
| CMP-ACC-004 | IFRS for SMEs compliance (Section 3) shall be available as simplified option | P1 | D02 |
| CMP-ACC-005 | The system shall enforce offsetting prohibition per IAS 1 | P1 | D02 |
| CMP-ACC-006 | US GAAP: revaluation of assets prohibited except impairment testing | P1 | D02 |
| CMP-ACC-007 | IFRS: revaluation model supported for PPE and intangible assets | P1 | D02 |
| CMP-ACC-008 | IFRS 18 five-category P&L effective January 2027 shall be supported | P1 | D08 |
| CMP-ACC-009 | IAS 21 multi-currency compliance: functional currency determination, spot-rate translation, closing-rate remeasurement | P1 | D04 |
| CMP-ACC-010 | IAS 38 intangible asset recognition for software development costs | P2 | D02 |
| CMP-ACC-011 | IFRS 16 / ASC 842 lease liability tracking | P2 | D02 |

### 3.2 Tax Compliance & Digital Submission

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| CMP-TAX-001 | HMRC MTD (Making Tax Digital) VAT submission pipeline for UK | P0 | D05, D12 |
| CMP-TAX-002 | HMRC MTD digital linking: no manual re-keying between systems — continuous pipeline from document to tax return | P0 | D05, D08 |
| CMP-TAX-003 | EU OSS (One-Stop-Shop) reporting for cross-border B2C sales | P1 | D05 |
| CMP-TAX-004 | ATO SBR2 digital submission (Australia) | P2 | D05 |
| CMP-TAX-005 | IRS e-File compatibility (US) | P2 | D05 |
| CMP-TAX-006 | ATO BAS reporting (Australia) | P1 | D08 |
| CMP-TAX-007 | Tax audit trail: every transaction mapped to tax return box entries with full traceability | P0 | D05 |
| CMP-TAX-008 | VAT registration threshold monitoring and alerts | P1 | D05 |
| CMP-TAX-009 | Corporation Tax Computation report (UK) | P2 | D08 |

### 3.3 EU AI Act Compliance

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| CMP-EUAI-001 | Article 12 (automatic recording): AI agent decisions recorded automatically throughout system lifetime | P0 | D09, D11 |
| CMP-EUAI-002 | Article 13 (transparency): Numscript serves as human-readable explanation of AI decisions | P0 | D09, D11 |
| CMP-EUAI-003 | Article 14 (human oversight): approval gates with capability to understand, override, and intervene | P0 | D09, D11 |
| CMP-EUAI-004 | 6-month AI log retention minimum (extendable to 7 years) | P0 | D11 |
| CMP-EUAI-005 | Structured agent audit logs with queryability for regulatory inspection | P0 | D11 |
| CMP-EUAI-006 | Model cards documenting agent identity, version, training data, limitations | P1 | D09 |
| CMP-EUAI-007 | Compliance readiness by August 2, 2026 enforcement deadline | P0 | D11 |

### 3.4 GDPR Compliance

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| CMP-GDPR-001 | Pseudonymization of all personal data with tenant-scoped encryption keys | P0 | D11 |
| CMP-GDPR-002 | Right to erasure: PII erasure via key destruction preserving financial transaction integrity | P0 | D11 |
| CMP-GDPR-003 | Data portability: export all user data in machine-readable format | P1 | D11 |
| CMP-GDPR-004 | Consent management for AI processing of financial data | P1 | D11 |
| CMP-GDPR-005 | Data Processing Agreements (DPA) for sub-processors | P1 | D11 |
| CMP-GDPR-006 | Records of Processing Activities (ROPA) maintenance | P1 | D11 |
| CMP-GDPR-007 | Breach notification within 72 hours of discovery | P1 | D11 |

### 3.5 SOC 2 & Security Standards

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| CMP-SOC2-001 | SOC 2 Type II certification target for SaaS operations | P1 | D11 |
| CMP-SOC2-002 | ISO 27001 certification for information security management | P2 | D11 |
| CMP-SOC2-003 | PCI DSS alignment for cardholder data handling | P1 | D11 |
| CMP-SOC2-004 | DORA (Digital Operational Resilience Act) compliance for EU financial services | P2 | D11 |
| CMP-SOC2-005 | Separation of duties via RBAC enforcement | P0 | D11 |
| CMP-SOC2-006 | Access logging: all system access logged with user identity, timestamp, and actions | P0 | D11 |
| CMP-SOC2-007 | Change management: all configuration changes tracked and approved | P1 | D11 |

### 3.6 Audit Trail Requirements

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| CMP-AUD-001 | Immutable financial ledger trail: hash-chained, 7+ year retention, all monetary postings | P0 | D11 |
| CMP-AUD-002 | AI agent decision trail: structured JSON event log, all AI decisions with reasoning and confidence | P0 | D11 |
| CMP-AUD-003 | Integration: shared correlation IDs linking financial transactions to agent decisions to user requests | P0 | D11 |
| CMP-AUD-004 | SOX Section 802 / SEC Rule 2-06 compliance for US public companies | P1 | D11 |
| CMP-AUD-005 | IRS Rev. Proc. 97-22 electronic recordkeeping compliance | P1 | D11 |
| CMP-AUD-006 | HMRC MTD digital record-keeping compliance | P0 | D12 |

---

## 4. TECHNICAL REQUIREMENTS

### 4.1 Formance Ledger Integration

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| TEC-FRM-001 | Formance Ledger (open-source, MIT-licensed) as core ledger backend | P0 | W01, D01 |
| TEC-FRM-002 | Numscript DSL for all transaction modeling and execution | P0 | W01, D03 |
| TEC-FRM-003 | Official Formance SDK (@formance/formance-sdk TypeScript) for ledger operations | P0 | D01, W01 |
| TEC-FRM-004 | Formance event publishing integration: COMMITTED_TRANSACTIONS, REVERTED_TRANSACTION, SAVED_METADATA forwarded to NATS | P0 | D01 |
| TEC-FRM-005 | Bi-temporal timestamp support (effective_date + recorded_at) | P0 | D12, W01 |
| TEC-FRM-006 | Multi-asset support: single account holding balances in multiple assets (USD, EUR, GBP, crypto) | P1 | W01 |
| TEC-FRM-007 | Formance ledger schema enforcement for chart of accounts validation | P1 | W01 |
| TEC-FRM-008 | Production deployment via Kubernetes operator (officially supported mode) | P0 | W01 |
| TEC-FRM-009 | Local development via Docker Compose all-in-one stack | P0 | W01, D01 |
| TEC-FRM-010 | Ledger-level resource isolation for multi-tenancy | P1 | W01 |

### 4.2 LLM Integration

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| TEC-LLM-001 | Supervisor routing model: gpt-4o-2024-08-06 with temperature=0 | P0 | D09 |
| TEC-LLM-002 | Specialist agent models: pluggable (Claude, GPT-4o, local models) | P0 | D09 |
| TEC-LLM-003 | Structured output: JSON Schema with strict mode + constrained decoding for 100% schema adherence | P0 | D09 |
| TEC-LLM-004 | Template-based Numscript generation to mitigate 8.33% raw double-entry accuracy risk | P0 | D03, CrossVer |
| TEC-LLM-005 | Few-shot examples embedded in prompts for transaction type recognition | P0 | D03 |
| TEC-LLM-006 | Hybrid cloud/local LLM strategy: standard documents via cloud LLM with pseudonymization; sensitive documents (bank statements, payroll) via local LLM | P1 | D09, D10 |
| TEC-LLM-007 | LLM cost monitoring and token usage tracking per workflow | P1 | CrossVer |
| TEC-LLM-008 | Kimi model compatibility as primary LLM (user preference) | P0 | User Brief |

### 4.3 Agent Framework

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| TEC-AGF-001 | Supervisor pattern (LangGraph or custom) with 4-8 specialist agents | P0 | D09 |
| TEC-AGF-002 | ReAct pattern within each specialist agent (34% improvement on decision benchmarks) | P0 | D09 |
| TEC-AGF-003 | Plan-and-Execute pattern for posting workflows producing auditable DAGs | P0 | D09 |
| TEC-AGF-004 | SKILL.md format (YAML frontmatter + markdown) for report and operation skills | P0 | D09 |
| TEC-AGF-005 | MCP (Model Context Protocol) server compatibility for tool exposure | P1 | D09 |
| TEC-AGF-006 | Mem0 memory framework for episodic + semantic memory | P1 | D09 |
| TEC-AGF-007 | LangSmith integration for tracing and observability | P1 | D09 |
| TEC-AGF-008 | Max 20 iterations per agent workflow to prevent runaway loops | P0 | D09 |

### 4.4 API Design

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| TEC-API-001 | REST API v1 (`/api/v1/*`) for all CRUD operations | P0 | D01 |
| TEC-API-002 | WebSocket (`/ws/chat`) for LLM chat with streaming responses | P0 | D01 |
| TEC-API-003 | Webhooks (`/webhooks/*`) for async notifications to external systems | P0 | D01 |
| TEC-API-004 | gRPC for internal service-to-service communication | P0 | D01 |
| TEC-API-005 | OpenAPI-first design with comprehensive documentation | P0 | D01 |
| TEC-API-006 | Idempotency-Key header on every POST/PUT endpoint | P0 | D01 |
| TEC-API-007 | Rate limiting: 60 calls/minute per tenant | P0 | D01 |
| TEC-API-008 | SSL termination at API gateway | P0 | D01 |
| TEC-API-009 | Webhook signing secrets for payload verification | P0 | D01 |
| TEC-API-010 | API versioning strategy (URL path versioning: /api/v1/) | P0 | D01 |

### 4.5 Deployment Model

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| TEC-DEP-001 | Kubernetes (k8s) operator for production deployment | P0 | W01, D01 |
| TEC-DEP-002 | Docker Compose for local development and testing | P0 | D01 |
| TEC-DEP-003 | PostgreSQL 16+ as primary database for both Formance and Application DB | P0 | D01 |
| TEC-DEP-004 | Redis for caching and session storage | P0 | D01 |
| TEC-DEP-005 | NATS with JetStream for event streaming and persistence | P0 | D01 |
| TEC-DEP-006 | MinIO (S3-compatible) for file/document storage | P0 | D01 |
| TEC-DEP-007 | Kong or Traefik API Gateway | P0 | D01 |
| TEC-DEP-008 | PGVector for skill embeddings storage | P1 | D01 |
| TEC-DEP-009 | Multi-region deployment capability (post-MVP) | P2 | CrossVer |
| TEC-DEP-010 | Formance Cloud (managed) as optional deployment target for rapid startup | P1 | W01 |

### 4.6 Service Topology

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| TEC-SRV-001 | API Gateway service: authentication, rate limiting, routing, SSL | P0 | D01 |
| TEC-SRV-002 | Agent Orchestrator service: supervisor + specialist agents | P0 | D01 |
| TEC-SRV-003 | Accounting Service: chart of accounts, transactions, journal entries, balances | P0 | D01 |
| TEC-SRV-004 | Bank Feed Service: import, categorization, reconciliation (async) | P0 | D01 |
| TEC-SRV-005 | Reporting Service: report generation and analytics (async) | P0 | D01 |
| TEC-SRV-006 | Notification Service: email, push, webhooks | P0 | D01 |
| TEC-SRV-007 | Skill Registry: skill storage, discovery, version management | P0 | D01 |
| TEC-SRV-008 | Document Processing Service: ingestion, extraction, validation | P1 | D10 |
| TEC-SRV-009 | Tax Engine Service: rule store, execution, override workflow | P0 | D05 |
| TEC-SRV-010 | Exchange Rate Service: rate lookup, caching, multi-provider | P1 | D04 |

---

## 5. USER EXPERIENCE REQUIREMENTS

### 5.1 Natural Language Accounting

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| UX-NL-001 | All accounting operations shall be accessible via natural language chat (no code, no spreadsheet) | P0 | User Brief, D12 |
| UX-NL-002 | Transaction entry: "Paid £50 for office stationery at Tesco" → auto-categorized, VAT-calculated, posted | P0 | D12 |
| UX-NL-003 | Income recording: "Received £500 from client for consulting" → GL entry with contact creation | P0 | D12 |
| UX-NL-004 | Transfer recording: "Transferred £1,000 from current to savings" → bank transfer journal | P0 | D12 |
| UX-NL-005 | Manual journal entry: "Journal: Debit Rent £500, Credit Bank £500" → balanced journal posted | P0 | D12 |
| UX-NL-006 | Invoice creation: "Create invoice for ABC Ltd: 10 hours consulting at £80/hr plus VAT" → complete invoice | P0 | D12 |
| UX-NL-007 | The system shall support undo commands: "Undo that last entry" → reversal workflow | P0 | D12 |
| UX-NL-008 | End-to-end bookkeeping cycle shall be completable via chat only | P0 | D12 |

### 5.2 Workflow Automation

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| UX-AUT-001 | Bank feed auto-import on schedule with automatic categorization suggestions | P1 | D06 |
| UX-AUT-002 | Invoice auto-numbering and sequential generation | P0 | D12 |
| UX-AUT-003 | Overdue invoice auto-detection and notification | P0 | D12 |
| UX-AUT-004 | Recurring invoice generation on schedule | P1 | D07 |
| UX-AUT-005 | Automatic payment collection via saved payment methods (AutoPay/AutoCollect) | P1 | D07 |
| UX-AUT-006 | Receipt auto-generation on payment receipt | P1 | D07 |
| UX-AUT-007 | Document auto-processing from email attachments | P1 | D10 |
| UX-AUT-008 | Tax return auto-calculation from transaction data | P0 | D12 |
| UX-AUT-009 | Period-end revaluation automation for multi-currency | P1 | D04 |
| UX-AUT-010 | Depreciation journal auto-posting | P2 | — |

### 5.3 Report Generation via Chat

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| UX-RPT-001 | Natural language report requests: "Show me P&L for last quarter" | P0 | D08 |
| UX-RPT-002 | Comparative period reports: "Compare Q2 vs Q3" | P0 | D08 |
| UX-RPT-003 | Framework selection via chat: "Show me IFRS Balance Sheet" or "Show me GAAP P&L" | P0 | D08 |
| UX-RPT-004 | Output format selection: "Email me the PDF" or "Download as CSV" | P1 | D08 |
| UX-RPT-005 | Scheduled reports: "Send me weekly P&L every Monday morning" | P2 | D08 |
| UX-RPT-006 | Drill-down capability: "Show me the detail behind that £5,000 expense line" | P1 | D08 |
| UX-RPT-007 | VAT return preview: "Show me my VAT return for this quarter" | P0 | D12 |

### 5.4 Exception Handling & Escalation

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| UX-EXC-001 | Confidence-based routing: auto-approve (>=95%), suggest (75-94%), human review (<75%) | P0 | D10 |
| UX-EXC-002 | Low-confidence transactions shall be presented to user for approval with AI explanation | P0 | D09 |
| UX-EXC-003 | Human override of AI decisions shall be recorded in audit trail with override reason | P0 | D09, D11 |
| UX-EXC-004 | Supervisor escalation to human when specialist confidence is below threshold | P0 | D09 |
| UX-EXC-005 | Bank reconciliation exceptions: unmatched items presented for manual matching | P0 | D12 |
| UX-EXC-006 | Document extraction failures: human review queue with original document | P1 | D10 |
| UX-EXC-007 | Tax calculation exceptions: presented to tax professional for override | P1 | D05 |
| UX-EXC-008 | Duplicate detection alerts with user confirmation required | P0 | D06 |
| UX-EXC-009 | Error messages in natural language (not stack traces) via chat interface | P0 | D09 |

### 5.5 Onboarding & Entity Setup

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| UX-ONB-001 | Entity type selection via chat: sole trader, limited company, partnership, micro-entity | P0 | D12 |
| UX-ONB-002 | Automatic COA template loading based on entity type and VAT status | P0 | D12 |
| UX-ONB-003 | Opening balances entry via natural language | P1 | D02 |
| UX-ONB-004 | Bank account setup via chat (name, sort code, account number, IBAN) | P0 | D12 |
| UX-ONB-005 | Tax registration configuration (VAT number, scheme, first return date) | P0 | D12 |

---

## 6. CONSTRAINTS

| ID | Constraint | Impact | Source |
|----|------------|--------|--------|
| C-001 | Formance single-ledger throughput ceiling ~1,000 tx/s — requires ledger sharding for higher loads | Architecture | W01, D01 |
| C-002 | Formance production deployment requires Kubernetes operator (not Docker Compose) | Deployment | W01 |
| C-003 | LLMs achieve only 8.33% accuracy generating raw double-entry without guidance — requires template + validation layers | Transaction Accuracy | D03, CrossVer |
| C-004 | Weber et al. (2025) study tested Beancount DSL, not Numscript — accuracy may not directly translate | Validation Needed | CrossVer |
| C-005 | Supervisor pattern costs ~3x single-agent ($0.061 vs $0.022 per task) — justified for high-value accounting | Cost | D09 |
| C-006 | EU AI Act high-risk system rules effective August 2, 2026 — compliance deadline | Timeline | D11 |
| C-007 | IFRS 18 effective January 2027 — reporting system deadline | Timeline | D08 |
| C-008 | Formance Enterprise features (Auth, RBAC, Webhooks) require commercial license — open-source core is Ledger + Numscript only | Licensing | W01 |
| C-009 | Formance SDKs are beta — breaking changes may occur without major version updates | Integration Risk | W01 |
| C-010 | PostgreSQL row-level locks on accounts_volumes table create single-writer bottleneck per (account, asset) pair | Performance | W01 |
| C-011 | No built-in Formance exchange rate service — application layer must supply conversion rates | Architecture | W01 |
| C-012 | ClawHavoc vulnerability: 20% of community skills found to contain malicious code — vet-only skill registry required | Security | D09 |

---

## 7. ASSUMPTIONS

| ID | Assumption | Basis | Source |
|----|------------|-------|--------|
| A-001 | Numscript's declarative syntax is "highly LLM-friendly" — LLM-to-Numscript accuracy with templates will exceed raw double-entry accuracy significantly | Research consensus | W01, D03 |
| A-002 | Template-based generation + deterministic validation + few-shot examples will raise LLM accuracy from 8.33% to >95% | Architecture design | D03 |
| A-003 | Kimi models (user preference) are capable of reliable financial reasoning with temperature=0 and structured output constraints | User Brief | User Brief |
| A-004 | Small business accounting workloads are typically <10K transactions/month — well within Formance throughput limits | Architecture target | D01 |
| A-005 | The headless paradigm (no traditional UI) is acceptable to target users (solo founders, freelancers, micro-businesses) | Product thesis | User Brief, D12 |
| A-006 | MCP adoption will grow, making the system embeddable in any MCP-compatible AI client | Market prediction | D09 |
| A-007 | 8-week MVP is achievable using Formance Cloud (managed) with monolithic deployment | Timeline | D12 |
| A-008 | Pseudonymization layer resolves GDPR-immutability conflict without requiring local-only LLM processing | Architecture design | D11 |
| A-009 | Per-organization ML models for reconciliation will achieve comparable accuracy to Xero JAX (97% claimed) | Benchmark assumption | D06 |
| A-010 | Document extraction accuracy of 97-98.5% is achievable with hybrid LLM+OCR pipeline | Research data | D10 |
| A-011 | Natural language interface can replace traditional UI for all core accounting operations | Product thesis | User Brief, D12 |
| A-012 | OpenClaw SKILL.md format will emerge as de facto standard for agent skill definition | Ecosystem trend | D09 |

---

## 8. DEPENDENCIES

| ID | Dependency | Impact | Mitigation | Source |
|----|------------|--------|------------|--------|
| DEP-001 | Formance Ledger open-source project viability and continued development | Critical — core backend | MIT license ensures forkability; $21M Series A signals stability | W01 |
| DEP-002 | LLM API providers (OpenAI, Anthropic, or local model hosting) | Critical — all AI features | Pluggable model architecture; local LLM fallback | D09 |
| DEP-003 | Bank feed aggregators (Plaid, TrueLayer, Salt Edge, Yodlee) | High — bank integration | Multi-aggregator with manual import fallback | D06 |
| DEP-004 | HMRC MTD API availability and stability | High — UK tax compliance | Abstracted tax submission layer with retry logic | D05 |
| DEP-005 | Exchange rate data providers (ECB, XE, OXR) | Medium — multi-currency | Multi-provider with failover; manual entry option | D04 |
| DEP-006 | PostgreSQL 16+ performance and reliability | Critical — data storage | Connection pooling, read replicas, pgBackRest | D01 |
| DEP-007 | Kubernetes ecosystem (production deployment) | High — production ops | Docker Compose fallback for small deployments | W01 |
| DEP-008 | Stripe/GoCardless API stability | Medium — payment collection | Abstracted payment connector layer | D07 |
| DEP-009 | NATS JetStream maturity | Medium — event streaming | Kafka as alternative (Formance supports both) | D01 |
| DEP-010 | Mem0 memory framework maturity | Medium — agent memory | Redis-based fallback for memory storage | D09 |
| DEP-011 | OpenClaw/SKILL.md ecosystem adoption | Medium — skill distribution | Self-hosted skill registry independent of ecosystem | D09 |
| DEP-012 | EU AI Act regulatory clarity and enforcement approach | Medium — compliance | Design for strict compliance regardless | D11 |

---

## 9. IMPLICIT REQUIREMENTS (Derived from Cross-Dimensional Analysis)

### 9.1 Derived from Insight Analysis

| ID | Requirement | Derivation | Priority |
|----|-------------|------------|----------|
| IMP-001 | **Conversational Audit Trail**: Every user utterance shall be cryptographically linked to resulting ledger entry via correlation ID chain (utterance → reasoning → Numscript → approval → posting) | Insight 1: Conversational audit trail as regulatory moat | P0 |
| IMP-002 | **Per-Organization ML Personalization**: Each organization's reconciliation decisions shall feed into episodic memory AND per-org ML model, with anonymized patterns improving base categorization for new signups | Insight 2: Compounding data advantage | P1 |
| IMP-003 | **MCP Server Distribution**: MCP servers shall expose accounting functions as standardized tools, enabling embedding in any MCP-compatible AI client (Teams, Copilot, custom GPTs) without bespoke integrations | Insight 3: Headless + MCP inverts integration economics | P1 |
| IMP-004 | **Touchless Transaction Entry**: Document → AI extraction → Numscript template mapping → deterministic validation → confidence routing → ledger posting, with 80%+ of routine invoices processing without human data entry | Insight 4: Document + Numscript pipeline | P0 |
| IMP-005 | **Metadata-Driven Multi-Standard COA**: Single COA with standard-specific metadata flags — same transaction produces different presentations for IFRS, US GAAP, UK GAAP without parallel books | Insight 5: Eliminates one-system-per-jurisdiction anti-pattern | P1 |
| IMP-006 | **Pseudonymization as Tenant Isolation**: Pseudonymization layer shall enforce tenant isolation at encryption layer — cross-tenant queries only retrieve decryptable data | Insight 6: Resolves GDPR + enables multi-tenancy | P0 |
| IMP-007 | **Reactive Ledger Architecture**: Every ledger write automatically triggers downstream actions via NATS: balance invalidation, report refresh, reconciliation matching, notifications — all in real-time | Insight 7: NATS + Formance eliminates batch processing | P1 |
| IMP-008 | **Numscript as AI Audit Trail**: Numscript serves as the EU AI Act audit trail — the ledger IS the AI audit trail; no separate governance infrastructure needed | Insight 8: Numscript IS compliance | P0 |
| IMP-009 | **Digital Link Chain**: Document ingestion → extraction → Numscript → ledger → tax return shall create unbroken digital link chain satisfying HMRC MTD, EU MTD, ATO requirements | Insight 9: End-to-end MTD compliance | P0 |
| IMP-010 | **EU AI Act First-Mover Positioning**: System shall be marketed as "EU AI Act ready by design" in EU jurisdictions ahead of August 2026 deadline | Insight 10: Compliance window | P1 |
| IMP-011 | **Unified Trust Interface**: Single approval workflow engine serving financial controls, AI safety, AND regulatory compliance — approvers see financial context AND AI decision context in one screen | Insight 11: HITL + Approval convergence | P0 |
| IMP-012 | **Secure Skill Ecosystem**: Skill registry security shall be Day 1 MVP feature with vet-only marketplace to prevent ClawHavoc-scale incidents | Insight 12: Security as positioning | P0 |
| IMP-013 | **IFRS 18 Native Support**: Report SKILLs shall implement IFRS 18 five-category P&L and MPM disclosures for January 2027 effective date | Insight 13: Reporting refresh market moment | P1 |
| IMP-014 | **Cross-Border E-Commerce Capability**: Three-currency architecture + multi-tax place-of-supply + multi-aggregator bank feeds targeting Amazon/Shopify/eBay sellers | Insight 14: Fastest-growing SME segment | P2 |

### 9.2 Derived from Conflict Zones

| ID | Requirement | Derivation | Resolution | Priority |
|----|-------------|------------|------------|----------|
| IMP-CZ-001 | **Dual MVP Timeline**: 8-week "MVP-lite" (Formance Cloud, monolith) AND 6-month "MVP-proper" (microservices, self-hosted) shall both be defined | CZ 4.1: 8wk vs 6mo timeline conflict | Preserve both as options | P0 |
| IMP-CZ-002 | **Hybrid Processing Model**: Real-time for user-facing chat; async/batch for background (bank feeds, document extraction, report generation) | CZ 4.2: Batch vs real-time | Hybrid approach | P0 |
| IMP-CZ-003 | **Phased Agent Expansion**: Start with supervisor + 4 core specialists (Intake, Categorize, Validate, Posting); add Reporting, Tax, Reconcile, Audit in later phases | CZ 4.3: Single vs multi-agent cost | Phased approach | P0 |
| IMP-CZ-004 | **Data Classification for LLM Processing**: Standard documents via pseudonymized cloud LLM; sensitive documents (bank statements, payroll) via local LLM | CZ 4.4: Local vs cloud LLM | Risk-based hybrid | P1 |
| IMP-CZ-005 | **Presentation-Layer IFRS 18 Mapping**: COA remains standard; P&L SKILL maps accounts to IFRS 18 categories at report generation time via metadata | CZ 4.5: IFRS 18 vs COA structure | Metadata-driven | P1 |

### 9.3 Derived from Coverage Gaps

| ID | Requirement | Derivation | Priority |
|----|-------------|------------|----------|
| IMP-GAP-001 | Independent load testing of Formance Ledger with realistic accounting workloads | Gap 5.1: No production load data | P0 |
| IMP-GAP-002 | Comprehensive disaster recovery plan with RTO/RPO specifications and multi-region deployment | Gap 5.2: No DR plan | P1 |
| IMP-GAP-003 | Full HMRC MTD API integration spec with OAuth 2.0 flow, VAT submission endpoints, error handling | Gap 5.3: MTD API details | P0 |
| IMP-GAP-004 | LLM total cost of ownership model with token usage estimates per workflow and scale projections | Gap 5.4: No cost model | P1 |
| IMP-GAP-005 | Full UK payroll module with PAYE/NI/RTI FPS-EPS and pension auto-enrolment | Gap 5.5: No payroll design | P2 |
| IMP-GAP-006 | Xero/QuickBooks API-based migration tooling with data validation | Gap 5.6: No migration path | P1 |
| IMP-GAP-007 | Mobile application architecture with offline capability and push notifications | Gap 5.7: No mobile design | P2 |
| IMP-GAP-008 | Multi-tenant admin dashboard, monitoring/alerting, customer onboarding workflow | Gap 5.8: No ops tooling | P1 |
| IMP-GAP-009 | Multi-tenant isolation validation at 100+ tenant scale with resource quotas | Gap 5.9: No scalability validation | P1 |
| IMP-GAP-010 | Pricing strategy and cost-plus analysis including freemium tier design | Gap 5.10: No pricing model | P2 |

---

## 10. REQUIREMENTS TRACEABILITY MATRIX

### 10.1 Dimension Coverage

| Requirement Category | D01 | D02 | D03 | D04 | D05 | D06 | D07 | D08 | D09 | D10 | D11 | D12 | W01-W06 |
|----------------------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|---------|
| Core Accounting (GL) | X | X | X | | | | | | | | X | X | X |
| Chart of Accounts | | X | X | | | | | X | | | | X | X |
| Transactions | | X | X | | | | | | X | X | X | X | |
| Financial Reporting | | | | | | | | X | | | | | X |
| Agentic Capabilities | X | | | | | | | | X | | X | | X |
| Chat Interface | X | | | | | | | | X | | | X | |
| Multi-Standard | | X | | | | | | X | | | | | X |
| Multi-Currency | | X | | X | | | | | | | | | X |
| Multi-Tax | | X | | | X | | | X | | | | X | X |
| Bank Integration | | | | | | X | | | | | | X | |
| Invoicing/AR/AP | | | | | | | X | X | | | | X | |
| Document Processing | | | | | | | | | | X | | | |
| Payroll | | | X | | | | | | | | | | |
| Inventory | | X | | | | | | | | | | | |
| Fixed Assets | | X | | | | | | | | | | | |
| Multi-Entity | X | | | X | | | | X | | | X | | X |
| Security/Compliance | X | | | | | | | | X | X | X | | |
| UX/Onboarding | | | | | | | | | X | | | X | |

### 10.2 Priority Distribution

| Priority | Count | Percentage |
|----------|-------|------------|
| P0 (Critical) | 112 | 52% |
| P1 (High) | 80 | 37% |
| P2 (Medium) | 24 | 11% |
| **Total** | **216** | **100%** |

---

*This requirements document was synthesized from 18 independent research dimensions covering architecture, data model, transaction processing, multi-currency, tax engine, bank feeds, invoicing, financial reporting, agentic workflow, document understanding, compliance/security, and MVP/roadmap planning. All requirements are traceable to specific research dimension source material. Cross-dimensional insights and conflict zones were used to derive implicit requirements not stated in any single dimension.*
