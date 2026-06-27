# 9. Phased Implementation Roadmap

## 9.1 Roadmap Overview

The transition from a functional MVP to a Xero-class accounting platform spans 15 months and 298 engineering days. The roadmap is organized into four phases of increasing scope and team size, each building upon the prior phase's foundation. The progression is deliberate: core ledger and single-entity accounting must be production-hardened before automation layers are added, automation must prove reliable before multi-currency and payroll complexity is introduced, and the API platform and marketplace require a mature feature set to expose to third-party developers.

**Table 9-1** summarizes the complete journey.

| Phase | Calendar Duration | Engineering Days | Peak Team | Cumulative Skills | Xero Parity |
|:---|:---|:---|:---|:---|:---|
| MVP | 8 weeks (48 days) | 48 | 2–3 | 25+ | 60% |
| Phase 2: Automation | Months 3–5 (65 days) | 65 | 3–4 | 65+ | 75% |
| Phase 3: Scale | Months 6–9 (80 days) | 80 | 4–5 | 120+ | 88% |
| Phase 4: Enterprise | Months 10–15 (105 days) | 105 | 5–7 | 190+ | 95%+ |
| **Total** | **15 months** | **298** | **5–7 (peak)** | **190+** | **95%+** |

**Table 9-1: Complete roadmap summary — four phases from MVP to Xero-class platform.**

The MVP establishes the architectural foundation: a headless, LLM-native accounting system built on Formance Ledger with PostgreSQL, delivering ten core modules across chart of accounts, general ledger, contact management, bank import, reconciliation, invoicing, VAT calculation, core reports, chat interface, and authentication [^45^][^213^]. These 48 engineering days produce 25+ registered LLM SKILLs and achieve approximately 60% feature parity with Xero's core accounting modules [^264^][^405^]. The team is small — two to three engineers — reflecting the focused scope and the leverage provided by Formance's built-in double-entry enforcement and Numscript transaction modeling.

Xero parity progresses non-linearly across phases. The jump from 60% to 75% (MVP to Phase 2) is driven by bank feed automation, document extraction, and MTD (Making Tax Digital) VAT submission — capabilities that dramatically reduce manual data entry but are technically additive rather than structurally complex. The 75% to 88% leap (Phase 2 to Phase 3) requires foundational changes: a multi-currency layer compliant with IAS 21, a multi-tax jurisdiction engine, UK payroll with Real Time Information (RTI) submission, and inventory tracking — each introducing new data models and compliance surfaces. The final 88% to 95%+ gain (Phase 3 to Phase 4) comes from multi-entity consolidation, project tracking, a public API platform, an app marketplace, ML-powered reconciliation, and white-label capabilities — features that position the system as infrastructure rather than application [^585^][^588^].

SKILL count grows from 25+ (MVP) to 65+ (Phase 2), 120+ (Phase 3), and 190+ (Phase 4). This growth reflects both new feature domains and increasing depth within existing domains. The Phase 2 rules engine alone adds seven SKILLs (rule creation, listing, editing, reordering, testing, analytics, and template import); Phase 3 payroll adds twelve SKILLs covering employee management, pay run execution, FPS/EPS submission, and statutory payment processing; Phase 4 multi-entity management adds eight SKILLs for entity switching, intercompany transactions, and consolidated reporting.

The growth in registered LLM SKILLs provides a measurable proxy for system capability. **Table 9-2** tracks this growth by category.

| Skill Category | MVP (25+) | Phase 2 (65+) | Phase 3 (120+) | Phase 4 (190+) |
|:---|:---|:---|:---|:---|
| Chart of Accounts | 4 | 4 | 4 | 4 |
| General Ledger | 7 | 7 | 7 | 7 |
| Contacts | 5 | 5 | 5 | 5 |
| Banking | 6 | 12 | 12 | 14 |
| Reconciliation | 5 | 5 | 5 | 8 |
| Invoicing | 6 | 10 | 10 | 12 |
| VAT / Tax | 4 | 8 | 16 | 20 |
| Reporting | 3 | 3 | 20 | 24 |
| Multi-user & Approvals | — | 8 | 8 | 10 |
| Payroll | — | — | 12 | 12 |
| Inventory & Assets | — | — | 8 | 8 |
| Multi-entity | — | — | — | 8 |
| Projects & Expenses | — | — | — | 10 |
| API & Marketplace | — | — | — | 12 |
| ML & Analytics | — | — | — | 6 |
| **Total** | **25+** | **65+** | **120+** | **190+** |

**Table 9-2: LLM SKILL growth trajectory — from 25+ MVP skills to 190+ enterprise skills.**

