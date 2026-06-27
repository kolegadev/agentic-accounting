# Facet: Xero Benchmark & SME Accounting Feature Taxonomy

## Key Findings

- **Xero has six distinct REST APIs** covering Accounting, Assets, Projects, Payroll (region-specific AU/NZ/UK), Files, and BankFeeds — all using OAuth 2.0 authentication with access tokens expiring in 30 minutes and refresh tokens in 60 days [^96^][^134^].
- **Xero's bank feed infrastructure connects to 21,000+ financial institutions globally** via a mix of direct bank partnerships (180+ institutions including Wells Fargo, Barclays, NAB, DBS) and aggregator connections through Open Banking frameworks (PSD2 in EU/UK, CDR in Australia) [^145^][^146^].
- **Xero's native multi-entity support is a significant gap** — each legal entity requires its own separate Xero organisation with separate subscriptions. There is no native consolidation, intercompany elimination, or consolidated reporting. This is handled entirely through third-party apps like Translucent, Joiin, dataSights, and Mayday [^136^][^148^].
- **Xero's inventory management has a practical limit of ~4,000 tracked items** using weighted average costing only — no FIFO, LIFO, or specific identification. No multi-warehouse, barcode scanning, batch/serial tracking, or BOM support natively [^42^][^44^][^48^].
- **Xero's API rate limits are 60 calls/minute per tenant, 5,000/day** (1,000 for starter tier), with 5 concurrent requests maximum [^96^][^134^].
- **JAX (Just Ask Xero)**, launched in beta 2024 and rebuilt as an "AI financial superagent" in September 2025, provides conversational invoice creation, bank reconciliation with 97% claimed accuracy on suggested matches, natural language queries, and cash flow predictions — but builds per-organisation models requiring clean historical data to work well [^142^][^149^].
- **Xero's UK payroll** handles PAYE, NI, auto-enrolment pensions (NEST, Smart, People's Pension, Aviva, Standard Life), RTI FPS/EPS submissions, P60s/P45s/P11Ds, and leave management — included in Grow plans at GBP 1.50/person/month additional [^87^][^90^].
- **Xero's purchase order workflow** is single-step only (Draft → Awaiting Approval → Approved → Billed) with no native multi-step routing, conditional rules, or delegation — third-party apps like ApprovalMax (GBP 32.50/month) fill this gap [^23^][^25^].
- **QuickBooks Online dominates the US market with 7M+ subscribers** vs Xero's 3.9M global subscribers. QBO has built-in US payroll, deeper CPA firm tools, but user limits per plan. Xero offers unlimited users on all plans, 160+ currencies, and stronger international compliance [^88^][^89^].
- **Xero's reporting suite includes 50+ pre-built report templates** across 6 categories (Financial Performance, Financial Statements, Payables/Receivables, Reconciliations, Taxes/Balances, Transactions) plus a Blank Report custom builder, but lacks automated KPI calculations, dynamic visualisations, or multi-entity consolidated views [^107^][^110^].

---

## Complete Feature Taxonomy (organized by category)

### 1. Core Accounting & General Ledger
- Chart of accounts with multi-level structure
- Double-entry bookkeeping (automated journal entries)
- Bank reconciliation (manual and automated matching)
- Bank rules engine (auto-categorisation based on payee, reference, amount)
- Cash coding (bulk reconciliation in spreadsheet-style interface)
- VAT/GST/Sales tax calculation and reporting
- Manual journal entries (standard and reversing)
- Audit trail (History & Notes report showing all changes by user)
- Multi-currency support (160+ currencies) [^139^]
- Hourly FX rate updates from XE.com [^136^]
- Foreign exchange gain/loss tracking and revaluation [^133^]
- Tracking categories (2 categories, unlimited values for segment reporting) [^94^]
- Budget manager (3/6/12/24 month budgets with budget vs actual reports)

### 2. Banking & Bank Feeds
- **21,000+ financial institution connections** [^145^]
- Direct bank feeds via Open Banking APIs (PSD2 in EU/UK, CDR in Australia) [^137^][^147^]
- 180+ direct bank partnerships globally [^146^]
- Aggregator feeds (Yodlee legacy, OpenWrks for UK Open Banking) [^150^]
- Historical transaction import (90 days to 2 years depending on bank) [^137^]
- Manual bank statement import (OFX, QIF, QBO, QFX, CSV formats) [^145^]
- Unlimited bank account connections [^145^]
- Bank feed API for financial institutions (OAuth-secured, closed API) [^139^]
- Stripe, Wise, PayPal direct feeds [^145^]

