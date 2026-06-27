# Headless LLM-Native Small Business Accounting System: Requirements Specification and Phased Implementation Roadmap

## Executive Summary

### System Vision
#### A headless, LLM-native small business accounting system built on Formance Ledger, replacing traditional UI with natural language conversation, targeting 95% Xero feature parity over 15 months with 298 engineering days
#### 216 requirements extracted across 5 categories: 112 functional, 35 non-functional, 38 compliance, 40 technical, 28 UX; 52% classified P0 (critical)

### Key Differentiators
#### Conversational audit trail: every natural language request becomes part of a cryptographically signed chain linking intent, reasoning, and ledger posting
#### Zero-data-entry pipeline: document upload to ledger posting with human approval only on exceptions, targeting 80% auto-processing
#### Compliance-by-design: EU AI Act (August 2026), HMRC MTD, and IFRS 18 (January 2027) compliance architected from day one, not retrofitted

### MVP Definition
#### 8-week MVP delivering single-entity UK VAT-registered small business accounting with 10 core modules, 25+ LLM skills, operated entirely via chat
#### Four complete user flows: first-time setup, daily bookkeeping, month-end reconciliation, VAT return calculation and preview

### Roadmap Summary
#### Four phases over 15 months: MVP (8 weeks) → Automation (M3-5) → Scale (M6-9) → Enterprise (M10-15)
#### Xero feature parity progression: 60% (MVP) → 75% (P2) → 88% (P3) → 95%+ (P4)
#### Engineering effort: 48 days (MVP) + 65 days (P2) + 80 days (P3) + 105 days (P4) = 298 total days, peak team 5-7 engineers

## 1. System Vision and Architectural Principles (~3,500 words, 4 tables)

### 1.1 Problem Domain and Opportunity
#### 1.1.1 Small business accounting market: Xero serves 3.9M subscribers globally with 1,000+ app integrations, yet users spend 8-10 hours monthly on manual bookkeeping tasks that could be conversational
#### 1.1.2 Limitations of legacy systems: complex UI navigation, fragmented workflows, LLM bolted-on as feature rather than core interface, compliance retrofitted rather than architected-in
#### 1.1.3 Headless architecture opportunity: accounting capabilities distributed via MCP to any AI-compatible tool, inverting integration economics

### 1.2 Design Philosophy
#### 1.2.1 Three core principles: Headless-First (no traditional UI, all interaction via LLM), Ledger-Centric (Formance as single source of truth, Numscript as transaction DSL), Compliance-Native (regulatory requirements as architectural constraints)
#### 1.2.2 LLM-native vs LLM-bolted-on: traditional systems add AI as feature; this system uses LLM as primary interface with deterministic validation beneath, mitigating Weber et al. (2025) finding of 8.33% raw double-entry accuracy
#### 1.2.3 Why Formance Ledger: MIT-licensed, ~1,000 tx/s per ledger, Numscript DSL, append-only hash-chained immutable storage, PostgreSQL-backed, production-grade with k8s operator

### 1.3 System Architecture Overview
#### 1.3.1 Five-layer microservices architecture: Client Layer (web, mobile, third-party integrations) → API Gateway (Kong/Traefik) → Application Services (6 services) → Core Ledger (Formance cluster) → Data and Infrastructure (PostgreSQL, Redis, NATS, MinIO)
#### 1.3.2 Supervisor-pattern multi-agent topology: central orchestrator routes to 8 specialist agents (Intake, Categorization, Validation, Posting, Reconciliation, Reporting, Tax, Audit) achieving 89% end-to-end success rate
#### 1.3.3 Communication patterns: REST + WebSocket external, gRPC internal (3-4x faster), NATS for async event streaming (sub-ms latency)
#### 1.3.4 Three primary data flows: chat-to-ledger (6-step synchronous), bank feed processing (async pipeline), report generation (async job queue)

### 1.4 Target Users and Scope
#### 1.4.1 Primary personas: UK-based freelancer/sole trader (1 person, simple transactions), small limited company (2-10 employees, VAT registered), accounting practice managing multiple client entities
#### 1.4.2 In-scope: core GL, invoicing, bank reconciliation, VAT, reporting, document processing, multi-currency, payroll (UK), multi-entity (Phases 1-4)
#### 1.4.3 Out-of-scope (Phase 4+): construction industry scheme (CIS), property management, advanced manufacturing, US/Canadian payroll