Team composition evolves with each phase. The MVP requires one backend/ledger engineer, one API/integration engineer, and one LLM/chat specialist. Phase 2 adds a bank feed integration engineer. Phase 3 adds a payroll specialist (critical given HMRC RTI compliance requirements) [^592^][^593^]. Phase 4 adds an ML engineer for the reconciliation engine and a DevOps/integrations specialist for the API platform and marketplace. Peak headcount of 5–7 occurs only in the final months; the average across 15 months is 3–4 engineers.

## 9.2 Phase 2: Automation (Months 3–5)

Phase 2 reduces manual data entry effort by 70% or more through three automation vectors: automatic data ingestion (bank feeds, document upload), intelligent categorization (rules engine), and workflow collaboration (multi-user, approvals). The 65 engineering days are distributed across seven major feature areas, with bank feed integration and HMRC MTD VAT submission carrying the highest complexity.

### 9.2.1 Month 3: Bank Feeds, Rules Engine, and Recurring Transactions

Bank feed integration is the highest-impact feature of Phase 2. The aggregator strategy uses a tiered failover chain: TrueLayer as the primary UK provider (PSD2-compliant, FCA-regulated), Plaid as secondary (broader coverage across 12,000+ institutions), Salt Edge for EU multi-country support, and Yodlee as fallback [^258^][^261^][^265^][^254^]. Each connection uses Open Banking APIs with Strong Customer Authentication (SCA), supports daily polling with configurable frequency (hourly, daily, weekly), and provides historical backfill of 12–24 months on initial connection [^352^]. The ingestion pipeline — POLL from aggregator → NORMALIZE to canonical schema → DEDUPLICATE via persistent transaction IDs → QUEUE via message broker → PROCESS with automatic categorization triggering — runs asynchronously, allowing real-time webhook notifications without blocking the chat interface [^221^][^222^]. The canonical transaction schema normalizes across all aggregators, capturing transaction_id, account_id, amount, currency, transaction_date, description, merchant_name (97% fill rate from Plaid), reference, transaction_type, status, and raw original data for audit purposes [^348^].

The bank rules engine implements Xero-style automatic categorization. Each rule comprises conditions (description contains/equals/regex, amount between/equals/greater_than, reference matching, bank account filtering, direction) combined with AND/OR logic, and actions (assign contact, general ledger account, VAT rate, tracking category) [^277^][^279^][^281^]. Three execution modes govern risk: Suggest (pre-fills categorization for user confirmation, recommended default), Auto-apply (automatically categorizes and posts, available only after a rule has proven reliable), and Disabled (stored but not evaluated). A pre-built library of 50+ common patterns covers recurring merchants such as Stripe payouts, AWS charges, council tax payments, and subscription services. Rule effectiveness analytics track the percentage of transactions auto-matched versus suggested versus missed, enabling continuous refinement.

Recurring transactions and invoices complete Month 3. Templates support weekly, bi-weekly, monthly, quarterly, and annual schedules with end conditions (never, after N occurrences, until date). Auto-post and draft-for-review modes accommodate varying risk tolerances. Pre-built templates cover rent, insurance, subscriptions, loan repayments, and depreciation. Recurring invoices extend the template architecture with auto-send via email, optional automatic payment collection via Stripe or GoCardless integration, failed payment retry logic, and the ability to pull unbilled time or expenses onto generated invoices [^220^][^349^][^350^].

### 9.2.2 Month 4: Recurring Invoices, Document Extraction, and Multi-User Support

Document upload and OCR (Optical Character Recognition) extraction transforms receipt and invoice images into structured transaction data. The pipeline runs: Document Upload → Preprocessing (deskew, enhance contrast) → OCR (Tesseract or DocTR) → LLM Extraction (GPT-4o Vision or Claude) → Validation Rules → Structured Output → Draft Transaction or Bill [^62^][^602^]. Validation enforces amount consistency (sum of line items equals subtotal equals total minus VAT), date validity (invoice date precedes or equals due date), VAT calculation verification (VAT amount equals net multiplied by rate), and duplicate detection (same vendor, number, and amount flagged). Low-confidence extractions (below 90%) route to human-in-the-loop review with side-by-side document and extracted data display. End-to-end extraction accuracy reaches 95–97% with validation rules, reducing human intervention by 80% compared to manual entry [^602^].

Multi-user support introduces role-based access control with five roles: Owner (full access including entity deletion and billing), Admin (full access except deletion), Bookkeeper (transaction recording, reconciliation, report generation), Accountant (read-only access to all data plus report execution), and Viewer (read-only, no transaction details). Features include email-based user invitation, activity logging, concurrent editing protection, and user-specific preferences for date format, currency display, and timezone.