### 3. Invoicing & Accounts Receivable
- Customisable invoice templates with branding [^24^]
- Quote → Invoice workflow (convert accepted quotes to invoices in one click) [^99^]
- Recurring invoices and repeating invoice templates
- Automatic payment reminders (configurable by due date) [^27^]
- Bulk invoicing
- Credit notes and overpayments
- Online payment acceptance via Stripe (credit/debit cards, Apple Pay, Google Pay, buy now pay later) [^30^][^32^]
- GoCardless direct debit integration
- PayPal, Square payment options
- Auto-pay for recurring billing (customer authorises card, subsequent invoices charged automatically) [^27^]
- Invoice status tracking (Draft, Awaiting Approval, Awaiting Payment, Paid)
- Contact management with default currency assignment [^139^]
- Customer statements
- Sales tax/VAT auto-calculation per jurisdiction

### 4. Bills & Accounts Payable
- Supplier bill creation and management
- Bill approval workflow (Draft → Awaiting Approval → Awaiting Payment) [^25^]
- Payment scheduling and payment runs
- Payment file export for bulk bank upload
- Aged payables report
- Recurring bills
- Purchase orders (Draft → Awaiting Approval → Approved → Billed) [^23^]
- Copy PO to Bill conversion (single or batch up to 25 POs) [^23^]
- Partial PO conversion for split deliveries [^24^]
- Purchase order templates with branding
- File attachments to bills and POs [^23^]
- **Note: Native approval is single-step only; multi-step/conditional routing requires third-party apps** [^25^]

### 5. Expense Management
- Xero Expenses module (included in higher-tier plans) [^43^]
- Receipt capture via Xero Me mobile app [^41^][^46^]
- Hubdoc data capture tool (included free with all plans) for receipt/bill extraction [^41^]
- OCR data extraction (supplier name, date, amount, VAT) [^41^]
- Expense claims workflow (submit → approve → reimburse) [^46^]
- Mileage tracking with GPS-based distance calculation [^43^][^46^]
- HMRC-approved mileage rates (45p/mile first 10,000 miles, 25p after) [^41^]
- Project-based expense allocation
- Reimbursement via next pay run or batch payment
- Expense policy enforcement [^46^]

### 6. Inventory Management
- Tracked vs untracked items [^42^]
- Weighted average cost valuation (only method supported) [^42^]
- Automatic stock level updates on purchases and sales
- Automatic COGS posting on sales [^42^]
- Manual inventory adjustments (quantity and value) [^40^]
- Item Summary report for stocktake verification [^42^]
- CSV bulk import/export of inventory items
- Purchase order-driven stock receipt updates [^24^]
- **Limitations: ~4,000 tracked items max, single location, no barcode, no FIFO/LIFO, no serial/batch tracking, no BOM** [^44^][^48^]

### 7. Fixed Assets
- Fixed asset register with import/export [^137^]
- Multiple depreciation methods per asset type [^137^]
- Automatic depreciation calculations and schedules [^137^]
- Depreciation Schedule report [^138^]
- Disposal Schedule report for sold/written-off assets [^138^]
- Fixed Asset Reconciliation report (balance sheet vs register) [^138^]
- Asset creation from bills (auto-convert purchase to asset)
- Disposal processing with gain/loss calculation
- Bulk asset import via CSV [^138^]