## 2. Core Ledger and Data Model (~4,000 words, 6 tables)

### 2.1 Formance Ledger Foundation
#### 2.1.1 Double-entry properties: sum-to-zero enforcement at database constraint level, append-only postings with no UPDATE/DELETE, bi-temporal timestamps (effective_date + recorded_at), idempotency keys, SHA-256 hash chaining
#### 2.1.2 Numscript as transaction DSL: human-readable, machine-parseable, deterministic validation before execution; example `send [GBP/2 10000] from @user:world to @bank:checking`
#### 2.1.3 Throughput and scaling: 1,000 tx/s per ledger (86M+ transactions/day), horizontal scaling via ledger sharding for multi-tenant isolation

### 2.2 Chart of Accounts Architecture
#### 2.2.1 Five-category, 4-digit gap-friendly numbering: Assets (1000-1999), Liabilities (2000-2999), Equity (3000-3999), Revenue (4000-4999), Expenses (5000-6999); max 2-level hierarchy
#### 2.2.2 Eight pre-loaded COA templates: UK Sole Trader (No VAT/VAT), UK Limited Company (No VAT/VAT), UK Partnership (No VAT/VAT), Micro-Entity Simplified, Property/Landlord VAT
#### 2.2.3 Metadata-driven multi-standard support: single COA serves IFRS, US GAAP, UK GAAP simultaneously via presentation-layer mapping; IFRS 18 five-category metadata on each account

### 2.3 Transaction Processing
#### 2.3.1 Transaction data model: Entity 1--* Accounts 1--* Postings *--1 Transactions; status flow Draft → Posted → Reversed; auto-numbering JE-YYYY-NNNN
#### 2.3.2 VAT-aware processing: VAT rate stored as account metadata (20% standard, 5% reduced, 0% zero-rated, exempt); natural language parsing extracts accounts, amounts, VAT splits
#### 2.3.3 50+ pre-built Numscript templates: SALES_INVOICE, PURCHASE_BILL, PAYMENT_OUT, RECEIPT_IN, EXPENSE_CASH, JOURNAL_ENTRY, CURRENCY_EXCHANGE, TAX_SETTLEMENT, PAYROLL_GROSS, and reversal patterns
#### 2.3.4 Three-layer validation: syntax (Numscript parser) → business rules (balance check, COA membership, period lock) → ledger constraints (overdraft, account existence)

### 2.4 Supporting Data Models
#### 2.4.1 Contact management: types Customer/Supplier/Both; fields name, company, email, addresses, VAT number, payment terms; auto-creation from transactions; AR/AP balance tracking
#### 2.4.2 Invoice lifecycle: Draft → Sent → Viewed → Paid → Overdue → Cancelled; post-send immutability on core fields; corrections via credit note + re-issue
#### 2.4.3 Bank account model: multiple accounts per entity; fields account name, sort code, account number, IBAN, currency, opening balance; transaction status Imported → Categorized → Reconciled

## 3. Agentic Interface and LLM Chat (~4,500 words, 8 tables)

### 3.1 Agent Architecture
#### 3.1.1 Supervisor agent: ReAct pattern, GPT-4o-2024-08-06, temperature=0 (deterministic routing), max_iterations=20; responsibilities: intent classification, task decomposition, routing, escalation
#### 3.1.2 Eight specialist agents: Intake (document/transaction ingestion), Categorization (COA classification), Validation (pre-posting checks), Posting (ledger writes), Reconciliation (matching), Reporting (financial reports), Tax (calculations/filings), Audit (anomaly detection)
#### 3.1.3 Agent selection rationale: 89% end-to-end success vs 71% single-agent; 3x cost justified for accounting where errors carry regulatory risk; 18-point improvement from LangGraph production data