### 9.2.3 Month 5: Approval Workflows and HMRC MTD VAT Submission

Approval workflows implement multi-step chains for invoices, bills, and journal entries. Configuration supports 1–3 approval levels with threshold-based routing (for example, under GBP 500 auto-approved, GBP 500–2,000 requires manager approval, over GBP 2,000 requires director approval). Approval types cover invoice approval, bill payment approval, and journal entry approval. Delegation during absence, automatic escalation after N days of inaction, and approval via natural language chat or email link provide operational flexibility. The status flow — Draft → Submitted for Approval → Approved → Posted/Sent, with a rejection path back to Draft — integrates with the Phase 2 notification system to alert approvers via chat and email.

HMRC MTD VAT submission is the compliance milestone of Phase 2. Requirements include HMRC Developer account registration, VAT registration number linked to MTD, OAuth2 authentication, mandatory fraud prevention headers (Gov-Client-Connection-Method, Public-IP, Device-ID, and others), and digital link compliance ensuring no manual re-keying between source data and submitted return [^124^][^579^][^583^]. The submission flow — one-click VAT submission from chat, pre-submission validation of all nine boxes, HMRC obligation sync so the system knows which periods are due, status tracking from Submitted through Acknowledged to Accepted, and parsed error explanations for HMRC rejections — completes the compliance chain that began with MVP digital record keeping. Correction workflows support additional VAT returns for amendments.

**Table 9-3** details the full Phase 2 feature set.

| Feature | Month | Description | Dependencies | Complexity | Effort (days) |
|:---|:---|:---|:---|:---|:---|
| Bank feed integration | 3 | TrueLayer + Plaid + Salt Edge + Yodlee aggregator chain, PSD2 SCA, 12–24 month backfill | Aggregator contract | High | 15 |
| Bank rules engine | 3 | 50+ pre-built patterns, condition operators, 3 execution modes | Bank feeds | Medium | 8 |
| Recurring transactions | 3 | Weekly to annual schedules, auto-post/draft modes, templates | GL engine | Medium | 8 |
| Recurring invoices | 4 | Auto-send, Stripe/GoCardless collection, failed payment handling | Invoicing, recurring | Medium | 6 |
| Document upload + OCR | 4 | PDF/JPG/PNG extraction, 95–97% accuracy, human-in-the-loop | OCR engine, LLM vision | High | 12 |
| Multi-user support | 4 | 5 roles, invitation, activity logging, concurrent editing | Auth system (MVP) | Low-Med | 5 |
| Approval workflows | 5 | 1–3 levels, threshold-based, delegation, escalation | Multi-user, email | Medium | 7 |
| HMRC MTD VAT submission | 5 | OAuth2, fraud headers, 9-box submission, obligation sync | HMRC dev account | High | 10 |
| **Total** | | | | | **65** |

**Table 9-3: Phase 2 feature detail — seven major features reducing manual data entry by 70%+.**

## 9.3 Phase 3: Scale (Months 6–9)

Phase 3 transforms the single-entity UK GBP system into a multi-currency, multi-jurisdiction platform suitable for growing businesses, e-commerce operations, and product-based companies. The 80 engineering days span eight major feature areas, with multi-tax jurisdiction support and UK payroll carrying the highest complexity due to regulatory compliance requirements.

### 9.3.1 Month 6: Multi-Currency and Multi-Tax Jurisdictions

Multi-currency support implements a three-currency architecture: functional currency (the primary economic environment, typically GBP for UK businesses), transaction currency (the denomination of individual invoices or payments), and presentation currency (the currency used for reporting). The system supports 150+ currencies per ISO 4217, with exchange rate sources from the European Central Bank (ECB, EUR-based), XE.com, and Open Exchange Rates. Daily automatic updates keep rates current. Transaction-level currency recording preserves the original transaction currency alongside the functional currency equivalent [^585^].

FX (Foreign Exchange) gain and loss handling complies with IAS 21. When an invoice is issued in a foreign currency, it is recorded at the spot rate on the invoice date. When payment is received, the spot rate on the payment date determines realized FX gain or loss. At period end, revaluation using the closing rate calculates unrealized gain or loss on open foreign currency positions. This three-stage treatment — transaction date, payment date, period-end — matches IAS 21 requirements for monetary items and ensures accurate financial reporting for businesses operating across borders.

