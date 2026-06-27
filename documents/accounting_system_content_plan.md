# Content Plan: Headless LLM-Native Small Business Accounting System
## Requirements Document - Chapter-by-Chapter Writing Guide

**Document Version:** 1.0
**Date:** 2025-07-15
**Status:** Ready for Writing

---

## How to Use This Plan

Each chapter entry contains:
- **Content Points**: H4-level writing instructions. Numbered for traceability.
- **Tables**: Required data tables with column specifications.
- **Diagrams**: Required visual elements with type and content description.
- **Citations**: Source references from research files that must be included.
- **Word Count Target**: Approximate length guidance.

**Source File Key:**
- dim01 = System Architecture
- dim05 = Tax Engine
- dim08 = Financial Reporting
- dim09 = Agentic Workflow
- dim12 = MVP & Roadmap
- cross = Cross-Verification Report
- insight = Strategic Insights

---

# Chapter 1: Executive Summary
**Word Count Target:** 1,200-1,500 words

## Content Points

1.1. **System Definition.** One-paragraph definition of the system: a headless, LLM-native small business accounting system built on Formance Ledger, operated entirely through natural language conversation, targeting UK SMEs initially with global expansion capability.

1.2. **Problem Statement.** Current accounting software (Xero, QuickBooks, Sage) requires manual navigation of complex UIs, extensive data entry, and fragmented workflows. Small business owners spend 8-10 hours per month on bookkeeping tasks that could be conversational.

1.3. **Solution Approach.** The system replaces the traditional UI with an LLM conversational interface backed by a supervisor-pattern multi-agent architecture. Every accounting function -- transaction entry, invoicing, reconciliation, reporting, tax filing -- is exposed as a natural language SKILL with deterministic execution.

1.4. **Key Differentiators (5).**
  - Conversational audit trail: every natural language request becomes part of a cryptographic chain
  - Zero-data-entry document pipeline: document upload to ledger posting with human approval only on exceptions
  - Compliance-by-design: EU AI Act, HMRC MTD, and IFRS 18 compliance architected in from day one
  - Headless + MCP distribution: accounting becomes infrastructure embeddable in any AI-compatible tool
  - Metadata-driven multi-standard COA: single chart serves IFRS, US GAAP, UK GAAP simultaneously

1.5. **Architecture Summary.** Five-layer architecture (Client, API Gateway, Application Services, Core Ledger, Data & Infrastructure) built on Formance Ledger with PostgreSQL, NATS event streaming, and Redis caching.

1.6. **MVP Scope Summary.** 8-week MVP delivering single-entity UK VAT-registered small business accounting with 10 core modules, 25+ LLM skills, operated entirely via chat.

1.7. **Roadmap Summary.** 15-month phased roadmap from MVP (8 weeks) through Phase 2 Automation (Months 3-5), Phase 3 Scale (Months 6-9), to Phase 4 Enterprise (Months 10-15), achieving Xero-class feature parity at 95%+.

1.8. **Confidence Assessment.** Cross-verification across 18 research dimensions yielded 10 high-confidence findings, 4 medium-confidence findings, 5 identified risks with mitigations, and 7 coverage gaps requiring follow-up research.

1.9. **Strategic Insights Summary.** Reference the 14 cross-dimensional insights organized into: Competitive Differentiation (4), Architectural Elegance (3), Compliance Synergies (4), and Risk & Timing (3).

1.10. **Investment Ask.** Engineering effort: 298 days over 15 months, peak team 5-7 engineers. Present as a focused, high-conviction build.

## Required Tables

| Table # | Title | Columns |
|---------|-------|---------|
| T1-1 | Confidence Tier Summary | Finding, Tier (High/Med/Low/Conflict/Gap), Confirming Dimensions, Action Required |
| T1-2 | Phased Feature Progression | Phase, Duration, New Features, Cumulative Skills, Xero Parity % |
| T1-3 | Engineering Effort Summary | Phase, Effort (days), Team Size, Calendar Time |
| T1-4 | Top 10 High-Confidence Architectural Decisions | Decision, Confirming Sources, Contradictions, Mitigation |

## Required Diagrams

| Diagram # | Type | Description |
|-----------|------|-------------|
| D1-1 | Layered architecture block diagram | 5-layer architecture with key technologies labeled per layer |
| D1-2 | Timeline/Gantt chart | 15-month roadmap with 4 phases, key milestones, and compliance deadlines (EU AI Act Aug 2026, IFRS 18 Jan 2027) |

## Key Citations
- dim12: 8-week MVP scope, 48 engineering days, 2-3 engineer team
- dim12: 298 total engineering days, 15-month timeline
- dim12: Xero feature parity progression 60%->95%+
- cross: 10 high-confidence findings, 5 conflict zones, 7 coverage gaps
- insight: 14 strategic insights across 4 categories
- insight: Competitive moat analysis (conversational audit trail, per-org ML, headless+MCP, touchless entry)

---

# Chapter 2: System Vision & Architectural Principles
**Word Count Target:** 3,000-3,500 words

## Content Points

2.1. **Design Philosophy.** The system is built on three core principles: (a) Headless-First -- no traditional UI, all interaction via LLM conversation; (b) Ledger-Centric -- Formance Ledger is the single source of truth with Numscript as the transaction DSL; (c) Compliance-Native -- regulatory requirements are architectural constraints, not add-ons.

2.2. **Why Headless.** Headless architecture inverts integration economics: instead of users coming to accounting software, accounting capabilities go to users wherever they work (Slack, Teams, WhatsApp, CRM dashboards). MCP compatibility means any AI client can consume accounting functions without bespoke integrations. Reference Xero's API-first strategy yielding 80%+ revenue growth and 1M+ connected applications.

2.3. **Why Formance Ledger.** MIT-licensed, ~1,000 tx/s per ledger, Numscript DSL, append-only hash-chained immutable storage, PostgreSQL-backed, production-grade with k8s operator. Comparison with alternatives: Modern Treasury (closed-source), TigerBeetle (no DSL), Fragment (enterprise-focused).

2.4. **Why LLM-Native (Not LLM-Bolted-On).** Traditional accounting software adds AI as a feature. This system uses LLM as the primary interface layer with deterministic validation layers beneath. The LLM translates natural language to structured Numscript; validation layers ensure accounting correctness. This mitigates the Weber et al. (2025) finding of 8.33% raw double-entry accuracy through template-based generation (+40% accuracy) and deterministic validation.

2.5. **Multi-Agent Architecture.** Supervisor pattern with 8 specialist agents: Intake, Categorization, Validation, Posting, Reconciliation, Reporting, Tax, Audit. 89% end-to-end success rate vs 71% single-agent. Temperature=0 for deterministic routing. Cost: ~3x single-agent ($0.061 vs $0.022 per task) justified for accounting where errors carry regulatory risk.

2.6. **Service Topology.** Five-layer architecture:
  - Layer 1 (Client): Web App, Mobile App, Third-Party Integrations
  - Layer 2 (API Gateway): Kong/Traefik -- REST routing, WebSocket handling, OAuth, rate limiting (60 calls/min/tenant)
  - Layer 3 (Application Services): Agent Orchestrator (Supervisor), Accounting Service, Bank Feed Service, Reporting Service, Notification Service, Skill Registry
  - Layer 4 (Core Ledger): Formance Ledger Cluster -- Ledger API, Numscript Engine, Event Publisher
  - Layer 5 (Data & Infrastructure): PostgreSQL, Redis, NATS/Kafka, MinIO