### 3.2 Chat Interface
#### 3.2.1 WebSocket protocol at /ws/chat/{session_id}: bidirectional streaming with typed JSON messages (stream_start, stream_token, stream_end, approval_request, error)
#### 3.2.2 Context management: five-layer context (conversation history, user preferences, episodic memory, working state, entity context) with Redis + PostgreSQL + Mem0 persistence
#### 3.2.3 Natural language capabilities: date parsing ("last month", "Q2 2025"), ambiguity resolution, multi-turn workflows, error recovery with explanation, 3 persona options

### 3.3 Human-in-the-Loop Framework
#### 3.3.1 Graduated autonomy model: Phase 1 (Weeks 1-4): 100% approval; Phase 2 (Weeks 5-12): 20% sampled; Phase 3 (Months 3-6): exception-only; Phase 4 (Months 6+): full autonomy with policy triggers
#### 3.3.2 Approval decision matrix: post journal entry → finance manager + accountant; delete entry → dual approval; tax filing submission → controller + external review; generate report → exception-only
#### 3.3.3 Four approval workflow patterns: action-level gate, draft approval, dual approval, exception-only with policy triggers

### 3.4 SKILL Registry
#### 3.4.1 OpenClaw SKILL.md format: YAML frontmatter + markdown instructions; discoverable via vector search; versioned with loading precedence (workspace > user > bundled)
#### 3.4.2 Security model (post-ClawHavoc): SHA-256 + VirusTotal scan on upload, daily rescanning, cryptographic signing, Docker sandboxing, least-privilege, deny-by-default network egress
#### 3.4.3 Skill growth trajectory: 25+ (MVP) → 65+ (P2) → 120+ (P3) → 190+ (P4)

### 3.5 Safety and Reliability
#### 3.5.1 Five-layer input validation: syntax, semantic, authorization, content safety, business rules; five-layer output validation: schema, accounting rules, balance check, duplicate check, anomaly detection
#### 3.5.2 Error taxonomy: hard failures (retry with backoff), structural failures (retry with clearer instructions), semantic failures (human review); four degradation levels: full → cached → restricted → human-only
#### 3.5.3 EU AI Act compliance: high-risk classification (Annex III, Section 5b), Article 12 automatic logging, Article 14 human oversight, August 2026 full obligations deadline

## 4. Financial Reporting SKILLs (~4,000 words, 8 tables)

### 4.1 Report Engine Architecture
#### 4.1.1 Five-stage pipeline: Parameter Ingestion → Query Layer Execution → Data Model Transformation → Rule Application → Output Formatting; all reports deterministic with JSON schemas
#### 4.1.2 Framework parameterization: single SKILL produces GAAP or IFRS output via `framework` parameter; rule bundles define classification mapping, line ordering, subtotals, disclosure requirements

### 4.2 Core Financial Statement SKILLs
#### 4.2.1 P&L Statement (core.pl): IFRS 18 five-category structure (Operating, Investing, Financing, Income Taxes, Discontinued Operations) with mandatory subtotals; effective January 2027
#### 4.2.2 Balance Sheet (core.bs): Assets = Liabilities + Equity; current/non-current split; three format options (standard, IFRS 18, comparative)
#### 4.2.3 Cash Flow Statement (core.cf): direct and indirect method per IAS 7; IFRS 18 changes: indirect starts from Operating Profit, interest paid → Financing
#### 4.2.4 Trial Balance (core.tb): unadjusted, adjusted, and post-closing variants; verification that debits equal credits

### 4.3 Management and Tax Report SKILLs
#### 4.3.1 Management reports: Aged AR/AP with 30-60-90-90+ buckets and DSO/DPO metrics; GL Detail/Summary; Executive Summary combining P&L highlights, balance sheet snapshot, KPIs
#### 4.3.2 Tax reports: UK VAT 9-box (tax.vat_uk) with MTD compliance; Australian BAS; generic GST; US/Canada sales tax by jurisdiction; corporation tax computation
#### 4.3.3 Complete SKILL catalog: 33+ reports across 7 categories (Core Statements, Internal Verification, Management, Tax, Variance, KPI, Audit)