The multi-tax jurisdiction engine expands the MVP's UK VAT support to encompass VAT, GST (Goods and Services Tax), US Sales Tax, and Digital Services Tax. The tax rule engine stores jurisdiction-specific rates, thresholds, exemptions, and place-of-supply rules. For EU operations, reverse charge handling for cross-border B2B transactions and OSS (One-Stop Shop) reporting are implemented [^257^]. US sales tax includes economic nexus tracking post-Wayfair (2018) with destination-based sourcing, monitoring the relevant thresholds. The place of supply engine determines tax jurisdiction based on supply category, party types (B2B versus B2C), customer location, and applicable specific and general rules. Tax registration threshold monitoring provides Green, Amber, Orange, and Red alert levels as a business approaches registration requirements in each jurisdiction [^234^][^236^].

### 9.3.2 Month 7: Inventory and Fixed Assets

Inventory and stock tracking introduces product catalog management with SKU, name, description, category, and unit of measure. Quantity tracking covers on-hand, committed, and available stock. FIFO (First-In, First-Out) is the default cost method, with average cost as an alternative. Stock adjustments handle write-offs, damage, and count corrections. Purchase orders flow through the full procurement cycle: creation, transmission to supplier, goods receipt (partial or full), bill matching, and payment. Cost of Goods Sold (COGS) is calculated automatically on sale through the inventory transaction flow — purchase order generates a liability, goods receipt increases inventory, sales invoice triggers COGS recognition and inventory reduction.

The fixed asset register tracks assets with automatic depreciation calculation. Asset categories carry default useful lives: Buildings (50 years), Vehicles (4 years), IT Equipment (3 years), Furniture (5 years), and Machinery (10 years). Two depreciation methods are supported: straight-line (default, equal charge per period) and diminishing value (reducing balance, higher charge in early years) [^586^][^591^]. Automatic monthly depreciation journals are posted to the general ledger: debit Depreciation Expense, credit Accumulated Depreciation. Asset disposal calculates gain or loss and removes the asset from the register. The Xero-style integrated approach — asset register with automatic GL posting — avoids the need for separate depreciation software.

### 9.3.3 Month 8: UK Payroll with RTI and Advanced Reporting

UK payroll with RTI integration is the most complex feature of Phase 3. Employee records store personal details, National Insurance number, tax code, salary or hourly rate, and start date. Pay elements include basic pay, overtime, bonuses, and commissions. Deductions cover PAYE (Pay As You Earn) income tax, employee National Insurance contributions (NICs), student loan repayments, and pension contributions. Employer costs include employer NICs, pension contributions, and apprenticeship levy. Payslip generation produces PDF documents. Pay runs support monthly, weekly, fortnightly, and four-weekly cycles [^592^][^593^].

RTI submissions are mandatory for all UK employers. FPS (Full Payment Submission) reports employee payments, tax, NICs, and deductions on or before each payday. EPS (Employer Payment Summary) provides monthly adjustments, statutory payment reclaims, and other corrections by the 19th of each month. Late submission penalties scale from GBP 100 per month (1–9 employees) to GBP 400 (250+ employees) [^593^]. Additional payroll features include starters and leavers processing (P45, starter checklist), statutory payments (SMP, SPP, SAP, SSP), Employment Allowance claim, P60 year-end generation, and auto-enrolment pension compliance [^598^][^600^].

The advanced report library adds 15+ reports across six categories: Core Statements (Cash Flow Statement, Statement of Changes in Equity), Management (General Ledger Detail, Executive Summary, Cash Summary), Tax (Corporation Tax Computation), Variance (Budget vs Actual, Period-over-Period Comparison), KPI (Profitability Ratios, Liquidity Ratios, Burn Rate and Runway), and Audit (Audit Trail, Journal Entry Report) [^139^][^114^].

### 9.3.4 Month 9: Custom Reports, Purchase Orders, and Tracking Categories

The custom report builder provides drag-and-drop (API-configurable) report design with column selection, filtering by any field with conditions (equals, contains, greater than, between), grouping by account, contact, date period, or tracking category, and sorting. Custom reports can be saved as templates and scheduled for daily, weekly, or monthly generation with email delivery in PDF, CSV, Excel, or JSON formats.

Purchase orders and bills implement a three-way matching workflow: Purchase Order → Goods Receipt → Bill [^220^]. PO status flows from Draft through Sent, Partially Received, Received, Billed, to Closed. Bill creation auto-populates from received goods. Bill approval leverages Phase 2 workflows. Payment scheduling allows pay-now or pay-later with A/P aging and payment forecasting.