### 8. Payroll (UK-Specific)
- HMRC-recognised for PAYE and RTI [^87^]
- Automatic PAYE, NI, and student loan calculations [^93^]
- RTI Full Payment Submission (FPS) and Employer Payment Summary (EPS) [^87^]
- Auto-enrolment pension support (NEST, Smart, People's Pension, Aviva, Standard Life, etc.) [^87^]
- Contribution file generation and API push to providers
- Postponement period tracking and 3-year re-enrolment cycles [^87^]
- Payslip generation and digital distribution via Xero Me [^90^]
- P60, P45, P11D generation [^87^]
- Leave management (holiday, sick, maternity/paternity, TOIL) [^87^]
- Timesheet submission and approval via Xero Me
- Public holiday calendar (UK bank holidays with Scotland/NI variants) [^87^]
- Flexible pay frequencies (weekly, fortnightly, monthly, 4-weekly) [^91^]
- **UK Pricing: included in Grow+ plans; GBP 1.50 per additional person/month** [^86^]
- **Note: US payroll via Gusto integration, AU/NZ have native payroll** [^89^]

### 9. Project Tracking & Job Costing
- Xero Projects module (time tracking, expense allocation, invoicing) [^94^][^98^]
- Time tracking via manual timer and mobile app
- Location-based auto-tracking (mobile app detects job site entry) [^97^]
- Budget tracking with estimated vs actual cost comparison [^94^]
- Project profitability dashboard [^94^]
- Invoice generation from tracked time and expenses
- Quote → Invoice workflow within projects [^97^]
- Task assignment and team management
- Xero Expenses integration for project-linked expense claims [^97^]
- Tracking categories as alternative job costing method (2 categories, unlimited values) [^94^][^102^]
- **Limitations: No procurement workflows, no construction cost codes, weak reporting for construction** [^97^]

### 10. Reporting Suite
- **50+ pre-built report templates** across 6 categories [^107^]:
  - Financial Statements: Balance Sheet, Income Statement (P&L), Blank Report (custom builder)
  - Financial Performance: Budget Variance, Cash Summary, Business Performance
  - Payables/Receivables: Aged Receivables, Aged Payables, Expense Claim Detail
  - Reconciliations: Bank Reconciliation, Bank Reconciliation Detail, Bank Summary
  - Taxes/Balances: General Ledger Detail/Summary, Trial Balance, Sales Tax Report
  - Transactions: Account Transactions, Inventory Item Details
- Custom report builder (Blank Report with drag-and-drop layout editor) [^49^]
- Formulas for calculated metrics, switch rules for conditional display [^49^]
- Tracking category filtering in reports [^102^]
- Scheduled report exports (to Excel/Google Sheets via tools like Coupler.io) [^107^]
- Fixed Assets reports: Depreciation Schedule, Disposal Schedule, Fixed Asset Reconciliation [^138^]
- Management Report pack (Executive Summary, Cash Summary, P&L, Balance Sheet, Aged R/P) [^110^]
- **Limitations: No automated KPI calculations, no dynamic visualisations, no multi-entity consolidation, no automated board pack distribution** [^110^]

### 11. Multi-Currency
- 160+ currencies supported [^139^]
- Hourly FX rate updates from XE.com [^133^]
- Foreign currency invoices and bills [^133^]
- Multi-currency bank accounts [^133^]
- FX gain/loss tracking and realised/unrealised reporting [^136^]
- Multi-currency financial statements [^139^]
- Manual exchange rate override capability [^139^]
- Currency exposure reporting
- **Available on Premium/Ultimate plans only** [^135^]

### 12. AI & Automation (JAX)
- JAX (Just Ask Xero) conversational AI assistant — beta launched 2024, rebuilt as "AI financial superagent" September 2025 [^149^]
- Natural language invoice/quote creation [^138^]
- Smart bank reconciliation with ML-based matching (97% claimed accuracy) [^142^]
- Per-organisation ML model trained on historical coding patterns [^142^]
- Cash flow predictions based on historical data [^138^]
- Plain-language financial queries ("What were my top expenses last quarter?") [^142^]
- External data integration via OpenAI (tax rates, regulatory details) [^142^]
- WhatsApp/SMS/email interface for invoice creation [^138^]
- JAX Assure safety filter to prevent hallucinations [^138^]
- **Limitations: No comparative analysis with adjustments, no proactive anomaly detection, requires clean historical data** [^142^]

### 13. API Ecosystem
- **Six APIs**: Accounting, Assets, Projects, Payroll (region-specific), Files, BankFeeds [^96^]
- RESTful JSON over HTTPS
- OAuth 2.0 authentication with PKCE support
- Rate limits: 60 calls/min, 5,000/day per tenant (1,000 for starter), 5 concurrent requests [^96^][^134^]
- Official SDKs: C#, Java, Node.js, PHP, Ruby, Python, Go [^96^]
- Webhooks for contacts and invoices [^152^]
- Sandbox environment for testing
- AI Toolkit for developers (OpenAI Agents SDK, MCP Server, LangChain resources) [^134^]
- Xero App Store with 1,000+ third-party integrations [^95^][^101^]
- App categories: Payments, Expenses/Bills, Inventory, CRM, Ecommerce, Time Tracking, Banking, Reporting, Document Management [^95^]

### 14. Multi-Entity & Consolidation
- **Each legal entity requires separate Xero organisation** [^136^]
- Single login access to multiple organisations with dropdown switching [^148^]
- Automatic volume discounts for same-country organisations [^136^]
- Tracking categories for segment/location analysis within an entity [^140^]
- **No native consolidation, intercompany elimination, or group reporting** [^136^]
- Third-party consolidation apps: Translucent, Joiin, dataSights, Mayday (Recharger/Balancer) [^136^][^142^][^148^]

---

## Trends & Signals

- **Open Banking is displacing screen-scraping aggregators**: Australia's CDR legislation (July 2026 expansion to non-bank lenders) and EU PSD2 standards are replacing Yodlee-style connections with regulated API-based feeds, improving data quality and security [^137^][^147^]. Xero was an early participant in CDR consultations.

- **AI assistants are becoming the primary interface**: JAX represents a shift from "accounting software you navigate" to "financial data you converse with." At Xerocon 2025, Xero positioned JAX as the backbone of its next era, moving from passive record-keeping to proactive financial guidance [^138^][^149^].

- **The "best-of-breed" ecosystem model dominates over monolithic ERP**: Xero's 1,000+ app marketplace (Unleashed for inventory, ApprovalMax for approvals, Dext for receipt capture, Gusto for US payroll) reflects a deliberate strategy to be the accounting kernel while specialists handle vertical depth [^95^][^101^].

- **Bank feed reconciliation is becoming fully autonomous**: JAX's ML models claim 97% accuracy on suggested matches, and Xero's bank rules can pre-categorise 60-70% of transactions. The direction is towards "exception-only" reconciliation where humans only review edge cases [^142^][^137^].

- **Multi-entity accounting is the biggest unsolved problem in SME software**: Xero, QuickBooks, and Sage all lack native multi-entity consolidation. A cottage industry of third-party apps (Translucent, Joiin, Fathom, dataSights) has emerged to fill this gap, suggesting significant market demand [^136^][^148^].

---

## Controversies & Conflicting Claims

- **User count**: Some sources claim "unlimited users on all plans" [^89^] while Xero's own US pricing shows the Early/Starter plan is limited for invoice/bill volume (20 invoices, 5 bills) which functionally constrains users even if login access is unlimited [^97^][^155^].

- **JAX accuracy claims**: Xero claims "over 97% accuracy" on suggested bank reconciliation matches [^142^], but practitioners note this holds for businesses with consistent transaction patterns (e.g., trades businesses buying from the same suppliers weekly) but "a business with irregular, varied spending takes longer for the model to learn" [^142^]. New Xero files or those with messy historical coding get poor suggestions initially.

- **Xero Projects pricing**: Contradictory reports on whether Xero Projects is included or an add-on. JacRox (Xero Platinum Partner) states "available on Xero Standard and Premium plans at no extra cost" [^94^], while LiveCosts' review states "Xero Projects is a paid add-on... pricing increases as more users are added" and that it's "only available on the Established plan" ($90/month) [^97^]. This appears to reflect regional pricing plan differences (UK vs US).

- **Bank feed reliability**: Xero's marketing states "transactions flow into Xero every business day" [^137^], but practitioner reports document frequent feed disconnects after password changes, missing transactions after gaps, duplicate transactions from manual imports, and consent renewal requirements under Open Banking that "catch businesses off guard" [^137^].

---

## Recommended Deep-Dive Areas

1. **Bank Feed Infrastructure Architecture**: Understanding the exact technical stack (which aggregators Xero uses by region, fallback mechanisms, data normalisation pipelines) is critical for building a competitive headless system. The Open Banking API landscape is rapidly evolving and varies significantly by jurisdiction.

2. **JAX AI/ML Model Architecture**: The per-organisation ML approach (training on specific coding history rather than generic models) has important implications for a new system — accuracy will be poor initially and require significant training data. Understanding the feature vectors, model retraining cadence, and confidence thresholds would inform our own ML reconciliation design.

3. **Multi-Entity Consolidation**: This is the single largest functional gap across all major SME accounting platforms. A headless system that offers native multi-entity support with automatic intercompany eliminations would be a significant competitive differentiator. The third-party consolidation ecosystem (Translucent, Joiin, dataSights) represents a ~$30-150/month per entity addressable market.

4. **Inventory Costing Methods**: Xero's weighted-average-only approach is a major limitation for manufacturing and wholesale businesses. Supporting FIFO, LIFO, and specific identification natively — especially for multi-warehouse scenarios — would be a strong differentiator.

5. **Approval Workflow Engine**: Xero's single-step approval is universally criticised. A headless system with native multi-step, conditional, parallel, and delegation-based approval workflows (amount thresholds, department-based routing, DoA policy enforcement) would significantly outclass incumbents.

6. **API Design & Rate Limiting Strategy**: Xero's 5,000 calls/day limit is constraining for high-volume integrations. Designing a more generous rate limit structure (or usage-based pricing tiers) could attract developers building data-intensive applications.

---

## MVP vs Full Feature Roadmap Implications

### MVP-Phase 1 (Core Ledger — Months 1-6)
- **Must-have for MVP**:
  - Double-entry general ledger with chart of accounts
  - Basic invoicing (create, send, status tracking)
  - Bank transaction import (CSV/OFX manual upload)
  - Basic bank reconciliation (manual matching)
  - Contact management (customers and suppliers)
  - Sales tax/VAT calculation
  - Basic reporting (P&L, Balance Sheet, Trial Balance)
  - Multi-currency support (at least major 10-20 currencies)
  - Basic expense capture (receipt upload, manual entry)
  - User authentication and role-based access

### Phase 2 (Automation Layer — Months 6-12)
  - Bank feed integrations (start with 5-10 major banks via Plaid/TrueLayer)
  - Bank rules engine for auto-categorisation
  - Recurring invoices and payment reminders
  - Online payment acceptance (Stripe/GoCardless integration)
  - Quote → Invoice workflow
  - Purchase orders and basic bill management
  - Cash flow forecasting
  - Budgeting and budget vs actual reporting
  - API endpoints for core operations (REST + webhooks)
  - Basic receipt OCR (integration with receipt capture API)

### Phase 3 (Advanced Features — Months 12-18)
  - Payroll module (start with UK: PAYE, RTI, auto-enrolment)
  - Inventory tracking (tracked/untracked items, weighted average COGS)
  - Fixed asset register with depreciation
  - Project tracking with time/expense allocation
  - Multi-step approval workflows for POs and bills
  - Expense claims with mileage tracking
  - Advanced reporting suite (50+ templates, custom report builder)
  - AI-powered bank reconciliation (ML matching)
  - Conversational AI assistant (JAX equivalent)

### Phase 4 (Enterprise Scale — Months 18-24)
  - Multi-entity consolidation with intercompany eliminations
  - Advanced inventory (FIFO/LIFO, multi-warehouse, barcode, serial/batch)
  - Multi-location support with tracking categories
  - 1,000+ app integrations via marketplace
  - Advanced API (GraphQL, higher rate limits, real-time webhooks)
  - Industry-specific modules (construction job costing, manufacturing BOM)
  - International payroll expansion (AU, US via Gusto model)

### Key Architectural Decisions
- **Bank feeds**: Integrate via Plaid/TrueLayer/Salt Edge aggregators rather than building direct bank connections — faster time-to-market, broader coverage
- **Multi-currency**: Build in from day one (FX rate service, multi-currency accounts, revaluation) — retrofitting is painful
- **Inventory**: Start with weighted average, plan FIFO/LIFO as plugin modules
- **Payroll**: Consider UK-first with HMRC-recognised status, then partner model for US (like Xero+Gusto)
- **API-first design**: Every feature must be API-accessible from launch — the UI is just a client of the API
- **ML/AI**: Bank reconciliation matching is the highest-value ML application; build data pipelines for per-tenant model training from the start