### 4.4 Output and Distribution
#### 4.4.1 Six output formats: JSON (API), HTML (web), PDF (document), CSV (spreadsheet), XBRL (machine-readable regulatory), iXBRL (human + machine readable)
#### 4.4.2 Report scheduling: time-based (daily/weekly/monthly/quarterly), event-driven (period close, threshold breach), data-driven (burn rate exceeds threshold)
#### 4.4.3 XBRL/iXBRL layer: UK mandate April 2028 for software-only iXBRL filing; taxonomy mapping; 6-stage generation pipeline with validation

## 5. Multi-Currency, Multi-Standard and Tax Engine (~4,500 words, 10 tables)

### 5.1 Multi-Currency Architecture
#### 5.1.1 Three-currency model per IAS 21: functional currency (primary economic environment), transaction currency (invoice/payment denomination), presentation currency (reporting)
#### 5.1.2 Exchange rate management: multi-provider architecture (ECB free → XE premium → OXR mid-tier) with circuit breaker failover; daily automatic updates
#### 5.1.3 FX gain/loss handling: realized at settlement date; unrealized at period-end revaluation for monetary items; cumulative translation adjustment in OCI
#### 5.1.4 150+ ISO 4217 currencies; Phase 3 implementation with automatic revaluation journal generation

### 5.2 Tax Engine Architecture
#### 5.2.1 Three-layer configurable architecture: Rule Store (structured repository with effective dates, priorities, statutory references) → Execution Engine (runtime rules interpreter) → Override Workflow (approval with segregation of duties)
#### 5.2.2 Five tax types: VAT (credit-invoice, 20% UK), GST (Australia 10%, NZ 15%, Canada 5%), US Sales Tax (45 states, economic nexus), Withholding Tax (dividends 0-30%, interest 0-25%), Digital Services Tax (UK 2%, France 3%)
#### 5.2.3 Place of supply engine: 6-step pipeline per OECD Guidelines — identify supply category, party types (B2B/B2C), customer location, apply specific rules, apply general rules, validate evidence

### 5.3 VAT/GST Returns and Digital Submission
#### 5.3.1 UK VAT 9-box return: Boxes 1-9 with auto-calculation, MTD compliance, digital link chain evidence; 6-year record retention
#### 5.3.2 HMRC MTD API integration: OAuth 2.0 authentication, fraud prevention headers (Gov-Client-Connection-Method, Public-IP, Device-ID), digital linking rules
#### 5.3.3 EU OSS: single registration, quarterly filing, EUR 10,000 threshold for intra-EU B2C supplies; no input tax deduction through OSS
#### 5.3.4 Registration threshold monitoring: global thresholds with 4-tier alert engine (Green <50%, Amber 50-79%, Orange 80-99%, Red 100%+)

### 5.4 Accounting Standards Compliance
#### 5.4.1 GAAP and IFRS support: dual framework capability with metadata-driven presentation switching; IFRS for SMEs as default for small businesses
#### 5.4.2 Key GAAP-IFRS differences handled: inventory valuation (LIFO prohibited under IFRS), lease classification, revenue recognition timing, extraordinary items, cash flow presentation
#### 5.4.3 IFRS 18 readiness: five-category P&L structure, Management Performance Measures (MPMs) with mandatory reconciliation; effective January 2027

## 6. Document Processing and Workflow Automation (~3,500 words, 6 tables)

### 6.1 Document Ingestion and Extraction
#### 6.1.1 Document types: supplier invoices/bills, receipts, bank statements, credit notes; upload via API, email, or mobile capture
#### 6.1.2 Extraction pipeline: Upload → Preprocessing (deskew, enhance) → OCR (Tesseract/DocTR) → LLM Extraction (GPT-4o Vision) → Validation Rules → Structured Output
#### 6.1.3 Key metrics: OCR accuracy 92-95%, end-to-end extraction 95-97%, 80% human intervention reduction; low-confidence (<90%) flagged for human review
#### 6.1.4 Validation rules: amount consistency (line items = subtotal = total - VAT), date validation, VAT calculation verification, duplicate detection