Tracking categories (Xero-style dimensions) enable segmental analysis. Two categories can be active simultaneously — for example, "Department" and "Region" — with unlimited options per category. Transactions, invoice lines, and journal entries can be tagged, and all reports filter by tracking category. Budgets per tracking category option support departmental or regional budget variance analysis.

**Table 9-4** consolidates the Phase 3 feature set.

| Feature | Month | Description | Dependencies | Complexity | Effort (days) |
|:---|:---|:---|:---|:---|:---|
| Multi-currency (150+) | 6 | IAS 21 compliant, 3-currency architecture, realized/unrealized FX | GL engine | High | 10 |
| Multi-tax jurisdictions | 6 | VAT/GST/Sales Tax, place of supply engine, OSS, nexus tracking | Tax rule engine | Very High | 15 |
| Inventory/stock tracking | 7 | FIFO, COGS, purchase orders, stock adjustments, low-stock alerts | GL, invoicing | High | 12 |
| Fixed asset register | 7 | Straight-line/diminishing value, auto depreciation journals | GL engine | Medium | 8 |
| UK payroll with RTI | 8 | FPS/EPS submission, PAYE, NICs, pension auto-enrolment | HMRC PAYE API | Very High | 20 |
| Advanced reports (15+) | 8 | Cash flow, KPIs, variance, audit reports | Report engine (MVP) | High | 12 |
| Custom report builder | 9 | Drag-drop API, scheduling, multi-format export | Report engine | High | 8 |
| Purchase orders/bills | 9 | 3-way matching, PO-to-bill flow, payment scheduling | Inventory, approvals | Medium | 8 |
| Tracking categories | 9 | 2 active dimensions, budget per option, segmental reporting | GL, reports | Low-Med | 5 |
| **Total** | | | | | **80** |

**Table 9-4: Phase 3 feature detail — nine major features expanding to multi-currency, multi-jurisdiction, and payroll.**

## 9.4 Phase 4: Enterprise (Months 10–15)

Phase 4 transforms the platform into multi-entity accounting infrastructure suitable for accounting practices, multi-company groups, and enterprise deployment. The 105 engineering days cover eight major feature areas, with multi-entity management and ML-powered reconciliation carrying the highest complexity. This phase also delivers the API platform, app marketplace, white-label capabilities, and industry-specific modules that differentiate the system from small-business accounting software and position it as embeddable infrastructure.

### 9.4.1 Multi-Entity Management (Months 10–11)

Multi-entity management supports multiple legal entities — companies, subsidiaries, branches — within a single account. Each entity maintains its own chart of accounts, bank accounts, tax settings, and reporting currency. Entity switching operates via natural language ("Switch to Acme UK Ltd"). Shared COA templates ensure consistency across entities. The five non-negotiable capabilities for multi-entity accounting are all implemented: automated intercompany elimination (intercompany sales and purchases netted to zero in consolidated reports), entity-level and consolidated reporting from the same underlying data, shared services allocation (central costs distributed to entities), multi-currency per entity with cumulative translation adjustments, and per-entity audit trails with access controls [^585^][^588^].

Intercompany transactions generate automatic double-entry pairs. When Entity A invoices Entity B, the system simultaneously creates a receivable in Entity A and a payable in Entity B, auto-matches them as an intercompany pair, and eliminates both in consolidated reports. This eliminates the manual elimination journals that consume significant time in traditional group accounting and that are a common source of consolidation errors.

### 9.4.2 Project Tracking and Expense Claims (Months 11–12)

Project tracking provides time tracking, job costing, and project profitability analysis. Projects carry name, client, dates, budget, and status (Planning → Active → On Hold → Completed → Archived). Time entries log hours by project, task, and user. Expenses allocate to projects via receipt capture and direct assignment. Invoices link to projects for revenue tracking. Project P&L reports income versus costs per project with budget variance alerts. Utilization reports compare billable to non-billable hours. Margin analysis calculates gross profit margin per project.

Expense claims handle employee expense submission, approval, and reimbursement. Receipt capture uses the Phase 2 OCR pipeline. Mileage tracking applies HMRC approved rates (45p per mile for the first 10,000 miles, 25p thereafter). Per diem and subsistence claims follow standard categories. Multi-level approval workflows route from submitter through manager to finance. Reimbursement tracking schedules and records payments, with integration to payroll for on-payslip reimbursements. Policy enforcement enforces category limits, daily limits, and receipt requirements.

### 9.4.3 API Platform and Developer Ecosystem (Months 12–13)