2.7. **Communication Patterns.** External: REST API (/api/v1/*), WebSocket (/ws/chat for LLM streaming), Webhooks (/webhooks/*). Internal: gRPC between app services (3-4x faster than REST), NATS for async event streaming (sub-ms latency), REST for Formance Ledger integration via official TypeScript SDK.

2.8. **Data Flow -- Primary Flow (Chat to Ledger).** 6-step walkthrough: (1) WebSocket connection with JWT auth, (2) Intent classification by Supervisor, (3) Skill execution by specialist agent with Numscript template, (4) Ledger write via Formance API, (5) Event propagation via NATS to downstream services, (6) Streaming response to user.

2.9. **Data Flow -- Secondary Flow (Bank Feed Processing).** Async pipeline: Scheduler triggers -> Bank Feed Importer fetches -> Categorize + Match (ML + rules) -> Formance Ledger write -> Reconcile matched transactions -> Emit events.

2.10. **Data Flow -- Tertiary Flow (Report Generation).** Async pipeline: User request -> reporting-service validates permissions -> enqueues job -> worker queries Formance -> calculates in Python/Pandas -> generates PDF/Excel -> stores in MinIO -> emits completion event -> email notification.

2.11. **Database Strategy.** PostgreSQL 16+ for both Formance Ledger storage (per-tenant schema/bucket isolation) and application metadata. Redis for session cache (24h TTL), rate limiting (1-min TTL), balance cache (30s TTL), report cache (1h TTL). PGVector for skill embeddings with HNSW index. MinIO for S3-compatible document storage.

2.12. **API Design.** REST API following Xero-inspired patterns: OAuth 2.0 + PKCE, cursor-based pagination, BigInt-as-String header, idempotency keys on all POST/PUT. WebSocket chat API with typed JSON protocol (stream_start, stream_token, stream_end, approval_request, error). gRPC internal APIs for AccountingService, AgentService, BankFeedService, ReportService.

2.13. **Deployment Model.** Development: Docker Compose with full stack. Production: Kubernetes with Formance Operator, Patroni HA PostgreSQL (1 primary + 2 replicas), Redis Cluster (6-node), NATS JetStream (3-node), MinIO distributed (4+ nodes). HPA for all application services.

2.14. **Performance Targets.** Ledger write: 1,000 tx/s per ledger. API p99: <200ms. LLM streaming start: <3 seconds. Report generation: <30s for quarterly. System availability: 99.9%.

## Required Tables

| Table # | Title | Columns |
|---------|-------|---------|
| T2-1 | Service Definitions | Service Name, Technology, Role, Key Functions, Protocols |
| T2-2 | Inter-Service Communication Matrix | Source, Destination, Protocol, Pattern, Purpose |
| T2-3 | Technology Stack Summary | Category, Technology, Version, License, Rationale |
| T2-4 | Data Store Overview | Store, Technology, Purpose, Persistence Model |
| T2-5 | Redis Cache Strategy | Cache Type, Key Pattern, TTL, Purpose |
| T2-6 | API Endpoint Groups | Endpoint Group, Methods, Description |
| T2-7 | Performance Targets | Metric, Target, Basis/Source |
| T2-8 | Capacity Planning by Tenant Tier | Tier, Tx/Month, Ledger Design, PostgreSQL Config |
| T2-9 | Multi-Tenant Data Isolation | Isolation Level, Mechanism |

## Required Diagrams

| Diagram # | Type | Description |
|-----------|------|-------------|
| D2-1 | 5-layer block diagram | Full service topology with all services labeled and inter-layer connections |
| D2-2 | Sequence diagram | Primary chat-to-ledger data flow (6 steps) |
| D2-3 | Pipeline diagram | Bank feed processing async pipeline |
| D2-4 | Pipeline diagram | Report generation async pipeline |
| D2-5 | Deployment diagram | Kubernetes production architecture with replica counts and resource classes |
| D2-6 | Cache hierarchy diagram | L1 (in-memory) -> L2 (Redis) -> L3 (CDN) with TTL annotations |
| D2-7 | WebSocket message flow | Client <-> Server message types and sequence |

## Key Citations
- dim01: Full 5-layer architecture, service topology, communication patterns
- dim01: Database strategy, PostgreSQL for Formance, Redis caching
- dim01: API design (REST + WebSocket + gRPC), endpoint groups
- dim01: Kubernetes deployment model, Formance Operator
- dim01: Performance targets (1,000 tx/s, 200ms p99)
- dim09: Supervisor pattern, 8 specialist agents, 89% vs 71% success rate
- insight: Headless + MCP inverts integration economics
- insight: Reactive ledger eliminates batch processing

---

# Chapter 3: Core Ledger & Data Model
**Word Count Target:** 3,500-4,000 words

## Content Points

3.1. **Ledger Foundation.** Formance Ledger as the programmable double-entry ledger. Key properties: sum-to-zero enforcement at database constraint level, append-only postings (no UPDATE/DELETE -- corrections via reversing entries), bi-temporal timestamps (effective_date + recorded_at), idempotency keys on every write, hash-chained immutability.

3.2. **Numscript as Transaction DSL.** Numscript is a declarative domain-specific language for financial transactions. LLM-friendly syntax: `send [GBP/2 10000] from @user:world to @bank:checking`. Benefits: human-readable, machine-parseable, deterministic validation before execution, compensating transactions for corrections. 50+ pre-built templates (SALES_INVOICE, PAYMENT_OUT, PAYROLL_GROSS, etc.).

3.3. **Chart of Accounts Architecture.** Standard 5-category, 4-digit numbering: Assets (1000-1999), Liabilities (2000-2999), Equity (3000-3999), Revenue (4000-4999), Expenses (5000-6999). Gaps of 10 between account codes for future insertion. Max 2-level parent-child hierarchy. Each account maps to Formance address: `gl:{account_code}:{entity_id}`.

3.4. **COA Templates (8 Variants).** Pre-loaded templates for:
  - UK Sole Trader -- No VAT (40 accounts)
  - UK Sole Trader -- VAT Registered (55 accounts)
  - UK Limited Company -- No VAT (50 accounts)
  - UK Limited Company -- VAT Registered (65 accounts)
  - UK Partnership -- No VAT (45 accounts)
  - UK Partnership -- VAT Registered (60 accounts)
  - Micro-Entity Simplified (30 accounts)
  - Property/Landlord -- VAT Registered (45 accounts)

3.5. **Entity Data Model.** Core relationships: Entity 1--* Accounts 1--* Postings *--1 Transactions. Entity 1--* Contacts 1--* Invoices 1--* InvoiceLines. Entity 1--* BankAccounts 1--* BankTransactions. Transactions *--* BankTransactions (reconciliation_matches).

3.6. **Transaction Data Model.** Tables: transaction (id, date, description, reference, contact_id, total_amount, currency, status, metadata, created_at), posting (id, transaction_id, account_id, debit_amount, credit_amount, description), vat_line (id, posting_id, vat_rate, vat_amount, net_amount, vat_type). Transaction status: Draft -> Posted -> Reversed.

3.7. **Double-Entry Validation.** Database-level constraint: total debits = total credits on every transaction. Numscript sum-to-zero enforcement at storage level. Validation Agent pre-posting checklist: debits=credits, COA membership, period open, entity match, unique reference, amount bounds, currency validity.

3.8. **VAT-Aware Transaction Processing.** VAT rate stored as account metadata (20% standard, 5% reduced, 0% zero-rated, exempt). Applied automatically on transaction entry. Natural language parsing: "Paid GBP 120 to Acme for marketing plus VAT" -> parsed with accounts, amounts, VAT split (GBP 100 net + GBP 20 VAT).

3.9. **Journal Entry Numbering.** Auto-sequential format: JE-YYYY-NNNN. Idempotency key: client-generated UUID on every write. Bi-temporal: effective_date (when event occurred) and recorded_at (when system recorded).

3.10. **Invoice Lifecycle.** Status flow: Draft -> Sent -> Viewed -> Paid -> Overdue -> Cancelled. After invoice is SENT, core fields (customer, line items, amounts, VAT) become immutable. Corrections require credit note + re-issue workflow. Payment reconciliation is safe post-send operation.

3.11. **Contact Management.** Types: Customer, Supplier, Both. Fields: name, company, email, phone, billing/shipping address, VAT number, payment terms (Net 30 default), default account. Auto-creation from transaction descriptions. Duplicate detection by name/email/VAT. AR/AP balance tracking.

3.12. **Bank Account Model.** Fields: account name, sort code, account number, IBAN, currency, opening balance, current balance. Multiple bank accounts per entity. Transaction status: Imported -> Categorized -> Reconciled.

3.13. **COA-IFRS 18 Mapping.** Metadata-driven approach: add IFRS 18 category metadata to all COA accounts. Five IFRS 18 categories map to accounts: Operating (default), Investing, Financing, Income Taxes, Discontinued Operations. Same COA serves traditional and IFRS 18 reporting via presentation-layer mapping.

## Required Tables

| Table # | Title | Columns |
|---------|-------|---------|
| T3-1 | 5-Category COA Numbering Scheme | Category, Code Range, Account Types, Example Accounts |
| T3-2 | COA Template Comparison | Template Name, Target Entity, Account Count, VAT Status, Key Differentiators |
| T3-3 | Transaction Data Model | Table, Columns, Constraints, Relationships |
| T3-4 | VAT Rate Configuration | Rate Type, Percentage, Applicable Categories, Use Cases |
| T3-5 | Invoice Status Lifecycle | Status, Description, Immutable Fields, Allowed Transitions |
| T3-6 | Contact Fields & Validation | Field, Type, Required, Validation Rules |
| T3-7 | Pre-built Numscript Templates | Template ID, Transaction Type, Description, Key Variables |
| T3-8 | Double-Entry Validation Rules | Rule, Check Type, Action on Failure, Severity |
| T3-9 | IFRS 18 Category Mapping | IFRS 18 Category, COA Account Types, Example Accounts |

## Required Diagrams

| Diagram # | Type | Description |
|-----------|------|-------------|
| D3-1 | ER diagram | Core data model: Entity, Accounts, Transactions, Postings, Contacts, Invoices, BankAccounts |
| D3-2 | State machine diagram | Invoice lifecycle: Draft->Sent->Viewed->Paid->Overdue->Cancelled |
| D3-3 | State machine diagram | Transaction status: Draft->Posted->Reversed |
| D3-4 | Hierarchy diagram | COA 5-category structure with example accounts |
| D3-5 | Flow diagram | Numscript generation pipeline: NL -> LLM -> Template -> Validation -> Ledger |
| D3-6 | Account address mapping | How COA accounts map to Formance ledger addresses |

## Key Citations
- dim12: COA templates (8 variants), account numbering, VAT assignment
- dim12: Transaction data model, posting model, VAT line model
- dim12: Invoice lifecycle, immutability rules, credit note workflow
- dim12: Bank account model, reconciliation status flow
- dim01: Formance Ledger integration, Numscript, bucket isolation
- cross: 4-digit gap-friendly COA (high confidence), immutable append-only ledger
- insight: Metadata-driven COA eliminates parallel books

---

# Chapter 4: Agentic Interface & LLM Chat
**Word Count Target:** 4,000-4,500 words

## Content Points

4.1. **Architecture Overview.** WebSocket-based bidirectional chat as the sole user interface. Supervisor agent routes user requests to 8 specialist agents. Each agent handles a discrete accounting domain. Streaming responses for real-time conversational feel. Session management with persistent history.

4.2. **Supervisor Agent.** Central router using ReAct pattern. Responsibilities: intent classification, task decomposition, routing to single specialist, synthesizing multi-step results, managing conversation flow, escalation on low confidence. Configuration: gpt-4o-2024-08-06, temperature=0 (deterministic), max_iterations=20, routing_accuracy_target=95%. Temperature MUST be 0 for deterministic routing.

4.3. **Specialist Agents (8).**
  - **Intake Agent**: Document/transaction ingestion. Tools: parse_invoice, parse_receipt, parse_bank_statement. ReAct pattern for document type reasoning.
  - **Categorization Agent**: Classify transactions to COA. Tools: lookup_coa, suggest_category, match_vendor_to_account. Memory dependency: episodic (past decisions) + semantic (COA hierarchy).
  - **Validation Agent**: Pre-posting validation. Tools: check_debit_credit_balance, validate_coa_membership, check_duplicate, run_compliance_check. Critical checks: balance validation, COA membership, duplicate detection.
  - **Posting Agent**: Execute journal entries. Tools: create_journal_entry, post_to_ledger, create_reversing_entry. Uses Plan-and-Execute (not pure ReAct) for auditable DAGs. ALL posting operations require human approval.
  - **Reconciliation Agent**: Match transactions across ledgers/statements. Tools: match_transactions, identify_discrepancies, suggest_matches. HITL gate: discrepancies above threshold.
  - **Reporting Agent**: Financial reports/analytics. Tools: generate_trial_balance, generate_pnl, generate_balance_sheet. HITL gate: exception-only (auto-generated reports sampled at 5%).
  - **Tax Agent**: Tax calculations/filings. Tools: calculate_vat, calculate_income_tax, generate_tax_report. HITL gate: ALL tax filings require 100% human approval.
  - **Audit Agent**: Audit trails, anomaly detection. Tools: generate_audit_trail, detect_anomalies, run_compliance_check. HITL gate: anomaly investigation requires human review.

4.4. **SKILL Registry.** OpenClaw SKILL.md format (YAML frontmatter + markdown). Local-first, SDK-free, discoverable via vector search, versioned. Loading precedence: workspace > user > bundled. Each SKILL.md contains: name, description, version, metadata (accounting domain, risk_level, requires_approval, audit_trail), dependencies.

4.5. **Skill Security (ClawHavoc Defense).** ClawHavoc incident: 341+ malicious skills, 20% of packages compromised. Attack vectors: C2 callbacks, credential harvesting, prompt injection. Defense layers: SHA-256 + VirusTotal scan on upload, daily rescanning, cryptographic signing, Docker sandboxing, least-privilege permissions, deny-by-default network egress, complete invocation logging.

4.6. **Chat Interface Protocol.** WebSocket at /ws/chat/{session_id}. Client messages: message, approval, rejection, upload. Server messages: stream_start, stream_token, stream_end, approval_request, error, status. Multi-connection sessions (multiple browser tabs). Persistent history in Redis.

4.7. **Context Management.** Five-layer context: conversation history (Redis, session), user preferences (PostgreSQL, permanent), episodic memory (Mem0, permanent -- past decisions, corrections, patterns), working state (in-memory, session -- pending approvals, drafts), entity context (Redis, session -- active company/book/period).

4.8. **Human-in-the-Loop Framework.** Graduated autonomy model: Phase 1 (Weeks 1-4): 100% approval; Phase 2 (Weeks 5-12): 20% sampled; Phase 3 (Months 3-6): exception-only; Phase 4 (Months 6+): full autonomy with policy triggers.

4.9. **Approval Decision Matrix.** Risk-based approval: Post journal entry (high cost, low reversibility -> finance manager + accountant), Delete entry (very high -> dual approval), Bulk posting (very high -> controller review), Generate standard report (low -> exception-only), Tax filing submission (very high -> controller + external review).

4.10. **Approval Workflow Patterns.** Four patterns: (1) Action-Level Gate -- agent proposes tool call, waits for approval; (2) Draft Approval -- agent drafts content, human reviews/edits; (3) Dual Approval -- two-person rule for high-risk; (4) Exception-Only -- auto-approves unless policy trigger fires.

4.11. **Memory Architecture.** Three-tier model: Short-Term (Redis, <10MB/agent, session TTL) -- conversation messages, session state, working drafts; Episodic (Mem0, ~GB scale, persistent) -- past categorization decisions, correction history, approval patterns, reconciliation matches; Semantic (PostgreSQL + Mem0, ~GB scale, persistent) -- COA hierarchy, business rules, vendor mappings, tax jurisdiction rules.

4.12. **Tool Calling.** JSON Schema function definitions with single-responsibility tools, clear parameter descriptions, domain_action naming convention (gl_create_journal_entry), additionalProperties: false. Cross-provider compatibility via MCP (Model Context Protocol). Capability router selects optimal provider per task: Anthropic for complex tool calling (8.4/10 reliability), OpenAI for routing (cost-effective), GPT-4o for document parsing (multimodal).

4.13. **Error Handling.** Three failure categories: Hard (API timeout, rate limit -> retry with exponential backoff), Structural (invalid JSON, schema failure -> retry with clearer instructions), Semantic (hallucinated account codes -> flag for human review). Four degradation levels: Full -> Cached -> Restricted -> Human-only. Circuit breakers prevent cascading failures.

4.14. **Safety Guardrails.** Input validation: 5-layer pipeline (syntax, semantic, authorization, content safety, business rules). Output validation: 5-layer pipeline (schema, accounting rules, balance check, duplicate check, anomaly detection). Content safety: PII detection, prompt injection scan, SQL injection prevention, data exfiltration prevention.

4.15. **EU AI Act Compliance.** High-risk system classification (Annex III, Section 5b). Key dates: Feb 2025 (prohibited practices), Aug 2025 (GPAI obligations), Aug 2026 (full high-risk obligations, penalties up to EUR 35M or 7% global turnover). Requirements: risk management, data governance, technical documentation, record-keeping (Art. 12), transparency (Art. 13), human oversight (Art. 14), accuracy, cybersecurity, conformity assessment, registration, post-market monitoring.

## Required Tables

| Table # | Title | Columns |
|---------|-------|---------|
| T4-1 | Specialist Agent Specifications | Agent, Purpose, Tools, Input, Output, HITL Gate, Execution Pattern |
| T4-2 | Cost-Benefit Analysis of Agent Topologies | Approach, Avg Tokens, Avg Cost, E2E Success Rate, When It Wins |
| T4-3 | SKILL.md Format Specification | Field, Type, Description, Example |
| T4-4 | ClawHavoc Security Measures | Layer, Control, Implementation |
| T4-5 | WebSocket Message Protocol | Direction, Message Type, Fields, Purpose |
| T4-6 | Context Layers | Layer, Storage, Lifetime, Purpose, Size |
| T4-7 | Graduated Autonomy Phases | Phase, Timeframe, Approval Rate, Description |
| T4-8 | Approval Decision Matrix | Action Type, Cost of Error, Reversibility, Required Approver, SLA |
| T4-9 | Error Taxonomy | Category, Definition, Examples, Response Strategy |
| T4-10 | Degradation Levels | Level, Trigger, Agent Behavior |
| T4-11 | EU AI Act Requirements | Requirement, Article, Implementation |
| T4-12 | Per-Agent Cost Tracking | Agent, Avg Tokens, Avg Cost, Primary Cost Driver |
| T4-13 | Memory Framework Comparison | Framework, Strengths, Best For |

## Required Diagrams

| Diagram # | Type | Description |
|-----------|------|-------------|
| D4-1 | Star topology diagram | Supervisor in center with 8 specialist agents radiating outward |
| D4-2 | Sequence diagram | Full chat flow: user message -> intent classification -> skill loading -> agent delegation -> tool calls -> approval gate -> ledger write -> response synthesis |
| D4-3 | State machine diagram | Graduated autonomy phases: 100% -> sampled -> exception-only -> full |
| D4-4 | Hierarchy diagram | Three-tier memory architecture with storage types and contents |
| D4-5 | Flow diagram | 5-layer input validation pipeline |
| D4-6 | Flow diagram | 5-layer output validation pipeline |
| D4-7 | WebSocket state diagram | Connection lifecycle with message types |
| D4-8 | MCP architecture diagram | Supervisor -> MCP Client -> MCP Servers (GL, COA, Tax) |

## Key Citations
- dim09: Complete agent topology, supervisor configuration, 8 specialist agents
- dim09: SKILL.md format, registry API, skill discovery, ClawHavoc security
- dim09: WebSocket protocol, session management, context layers
- dim09: Human-in-the-loop framework, approval decision matrix, workflow patterns
- dim09: Three-tier memory architecture (episodic/semantic/short-term), Mem0
- dim09: Error handling taxonomy, circuit breakers, saga pattern, graceful degradation
- dim09: EU AI Act compliance, high-risk classification, article-by-article implementation
- dim09: Observability, tracing, metrics, cost tracking per agent
- cross: Supervisor pattern (89% success), EU AI Act deadline (high confidence)
- insight: HITL + Approval convergence = single trust interface
- insight: ClawHavoc creates risk + positioning opportunity

---

# Chapter 5: Financial Reporting SKILLs
**Word Count Target:** 3,500-4,000 words

## Content Points

5.1. **SKILL Taxonomy Overview.** 33+ report SKILLs organized across 7 categories: Core Statements (4), Internal Verification (3), Management (6), Tax (5), Variance (5), KPI (5), Audit/Compliance (3+). Every SKILL registered with deterministic JSON schema defining inputs, parameters, data model, and output format.

5.2. **Report Engine Architecture.** 5-stage pipeline: (1) Parameter Ingestion & Validation, (2) Query Layer Execution, (3) Data Model Transformation, (4) Rule Application, (5) Output Formatting. All reports deterministic, cacheable with JSON schemas.

5.3. **Core Statement SKILLs.**
  - P&L Statement (core.pl): Revenue minus expenses. IFRS 18 five-category structure (Operating, Investing, Financing, Income Taxes, Discontinued Operations). Mandatory subtotals: Operating Profit, Profit before Financing and Tax, Net Income.
  - Balance Sheet (core.bs): Assets = Liabilities + Equity. Current/Non-current split. IFRS 18: goodwill as separate line item.
  - Cash Flow Statement (core.cf): Direct and Indirect method per IAS 7. IFRS 18 changes: indirect starts from Operating Profit (not Net Income), interest paid -> Financing, interest received -> Investing.
  - Trial Balance (core.tb): All account balances verifying debits=credits. Three types: Unadjusted, Adjusted, Post-Closing.

5.4. **IFRS 18 Implementation.** Effective January 2027. Most significant P&L change in 20+ years. Five categories replace traditional single-step/multi-step. Management Performance Measures (MPMs) require mandatory disclosure with reconciliation. The P&L SKILL supports MPM reconciliation (e.g., Adjusted EBITDA with line-item reconciliation to Operating Profit).

5.5. **Internal Verification SKILLs.** Trial Balance Verification (verify.tb_balanced), Balance Sheet/Cash Flow Reconciliation (verify.bs_cf), Intercompany Elimination Check (verify.intercompany).

5.6. **Management Report SKILLs.** Aged AR (mgmt.ar_aging): buckets Current, 1-30, 31-60, 61-90, 90+ days, DSO metric. Aged AP (mgmt.ap_aging): similar buckets with Days Payable Outstanding. GL Detail/Summary (mgmt.gl_detail, mgmt.gl_summary). Executive Summary (mgmt.executive): combines P&L highlights, balance sheet snapshot, cash position, KPIs, variance alerts. COA Listing (mgmt.chart_of_accounts).

5.7. **Tax Report SKILLs.** UK VAT 9-box (tax.vat_uk): Boxes 1-9 with auto-calculation, MTD compliance. BAS Australia (tax.bas_au): G1-G20 labels. Generic GST (tax.gst): jurisdiction-agnostic. Sales Tax by Jurisdiction (tax.sales_tax): US state/county/city/district breakdown. Corporation Tax Computation (tax.corporation_tax).

5.8. **KPI SKILLs.** Profitability: Gross Margin, Operating Margin, Net Margin, ROA, ROE, EBITDA Margin. Liquidity: Current Ratio (>2.0 ideal), Quick Ratio, Cash Ratio, Working Capital. Efficiency: Inventory Turnover, DSO (<45 days healthy), DPO, Cash Conversion Cycle, Asset Turnover. Solvency: Debt-to-Equity, Debt-to-Assets, Interest Coverage. Startup: Gross/Net Burn Rate, Runway, CAC, LTV, LTV:CAC Ratio (>3:1), MRR, ARR, Net Revenue Retention (>100%).

5.9. **Variance SKILLs.** Period-over-Period Comparison (var.period): absolute, percentage, direction indicators. Budget vs Actual (var.budget): favorable/unfavorable flags, auto-explanation threshold. Tracking Category Analysis (var.tracking): dimensional pivot by department, region, project. Year-End Comparison (var.year_end): multi-year trends with CAGR.

5.10. **Framework Parameterization.** Single SKILL produces GAAP or IFRS output via `framework` parameter. Framework rule bundles define: account classification mapping, line item ordering, required subtotals, disclosure requirements, sign conventions, terminology (e.g., "Income Statement" vs "Profit & Loss Account").

5.11. **Output Format Layer.** Six formats: JSON (API), HTML (web viewing), PDF (document distribution via headless browser), CSV (spreadsheet import), XBRL (machine-readable regulatory), iXBRL (human + machine readable). Format selection is parameter-driven.

5.12. **Report Scheduling & Distribution.** Time-based (daily/weekly/monthly/quarterly), event-driven (on period close, threshold breach), data-driven (when burn rate exceeds threshold), on-demand. Distribution channels: email, SFTP, API/webhook, SharePoint/Teams, Slack, dashboard. Triggered alerts: low runway warning, high overdue AR.

5.13. **XBRL/iXBRL Layer.** UK mandate: April 2028 software-only iXBRL filing for all companies. Taxonomy mapping: report line items -> XBRL elements. 6-stage iXBRL generation pipeline: HTML report -> taxonomy mapping -> embed XBRL tags -> generate context -> validate -> output. Validation: schema, calculation consistency, business rules, mandatory items, data types, duplicate detection.

5.14. **LLM SKILL Registry for Reports.** Each report SKILL is a registered, schema-validated capability. LLM can discover reports via semantic search. Natural language report requests: "Show me my P&L for last quarter" -> core.pl with extracted parameters. Report parameters: entity_id, period (start/end), comparison period, framework, currency, tracking dimensions, filters, output format.

## Required Tables

| Table # | Title | Columns |
|---------|-------|---------|
| T5-1 | Complete Report SKILL Catalog (33 reports) | #, Category, SKILL ID, Report Name, Framework |
| T5-2 | IFRS 18 Five-Category P&L Structure | Category, Description, Typical Items |
| T5-3 | IFRS 18 Required Subtotals | Subtotal Name, Components, Calculation Order |
| T5-4 | KPI Formulas and Benchmarks | KPI Category, KPI Name, Formula, Benchmark |
| T5-5 | Framework Rule Bundle Structure | Framework, Section, Rules, Differences |
| T5-6 | GAAP vs IFRS Key Differences | Area, GAAP (US), IFRS |
| T5-7 | Output Format Comparison | Format, Use Case, Implementation |
| T5-8 | Report Scheduling Types | Schedule Type, Description, Example |
| T5-9 | Distribution Channels | Channel, Use Case, Configuration |
| T5-10 | XBRL Validation Requirements | Validation Type, Description |
| T5-11 | AR Aging Buckets | Bucket, Range, Collection Priority, Typical Action |
| T5-12 | UK VAT 9-Box Structure | Box, Description, Content, Amount Type |
| T5-13 | Startup KPI Definitions | KPI, Formula, Purpose, Healthy Threshold |

## Required Diagrams

| Diagram # | Type | Description |
|-----------|------|-------------|
| D5-1 | Flow diagram | 5-stage report engine pipeline |
| D5-2 | Structural diagram | IFRS 18 P&L hierarchy with mandatory subtotals |
| D5-3 | Comparison diagram | Traditional P&L vs IFRS 18 5-category P&L side-by-side |
| D5-4 | Process diagram | XBRL/iXBRL 6-stage generation pipeline |
| D5-5 | Class diagram | SKILL taxonomy by category (7 categories, 33+ reports) |

## Key Citations
- dim08: Complete 33-report SKILL taxonomy across 7 categories
- dim08: IFRS 18 five-category P&L, mandatory subtotals, MPM disclosures
- dim08: Framework parameterization (GAAP vs IFRS rule bundles)
- dim08: Report scheduling, distribution channels, triggered alerts
- dim08: XBRL/iXBRL layer, UK mandate timeline, taxonomy mapping
- dim08: 5-stage report engine architecture
- dim12: MVP core reports (P&L, BS, TB, AR Aging, AP Aging)
- cross: IFRS 18 vs current COA (conflict zone with resolution)
- insight: IFRS 18 creates reporting refresh market moment

---

# Chapter 6: Multi-Standard, Multi-Currency & Tax
**Word Count Target:** 4,000-4,500 words

## Content Points

6.1. **Tax Engine Architecture.** Three-layer model: Rule Store + Execution Engine + Override Workflow. Informed by OECD VAT/GST Guidelines, HMRC MTD specifications, EU OSS frameworks. Configurable by tax professionals, not developers. Supports 5 tax types across 19,000+ jurisdictions.

6.2. **Tax Type Registry (5 Types).**
  - VAT: Credit-invoice with input tax deduction. UK 20%, DE 19%, FR 20%, EU avg ~21%. Reverse charge, intra-community supplies, OSS reporting.
  - GST: Credit-invoice with input tax credits. Australia 10%, NZ 15%, Canada 5%, Singapore 9%.
  - US Sales Tax: Retail single-stage, no input credit. ~45 states. Economic nexus post-Wayfair. Destination-based vs origin-based sourcing.
  - Withholding Tax: Deducted at source on cross-border payments. Dividends 0-30%, Interest 0-25%, Royalties 0-20%. Treaty rates vs statutory rates.
  - Digital Services Tax: Revenue-based. UK 2%, France 3%, Italy 3%, etc. Global revenue threshold EUR 750M typical.

6.3. **Tax Rule Store Schema.** Core rule entity with: rule_id, version, status, priority, tax_type, jurisdiction (country/subdivision/local), applicability_conditions (transaction_type, party_type, product_category, digital_indicator, cross_border), rate_configuration (type, value, basis, compound), effective_dates, threshold_conditions, exemption_conditions, place_of_supply_rule, accounting_treatment, reporting_mapping.

6.4. **Place of Supply Engine.** 6-step pipeline: (1) Identify supply category, (2) Identify party types (B2B/B2C/B2G), (3) Determine customer location, (4) Apply specific rules (property location, event location), (5) Apply general rules (B2B: customer belongs; B2C: supplier belongs), (6) Validate evidence. OECD Guidelines as foundation.

6.5. **B2B vs B2C Place of Supply Rules.** B2B services: place of supply = customer's jurisdiction (reverse charge). B2C services: place of supply = supplier's jurisdiction. B2C digital services: place of supply = consumer's residence (OSS applicable). 130+ countries have digital services VAT rules.

6.6. **Input/Output Tax Tracking.** Separate control accounts: VAT Output Tax (liability to HMRC, Box 1), VAT Input Tax (recoverable, Box 4), VAT on EU Acquisitions (Box 2), VAT Control Account (net position, Box 5). Settlement entries for payable vs repayable scenarios.

6.7. **UK VAT Return (9-Box).** Box 1: VAT due on sales. Box 2: VAT on EU acquisitions (NI only). Box 3: Total VAT due (1+2). Box 4: VAT reclaimed on purchases. Box 5: Net VAT (3-4). Box 6: Total sales ex-VAT. Box 7: Total purchases ex-VAT. Box 8: EU supplies (NI). Box 9: EU acquisitions (NI). Digital records 6 years.

6.8. **HMRC MTD Digital Submission.** OAuth 2.0 authentication. API endpoints: obligations, returns submission, view return, liabilities, payments. Mandatory fraud prevention headers (Gov-Client-Connection-Method, Public-IP, Device-ID, etc.). Digital linking rules: formula-driven connections acceptable; copy-paste/manual re-keying not acceptable.

6.9. **Multi-Currency Support (Phase 3).** 150+ currencies (ISO 4217). Exchange rate sources: ECB, XE.com, Open Exchange Rates. Daily automatic updates. Transaction-level currency recording. Realized FX gain/loss on payment. Unrealized FX gain/loss at period-end revaluation. IAS 21 compliance: functional currency determination, spot-rate translation, closing-rate remeasurement.

6.10. **Three-Currency Architecture.** Functional currency (primary economic environment), Transaction currency (invoice/payment denomination), Presentation currency (reporting). Exchange rate types: spot, average, closing. Cumulative Translation Adjustment (CTA) in OCI for consolidation.

6.11. **Registration Threshold Monitoring.** Global thresholds: UK GBP 90,000, Germany EUR 22,000/50,000, EU distance selling EUR 10,000, Australia AUD 75,000, Canada CAD 30,000, Singapore SGD 1,000,000, US varies by state (~$100,000 typical). Alert levels: Green (<50%), Amber (50-79%), Orange (80-99%), Red (100%+).

6.12. **US Economic Nexus Monitoring.** Post-Wayfair (2018): 25 states use dollar-only threshold (typically $100,000), 17 use dollar OR transactions (typically $100K or 200 tx), 2 use dollar AND transactions (NY: $500K + 100 tx). Key risk: 200 transactions at $5 each = $1,000 revenue triggers nexus.

6.13. **Exemption Handling.** Zero-rated (taxable at 0%, input tax recoverable): exports, certain food, children's clothing. Exempt (outside scope, no input recovery): financial services, residential property, postal services. Reverse charge: shifts VAT liability from supplier to customer (B2B cross-border services, domestic construction CIS). Partial exemption formula for mixed businesses.

6.14. **EU OSS (One-Stop Shop).** Single registration in any EU member state. Quarterly filing by calendar quarter. Import OSS monthly. VAT at member state of consumption rate. No input tax deduction through OSS. EUR 10,000 threshold for intra-EU B2C supplies.

6.15. **Tax Audit Trail.** Full traceability from source document through tax calculation to return line item. 7-step trace: source_document -> jurisdiction_determination -> rule_evaluation -> tax_calculation -> accounting_entry -> return_mapping -> submission. 6-year retention. MTD digital linking evidence.

## Required Tables

| Table # | Title | Columns |
|---------|-------|---------|
| T6-1 | Tax Type Registry Summary | Tax Type, Mechanism, Standard Rates, Scope, Key Features |
| T6-2 | VAT Rates by Jurisdiction (Key Countries) | Country, Standard Rate, Reduced Rate, Zero Rate, Notes |
| T6-3 | WHT Rates by Country (Non-Treaty) | Country, Dividends, Interest, Royalties |
| T6-4 | UK VAT 9-Box Return | Box, Description, Content, Amount Type |
| T6-5 | Australia BAS Structure | Label, Description, Calculation |
| T6-6 | HMRC MTD API Endpoints | Endpoint, Purpose, Method |
| T6-7 | Fraud Prevention Headers | Header, Description, Example |
| T6-8 | Digital Link Compliance | Acceptable Links, Non-Acceptable Links |
| T6-9 | Global Registration Thresholds | Jurisdiction, Tax Type, Threshold, Notes |
| T6-10 | US Economic Nexus Patterns | Pattern Type, States, Revenue Threshold, Transaction Threshold |
| T6-11 | Threshold Alert Levels | Level, Trigger, Action |
| T6-12 | Exemption Types Comparison | Type, Input Tax Recovery, Examples |
| T6-13 | Reverse Charge Scenarios | Scenario, Application, Reference |
| T6-14 | Exchange Rate Handling by Transaction Type | Transaction Type, Rate Applied, FX Treatment |
| T6-15 | Tax Audit Trail Components | Component, Description, Retention Period |

## Required Diagrams

| Diagram # | Type | Description |
|-----------|------|-------------|
| D6-1 | 3-layer block diagram | Tax engine: Rule Store -> Execution Engine -> Override Workflow |
| D6-2 | Flow diagram | Place of supply 6-step determination pipeline |
| D6-3 | Flow diagram | Digital submission architecture: HMRC MTD, EU OSS, ATO SBR adapters |
| D6-4 | State machine diagram | Threshold monitoring: Green->Amber->Orange->Red with actions |
| D6-5 | Data flow diagram | Tax audit trail: 7-step trace from source to submission |
| D6-6 | Comparison table/matrix | B2B vs B2C place of supply rules by supply category |

## Key Citations
- dim05: Complete tax engine 3-layer architecture, 5 tax types, rule store schema
- dim05: Place of supply engine, OECD Guidelines, B2B/B2C rules, digital services
- dim05: UK VAT 9-box, Australia BAS, EU OSS, Canada GST/HST return structures
- dim05: HMRC MTD API, fraud prevention headers, digital linking rules
- dim05: Registration thresholds by jurisdiction, US economic nexus patterns
- dim05: Exemption handling, zero-rated vs exempt, reverse charge
- dim05: Tax audit trail 7-step data model
- dim12: Phase 3 multi-currency, multi-tax features
- cross: Tax engine 3-layer architecture (high confidence), IAS 21 multi-currency
- insight: Digital link chain for intrinsic MTD compliance

---

# Chapter 7: Document Processing & Workflow Automation
**Word Count Target:** 3,000-3,500 words

## Content Points

7.1. **Document Upload & OCR Extraction (Phase 2, Month 4).** Upload receipts, invoices, bills (PDF, JPG, PNG). Extraction pipeline: Upload -> Preprocessing (deskew, enhance) -> OCR (Tesseract/DocTR) -> LLM Extraction (GPT-4o Vision / Claude) -> Validation Rules -> Structured Output -> Draft Transaction/Bill. Key metrics: OCR accuracy 92-95%, end-to-end 95-97%, 80% human intervention reduction.

7.2. **Document Types Supported.** Supplier invoices/bills: vendor, date, due date, line items, subtotal, VAT, total. Receipts: vendor, date, items, total, payment method. Bank statements: transactions for import. Credit notes: same as invoices.

7.3. **Validation Rules.** Amount consistency: sum of line items = subtotal = total - VAT. Date validation: invoice date <= due date. VAT calculation: VAT amount = net * rate. Duplicate detection: same vendor + number + amount flagged.

7.4. **Human-in-the-Loop for Documents.** Low-confidence extractions (<90%) flagged for review. Side-by-side: extracted data + original document. One-click correction: edit any field, system learns from correction via episodic memory.

7.5. **Bank Statement Import (MVP, Weeks 2-3).** CSV import with column mapping. OFX parsing (versions 1.02, 2.1, 2.2). Pre-built bank templates: Barclays, HSBC, Lloyds, NatWest, Monzo, Starling, Revolut. Duplicate detection: FITID (OFX) or hash of date+amount+description (CSV).

7.6. **Bank Feed Integration (Phase 2, Month 3).** Open Banking via PSD2 APIs with Strong Customer Authentication. Aggregator strategy: TrueLayer (primary UK), Plaid (secondary), Salt Edge (tertiary EU), Yodlee (fallback). Features: daily polling, 12-24 month historical backfill, multi-bank, automatic deduplication, real-time webhooks.

7.7. **Bank Rules Engine (Phase 2, Month 3).** Xero-style automatic categorization. Rule structure: conditions (description contains/equals/regex, amount between/equals, bank account, direction) + actions (contact, account, tax rate) + execution mode (suggest/auto-apply/disabled). Pre-built library: 50+ common patterns.

7.8. **Manual Bank Reconciliation (MVP, Week 3).** Side-by-side: bank transactions left, unmatched ledger entries right. Match types: one-to-one, one-to-many (single deposit matching multiple invoices), partial (amount difference e.g., bank fees). Match criteria: amount difference, date difference, reference similarity. Reconciliation report: opening balance + bank transactions - reconciled = closing balance.

7.9. **ML-Powered Reconciliation (Phase 4, Month 14).** Xero JAX-inspired. 4-layer architecture: Rule layer, Match layer, Memory layer, Prediction layer. Per-organization Random Forest model trained on 12 months of data. Features: amount, day_of_week, hour, merchant_name, description keywords, historical category distribution. Target: 80%+ auto-reconcile, 97%+ accuracy on suggested matches.

7.10. **Recurring Transactions & Invoices (Phase 2, Months 3-4).** Templates with schedule: weekly, bi-weekly, monthly, quarterly, annual. End conditions: never, after N occurrences, until date. Auto-post or draft-for-review. Pre-built templates: rent, insurance, subscriptions, loan repayments, depreciation. Recurring invoices: template + schedule, auto-send, Stripe/GoCardless integration, failed payment handling.

7.11. **Approval Workflows (Phase 2, Month 5).** Multi-step approval chains. Threshold-based routing: <GBP 500 auto-approved, 500-2000 manager, >2000 director. Types: invoice, bill payment, journal entry. Delegate during absence. Reminder escalation after N days. Approval via chat or email.

7.12. **Multi-User Support (Phase 2, Month 4).** Roles: Owner (full), Admin (no deletion), Bookkeeper (ledger read/write), Accountant (read-only + reports), Viewer (read-only). Email invitation. Concurrent editing protection. Activity logging.

7.13. **Ingestion Pipeline Architecture.** POLL (aggregator API) -> NORMALIZE (canonical schema) -> DEDUPLICATE -> QUEUE (message broker) -> PROCESS (store + trigger matching). Canonical transaction schema: transaction_id, account_id, amount, currency, transaction_date, description, merchant_name (97% fill rate), reference, transaction_type, status, raw_data.

## Required Tables

| Table # | Title | Columns |
|---------|-------|---------|
| T7-1 | Document Type Support | Type, Formats, Extraction Fields |
| T7-2 | OCR/Extraction Accuracy Metrics | Metric, Rate, Comparison |
| T7-3 | Bank Aggregator Strategy | Provider, Region, Institutions, Priority |
| T7-4 | File Format Support | Format, Version, Priority |
| T7-5 | Bank Rule Structure | Component, Fields, Description |
| T7-6 | Rule Condition Operators | Field, Operators Available |
| T7-7 | Rule Execution Modes | Mode, Description, Risk Level |
| T7-8 | Reconciliation Workflow Steps | Step, Description, System Action |
| T7-9 | ML Reconciliation Layers | Layer, Function, Technology |
| T7-10 | Recurring Schedule Options | Frequency, End Conditions, Post Mode |
| T7-11 | User Roles & Permissions | Role, Permissions, Restrictions |
| T7-12 | Approval Workflow Configuration | Element, Options, Description |
| T7-13 | Canonical Transaction Schema | Field, Type, Source Mapping |

## Required Diagrams

| Diagram # | Type | Description |
|-----------|------|-------------|
| D7-1 | Pipeline diagram | Document extraction: upload -> OCR -> LLM -> validation -> draft |
| D7-2 | Pipeline diagram | Bank feed ingestion: poll -> normalize -> dedup -> queue -> process |
| D7-3 | Flow diagram | Reconciliation workflow: import -> review -> match -> confirm -> report |
| D7-4 | Architecture diagram | ML reconciliation 4-layer stack |
| D7-5 | State machine diagram | Approval workflow: Draft -> Submitted -> Approved -> Posted, with rejection path |

## Key Citations
- dim12: MVP bank import (CSV/OFX), reconciliation workflow
- dim12: Phase 2 bank feeds, rules engine, recurring transactions, document extraction
- dim12: Phase 2 multi-user, approval workflows
- dim12: Phase 4 ML-powered reconciliation (JAX-style)
- dim09: Human-in-the-loop for document review, confidence thresholds
- insight: Touchless transaction entry (document to ledger pipeline)
- insight: Per-organization ML personalization

---

# Chapter 8: Security, Compliance & Audit Trail
**Word Count Target:** 3,000-3,500 words

## Content Points

8.1. **Authentication.** OAuth 2.0 + PKCE (RFC 9700) following Xero pattern. Authorization Code + PKCE S256 for all clients. JWT access tokens (RS256, 30-min expiry). Rotating refresh tokens (60-day expiry). HTTP-only, Secure, SameSite=Strict cookies. Optional mTLS for server-to-server. Token claims: sub, org, roles, scope.

8.2. **Authorization (RBAC).** Five roles: Owner (full), Admin (all except billing/deletion), Bookkeeper (ledger read/write, contacts, reports), Accountant (read-only + reports), Viewer (read-only). RBAC middleware checks roles claim against endpoint requirements.

8.3. **Data Encryption.** In transit: TLS 1.3 external, mTLS internal gRPC. At rest DB: PostgreSQL TDE or LUKS. At rest files: MinIO AES-256. Secrets: HashiCorp Vault or Kubernetes sealed secrets. Sensitive fields: application-level AES-256-GCM for bank credentials, tax IDs.

8.4. **Immutable Append-Only Ledger.** Formance hash-chained architecture with SHA-256 chaining. Postings table: no UPDATE/DELETE. Corrections via compensating reversing entries. WORM storage option. Verification on read. This creates tamper-evident financial records.

8.5. **Conversational Audit Trail.** Cross-dimensional insight: every natural language request becomes the first link in a cryptographic chain including LLM reasoning trace, generated Numscript, human approval decision, final ledger posting -- all time-stamped and signed. Traditional systems log WHAT happened; this system logs WHY (human language intent), HOW (AI reasoning), and WHO (approver identity).

8.6. **Pseudonymization Layer.** GDPR-compliant: encrypt PII with managed keys. Erasure = key destruction (preserves financial transaction integrity while satisfying GDPR Article 17). Dual purpose: enables multi-tenant isolation (destroy tenant keys = anonymize their PII while preserving audit trail).

8.7. **Audit Log Data Model.** id, organization_id, user_id, action (CREATE/READ/UPDATE/DELETE/LOGIN), resource_type, resource_id, details (JSONB before/after), ip_address, user_agent, timestamp, session_id. Indexed by org + time for efficient querying.

8.8. **EU AI Act Compliance (High-Risk System).** Classification: Annex III, Section 5b (financial health assessment). Key date: August 2, 2026 (full obligations, penalties up to EUR 35M or 7% global turnover). Article-by-article implementation:
  - Art. 9: Risk management system with documented risk register
  - Art. 10: Data governance and quality management
  - Art. 11: Technical documentation
  - Art. 12: Automatic event logging, 6+ year retention
  - Art. 13: AI disclosure, capability disclosure, decision explanation
  - Art. 14: Graduated autonomy HITL framework (already implemented)
  - Art. 15: Accuracy certification, regular assessment
  - Art. 43: Third-party conformity assessment
  - Art. 71: EU database registration
  - Art. 72: Post-market monitoring, 15-day incident reporting

8.9. **HMRC MTD Compliance Roadmap.** MVP: digital records, 9-box calculation, preview only. Phase 2: full API submission. Phase 3: multi-scheme (cash/accrual/flat rate). Phase 4: group VAT, partial exemption. Digital links mandatory. 6-year record retention.

8.10. **GDPR Compliance.** Pseudonymization for right-to-erasure. Data export capability. Consent management. DPO workflow (Phase 3). Cross-border data transfer (Phase 4). Future-proofed for CCPA, Virginia CDPA.

8.11. **Security Model for Skills.** ClawHavoc defense: SHA-256 + VirusTotal scan, daily rescanning, cryptographic signing, Docker sandboxing, least-privilege, deny-by-default network egress. Third-party skill marketplace: vet-only (curated), not open-upload.

8.12. **Incident Response.** Automatic detection of serious incidents (balance corruption, unauthorized access). Immediate alert to responsible person. Structured report generation. 15-day reporting SLA to competent authorities (EU AI Act).

8.13. **Multi-Tenant Data Isolation.** Ledger: per-tenant Formance ledgers + PostgreSQL schema buckets. Application: organization_id column with RLS policies. Files: per-tenant MinIO buckets. Cache: key prefixing {org_id}:{resource}. Events: topic namespacing {resource}.{org_id}.{event}.

## Required Tables

| Table # | Title | Columns |
|---------|-------|---------|
| T8-1 | Authentication Configuration | Aspect, Implementation |
| T8-2 | RBAC Role Matrix | Role, Create, Read, Update, Delete, Manage Users, Billing |
| T8-3 | Data Encryption Layers | Layer, Method, Standard |
| T8-4 | Multi-Tenant Isolation | Isolation Level, Mechanism |
| T8-5 | EU AI Act Requirements | Article, Requirement, Implementation, Status |
| T8-6 | Compliance Roadmap (UK) | Regulation, MVP, Phase 2, Phase 3, Phase 4 |
| T8-7 | Security Measures for Skills | Layer, Control, Implementation |
| T8-8 | Incident Escalation Policy | Trigger, Routing, SLA, Auto-Action |
| T8-9 | Audit Log Schema | Field, Type, Description |

## Required Diagrams

| Diagram # | Type | Description |
|-----------|------|-------------|
| D8-1 | Chain diagram | Conversational audit trail: NL request -> reasoning -> Numscript -> approval -> ledger entry with cryptographic links |
| D8-2 | Block diagram | Pseudonymization layer: PII encryption/decryption separated from transaction data flow |
| D8-3 | Flow diagram | EU AI Act compliance implementation flow |
| D8-4 | Isolation diagram | Multi-tenant data isolation across all layers |

## Key Citations
- dim01: OAuth 2.0 + PKCE, RBAC roles, data encryption, multi-tenant isolation
- dim09: EU AI Act compliance, article-by-article implementation, HITL framework
- dim09: Skill security, ClawHavoc defense layers
- dim09: Error handling, circuit breakers, incident escalation
- cross: EU AI Act Aug 2026 deadline (high confidence), immutable append-only ledger
- insight: Conversational audit trail as regulatory moat
- insight: Pseudonymization resolves GDPR + enables multi-tenancy
- insight: Numscript IS the EU AI Act audit trail

---

# Chapter 9: MVP Requirements Specification
**Word Count Target:** 4,500-5,000 words

## Content Points

9.1. **MVP Scope Definition.** Single-entity accounting system for UK VAT-registered small business (freelancer, sole trader, or limited company, 0-10 employees, single currency GBP). Operated entirely through natural language conversation with LLM. 8-week delivery, 48 engineering days, 2-3 engineer team.

9.2. **Success Criteria.** User completes full bookkeeping cycle via chat: record transactions -> create invoice -> import bank statement -> reconcile -> run VAT return -> generate P&L and Balance Sheet. All data passes double-entry validation. HMRC MTD VAT nine-box return calculated and previewed. End-to-end without code or spreadsheets.

9.3. **Module 1: Chart of Accounts (Week 1).** 8 pre-loaded COA templates. Standard 5-category 4-digit numbering. 9 account types. VAT rate assignment per account. Account enabling/disabling. LLM SKILLs: coa.list, coa.add_account, coa.edit_account, coa.set_vat_rate. Effort: 3 days.

9.4. **Module 2: Core General Ledger (Weeks 1-2).** Natural language -> structured transaction parsing. Numscript-style modeling with sum-to-zero enforcement. Transaction metadata: date, description, reference, contact, attachments. Multi-line splits, VAT-inclusive/exclusive. Journal numbering: JE-YYYY-NNNN. Status: Draft/Posted/Reversed. Full audit trail. Effort: 10 days.

9.5. **Module 3: Contact Management (Week 2).** Types: Customer, Supplier, Both. Fields: name, company, email, phone, addresses, VAT number, payment terms. Auto-creation from transactions. Duplicate detection. Balance tracking (AR/AP). Effort: 3 days.

9.6. **Module 4: Bank Statement Import (Weeks 2-3).** CSV import with column mapping. OFX parsing (1.02, 2.1, 2.2). 7 pre-built bank templates. Duplicate detection (FITID/hash). Bank account entity. Status: Imported/Categorized/Reconciled. Effort: 5 days.

9.7. **Module 5: Manual Bank Reconciliation (Week 3).** Side-by-side matching. One-to-one and one-to-many matching. Partial matching with amount difference explanation. Reconciliation report. 6-step workflow: import -> review unmatched -> match to entries -> create new entries for unmatched -> confirm balance -> generate report. Effort: 5 days.

9.8. **Module 6: Basic Invoicing (Weeks 3-4).** Line items with quantity, price, VAT. Status: Draft/Sent/Viewed/Paid/Overdue/Cancelled. Auto-numbering (INV-YYYY-NNNN). VAT calculation (20%/5%/0%). Payment terms. Credit notes. PDF generation. Email delivery tracking. Overdue detection. Post-send immutability. Effort: 6 days.

9.9. **Module 7: VAT Calculation & MTD Preview (Weeks 4-5).** Automatic VAT tracking per transaction. UK nine-box calculation (Boxes 1-9). VAT audit trail per box. Flat Rate Scheme toggle. Cash vs Accrual scheme support. VAT period configuration (monthly/quarterly/annual). MTD preview (not submission). Digital link compliance. Effort: 5 days.

9.10. **Module 8: Core Financial Reports (Weeks 5-6).** P&L, Balance Sheet, Trial Balance, Aged AR, Aged AP. 5-stage report engine. Period parameters, comparison options. Output: JSON, HTML, PDF, CSV. 5-stage pipeline: parameter ingestion -> query execution -> data transformation -> rule application -> output formatting. Effort: 5 days.

9.11. **Module 9: LLM Chat Interface (Weeks 6-8).** Conversational transaction entry. Context memory (VAT period, recent transactions, open invoices). Intent routing. Multi-turn workflows. Error handling with explanation. Confirmation gates for destructive actions. Natural date parsing ("last month", "yesterday", "Q2 2025"). Ambiguity resolution. 3 persona options. Effort: 10 days.

9.12. **Module 10: Authentication & Security (Week 2, ongoing).** JWT-based API auth. Single user (MVP constraint). API key for programmatic access. HTTPS/TLS. Database encryption at rest. Row-level audit logging. GDPR-compliant data handling. Effort: 3 days.

9.13. **MVP Technical Stack.** Ledger: Formance Ledger. API: FastAPI or NestJS. Database: PostgreSQL 16+. LLM: OpenAI GPT-4o / Claude Sonnet via function calling. Message Queue: Redis or RabbitMQ. Document Storage: S3-compatible (MinIO). PDF: WeasyPrint or Playwright. Background Jobs: Celery + Redis or BullMQ. Container: Docker + Docker Compose.

9.14. **MVP Data Model.** Entity 1--* Accounts 1--* Postings *--1 Transactions. Entity 1--* Contacts 1--* Invoices 1--* InvoiceLines. Entity 1--* BankAccounts 1--* BankTransactions. Transactions *--* BankTransactions (reconciliation_matches).

9.15. **MVP User Flows.** Four complete flows: (1) First-time setup via chat (entity creation, COA template selection, VAT configuration), (2) Daily bookkeeping (conversational transaction entry with confirmation), (3) Month-end reconciliation (import -> match -> report), (4) VAT return (quarterly calculation and preview).

9.16. **MVP SKILL Registry (25+ Skills).** Table all 25+ skills with ID, description, example query. Categories: COA (4), GL (7), Contacts (5), Bank (6), Reconciliation (5), Invoicing (6), VAT (4), Reporting (3), Chat (3).

9.17. **MVP Quality Gates.** Double-entry validation on every transaction. COA membership validation. Period open check. Unique reference enforcement. Amount bounds checking. VAT calculation verification. All write operations require explicit confirmation.

9.18. **MVP Timeline (Week by Week).** Week 1: scaffolding, DB schema, COA templates, GL engine. Week 2: contacts, bank accounts, CSV/OFX import, auth. Week 3: reconciliation, invoicing, PDF. Week 4: VAT engine, nine-box, credit notes. Week 5: report engine, P&L, BS, TB. Week 6: AR/AP aging, skill registry, basic chat. Week 7: multi-turn flows, context, errors. Week 8: end-to-end testing, UAT, docs.

## Required Tables

| Table # | Title | Columns |
|---------|-------|---------|
| T9-1 | MVP Module Summary | Module, Week, Description, Complexity, Effort (days) |
| T9-2 | MVP Technical Stack | Layer, Technology, Rationale |
| T9-3 | Complete MVP SKILL Registry (25+ skills) | Skill ID, Category, Description, Example Query |
| T9-4 | GL Transaction SKILLs | Skill ID, Description, Example Query |
| T9-5 | Invoice SKILLs | Skill ID, Description, Example Query |
| T9-6 | Reconciliation SKILLs | Skill ID, Description, Example Query |
| T9-7 | VAT SKILLs | Skill ID, Description, Example Query |
| T9-8 | MVP Timeline | Week, Deliverables, Dependencies |
| T9-9 | MVP Quality Gates | Gate, Check, Action on Failure |
| T9-10 | MVP User Flow -- First-Time Setup | Step, User Input, System Action, Output |
| T9-11 | MVP User Flow -- Daily Bookkeeping | Step, User Input, System Action, Output |
| T9-12 | MVP User Flow -- Month-End Reconciliation | Step, User Input, System Action, Output |
| T9-13 | MVP User Flow -- VAT Return | Step, User Input, System Action, Output |
| T9-14 | Invoice Status Lifecycle | Status, Description, Allowed Actions, Constraints |
| T9-15 | File Format Support | Format, Version, Priority, Notes |

## Required Diagrams

| Diagram # | Type | Description |
|-----------|------|-------------|
| D9-1 | Gantt chart | 8-week MVP timeline with module dependencies |
| D9-2 | Data model diagram | MVP simplified ER diagram |
| D9-3 | Sequence diagram | First-time setup user flow |
| D9-4 | Sequence diagram | Daily bookkeeping conversation flow |
| D9-5 | Sequence diagram | Month-end reconciliation flow |
| D9-6 | Sequence diagram | VAT return calculation flow |

## Key Citations
- dim12: Complete MVP specification (primary source)
- dim12: 10 core modules with feature specifications
- dim12: MVP technical stack, data model, user flows
- dim12: 25+ LLM skills with IDs and example queries
- dim12: 8-week timeline, 48 engineering days, 2-3 team
- dim12: Success criteria, quality gates
- dim01: Formance Ledger integration, deployment model
- dim09: Agent orchestrator, chat interface, HITL framework
- cross: MVP timeline conflict (8wk vs 6mo) with resolution

---

# Chapter 10: Phased Implementation Roadmap
**Word Count Target:** 4,000-4,500 words

## Content Points

10.1. **Roadmap Overview.** 15-month journey from 8-week MVP to full Xero-class platform (95%+ parity). Four phases: MVP (Weeks 1-8), Phase 2 Automation (Months 3-5), Phase 3 Scale (Months 6-9), Phase 4 Enterprise (Months 10-15). Total: 298 engineering days, peak team 5-7 engineers.

10.2. **Phase 2: Automation (Months 3-5).** Goal: reduce data entry effort by 70%+. 65 engineering days, 3-4 engineers.
  - Month 3: Bank feed integration (TrueLayer + Plaid, Open Banking PSD2), rules engine (50+ pre-built patterns), recurring transactions
  - Month 4: Recurring invoices (auto-send, Stripe/GoCardless), document upload + OCR extraction (95-97% accuracy), multi-user support (5 roles)
  - Month 5: Approval workflows (threshold-based, 1-3 levels), HMRC MTD VAT submission (OAuth, fraud headers), Phase 2 testing

10.3. **Phase 2 Key Features Detail.** Bank feeds: daily polling, 12-24 month backfill, multi-bank, webhook notifications, connection health monitoring. Rules engine: condition operators (contains/equals/regex/between), execution modes (suggest/auto-apply/disabled), rule effectiveness analytics. Document extraction: OCR + LLM vision, validation rules, human-in-the-loop for low-confidence.

10.4. **Phase 3: Scale (Months 6-9).** Goal: multi-currency, multi-jurisdiction, inventory, payroll, advanced reporting. 80 engineering days, 4-5 engineers.
  - Month 6: Multi-currency (150+, IAS 21 compliant, FX gain/loss), multi-tax jurisdictions (VAT/GST/Sales Tax, place of supply engine)
  - Month 7: Inventory/stock tracking (FIFO, COGS, purchase orders), fixed asset register (straight-line/diminishing value depreciation)
  - Month 8: UK payroll with RTI (FPS/EPS submission, PAYE, NICs, pension auto-enrolment), advanced report library (15+ additional reports)
  - Month 9: Custom report builder (drag-and-drop API), purchase orders/bills (3-way matching), tracking categories (department/project/region)

10.5. **Phase 3 Key Features Detail.** Multi-currency: 3-currency architecture (functional/transaction/presentation), ECB/XE/Open Exchange rate sources, daily auto-updates, realized/unrealized FX. Multi-tax: rule engine with jurisdiction-specific rates, OSS support, US economic nexus tracking. Payroll: FPS/EPS RTI submissions, starter/leaver processing (P45), statutory payments (SMP/SPP/SAP/SSP), penalties table.

10.6. **Phase 4: Enterprise (Months 10-15).** Goal: multi-entity, API platform, marketplace, white-label, ML reconciliation. 105 engineering days, 5-7 engineers.
  - Months 10-11: Multi-entity management (intercompany elimination, consolidated reporting), project tracking (time, job costing)
  - Months 11-12: Expense claims (receipt capture, mileage, per diem), API platform (OpenAPI 3.0, webhooks, SDKs)
  - Months 12-13: Developer portal, app marketplace (30+ pre-built integrations)
  - Month 14: ML-powered reconciliation (per-organization Random Forest, 97%+ accuracy, 80%+ auto-reconcile)
  - Months 14-15: White-label/embedded accounting, industry-specific modules (CIS, property, SaaS, practice management)

10.7. **Phase 4 Key Features Detail.** Multi-entity: automated intercompany elimination, entity-level + consolidated reporting, shared services allocation, cumulative translation adjustments. API platform: RESTful CRUD, webhooks (10+ events), rate limiting, SDKs in 5 languages, sandbox. Marketplace: app directory, OAuth2 installation, review process, 30+ pre-built integrations across 8 categories.

10.8. **Engineering Effort Summary.** MVP: 48 days (2-3 engineers). Phase 2: 65 days (3-4). Phase 3: 80 days (4-5). Phase 4: 105 days (5-7). Total: 298 days over 15 months. Risk: payroll (20 days, very high complexity), multi-entity (18 days, very high), ML reconciliation (15 days, very high).

10.9. **Xero Feature Parity Progression.** MVP (8 wks): 60% parity (core GL, invoicing, bank, VAT, reports). Phase 2 (M3-5): 75% (+automation, feeds, rules, MTD). Phase 3 (M6-9): 88% (+multi-currency, payroll, inventory, assets). Phase 4 (M10-15): 95%+ (+multi-entity, projects, marketplace, ML).

10.10. **Compliance Roadmap.** UK: MTD VAT (MVP preview -> Phase 2 submission -> Phase 3 multi-scheme -> Phase 4 group VAT). RTI Payroll (Phase 3 FPS/EPS). Companies House iXBRL (Phase 3 preview -> Phase 4 filing, mandatory April 2028). IFRS 18 (Phase 4, effective Jan 2027). International: EU VAT OSS (Phase 3), US Sales Tax (Phase 3), Australia GST (Phase 3).

10.11. **Technical Dependencies by Phase.** Phase 2: bank feeds depend on aggregator contract (medium risk), rules depend on feeds (low), MTD depends on HMRC dev account (medium). Phase 3: multi-tax requires research per jurisdiction (medium), payroll requires HMRC PAYE API (high), inventory requires GL + invoicing (medium). Phase 4: ML reconciliation needs historical data (medium), white-label needs multi-tenant architecture (medium).

10.12. **Skill Growth Trajectory.** MVP: 25+ skills. Phase 2: 65+ skills (+bank feeds, rules, recurring, documents, multi-user, approvals, MTD). Phase 3: 120+ skills (+multi-currency, multi-tax, inventory, assets, payroll, advanced reports, custom reports). Phase 4: 190+ skills (+multi-entity, projects, expenses, API platform, marketplace, ML reconciliation, white-label, industry modules).

## Required Tables

| Table # | Title | Columns |
|---------|-------|---------|
| T10-1 | Complete Roadmap Summary | Phase, Duration, Features, Skills, Effort (days), Team Size, Xero Parity |
| T10-2 | Phase 2 Feature List | Feature, Month, Description, Dependencies, Complexity, Effort |
| T10-3 | Phase 3 Feature List | Feature, Month, Description, Dependencies, Complexity, Effort |
| T10-4 | Phase 4 Feature List | Feature, Month, Description, Dependencies, Complexity, Effort |
| T10-5 | Engineering Effort by Phase | Phase, Effort (days), Team Size, Calendar Time |
| T10-6 | Xero Feature Parity Progression | Capability, Xero Features, Our Timeline, Parity % |
| T10-7 | UK Compliance Roadmap | Regulation, MVP, Phase 2, Phase 3, Phase 4 |
| T10-8 | International Compliance Roadmap | Jurisdiction, Phase 3, Phase 4 |
| T10-9 | Technical Dependencies by Phase | Feature, Depends On, Blocker Risk |
| T10-10 | Pre-built Marketplace Integrations | Category, Integration, Purpose |
| T10-11 | Webhook Events | Event, Description |
| T10-12 | Industry-Specific Modules | Industry, Features, Compliance Requirements |

## Required Diagrams

| Diagram # | Type | Description |
|-----------|------|-------------|
| D10-1 | Gantt chart | 15-month full roadmap with 4 phases, monthly deliverables, and compliance deadlines |
| D10-2 | Stacked bar chart | Xero feature parity progression by phase (60% -> 75% -> 88% -> 95%+) |
| D10-3 | Timeline diagram | Compliance roadmap overlay: EU AI Act (Aug 2026), IFRS 18 (Jan 2027), Companies House (Apr 2028) |
| D10-4 | Dependency graph | Phase-to-phase technical dependencies with blocker risk color-coding |
| D10-5 | Growth chart | SKILL count growth: 25 -> 65 -> 120 -> 190+ |

## Key Citations
- dim12: Complete phased roadmap (primary source)
- dim12: Feature lists per phase with complexity and effort
- dim12: Technical dependencies and blocker risks
- dim12: Xero feature parity progression
- dim12: Compliance roadmap (UK and international)
- dim12: Engineering effort summary (298 days)
- insight: EU AI Act compliance window (Aug 2026)
- insight: IFRS 18 reporting refresh market moment (Jan 2027)
- cross: MVP timeline conflict resolution (8-week lite + 6-month proper)

---

# Chapter 11: Risk Assessment & Mitigation
**Word Count Target:** 2,000-2,500 words

## Content Points

11.1. **Risk Methodology.** Risks assessed by likelihood (Low/Medium/High) and impact (Low/Medium/High/Very High). 10 primary risks identified. Mitigation strategies specified for each.

11.2. **Risk R1: HMRC API Changes.** Likelihood: Medium. Impact: High. HMRC may change MTD VAT API endpoints, authentication, or fraud prevention requirements. Mitigation: abstract HMRC API layer with adapter pattern; monitor HMRC developer updates; maintain compatibility layer.

11.3. **Risk R2: LLM Hallucination.** Likelihood: Medium. Impact: High. LLM may generate incorrect transactions, wrong account codes, invalid amounts. Mitigation: confirmation gates for ALL transactions; full audit trail; undo capability; deterministic validation layer catches 91.67% of errors; template-based generation (not raw double-entry).

11.4. **Risk R3: Open Banking Aggregator Downtime.** Likelihood: Medium. Impact: Medium. TrueLayer/Plaid may experience outages. Mitigation: multi-aggregator failover chain (TrueLayer -> Plaid -> Salt Edge -> Yodlee); manual CSV/OFX import always available as fallback.

11.5. **Risk R4: Exchange Rate API Failure.** Likelihood: Low. Impact: Medium. ECB/XE/Open Exchange Rates may be unavailable. Mitigation: cached rates (daily updates); manual override capability; fallback provider chain.

11.6. **Risk R5: Payroll Calculation Errors.** Likelihood: Low. Impact: Very High. PAYE/NICs errors can result in HMRC penalties and employee under/overpayment. Mitigation: extensive testing against HMRC calculators; beta with volunteer users; parallel run with existing payroll for 3 months before go-live.

11.7. **Risk R6: Multi-Entity Consolidation Errors.** Likelihood: Medium. Impact: High. Intercompany elimination errors produce incorrect consolidated financials. Mitigation: automated elimination checks; reconciliation reports; audit trail; non-negotiable capabilities from design (auto-elimination, entity+consolidated reporting).

11.8. **Risk R7: LLM Context Window Exceeded.** Likelihood: Medium. Impact: Medium. Large reports or long conversations may exceed token limits. Mitigation: streaming reports; pagination; summary-first approach; sliding window for conversation history (last 20 message pairs).

11.9. **Risk R8: Regulatory Deadline Changes.** Likelihood: Medium. Impact: Medium. IFRS 18, Companies House digital filing dates may shift. Mitigation: modular report architecture; configurable templates; presentation-layer mapping (not structural changes).

11.10. **Risk R9: Data Loss/Corruption.** Likelihood: Low. Impact: Very High. Critical for financial data. Mitigation: daily backups; append-only ledger (no data ever deleted); point-in-time recovery; hash-chained immutability detects tampering.

11.11. **Risk R10: Scaling Bottleneck.** Likelihood: Low. Impact: High. Transaction volume may exceed single-ledger capacity. Mitigation: read replicas for report queries; Redis caching; async processing; horizontal scaling via ledger sharding; PostgreSQL HA via Patroni.

11.12. **Coverage Gaps Requiring Follow-Up Research.**
  - Production load testing: no actual Formance benchmarks at scale (high severity)
  - Disaster recovery: no RTO/RPO specifications, no multi-region strategy (high)
  - HMRC MTD API integration details: no OAuth flow spec, no error handling (medium-high)
  - LLM production cost modeling: no TCO model, no token usage estimates (medium-high)
  - Payroll module deep design: no PAYE/NI/RTI FPS-EPS spec (medium)
  - Migration tooling from Xero/QBO: no detailed migration path (medium)
  - Mobile/offline architecture: no app design, no offline capability (medium)
  - Customer support/operations: no admin dashboard, no monitoring (medium)

11.13. **Conflict Zones Resolved.**
  - MVP timeline: resolved as two tiers (8-week MVP-lite with managed services + 6-month MVP-proper with full architecture)
  - Batch vs real-time: resolved as hybrid (real-time for chat, async/batch for background)
  - Single vs multi-agent cost: resolved as phased (supervisor + 4 core specialists for MVP, add others later)
  - Local vs cloud LLM: resolved as hybrid with data classification (pseudonymized cloud for standard, local for sensitive)
  - IFRS 18 vs current COA: resolved as metadata-driven presentation-layer mapping

11.14. **Architectural Consistency Score.** Overall: 87/100. Scores by category: Backend technology 95/100, Agent architecture 90/100, Data model 92/100, Transaction processing 88/100, Multi-currency 90/100, Tax engine 85/100, Reporting 88/100, Security/compliance 82/100, Bank feeds 80/100, Document processing 78/100, DevOps/deployment 75/100, Cost/business model 55/100.

## Required Tables

| Table # | Title | Columns |
|---------|-------|---------|
| T11-1 | Risk Register | ID, Risk, Likelihood, Impact, Mitigation, Owner |
| T11-2 | Coverage Gaps | Gap, Impact, Severity, Dimensions Touching, Action Required |
| T11-3 | Conflict Zones Resolution | Conflict, Dimensions, Resolution, Severity |
| T11-4 | Architectural Consistency Score | Category, Score, Rationale |
| T11-5 | Risk Heat Map Matrix | Likelihood x Impact grid with risk IDs positioned |

## Required Diagrams

| Diagram # | Type | Description |
|-----------|------|-------------|
| D11-1 | Heat map | Risk likelihood x impact matrix with 10 risks positioned |
| D11-2 | Radar/spider chart | Architectural consistency scores across 12 categories |
| D11-3 | Timeline diagram | Coverage gaps mapped to research timeline with severity |

## Key Citations
- dim12: Risk register (10 risks with likelihood, impact, mitigation)
- cross: Confidence tier summary (high/medium/low/conflict/gap)
- cross: 7 coverage gaps with severity ratings
- cross: 5 conflict zones with resolution recommendations
- cross: Architectural consistency score (87/100)
- cross: Cross-dimensional agreement heatmap
- insight: Risk assessment across all 14 strategic insights

---

# Chapter 12: Appendices
**Word Count Target:** 2,500-3,000 words (reference material, dense formatting)

## Appendix A: Chart of Accounts Templates

### Content Points
A.1. Complete COA template for **UK Limited Company -- VAT Registered** (65 accounts). Five categories with 4-digit codes:
  - Assets (1000-1999): Cash (1000-1090), Accounts Receivable (1100), Inventory (1200), Prepayments (1300), Fixed Assets (1500-1590)
  - Liabilities (2000-2999): Accounts Payable (2100), VAT Control (2200), Accruals (2300), Loans (2500-2590)
  - Equity (3000-3999): Share Capital (3000), Retained Earnings (3100), Dividends (3200)
  - Revenue (4000-4999): Sales (4000-4100), Other Income (4200-4300)
  - Expenses (5000-6999): Cost of Sales (5000-5100), Operating Expenses (5200-5999), Admin (6000-6999)

A.2. Abbreviated templates for other 7 variants showing key differences.

### Required Tables
| Table # | Title | Columns |
|---------|-------|---------|
| TA-1 | UK Ltd Co VAT COA (65 accounts) | Code, Account Name, Type, VAT Rate, Category |
| TA-2 | COA Template Comparison | Template, Entity Type, VAT, Account Count, Key Differences |

## Appendix B: Tax Matrix

### Content Points
B.1. UK VAT reference: standard 20%, reduced 5%, zero 0%, exempt. Registration threshold GBP 90,000. Nine-box return structure with calculation logic.
B.2. EU VAT summary: Germany 19%, France 20%, Ireland 23% (standard). OSS threshold EUR 10,000.
B.3. GST summary: Australia 10%, NZ 15%, Canada 5%, Singapore 9%.
B.4. US Sales Tax: economic nexus thresholds by state pattern.
B.5. DST rates: UK 2%, France 3%, Italy 3%, etc.

### Required Tables
| Table # | Title | Columns |
|---------|-------|---------|
| TB-1 | UK VAT Quick Reference | Rate Type, Percentage, Applicable To, Examples |
| TB-2 | Global VAT/GST Rates | Country, Tax Type, Standard Rate, Reduced Rate, Threshold |
| TB-3 | US Economic Nexus by State Pattern | Pattern, States, Revenue Threshold, Transaction Threshold |
| TB-4 | DST Rates by Country | Country, Rate, Global Revenue Threshold, Domestic Threshold |

## Appendix C: SKILL Registry

### Content Points
C.1. Complete registry of all 190+ skills across 4 phases. Organized by category with SKILL ID, description, parameters, risk level, approval requirement, phase introduced.
C.2. SKILL.md format template with YAML frontmatter example.
C3. Base parameter schema template.

### Required Tables
| Table # | Title | Columns |
|---------|-------|---------|
| TC-1 | MVP SKILL Registry (25+) | SKILL ID, Category, Description, Risk Level, Approval Required |
| TC-2 | Phase 2 Skills (+40) | SKILL ID, Category, Description, Risk Level |
| TC-3 | Phase 3 Skills (+55) | SKILL ID, Category, Description, Risk Level |
| TC-4 | Phase 4 Skills (+70) | SKILL ID, Category, Description, Risk Level |
| TC-5 | SKILL.md Format Template | Section, Content, Example |

## Appendix D: Glossary

### Content Points
D.1. Technical terms: Formance Ledger, Numscript, Bucket, Posting, Transaction, SKILL.md, Supervisor Pattern, MCP, HITL, ReAct, Plan-and-Execute, Saga, Circuit Breaker.
D.2. Accounting terms: Chart of Accounts, Double-Entry, Debit/Credit, VAT, GST, MTD, RTI, OSS, COGS, DSO, DPO, EBITDA, MPM, XBRL/iXBRL.
D.3. Regulatory terms: EU AI Act, GDPR, HMRC, PSD2, Economic Nexus, Place of Supply, Reverse Charge.

### Required Tables
| Table # | Title | Columns |
|---------|-------|---------|
| TD-1 | Technical Glossary | Term, Definition |
| TD-2 | Accounting Glossary | Term, Definition |
| TD-3 | Regulatory Glossary | Term, Definition, Jurisdiction |

## Appendix E: Cross-Verification Summary

### Content Points
E.1. Complete confidence tier table: all findings with tier, confirming dimensions, contradictions, action required.
E.2. Cross-dimensional agreement heatmap (simplified).

### Required Tables
| Table # | Title | Columns |
|---------|-------|---------|
| TE-1 | Full Confidence Tier Table | Finding, Tier, Confirming Dimensions, Contradictions, Action |

## Key Citations
- dim12: COA templates, skill registry
- dim05: Tax rates, thresholds, jurisdictions
- dim08: Report SKILL taxonomy
- dim01: Glossary terms
- dim09: Agent architecture terms
- cross: Full confidence tier summary

---

# Document Production Summary

| Chapter | Title | Word Target | Tables | Diagrams | Primary Sources |
|---------|-------|-------------|--------|----------|-----------------|
| 1 | Executive Summary | 1,200-1,500 | 4 | 2 | dim12, cross, insight |
| 2 | System Vision & Architectural Principles | 3,000-3,500 | 9 | 7 | dim01, dim09, insight |
| 3 | Core Ledger & Data Model | 3,500-4,000 | 9 | 6 | dim12, dim01, cross |
| 4 | Agentic Interface & LLM Chat | 4,000-4,500 | 13 | 8 | dim09, cross, insight |
| 5 | Financial Reporting SKILLs | 3,500-4,000 | 13 | 5 | dim08, dim12, insight |
| 6 | Multi-Standard, Multi-Currency & Tax | 4,000-4,500 | 15 | 6 | dim05, dim12, insight |
| 7 | Document Processing & Workflow Automation | 3,000-3,500 | 13 | 5 | dim12, dim09, insight |
| 8 | Security, Compliance & Audit Trail | 3,000-3,500 | 9 | 4 | dim01, dim09, insight |
| 9 | MVP Requirements Specification | 4,500-5,000 | 15 | 6 | dim12, dim01, dim09 |
| 10 | Phased Implementation Roadmap | 4,000-4,500 | 12 | 5 | dim12, insight, cross |
| 11 | Risk Assessment & Mitigation | 2,000-2,500 | 5 | 3 | cross, dim12, insight |
| 12 | Appendices | 2,500-3,000 | 11 | 0 | dim12, dim05, dim08 |
| **TOTAL** | | **38,700-44,000** | **128** | **57** | |

---

# Writing Guidelines

1. **Tone**: Technical, precise, authoritative. No marketing language.
2. **Citations**: Every claim must cite a source file. Use [^N^] format referencing the citation tables in each source document.
3. **Tables**: All tables must have a unique identifier (Chapter-Table#). Include column headers, consistent formatting.
4. **Diagrams**: Prefer Mermaid syntax for diagrams. Each diagram must have a unique identifier (Chapter-Diagram#). Include descriptive caption.
5. **Code**: Code snippets (Numscript, JSON schemas, SQL) should be in fenced code blocks with language tag.
6. **Consistency**: Use consistent terminology throughout. Refer to the glossary in Appendix D for standard definitions.
7. **Traceability**: Each content point has a numbered reference. Use these when cross-referencing within the document.