### 6.2 Bank Feed Integration
#### 6.2.1 Aggregator strategy: TrueLayer (primary UK), Plaid (secondary), Salt Edge (tertiary EU), Yodlee (fallback); Open Banking PSD2 with Strong Customer Authentication
#### 6.2.2 Features: daily polling, 12-24 month historical backfill, multi-bank, automatic deduplication, real-time webhooks, connection health monitoring
#### 6.2.3 Bank rules engine: Xero-style auto-categorization; conditions (description contains/equals/regex, amount between/equals); execution modes (suggest/auto-apply/disabled); 50+ pre-built patterns

### 6.3 Reconciliation
#### 6.3.1 Manual reconciliation (MVP): side-by-side matching; one-to-one and one-to-many; partial matching with amount difference explanation; 6-step workflow
#### 6.3.2 ML-powered reconciliation (Phase 4): per-organization Random Forest model; 4-layer architecture (Rule → Match → Memory → Prediction); target 80%+ auto-reconcile, 97%+ accuracy

### 6.4 Recurring Transactions and Approvals
#### 6.4.1 Recurring transactions: templates with schedules (weekly/bi-weekly/monthly/quarterly/annual); end conditions (never/after N/until date); auto-post or draft-for-review
#### 6.4.2 Recurring invoices: template + schedule, auto-send, Stripe/GoCardless integration, failed payment retry (3 attempts)
#### 6.4.3 Approval workflows: threshold-based routing (<GBP 500 auto, 500-2000 manager, >2000 director); delegation during absence; reminder escalation

## 7. Security, Compliance and Audit Trail (~3,500 words, 6 tables)

### 7.1 Security Architecture
#### 7.1.1 Authentication: OAuth 2.0 + PKCE (RFC 9700); JWT access tokens (RS256, 30-min expiry); rotating refresh tokens (60-day); optional mTLS for server-to-server
#### 7.1.2 RBAC: five roles (Owner, Admin, Bookkeeper, Accountant, Viewer); middleware-enforced claim validation
#### 7.1.3 Data encryption: TLS 1.3 in transit, mTLS internal gRPC; PostgreSQL TDE + LUKS at rest; MinIO AES-256 for files; application-level AES-256-GCM for sensitive fields
#### 7.1.4 Multi-tenant isolation: per-tenant Formance ledgers + PostgreSQL schema buckets + RLS policies; per-tenant MinIO buckets; key-prefixed Redis cache

### 7.2 Immutable Audit Trail
#### 7.2.1 Formance hash-chained ledger: SHA-256 chaining, no UPDATE/DELETE on postings, corrections via compensating reversing entries, WORM storage option
#### 7.2.2 Conversational audit trail: every NL request → LLM reasoning trace → generated Numscript → human approval decision → final ledger posting, all cryptographically linked and timestamped
#### 7.2.3 Agent decision provenance: prompt hash, context, chain-of-thought, confidence scores, tool calls, validation results, human override; 6+ year retention per EU AI Act Article 12

### 7.3 Regulatory Compliance
#### 7.3.1 EU AI Act: high-risk system classification (Annex III, Section 5b); Article-by-article implementation (Art. 9 risk management, Art. 12 logging, Art. 13 transparency, Art. 14 human oversight, Art. 15 accuracy); August 2026 deadline
#### 7.3.2 GDPR: pseudonymization with managed keys (erasure = key destruction, preserving financial integrity); data export capability; consent management; 30-day DSAR SLA
#### 7.3.3 SOC 2 alignment: all 5 Trust Services Criteria (Security, Availability, Processing Integrity, Confidentiality, Privacy); continuous monitoring
#### 7.3.4 HMRC MTD compliance roadmap: MVP (digital records, 9-box preview) → Phase 2 (API submission) → Phase 3 (multi-scheme) → Phase 4 (group VAT, partial exemption)

## 8. MVP Requirements Specification (~5,000 words, 10 tables)

### 8.1 MVP Scope and Success Criteria
#### 8.1.1 Target: single-entity UK VAT-registered small business (freelancer, sole trader, or limited company, 0-10 employees, single currency GBP); operated entirely via natural language chat
#### 8.1.2 Success criteria: complete bookkeeping cycle via chat (record transactions → create invoice → import bank statement → reconcile → run VAT return → generate P&L and Balance Sheet); all data passes double-entry validation
#### 8.1.3 Timeline: 8 weeks, 48 engineering days, 2-3 engineer team