The API platform exposes all system operations via a RESTful API with OpenAPI 3.0 specification and auto-generated documentation. Webhook subscriptions cover ten event types: entity.created, transaction.posted, invoice.created, invoice.paid, invoice.overdue, bank.transaction.imported, bank.reconciled, vat.return.submitted, contact.created, and report.generated [^603^]. Tiered rate limiting supports free (100 requests per hour), pro (10,000 per hour), and enterprise (unlimited) tiers. URL-based versioning (/v1/, /v2/) ensures backward compatibility. OAuth2 authentication supports both client credentials and authorization code flows. Bulk operations enable batch transaction creation and contact updates. SDKs in five languages — JavaScript/TypeScript, Python, PHP, Java, and Go — lower integration barriers. The developer portal provides an interactive API explorer (Swagger UI), code examples in all SDK languages, a webhook testing endpoint, and a sandbox environment with pre-loaded test data.

### 9.4.4 App Marketplace (Months 13–14)

The app marketplace provides a directory of third-party integrations organized into eight categories: Banking (TrueLayer, Plaid, Yodlee), Payments (Stripe, GoCardless, PayPal), E-commerce (Shopify, WooCommerce, Square), CRM (HubSpot, Salesforce), Time Tracking (Toggl, Harvest), Expenses (Pleo, Soldo), Document (Dext, Hubdoc), and Analytics (Syft, Fathom). Each integration uses OAuth2 one-click installation with scoped permissions. An app review process ensures quality and security before listing. Developer analytics track installs, active users, and API calls. Featured and verified app badges highlight quality integrations. User reviews and ratings provide social proof. Billing integration supports subscription management for paid apps.

### 9.4.5 ML-Powered Reconciliation (Month 14)

ML-powered reconciliation implements a Xero JAX-inspired four-layer intelligence architecture: Rule layer (user-defined bank rules from Phase 2), Match layer (transaction-to-document matching), Memory layer (learning from the user's historical reconciliation patterns), and Prediction layer (suggestions based on anonymized aggregate behavior) [^345^][^346^][^349^][^351^]. A per-organization Random Forest model is trained on 12 months of historical reconciliation data. The feature vector includes amount, day of week, hour, merchant name, description keywords, and historical category distribution [^280^]. Auto-reconcile targets 80%+ of bank lines in real-time, with confidence scoring ensuring only high-confidence matches auto-process. Suggested match accuracy targets 97%+ [^349^]. Continuous learning retrains models periodically with new data, and confidence calibration adjusts probability outputs per organization.

### 9.4.6 White-Label and Industry Modules (Months 14–15)

White-label capabilities enable rebrandable deployment for banks, fintechs, and vertical SaaS companies. Features include custom branding (logo, colors, domain), embeddable chat widget and report viewer components, multi-tenant data isolation per deployment, a partner portal for managing multiple white-label deployments, usage-based billing for partners, custom onboarding flows, per-region regulatory compliance, and SSO integration. Target partners include challenger banks seeking built-in bookkeeping, vertical SaaS platforms (property management, hospitality, retail), fintech lending and payments platforms, and accounting practices wanting branded client portals.

Industry-specific modules provide specialized functionality for four verticals. The Construction Industry Scheme (CIS) module handles contractor registration, CIS deductions on subcontractor payments (20% for registered, 30% for unregistered), monthly CIS300 returns to HMRC, and CIS deduction statements to subcontractors [^598^]. The Property/Landlord module supports property portfolio tracking with per-property P&L, rent roll management, tenant deposit handling, service charge apportionment, and mortgage interest tracking. The SaaS/Subscription Business module provides MRR/ARR tracking, churn analysis, customer cohort reporting, revenue recognition per IFRS 15 and ASC 606, and burn rate and runway calculation [^156^][^157^]. The Practice Management module (for accountants) offers client management with multiple entities per client, bulk operations, practice-level reporting, time tracking and WIP, client billing, and AML compliance checks.

**Table 9-5** details the full Phase 4 feature set.

| Feature | Month | Description | Dependencies | Complexity | Effort (days) |
|:---|:---|:---|:---|:---|:---|
| Multi-entity management | 10–11 | Intercompany elimination, consolidated reporting, shared services allocation | GL engine | Very High | 18 |
| Project tracking | 11 | Time tracking, job costing, project P&L, utilization reports | Invoicing | Medium | 10 |
| Expense claims | 11–12 | Receipt capture, mileage (HMRC rates), per diem, reimbursement | OCR, approvals | Medium | 8 |
| API platform | 12–13 | OpenAPI 3.0, 10+ webhooks, SDKs in 5 languages, sandbox | All existing APIs | High | 15 |
| App marketplace | 13–14 | 30+ integrations across 8 categories, OAuth2 install, app review | API platform | High | 12 |
| ML reconciliation | 14 | Per-org Random Forest, 80%+ auto-reconcile, 97%+ accuracy | Bank feeds, rules, historical data | Very High | 15 |
| White-label | 14–15 | Embeddable accounting, partner portal, multi-tenant | Multi-tenant architecture | High | 12 |
| Industry modules | 15 | CIS, property, SaaS metrics, practice management | Phase 2–3 features | Med-High | 15 |
| **Total** | | | | | **105** |

**Table 9-5: Phase 4 feature detail — eight major features positioning the system as accounting infrastructure.**

## 9.5 Compliance and Technical Milestones

The roadmap is anchored to three categories of compliance deadlines: UK regulatory milestones that the system must meet for market viability, international expansion requirements, and critical external deadlines that constrain the delivery timeline.

### 9.5.1 UK Compliance Timeline

HMRC MTD VAT progresses through all four phases. The MVP establishes digital record keeping and nine-box return calculation with preview-only display — sufficient for a business to use the system for bookkeeping while submitting via existing MTD software [^124^][^583^]. Phase 2 enables full API submission to HMRC with OAuth2 authentication and fraud prevention headers, making the system a complete MTD-compliant solution [^579^]. Phase 3 extends to multi-scheme support (cash accounting, accrual, flat rate scheme). Phase 4 adds group VAT and partial exemption handling for larger businesses.

RTI payroll arrives in Phase 3 with FPS and EPS submission capabilities, PAYE and NICs calculation, and pension auto-enrolment compliance. This aligns with the payroll module's delivery in Month 8. Companies House iXBRL (inline eXtensible Business Reporting Language) filing is introduced as a preview in Phase 3 and as full submission capability in Phase 4, ahead of the mandatory digital filing requirement [^159^].

### 9.5.2 International Expansion

International tax support begins in Phase 3 with three jurisdictions: EU VAT OSS (One-Stop Shop) registration and intra-community supply handling, US Sales Tax with economic nexus tracking and destination-based sourcing, and Australia GST with BAS (Business Activity Statement) reporting [^257^][^234^]. Phase 4 extends to full multi-state filing in the US, local VAT filings per EU country, and full ATO (Australian Taxation Office) integration. Canada GST/HST with GST34 calculation and CRA (Canada Revenue Agency) integration also lands in Phase 4.

### 9.5.3 Critical External Deadlines

Three external deadlines impose hard constraints on the delivery timeline. The EU AI Act's full high-risk system obligations take effect on August 2, 2026, with penalties up to EUR 35 million or 7% of global turnover. The system's Phase 2 delivery (Month 5) coincides with this window, and the built-in EU AI Act compliance — decision logging, human oversight, transparency, and accuracy certification — becomes a competitive differentiator against established players who must retrofit their architectures [^301^]. IFRS 18 (Presentation and Disclosure in Financial Statements) becomes effective January 2027, mandating the five-category P&L structure (Operating, Investing, Financing, Income Taxes, Discontinued Operations) and Management Performance Measure disclosures. Phase 3's advanced reporting module (Month 8–9) delivers native IFRS 18 support, positioning the system as ready before the mandatory effective date. UK Companies House digital filing via iXBRL becomes mandatory in April 2028; Phase 4's iXBRL filing capability (Month 10–11) ensures readiness well ahead of this deadline.

**Table 9-6** maps the compliance progression across all phases.

| Regulation / Deadline | MVP | Phase 2 | Phase 3 | Phase 4 |
|:---|:---|:---|:---|:---|
| HMRC MTD VAT | Digital records, 9-box preview [^124^] | Full API submission [^579^] | Multi-scheme (cash/accrual/flat rate) | Group VAT, partial exemption |
| HMRC RTI Payroll | — | — | FPS + EPS submission [^592^] | Full PAYE, auto-enrolment |
| Companies House iXBRL | — | — | iXBRL preview | Full filing (mandatory Apr 2028) [^159^] |
| IFRS 18 (Jan 2027) | — | — | Five-category P&L, MPM disclosures [^301^] | Full reporting suite |
| EU VAT OSS | — | — | Registration, intra-community [^257^] | Local filings per country |
| US Sales Tax | — | — | Economic nexus, destination sourcing [^234^] | Multi-state filing |
| Australia GST | — | — | BAS reporting | Full ATO integration |
| EU AI Act (Aug 2026) | — | High-risk system compliance [^124^] | Post-market monitoring | Full conformity assessment |

**Table 9-6: UK and international compliance roadmap — regulatory milestones across all four phases.**

The technical dependency chain reveals the critical path through the roadmap. Phase 2's bank feeds depend on aggregator partnership contracts — a medium-risk dependency mitigated by TrueLayer and Plaid's self-serve signup options. The rules engine depends on the bank feed pipeline but can be developed in parallel using test data. Phase 3's multi-tax engine requires research per jurisdiction — medium risk, manageable through phased rollout starting with EU VAT OSS. UK payroll carries the highest Phase 3 risk due to HMRC PAYE API credential requirements and the complexity of RTI compliance; mitigation includes extensive testing against HMRC reference calculators and a parallel-run beta period with volunteer users before general availability. Phase 4's ML reconciliation requires 12 months of historical data — medium risk, as Phase 2 bank feeds begin accumulating data from Month 3 onward, providing sufficient training history by Month 14. White-label deployment requires mature multi-tenant architecture, which is built incrementally from MVP onward through per-tenant Formance ledgers and PostgreSQL schema isolation.

**Table 9-7** consolidates the Xero feature parity progression that serves as the roadmap's north star metric.

| Capability Area | Xero Features (approx.) | Our Delivery Timeline | Parity % |
|:---|:---|:---|:---|
| Core accounting (GL, invoicing, bank import, VAT, reports) | ~30 | MVP (8 weeks) | 60% |
| + Automation (feeds, rules, recurring, MTD submission) | ~25 | Phase 2 (Months 3–5) | 75% |
| + Scale (multi-currency, payroll, inventory, assets, custom reports) | ~35 | Phase 3 (Months 6–9) | 88% |
| + Enterprise (multi-entity, projects, API, marketplace, ML, white-label) | ~30 | Phase 4 (Months 10–15) | 95%+ |

**Table 9-7: Xero feature parity progression — capability coverage from 60% at MVP to 95%+ at Phase 4.**

The 95%+ parity figure at Phase 4 reflects functional equivalence on core accounting, automation, scale, and enterprise dimensions. Remaining gaps at Phase 4 are expected in niche areas such as specific third-party integrations (Xero's app store lists 1,000+ applications), specialized payroll for non-UK jurisdictions, and advanced analytics. These gaps are deliberate: the roadmap prioritizes depth in UK small-business accounting over breadth of integration, with the API platform and marketplace designed to close the integration gap organically through third-party developers. The headless architecture — exposing all functions via MCP-standardized APIs — means that every integration built for the marketplace adds capability without increasing core system complexity, inverting the traditional model where each integration requires bespoke engineering within the accounting platform itself.

**Table 9-8** catalogues the critical technical dependencies and associated blocker risk by phase.

| Feature | Depends On | Blocker Risk | Mitigation |
|:---|:---|:---|:---|
| **Phase 2** | | | |
| Bank feeds | Aggregator partnership (TrueLayer/Plaid) | Medium | Self-serve signup available; multi-aggregator failover chain |
| Rules engine | Bank feed pipeline | Low | Can build in parallel using test data |
| Recurring invoices | GL engine, invoicing | Low | Extends existing systems |
| Document extraction | OCR engine + LLM vision | Low | GPT-4o Vision API available via standard API |
| Multi-user | Auth system (MVP) | Low | Extends existing JWT-based auth |
| HMRC MTD VAT | HMRC Developer account | Medium | Apply early; sandbox available for pre-live testing |
| **Phase 3** | | | |
| Multi-currency | GL engine (exchange rate fields) | Low | Additive schema changes only |
| Multi-tax | Tax rule engine per jurisdiction | Medium | Phased rollout: EU VAT first, US/AU follow |
| Inventory | GL engine, invoicing, PO module | Medium | Requires COGS posting logic |
| Fixed assets | GL engine, depreciation calc | Low | Self-contained module |
| Payroll | HMRC PAYE API credentials | High | Parallel-run beta for 3 months before GA [^593^] |
| Custom reports | Report engine (MVP) | Low | Extends existing pipeline |
| **Phase 4** | | | |
| Multi-entity | GL engine (entity isolation) | Medium | Per-tenant Formance ledgers from MVP |
| Project tracking | Invoicing, time tracking | Low | Builds on existing modules |
| API platform | All existing API endpoints | Low | Formalizes and extends current interfaces |
| Marketplace | API platform, OAuth2 | Low | Depends on API platform release |
| ML reconciliation | Bank feeds + 12 months data | Medium | Bank feeds accumulate data from Month 3 |
| White-label | Multi-tenant architecture | Medium | Schema isolation built incrementally |

**Table 9-8: Technical dependencies and blocker risk by phase — critical path identification and mitigations.**