### 8.2 MVP Module Specifications
#### 8.2.1 Module 1 Chart of Accounts (3 days): 8 pre-loaded templates, 5-category 4-digit numbering, 9 account types, VAT rate assignment, LLM skills: coa.list, coa.add_account, coa.edit_account, coa.set_vat_rate
#### 8.2.2 Module 2 Core General Ledger (10 days): NL to structured transaction parsing, Numscript modeling, multi-line splits, VAT-inclusive/exclusive, JE-YYYY-NNNN numbering, Draft/Posted/Reversed status
#### 8.2.3 Module 3 Contact Management (3 days): Customer/Supplier/Both types, auto-creation from transactions, duplicate detection, AR/AP balance tracking
#### 8.2.4 Module 4 Bank Statement Import (5 days): CSV with column mapping, OFX parsing (1.02, 2.1, 2.2), 7 pre-built bank templates, duplicate detection
#### 8.2.5 Module 5 Manual Bank Reconciliation (5 days): side-by-side matching, one-to-one/one-to-many, partial matching, reconciliation report
#### 8.2.6 Module 6 Basic Invoicing (6 days): line items with VAT, Draft/Sent/Viewed/Paid/Overdue/Cancelled lifecycle, PDF generation, email delivery, credit notes
#### 8.2.7 Module 7 VAT Calculation and MTD Preview (5 days): automatic VAT tracking, UK 9-box calculation, flat rate/accrual/cash schemes, MTD preview (not submission)
#### 8.2.8 Module 8 Core Financial Reports (5 days): P&L, Balance Sheet, Trial Balance, Aged AR, Aged AP with 5-stage report engine
#### 8.2.9 Module 9 LLM Chat Interface (10 days): conversational transaction entry, context memory, intent routing, multi-turn workflows, natural date parsing, 3 personas
#### 8.2.10 Module 10 Authentication and Security (3 days): JWT-based auth, API keys, HTTPS/TLS, database encryption, row-level audit logging

### 8.3 MVP Quality Gates
#### 8.3.1 Double-entry validation on every transaction; COA membership validation; period open check; unique reference enforcement; amount bounds checking; VAT calculation verification
#### 8.3.2 All write operations require explicit confirmation; 25+ registered LLM skills; four complete user flows validated end-to-end

## 9. Phased Implementation Roadmap (~4,500 words, 8 tables)

### 9.1 Roadmap Overview
#### 9.1.1 15-month journey: MVP (8 weeks, 48 days) → Phase 2 Automation (M3-5, 65 days) → Phase 3 Scale (M6-9, 80 days) → Phase 4 Enterprise (M10-15, 105 days); total 298 days, peak team 5-7
#### 9.1.2 Xero parity progression: 60% (MVP) → 75% (P2) → 88% (P3) → 95%+ (P4)
#### 9.1.3 Skill growth: 25+ (MVP) → 65+ (P2) → 120+ (P3) → 190+ (P4)

### 9.2 Phase 2: Automation (Months 3-5)
#### 9.2.1 Month 3: bank feed integration (TrueLayer + Plaid, Open Banking PSD2), bank rules engine (50+ patterns), recurring transactions
#### 9.2.2 Month 4: recurring invoices (auto-send, Stripe/GoCardless), document upload + OCR extraction (95-97% accuracy), multi-user support (5 roles)
#### 9.2.3 Month 5: approval workflows (threshold-based, 1-3 levels), HMRC MTD VAT submission (OAuth, fraud headers), 65+ total skills

### 9.3 Phase 3: Scale (Months 6-9)
#### 9.3.1 Month 6: multi-currency (150+, IAS 21 compliant, FX gain/loss), multi-tax jurisdictions (VAT/GST/Sales Tax, place of supply engine)
#### 9.3.2 Month 7: inventory/stock tracking (FIFO, COGS, purchase orders), fixed asset register (straight-line/diminishing value depreciation)
#### 9.3.3 Month 8: UK payroll with RTI (FPS/EPS, PAYE, NICs, pension auto-enrolment), advanced report library (15+ additional reports)
#### 9.3.4 Month 9: custom report builder (drag-and-drop API), purchase orders/bills (3-way matching), tracking categories (department/project/region), 120+ total skills

### 9.4 Phase 4: Enterprise (Months 10-15)
#### 9.4.1 Multi-entity management: intercompany elimination, consolidated reporting, shared services allocation, cumulative translation adjustments
#### 9.4.2 Project tracking: time tracking, job costing, project profitability
#### 9.4.3 API platform: OpenAPI 3.0, webhooks (10+ events), SDKs in 5 languages, sandbox, developer portal
#### 9.4.4 App marketplace: 30+ pre-built integrations across 8 categories; ML-powered reconciliation (per-org Random Forest, 97%+ accuracy)
#### 9.4.5 White-label and industry modules: embedded accounting, CIS, property, SaaS metrics, practice management; 190+ total skills

### 9.5 Compliance and Technical Milestones
#### 9.5.1 UK compliance timeline: MTD VAT (MVP preview → P2 submission → P3 multi-scheme → P4 group VAT); RTI payroll (P3); Companies House iXBRL (P4, mandatory April 2028)
#### 9.5.2 International expansion: EU VAT OSS (P3), US Sales Tax (P3), Australia GST (P3)
#### 9.5.3 Critical deadlines: EU AI Act August 2026 (P3), IFRS 18 January 2027 (P3/P4), Companies House digital filing April 2028 (P4)

## 10. Risk Assessment and Mitigation (~2,500 words, 4 tables)

### 10.1 Risk Register
#### 10.1.1 Technical risks: LLM hallucination (medium likelihood, high impact → template-based generation, deterministic validation, confirmation gates); Formance integration complexity (low → comprehensive testing, fallback strategies)
#### 10.1.2 Compliance risks: EU AI Act interpretation uncertainty (medium → legal review, modular compliance architecture); IFRS 18 timeline (medium → metadata-driven presentation layer)
#### 10.1.3 Business risks: user adoption (medium → graduated UX autonomy, familiar accounting concepts); resource constraints (medium → phased approach, 8-week MVP validation)
#### 10.1.4 External risks: HMRC API changes (medium → adapter pattern, abstraction layer); Open Banking aggregator downtime (medium → multi-aggregator failover); exchange rate API failure (low → cached rates, manual override)

### 10.2 Coverage Gaps and Resolutions
#### 10.2.1 Ten identified coverage gaps: production load testing, disaster recovery, HMRC MTD deep integration, LLM cost modeling, payroll deep design, migration tooling, mobile architecture, ops tooling, multi-tenant isolation at scale, pricing strategy
#### 10.2.2 Resolution approach: address highest-severity gaps (production testing, DR) in Phase 2; medium gaps in Phase 3; remaining in Phase 4

### 10.3 Architectural Consistency Assessment
#### 10.3.1 Overall consistency score: 87/100; highest scores in backend technology (95) and data model (92); lowest in cost/business model (55) and DevOps/deployment (75)

# References

## accounting_system_requirements_outline_references_raw.md
- **Type**: Requirements extraction
- **Description**: 216 requirements across 5 categories with priorities
- **Path**: /mnt/agents/output/accounting_system_requirements_outline_references_raw.md

## accounting_system_artifact_synthesis.md
- **Type**: Research synthesis
- **Description**: Thematic synthesis of 18 research dimension files
- **Path**: /mnt/agents/output/accounting_system_artifact_synthesis.md

## accounting_system_structure.md
- **Type**: Structure design
- **Description**: Chapter hierarchy with word counts and required elements
- **Path**: /mnt/agents/output/accounting_system_structure.md

## accounting_system_content_plan.md
- **Type**: Content plan
- **Description**: H4-level content points, tables, diagrams per chapter
- **Path**: /mnt/agents/output/accounting_system_content_plan.md

## Research Dimension Files
- **Type**: Deep research
- **Description**: 18 research files (wide01-06, dim01-12) at /mnt/agents/output/research/
- **Path**: /mnt/agents/output/research/accounting_system_*.md
