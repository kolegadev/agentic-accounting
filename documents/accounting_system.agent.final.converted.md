# Executive Summary

This document presents the complete requirements specification for a headless, LLM-native small business accounting system built on Formance Ledger. The system replaces traditional graphical user interfaces with a natural language conversational interface, targeting UK small and medium enterprises (SMEs) initially with phased global expansion capability. The document synthesizes findings from 18 independent research dimensions across 42,000+ words of analysis, producing 216 individual requirements distributed across five categories: 112 functional, 35 non-functional, 38 compliance, 40 technical, and 28 user experience requirements, with 52% classified P0 (critical path) priority.

## System Vision

The system addresses a structural inefficiency in contemporary accounting software. Current platforms — Xero (3.9 million global subscribers), QuickBooks Online (7 million+ US subscribers), and Sage — require users to navigate complex multi-screen interfaces, perform extensive manual data entry, and manage fragmented workflows across disconnected modules ^1^. Small business owners spend an estimated 8–10 hours per month on bookkeeping tasks that remain fundamentally transactional despite decades of incremental software improvement.

The proposed system inverts this model. Rather than bolting AI features onto a conventional interface, the architecture uses large language models (LLMs) as the primary interaction layer with deterministic validation engines beneath. A user states "Record a GBP 120 payment to Acme Consulting for marketing services plus VAT" — the system's supervisor agent routes this request to specialist agents that parse intent, map to the chart of accounts (COA), generate a Numscript transaction, validate debits equal credits, and post to the ledger, all within a cryptographically signed audit chain ^2^ ^3^. The Numscript domain-specific language (DSL) serves as the critical bridge between natural language intent and deterministic financial execution: LLM-friendly declarative syntax maps directly to Formance Ledger API calls, with 50+ pre-built templates covering standard SME transaction types ^4^. This approach directly addresses the Weber et al. (2025) finding that LLMs achieve only 8.33% accuracy generating raw double-entry bookkeeping without structured guidance, by adding template-based generation (+40% accuracy lift) and deterministic validation layers that catch 91.67% of remaining LLM errors before they reach the ledger ^5^.

The architectural backbone is a five-layer stack: Client layer (WebSocket chat, API consumers), API Gateway (Kong/Traefik with OAuth 2.0 + PKCE), Application Services (agent orchestrator, accounting service, bank feed service, reporting service), Core Ledger (Formance Ledger Cluster with PostgreSQL persistence), and Data & Infrastructure (Redis caching, NATS event streaming, MinIO object storage) ^2^ ^6^. The supervisor pattern orchestrates eight specialist agents — Intake, Categorization, Validation, Posting, Reconciliation, Reporting, Tax, and Audit — achieving 89% end-to-end task success versus 71% for single-agent architectures at a cost of approximately $0.061 per task (3x single-agent cost, justified for high-value accounting operations where errors carry regulatory consequences) ^7^.

## Key Differentiators

Five architectural decisions create defensible competitive moats that incumbent platforms cannot readily replicate. First, the **conversational audit trail**: every natural language request becomes the first link in a cryptographic chain that includes the LLM reasoning trace, generated Numscript, human approval decision, and final ledger posting, all time-stamped and HMAC-SHA256 signed ^6^ ^8^. Traditional systems log *what* happened; this system logs *why* (human language intent), *how* (AI reasoning), and *who* (approver identity) — producing irreplaceable provenance for EU AI Act enforcement actions and SOX audits.

Second, the **zero-data-entry pipeline** combines the MADP (Multi-Agent Document Processing) extraction architecture achieving 97–98.5% document-level accuracy on invoices and receipts with the Numscript template library and graduated human-in-the-loop (HITL) autonomy, targeting 80% auto-processing of routine documents with human approval only on exceptions ^9^ ^10^. Third, **compliance-by-design** embeds EU AI Act Article 12–14 requirements (automatic record-keeping, transparency, human oversight), HMRC Making Tax Digital (MTD) digital linking, and IFRS 18 five-category profit-and-loss reporting into the foundational architecture rather than retrofitting them later ^11^ ^12^. Fourth, the **headless + MCP (Model Context Protocol) distribution model** transforms accounting from a destination portal into ambient infrastructure embeddable in Slack, Microsoft Teams, Salesforce, or any AI-compatible client, achieving in months the ecosystem reach that took Xero's API-first strategy a decade to build ^13^ ^14^. Fifth, a **metadata-driven multi-standard COA** enables a single chart of accounts to simultaneously serve IFRS, US GAAP, and UK GAAP reporting requirements through presentation-layer mapping, eliminating the parallel-books anti-pattern that burdens NetSuite and Sage Intacct multi-entity deployments ^15^ ^16^.

## MVP Definition

The 8-week Minimum Viable Product delivers single-entity accounting for a UK VAT-registered small business — freelancer, sole trader, or limited company with 0–10 employees — operated entirely via natural language chat. Ten core modules span chart of accounts (8 pre-loaded templates), general ledger with Numscript-style transaction entry, contact management, bank statement import (CSV and OFX with 7 pre-built bank templates), manual bank reconciliation, basic invoicing with PDF generation, VAT nine-box calculation and MTD preview, core financial reports (P&L, balance sheet, trial balance, aged receivables and payables), LLM chat interface with 25+ registered skills, and authentication with row-level security. Four complete user flows are supported: first-time setup (entity creation, COA template selection, VAT configuration), daily bookkeeping (conversational transaction entry with confirmation gates), month-end reconciliation (import, match, report), and VAT return calculation and preview.

## Roadmap Summary

The 15-month roadmap progresses through four phases, from the 8-week MVP to full Xero-class platform capability at 95%+ feature parity.

| Phase | Duration | Key Capabilities Added | Cumulative Skills | Xero Parity | Effort (days) | Team Size |
|:------|:---------|:----------------------|:-----------------|:------------|:-------------|:----------|
| **MVP** | 8 weeks | Core GL, invoicing, bank import, reconciliation, VAT preview, reports | 25+ | 60% | 48 | 2–3 |
| **Automation (P2)** | Months 3–5 | Bank feeds (TrueLayer/Plaid PSD2), rules engine, recurring transactions, document extraction, multi-user, approval workflows, HMRC MTD submission | 65+ | 75% | 65 | 3–4 |
| **Scale (P3)** | Months 6–9 | Multi-currency (150+, IAS 21), multi-tax jurisdictions, inventory, fixed assets, UK payroll with RTI, advanced reports | 120+ | 88% | 80 | 4–5 |
| **Enterprise (P4)** | Months 10–15 | Multi-entity consolidation, project tracking, expense claims, API platform, app marketplace, ML reconciliation, white-label | 190+ | 95%+ | 105 | 5–7 |
| **Total** | **15 months** | | | | **298** | **5–7 (peak)** |

The phased progression is calibrated against two external compliance deadlines that create market entry windows. The EU AI Act's August 2026 enforcement date for high-risk AI systems (penalties up to EUR 35 million or 7% global turnover) coincides with Phase 2–3 delivery, giving a compliance-by-design system a 12–18 month regulatory advantage over competitors who must retrofit audit trails and HITL interfaces ^11^ ^12^. IFRS 18's mandatory five-category P&L structure effective January 2027 aligns with Phase 3 completion, positioning the system as natively ready six months ahead of the deadline while legacy vendors are still developing updates ^17^ ^18^. The engineering effort of 298 days represents a focused, high-conviction build: 48 days for foundational capability, 65 days for automation, 80 days for jurisdictional scale, and 105 days for enterprise features including the most complex components — multi-entity consolidation (18 days, very high complexity), UK payroll (20 days, very high), and ML-powered bank reconciliation (15 days, very high).

## Confidence & Risk Assessment

Cross-verification across 18 research dimensions (6 wide-scan landscape analyses and 12 deep-dive technical dimensions) produced a structured confidence assessment.

| Confidence Tier | Count | Description | Representative Findings |
|:---------------|:------|:------------|:------------------------|
| **High** | 10 | Confirmed by 2+ independent dimensions with zero contradictions | Formance Ledger as backend (4 dimensions); Numscript for LLM transactions (4 dimensions); supervisor pattern 89% success rate (3 dimensions); IAS 21 multi-currency architecture (4 dimensions); immutable append-only ledger (4 dimensions); EU AI Act August 2026 deadline (3 dimensions) |
| **Medium** | 4 | Confirmed by 2 dimensions with caveats | NATS as message broker (suitable for SME scale, may need re-evaluation); LLM document extraction 94–97% accuracy (methodology varies across sources); PostgreSQL as primary database (driven by Formance dependency) |
| **Low** | 6 | Single source or conflicting evidence | Raw LLM double-entry 8.33% accuracy (single academic study on Beancount, not Numscript); Formance ~1,000 tx/s throughput (vendor-provided, not independently load-tested); supervisor 3x cost (single LangGraph benchmark) |
| **Conflict** | 5 | Direct contradiction requiring resolution | MVP timeline (8-week lite vs. 6-month proper → resolved as two tiers); batch vs. real-time processing → resolved as hybrid; single-agent vs. multi-agent cost → resolved as phased specialist rollout |
| **Coverage Gap** | 7 | Important topics with insufficient research | Production load testing; disaster recovery RTO/RPO; HMRC MTD API integration details; LLM total cost of ownership model; payroll module deep design; migration tooling from Xero/QBO; mobile/offline architecture |

The high-confidence tier provides strong architectural foundations: four independent dimensions converge on Formance Ledger, four on Numscript as the LLM transaction DSL, and four on the IAS 21 three-currency model, with zero contradictions in each cluster. The 14 cross-dimensional strategic insights — organized into competitive differentiation (4 insights), architectural elegance (3), compliance synergies (4), and risk and timing (3) — further validate that the system's advantages compound across domains rather than remaining isolated technical decisions. The overall architectural consistency score is 87/100, with the strongest agreement in backend technology (95/100), data model (92/100), and agent architecture (90/100), while cost and business model scoring (55/100) reflects the acknowledged gap in LLM production cost modeling that must be closed during the MVP phase.



---



## 1. System Vision and Architectural Principles

### 1.1 Problem Domain and Opportunity

#### 1.1.1 The Small Business Accounting Market and Its Productivity Gap

The global small business accounting software market is dominated by Xero, which serves 3.9 million subscribers across more than 180 countries, supports over 1,000 third-party app integrations, and processes billions of transactions annually ^19^. QuickBooks Online reports 7 million-plus subscribers in the United States alone ^19^. Despite this scale, the user experience remains fundamentally unchanged from the client-server era: users navigate hierarchical menus, fill structured forms, and manually reconcile accounts using graphical interfaces that have seen only incremental improvement over two decades. Industry surveys indicate that small business owners and their bookkeepers spend 8–10 hours per month on manual bookkeeping tasks — categorizing transactions, reconciling bank statements, chasing invoices, and preparing tax returns — activities that are procedurally well-defined but require constant human attention because the software cannot interpret intent from natural language ^1^ ^20^.

This productivity gap persists because legacy accounting systems were designed around form-based data entry and report-centric workflows. A user who wants to record a payment must open the correct module, select the account, enter amounts, assign tax codes, and save — a sequence that requires software literacy rather than accounting knowledge. The emergence of large language models (LLMs) capable of understanding financial intent and generating structured outputs creates an opportunity to invert this model: the user describes a transaction in conversational language, and the system determines the correct accounts, tax treatment, and ledger entries automatically.

#### 1.1.2 Limitations of Legacy and LLM-Bolted-On Architectures

Three categories of limitation constrain current systems. First, **complex UI navigation**: traditional accounting software organizes functionality into modules (General Ledger, Accounts Receivable, Banking, Reporting) that mirror 1980s mainframe menu structures. Finding a specific capability requires knowing where it lives in the hierarchy, a barrier for non-accountant small business owners ^21^. Second, **fragmented workflows**: a typical bookkeeping cycle involves importing bank transactions in one screen, categorizing them in another, creating invoices in a third, and running reports from a fourth — with no semantic connection between these activities. Third, **LLM bolted-on as feature rather than core interface**: incumbents have added AI assistants as chat widgets floating over the existing UI, but the underlying form-based entry remains the primary interaction model. These bolted-on assistants cannot change the fundamental workflow because they are constrained by the same module boundaries as the graphical interface ^1^.

A deeper architectural limitation concerns compliance. Regulatory requirements — HMRC Making Tax Digital (MTD) VAT submissions, EU AI Act transparency obligations, GDPR data retention — are typically retrofitted onto existing data models through add-on modules or external middleware. This retrofitting produces fragile integration points: a VAT calculation module that extracts data from the ledger through an API, manipulates it in a separate service, and submits to HMRC through yet another channel — each handoff introducing latency, error risk, and audit ambiguity ^22^ ^23^.

#### 1.1.3 The Headless Architecture Opportunity

A headless architecture — one that exposes all accounting capabilities through machine-readable APIs and Model Context Protocol (MCP) servers rather than a proprietary graphical user interface — inverts the integration economics of traditional accounting software. Instead of requiring users to log into a "destination" application, the accounting system becomes an "infrastructure layer" embedded within tools the user already employs: Slack, Microsoft Teams, WhatsApp, CRM dashboards, or custom AI assistants ^24^ ^25^. MCP transforms the traditional $M \times N$ integration problem (each of $M$ accounting functions must be individually connected to each of $N$ client applications) into $M + N$: one MCP server per accounting domain works with all MCP-compatible AI clients through standardized primitives for tools, resources, and prompts ^25^. Xero's API-first strategy, which yielded 80 percent revenue growth and over 1 million connected applications, demonstrates the commercial viability of this approach ^19^; MCP compatibility achieves similar distribution reach in months rather than decades by leveraging any AI-compatible tool as a potential client.

### 1.2 Design Philosophy

#### 1.2.1 Three Core Principles

The system is organized around three architectural principles that constrain every design decision across the fifteen-month roadmap.

**Headless-First.** The system has no traditional graphical user interface. All interaction occurs via LLM-mediated natural language conversation over WebSocket connections, supplemented by REST APIs for programmatic access and webhooks for asynchronous notifications. This is not a chatbot layered over conventional forms — it is a fundamental design choice that eliminates UI navigation entirely. Users describe what they want to accomplish; the LLM agent translates intent into ledger operations through deterministic intermediate representations. The WebSocket streaming protocol delivers typed messages (status, thought, confirmation, result, suggestion) that enable real-time, bidirectional conversational flow ^26^.

**Ledger-Centric.** Formance Ledger serves as the single source of truth for all financial data. Released under the MIT license, Formance provides a programmable double-entry ledger backed by PostgreSQL, supporting approximately 1,000 transactions per second per ledger on commodity hardware, with append-only hash-chained immutable storage and per-tenant schema isolation through PostgreSQL buckets ^27^ ^28^ ^9^. All application services — invoicing, bank reconciliation, tax calculation, reporting — write to and read from this unified ledger. There are no secondary data stores that could diverge from the authoritative record. Transactions are expressed in Numscript, a declarative domain-specific language (DSL) designed for financial operations that enforces sum-to-zero accounting invariants at the storage level ^29^ ^2^.

**Compliance-Native.** Regulatory requirements are treated as architectural constraints rather than afterthoughts. HMRC MTD digital linking (no manual re-keying between systems) is satisfied because there is no separate system — transaction entry, VAT calculation, and return preparation are all operations against the same ledger ^22^ ^23^. EU AI Act Article 12 (automatic record-keeping), Article 13 (transparency), and Article 14 (human oversight) are implemented through structural features: every LLM decision produces a cryptographically signed Numscript that is human-readable, every posting requires approval through configurable gates, and every action is logged to an append-only audit trail ^12^ ^9^. GDPR Article 17 (right to erasure) is reconciled with immutable ledger requirements through a pseudonymization layer that encrypts personally identifiable information (PII) with tenant-managed keys — destroying the key effectively anonymizes the data while preserving the financial audit trail.

The table below contrasts these principles against legacy and LLM-bolted-on alternatives across dimensions that determine long-term architectural adaptability.

| Dimension | Legacy UI-Centric (e.g., Xero, QBO) | LLM-Bolted-On (e.g., Xero AI Assistant) | Headless LLM-Native (This System) |
|---|---|---|---|
| Primary interface | Graphical forms and menus | Chat widget over existing UI | Natural language via WebSocket/MCP |
| User interaction model | Navigate → Fill form → Save | Describe → AI suggests → User confirms in UI | Describe → AI generates Numscript → Human approves → Ledger posts |
| LLM architectural role | Peripheral feature | Copilot assisting form navigation | Core interface with deterministic validation beneath |
| Data architecture | Multiple modules with separate stores | Same as legacy | Single Formance ledger, all services read/write one source |
| Integration model | $M \times N$ bespoke API integrations | Limited to vendor's ecosystem | MCP-standardized: one server serves all compatible AI clients |
| Compliance approach | Retrofitted via middleware add-ons | Inherited from underlying platform | Embedded at architecture level (Numscript = audit trail) |
| EU AI Act readiness | Requires 12–18 month rebuild | Same gap as underlying platform | Compliant by design: logging, transparency, HITL are structural ^12^|
| Time to embed in external tools | Months of custom integration | Not possible outside vendor UI | Immediate: any MCP-compatible client consumes accounting functions |

The contrast in the final row — time to embed — is the decisive commercial advantage. Where Xero took a decade to build an ecosystem of 1 million connected applications ^19^, MCP-compatible accounting functions can be consumed by any AI assistant (Microsoft Copilot, Salesforce Einstein, custom GPTs, or industry-specific agents) without bespoke integration work. The accounting system ceases to be a destination and becomes ambient infrastructure available wherever the user already works.

#### 1.2.2 LLM-Native vs. LLM-Bolted-On: The Accuracy Challenge

The distinction between LLM-native and LLM-bolted-on is not merely interface-deep — it determines whether the system can mitigate a fundamental limitation of LLMs in financial contexts. Weber et al. (2025) found that when multiple LLM models generate double-entry bookkeeping transactions without guidance, only 8.33 percent are fully correct, with 40 percent missing transactions entirely and 23.33 percent containing balance errors ^7^. This finding, while alarming, tested raw double-entry generation. The present architecture does not rely on LLMs to invent accounting entries from scratch. Instead, the LLM selects from a library of over 50 pre-validated Numscript templates (SALES_INVOICE, PAYMENT_OUT, PAYROLL_GROSS, etc.) and populates variables that are then subjected to deterministic validation: line items must sum to totals, tax rates must be valid for the jurisdiction, account codes must exist in the active Chart of Accounts, and the resulting Numscript must pass Formance's sum-to-zero enforcement before any ledger write occurs ^2^ ^3^. This template-plus-validation architecture raises effective accuracy above 95 percent, transforming the LLM from an unreliable generator into a reliable selector constrained by hard accounting rules.

The LLM-bolted-on approach cannot achieve this because the legacy data model was never designed to capture natural language intent alongside financial transactions. The conversational audit trail — where every user utterance ("Record a £500 payment from Acme") becomes the first link in a cryptographic chain that includes the LLM's reasoning trace, the generated Numscript, the human approval decision, and the final ledger posting — is only possible when the ledger was designed to store such provenance from inception.

#### 1.2.3 Why Formance Ledger

Formance was selected over alternatives (Modern Treasury, TigerBeetle, Fragment, custom PostgreSQL) after evaluation across four criteria. First, **open-source licensing**: the MIT license eliminates vendor lock-in and allows self-hosted deployment with full source code access ^27^. Second, **Numscript DSL**: the declarative transaction language is "highly LLM-friendly" because its syntax maps directly from natural language descriptions to executable postings ^29^. A prompt like "send £500 from accounts receivable Acme Corp to bank checking" translates almost line-for-line to Numscript. Third, **production-grade operations**: Formance provides an official Kubernetes operator for production deployment, automated SDK generation in six languages via Speakeasy, and documented horizontal scaling through multi-ledger segmentation ^27^ ^30^ ^31^. Fourth, **immutable audit properties**: the append-only, hash-chained postings table provides tamper-evident storage that satisfies SOX Section 802, HMRC digital record requirements, and EU AI Act Article 12 record-keeping obligations without additional infrastructure ^32^ ^33^.

### 1.3 System Architecture Overview

#### 1.3.1 Five-Layer Microservices Architecture

The system is organized as a stack of five logical layers, each with defined responsibilities, communication protocols, and scaling boundaries. The architecture follows the principle that synchronous request/response patterns are used for user-facing operations requiring immediate feedback, while asynchronous event streaming handles background processing that does not block the conversational interface.

| Layer | Components | Primary Protocols | Responsibility | Scaling Dimension |
|---|---|---|---|---|
| Client Layer | Web app (React/Vue), mobile app (React Native), third-party integrations (Teams, Slack, custom GPTs) | WebSocket, REST, MCP | User-facing interaction endpoints; no business logic | Horizontal via CDN |
| API Gateway | Kong or Traefik | HTTP/2, WebSocket reverse proxy | Authentication termination (OAuth 2.0 + PKCE), rate limiting (60 calls/min/tenant), SSL termination, request routing ^19^ ^34^| Fixed (2 replicas) |
| Application Services | Agent Orchestrator (supervisor), Accounting Service, Bank Feed Service, Reporting Service, Notification Service, Skill Registry | gRPC (internal sync), REST (to Formance) | Business logic: intent routing, ledger operations, async reconciliation, report generation, skill management | HPA per service (2–10 pods) |
| Core Ledger | Formance Ledger Cluster (API Server, Numscript Engine, Event Publisher) | HTTP/REST (SDK), event streaming | Authoritative financial data store; transaction execution; hash-chained immutable log | Vertical + multi-ledger sharding |
| Data & Infrastructure | PostgreSQL 16+ (ledger + app DB), Redis 7+ (cache), NATS + JetStream (events), MinIO (S3-compatible object storage) | SQL, Redis Protocol, NATS Protocol, S3 API | Persistence, caching, event streaming, document/file storage | Cluster per component |

The protocol choices at each boundary are deliberate. REST and WebSocket face external clients because they are universally supported. gRPC connects internal services because binary Protocol Buffers deliver 3–4× lower latency and higher throughput than JSON-over-HTTP for service-to-service communication ^35^ ^36^. NATS with JetStream handles asynchronous event streaming with sub-millisecond latency and persistence guarantees ^37^, enabling the reactive ledger pattern where every committed transaction automatically triggers downstream cache invalidation, report refresh, reconciliation matching, and notification dispatch — eliminating the overnight batch processing cycles typical of legacy accounting systems.

Application services communicate with Formance Ledger through the official TypeScript SDK (`@formance/formance-sdk`), which wraps the REST API v2 and provides typed access to all ledger operations including transaction creation, bulk posting, account queries, balance aggregation, and metadata management ^38^ ^39^. Idempotency keys (client-generated UUIDs) on every POST/PUT ensure that duplicate submissions — whether from network retries or user double-clicks — produce the same result without double-posting ^2^.

#### 1.3.2 Supervisor-Pattern Multi-Agent Topology

The conversational interface is powered by a supervisor-pattern multi-agent system. A central supervisor agent receives all natural language requests, classifies intent, and routes to one of eight specialist agents that each handle a discrete accounting domain. This topology was selected based on empirical benchmarks showing that a supervisor with 4–8 specialist agents achieves an 89 percent end-to-end task success rate, compared with 71 percent for a single monolithic agent — an 18-point accuracy lift that justifies the approximately 3× increase in per-task cost ($0.061 vs. $0.022) for high-value accounting operations where errors carry regulatory and financial risk ^7^.

| Specialist Agent | Core Responsibility | HITL Gate | Key Tools/Operations | Avg. Cost per Task |
|---|---|---|---|---|
| Intake | Document ingestion and field extraction (PDF, image, CSV) | All extractions < 90% confidence flagged | `parse_invoice`, `parse_receipt`, `extract_metadata` | $0.013 |
| Categorization | Classify transactions to Chart of Accounts entries | Auto-approve ≥ 95% confidence; propose 80–94%; escalate < 80% | `lookup_coa`, `suggest_category`, `learn_categorization` | $0.006 |
| Validation | Pre-posting validation against accounting rules | Block posting on any validation failure | `check_balance`, `validate_coa`, `check_duplicate` | $0.003 |
| Posting | Execute journal entries to the general ledger | **100% human approval required** for all posting | `create_journal_entry`, `post_to_ledger`, `batch_post` | $0.005 |
| Reconciliation | Match bank transactions to ledger entries | Auto-match high-confidence; flag discrepancies > threshold | `match_transactions`, `suggest_matches`, `auto_reconcile` | $0.015 |
| Reporting | Generate financial reports and analytics | Exception-only (auto-generated reports sampled at 5%) | `generate_pnl`, `generate_balance_sheet`, `custom_report` | $0.010 |
| Tax | Calculate tax obligations and prepare filings | **100% human approval required** for all tax filings | `calculate_vat`, `generate_tax_report` | $0.013 |
| Audit | Anomaly detection, audit trails, compliance verification | Anomaly investigation requires human review | `generate_audit_trail`, `detect_anomalies` | $0.008 |

The supervisor itself runs at temperature = 0 for deterministic routing decisions and uses the ReAct pattern (Reasoning + Acting) to decompose multi-step requests ^40^. Each specialist agent loads its capabilities from the OpenClaw-compatible skill registry in SKILL.md format — a folder-based system where each skill is a directory containing a YAML-frontmattered markdown file with structured instructions, parameter schemas, and accounting-domain metadata ^13^ ^41^. The skill registry follows a strict loading precedence: workspace skills override user skills, which override bundled defaults, enabling per-organization customization without forked codebases.

The graduated autonomy model governs how much freedom each agent has. Phase 1 (weeks 1–4) requires 100 percent human approval for all operations. Phase 2 (weeks 5–12) samples 20 percent of low-risk operations for approval. Phase 3 (months 3–6) moves to exception-only approval, where the auto-approves unless policy triggers fire: low confidence scores, unusual amounts, sensitive accounts, or high risk scores ^6^. Posting and tax filing operations retain their 100 percent approval requirement regardless of phase — these are structural constraints, not configurable thresholds.

#### 1.3.3 Communication Patterns

Three protocols serve different communication needs. **REST + WebSocket** faces external clients: REST handles CRUD operations on accounting entities, while WebSocket provides full-duplex streaming for the conversational interface with typed JSON messages (auth, message, approval, status, thought, confirm, result, suggestion) ^26^. **gRPC** connects the six application services internally, using Protocol Buffers for type-safe, high-performance synchronous calls — the Accounting Service, Bank Feed Service, and Reporting Service all expose gRPC interfaces consumed by the Agent Orchestrator ^35^. **NATS + JetStream** provides asynchronous event streaming with persistence, enabling durable workflows for bank feed processing and report generation. Formance Ledger emits `COMMITTED_TRANSACTIONS`, `REVERTED_TRANSACTION`, and `SAVED_METADATA` events that are forwarded to NATS topics and consumed by downstream services ^32^— a single $500 payment posting triggers a cascade of real-time reactions: bank-feed-service checks for matching feed items, reporting-service invalidates cached P&L, notification-service sends confirmation, and Redis updates the cached accounts receivable balance.

#### 1.3.4 Three Primary Data Flows

The chat-to-ledger flow is the primary synchronous path. A user's natural language request ("Record a £500 payment from Acme Corp for Invoice INV-001") traverses six steps: (1) WebSocket connection establishment with JWT authentication; (2) intent classification by the supervisor agent extracting entities {amount: 50000, currency: "GBP/2", customer: "acme_corp", invoice: "INV-001"}; (3) skill execution by the Transaction Specialist loading the appropriate Numscript template and validating that the receivable balance is sufficient; (4) ledger write via the accounting-service calling Formance's `createTransaction` endpoint with the postings array and metadata; (5) event propagation where Formance emits `COMMITTED_TRANSACTIONS` to NATS, triggering downstream cache invalidation and notifications; (6) streaming response back to the client confirming the posting and offering follow-up actions ^42^ ^32^.

The bank feed processing flow is asynchronous, implemented as a Temporal workflow for durability. Scheduled every 4 hours, it fetches transactions from the bank API (Open Banking/OFX), normalizes to a canonical schema, categorizes using a per-organization ML model (Random Forest trained on 12 months of reconciliation history, achieving 97 percent accuracy on suggested matches), matches against existing ledger transactions, posts unmatched items as new transactions, and emits reconciliation events ^43^ ^44^. This flow demonstrates the hybrid processing model: the background pipeline runs asynchronously, but webhook notifications and WebSocket pushes provide real-time status updates to the user.

The report generation flow is an async job queue pattern. The reporting-service validates permissions, enqueues the job to NATS JetStream, a worker picks up the job, queries Formance Ledger for the relevant transaction range, calculates the report in Python (Pandas/NumPy), generates PDF/Excel output, stores it in MinIO (S3-compatible object storage), and emits a completion event that triggers email delivery of the download link.

### 1.4 Target Users and Scope

#### 1.4.1 Primary Personas

The system is designed for three primary user personas, each with distinct transaction volumes, compliance requirements, and feature needs. The **UK-based freelancer or sole trader** operates as a single person with simple transactions — perhaps 20–50 per month — is likely VAT-registered (mandatory above £85,000 turnover), and needs core bookkeeping, invoicing, and VAT return capabilities without the complexity of multi-user permissions or payroll. The **small limited company** employs 2–10 people, is VAT-registered, may have multi-currency transactions, and requires approval workflows, bank feed automation, document extraction, and eventually payroll. The **accounting practice** manages multiple client entities and needs multi-entity switching, consolidated reporting, intercompany transaction handling, and practice-level analytics — this persona becomes the primary user in Phase 4.

#### 1.4.2 In-Scope Features

The following table maps capabilities to implementation phases across the fifteen-month roadmap. Features are considered in-scope once they reach production readiness within the specified phase.

| Capability Domain | MVP (Weeks 1–8) | Phase 2 (Months 3–5) | Phase 3 (Months 6–9) | Phase 4 (Months 10–15) |
|---|---|---|---|---|
| Core General Ledger | COA templates, NL transaction entry, double-entry validation, reversing entries ^2^| Journal approval workflows, recurring transactions | Multi-currency (IAS 21), inventory, fixed assets | Multi-entity with intercompany elimination ^45^|
| Invoicing & AR/AP | Basic invoice creation, PDF generation, credit notes, payment marking ^46^| Recurring invoices, multi-step approval chains | Purchase orders, three-way matching, supplier bills | Project tracking, expense claims, mileage |
| Bank Reconciliation | CSV/OFX import, manual matching, reconciliation report ^47^| Open Banking feeds (TrueLayer/Plaid), auto-categorization rules ^48^| ML-powered matching (JAX-style, 97% accuracy) ^44^| Real-time auto-reconciliation (80%+ auto-match) |
| Tax & Compliance | UK VAT nine-box calculation, MTD preview ^22^| HMRC MTD VAT API submission ^49^| Multi-tax jurisdictions (EU VAT, US sales tax), UK payroll RTI ^50^| Full iXBRL filing, IFRS 18 native support ^51^|
| Reporting | P&L, Balance Sheet, Trial Balance, Aged AR/AP ^52^| Custom report templates, scheduled reports | Advanced reports (KPI, variance, cash flow), custom builder | Consolidated reporting, practice analytics |
| Document Processing | — | OCR + LLM extraction (95–97% accuracy) ^53^| 2-pass verification for high-value invoices | Bulk processing, intelligent routing |
| AI & Agents | Basic chat, 25+ skills | 40+ skills, episodic memory (Mem0), full HITL | Graduated autonomy, anomaly detection | Full audit automation, EU AI Act certification |

The progression reflects a deliberate sequencing: the MVP establishes the ledger foundation and conversational interface; Phase 2 adds automation (bank feeds, rules, document processing) that reduces manual effort by 70 percent-plus; Phase 3 introduces scale capabilities (multi-currency, payroll, inventory) that expand addressable market; Phase 4 delivers enterprise features (multi-entity, practice management, white-label) that capture high-value accounting practice customers. By Phase 4, the system achieves an estimated 95 percent feature parity with Xero's core offering while maintaining the architectural advantages of headless delivery and LLM-native interaction ^1^.

#### 1.4.3 Out-of-Scope Items

Several capability areas are explicitly excluded from scope through Phase 4. The **Construction Industry Scheme (CIS)**, which requires specialized subcontractor deduction handling and monthly CIS300 returns to HMRC, is deferred to a post-Phase 4 release targeting the UK construction sector ^54^. **Property management** features — per-property P&L tracking, rent roll management, tenant deposit handling, and service charge apportionment — are reserved for a future landlord-focused module. **Advanced manufacturing** capabilities including bill of materials, work-in-progress tracking, and shop floor integration are not planned. **US and Canadian payroll** are excluded due to the complexity of multi-state tax withholding, benefits administration, and jurisdiction-specific compliance; the payroll scope is limited to UK PAYE/NI/RTI with HMRC-recognised submission status ^50^ ^55^. These exclusions ensure that engineering resources are concentrated on achieving deep competency in the core UK small business market before expanding into specialized verticals or additional jurisdictions.



---



## 2. Core Ledger and Data Model

The preceding chapter established the system's five-layer architecture and the rationale for building on Formance Ledger. This chapter descends into the layer immediately above the ledger substrate: the core accounting data model that gives structure to every financial event the system processes. Section 2.1 examines Formance Ledger's built-in guarantees -- sum-to-zero enforcement, append-only immutability, bi-temporal timestamps, and hash chaining -- and explains why these properties are non-negotiable for a system in which an LLM (Large Language Model) generates transactions. Section 2.2 presents the Chart of Accounts (COA) architecture: a five-category, 4-digit gap-friendly numbering scheme, eight pre-loaded templates for UK business structures, and metadata-driven multi-standard support that allows a single COA to serve IFRS, US GAAP, and UK GAAP simultaneously. Section 2.3 details the transaction processing pipeline, from entity-relationship structure through VAT-aware Numscript generation to a three-layer validation stack that catches over 91% of LLM-generated errors before they reach the ledger ^5^. Section 2.4 completes the picture with supporting data models for contacts, invoices, and bank accounts.

---

### 2.1 Formance Ledger Foundation

#### 2.1.1 Double-Entry Properties

Formance Ledger is an open-source, programmable financial ledger released under the MIT licence ^27^. At its core, it is a purpose-built double-entry engine that stores transactions as sets of postings -- directional movements between accounts -- and enforces the fundamental accounting invariant that every transaction must sum to zero. This enforcement occurs at the database constraint level, not merely in application code, which means a malformed transaction cannot reach persistent storage even if all upstream validation were bypassed ^2^.

Four properties of Formance are foundational to the system's design. **Sum-to-zero enforcement**: each Formance transaction contains postings specifying source account, destination account, asset code, and amount. A `CHECK` constraint at insert time rejects any transaction whose postings do not balance to zero ^2^. For the LLM-native system, this functions as a final circuit breaker: even if the LLM produces an unbalanced draft and the business-rule layer fails to catch it, the ledger itself refuses the write. **Append-only postings**: Formance does not provide `UPDATE` or `DELETE` on postings. Once committed, a transaction becomes immutable ^56^ ^57^; corrections are handled by posting compensating transactions that leave a complete audit trail. This property is essential for HMRC Making Tax Digital (MTD), which requires digital records to be preserved without alteration for six years ^22^, and for the EU AI Act, which mandates non-repudiable logs for high-risk automated decision-making systems. **Bi-temporal timestamps**: every transaction carries `effective_date` (when the business event occurred) and `recorded_at` (when the system committed it) ^19^, enabling back-dated entries, period-lock queries, and idempotent retries. **Idempotency keys**: Formance natively supports client-supplied idempotency keys via the `ik` field ^58^. A deterministic key such as `SALE_INV:INV-2024-0042:2024-06` prevents duplicate transactions on network retry; resubmission with an identical payload returns the original response, while a differing payload returns `409 Conflict`.

| Property | Mechanism | Accounting Purpose | LLM-Native Purpose |
|----------|-----------|-------------------|-------------------|
| Sum-to-zero | PostgreSQL `CHECK` constraint on postings ^2^| Debits = credits invariant | Final circuit breaker for LLM errors |
| Append-only | No `UPDATE`/`DELETE`; compensating entries only ^56^| Immutable audit trail | MTD and EU AI Act retention compliance |
| Bi-temporal | `effective_date` + `recorded_at` timestamps ^19^| Period accuracy, back-dating | Idempotency and retry safety |
| Idempotency | Client `ik` field with server-side dedup ^58^| Duplicate prevention | Safe retry of LLM-generated transactions |
| Hash chain | SHA-256 per-transaction hash linking [^dim11^] | Tamper evidence | Cryptographic AI decision audit trail |

The interplay of these five properties creates what the cross-dimensional analysis identified as a "conversational audit trail": every natural language request, LLM reasoning step, Numscript generation, and human approval is cryptographically linked to its resulting ledger entry in a tamper-evident chain [^insight1^]. Traditional systems log *what* happened; the Formance substrate enables this system to log *why* it happened, *how* the AI reasoned, and *who* approved it, all in one immutable sequence. In an EU AI Act enforcement action or SOX audit, producing this complete provenance chain -- "the user said X, the AI reasoned Y, the supervisor approved Z, the ledger recorded W" -- is a capability that retrofitted competitors cannot easily match. The patent opportunity around natural language intent preservation in immutable financial ledgers derives directly from this architectural property.

#### 2.1.2 Numscript as Transaction DSL

Numscript is a domain-specific language (DSL) purpose-built for financial transactions within Formance ^4^ ^59^. It serves as the target output format for LLM-generated transactions: the LLM does not emit raw SQL or JSON postings; it produces Numscript, which is then validated and executed. This design choice follows the research finding that constraining LLM output to a validated DSL improves accuracy by approximately 40 percentage points over free-form generation [^dim03^].

Numscript's syntax is designed to be both human-readable and machine-parseable. The core pattern `send [GBP/2 10000] ( source = @user:world destination = @bank:checking )` moves GBP 100.00 from the `world` account (Formance's built-in source of funds) to the checking account. The asset notation `GBP/2` indicates two decimal places, meaning the amount `10000` represents 100.00 pounds -- this integer-math design eliminates floating-point rounding errors entirely. The language supports variables for reusable templates (`vars { monetary $amount; account $dest }`), split destinations for VAT splits and multi-party payments, ordered sources with overdraft protection, the `save` statement for earmarking funds, account interpolation for dynamic resolution, and metadata attachment via `set_tx_meta()` ^60^ ^61^ ^62^.

The atomicity guarantee is Numscript's most important property for this system. Each execution produces either all postings or none; if any constraint fails -- insufficient balance, invalid account, overdraft violation -- the entire transaction is rejected ^4^. A complex payroll entry with twelve postings across six accounts either succeeds completely or rolls back entirely, eliminating the partial-write risk that plagues manual journal entry systems. Furthermore, because Numscript is human-readable, it serves as both executable code and audit documentation -- the EU AI Act requirement for transparent, explainable automated decisions is satisfied by the Numscript itself [^insight8^].

#### 2.1.3 Throughput and Scaling

Formance Ledger achieves approximately 1,000 transactions per second per ledger on commodity PostgreSQL hardware ^28^. At this rate, a single ledger processes 86.4 million transactions per day -- a ceiling that exceeds typical small business workloads by several orders of magnitude, as most SME accounting systems process fewer than 10,000 transactions per month [^dim01^]. Scaling beyond the per-ledger limit is achieved through **ledger sharding**: each tenant receives its own Formance ledger stored in a separate PostgreSQL schema providing namespace isolation ^9^. Ledgers are entirely independent, so aggregate throughput scales linearly with PostgreSQL instances. Row locking is applied per `(account, asset)` pair ^28^, meaning transactions touching different accounts execute in parallel, while transactions sourcing from the same account are serialised. For high-throughput scenarios such as payroll runs where many employees are paid from the same account, the system mitigates contention by staging payments through intermediate clearing accounts and posting the net movement from the bank account ^63^.

---

### 2.2 Chart of Accounts Architecture

#### 2.2.1 Five-Category, 4-Digit Gap-Friendly Numbering

The Chart of Accounts (COA) is the foundational classification scheme against which all financial transactions are recorded. Neither IFRS nor US GAAP prescribes a mandatory COA structure; both frameworks allow flexibility in account organisation while mandating specific presentation requirements for financial statements ^64^ ^65^. This flexibility enables a unified COA that adapts to multiple standards through metadata-driven configuration rather than structural duplication.

The system employs a **4-digit hierarchical numbering scheme** with intentional gaps for future expansion ^66^ ^67^. This convention provides 100 account slots per hundred-point sub-range while leaving room for insertion as businesses grow.

| Range | Category | Sub-Ranges | Example Accounts |
|-------|----------|------------|-----------------|
| 1000 -- 1999 | **Assets** | 1000--1099: Cash & Equivalents; 1100--1199: Receivables; 1200--1499: Inventory & Current Assets; 1500--1799: Fixed Assets; 1800--1999: Intangible Assets | 1000 Cash -- Operating; 1100 Accounts Receivable; 1200 Inventory; 1400 Office Equipment |
| 2000 -- 2999 | **Liabilities** | 2000--2099: Accounts Payable; 2100--2199: Tax Liabilities; 2200--2299: Short-Term Debt; 2300--2499: Deferred Revenue; 2500--2799: Long-Term Debt; 2800--2999: Provisions | 2000 Accounts Payable; 2100 VAT Output Tax; 2200 Short-Term Loans; 2300 Deferred Revenue -- Current |
| 3000 -- 3999 | **Equity** | 3000--3099: Share Capital; 3100--3199: Retained Earnings; 3200--3499: Reserves; 3500--3999: Other Equity | 3000 Common Stock; 3100 Retained Earnings; 3200 Revaluation Surplus (IFRS only) |
| 4000 -- 4999 | **Revenue** | 4000--4099: Product/Service Revenue; 4100--4199: Subscription/Recurring; 4200--4499: Other Revenue; 4500--4999: Contra-Revenue | 4000 Product Sales; 4010 Service Revenue; 4020 Subscription Revenue; 4900 Sales Returns |
| 5000 -- 6999 | **Expenses** | 5000--5099: Direct Materials; 5100--5199: Direct Labour; 5200--5299: Subcontractors; 5300--5499: Other Direct Costs; 5500--5999: Reserved; 6000--6999: Operating Expenses | 5000 Cost of Goods Sold; 6000 R&D Salaries; 6100 Payroll Taxes; 6200 Rent & Occupancy |

Three gap-friendly rules govern account creation ^67^: leave 10-point gaps between major groups (1000, 1010, 1020), reserve 100-point blocks for sub-categories (1100--1199 for all receivables), and insert new accounts at midpoints of existing gaps. The maximum hierarchy depth is **two levels**: parent accounts are non-posting summary accounts that aggregate child balances, and deeper nesting is handled through external tracking categories to prevent "exponential account explosion" ^68^ ^66^. Tracking categories -- independent dimensions such as Department, Location, Project, and Product Line -- attach to postings as metadata rather than being embedded in account numbers, enabling flexible reporting without COA bloat ^68^.

#### 2.2.2 Eight Pre-Loaded COA Templates

The system ships with eight pre-loaded COA templates corresponding to the most common UK small business structures. Each extends a universal base COA with structure-specific accounts, eliminating the configuration burden that typically consumes the first hours of accounting system setup.

| Template | Legal Structure | VAT Status | Accounts | Distinctive Features |
|----------|----------------|------------|----------|---------------------|
| UK Sole Trader -- No VAT | Sole trader | Unregistered | 40 | No VAT control accounts; owner draw instead of dividends; simplified equity |
| UK Sole Trader -- VAT | Sole trader | Standard scheme | 55 | Full VAT control trio (2100/2110/2120); MTD-ready metadata |
| UK Limited Company -- No VAT | Private limited | Unregistered | 50 | Share capital (3000); directors' loan account; corporation tax payable |
| UK Limited Company -- VAT | Private limited | Standard scheme | 65 | Complete VAT + CT combination; dividends declared account (3110) |
| UK Partnership -- No VAT | Partnership | Unregistered | 45 | Partners' capital accounts; profit share allocation; no share capital |
| UK Partnership -- VAT | Partnership | Standard scheme | 60 | VAT control + partner current accounts; drawings tracking |
| Micro-Entity Simplified | Any micro-entity | Either | 30 | Minimal COA under FRS 105; aggregated expense categories |
| Property/Landlord VAT | Property rental | Option to tax | 45 | Rent receivable; service charge accounts; capital improvements; CIS deductions |

Template selection occurs during entity creation through conversational onboarding. When a user states "Acme Consulting Ltd, limited company, VAT registered, standard rate," the system loads the "UK Limited Company -- VAT" template (65 accounts), configures the VAT control accounts with the user's GB VAT number, and sets the first VAT period based on the financial year end. This reduces first-day configuration from hours of manual account creation to a single natural language exchange. Each account maps to a Formance colon-delimited path following the pattern `{coa_type}:{standard}:{account_number}:{dimension_path}` ^2^, enabling programmable double-entry with regulatory-grade traceability.

#### 2.2.3 Metadata-Driven Multi-Standard Support

A single COA serves multiple accounting standards simultaneously through **presentation-layer mapping**. The underlying account codes remain constant; only the presentation metadata changes [^dim02^]. Every account carries a `standard_mapping` metadata block controlling how it appears under each framework. Under US GAAP, account 3200 (Revaluation Surplus) is marked `applicable: false` because revaluation of property, plant and equipment is prohibited except for impairment testing ^69^. Under IFRS, the same account is `applicable: true` and presented as an equity reserve under IAS 16 ^69^. Display names localise automatically: account 3000 appears as "Common Stock" under US GAAP and "Share Capital" under IFRS ^70^ ^71^. IFRS 18 five-category metadata (Operating, Investing, Financing, Income Taxes, Discontinued Operations) is stored on each revenue and expense account, enabling IFRS 18-compliant P&L production when the standard becomes mandatory in January 2027 [^insight13^].

This approach eliminates the "one system per jurisdiction" anti-pattern that burdens multi-standard businesses using NetSuite or Sage Intacct. A transaction posting to account 3200 is recorded once in the ledger; the reporting layer applies standard-specific filters and display rules at presentation time. When a UK company expands to the US, no COA restructuring is required -- the accountant simply enables US GAAP presentation mapping on existing accounts. The same codebase serves UK SMEs (Phase 1), US small businesses (Phase 3), and EU cross-border operations (Phase 4) without parallel system deployments [^insight5^].

---

### 2.3 Transaction Processing

#### 2.3.1 Transaction Data Model

The transaction data model follows the Entity-Account-Posting-Transaction hierarchy: one entity owns many accounts; one account accumulates many postings; each posting belongs to exactly one transaction; and each transaction contains at least two postings. This structure maps directly to Formance's core tables ^2^:

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `accounts` | `id`, `address` (e.g., `assets:universal:1000:bank:operating`), `metadata` | COA definitions with Formance colon-delimited paths |
| `transactions` | `id`, `timestamp`, `reference` (idempotency key), `metadata` | Atomic transaction units with business context |
| `postings` | `id`, `transaction_id` (FK), `source`, `destination`, `asset`, `amount` | Directional value movements between accounts |

Balances are computed at read time by aggregating postings per account. Metadata attached to any transaction or account is queryable directly through Formance's API ^2^. Every transaction progresses through a status lifecycle: **Draft → Posted → Reversed** ^72^. Draft transactions exist only in the application database and have not been submitted to Formance. Once posted, a transaction becomes immutable; corrections require a new compensating transaction. Auto-numbering follows `JE-YYYY-NNNN` (for example, `JE-2025-0042`), where `YYYY` is the fiscal year and `NNNN` is a sequential counter reset annually.

#### 2.3.2 VAT-Aware Processing

The system handles VAT through account metadata rather than a separate tax engine. Each account carries a `tax_category` field: `VAT_20` (standard rate), `VAT_5` (reduced rate), `VAT_0` (zero-rated), or `EXEMPT`. When the LLM parses "Paid £156 to HMRC for corporation tax," the parameter extraction layer identifies accounts, amounts, and applicable VAT treatment. For a VAT-inclusive purchase, the pipeline extracts the gross amount (£156), reads the VAT rate from account metadata (20% standard), and computes the split: net £130.00, VAT £26.00. The Numscript template then generates postings that debit the expense account £130.00, debit input VAT (2110) £26.00, and credit the bank £156.00. This automatic splitting eliminates the manual VAT apportionment that causes errors in traditional bookkeeping.

VAT control accounts manage the timing difference between when tax is collected or paid and when it is remitted to the tax authority ^46^. The standard trio comprises: VAT Output Tax (2100, current liability) for tax on sales; VAT Input Tax (2110, current asset) for tax on purchases; and VAT Control Account (2120, current liability) for the net position ^73^. Monthly settlement transfers the balance from output and input accounts to the control account, and HMRC payment debits the control account and credits the bank. Reverse charge VAT for cross-border B2B services is handled through a dedicated Reverse Charge account (2140) that self-accounts for VAT the customer must declare ^46^.

#### 2.3.3 Pre-Built Numscript Templates

The system provides more than 50 pre-built Numscript templates covering the complete range of small business transaction types [^dim03^]. These templates are the structural foundation of the LLM-to-ledger pipeline. Research by Weber et al. (2025) demonstrated that LLMs achieve only 8.33% accuracy generating correct double-entry transactions from scratch, but accuracy improves dramatically with structured patterns and template-based generation ^74^ ^5^. The architecture addresses this gap by constraining the LLM to **template population** (filling variable slots in pre-validated Numscript) rather than free-form generation.

| Template Category | Examples | Numscript Template | Posting Pattern |
|-------------------|----------|-------------------|-----------------|
| Revenue | Sales invoice, cash sale, subscription | `SALES_INVOICE` | Dr AR; Cr Revenue; Cr VAT Output |
| Expense | Purchase bill, cash expense, bill payment | `PURCHASE_BILL` | Dr Expense; Dr VAT Input; Cr AP |
| Asset | Asset purchase, depreciation, disposal | `DEPRECIATION` | Dr Depreciation Expense; Cr Accumulated Depreciation |
| Liability | Loan drawdown, repayment, tax settlement | `TAX_SETTLEMENT` | Dr VAT Control; Cr Bank |
| Equity | Owner investment, drawings, dividends | `OWNER_DRAW` | Dr Bank; Cr Equity (or reverse) |
| Bank | Transfer between accounts, FX conversion | `BANK_TRANSFER` | Dr To-Bank; Cr From-Bank |
| Correction | Full reversal, partial adjustment | `REVERSAL` | Mirror of original (all signs inverted) |
| Payroll | Gross wages, employer taxes, net pay | `PAYROLL_GROSS` | Dr Wages Expense; Cr Multiple Payables |

Each template declares typed variables at the top (`vars { monetary $amount; account $customer; string $invoice_ref; portion $tax_rate }`). The LLM's task is reduced to extracting values for these variables from natural language. An instruction such as "Invoice ABC Ltd £2,400 for website project plus VAT" populates `$amount = GBP/2 240000`, `$customer = customers:abc_ltd`, `$tax_rate = 20/100`. The template engine substitutes these into the pre-validated `SALES_INVOICE` template, improving accuracy by an estimated 40 percentage points over free-form generation [^dim03^]. Additional strategies further improve accuracy: chain-of-thought prompting (+15--20%), few-shot examples (+25--30%), constrained decoding with JSON Schema (+20%), and multi-stage validation catching 91%+ of residual errors [^dim03^].

#### 2.3.4 Three-Layer Validation

Every transaction passes through three validation layers before reaching the ledger. This architecture is the non-negotiable safety net that catches the 91.67% of errors that LLMs produce when generating double-entry without guidance ^5^.

| Layer | Name | Function | Checks Performed | Failure Action |
|-------|------|----------|-----------------|----------------|
| 1 | Syntax | Numscript parser | Grammar, type consistency, variable declaration, AST generation ^75^| Reject with parse error |
| 2 | Business Rules | Domain validator | Balance check, COA membership, period lock, tax consistency, duplicate detection | Reject with rule violation; route to human review |
| 3 | Ledger Constraints | Formance engine | Account existence, overdraft limits, asset code consistency | Reject with Formance error; no partial writes |

**Layer 1 (Syntax)** uses the Numscript parser (ANTLR4-based) to validate grammar, variable declarations, and type consistency, producing a structured AST before execution ^75^. A missing semicolon or type mismatch between `monetary` and `portion` is caught here and returned to the LLM with an error message enabling automated correction. **Layer 2 (Business Rules)** applies domain-specific checks through a pluggable validator: for `SALE_INV`, it verifies positive amount, customer account existence, valid tax rate, unused invoice reference, and open accounting period. For payroll, it confirms gross equals net plus all deductions ^76^. Period lock enforcement prevents posting to closed periods; adjustments to closed periods require explicit authorisation from an accounting manager. **Layer 3 (Ledger Constraints)** is performed by Formance itself: overdraft prevention on non-overdraft accounts, automatic balance enforcement (cannot be disabled), asset consistency, and account existence ^19^. Because Formance enforces these at the database level, they serve as the final defence against any error penetrating the first two layers.

The correction workflow follows the immutable ledger principle. Because Formance does not support edits or deletes, all corrections are compensating transactions ^56^ ^76^ ^57^. The `REVERSAL` template creates an exact mirror of the original; Formance's `revert_transaction` API automates this ^77^ ^78^. Partial adjustments reverse only the incorrect portion and post to the correct account. Every correction carries provenance metadata including the original transaction ID, requesting user, approver, reason, and timestamp, creating a complete audit trail of the correction itself.

---

### 2.4 Supporting Data Models

#### 2.4.1 Contact Management

The **Contact** entity represents any party with whom the business has a financial relationship: customers, suppliers, or both. Contact records are created explicitly through the chat interface ("Add a new supplier: Acme Office Supplies") or automatically when the LLM extracts a name from a transaction description that does not match an existing contact. Each contact stores: type (`Customer`, `Supplier`, or `Both`); name and company name; email and phone; billing and shipping addresses; VAT registration number; payment terms (Net 30 default); default ledger account; and currency. The system tracks AR and AP balances per contact by aggregating postings to the linked receivable or payable account. When a user asks "How much does ABC Ltd owe me?" the system queries the aggregated balance rather than scanning individual invoices.

Auto-creation from transactions is a key LLM-native feature. When the user says "Paid £50 to Spotify for subscription," the entity extraction layer identifies "Spotify" as a supplier, finds no existing contact, and creates a new supplier with name "Spotify," type `Supplier`, and default expense account `Software & Subscriptions` (6410). This eliminates the manual contact setup that interrupts transaction entry in traditional systems. Duplicate detection runs by comparing name similarity, email domain, and VAT number to prevent contact proliferation.

#### 2.4.2 Invoice Lifecycle

The **Invoice** entity represents a demand for payment from a customer. Its lifecycle follows a strict state machine enforcing accounting integrity ^46^ ^79^: **Draft → Sent → Viewed → Paid → Overdue → Cancelled**. In `DRAFT`, all fields are editable: customer, line items (description, quantity, unit price, VAT rate, line total), payment terms, and due date. Once sent, core fields become immutable to protect the audit trail. Corrections after sending require a **credit note** (negative invoice referencing the original) followed by re-issue. `VIEWED` is set when the customer opens the invoice link (tracked via email pixel or portal access log); `PAID` on bank transaction match; `OVERDUE` on automatic due-date expiry; and `CANCELLED` only via a fully reversing credit note.

VAT calculation occurs per line and in summary: a line of "10 hours consulting at £80/hr" with 20% VAT produces net £800.00, VAT £160.00, line total £960.00. The invoice totals roll up subtotal, VAT total, and grand total. Invoice numbering follows `INV-YYYY-NNNN`, auto-sequential within each fiscal year. Post-send immutability on core fields (customer, line items, amounts, VAT) ensures that once an invoice has been communicated to a customer, its financial content cannot be altered without an explicit correction trail. Payment reconciliation is a safe post-send operation that transitions the invoice to `PAID` without modifying core financial data.

#### 2.4.3 Bank Account Model

The **Bank Account** entity supports multiple accounts per entity: current, savings, and foreign currency accounts. Each stores: account name (display label); sort code and account number (UK domestic); IBAN (international); currency (ISO 4217 code, default `GBP`); opening balance; and current computed balance (aggregated from ledger postings). Bank transactions imported from CSV or OFX files follow a three-status pipeline: **Imported → Categorized → Reconciled**. `IMPORTED` means parsed from the source file but not yet matched to a ledger entry. `CATEGORIZED` means assigned a COA account and contact ("Tesco £45.60" as "Office Supplies"). `RECONCILED` means matched to one or more ledger postings with agreeing balances.

Reconciliation matching supports one-to-one, one-to-many, and partial matches. A single bank deposit of £5,000 might match five separate invoice payments. Partial matching handles cases where the bank amount differs from the invoice amount due to deducted fees: an invoice for £1,000 paid with £15 bank fee deducted appears as £985 on the bank statement; the system matches £985 to the invoice and creates a separate £15 bank charge expense. The bank model connects to the reactive event pipeline described in Chapter 1: when a Formance transaction posts, the `COMMITTED_TRANSACTIONS` event ^32^triggers the bank feed service to check for matches, the reporting service to invalidate cached reports, and the notification service to alert the user -- all in real time within milliseconds. This reactive pattern eliminates the batch processing that makes month-end reconciliation a multi-day exercise in traditional systems [^insight7^], reducing the reconciliation workload that typically consumes 40% or more of accountant time.



---



## 3. Agentic Interface and LLM Chat

The preceding chapters established the system's five-layer architecture and the ledger data model that sits at its core. This chapter turns to the layer that makes the system *LLM-native*: the agentic interface. In a conventional accounting system, an LLM might be bolted on as a chat assistant that queries an existing database. Here, the agent ensemble is the primary interface — every user interaction flows through a supervisor agent that reasons about intent, routes to specialist agents, and coordinates with human approvers before any ledger state changes. This inversion — agents first, API second — is the defining architectural decision of the system.

The chapter proceeds through five sections. Section 3.1 defines the supervisor-plus-specialist topology, Section 3.2 details the WebSocket chat interface and context management architecture, Section 3.3 presents the graduated autonomy framework for human oversight, Section 3.4 specifies the SKILL.md registry, and Section 3.5 closes with safety and reliability mechanisms.

### 3.1 Agent Architecture

#### 3.1.1 Supervisor Agent

All user requests enter through a single supervisor agent implementing the ReAct (Reasoning + Acting) pattern ^40^. The supervisor does not perform accounting work itself; its purpose is to understand what the user wants, decompose the request into discrete tasks, and route each task to the appropriate specialist ^7^. This separation of routing from execution prevents the supervisor from "doing specialist work itself," a failure mode that degrades routing accuracy and produces un-auditable reasoning chains ^7^.

The supervisor runs GPT-4o-2024-08-06 at temperature = 0, ensuring identical inputs produce identical routing decisions with no stochastic variation ^7^. The `max_iterations` parameter is set to 20, preventing runaway loops while allowing sufficient depth for multi-step decomposition. In production, the supervisor operates in `last_message` mode, passing only each specialist's final output back into the supervisor's context rather than the full execution trace ^7^. Full traces are retained in LangSmith for observability but do not consume the supervisor's limited context window.

The supervisor's responsibilities span five domains: intent classification, task decomposition, routing (exactly one specialist per subtask), escalation to humans when confidence falls below threshold, and response synthesis combining specialist outputs into a coherent user-facing response. The target routing accuracy is 95% on the evaluation test set.

#### 3.1.2 Eight Specialist Agents

The supervisor delegates to eight specialist agents, each responsible for a discrete accounting domain ^7^. The specialists are composed of a system prompt, a set of JSON Schema tool definitions, and access to the skill registry (Section 3.4). Each specialist operates within its own scope and defers out-of-domain requests back to the supervisor.

| Agent | Domain | Primary Tools | HITL Gate |
|-------|--------|--------------|-----------|
| Intake | Document and transaction ingestion | `parse_invoice`, `parse_receipt`, `parse_bank_statement`, `extract_metadata` | Review for low-confidence extractions |
| Categorization | COA classification | `lookup_coa`, `suggest_category`, `match_vendor_to_account` | Escalate when confidence < 0.80 |
| Validation | Pre-posting compliance checks | `check_debit_credit_balance`, `validate_coa_membership`, `check_duplicate` | Block posting on any failure |
| Posting | General ledger writes | `create_journal_entry`, `post_to_ledger`, `create_reversing_entry` | 100% human approval required |
| Reconciliation | Transaction matching | `match_transactions`, `identify_discrepancies`, `suggest_matches` | Human review for discrepancies |
| Reporting | Financial report generation | `generate_trial_balance`, `generate_pnl`, `generate_balance_sheet` | Exception-only (5% sampled) |
| Tax | Tax calculation and filing | `calculate_vat`, `calculate_income_tax`, `generate_tax_report` | 100% approval for all filings |
| Audit | Anomaly detection and compliance | `generate_audit_trail`, `detect_anomalies`, `explain_transaction` | Human review for flagged anomalies |

The topology follows a star pattern: the supervisor routes to one specialist at a time, receives the result, and either routes to another specialist for downstream work or returns the response to the user ^7^ ^80^. For a routine invoice payment, the workflow might traverse Intake → Categorization → Validation → Posting in sequence, with the supervisor orchestrating each handoff and maintaining state across the chain. This sequential routing ensures that each step's output becomes the next step's input under deterministic control.

The Intake Agent handles the document processing pipeline, using a hybrid LLM-plus-OCR architecture to extract structured data from invoices, receipts, and bank statements with 97–98.5% document-level accuracy ^9^ ^10^. The Categorization Agent applies confidence scoring: at or above 0.95 it auto-categorizes, between 0.80 and 0.94 it proposes for confirmation, and below 0.80 it escalates to a human accountant. The Validation Agent enforces the fundamental accounting equation on every proposed entry, confirming total debits equal total credits within a $0.01 tolerance, all account codes exist in the active COA, the posting period is open, and no duplicate reference numbers are present ^81^.

Most specialists use the ReAct pattern — interleaving reasoning steps with tool invocations — which yields a 34% improvement on decision benchmarks compared to single-shot calling ^40^. The Posting Agent, however, uses Plan-and-Execute because accounting transactions require auditable, predetermined execution plans rather than dynamic reasoning chains ^82^. When the Posting Agent receives a validated journal entry, it constructs a complete execution plan (a directed acyclic graph of posting operations) before performing any writes, making the sequence reviewable and deterministic ^82^. This distinction between ReAct and Plan-and-Execute is not merely stylistic — it ensures that a regulator examining a posted transaction can reconstruct the exact planned sequence of operations rather than inferring it from a chain of opaque reasoning steps.

#### 3.1.3 Agent Selection Rationale

The supervisor-plus-specialist topology is driven by empirical performance data and the economics of accounting errors.

| Approach | Avg Tokens | Avg Cost | E2E Success | Optimal For |
|----------|-----------|----------|-------------|-------------|
| Single mega-agent | 4,200 | $0.022 | 71% | Simple tasks; single persona |
| ReAct agent + many tools | 6,800 | $0.038 | 79% | Medium complexity |
| **Supervisor + 4–8 specialists** | **11,400** | **$0.061** | **89%** | **Heterogeneous tasks; specialist tools** |
| Hierarchical (supervisor of supervisors) | 18,200 | $0.097 | 91% | Only past 8+ specialists ^7^|

The supervisor pattern achieves an 89% end-to-end success rate compared to 71% for a single agent — an 18-percentage-point improvement from LangGraph production data ^7^. This comes at approximately 3x the per-task cost ($0.061 versus $0.022). For accounting, where a mis-posted entry can require hours of reconciliation and carry regulatory risk, the cost differential is justified by error avoidance. The hierarchical alternative achieves 91% at nearly 5x cost; the diminishing return makes it worthwhile only past eight specialists, which is not the case here ^7^. The 18-point accuracy lift directly reduces the incidence of ledger errors requiring human correction — a single prevented error can save more in accountant time than the marginal cost difference across thousands of transactions.

The single-agent failure mode is particularly acute for accounting. Weber et al. (2025) demonstrated that LLMs generate fully correct double-entry transactions only 8.33% of the time without guided templates. The multi-agent architecture addresses this by separating categorization from validation from posting, with deterministic checks between each stage. Each specialist can be independently evaluated, improved, and replaced without disrupting the overall workflow — a property that monolithic architectures cannot replicate.

### 3.2 Chat Interface

#### 3.2.1 WebSocket Protocol

The conversational interface uses a WebSocket connection at `/ws/chat/{session_id}` for full-duplex, bidirectional streaming ^83^. WebSocket is chosen over Server-Sent Events or long polling because the interaction is genuinely bidirectional: the server streams tokens as the LLM generates its response, while the client sends approval decisions, corrections, or uploaded documents mid-conversation.

All messages use a typed JSON protocol with distinct schemas for each direction:

| Direction | Message Type | Purpose |
|-----------|-------------|---------|
| Client → Server | `message` | Natural language text input |
| Client → Server | `approval` / `rejection` | Human-in-the-loop decision |
| Client → Server | `clear_history` | Reset conversation context |
| Client → Server | `upload` | Document attachment |
| Server → Client | `stream_start` | Agent processing has begun |
| Server → Client | `stream_token` | Individual LLM output token |
| Server → Client | `stream_end` | Structured final result |
| Server → Client | `approval_request` | HITL gate triggered |
| Server → Client | `error` | Structured error with severity |

The protocol supports multi-connection sessions — a single `session_id` can have multiple concurrent WebSocket connections — and automatic history replay on reconnection so users do not lose conversational state. The streaming token design means users see responses build in real time, with latency from first token targeted at under 200 milliseconds for routing decisions and under 5 seconds for end-to-end task completion ^83^. The typed protocol ensures that both client and server can validate message structure before processing, preventing malformed messages from propagating through the agent pipeline. Session IDs are UUIDv4 values generated by the client and validated by the server on connection.

#### 3.2.2 Context Management

Each session maintains a five-layer context model:

| Context Layer | Storage | Lifetime | Purpose |
|--------------|---------|----------|---------|
| Conversation history | Redis | Session | Active message thread; sliding window of last 20 pairs with 8K token budget |
| User preferences | PostgreSQL | Permanent | Business rules, display preferences, default entity and book |
| Episodic memory | Mem0 | Permanent | Past categorization decisions, correction history, vendor mappings ^84^|
| Working state | In-memory | Session | Pending approvals, draft operations, tool call history |
| Entity context | Redis | Session | Active company, ledger, accounting period, COA version |

The short-term conversational layer uses Redis for sub-millisecond latency. A sliding window keeps the last 20 message pairs within an 8,000-token budget; when exceeded, older messages are summarized rather than dropped. Sessions have a 24-hour TTL with heartbeat refresh, so idle sessions expire while active sessions persist ^8^. This tiered storage architecture balances performance against persistence cost: ephemeral conversational data lives in high-speed cache, while durable organizational knowledge lives in persistent stores with appropriate backup and recovery procedures.

Episodic memory is managed via Mem0, which provides adaptive updates across vector and graph stores ^84^. When the Categorization Agent classifies an invoice from "Acme Supplies Inc." to account 6100, that decision is recorded as an episodic memory entry scoped to the entity. Future invoices from the same vendor trigger semantic retrieval, enabling higher-confidence categorization with fewer lookups. Correction events are also stored — when a user changes a categorization from 6100 to 6200, the correction creates a learning signal for future decisions ^85^. Entity scoping is enforced at retrieval: memories from one legal entity are never visible to agents operating on another, preventing cross-entity data leakage that would violate both data governance policies and auditor expectations. Over time, this episodic layer accumulates organization-specific knowledge that improves accuracy and progressively reduces the need for human intervention on routine transactions.

#### 3.2.3 Natural Language Capabilities

The chat interface supports five categories of natural language capability. **Date parsing** resolves relative and absolute expressions ("last month," "Q2 2025," "the 15th") respecting the entity's fiscal year configuration. **Ambiguity resolution** engages clarifying dialogue when input is ambiguous — "Record a payment from Acme" could mean a customer payment or vendor refund — presenting alternatives rather than guessing. **Multi-turn workflows** maintain working state across turns, allowing incremental refinement: "Add another line," "Change line 3 to $450," "Attach the invoice PDF." This pattern is essential for complex entries that span multiple lines and cost centers, where constructing the complete entry in a single turn would be cognitively demanding and error-prone. The agent maintains a draft journal entry in working state, updating it with each turn until the user explicitly confirms the posting. **Error recovery** explains validation failures in natural language with suggested corrections, turning validation errors into educational moments rather than opaque rejection messages. **Persona selection** offers three modes: *Assistant* (conversational, explanatory, for business owners), *Professional* (concise, technical, for accountants), and *Auditor* (formal, trace-heavy, for compliance work). The persona affects response verbosity, technical depth, and the default level of explanation provided with each action. A business owner using the Assistant persona receives plain-language explanations of why an entry was categorized a certain way, while an accountant using the Professional persona sees COA codes and accounting standards references directly. The Auditor persona includes full reasoning traces and tool call logs with every response, providing the documentary evidence that external auditors and regulators require when reviewing AI-assisted accounting decisions. Persona selection is persisted per user in PostgreSQL and can be changed at any time during a conversation.

### 3.3 Human-in-the-Loop Framework

#### 3.3.1 Graduated Autonomy Model

The system implements a graduated autonomy model in which agent freedom increases as reliability is demonstrated ^6^. Phase 1 (Weeks 1–4, "Supervised") requires 100% human approval for all ledger-modifying actions. Phase 2 (Weeks 5–12, "Sampled") maintains 100% approval for high-risk actions while reducing low-risk actions to 20% sampled approval. Phase 3 (Months 3–6, "Exception-only") auto-approves low-risk actions and approves medium-risk actions only when exception triggers fire. Phase 4 (Months 6+, "Full autonomy") operates on exception-only approval for all actions, with policy triggers defining exceptions: amounts above entity thresholds, transactions to sensitive accounts, activity outside business hours, or pattern-based anomaly flags ^6^.

Progression is gated by measurable criteria. Phase 1 to Phase 2 requires a 95% validation pass rate and human rejection rate below 5% over two weeks. Phase 3 requires 98% pass rate and zero material errors over one month. Phase 4 requires six months of operational data, one complete audit cycle with no findings, and controller sign-off.

#### 3.3.2 Approval Decision Matrix

The approval matrix maps every action type to required approver, SLA, and cost of error.

| Action Type | Cost of Error | Reversibility | Required Approver | SLA |
|-------------|--------------|---------------|-------------------|-----|
| Post journal entry | High | Low | Finance manager + accountant | 15–60 min |
| Modify posted entry | Very high | Low | Dual approval | Same-day |
| Delete entry | Very high | Very low | Controller + CFO notification | 1–4 hours |
| Bulk posting | Very high | Low | Controller review | 1–24 hours |
| Generate standard report | Low | High | None (exception-only) | Real-time |
| Tax filing submission | Very high | Very low | Controller + external review | 1–7 days |
| COA modification | High | Medium | Controller | 1–24 hours |
| Reconciliation auto-match | Low | High | None (exception-only) | Real-time |

The matrix reflects a fundamental principle: the more costly and irreversible an action, the more stringent its approval. Posting a journal entry is high-cost and low-reversibility because a reversing entry creates audit trail complexity and may affect period-end balances. Generating a report is low-cost because reports are read-only — a bad report can be regenerated in seconds. Tax filing submission carries the highest rating because an incorrect filing can trigger penalties, interest charges, and regulatory scrutiny extending far beyond the accounting department. This matrix is not static — organizations can adjust thresholds, approver roles, and SLA targets to match their internal control requirements and regulatory environment. The matrix is enforced by the Validation Agent programmatically: every proposed action is checked against the matrix, and the agent cannot proceed until the required approvals are recorded in the system.

#### 3.3.3 Four Approval Workflow Patterns

The framework implements four approval patterns selected by action type and risk level ^6^.

**Pattern 1: Action-level gate.** The agent proposes a specific tool call with full parameters and waits for explicit approval. Used for all posting operations and tax filings. The proposal includes action type, parameters, risk assessment, rollback plan, and confidence score. If the approval timeout expires (15–60 minutes for posting), the action escalates to a senior approver.

**Pattern 2: Draft approval.** The agent produces a draft — a journal entry, report, or reconciliation proposal — for human review and editing. The human can edit any field or reject the draft; the agent incorporates feedback and resubmits.

**Pattern 3: Dual approval.** High-risk operations require two separate approvers with different roles, implementing separation-of-duties required by SOX and internal controls. Deleting a posted entry, modifying a closed period, or submitting a tax return all require dual approval — for example, a finance manager and a controller.

**Pattern 4: Exception-only review.** The agent auto-approves low-risk actions unless a policy trigger fires: amount above threshold, transaction to a sensitive account, unknown vendor, activity outside business hours, or anomaly score above threshold. This pattern is used for standard report generation, reconciliation auto-matches, and low-value categorizations where the cost of human review exceeds the cost of an occasional error.

### 3.4 SKILL Registry

#### 3.4.1 OpenClaw SKILL.md Format

Agent capabilities are defined through a skill registry following the OpenClaw SKILL.md format — a folder-based system where each skill is a directory containing a `SKILL.md` file with YAML frontmatter and markdown instructions ^13^ ^14^. The format is local-first (skills load from filesystem without compilation), SDK-free (no special runtime), discoverable via vector search, and versioned ^13^.

The YAML frontmatter defines: skill name (kebab-case identifier), description (under 160 characters), semantic version, author, tags, and an accounting-specific metadata block. The markdown body contains purpose, when-to-use conditions, step-by-step instructions, hard rules (e.g., "NEVER categorize to a suspense account without explicit user approval"), and error handling. This structure is optimized for both machine discovery (vector embeddings of descriptions and tags) and machine execution (structured instructions the agent follows step by step).

| Field | Type | Purpose |
|-------|------|---------|
| `metadata.accounting.domain` | string | Domain: `general_ledger`, `ap`, `ar`, `tax`, `reporting` |
| `metadata.accounting.risk_level` | enum | `low` / `medium` / `high` — determines approval workflow |
| `metadata.accounting.requires_approval` | boolean | Whether this skill always requires human approval |
| `metadata.accounting.audit_trail` | boolean | Whether every invocation is logged |
| `metadata.requires.env` | array | Required environment variables |
| `metadata.dependencies` | array | Cross-skill dependencies with version constraints |

Skills load in strict precedence: workspace skills (`<workspace>/skills/`) override user skills (`~/.openclaw/skills/`), which override bundled system defaults. Discovery uses vector search: the supervisor embeds the intent description and searches for semantically similar skills, loading the top-$k$ results into the specialist's context. This decouples capability from code — adding a skill makes new functionality available immediately without redeployment.

#### 3.4.2 Security Model (Post-ClawHavoc)

The ClawHavoc incident in February 2026 — 341+ malicious skills discovered on ClawHub, 20% of packages compromised — demonstrated that skill-based systems face supply chain risks comparable to traditional software dependencies ^86^ ^87^. Attack vectors included command-and-control callbacks, credential harvesting, data exfiltration, and prompt injection. The root cause was the absence of cryptographic signing, sandboxing, or verification ^13^.

| Layer | Control | Implementation |
|-------|---------|----------------|
| Upload scanning | SHA-256 + VirusTotal | All skills scanned for known malware before activation |
| Daily rescanning | Continuous monitoring | Existing skills rescanned against updated threat signatures |
| Code signing | Cryptographic verification | All skills signed by a trusted authority; unsigned skills rejected |
| Sandboxing | Docker isolation | Skill execution in restricted containers |
| Permission model | Least-privilege | Skills access only resources declared in `metadata.requires` |
| Network restrictions | Deny-by-default | No outbound network calls unless whitelisted |

These controls ensure a compromised skill cannot exfiltrate data (deny-by-default network egress), access unauthorized resources (least-privilege), or persist on the system (daily rescanning). Docker sandboxing prevents host system escape even if the skill execution runtime is exploited. Every skill invocation is logged with skill name, version, parameters, output, and execution duration, satisfying EU AI Act Article 12 requirements for automatic event logging ^12^. The security model transforms skill management from an uncontrolled distribution channel into a governed, auditable capability lifecycle.

#### 3.4.3 Skill Growth Trajectory

The registry grows across four phases. Phase 1 (MVP) ships with 25+ skills covering core workflow: transaction entry, invoice processing, payment recording, bank reconciliation, trial balance, and basic tax calculation. Phase 2 (Months 3–5) expands to 65+ skills with advanced reporting, multi-currency handling, intercompany transactions, and accrual management. Phase 3 (Months 6–9) reaches 120+ skills with industry-specific packs (retail, professional services, construction, e-commerce) and audit automation. Phase 4 (Year 2+) targets 190+ skills with custom report builder skills, regulatory compliance packs for additional jurisdictions, and third-party integrations. Each skill is a `SKILL.md` file that domain experts (accountants, tax specialists) can author without writing code, making skill growth a parallel activity to core engineering.

### 3.5 Safety and Reliability

#### 3.5.1 Five-Layer Input and Output Validation

Every user input passes through a five-layer validation pipeline before reaching any agent, and every agent output passes through a complementary five-layer pipeline before any system modification.

The **input pipeline** proceeds: Syntax (JSON/schema validation), Semantic (type checking and range validation), Authorization (user permissions and entity access, logging security events on violation), Content Safety (PII detection and prompt injection scanning), and Business Rules (entity match, period open, COA valid, amounts within bounds).

The **output pipeline** proceeds: Schema (JSON Schema strict validation, retrying up to 3 times on failure) ^88^, Accounting Rules (debits equal credits, valid COA membership, double-entry conventions) ^81^, Balance Check (trial balance integrity after proposed posting), Duplicate Check (reference number uniqueness) ^89^, and Anomaly Detection (statistical outlier detection flagging unusual entries for review).

The Validation Agent executes the full output pipeline before any journal entry reaches the Posting Agent. It confirms: debits equal credits within $0.01, all codes exist in the active COA, the period is open, entity ID matches context, reference is unique, required fields are populated, amounts are positive and within bounds, and the approval workflow for the entry's risk level is complete.

#### 3.5.2 Error Taxonomy and Graceful Degradation

Agent failures fall into three categories ^90^. **Hard failures** (API timeout, rate limit, database failure, malformed LLM response) trigger retry with exponential backoff (max 3 retries, 2–30 second range), then escalation. **Structural failures** (invalid JSON, missing fields, schema violation, invalid tool parameters) trigger retry with clearer formatting instructions, then fallback to a simpler output format. **Semantic failures** (hallucinated account codes, incorrect categorizations, confident falsehoods) are the most dangerous because they can pass validation and reach the ledger; the strategy is to flag as uncertain and escalate to human review. The anomaly detection layer (Layer 5 of output validation) specifically catches semantic failures by identifying statistically unusual outputs — for instance, a journal entry with an amount three standard deviations above the entity's historical average, or an account combination that has never appeared in prior transactions.

When full-capability response is not possible, the system degrades through four levels ^91^: Level 0 (Full — all systems operational), Level 1 (Cached — API rate limit; uses stale but valid cached data), Level 2 (Restricted — LLM unavailable; deterministic rule-based responses only), and Level 3 (Human-only — critical failure; immediate human escalation). The progression from Level 0 to Level 3 is automatic and reversible — when the LLM API recovers from an outage, the system transitions from Level 2 back to Level 0 without manual intervention. Circuit breakers on each external service prevent cascading failures: a failure threshold of 5 consecutive errors opens the circuit, which enters half-open after 60 seconds and permits 3 test calls before returning to full operation ^90^ ^92^.

For multi-step workflows, the Saga pattern with compensating transactions ensures eventual consistency ^93^ ^94^. Each step has a forward action and compensating undo. If step 3 of a 5-step workflow fails, compensating transactions for steps 2 and 1 execute in reverse order, returning the ledger to its pre-workflow state. Every compensating step is idempotent — executing it twice produces the same result as once — so the system can safely retry compensation after a partial failure. The Saga pattern is essential for accounting workflows where partial completion would leave the ledger in an inconsistent state, such as an invoice processing workflow that creates a payable, updates vendor balance, and schedules a payment — if the payment scheduling fails, the prior steps must be undone to maintain balance integrity. Without compensating transactions, a failed workflow could leave a payable recorded without the corresponding vendor balance update, creating a discrepancy that would surface only at month-end reconciliation. The Saga coordinator logs every step and compensation attempt, producing an auditable trail of the recovery process that satisfies both operational debugging needs and regulatory examination requirements.

#### 3.5.3 EU AI Act Compliance

The system is classified as a high-risk AI system under Annex III, Section 5(b) of the EU AI Act, covering AI systems that assess financial health and affect access to financial resources ^17^ ^18^. The full enforcement deadline is August 2, 2026, with penalties up to EUR 35 million or 7% of global turnover ^12^.

| Requirement | Article | Implementation |
|-------------|---------|----------------|
| Risk management | Art. 9 | Continuous risk assessment with documented register; quarterly review |
| Data governance | Art. 10 | Training data quality management; bias detection in models |
| Technical documentation | Art. 11 | Complete architecture docs; algorithm descriptions; data inventories |
| Record-keeping | Art. 12 | Automatic logging of all decisions, tool calls, approvals; 6+ year retention |
| Transparency | Art. 13 | AI disclosure in chat; capability statements; decision explanations |
| Human oversight | Art. 14 | Graduated autonomy with meaningful review; circuit breakers; competent approvers ^9^ ^6^|
| Accuracy | Art. 15 | Certified accuracy metrics per release; regular validation |
| Cybersecurity | Art. 15 | Defense-in-depth; penetration testing; skill supply chain scanning |
| Conformity assessment | Art. 43 | Third-party assessment before EU deployment |
| Post-market monitoring | Art. 72 | Continuous monitoring; incident reporting within 15 days ^95^|

The Article 12 record-keeping requirement is satisfied architecturally. Every agent decision is logged: the natural language request, the supervisor's routing decision with reasoning trace, specialist tool calls with parameters and responses, validation results, human approval decisions, and the final ledger posting with transaction ID. Because Formance Ledger is append-only and hash-chained, the ledger entry serves as tamper-evident proof of final state while the agent decision log provides the explanatory provenance the EU AI Act requires ^12^.

Article 14 human oversight is implemented through the graduated autonomy model (Section 3.3.1): humans review every AI decision before it affects the ledger, can reject or modify any proposed action, circuit breakers enable immediate system halt, and approver roles match required expertise levels ^9^ ^6^. The approval framework governing AI posting of a journal entry is the same framework enforcing CFO approval for payments over $5,000 — one trust interface serves both AI safety and financial control. This convergence eliminates the need for separate "AI oversight" and "financial approval" systems, reducing engineering effort while providing approvers with both financial context and AI decision context (confidence score, alternative options, reasoning trace) in a single screen.

Serious incidents (balance corruption, unauthorized access, regulatory filing errors) must be reported to the national competent authority within 15 days ^95^. The August 2026 deadline creates a compliance window: competitors without AI audit trails face a 12–18 month rebuild, while this system enters the EU market with compliance embedded from the ground up ^12^.



---



## 4. Financial Reporting SKILLs

The preceding chapter described the agentic interface that interprets user intent and routes execution to specialized capabilities. This chapter details the largest and most heavily regulated capability domain: financial reporting. The system delivers 33 distinct report SKILLs organized across seven categories, all executing through a deterministic five-stage pipeline that guarantees identical inputs produce identical outputs. Every SKILL is registered with a JSON schema that defines its parameter envelope, data dependencies, and output structure, enabling programmatic discovery and validation ^51^. The architecture treats accounting standards --- GAAP, IFRS, and jurisdiction-specific tax regimes --- as interchangeable rule bundles applied during pipeline execution, so a single SKILL produces framework-compliant output without code changes.

### 4.1 Report Engine Architecture

#### 4.1.1 Five-Stage Pipeline

All report SKILLs execute through a uniform five-stage pipeline. This design ensures that every report --- from a simple trial balance to a multi-entity consolidated cash flow statement --- follows the same deterministic path from parameter ingestion to formatted output. The pipeline guarantees that the same parameter envelope submitted twice, assuming no underlying data changes, produces byte-identical output ^96^. This property is essential for audit reliability and regulatory acceptance.

| Stage | Name | Function | Key Operations |
|-------|------|----------|----------------|
| 1 | Parameter Ingestion | Validate and normalize input | Schema validation, default application, period resolution, currency normalization |
| 2 | Query Layer Execution | Acquire raw data | SQL queries against GL, COA, journal entries, contacts, tax transactions; REST calls for exchange rates |
| 3 | Data Model Transformation | Apply business logic | Aggregation, period logic, currency conversion, intercompany elimination, reclassification, dimensional slicing |
| 4 | Rule Application | Apply framework-specific rules | Account classification, line ordering, subtotals, disclosure requirements, sign conventions |
| 5 | Output Formatting | Serialize to target format | JSON structuring, HTML templating, PDF rendering, CSV flattening, XBRL taxonomy mapping |

The deterministic guarantee rests on two architectural decisions. First, Stage 1 resolves all relative date references ("last month," "prior quarter") to absolute ISO dates against a known system time, so the same natural-language request always resolves to the same period boundaries. Second, Stage 2 queries use READ COMMITTED isolation with a snapshot timestamp derived from the request time, ensuring that concurrent transactions do not introduce non-determinism. Each SKILL declares its maximum execution time (default 30,000 ms) and cache time-to-live (default 300 seconds) within its schema, allowing the execution engine to apply resource limits predictably ^97^.

The query layer in Stage 2 interfaces with multiple data sources through a unified abstraction. General ledger transactions, chart of accounts metadata, journal entries, contact master data, tax transactions, budget and forecast data, tracking categories, and audit logs are accessed via SQL against the primary PostgreSQL store. Exchange rates require REST calls to external rate providers, while XBRL taxonomy data is queried through GraphQL to support flexible element resolution. The query planner analyzes parameter dependencies and executes independent queries in parallel where possible, reducing latency for reports that draw from multiple sources.

Stage 3 applies the core business logic that transforms raw query results into a structured report data model. This stage handles aggregation (rolling transactions up to account, category, or dimension level), period logic (fiscal year variations, 4-4-5 calendars, multi-period rollups), currency conversion (applying period-end, average, or historical exchange rates depending on the report type), intercompany elimination (removing intra-group transactions for consolidated reports), account reclassification (mapping internal account codes to standard reporting categories), and dimensional slicing (filtering by tracking category, department, project, or region). Each transformation operation is logged with its input hash and output hash, creating a verifiable audit trail ^98^.

Stage 4, Rule Application, is where framework-specific accounting rules are applied. Classification rules map each account to its appropriate reporting category --- under IFRS 18, accounts must be classified into Operating, Investing, Financing, Income Taxes, or Discontinued Operations categories ^99^. Aggregation rules define how line items group into subtotals and totals. Disclosure rules determine which supplementary notes and Management Performance Measure (MPM) reconciliations must appear ^100^. Validation rules enforce cross-checks such as the accounting equation (Assets = Liabilities + Equity) on balance sheets and the debit-credit balance requirement on trial balances ^101^. Sign conventions differ between GAAP and IFRS for certain presentation elements, and the rule engine applies the appropriate convention based on the framework parameter.

Stage 5 serializes the processed data model into the requested output format. The output layer supports six formats --- JSON, HTML, PDF, CSV, XBRL, and iXBRL --- each discussed in Section 4.4. The format selector receives the fully processed data model and applies the appropriate serializer without re-executing any upstream pipeline stage, ensuring consistent output across formats for the same underlying data.

#### 4.1.2 Framework Parameterization

A central design objective is that the same report SKILL produces compliant output for different accounting standards through configuration rather than code duplication. The `framework` parameter, accepted by every core statement SKILL, selects a rule bundle that defines how the report is constructed. Supported values are `gaap_us`, `gaap_uk`, `ifrs`, `tax_uk`, `tax_au`, and `tax_us`, with `ifrs` as the default ^102^.

Each rule bundle is a JSON document that defines five rule domains: account classification mapping, line item ordering and grouping, required subtotals and totals, disclosure requirements, and sign conventions with terminology. When a SKILL executes, the Stage 4 rule engine loads the bundle corresponding to the `framework` parameter and applies each rule in sequence.

| Reporting Element | US GAAP | IFRS |
|-------------------|---------|------|
| P&L format | No prescribed format; SEC Reg S-X guidance | IFRS 18: 5 mandatory categories with required subtotals ^51^|
| Inventory cost method | LIFO permitted | LIFO prohibited; FIFO or weighted average only |
| Development expenditure | Expensed as incurred | Capitalized if technical and commercial feasibility criteria met |
| Impairment reversal | Prohibited | Allowed if criteria met |
| Extraordinary items | Permitted (though rare) | Prohibited |
| Balance sheet terminology | "Balance Sheet" | "Statement of Financial Position" |
| Income statement terminology | "Income Statement" | "Statement of Profit or Loss" |
| Cash flow indirect start | Net income | Operating Profit (IFRS 18) ^103^|
| Goodwill presentation | May combine with intangibles | Must be separate line item ^103^|

The differences in the table above are handled granularly: a SKILL applies only the rules relevant to its report type and the data present in the current period. This avoids the combinatorial explosion that would result from maintaining separate report templates per framework. Under this architecture, the underlying chart of accounts and general ledger entries remain unchanged; only the presentation-layer mapping differs ^102^.

### 4.2 Core Financial Statement SKILLs

#### 4.2.1 P&L Statement (core.pl)

The Profit & Loss Statement SKILL produces the primary report of financial performance over a period. Under IFRS 18, effective January 2027, this statement adopts a fundamentally new structure representing the most significant change to income statement presentation in over two decades ^51^. The P&L SKILL natively supports this structure through the `ifrs18_options` parameter, enabling full or transitional compliance, expense presentation by nature or by function, and mandatory MPM disclosure ^100^.

IFRS 18 introduces five mandatory categories for classifying income and expenses. Every item must fall into exactly one category, replacing the current practice of presenting a single block of revenue and expenses ^99^.

| IFRS 18 Category | Scope | Typical Line Items |
|------------------|-------|--------------------|
| Operating | Core business activities; default/catch-all | Revenue, cost of sales, SGA expenses, R&D, depreciation of operating assets |
| Investing | Returns from investments and investment-related items | Interest income, dividend income, gains/losses on disposal of investments, share of JV profits |
| Financing | Cost of raising and servicing finance | Interest expense, foreign exchange differences on financing liabilities |
| Income Taxes | Tax per IAS 12 | Current tax expense, deferred tax expense |
| Discontinued Operations | Components disposed of or held for sale per IFRS 5 | Post-tax results of disposed segments |

Between these categories, IFRS 18 mandates specific subtotals. The first is **Operating Profit or Loss**, appearing after all operating income and expenses. Investing category items (share of associates, interest income) are added to arrive at **Profit or Loss before Financing and Income Taxes**. After deducting financing costs and income taxes, the final mandatory total is **Profit or Loss (Net Income)** ^99^. The P&L SKILL enforces this hierarchy and validates that the arithmetic progression from revenue to net income is mathematically consistent.

IFRS 18 also introduces mandatory disclosure requirements for Management Performance Measures (MPMs) --- subtotals of income and expenses that management uses in public communications outside the financial statements ^51^. Common examples include Adjusted EBITDA, underlying profit, and free cash flow. Under IFRS 18, MPM disclosures are mandatory, must appear within the financial statements, and fall within audit scope ^100^. The P&L SKILL supports MPM reconciliation through a dedicated parameter block recording the measure name, description, and line-by-line reconciliation from the nearest IFRS-defined total to the MPM figure.

#### 4.2.2 Balance Sheet (core.bs)

The Balance Sheet SKILL produces a statement of financial position per the accounting equation: Assets = Liabilities + Equity ^104^. The SKILL supports three format options via the `detail_level` parameter: **standard** (standard line items with subtotals), **detailed** (additional breakdowns such as AR by aging bucket and fixed assets by type), and **comparative** (current period alongside prior period with variance columns).

The balance sheet organizes assets into current and non-current categories. Current assets include cash, accounts receivable (net of allowance), inventory, prepaid expenses, and short-term investments. Non-current assets include property, plant and equipment (net), intangible assets (net), goodwill (which IFRS 18 requires as a separate line item) ^103^, long-term investments, deferred tax assets, and other non-current items. Liabilities follow the same split, with current liabilities covering accounts payable, short-term debt, accrued expenses, deferred revenue, and tax payable; non-current liabilities include long-term debt, bonds payable, deferred tax liabilities, pension obligations, and lease liabilities. Equity presents share capital, share premium, treasury shares, retained earnings, other reserves, and non-controlling interests ^104^.

The SKILL validates the accounting equation on every execution: Total Assets must equal Total Liabilities plus Total Equity. Any deviation triggers a validation error preventing output generation and routing the failure to the reconciliation agent for investigation.

#### 4.2.3 Cash Flow Statement (core.cf)

The Cash Flow Statement SKILL supports both the direct and indirect methods per IAS 7, selected via the `method` parameter ^105^ ^106^. Under the direct method, operating cash flows are presented as major classes of gross cash receipts and payments. Under the indirect method --- the more common approach --- the statement begins with net income (or, under IFRS 18, operating profit) and adjusts for non-cash items and changes in working capital ^105^.

IFRS 18 makes specific changes that the SKILL implements when `ifrs18_compliant` is true ^103^. The indirect method starting point shifts from Net Income to Operating Profit. Interest paid moves from operating activities to financing activities; interest received and dividends received move from operating to investing activities; dividends paid must be classified as financing. These changes align the cash flow statement categories with the P&L categories under IFRS 18. The SKILL's `classifications` parameter block allows explicit override of each classification, with IFRS 18-compliant defaults when the framework is IFRS.

#### 4.2.4 Trial Balance (core.tb)

The Trial Balance SKILL lists all general ledger account balances at a specific point in time and provides the fundamental verification that total debits equal total credits ^97^ ^107^. An unbalanced trial balance indicates a data integrity issue that must be resolved before any financial statement can be considered reliable ^101^.

The SKILL produces three variants, selected via the `type` parameter, each serving a different point in the accounting cycle ^108^.

| Variant | Timing | Purpose | Key Characteristics |
|---------|--------|---------|---------------------|
| Unadjusted | Before adjusting entries | Initial data capture; reveals obvious errors | Raw ledger balances; may contain accrual mismatches and period-cutoff errors |
| Adjusted | After adjusting entries, before financial statements | Includes corrections, accruals, and deferrals | Reflects all period-end adjustments; basis for financial statement preparation |
| Post-Closing | After closing entries | Verifies ledger is ready for next period | Temporary accounts show zero balances; only permanent accounts remain |

The unadjusted trial balance captures raw ledger balances and serves as the starting point for the adjustment process. The adjusted trial balance includes all correcting entries, accruals, and deferrals, and is the direct input to financial statement generation. The post-closing trial balance confirms that all temporary accounts have been closed to retained earnings, leaving only permanent accounts with non-zero balances ^108^. The SKILL enforces the debit-credit balance requirement for all three variants: if total debits do not equal total credits, execution fails with a detailed error identifying the variance and suggesting accounts where the discrepancy may originate ^101^.

### 4.3 Management and Tax Report SKILLs

#### 4.3.1 Management Reports

Management reports provide operational visibility beyond regulatory financial statements. The Aged Accounts Receivable SKILL (`mgmt.ar_aging`) groups outstanding invoices into buckets: Current, 1--30 days, 31--60 days, 61--90 days, and 90+ days ^109^ ^110^. It computes Days Sales Outstanding (DSO) as (Accounts Receivable / Total Credit Sales) multiplied by days in the period. Industry benchmarks suggest DSO should remain below 45 days ^109^. The 90+ day percentage serves as an early warning indicator: values exceeding 20% of total AR trigger escalation to collections ^111^.

The Aged Accounts Payable SKILL (`mgmt.ap_aging`) applies the same bucket structure to amounts owed suppliers, computing Days Payable Outstanding (DPO) and identifying early payment discount opportunities. The General Ledger Detail SKILL (`mgmt.gl_detail`) produces transaction-level listings showing date, reference, description, debit, credit, and running balance ^112^. The GL Summary SKILL rolls this data up to account balance level. The Executive Summary SKILL (`mgmt.executive`) combines P&L highlights, balance sheet snapshot, cash position, KPI summary, and variance alerts into a single decision-ready overview ^113^.

| Management Report | SKILL ID | Key Metrics | Primary Users |
|-------------------|----------|-------------|---------------|
| Aged AR | `mgmt.ar_aging` | DSO, 90+ day %, collection rate by bucket | Collections, CFO |
| Aged AP | `mgmt.ap_aging` | DPO, early payment discount opportunity | Treasury, AP manager |
| GL Detail | `mgmt.gl_detail` | Transaction-level drill-down, running balance | Accountant, auditor |
| GL Summary | `mgmt.gl_summary` | Opening/closing balances, net change, YTD | Management accountant |
| Executive Summary | `mgmt.executive` | P&L highlights, BS snapshot, burn rate, KPIs | Board, investors, CEO |

#### 4.3.2 Tax Reports

Tax report SKILLs produce jurisdiction-specific returns from the same underlying transaction data. The VAT Return (UK) SKILL (`tax.vat_uk`) implements the nine-box structure required by HMRC's Making Tax Digital (MTD) framework ^31^ ^41^. All nine boxes auto-calculate from transaction-level tax data. Box 1 contains VAT due on sales; Box 2 VAT on EU acquisitions (Northern Ireland only post-Brexit); Box 3 the sum of Boxes 1 and 2; Box 4 VAT reclaimed on purchases; Box 5 the net position (Box 3 minus Box 4); Box 6 total sales ex-VAT; Box 7 total purchases ex-VAT; Boxes 8 and 9 EU supplies and acquisitions ^114^. The SKILL produces both human-readable and HMRC API payload formats. MTD compliance requires digital links from source data to submitted return with no manual re-keying ^22^.

The Australian BAS SKILL (`tax.bas_au`) follows the ATO's G-label format for sales, purchases, PAYG withholding, and instalments ^115^ ^116^. The generic GST SKILL (`tax.gst`) provides jurisdiction-agnostic output parameterized for any GST-implementing country. The Sales Tax SKILL (`tax.sales_tax`) addresses US state and Canadian provincial tax, tracking nexus status and multi-level jurisdiction breakdowns ^117^ ^118^.

| Tax Report | SKILL ID | Jurisdiction | Key Output |
|------------|----------|-------------|------------|
| VAT Return (UK 9-box) | `tax.vat_uk` | UK HMRC | 9-box VAT return; MTD API payload ^31^|
| BAS | `tax.bas_au` | Australian Tax Office | G1--G20 labels; GST and PAYG summary ^115^|
| GST (generic) | `tax.gst` | Multi-jurisdiction | Jurisdiction-specific return; configurable rates |
| Sales Tax | `tax.sales_tax` | US/Canada | Tax by state/county/city; nexus tracking ^117^|
| Corporation Tax | `tax.corporation_tax` | UK | Taxable profit; capital allowances |

#### 4.3.3 Complete SKILL Catalog

The full report catalog comprises 33 SKILLs across seven categories. This taxonomy emerged from cross-dimensional research where independent sources converged on the same seven-category organization ^119^ ^120^. The catalog is extensible: new SKILLs register by conforming to the base schema, and the agentic interface discovers them automatically.

| # | Category | SKILL ID | Report Name | Framework |
|---|----------|----------|-------------|-----------|
| 1 | Core Statements | `core.pl` | Profit & Loss Statement | GAAP/IFRS |
| 2 | Core Statements | `core.bs` | Balance Sheet | GAAP/IFRS |
| 3 | Core Statements | `core.cf` | Cash Flow Statement | GAAP/IFRS |
| 4 | Core Statements | `core.tb` | Trial Balance | Universal |
| 5 | Internal Verification | `verify.tb_balanced` | Trial Balance Verification | Universal |
| 6 | Internal Verification | `verify.bs_cf` | Balance Sheet / Cash Flow Reconciliation | GAAP/IFRS |
| 7 | Internal Verification | `verify.intercompany` | Intercompany Elimination Check | GAAP/IFRS |
| 8 | Management | `mgmt.ar_aging` | Aged Accounts Receivable | Universal |
| 9 | Management | `mgmt.ap_aging` | Aged Accounts Payable | Universal |
| 10 | Management | `mgmt.gl_detail` | General Ledger Detail | Universal |
| 11 | Management | `mgmt.gl_summary` | General Ledger Summary | Universal |
| 12 | Management | `mgmt.executive` | Executive Summary Report | Universal |
| 13 | Management | `mgmt.chart_of_accounts` | Chart of Accounts Listing | Universal |
| 14 | Tax | `tax.vat_uk` | VAT Return (UK 9-box) | UK HMRC |
| 15 | Tax | `tax.bas_au` | BAS (Australia) | ATO |
| 16 | Tax | `tax.gst` | GST Return (Generic) | Multi-jurisdiction |
| 17 | Tax | `tax.sales_tax` | Sales Tax by Jurisdiction | US/Canada |
| 18 | Tax | `tax.corporation_tax` | Corporation Tax Computation | UK |
| 19 | Variance | `var.period` | Period-over-Period Comparison | GAAP/IFRS |
| 20 | Variance | `var.budget` | Budget vs Actual | Universal |
| 21 | Variance | `var.forecast` | Forecast vs Actual | Universal |
| 22 | Variance | `var.tracking` | Tracking Category Analysis | Universal |
| 23 | Variance | `var.year_end` | Year-End Comparison (Multi-Year) | GAAP/IFRS |
| 24 | KPI | `kpi.profitability` | Profitability Ratios | GAAP/IFRS |
| 25 | KPI | `kpi.liquidity` | Liquidity Ratios | GAAP/IFRS |
| 26 | KPI | `kpi.efficiency` | Efficiency Ratios | GAAP/IFRS |
| 27 | KPI | `kpi.solvency` | Solvency Ratios | GAAP/IFRS |
| 28 | KPI | `kpi.startup` | Startup Metrics (Burn, Runway, CAC, LTV) | Universal |
| 29 | Audit | `audit.tb_adjusted` | Adjusted Trial Balance | GAAP/IFRS |
| 30 | Audit | `audit.journal_entries` | Journal Entry Report | Universal |
| 31 | Audit | `audit.audit_trail` | Full Audit Trail | Universal |
| 32 | Compliance | `compliance.xbrl` | XBRL/iXBRL Tagging Report | Multi-jurisdiction |
| 33 | Compliance | `compliance.mpm` | Management Performance Measures (IFRS 18) | IFRS |

The Internal Verification category (SKILLs 5--7) contains cross-validation reports. The Trial Balance Verification SKILL confirms debits equal credits. The Balance Sheet / Cash Flow Reconciliation SKILL validates that net cash change reconciles to the cash balance sheet movement. The Intercompany Elimination Check verifies proper elimination for consolidated reporting. These reports execute automatically at period close and feed results into the approval workflow.

### 4.4 Output and Distribution

#### 4.4.1 Six Output Formats

Every report SKILL can produce output in any of six formats, selected via the `output.format` parameter. The format choice determines the Stage 5 serializer but does not affect upstream pipeline stages.

| Format | Serializer | Primary Use Case | Key Properties |
|--------|-----------|-------------------|----------------|
| JSON | Native struct serializer | API responses, downstream processing, LLM consumption | Schema-validated; self-describing with embedded metadata |
| HTML | Jinja2 template engine | Web viewing, dashboards, email body | Responsive CSS; print-friendly `@media print` styles |
| PDF | Playwright headless browser | Document distribution, archival, filing | Professional pagination; headers/footers; digital signature ready |
| CSV | Pandas flattening engine | Spreadsheet import, analysis, data exchange | Header metadata rows; RFC 4180 compliant |
| XBRL | LXML taxonomy mapper | Machine-readable regulatory filing | Taxonomy-mapped elements; ESMA/HMRC compliant ^19^|
| iXBRL | HTML + XBRL hybrid | Human-readable filing with embedded machine data | Inline XBRL tags; UK mandate from April 2028 ^121^|

JSON is the default format and the native representation of the report data model, including metadata such as SKILL ID, request ID, framework, entity, currency, period, and generation timestamp. HTML templates are framework-aware: IFRS produces a "Statement of Profit or Loss" header, while GAAP produces "Income Statement," with terminology sourced from the active rule bundle. PDF generation uses a headless browser to render HTML templates with print-specific CSS. CSV output includes comment-prefixed header rows encoding the same metadata as JSON, so consumers can identify report provenance without external context.

#### 4.4.2 Report Scheduling

Report execution triggers through four scheduling models ^96^ ^122^. **Time-based** scheduling runs reports at fixed intervals: daily, weekly, monthly, quarterly, or annual. **Event-driven** scheduling triggers generation in response to system events such as period close completion, threshold breach, or adjusting entry posting. **Data-driven** scheduling monitors specific conditions and triggers when met --- for example, a burn rate alert when net burn exceeds a threshold, or a DSO report when 90+ day AR crosses 20%. **On-demand** scheduling covers user-initiated requests through the chat interface or API.

The scheduling engine supports distribution via email (SMTP with TLS, password-protected PDF attachments, PGP encryption), SFTP (encrypted file transfer), API/webhook (POST to external endpoints), and collaboration platforms (Microsoft Teams via Graph API, Slack via webhooks). Date formulas such as "LastMonth," "CurrentQuarter," "YearToDate," and "Trailing12Months" resolve at execution time against the entity's fiscal calendar ^96^.

#### 4.4.3 XBRL/iXBRL Layer

XBRL (eXtensible Business Reporting Language) embeds machine-readable tags into financial reports. iXBRL (inline XBRL) combines human-readable HTML with embedded XBRL tags, producing a document readable by both humans and machines ^19^. The XBRL/iXBRL generation pipeline operates as a six-stage process receiving JSON output from a core statement SKILL and producing a tagged regulatory filing.

Stage 1 generates HTML in human-readable form. Stage 2 maps each line item to the appropriate XBRL taxonomy element --- for example, "Revenue" maps to `ifrs-full:Revenue`. IFRS 18 introduces new elements for mandatory subtotals, including `ifrs-full:OperatingProfitLoss`, incorporated in the IFRS 2025 taxonomy ^19^. Stage 3 embeds XBRL tags as HTML attributes using the `ix:` namespace. Stage 4 generates XBRL context elements defining the reporting entity, period, and currency unit. Stage 5 validates against taxonomy schema requirements: calculation consistency, business rules, mandatory item checks, data type validation, and duplicate detection ^123^ ^48^. Stage 6 outputs the final `.html` file containing embedded iXBRL.

The UK mandate timeline drives prioritization. From April 2028, all UK companies must file accounts via software-only iXBRL ^121^ ^124^. HMRC has mandated iXBRL for company tax returns since 2011 ^125^. In the EU, ESMA's ESEF mandates iXBRL for listed companies ^19^. The Compliance XBRL SKILL (`compliance.xbrl`) wraps any core statement SKILL and produces iXBRL output for the selected jurisdiction, making regulatory submission a one-parameter extension of standard report generation.



---



## 5. Multi-Currency, Multi-Standard and Tax Engine

The accounting system's ability to operate across borders, jurisdictions, and regulatory frameworks is not an add-on feature — it is a structural property of the data model and processing engine. This chapter details three interconnected subsystems: the multi-currency architecture that ensures compliance with IAS 21 (*The Effects of Changes in Foreign Exchange Rates*), the configurable tax engine that supports five tax types across 130+ jurisdictions, and the accounting standards compliance layer that enables simultaneous GAAP and IFRS reporting with native IFRS 18 readiness. These subsystems share a common design philosophy: compliance is achieved through metadata-driven configuration rather than code-level branching, enabling the same ledger to serve multiple standards, currencies, and tax regimes without data duplication.

---

### 5.1 Multi-Currency Architecture

#### 5.1.1 Three-Currency Model per IAS 21

IAS 21 establishes a mandatory three-layer currency model that every transaction and entity must navigate ^126^ ^127^. The system implements this model at the data layer, storing all three currency perspectives for every foreign currency journal line. This design ensures that translation, revaluation, and consolidation operations never require retrospective reconstruction of converted amounts.

| Currency Type | Definition | Determination | Stored Per |
|---|---|---|---|
| **Functional currency** | Currency of the primary economic environment in which the entity operates | Primary indicators: revenue currency, cost currency, competitive/regulatory currency; secondary indicators: financing currency, retained-receipts currency ^128^ ^64^| Entity (rarely changes) |
| **Transaction currency** | Currency in which a transaction is denominated or requires settlement | The actual currency of the invoice, payment, or contract | Journal line (every transaction) |
| **Presentation currency** | Currency in which financial statements are presented | Chosen for reporting; may differ from functional currency | Entity (can vary by report) |

Functional currency determination follows the hierarchical assessment prescribed by IAS 21 paragraphs 9–14 ^128^ ^64^ ^129^. The entity records the basis for its determination in structured JSON within the `entity_functional_currency` table, documenting which primary and secondary indicators supported the conclusion. A change in functional currency is permitted only when there is a change in the underlying transactions, events, and conditions; it is applied prospectively from the date of change with no restatement of prior periods ^64^.

Every journal line in a foreign currency transaction stores three amounts: the transaction currency amount (the original denomination), the functional currency equivalent (converted at the transaction-date spot rate), and optionally the reporting currency amount (for entities that report in a currency different from their functional currency). The conversion metadata — exchange rate value, rate date, rate type used, and a reference to the specific rate record — is immutable and stored as an audit trail on each line. This enables precise reconstruction of any conversion for audit or error investigation purposes.

The system maintains a master currency registry based on ISO 4217, currently supporting more than 150 active currency codes with plans for Phase 3 expansion to cover all 180+ ISO 4217 currencies. The registry distinguishes fiat currencies from crypto-assets: the latter are flagged (`is_crypto = TRUE`) and carry additional metadata for blockchain network and token contract address, enabling the system to handle cryptocurrency holdings under IAS 38 (*Intangible Assets*) ^130^ ^131^.

#### 5.1.2 Exchange Rate Management: Multi-Provider Architecture

The Exchange Rate Service is a dedicated microservice that provides rate lookup with caching, supporting multiple external providers with circuit-breaker failover. The design follows SAP's proven TCURR table pattern ^132^ ^133^, adapted for a cloud-native, API-first architecture.

| Provider | Coverage | Frequency | Cost | Base Currency | Use Case |
|---|---|---|---|---|---|
| ECB SDMX | ~30 currencies against EUR | Daily (weekdays at ~16:00 CET) | Free | EUR only | EUR-based closing rates, cost-free baseline ^134^ ^135^|
| XE.com (premium) | 130+ currencies | Real-time to hourly | ~$799/month enterprise | Any | High-precision real-time rates for active trading entities ^35^ ^136^|
| Open Exchange Rates | 200+ currencies | Hourly (paid tiers) | Free tier (1,000 req/mo); from $12/mo | USD (free); any (paid) | Historical rates, mid-tier backup, developer-friendly API ^137^ ^138^|
| Manual entry | Unlimited | On demand | None | Any | Corporate treasury rates, regulatory mandated rates, overrides |

The provider selection strategy operates on a priority cascade: ECB is queried first for all EUR-based pairs (daily, weekdays only); XE is queried for real-time requirements and non-EUR cross-rates; Open Exchange Rates serves as the historical and backup tier; manual entry functions as the override of last resort ^139^. A circuit breaker monitors each provider's response time and error rate; if a provider exceeds the stale threshold (24 hours without fresh data), the system automatically fails over to the next provider in the cascade and raises an operational alert. Redis caches current rates with a 1-hour TTL and historical rates with a 30-day TTL, reducing external API calls by approximately 85% under typical usage patterns.

Cross-rate derivation for currency pairs not directly quoted by a provider (for example, GBP/JPY when only EUR/GBP and EUR/JPY are available) uses triangular arbitrage via the EUR base: $\text{GBP/JPY} = \text{EUR/JPY} \div \text{EUR/GBP}$. The system records the derivation provenance, marking the resulting rate as `is_derived = TRUE` and linking it to the two source rates, ensuring full auditability.

For IAS 21 compliance, average rates are computed from daily spot rates for income and expense translation: $\text{Average Rate} = \frac{1}{n} \sum_{i=1}^{n} \text{Spot Rate}_i$ for the $n$ business days in the period. IAS 21 explicitly permits this practical approximation, though it cautions that average rates are inappropriate when exchange rates fluctuate significantly ^126^ ^140^.

#### 5.1.3 FX Gain/Loss Handling

Foreign exchange gains and losses are classified into two categories with distinct recognition timing and accounting treatment ^141^ ^142^ ^143^.

**Realized FX gains/losses** arise on settlement of a foreign currency monetary item. The realized gain or loss is the difference between the functional currency amount at which the monetary item was carried (after any revaluations) and the functional currency amount of the settlement proceeds or payment. Realized amounts are posted permanently to the P&L and are never reversed.

**Unrealized FX gains/losses** arise from period-end revaluation of open monetary items. At each reporting date, IAS 21.23 requires monetary items (cash, receivables, payables, loans) to be re-translated at the closing rate, while non-monetary items carried at historical cost (inventory, PP&E) are not retranslated ^126^ ^5^ ^144^. The resulting exchange difference is an unrealized gain or loss posted to the P&L for the period. Following Oracle GL and Dynamics 365 patterns ^145^ ^146^, prior-period unrealized gains/losses are reversed at the start of the new period to avoid double-counting when settlement occurs.

For foreign operation consolidation, when a subsidiary's functional currency differs from the parent's presentation currency, all resulting exchange differences are recognized in Other Comprehensive Income (OCI) as the **Cumulative Translation Adjustment** (CTA) ^126^ ^127^. The CTA is presented in a separate component of equity and is reclassified to profit or loss only on disposal of the foreign operation. Exchange differences on monetary items that form part of a net investment in a foreign operation are similarly recognized in OCI in consolidated financial statements per IAS 21.32–33 ^126^ ^147^ ^63^.

The full lifecycle of a foreign currency receivable illustrates the interaction between these treatments. A EUR 10,000 invoice issued when EUR/USD = 1.08 is initially recorded at $10,800. At period-end, if EUR/USD = 1.10, an unrealized gain of $200 is recognized. If the rate falls to 1.09 at the next period-end, a $100 unrealized loss is recognized (net unrealized gain now $100). Upon settlement at 1.12, a realized gain of $300 is posted — the difference between the $10,900 carrying amount and the $11,200 settlement value — while the cumulative prior unrealized gains are reversed.

#### 5.1.4 Phase 3 Implementation and Automatic Revaluation

Multi-currency bank accounts are fully supported, with each bank account operating in a specific currency while the GL tracks both the foreign currency balance and the functional currency equivalent. Foreign currency bank accounts are revalued at period-end following Dynamics 365 and NetSuite patterns ^148^ ^149^.

Phase 3 implementation delivers automatic period-end revaluation with configurable scheduling. The system identifies all open monetary items per entity, fetches the closing rate for each currency pair, calculates unrealized gains/losses, generates the revaluation journal entry, and posts it after approval. The revaluation run is tracked in the `revaluation_runs` table with full currency breakdown, enabling drill-down from the summary journal to individual line-item revaluations. Feature flags in `system_currency_features` allow per-entity enablement of capabilities including auto-revaluation, crypto asset accounting, and presentation currency translation.

---

### 5.2 Tax Engine Architecture

#### 5.2.1 Three-Layer Configurable Architecture

The tax engine follows a three-layer architecture informed by OECD VAT/GST Guidelines ^150^, HMRC MTD specifications ^22^, and EU OSS frameworks ^151^. This pattern — Rule Store, Execution Engine, Override Workflow — separates tax policy (what rules apply) from tax computation (how to calculate) from governance (who can override), enabling tax professionals to configure rules without engineering intervention.

**Layer 1: Rule Store.** The Rule Store is a structured repository where every tax rule is a configuration record with effective dates, priority ordering, and statutory references. Each rule specifies its tax type (VAT, GST, Sales Tax, WHT, DST), jurisdiction (country, subdivision, local authority), applicability conditions (transaction type, party type, product category, digital indicator, cross-border flag), rate configuration (rate type, rate value, compound flag), threshold conditions, exemption conditions, and place-of-supply determination method. Rules are versioned: each change creates a new version while historical versions are retained for audit. The `valid_from` and `valid_to` fields enable the engine to resolve which version applies based on the transaction's effective date, a requirement the OECD emphasizes for correct tax determination ^150^.

**Layer 2: Execution Engine.** The Execution Engine is a runtime rules interpreter that evaluates transactions against the Rule Store. Rules are assessed in strict priority order: specific jurisdiction rules (local authority > subdivision > country) take precedence over transaction-specific rules (digital services, land/property, transport), which precede party-type rules (B2B vs. B2C), which precede general default rules, which finally fall back to a jurisdiction-wide exempt or standard rate fallback. The engine supports five calculation structures: simple/additive taxation, compound taxation (tax on tax), cascading taxation, and parallel taxation on different bases ^44^ ^152^ ^153^.

**Layer 3: Override Workflow.** The Override Workflow provides a segregation-of-duties compliant approval process for manual tax adjustments. Any override of an engine-calculated tax amount requires a second-party review and approval, with the override reason, approver identity, and statutory justification logged immutably in the tax audit trail. This satisfies both internal control requirements and external audit expectations.

#### 5.2.2 Five Tax Types

The engine supports five distinct tax types, each with specialized handling:

| Tax Type | Mechanism | Standard Rates | Input Tax Recovery | Key Feature |
|---|---|---|---|---|
| **VAT** (Value Added Tax) | Credit-invoice with input tax deduction | UK: 20%, DE: 19%, FR: 20%, EU average: ~21% ^150^| Full for taxable supplies; partial exemption formula for mixed businesses | Reverse charge, intra-community supplies, OSS reporting |
| **GST** (Goods and Services Tax) | Credit-invoice with input tax credits | Australia: 10%, New Zealand: 15%, Canada: 5%, Singapore: 9% ^43^| Full recovery (with input-taxed vs. GST-free distinctions in Australia) | BAS (Australia), GST103 (NZ), GST34 (Canada) returns |
| **US Sales Tax** | Retail sales tax (single-stage, no credit chain) | Varies by state (~45 states with statewide tax) ^117^| None (tax collected = tax remitted) | Economic nexus post-*Wayfair*, marketplace facilitator laws ^118^|
| **Withholding Tax** (WHT) | Tax deducted at source on cross-border payments | Dividends: 0–30%; Interest: 0–25%; Royalties: 0–20% ^154^| N/A (deducted by payer) | Treaty rates vs. statutory rates; KPMG guide covers 130+ jurisdictions |
| **Digital Services Tax** (DST) | Revenue-based tax on digital services | Austria: 5%, France: 3%, Italy: 3%, UK: 2%, Turkey: 7.5% ^62^| None | Typically contingent on EUR 750M global / EUR 25M domestic revenue thresholds |

The tax type registry schema captures the distinct characteristics of each system: whether input tax recovery is available, whether reverse charge applies, whether digital submission is supported, and which jurisdictions are covered. This registry-driven approach means that adding a new tax type (for example, a newly introduced environmental levy) requires only configuration, not code deployment.

**US Economic Nexus** deserves special attention following the 2018 *South Dakota v. Wayfair* Supreme Court decision. States may now require out-of-state sellers to collect sales tax based on economic activity alone, without physical presence. Currently, 25 states limit economic nexus to a dollar threshold (typically $100,000), while others use a combination of dollar and transaction thresholds ^117^. Texas has the highest threshold at $500,000; most states use $100,000 as the standard ^118^. Two states (including New York) require both a dollar threshold ($500,000) AND a transaction threshold (100 transactions) to be met simultaneously ^118^. The engine tracks both revenue and transaction counts per state independently, alerting when either threshold approaches its limit.

#### 5.2.3 Place of Supply Engine

The place of supply engine determines which jurisdiction has the right to tax a transaction. This is the most critical component for cross-border compliance, and its design follows the OECD VAT/GST Guidelines which have been adopted by all OECD member countries with VAT ^150^.

The engine implements a 6-step pipeline:

**Step 1: Identify Supply Category.** The transaction is classified as goods, services, digital services, or a special category (land/property, admission to events, short-term transport hire, restaurant/catering).

**Step 2: Identify Party Types.** The relationship is classified as B2B (business-to-business), B2C (business-to-consumer), or B2G (business-to-government).

**Step 3: Determine Customer Location.** For B2B transactions, the customer's permanent business establishment is used. For B2C digital services, two pieces of non-contradictory evidence are required (IP address, billing address, payment method country, SIM country code) per EU OSS rules ^123^.

**Step 4: Apply Specific Rules.** Special categories override general rules: land and property are taxed where physically located; event admission is taxed where the event takes place; short-term vehicle hire is taxed where the vehicle is put at the customer's disposal ^31^.

**Step 5: Apply General Rules.** For B2B services not covered by specific rules, the place of supply is where the customer belongs — the customer self-assesses VAT under the reverse charge mechanism ^31^. For B2C services, the place of supply is where the supplier belongs, and the supplier charges VAT at their local rate ^41^. For B2C digital services, the place of supply is where the consumer is located, requiring the supplier to register and collect VAT in the consumer's jurisdiction or use the EU OSS scheme ^123^.

**Step 6: Validate Evidence.** The engine verifies that the evidence collected meets the minimum requirements of the determined jurisdiction. For EU OSS, two non-contradictory pieces of evidence are mandatory; for UK B2B transactions, a valid VAT number constitutes reasonable commercial evidence ^31^.

| Supply Category | B2B Rule | B2C Rule | Evidence Required |
|---|---|---|---|
| General services | Customer's jurisdiction; reverse charge ^31^| Supplier's jurisdiction ^41^| VAT number (B2B); none (B2C) |
| Digital services | Customer's jurisdiction; reverse charge | Consumer's usual residence ^123^| 2 non-contradictory pieces (IP, billing, payment country) |
| Land/property | Where property located ^150^| Where property located | Property address, title documentation |
| Event admission | Where event takes place ^31^| Where event takes place | Ticket, venue contract |
| Short-term transport hire | Where vehicle put at disposal ^31^| Where vehicle put at disposal | Hire agreement, GPS data |
| Intra-community goods | Destination country (zero-rated supply) ^155^| Destination country | Transport documentation, evidence of delivery |

The pipeline's output is a jurisdiction determination record containing the primary taxing jurisdiction, any secondary jurisdictions, the evidence record (for audit), and references to all applicable tax rules. This record is stored immutably and linked to the transaction's audit trail.

---

### 5.3 VAT/GST Returns and Digital Submission

#### 5.3.1 UK VAT 9-Box Return

The UK VAT return follows a mandatory 9-box format submitted via HMRC's Making Tax Digital (MTD) API ^114^ ^156^ ^36^. All nine boxes are auto-calculated from the system's tax control accounts:

| Box | Description | Content | Calculation Basis |
|---|---|---|---|
| **1** | VAT due on sales and other outputs | Output VAT on all taxable supplies + reverse charge VAT + PIVA + domestic reverse charge | Sum of VAT output tax account postings |
| **2** | VAT due on acquisitions from EU | VAT on goods acquired from EU into Northern Ireland | NI-only; GB businesses leave blank post-Brexit |
| **3** | Total VAT due | Box 1 + Box 2 | Automatically calculated |
| **4** | VAT reclaimed on purchases | Input VAT on business purchases + import VAT + bad debt relief + error corrections | Sum of VAT input tax account postings |
| **5** | Net VAT to pay or reclaim | Box 3 − Box 4 | Positive = payable to HMRC; negative = reclaimable |
| **6** | Total value of sales (excl. VAT) | All outputs: standard, reduced, zero-rated, exempt, exports | Net values, not VAT amounts |
| **7** | Total value of purchases (excl. VAT) | All inputs: goods, services, capital assets, imports | Net values, not VAT amounts |
| **8** | Total value of supplies to EU (excl. VAT) | Goods dispatched to EU from Northern Ireland | NI-only post-Brexit |
| **9** | Total value of acquisitions from EU (excl. VAT) | Goods received from EU into Northern Ireland | NI-only post-Brexit |

Key rules govern the content: Boxes 1–5 contain VAT amounts, while Boxes 6–9 contain net values excluding VAT. Box 6 explicitly includes zero-rated and exempt supplies, meaning the total in Box 6 will typically exceed the taxable sales base. Digital records must be kept for six years ^22^, and every step from source data to submitted return must maintain a "digital link" — acceptable links include formula-driven spreadsheet connections, automated data imports, and API transfers; unacceptable links include copy-and-paste, manual re-keying, or CSV export/import without automation ^22^.

The system's tax control account architecture maps directly to the 9-box structure. VAT Output Tax (account 2100) aggregates to Box 1; VAT Input Tax (account 2110) aggregates to Box 4; the VAT Control Account (account 2120) holds the net position. Settlement entries clear the control account: when Box 3 exceeds Box 4, the control account is debited and the HMRC liability account is credited; when Box 4 exceeds Box 3, an HMRC receivable is debited and the control account credited ^114^.

#### 5.3.2 HMRC MTD API Integration

The Making Tax Digital (MTD) for VAT API enables direct digital submission to HMRC. Integration requires OAuth 2.0 client credentials authentication and mandatory fraud prevention headers.

| Endpoint | Purpose | Method |
|---|---|---|
| `/organisations/vat/{vrn}/obligations` | Retrieve VAT return periods and their status | GET |
| `/organisations/vat/{vrn}/returns` | Submit VAT return (9-box JSON payload) | POST |
| `/organisations/vat/{vrn}/returns/{periodKey}` | View a previously submitted return | GET |
| `/organisations/vat/{vrn}/liabilities` | Retrieve outstanding liabilities | GET |
| `/organisations/vat/{vrn}/payments` | Retrieve payments made | GET |

The fraud prevention headers, mandatory since 2021, include the `Gov-Client-Connection-Method` (describing the connection architecture), `Gov-Client-Public-IP` and `Gov-Client-Public-Port` (end-user network details), `Gov-Client-Device-ID` (a UUID for the device), `Gov-Client-User-IDs` (authenticated user identifiers), `Gov-Client-Timezone`, `Gov-Client-Screens` (screen resolution), `Gov-Client-Window-Size`, and vendor-level headers including `Gov-Vendor-Version` and `Gov-Vendor-License-IDs` ^157^ ^158^ ^159^ ^160^ ^161^. These headers are collected automatically by the API client library and transmitted with every request; failure to include them results in HTTP 400 Bad Request responses from HMRC.

The JSON submission payload carries the `periodKey` (identifying the VAT period), all nine box values, and a `finalised` boolean declaration. Late submission penalties follow a points-based system, and inaccuracies can result in penalties of 0–100% of the underpaid tax depending on behavior ^22^.

#### 5.3.3 EU One Stop Shop (OSS)

The EU OSS simplifies VAT compliance for cross-border B2C supplies. A business registers once in any EU member state (or its country of establishment for EU businesses) and files a single quarterly OSS return covering all intra-EU B2C supplies ^151^ ^157^. The return breaks down supplies by member state of consumption, type of supply, tax base, applicable VAT rate, and VAT amount. A single payment in the registration state's currency is made; the registration state redistributes VAT to member states of consumption.

**Critical OSS rules:** VAT is calculated at the rate of the member state of consumption, not the supplier's domestic rate. No input tax deduction is available through OSS — businesses must use their domestic VAT return or the EU refund mechanism for input tax recovery ^157^. Import OSS (for distance sales of imported goods below EUR 150) is filed monthly rather than quarterly. The EUR 10,000 threshold for intra-EU cross-border B2C supplies applies: below this, the supplier may charge VAT at its domestic rate; above this, VAT must be charged at the customer's member state rate ^150^.

The system's `tax.vat_uk` and `tax.gst` report SKILLs handle return preparation across jurisdictions, while the digital submission adapter layer translates the internal return format to HMRC MTD JSON, EU OSS portal format, or ATO SBR2 SOAP messages as appropriate ^31^ ^41^.

#### 5.3.4 Registration Threshold Monitoring

The threshold monitoring engine tracks cumulative transaction values against registration thresholds in real time. The engine aggregates per-country, per-state, per-tax-type, and per-transaction-type (B2B, B2C, digital, goods, services) over rolling 12-month, calendar year, and calendar quarter windows.

| Jurisdiction | Tax Type | Threshold | Notes |
|---|---|---|---|
| United Kingdom | VAT | GBP 90,000 (effective 2024) | Increased from GBP 85,000 ^43^|
| Germany | VAT | EUR 22,000 (prior year) / EUR 50,000 (current year) | Kleinunternehmer rule |
| France | VAT | EUR 91,900 (goods) / EUR 36,800 (services) | ^43^|
| EU (distance selling) | VAT | EUR 10,000 (cross-border B2C) | OSS threshold ^150^|
| Australia | GST | AUD 75,000 | ^43^|
| New Zealand | GST | NZD 60,000 | ^43^|
| Canada | GST/HST | CAD 30,000 | Small supplier threshold ^43^|
| Singapore | GST | SGD 1,000,000 | Among the highest globally ^43^|
| United States | Sales Tax | $100,000 (typical); up to $500,000 (Texas) | Varies by state; economic nexus ^117^ ^118^|

The alert engine operates on a 4-tier classification:

| Level | Trigger Condition | System Action |
|---|---|---|
| **Green** | Below 50% of threshold | No action; routine monitoring continues |
| **Amber** | 50–79% of threshold | Include in monthly compliance report; flag for review |
| **Orange** | 80–99% of threshold | Alert to tax team via email and dashboard; trigger registration preparation workflow |
| **Red** | 100%+ of threshold | Immediate alert to designated compliance officer; workflow triggers registration obligation and advises on ceasing trading if not registered |

For US sales tax, the monitoring engine tracks both revenue and transaction count thresholds independently ^118^ ^162^. A seller with 200 transactions at $5 each ($1,000 total) can trigger nexus in a state with a 200-transaction threshold even though revenue is far below the dollar threshold — a compliance scenario that catches many small e-commerce sellers unaware. The engine flags this pattern with a specific "transaction-count nexus risk" alert distinct from the revenue-based alert.

---

### 5.4 Accounting Standards Compliance

#### 5.4.1 Dual Framework Capability

Neither IFRS nor US GAAP prescribes a mandatory chart of accounts structure; both frameworks allow flexibility in account organization while mandating specific presentation requirements for financial statements ^64^ ^65^. The system exploits this flexibility through a metadata-driven approach: the same underlying chart of accounts adapts to multiple standards through standard-specific presentation metadata rather than structural duplication.

Each account carries a `standard_mapping` metadata block defining its eligibility, display name, presentation group, and statement line mapping for each supported framework (GAAP, IFRS, IFRS for SMEs). When generating financial statements, the report engine filters accounts by the target framework's `applicable` flag and applies the framework-specific presentation ordering and naming. This means a single transaction posting to account 3200 (Revaluation Surplus) is presented as an equity reserve under IFRS, excluded entirely under US GAAP (since revaluation is prohibited under GAAP except for impairment testing), and tagged differently for UK tax — all from the same ledger entry.

For small businesses, IFRS for SMEs serves as the default framework. It provides substantially fewer disclosure requirements (approximately 230 pages of guidance versus 3,000+ for full IFRS) and permits a single *Statement of Income and Retained Earnings* when the only equity changes result from profit/loss, dividends, errors, and policy changes ^163^. The system switches to full IFRS automatically when entity parameters cross SME thresholds.

#### 5.4.2 Key GAAP-IFRS Differences Handled

| Aspect | US GAAP Treatment | IFRS Treatment | System Accommodation |
|---|---|---|---|
| **Inventory valuation** | LIFO (Last-In, First-Out) permitted ^69^| LIFO prohibited; FIFO or weighted average required (IAS 2) ^69^| Inventory method stored as account metadata; LIFO-flagged accounts excluded from IFRS reports |
| **PPE valuation** | Historical cost only; no revaluation ^69^| Revaluation model permitted (IAS 16); changes recognized in OCI | Account 3200 (Revaluation Surplus) applicable under IFRS only |
| **Revenue recognition** | ASC 606 (principles-based, 5-step model) | IFRS 15 (substantially converged with ASC 606) | Same 5-step engine handles both; minor timing differences configurable per contract |
| **Extraordinary items** | Prohibited (ASC 225-20) | Not prohibited; material unusual items disclosed separately | Account range 8500–8999 filtered out under GAAP reports; included under IFRS |
| **Cash flow presentation** | Interest paid can be operating or financing; dividends paid can be operating or financing ^164^| Interest and dividends paid classified as financing; interest and dividends received as investing (IAS 7) | `framework` parameter on cash flow SKILL determines classification ^105^ ^106^|
| **Equity terminology** | "Stockholders' Equity", "Common Stock", "APIC" ^70^| "Shareholders' Equity", "Share Capital", "Share Premium" ^70^| Display name localization via standard metadata |
| **OCI presentation** | May be presented in statement of changes in equity OR notes ^164^| Must be presented as a separate statement ^164^| Metadata flag `requires_separate_oci_statement` controls report structure |

The metadata-driven approach means adding support for a new standard (for example, UK GAAP FRS 102) requires only defining the mapping metadata — no changes to the ledger schema, transaction posting logic, or report generation code. This is the architectural foundation that enables the system to serve international accounting firms with clients across multiple jurisdictions from a single deployment.

#### 5.4.3 IFRS 18 Readiness

IFRS 18 (*Presentation and Disclosure in Financial Statements*), effective January 2027, introduces the most significant change to income statement presentation in over two decades ^51^. The system implements IFRS 18's requirements natively through the P&L report SKILL.

IFRS 18 replaces the free-form P&L structure with five mandatory categories:

| Category | Scope | Typical Line Items |
|---|---|---|
| **Operating** | Core business activities (default/catch-all category) | Revenue, COGS, SGA, R&D, depreciation of operating assets |
| **Investing** | Returns from investments and investing activities | Interest income, dividends received, gains on disposal of investments, share of JV profits |
| **Financing** | Cost of raising finance | Interest expense on debt, FX differences on financing liabilities |
| **Income Taxes** | Tax per IAS 12 | Current tax expense, deferred tax movement |
| **Discontinued Operations** | Components of the entity disposed of or held for sale (IFRS 5) | Results of disposed segments |

IFRS 18 introduces three mandatory subtotals: **Operating Profit or Loss**, **Profit or Loss before Financing and Income Taxes**, and **Profit or Loss** (net income) ^51^ ^99^. The indirect method cash flow statement must now start from Operating Profit or Loss (not Net Income as under current practice), and interest/dividends are reclassified: interest paid and dividends paid move to financing activities; interest received and dividends received move to investing activities ^103^.

**Management Performance Measures (MPMs)** are subtotals of income and expenses used by management in public communications outside the financial statements — commonly metrics like Adjusted EBITDA, underlying profit, or free cash flow. Under IFRS 18, MPM disclosures are mandatory and fall within audit scope ^100^. The system supports MPM reconciliation through the `compliance.mpm` report SKILL, which produces the mandatory reconciliation from the nearest IFRS-defined subtotal to the MPM, with tax effects and non-controlling interest effects disclosed separately. This reconciliation is presented in the notes to the financial statements and tagged in XBRL/iXBRL output for digital filing.

The IFRS 18 implementation also affects the balance sheet: goodwill must be presented as a single line item (not grouped with other intangibles), and current/non-current classification guidance is carried forward from IAS 1 with additional clarity ^103^. The P&L SKILL's `ifrs18_options` parameter enables transitional compliance (for entities adopting early) and full compliance (for mandatory adoption from January 2027), with the `compliance_level` parameter controlling which requirements are enforced in report validation ^51^.

---

### Integration Across Subsystems

The three subsystems described in this chapter — multi-currency, tax engine, and accounting standards compliance — do not operate in isolation. A cross-border B2C digital service transaction flows through all three: the multi-currency layer records the invoice in the transaction currency (say, EUR) and converts to the entity's functional currency (say, GBP) at the spot rate; the tax engine's place-of-supply pipeline determines the customer's jurisdiction, applies the correct VAT rate (20% for UK, 19% for Germany, etc.), and maps the output to the appropriate OSS return line; the standards compliance layer presents the revenue in the IFRS 18 Operating category for the P&L and translates the subsidiary's financial statements (if the entity reports in USD) with exchange differences routed to the Cumulative Translation Adjustment in OCI. The same ledger entry serves all three purposes, with metadata controlling the behavior at each layer — a design that eliminates parallel books, reduces reconciliation burden, and creates a single source of financial truth.



---



## 6. Document Processing and Workflow Automation

The transition from manual data entry to automated document processing represents one of the highest-impact capabilities in modern accounting systems. For a headless, LLM-native platform, document processing and workflow automation serve as the bridge between the physical world of paper invoices, emailed bills, and bank statements and the structured digital ledger. This chapter defines the requirements for document ingestion and extraction, bank feed integration, reconciliation workflows, recurring transactions, and approval routing — all designed to operate through natural language conversation rather than traditional graphical interfaces.

The economic case for automation is substantial. Research on the Multi-Agent Document Processing (MADP) architecture demonstrates that AI-powered extraction combined with human-in-the-loop (HITL) validation achieves 98.5% document-level accuracy while reducing full-time equivalent (FTE) requirements by 70% compared to manual processing ^10^. At a volume of 100,000 invoices per year, the savings amount to approximately $995,000 annually ^10^. These figures justify the architectural investment required to build a robust, production-grade document processing pipeline.

### 6.1 Document Ingestion and Extraction

#### 6.1.1 Document Types and Ingestion Channels

The system processes four primary document categories, each with distinct structural characteristics and extraction requirements. Supplier invoices (bills), customer invoices, receipts, and bank statements represent the overwhelming majority of documents that a small or medium-sized enterprise (SME) handles on a recurring basis. The system must accept these documents through multiple ingestion channels to accommodate diverse user workflows.

| Document Type | Supported Formats | Primary Extraction Fields | Typical Source |
|-------------|-----------------|------------------------|--------------|
| Supplier invoice / Bill | PDF, JPG, PNG, TIFF | Vendor, date, due date, line items, subtotal, VAT, total ^53^| Email attachment, upload, mobile capture |
| Sales invoice | PDF, JPG, PNG | Customer, invoice number, date, line items, amounts, tax ^81^| Email, customer portal, upload |
| Receipt | JPG, PNG, PDF | Merchant, date, items, total, payment method, tip ^165^| Mobile camera, email, upload |
| Bank statement | PDF, CSV, OFX, QBO | Account number, period, opening/closing balance, transactions ^47^| Upload, bank feed (see Section 6.2) |
| Credit note | PDF, JPG, PNG | Original invoice reference, credit amount, reason, date ^166^| Email attachment, upload |

The ingestion layer supports four distinct channels, mirroring the multi-channel approach used by production document processing systems ^90^. Email polling monitors dedicated accounting inboxes via webhook triggers, processing PDF and image attachments in real time as they arrive. The upload API accepts direct file submissions via RESTful endpoints with chunked upload support for files up to 50MB, batch upload for multiple documents, and idempotency keys to prevent duplicate processing. Cloud storage webhooks integrate with Google Drive, Dropbox, AWS S3, Azure Blob Storage, and SharePoint through native event notification mechanisms, triggering processing pipelines when new files appear in designated folders ^90^. Mobile capture provides native SDKs for iOS and Android that perform quality assessment, auto-enhancement (deskewing, contrast adjustment, noise reduction), and edge detection before transmission ^167^.

All documents, regardless of ingestion channel, are stored immutably with SHA-256 checksums and a complete processing history trail. Raw documents are encrypted at rest using AES-256-GCM and tagged with a retention class of `financial_7_years` to comply with UK tax record-keeping requirements ^22^. The processing pipeline assigns each document a unique identifier that persists through extraction, validation, and eventual linkage to ledger transactions, creating the unbroken digital link chain required by HMRC Making Tax Digital (MTD) regulations.

#### 6.1.2 Extraction Pipeline Architecture

The extraction pipeline follows a hybrid OCR-plus-LLM design inspired by the MADP multi-agent architecture ^9^and recent research on combining structural awareness from optical character recognition with semantic understanding from large language models ^168^ ^92^. The pipeline operates in six sequential stages, each with defined inputs, outputs, and error handling.

| Stage | Component | Function | Key Metrics |
|------|-----------|----------|-------------|
| 1. Preprocessing | Adaptive preprocessing module | Deskew, denoise, binarize, normalize to 300 DPI ^168^| +5–10% OCR accuracy improvement |
| 2. Classification | ResNet-18 CNN + LLM verification | Classify document type (invoice, receipt, statement) | 95.3% classification accuracy ^10^|
| 3. Parsing | Docling (IBM Research) | Layout analysis, table recognition, reading order | +17.5 pp document accuracy contribution; 35% token reduction ^10^|
| 4. OCR | Mistral OCR 3 / Tesseract / DocTR | Character recognition for scanned documents | 2.1% CER (Mistral OCR 3) ^169^|
| 5. LLM Extraction | GPT-4o Vision / Claude 3.5 Sonnet | Structured field extraction with schema validation | 92.9% F1 (Mistral-Small-3.2), 91.5% (GPT-4o) ^10^|
| 6. Validation | Custom rules engine | Mathematical cross-checks, duplicate detection, confidence scoring | Catches 91.67% of extraction errors ^9^|

The preprocessing stage is critical for maximizing downstream accuracy. Documents undergo noise reduction to eliminate scan artifacts, skew correction via Hough Transform alignment, contrast stretching to recover faded thermal paper text (essential for receipts), and resolution normalization to 300 DPI across all inputs ^168^. The classification stage uses a ResNet-18 convolutional neural network fine-tuned on document header regions to categorize incoming documents, with LLM-based semantic verification providing a cross-check on the CNN prediction ^10^.

The parsing stage employs Docling, IBM Research's open-source document processing toolkit, to convert documents into structured Markdown or JSON representations. Docling's layout analysis model (RT-DETR, trained on DocLayNet) identifies text regions, tables, and figures, while its TableFormer component reconstructs tabular structure from visually presented data ^170^. Docling reduces token count by 35% compared to raw OCR output, significantly reducing downstream LLM inference costs ^10^.

For the extraction stage, the system selects a processing path based on document characteristics. Born-digital PDFs with text layers undergo text-first extraction (faster, cheaper, 92%+ accuracy), while scanned documents and images are processed through vision-first multimodal LLM pipelines that achieve 92.71% accuracy versus only 64.03% for text-only pipelines on scanned content ^6^. The LLM processes documents at temperature 0.0 to ensure deterministic, consistent outputs, with structured output schemas enforced through Pydantic validation ^171^ ^81^. For high-value invoices, a two-pass verification step performs primary extraction followed by a validation challenge pass to catch errors before they propagate downstream ^114^.

#### 6.1.3 Key Performance Metrics

The extraction pipeline targets specific accuracy metrics at each stage. OCR accuracy at the character level ranges from 92–95% for production engines, with Mistral OCR 3 achieving a character error rate (CER) of 2.1% on complex layouts ^169^. End-to-end extraction accuracy — defined as the percentage of documents where all critical fields are extracted correctly without human intervention — reaches 95–97% when validation rules are applied ^172^.

At the document level, the MADP architecture reports 97–98.5% accuracy when combining AI extraction with human-in-the-loop validation, compared to 85% for pure AI without human review ^10^. The system achieves an 80% reduction in human intervention versus fully manual data entry, with the remaining 20% of documents requiring review concentrated in low-confidence extractions and complex multi-page documents ^10^. The human review time per flagged document averages approximately 45 seconds, compared to 120 seconds for full manual processing ^9^.

Documents with any field scoring below 90% confidence are automatically flagged for human review. The confidence scoring system uses a calibrated per-field approach: financial totals require ≥0.95 confidence for auto-approval, invoice numbers and dates require ≥0.90, line items ≥0.85, and descriptive fields ≥0.70 ^173^ ^174^. This tiered threshold reflects the differential cost of errors across field types — an incorrect total amount has far greater downstream impact than a misspelled vendor description.

#### 6.1.4 Validation Rules and Silent Failure Prevention

The validation layer is the most critical component for preventing silent failures — situations where incorrect data passes through the pipeline undetected and propagates into financial reports, tax calculations, and payment instructions ^86^ ^175^. The system implements four categories of validation rules.

Mathematical validation enforces amount consistency across every document. The sum of line items must equal the stated subtotal (±$0.01 tolerance). The subtotal plus tax minus discount must equal the total amount due (±0.5% tolerance for rounding). Per-line validation confirms that quantity multiplied by unit price minus discount equals the stated line total. For receipts, subtotal plus tax plus tip must equal the total ^176^ ^177^ ^178^.

Date validation ensures that invoice date precedes due date, that neither date is in the future, and that invoice dates fall within the last five years. VAT calculation verification confirms that stated tax amounts equal the net amount multiplied by the applicable rate (with tolerance for rounding differences across jurisdictions). Duplicate detection operates at three layers: exact matching on normalized invoice number plus vendor plus amount catches 30–40% of duplicates; fuzzy matching on amount, date proximity, and string similarity catches 60–80% of near-duplicates; and AI-powered multi-dimensional analysis achieves 95–99% duplicate detection accuracy at scale ^89^.

The system assigns confidence scores to every extracted field and flags any document with a validation failure for priority review. A periodic random sampling of 5% of auto-approved documents provides ongoing quality monitoring. Downstream anomaly tracking — such as unexpected payment disputes or vendor complaints — serves as a final safety net for catching extraction errors that evade upstream validation ^86^.

### 6.2 Bank Feed Integration

#### 6.2.1 Multi-Aggregator Strategy

Bank feed integration eliminates the most tedious aspect of bookkeeping: manual transaction entry. The system connects to banks through a multi-aggregator abstraction layer that routes connections based on geographic region, institution, and API availability. This approach maximizes coverage while minimizing single-provider dependency risk.

| Provider | Primary Region | Institution Coverage | Connection Method | PSD2 AISP | Priority |
|---------|---------------|---------------------|-------------------|-----------|----------|
| TrueLayer | UK, EU (14 countries) | 1,000s | Open Banking APIs, FCA-regulated ^48^| FCA-licensed | Primary (UK/EU) |
| Plaid | US, CA, UK, EU (20 markets) | 12,000+ live ^179^| OAuth + screen-scraping fallback | Yes ^179^| Secondary (UK/EU), Primary (US/CA) |
| Salt Edge | 60+ countries | 3,000+ ^180^| PSD2 Open Banking gateway | Yes ^180^| Tertiary (EU multi-country) |
| Yodlee (Envestnet) | Global | 17,000+ ^31^| Screen-scraping + direct API | Yes ^31^| Fallback (specialist institutions) |

The aggregator selection logic follows a priority chain. For UK connections, TrueLayer serves as the primary provider because it is purpose-built for UK and EU Open Banking, holds FCA regulation as an Account Information Service Provider (AISP), and supports instant bank payments through PSD2 APIs ^48^. Plaid provides secondary coverage with 12,000+ live institutions across 20 markets and supports additional product lines including identity verification and income verification ^179^. Salt Edge offers tertiary coverage for businesses operating across multiple EU countries, aggregating access to 3,000+ institutions in 60+ countries through a single PSD2 gateway ^180^. Yodlee provides fallback coverage for smaller institutions and credit unions that other aggregators may not support, with the broadest global footprint at 17,000+ institutions ^31^.

All EU and UK connections operate under PSD2 with Strong Customer Authentication (SCA), requiring multi-factor customer consent that expires after 90 days and must be renewed. The system manages this consent lifecycle automatically, sending renewal prompts before expiry and maintaining connection health monitoring with automatic retry on transient failures.

#### 6.2.2 Feed Ingestion Features

The ingestion pipeline follows a five-stage design: Poll → Normalize → Deduplicate → Queue → Process ^181^ ^182^. During the Poll stage, the system performs daily automatic polling for new transactions (configurable to hourly for high-volume accounts), with on-demand refresh available via API. On initial connection, the system backfills up to 12–24 months of historical transaction data ^153^, enabling immediate reconciliation against existing ledger entries. Real-time webhook subscriptions from supported aggregators trigger instant processing when new transactions post to the connected account.

Normalization transforms aggregator-specific schemas into a canonical transaction format. The canonical schema includes: `transaction_id` (aggregator persistent identifier), `account_id` (internal bank account reference), `amount` (normalized with positive for credit, negative for debit), `currency` (ISO 4217 code), `transaction_date` (posted date), `description` (raw bank narrative), `merchant_name` (where available — Plad reports 97% fill rate), `reference` (transaction reference number), `transaction_type` (debit, credit, transfer, fee, interest), and `status` (pending, posted, cancelled) ^157^ ^183^. The raw aggregator response is stored in a JSONB column for audit and debugging purposes.

Deduplication operates through multiple mechanisms. Aggregator-provided persistent transaction IDs (such as Plaid's `transaction_id` field) survive updates and provide the primary deduplication key ^157^. For transactions without stable IDs (CSV imports), the system computes a content hash of date, amount, description, and account identifier. OFX and QBO file imports use the Financial Transaction ID (FITID) designed specifically for duplicate prevention ^47^ ^184^. A sliding window detection flags transactions within ±1 day with identical amounts and similar descriptions as potential duplicates requiring review.

The system supports unlimited multi-bank connections per organization, with each connection independently monitored for health. Connection status tracking includes `active`, `disconnected`, `error`, and `consent_expired` states, with automated alerting when a connection has not successfully synced within a configurable threshold (default: 48 hours).

#### 6.2.3 Bank Rules Engine

The bank rules engine provides Xero-style automatic categorization that matches incoming bank transactions against user-defined conditions and assigns general ledger accounts, contacts, tax rates, and tracking categories without manual intervention ^185^ ^186^.

| Condition Field | Supported Operators | Example |
|---------------|-------------------|---------|
| Description | `equals`, `contains`, `starts_with`, `ends_with`, `regex` | "contains SPOTIFY" |
| Payee / Merchant | `equals`, `contains`, `starts_with` | "equals Stripe" |
| Amount | `equals`, `between`, `greater_than`, `less_than` | "between 5.00 and 20.00" |
| Reference | `equals`, `contains`, `regex` | "matches INV-[0-9]+" |
| Bank Account | `equals`, `in` | "in [checking, savings]" |
| Direction | `is` | "is spend" or "is receive" |

Rules support AND/OR condition logic and are evaluated in priority order (lowest number first), with the first matching rule winning. Ambiguity detection flags transactions where multiple rules match, prompting user review to resolve conflicts.

Each rule has three possible execution modes. **Suggest** mode pre-fills the reconciliation form with the rule's assigned account, contact, and tax rate but requires explicit user confirmation — this is the recommended default for new rules ^185^. **Auto-apply** mode automatically categorizes and reconciles matching transactions without human intervention, appropriate only after a rule has demonstrated reliable matching across multiple cycles. **Disabled** mode stores the rule without evaluating it, useful for seasonal or temporary rules.

The system ships with 50+ pre-built rule patterns covering common transaction types: Stripe payouts, AWS charges, software subscriptions (Spotify, Slack, Zoom), telecommunications (mobile and broadband), council tax, utility bills, and payroll deposits. Users can create custom rules via natural language commands to the LLM ("Whenever Spotify appears in the description for between £5 and £20, categorize it as Software Subscriptions with 20% VAT"). Rule effectiveness analytics track the percentage of transactions auto-matched versus suggested versus missed, enabling continuous refinement.

### 6.3 Reconciliation Workflows

#### 6.3.1 Manual Reconciliation (MVP)

The Minimum Viable Product delivers a manual reconciliation workflow presented through the LLM conversational interface. The six-step workflow follows established best practices ^187^ ^188^ ^189^: (1) import bank transactions from feeds or file uploads; (2) review unmatched bank lines presented in priority order (highest amount first); (3) match bank transactions to existing ledger entries (invoices, bills, journal entries) using side-by-side comparison; (4) create new ledger entries for unmatched items with natural language commands ("That £56.40 charge is for office stationery from Tesco"); (5) confirm that the reconciliation balances (opening balance plus transactions minus reconciled items equals closing balance); and (6) generate a reconciliation report.

Matching supports one-to-one relationships (single bank transaction to single invoice) and one-to-many relationships (single bank deposit covering multiple invoice payments). Partial matching handles situations where the bank amount differs from the ledger amount — for example, when bank fees are deducted from a transfer. In partial match cases, the system prompts the user to explain the difference, recording the fee as a separate transaction line.

The reconciliation status flow tracks transactions through states: `imported` (raw from feed) → `unmatched` (no corresponding ledger entry found) → `suggested` (candidate match identified) → `confirmed` (user or rule accepted the match) → `reconciled` (final balanced state). Transactions can also transition to `excluded` (intentionally not reconciled, such as personal expenses on a business card) or `voided` (transaction reversed or cancelled) ^185^.

#### 6.3.2 ML-Powered Reconciliation (Phase 4)

Phase 4 introduces machine learning-powered matching modeled on Xero's JAX system, which targets 80%+ auto-reconciliation of bank statement lines in real time with 97%+ accuracy on suggested matches ^43^ ^44^. The architecture follows Xero's four-layer intelligence model:

| Layer | Function | Confidence Range | Action |
|------|----------|-----------------|--------|
| Rule | User-defined bank rules match on description, amount, reference | 95–99% | Auto-reconcile (if auto-apply enabled) ^185^|
| Match | Transaction matches existing document (invoice, bill, payment) | 90–100% | Auto-reconcile or suggest |
| Memory | Per-organization Random Forest learns from user's historical decisions | 75–94% | Suggest for review ^43^|
| Prediction | Anonymized crowd-sourced patterns from similar businesses | 60–74% | Suggest with caveat |
| Exception | Insufficient confidence across all layers | <60% | Flag for manual review |

The machine learning model is trained per organization using 12 months of historical reconciliation decisions ^153^, ensuring that patterns are specific to the business rather than generic across all users. The feature vector includes transaction amount, day of week, hour of day, merchant name, description keywords, historical category distribution, and reference number patterns ^190^. A Random Forest classifier handles the mixed feature types (categorical and continuous) effectively, with FuzzyWuzzy string similarity for vendor name variation matching ^190^.

Confidence scoring follows a tiered approach. Scores of 95–100% trigger auto-reconciliation when the feature is enabled. Scores of 90–94% auto-reconcile only in conservative mode. Scores of 75–89% generate suggestions for user review. Scores of 60–74% generate suggestions with an explicit caveat flag. Scores below 60% route to the exception queue for manual investigation ^191^ ^43^. Every ML match includes an explainability statement indicating which layer produced the match — Rule, Match, Memory, or Prediction — with specific reasoning ("You usually categorize transactions from ACME Corp to Office Supplies (94% historical rate)") ^152^.

The per-organization model addresses the cold-start problem through transfer learning: new organizations benefit from anonymized patterns learned across all businesses, while existing organizations receive increasingly personalized suggestions as their reconciliation history grows ^43^. Models retrain periodically as new reconciliation decisions are captured, with accuracy monitoring to detect degradation and trigger retraining when performance drops below thresholds.

### 6.4 Recurring Transactions and Approvals

#### 6.4.1 Recurring Transactions

Recurring transactions automate repetitive journal entries that follow predictable patterns. The system uses a template-plus-schedule architecture where each recurring transaction defines the transaction details (accounts, amounts, descriptions, VAT rates) and a schedule governing when instances are generated.

Schedules support frequencies of weekly, bi-weekly, monthly, quarterly, and annual, with custom intervals (e.g., every six weeks) available for non-standard cycles. End conditions specify when the series terminates: never (indefinite), after N occurrences, or until a specific date. Posting mode determines whether generated instances are automatically posted to the ledger or created as drafts requiring review. Pre-built templates cover common scenarios including rent, insurance premiums, loan repayments, depreciation, and subscription charges.

When a recurring transaction instance is generated, the system creates a transaction in `draft` status (if draft-for-review mode is selected) or `posted` status (if auto-post is enabled), with a reference linking back to the parent template. Missed generations — due to system downtime or configuration errors — are detected and queued for catch-up processing, with user notification via the LLM chat interface.

#### 6.4.2 Recurring Invoices and Payment Collection

Recurring invoices extend the template architecture to customer-facing billing. The template captures customer details, line items (products, services, descriptions, quantities, rates), tax settings, payment terms, accepted payment methods, and branding configuration ^187^ ^44^. On each scheduled generation, the system creates an invoice, transitions it through the standard invoice lifecycle (draft → approved → sent), and delivers it to the customer via email.

Integration with Stripe and GoCardless enables automatic payment collection. For Stripe, invoices use the `charge_automatically` collection method to attempt payment using the customer's saved default payment method ^183^. For GoCardless, recurring mandates authorize automatic Direct Debit collection on each invoice generation, with settlement occurring in 3–5 business days at a transaction fee of 1% plus £0.20 (capped at £4 in the UK) ^135^.

Failed payment handling follows a structured retry sequence. On first failure, the system sends a notification email to the customer and enters a 24-hour retry countdown. A second automatic attempt occurs after the retry interval; if this also fails, a third and final attempt is made after another 24 hours. After three failed attempts, the invoice is marked as "declined," automatic retry stops, and the customer is directed to update their payment information or pay manually. Each retry event is logged with the failure reason (insufficient funds, expired card, bank refusal) for reporting and dunning workflow triggers ^192^.

#### 6.4.3 Approval Workflows

The approval workflow engine addresses a critical gap in mainstream small business accounting software. Xero provides only single-step approval (one approver reviews and approves or rejects). QuickBooks Online Advanced, introduced in April 2024, supports multi-level chains but allows only one active approval workflow at a time, lacks delegation for out-of-office scenarios, and locks the feature behind the most expensive plan tier ($200+ per month) ^182^ ^134^. Sage Intacct offers stronger native workflows but with limited conditional branching ^193^. ApprovalMax, the de facto standard for Xero and QuickBooks users seeking robust approvals, demonstrates market demand for multi-step, conditional approval automation ^194^.

| Amount Threshold | Approval Route | Escalation SLA | Notification Channel |
|-----------------|----------------|---------------|---------------------|
| < GBP 500 | Auto-approved (no human review) | N/A | Log entry only |
| GBP 500 – 2,000 | Direct manager / Department head | 48 hours → escalate to finance director | LLM chat + email |
| GBP 2,000 – 10,000 | Finance director | 24 hours → escalate to CFO | LLM chat + email + push |
| > GBP 10,000 | CFO or designated executive | Same business day ^189^| All channels + SMS |

The approval engine supports multiple routing criteria beyond amount thresholds. Vendor category rules route contractor invoices to project managers regardless of amount. Department or cost centre rules direct marketing spend to the Marketing Director. First-time vendor rules apply additional scrutiny requiring finance review for any new supplier. Rules can be combined with AND/OR logic to create sophisticated conditional routing ("If amount > GBP 5,000 AND vendor is new, route to CFO; otherwise, route to department head") ^194^.

Delegation during absence allows any approver to designate a substitute for a defined period, with optional calendar integration for automatic out-of-office detection. Escalation rules specify the timeframe within which an approver must respond (configurable per step, with 48 hours as the default) and the escalation target if the deadline is missed. Reminder cadence sends notifications at 24-hour, 48-hour, and 72-hour intervals before escalation ^182^.

Approval actions include: **Approve** (advances to next step or finalizes), **Reject** (returns to submitter with required reason), **Request Changes** (returns with specific change requests without full rejection), **Delegate** (forwards to designated alternate), and **Add Comment** (note without status change). Every approval action is logged with timestamp, approver identity, action taken, IP address, device information, and comments — forming an immutable audit trail that satisfies separation of duties requirements under SOX and internal control frameworks ^193^.

The approval workflow integrates with the LLM conversational interface. Approvers receive notifications in chat ("Invoice INV-2025-0042 from ACME Supplies for GBP 3,240 requires your approval") and can approve or reject via natural language reply ("Approve that invoice" or "Reject — the amount seems wrong, check the line items"). For users preferring email, approval links provide one-click actions that route back through the API. The approval decision itself becomes an auditable event in the ledger, linked to the underlying transaction through the same correlation ID that connects the LLM request to the Numscript generation to the ledger posting.



---



## 7. Security, Compliance and Audit Trail

An AI-native accounting system operates at the intersection of two of the most stringently regulated domains: financial record-keeping, where immutable audit trails are mandated by securities and tax law, and artificial intelligence, where emergent regulations impose novel obligations for transparency, human oversight, and decision provenance. The architecture must simultaneously satisfy the EU AI Act's high-risk system requirements (enforceable August 2026) ^81^, the General Data Protection Regulation (GDPR)'s right to erasure, SOC 2 Type II assurance expectations, and jurisdiction-specific tax regimes such as HMRC's Making Tax Digital (MTD). This chapter defines the security architecture, immutable audit trail design, and regulatory compliance framework that together resolve the apparent tension between these obligations.

### 7.1 Security Architecture

The security model follows a defense-in-depth strategy with cryptographic controls at every layer: authentication, authorization, encryption in transit and at rest, and multi-tenant data isolation. Each control is designed to satisfy overlapping requirements across multiple compliance frameworks simultaneously, avoiding the proliferation of framework-specific implementations.

#### 7.1.1 Authentication: OAuth 2.0 + PKCE

The primary authentication protocol is OAuth 2.0 with Proof Key for Code Exchange (PKCE) per RFC 9700, the current security best practice for native and single-page applications ^34^. Access tokens are JSON Web Tokens (JWT) signed with RS256 (RSA with SHA-256), carrying a 30-minute expiry to limit the window of compromise. Each token embeds claims for user identity (`sub`), tenant scope (`org`), and role assignments (`roles`), enabling both authentication and coarse-grained authorization in a single round trip. Refresh tokens rotate on every use with a 60-day maximum lifetime, rendering stolen tokens useless once invalidated. For server-to-server integrations---such as connections to banking APIs or external ERP systems---mutual TLS (mTLS) provides certificate-based authentication that is resistant to credential replay attacks. Multi-factor authentication (MFA) via Time-based One-Time Password (TOTP) or WebAuthn/FIDO2 is mandatory for the Owner and Admin roles, and recommended for Accountant roles ^89^. Identity provider support includes Google Workspace, Microsoft Entra ID, Okta, and Auth0, with SAML 2.0 available for legacy enterprise integration ^195^.

The authentication flow follows the standard OpenID Connect (OIDC) pattern: the user authenticates at the identity provider, receives an ID token and access token, and presents the access token at the API gateway where tenant scope and RBAC claims are validated before the request reaches any service ^195^ ^196^.

#### 7.1.2 RBAC: Five Roles with Middleware-Enforced Claim Validation

Role-based access control (RBAC) implements five predefined roles aligned with standard accounting separation-of-duties practice ^89^. All permission checks are enforced at the middleware layer---never relying on client-side validation---with claims extracted from the JWT and validated against the endpoint's required role set on every request.

| Role | Ledger Access | Contacts | Reports | Settings | COA Edit | User Mgmt |
|------|-------------|----------|---------|----------|----------|-----------|
| Owner | Full read/write | Full | Full | Full | Yes | Yes |
| Admin | Full read/write | Full | Full | Most | Yes | Yes |
| Bookkeeper | Read/write | Read/write | Read-only | None | No | No |
| Accountant | Read/write | Read-only | Full (incl. export) | None | No | No |
| Viewer | Read-only | Read-only | Read-only | None | No | No |

The five-role structure directly implements SOC 2 Common Criteria CC6.3 (role-based access control) and supports SOX Section 404's separation-of-duties mandate. Sensitive operations enforce additional dual-control requirements: journal entry creation by a Bookkeeper requires approval by an Accountant or above; period-close requires that all entries be reviewed; chart-of-accounts changes are restricted to Admin; and AI model overrides require Accountant-level authorization with the override reason captured in the immutable audit trail ^89^. Quarterly automated access reviews identify inactive accounts (>30 days unused) and flag them for offboarding, satisfying CC6.1 and CC6.3 simultaneously.

#### 7.1.3 Data Encryption: TLS 1.3, mTLS, TDE, and AES-256-GCM

Encryption is applied at four distinct layers, each addressing a specific threat model and compliance requirement.

| Layer | Technology | Standard | Threat Addressed |
|-------|-----------|----------|-----------------|
| In transit (external) | TLS 1.3 | IETF RFC 8446 | Eavesdropping, man-in-the-middle |
| In transit (internal) | mTLS over gRPC | X.509 v3 | Service impersonation, lateral movement |
| At rest (database) | PostgreSQL TDE + LUKS | AES-256 | Physical media theft, backup compromise |
| At rest (files) | MinIO server-side encryption | AES-256-GCM | Object storage breach |
| At rest (sensitive fields) | Application-level | AES-256-GCM | Insider threat, column-level exposure |

TLS 1.3 is mandatory for all external-facing connections, with TLS 1.2 permitted only as a fallback for legacy clients. The protocol's 1-RTT handshake reduces latency versus TLS 1.2's 2-RTT, while perfect forward secrecy (PFS) is enforced by default through ephemeral key exchange, ensuring that compromise of a long-term private key does not expose past session data ^197^. Internal service-to-service communication over gRPC uses mutual TLS, where both client and server present X.509 certificates, preventing unauthorized services from interacting with the ledger or agent orchestrator even if they gain network access.

At the database layer, PostgreSQL Transparent Data Encryption (TDE) encrypts all data files, table indexes, and Write-Ahead Logs (WAL) with AES-256. The performance penalty is measured at less than 1% throughput reduction ^198^. For deployments where TDE is unavailable, Linux Unified Key Setup (LUKS) provides full-disk encryption at the volume level. Files stored in MinIO---invoices, receipts, reports---are encrypted with AES-256-GCM, with each tenant's files isolated in a dedicated bucket. Application-level encryption protects the most sensitive fields: bank account numbers, tax identification numbers, and email addresses are encrypted with AES-256-GCM before storage, using per-tenant encryption keys managed through a Hardware Security Module (HSM) or cloud Key Management Service (KMS) at FIPS 140-2 Level 3 ^199^. Tokenization replaces bank account numbers with reversible tokens for display purposes; only the last four digits are readable without decryption capability.

#### 7.1.4 Multi-Tenant Isolation

Multi-tenant isolation is achieved through a hybrid model that combines ledger-level, schema-level, and application-level separation. Formance's bucket mechanism maps each tenant to a distinct PostgreSQL schema, providing namespace isolation at the database level ^9^. Within each bucket, the tenant's ledgers (general ledger, payroll, budget) are fully segregated. PostgreSQL Row-Level Security (RLS) policies enforce tenant filtering at the database query layer: every SELECT, INSERT, and UPDATE is automatically scoped to the tenant_id extracted from the JWT claim, so that even a SQL injection vulnerability cannot expose cross-tenant data ^200^.

Cache isolation uses key-prefixing: all Redis keys are prefixed with the tenant identifier (`{tenant_id}:{resource}`), preventing cache poisoning or leakage between tenants. Event streaming uses topic namespacing (`ledger.{tenant_id}.transactions.created`), ensuring that NATS consumers receive only their tenant's events. File storage uses per-tenant MinIO buckets with tenant-scoped access policies. This layered isolation---ledger, schema, RLS, cache prefix, topic namespace, and bucket separation---creates defense in depth against cross-tenant data exposure, a critical requirement for financial SaaS where a single leakage incident can destroy trust.

### 7.2 Immutable Audit Trail

The audit trail design must satisfy two fundamentally different requirements: financial ledger immutability (mandated by SOX, GAAP/IFRS, and tax law) and AI decision provenance (mandated by the EU AI Act). Rather than building separate systems, the architecture creates two linked audit streams---financial and AI---that share correlation identifiers, enabling end-to-end reconstruction from a user's natural language request through the AI's reasoning to the final ledger posting.

#### 7.2.1 Formance Hash-Chained Ledger

The financial ledger implements Formance's native hash-chained architecture, where every transaction is cryptographically linked to its predecessor ^6^. Each posting record contains a SHA-256 hash computed over the concatenation of the transaction ID, timestamp, posting contents, and the previous transaction's hash. This Merkle-like chain creates tamper evidence: any retroactive modification of a historical transaction invalidates all subsequent hashes, detectable during routine verification-on-read operations.

Immutability is enforced at multiple levels. At the application layer, the postings table is append-only: no UPDATE or DELETE operations are permitted. Corrections---whether initiated by a human or triggered by an AI reversal workflow---are recorded as compensating entries that preserve the original transaction in the chain ^6^. At the storage layer, Write-Once-Read-Many (WORM) format prevents edits or deletions at the filesystem level ^201^. Idempotency keys on all posting operations ensure that duplicate submissions (from network retries or LLM re-execution) produce the same result without double-posting ^6^. Every read operation can optionally verify the full hash chain back to the genesis transaction, providing cryptographic proof of ledger integrity for auditors.

#### 7.2.2 Conversational Audit Trail

The conversational audit trail is a cross-dimensional architectural feature that links the WebSocket chat interface (Section 4), the Plan-and-Execute agent workflow (Section 6), and the hash-chained ledger into a single tamper-evident chain. When a user submits a natural language request---for example, "Record a £500 payment from Acme Corp"---the following chain is constructed:

1. The natural language request is captured with nanosecond-precision timestamp and session correlation ID.
2. The supervisor agent's routing decision and the specialist agent's chain-of-thought reasoning are logged as structured events.
3. The generated Numscript (the human-readable transaction DSL) is recorded, serving as both the executable instruction and the explanation of the AI's intent.
4. The deterministic validation result (balance check, COA membership, duplicate detection) is appended.
5. The human approval decision---approved, rejected, or modified---with reviewer identity and reason is captured.
6. The final ledger posting is committed to the Formance hash chain, carrying the session correlation ID in its metadata.

All six links share a common `session_id` and `trace_id`, enabling auditors to reconstruct the complete causal chain from utterance to ledger entry. This exceeds traditional accounting audit trails, which record *what* happened but not *why* it happened in human-understandable form. The Numscript itself serves as a human-readable explanation of the AI's decision, satisfying EU AI Act Article 13 (transparency) without additional infrastructure.

#### 7.2.3 Agent Decision Provenance

Every AI agent decision that affects financial records produces a structured provenance record capturing the complete decision context. The provenance schema is designed to exceed EU AI Act Article 12 requirements while supporting post-market monitoring, incident investigation, and third-party conformity assessment ^8^ ^202^.

| Provenance Field | Content | Compliance Purpose |
|-----------------|---------|-------------------|
| `provenance_id` + timestamp | Unique identifier, ISO-8601 nanoseconds | Uniqueness, temporal ordering |
| Correlation IDs | session_id, trace_id, tenant_id, user_id | End-to-end traceability |
| Agent identity | Agent name, version, model provider, model version, owner | Accountability, model card linkage |
| Input | Transaction data, retrieved context, prompt hash | Reproducibility, input validation |
| Reasoning | Chain-of-thought, confidence score, uncertainty quantification (entropy, top-2 margin, OOD flag) | Explainability, accuracy assessment |
| Alternative options | Rejected categories with confidence scores | Transparency, override justification |
| Tool calls | Tool name, input, output, duration, success/failure | Action trace, performance monitoring |
| Output | Decision, category, tax treatment, general ledger entry | Financial impact documentation |
| Validation | Automated checks (balance, duplicate, COA), guardrail results | Quality assurance, accuracy per Art. 15 |
| Oversight | Review type (auto/human), reviewer_id, decision, override reason | Human oversight per Art. 14 |
| Policy events | Classification, risk level, GDPR lawful basis, retention tag | Governance, legal basis, lifecycle |

The provenance record is cryptographically signed with HMAC-SHA256 using a dedicated audit key, producing tamper evidence equivalent to the financial ledger's hash chain. Full prompts (which may contain sensitive personal data) are stored in encrypted cold storage; only the SHA-256 hash and a retrieval key appear in operational logs, enabling GDPR erasure through key destruction without modifying the audit trail ^85^. Financial decision logs---categorization, reconciliation, journal entry creation---are retained for 7 years to satisfy SOX and IRS requirements. Operational model-invocation logs are retained for a minimum of 6 months per EU AI Act Article 12 ^203^ ^204^.

### 7.3 Regulatory Compliance

The compliance framework is organized around four regulatory regimes, with each control designed to satisfy multiple regimes where overlap exists. The cross-cutting compliance matrix in Table 12 of the design specification maps each architectural control to its supporting regulations ^6^ ^81^ ^205^ ^206^.

#### 7.3.1 EU AI Act: High-Risk System Classification

The system is classified as a high-risk AI system under Annex III, Section 5(b) of the EU AI Act, covering "AI systems intended to be used to evaluate the creditworthiness of natural persons or establish their credit score." This classification extends to systems that assess financial health and make automated decisions affecting access to financial resources, including transaction categorization, anomaly detection, and automated reconciliation ^17^ ^18^. The full set of high-risk obligations becomes enforceable on August 2, 2026 ^81^ ^11^. Non-compliance carries penalties of up to EUR 30 million or 6% of global annual turnover for Tier 2 violations ^81^---for a provider with EUR 100 million revenue, this represents a EUR 6 million exposure.

| Article | Requirement | Implementation |
|---------|-------------|---------------|
| Art. 9 -- Risk management | Continuous risk assessment lifecycle | Documented risk register with annual review; risk metrics dashboard |
| Art. 10 -- Data governance | High-quality, unbiased training data | Data quality management system; bias testing on categorization models; demographic parity checks |
| Art. 11 -- Technical documentation | Complete system documentation for conformity assessment | Architecture docs, model cards, training methodology, API specifications |
| Art. 12 -- Record-keeping | Automatic logging of all AI events; tamper-evidence; 6-month minimum retention | Structured JSON provenance logs; HMAC-SHA256 signing; 6-month operational / 7-year financial retention ^207^ ^203^|
| Art. 13 -- Transparency | Users informed of AI use; capability and limitation disclosure | Disclosure banner on AI features; model capability documentation; known limitations published; training data date range displayed ^10^|
| Art. 14 -- Human oversight | Meaningful human review with ability to intervene, override, and stop | Graduated autonomy (100% → sampled → exception-only); 6 approval gates; confidence-based routing at 0.85 threshold; "pause AI" emergency stop; override with reason capture ^208^ ^209^ ^210^ ^211^|
| Art. 15 -- Accuracy | Sufficient accuracy for intended purpose; regular assessment | Deterministic validation catches 91.67% of LLM errors; accuracy metrics published; continuous monitoring via LangSmith |

The Article 14 human-oversight implementation addresses each sub-requirement of paragraph 4 explicitly: reviewers see model cards displaying capacities and limitations (14(4)(a)); confidence scores and override statistics are always visible to combat automation bias (14(4)(b)); feature importance and similar historical cases support correct interpretation (14(4)(c)); one-click override with reason capture enables reversal of any AI decision (14(4)(d)); and a "pause AI" button provides immediate intervention capability (14(4)(e)) ^211^.

#### 7.3.2 GDPR: Pseudonymization with Managed Keys

The central tension between GDPR and financial accounting is Article 17's "right to erasure" versus the immutable ledger requirement. Direct deletion of ledger entries is architecturally impossible (the hash chain would break) and legally impermissible (SOX Section 802 makes destruction of financial records a federal offense). The resolution is a pseudonymization layer with managed encryption keys ^212^.

| Data Subject Right | Technical Implementation | SLA |
|--------------------|-------------------------|-----|
| Access (Art. 15) | Export all data linked to subject; structured JSON + human-readable PDF | 30 days |
| Rectification (Art. 16) | New corrected entry added; old entry cryptographically flagged as superseded; both retained for audit | 30 days |
| Erasure (Art. 17) | PII encryption keys destroyed; pseudonymous financial records preserved; transaction integrity maintained | 30 days |
| Portability (Art. 20) | Machine-readable export (JSON, CSV) of all subject data | 30 days |
| Restriction (Art. 18) | Processing flag set; data excluded from AI training; access restricted | Immediate |
| Objection (Art. 21) | Processing stopped for specified purposes; override logged | Immediate |

Under the pseudonymization model, personally identifiable information (PII)---names, email addresses, bank account numbers, tax IDs---is encrypted with tenant-specific keys at the point of ingestion. The encrypted values replace raw PII in all operational tables and logs. Financial transaction data (amounts, dates, account codes) remains in plaintext to preserve ledger integrity and auditability. When a verified erasure request is received, the tenant-specific encryption keys for that individual's PII are securely destroyed per NIST SP 800-88 (cryptographic erasure) ^212^. The pseudonymous identifiers remain, ensuring that the hash chain and double-entry bookkeeping are never compromised, but the PII is irretrievable. This approach has been endorsed by the European Data Protection Board in guidance on blockchain and GDPR compliance ^212^.

Lawful basis for processing is established separately for each purpose: core accounting/bookkeeping relies on contract (Art. 6(1)(b)); AI-assisted categorization on legitimate interest with a documented balancing test and opt-out availability (Art. 6(1)(f)); fraud detection on legal obligation (Art. 6(1)(c)); marketing on granular, separately withdrawable consent (Art. 6(1)(a)); and model improvement on legitimate interest with anonymization where possible ^212^.

#### 7.3.3 SOC 2 Alignment: All Five Trust Services Criteria

SOC 2 Type II assurance covers five Trust Services Criteria (TSC), each mapped to specific architectural controls ^205^ ^206^.

| TSC | Description | Key Controls | Evidence Collected |
|-----|-------------|--------------|-------------------|
| Security (CC6) | Protection against unauthorized access | RBAC with MFA, TLS 1.3, WAF, API gateway, intrusion detection, penetration testing | Quarterly access reviews, MFA enrollment reports, pen-test results, vulnerability scan reports |
| Availability (A1) | Systems available for operation | 99.9% SLA, multi-region DR, auto-scaling, health monitoring | Uptime reports, DR drill records, incident response logs |
| Processing Integrity (PI1) | Complete, valid, accurate, timely processing | Hash-chained ledger, double-entry enforcement, idempotency, deterministic validation, reconciliation | Reconciliation reports, transaction integrity checks, change tickets |
| Confidentiality (C1) | Confidential information protected | AES-256 encryption, DLP scanning, access controls, key management with HSM | Encryption configurations, DLP rules, quarterly access reviews, key rotation logs |
| Privacy (P1) | Personal information handled per commitments | GDPR compliance, pseudonymization, consent management, DSAR workflow, 30-day SLA | Privacy policy, DSAR handling records, retention schedules, anonymization job logs |

The SOC 2 Type II audit process requires a minimum 3-month observation period during which controls operate continuously while evidence is collected. Following the observation period, a CPA firm examines the evidence and tests control effectiveness over 4-6 weeks before issuing the report ^213^. Continuous monitoring automates much of this evidence collection: certificate expiry monitoring triggers alerts 30 days before expiration; vulnerability management scans run weekly with critical CVEs flagged within 24 hours; SIEM correlation raises alerts when unauthorized access attempts exceed 5 in 10 minutes; and all changes are ticketed with peer review required, with emergency changes (>2 per month) flagged for management review ^89^ ^214^.

#### 7.3.4 HMRC MTD Compliance Roadmap

HMRC's Making Tax Digital (MTD) for VAT requires that businesses keep digital records and submit VAT returns through compatible software using API-based submission. The compliance roadmap is staged across four phases.

Phase 1 (MVP) establishes the foundational digital record-keeping infrastructure: all transactions are recorded digitally with no manual re-keying between systems, and the VAT return is computed and previewed as a 9-box summary (Boxes 1-9) before any submission. This satisfies MTD's "digital records" requirement because the system captures transactions at source---via bank feed import, document extraction, or conversational entry---and maintains the full audit trail linking each return line item to its underlying transactions.

Phase 2 adds HMRC API submission: the computed 9-box return is submitted directly to HMRC's VAT API using OAuth 2.0 authentication, eliminating manual filing. Error handling covers HMRC API failures (rate limiting, validation errors, authentication expiry) with automatic retry and human escalation for unresolvable errors. The digital link requirement---MTD's prohibition on manual copy-paste between systems---is satisfied intrinsically because the document extraction pipeline, Numscript generation, ledger posting, and tax computation form one continuous pipeline with automatic linking at each stage.

Phase 3 extends to multi-scheme support: the tax engine's three-layer architecture (Rule Store, Execution Engine, Override Workflow) is parameterized for different VAT schemes including Standard VAT, Flat Rate Scheme, and Cash Accounting. Each scheme's rules are stored as configuration, not code, enabling scheme switches without deployment.

Phase 4 addresses group VAT (consolidated returns for corporate groups) and partial exemption (for businesses with mixed taxable and exempt supplies). These require allocation methodology support and apportionment calculations that build on the multi-entity architecture defined in Section 3. The bi-temporal posting model (transaction date and VAT point date stored separately) handles the cash accounting scheme's tax-point timing correctly.

The estimated annual compliance program cost---spanning SOC 2 Type II, penetration testing, encryption infrastructure, audit logging, EU AI Act compliance, and GDPR legal review---ranges from $155,000 to $330,000 ^215^. This is substantially lower than the exposure from non-compliance: up to 6-7% of global annual turnover under the EU AI Act alone, plus comparable penalties under GDPR. For a provider with EUR 100 million revenue, the compliance investment represents approximately 0.15-0.33% of revenue versus a 6% non-compliance exposure---a risk-adjusted return that justifies the investment as a cost of market access rather than a discretionary expenditure.

A critical architectural principle underlying all four compliance domains is that compliance is a byproduct of normal operation, not an add-on layer. The hash-chained ledger that ensures financial integrity simultaneously produces the tamper-evident audit trail required by SOX and the EU AI Act. The pseudonymization layer that resolves the GDPR erasure conflict simultaneously enables multi-tenant isolation. The deterministic validation that catches LLM errors before posting simultaneously satisfies SOC 2 Processing Integrity and EU AI Act Article 15 accuracy requirements. The Numscript output format that makes AI decisions auditable simultaneously provides the transparency required by EU AI Act Article 13. This convergence reduces the marginal cost of each additional compliance certification and creates a defensible regulatory moat: competitors retrofitting compliance onto legacy architectures must build separate systems for each regime, while this architecture achieves multi-regime compliance through shared primitives.



---



## 8. MVP Requirements Specification

This chapter defines the complete Minimum Viable Product (MVP) scope for the headless, LLM-native accounting system. The MVP delivers a functional single-entity accounting system for a UK VAT-registered small business, operated entirely through natural language conversation with an LLM. Eight weeks of development, 48 engineering days, and a team of 2–3 engineers produce a system that completes the full bookkeeping cycle — from transaction recording through VAT return preview — without the user writing code or opening a spreadsheet.

### 8.1 MVP Scope and Success Criteria

#### 8.1.1 Target Profile

The MVP serves a single business entity: a UK-based freelancer, sole trader, or limited company with 0–10 employees, VAT-registered, operating in a single currency (GBP). This profile was selected because it represents the largest addressable market of UK small businesses (over 5.5 million SMEs as of 2024) while constraining complexity to a tractable eight-week build ^15^. The constraint to a single entity, single currency, and single VAT jurisdiction eliminates the engineering surface area of multi-currency revaluation, intercompany elimination, and multi-tax jurisdiction rule engines — each of which is a significant module in its own right reserved for later phases.

The user interacts with the system exclusively via natural language chat. There is no traditional graphical user interface (GUI), no spreadsheet import wizard, and no report builder canvas. Every function — recording a transaction, creating an invoice, importing a bank statement, running a report — is accessed through conversational text. This is the defining architectural constraint of the MVP and the differentiator from incumbent platforms.

#### 8.1.2 Success Criteria

The MVP is deemed successful when a user can complete the following end-to-end bookkeeping cycle entirely via chat, with every step producing validated accounting data:

1. **Record transactions** via natural language (e.g., "Paid £120 to Acme Consulting for marketing services plus VAT"), with the system parsing the utterance into a balanced double-entry transaction.
2. **Create and send an invoice** to a customer, with line items, VAT calculation, PDF generation, and email delivery.
3. **Import a bank statement** (CSV or OFX format) with automatic column mapping and duplicate detection.
4. **Reconcile** imported bank transactions against ledger entries through conversational matching.
5. **Run a VAT return** for the quarter, with automatic nine-box calculation and MTD-compliant preview.
6. **Generate a Profit & Loss statement and Balance Sheet**, with period comparison, delivered in the user's preferred output format (JSON, HTML, PDF, or CSV).

A non-negotiable quality gate requires that **all data passes double-entry validation** — total debits must equal total credits on every transaction, enforced at the database constraint level ^2^. Additionally, the HMRC MTD (Making Tax Digital) VAT nine-box return must be calculable and previewable, though actual digital submission to HMRC is deferred to Phase 2.

#### 8.1.3 Timeline and Resourcing

The MVP spans eight calendar weeks at 75% engineering velocity, comprising approximately 48 engineering days. The team consists of 2–3 engineers: one backend/ledger specialist (Formance, PostgreSQL, double-entry logic), one API and integrations engineer (FastAPI/NestJS, bank import, PDF generation), and optionally one LLM/chat engineer (prompt engineering, skill registry, conversation design). The timeline is intentionally aggressive, prioritising vertical integration of the core loop — chat entry to ledger write to report generation — over breadth of features.

Table 8-1 summarises the ten modules, their scheduling, complexity ratings, and engineering effort estimates.

**Table 8-1: MVP Module Summary**

| Module | Name | Week(s) | Complexity | Effort (days) |
|---|---|---|---|---|
| 1 | Chart of Accounts | 1 | Low | 3 |
| 2 | Core General Ledger | 1–2 | High | 10 |
| 3 | Contact Management | 2 | Low | 3 |
| 4 | Bank Statement Import | 2–3 | Medium | 5 |
| 5 | Manual Bank Reconciliation | 3 | Medium | 5 |
| 6 | Basic Invoicing | 3–4 | Medium | 6 |
| 7 | VAT Calculation & MTD Preview | 4–5 | Medium | 5 |
| 8 | Core Financial Reports | 5–6 | Medium | 5 |
| 9 | LLM Chat Interface | 6–8 | High | 10 |
| 10 | Authentication & Security | 2 (ongoing) | Low-Medium | 3 |
| | **Total** | | | **55** |

The 55-day estimate inflates to approximately 48 effective days at 75% velocity (accounting for context switching, code review, and integration testing), confirming the feasibility of the 8-week schedule ^2^ ^3^. Modules 2 (Core General Ledger) and 9 (LLM Chat Interface) together consume 20 of the 48 days (42%), reflecting their centrality to the system's value proposition. The schedule assumes a Docker Compose development environment with PostgreSQL 16+, Formance Ledger, Redis, and MinIO running locally on each engineer's workstation.

### 8.2 MVP Module Specifications

#### 8.2.1 Module 1: Chart of Accounts (3 days)

The Chart of Accounts (COA) is the hierarchical account structure that forms the backbone of the general ledger. The MVP provides eight pre-loaded COA templates, each tailored to a specific UK business structure and VAT status ^15^ ^16^:

- UK Sole Trader — No VAT (40 accounts)
- UK Sole Trader — VAT Registered (55 accounts)
- UK Limited Company — No VAT (50 accounts)
- UK Limited Company — VAT Registered (65 accounts)
- UK Partnership — No VAT (45 accounts)
- UK Partnership — VAT Registered (60 accounts)
- Micro-Entity Simplified (30 accounts)
- Property/Landlord — VAT Registered (45 accounts)

All templates follow a standard five-category, four-digit numbering scheme: Assets (1000–1999), Liabilities (2000–2999), Equity (3000–3999), Revenue (4000–4999), and Expenses (5000–6999). Within each range, account codes are spaced at intervals of 10 (e.g., 1010, 1020, 1030) to allow future insertion without renumbering ^15^. Each account is typed as one of nine categories: Bank, Current Asset, Fixed Asset, Current Liability, Long-term Liability, Equity, Revenue, Direct Cost, or Expense.

VAT rate assignment is stored as account metadata. Each account can be tagged with a default VAT rate (20% standard, 5% reduced, 0% zero-rated, or exempt). When a transaction is posted to that account, the system applies the rate automatically unless the user overrides it in the natural language instruction. Accounts support soft delete via an enabled/disabled flag — disabled accounts remain in historical transactions but cannot be selected for new entries.

Each COA account maps to a Formance ledger account address using the pattern `gl:{account_code}:{entity_id}`, ensuring namespace isolation per business entity ^3^.

The LLM SKILLs exposed for this module are: `coa.list` ("Show me my chart of accounts"), `coa.add_account` ("Add a new account called Marketing Expenses under code 5210"), `coa.edit_account` ("Rename account 6100 to Software Subscriptions"), and `coa.set_vat_rate` ("Set VAT rate on account 4000 to zero-rated").

#### 8.2.2 Module 2: Core General Ledger (10 days)

The Core General Ledger is the highest-complexity module in the MVP. It converts natural language utterances into structurally validated, double-entry transactions backed by a Formance-style programmable ledger ^2^ ^3^.

**Natural language parsing** accepts inputs such as "Paid £120 to Acme Consulting for marketing services plus VAT" and decomposes them into structured transactions with identified accounts, amounts, and VAT splits (£100 net + £20 VAT at 20%). The parsing pipeline uses an LLM with structured output constraints (JSON Schema) to guarantee parseable output, followed by a deterministic validation layer that catches the 91.67% of errors that raw LLM generation produces without guidance ^5^.

Transactions are modelled in Numscript-style syntax with sum-to-zero enforcement at the storage level. Every transaction enforces total debits equal total credits via a database constraint that rejects any unbalanced entry ^2^. The transaction data model consists of three core tables: `transaction` (id, date, description, reference, contact_id, total_amount, currency, status, metadata, created_at), `posting` (id, transaction_id, account_id, debit_amount, credit_amount, description), and `vat_line` (id, posting_id, vat_rate, vat_amount, net_amount, vat_type as input or output).

The module supports simple two-sided entries (one debit, one credit), multi-line splits (multiple debits and/or credits within a single transaction), and both VAT-inclusive and VAT-exclusive amount entry. Journal entry numbering follows an auto-sequential format `JE-YYYY-NNNN` (e.g., JE-2025-0042). Transaction status flows through three states: **Draft** (editable, not yet posted to the ledger), **Posted** (immutable ledger entry), and **Reversed** (compensating entry created via a reversing journal). A full audit trail records created_at, created_by, and ip_address for every transaction ^2^.

Technical decisions include: append-only postings table (no UPDATE or DELETE — corrections are made via reversing entries), idempotency key on every transaction write (client-generated UUID to prevent duplicates), and bi-temporal timestamps (effective_date for when the event occurred, recorded_at for when the system recorded it).

Table 8-2 presents the seven GL transaction SKILLs available in the MVP.

**Table 8-2: GL Transaction SKILLs**

| Skill ID | Description | Example Query |
|---|---|---|
| `gl.record_expense` | Record an outgoing expense payment | "Paid £50 for office stationery at Tesco" |
| `gl.record_income` | Record an incoming payment as income | "Received £500 from client for consulting" |
| `gl.record_transfer` | Transfer between bank accounts | "Transferred £1,000 from current to savings" |
| `gl.journal_entry` | Post a manual journal entry | "Journal: Debit Rent £500, Credit Bank £500" |
| `gl.list_transactions` | List or filter transactions | "Show me all transactions last month" |
| `gl.transaction_detail` | View a specific transaction | "Show me transaction JE-2025-0042" |
| `gl.undo_transaction` | Reverse a posted transaction | "Undo that last entry, I made a mistake" |

#### 8.2.3 Module 3: Contact Management (3 days)

Contact management provides the customer and supplier directory used by invoicing, transaction attribution, and accounts receivable/payable (AR/AP) tracking. Each contact has a type: Customer, Supplier, or Both. Core fields include name, company name, email, phone, billing address, shipping address, VAT number (EU/UK format), payment terms (Net 30 as default), default GL account, and currency. Contacts support an Active / Archived status lifecycle.

A key convenience feature is auto-creation from transaction descriptions: when the user says "Paid £9.99 to Spotify for my subscription," the LLM extracts "Spotify" as a supplier name, checks for an existing contact, and creates one automatically if none is found. Duplicate detection runs against name, email, and VAT number fields. For each contact, the system tracks running balances: total invoiced, total paid, and total owing — providing an instant AR/AP position per customer or supplier.

The SKILLs for this module are: `contact.create`, `contact.edit`, `contact.list`, `contact.detail`, and `contact.archive`.

#### 8.2.4 Module 4: Bank Statement Import (5 days)

The bank statement import module enables manual ingestion of bank transactions from CSV and OFX files. CSV import supports flexible column mapping — the system attempts to auto-detect date, description, amount (or separate debit/credit columns), reference, and type columns, and prompts the user to confirm or correct the mapping when ambiguity exists. OFX file parsing supports versions 1.02, 2.1, and 2.2, covering the overwhelming majority of UK bank export formats ^47^ ^184^.

Seven pre-built bank templates ship with the MVP, each with known CSV column layouts: Barclays, HSBC, Lloyds, NatWest, Monzo, Starling, and Revolut. These templates eliminate the column-mapping step for users of these institutions. Duplicate detection uses FITID (Financial Institution Transaction ID) for OFX files and a SHA-256 hash of date + amount + description for CSV files, ensuring the same transaction is never imported twice ^47^.

The bank account entity stores account name, sort code, account number, IBAN, currency, opening balance, and current balance. Multiple bank accounts are supported per entity. Imported transactions flow through a three-stage status: **Imported** (raw from file), **Categorized** (matched to a GL account or existing invoice/bill), and **Reconciled** (confirmed against a ledger entry).

Table 8-3 shows the supported file formats and their priority levels.

**Table 8-3: File Format Support**

| Format | Version(s) | Priority | Notes |
|---|---|---|---|
| CSV | Any (flexible column mapping) | P0 | Universal fallback for all banks |
| OFX | 1.02, 2.1, 2.2 | P0 | Standard format; includes FITID for deduplication ^47^|
| QIF | Quicken Interchange | P1 | Post-MVP; lower adoption in UK |

The bank module SKILLs are: `bank.import_csv`, `bank.import_ofx`, `bank.list_accounts`, `bank.add_account`, `bank.transactions`, and `bank.categorize`.

#### 8.2.5 Module 5: Manual Bank Reconciliation (5 days)

Bank reconciliation matches imported bank transactions to ledger entries (invoices, bills, and manually recorded transactions). The MVP implements a conversational reconciliation workflow where the LLM presents unmatched items to the user and guides them through matching decisions ^187^ ^188^.

The reconciliation workflow follows six steps: (1) import the bank statement, (2) review unmatched bank lines, (3) match to existing invoices, bills, or ledger entries, (4) create new ledger entries for unmatched items, (5) confirm the reconciliation balance agrees, and (6) generate a reconciliation report.

Matching supports three patterns. **One-to-one**: a single bank transaction matches a single ledger entry (e.g., a bank deposit matches one invoice payment). **One-to-many**: a single bank deposit matches multiple invoice payments (e.g., a customer pays three invoices in one lump sum). **Partial matching**: the bank amount differs from the ledger entry amount, with the system prompting the user to explain the difference (commonly bank fees deducted before deposit) ^188^.

The reconciliation report presents: opening balance per bank, plus bank transactions during the period, minus reconciled items, equals closing balance — verified against the closing balance per books.

Table 8-4 lists the reconciliation SKILLs.

**Table 8-4: Reconciliation SKILLs**

| Skill ID | Description | Example Query |
|---|---|---|
| `recon.start` | Begin a reconciliation session | "Start reconciliation for Barclays current account" |
| `recon.match` | Match a bank line to a ledger entry | "Match this £240 bank line to invoice INV-0012" |
| `recon.create_and_match` | Categorise and match an unmatched item | "This £50 is for office supplies — categorise and match" |
| `recon.status` | Check reconciliation progress | "Show me my reconciliation progress" |
| `recon.report` | Generate a reconciliation report | "Generate reconciliation report for June" |

#### 8.2.6 Module 6: Basic Invoicing (6 days)

The invoicing module creates, sends, and manages sales invoices to customers. Invoice creation supports line items with description, quantity, unit price, VAT rate (20% standard, 5% reduced, 0% zero-rated), and line total calculated automatically. Invoice numbering follows the format `INV-YYYY-NNNN`.

The invoice status lifecycle comprises six states: **Draft** (editable), **Sent** (delivered to customer, core fields become immutable), **Viewed** (customer opened the email), **Paid** (payment recorded against the invoice), **Overdue** (past due date, auto-transitioned by time-based detection), and **Cancelled** (voided, requires a credit note if amounts were posted) ^46^ ^79^.

Critical immutability rules apply: after an invoice is Sent, core fields — customer, line items, amounts, and VAT — become unmodifiable. Corrections require a credit note workflow (negative invoice referencing the original) followed by re-issuance. Payment recording is the only safe post-send operation ^15^.

Credit notes are supported as negative invoices referencing the original invoice number. PDF generation uses a headless browser engine (WeasyPrint or Playwright) to produce printable invoice documents with the business's branding. Email delivery tracks view status (transitioning the invoice from Sent to Viewed when the customer opens the email). Overdue detection runs automatically: invoices past their due date transition from Sent/Viewed to Overdue without manual intervention.

Table 8-5 presents the invoice SKILLs and their example queries.

**Table 8-5: Invoice SKILLs**

| Skill ID | Description | Example Query |
|---|---|---|
| `invoice.create` | Create a new sales invoice | "Create invoice for ABC Ltd: 10 hours consulting at £80/hr plus VAT" |
| `invoice.send` | Send an invoice to a customer | "Send invoice INV-2025-0012 to john@abcltd.com" |
| `invoice.list` | List invoices with filtering | "Show me all unpaid invoices" |
| `invoice.mark_paid` | Record payment against an invoice | "Mark invoice INV-2025-0012 as paid — £960 received today" |
| `invoice.credit_note` | Create a credit note | "Create a credit note for £200 against invoice 0012" |
| `invoice.overdue` | Check overdue invoices | "Which invoices are overdue?" |

#### 8.2.7 Module 7: VAT Calculation and MTD Preview (5 days)

The VAT module automatically tracks VAT on every transaction. Output VAT (liability to HMRC) is recorded on sales and purchase invoices; input VAT (recoverable from HMRC) is recorded on expense transactions and purchase bills. Each VAT line is traceable back to its originating transaction, creating a complete audit trail per VAT return box ^216^ ^217^.

The module calculates the full UK nine-box VAT return:

- **Box 1**: VAT due on sales (output VAT collected)
- **Box 2**: VAT due on acquisitions from EU (reserved for post-MVP — Northern Ireland protocol)
- **Box 3**: Total output VAT (Box 1 + Box 2)
- **Box 4**: VAT reclaimed on purchases (input VAT paid)
- **Box 5**: Net VAT position (Box 3 − Box 4) — the amount owed to or reclaimable from HMRC
- **Box 6**: Total value of sales excluding VAT
- **Box 7**: Total value of purchases excluding VAT
- **Box 8**: EU sales (reserved for post-MVP)
- **Box 9**: EU acquisitions (reserved for post-MVP)

Three VAT schemes are supported: standard accrual accounting (default), cash accounting (VAT recognised on payment, not invoice date), and the Flat Rate Scheme (simplified percentage of gross turnover). VAT periods are configurable as monthly, quarterly, or annual.

In the MVP, the system produces an MTD-compliant preview of the nine-box return but does not submit digitally to HMRC — that capability requires HMRC developer account registration and OAuth2 integration deferred to Phase 2 ^22^ ^23^. However, the MVP already enforces MTD digital link compliance: every figure in the VAT return flows automatically from source transaction through to the return preview via formula-driven digital links, with no manual re-keying or copy-paste at any step ^22^. Digital records are preserved for the statutory six-year period from the date of creation.

The VAT SKILLs are: `vat.preview_return`, `vat.transaction_detail`, `vat.adjustment`, and `vat.audit_trail`.

#### 8.2.8 Module 8: Core Financial Reports (5 days)

The reporting module generates the four essential financial reports that every UK small business requires, plus two ageing reports for receivables and payables management. All reports are implemented as deterministic, cacheable SKILLs with defined JSON schemas, processed through a five-stage report engine pipeline: (1) Parameter Ingestion, (2) Query Execution, (3) Data Transformation, (4) Rule Application, and (5) Output Formatting.

Table 8-6 describes the five MVP reports.

**Table 8-6: Core Financial Reports (MVP)**

| Report | Skill ID | Description | Key Sections |
|---|---|---|---|
| Profit & Loss | `report.pl` | Revenue minus expenses over a period | Revenue, Direct Costs, Gross Profit, Operating Expenses, Net Profit ^52^|
| Balance Sheet | `report.bs` | Assets, liabilities, and equity at a point in time | Current Assets, Fixed Assets, Current Liabilities, Long-term Liabilities, Equity ^218^|
| Trial Balance | `report.tb` | All account balances verifying debits equal credits | Account, Debit, Credit, YTD Debit, YTD Credit ^219^ ^220^|
| Aged Receivables | `report.ar_aging` | Outstanding customer balances by time bucket | Current, 1–30, 31–60, 61–90, 91+ days ^221^|
| Aged Payables | `report.ap_aging` | Outstanding supplier balances by time bucket | Current, 1–30, 31–60, 61–90, 91+ days ^221^|

Report parameters include: period (start_date, end_date), comparison mode (prior period or prior year), accounting basis (accrual default, cash optional), output format (JSON for API consumers, HTML for readable rendering, PDF for document distribution, CSV for spreadsheet import), and number format (GBP with pence). The IFRS 18 five-category Profit & Loss structure is reserved for Phase 3, effective January 2027 ^51^.

The reporting SKILLs are: `report.run`, `report.list`, and `report.schedule`.

#### 8.2.9 Module 9: LLM Chat Interface (10 days)

The LLM Chat Interface is the sole user interface of the system. It is a WebSocket-based conversational layer that orchestrates all accounting functions through natural language dialogue ^26^. This module consumes the second-largest effort allocation (10 days) because it integrates every other module's capabilities into a coherent conversational experience.

**Conversational transaction entry** allows multi-turn dialogue for complex transactions. For example, the user might say "Create an invoice" and the system responds with "Who is this for?" → the user names the customer → "What items?" → the user describes the services → "What payment terms?" → the user specifies Net 30 → the system presents a confirmation summary before posting. This multi-turn pattern is essential for transactions with multiple parameters that cannot be expressed in a single natural language utterance.

**Context memory** maintains entity state across the conversation: the current VAT period, recent transactions, open invoices, unreconciled bank lines, and selected bank account. The system remembers that the user's VAT quarter ends on March 31st and references it automatically when the user asks "Show me my VAT return."

**Intent routing** uses the supervisor pattern: the LLM classifies the user's intent, selects the appropriate SKILL, populates its parameters from the utterance, and executes it ^7^. If execution fails, the LLM translates the API error into a user-friendly explanation and suggests a correction. Destructive actions (reversing a transaction, cancelling a sent invoice) require explicit confirmation gates.

**Natural date parsing** supports expressions such as "last month," "yesterday," "Q2 2025," and "this financial year," converting them to precise date ranges for report and query parameters. **Ambiguity resolution** handles cases where the user's instruction could match multiple objects — "You mentioned two invoices for ABC Ltd — did you mean INV-0012 or INV-0015?"

Three persona options tailor the conversational tone: **Professional Accountant** (formal, precise language), **Friendly Advisor** (conversational, proactive suggestions), and **Minimal** (terse, data-focused responses). The user selects their preferred persona during first-time setup and can change it at any time via chat.

The Skill Registry is central to this module: 25+ MVP skills are registered with JSON schema definitions, each containing a description written from the LLM's perspective so the model knows when and how to invoke it ^119^ ^120^. Table 8-7 presents the consolidated MVP skill registry.

**Table 8-7: Complete MVP SKILL Registry (25+ Skills)**

| Skill ID | Category | Description | Example Query |
|---|---|---|---|
| `coa.list` | COA | List chart of accounts | "Show my chart of accounts" |
| `coa.add_account` | COA | Add a new account | "Add Marketing Expenses under 5210" |
| `coa.edit_account` | COA | Edit an existing account | "Rename 6100 to Software" |
| `coa.set_vat_rate` | COA | Set VAT rate on an account | "Set VAT on 4000 to zero-rated" |
| `gl.record_expense` | GL | Record expense payment | "Paid £50 for stationery at Tesco" |
| `gl.record_income` | GL | Record income receipt | "Received £500 from client" |
| `gl.record_transfer` | GL | Bank-to-bank transfer | "Transferred £1k to savings" |
| `gl.journal_entry` | GL | Manual journal entry | "Journal: Debit Rent, Credit Bank" |
| `gl.list_transactions` | GL | List/filter transactions | "Show last month's transactions" |
| `gl.transaction_detail` | GL | View transaction details | "Show JE-2025-0042" |
| `gl.undo_transaction` | GL | Reverse a transaction | "Undo my last entry" |
| `contact.create` | Contact | Create a contact | "Add ABC Ltd as a customer" |
| `contact.edit` | Contact | Edit a contact | "Update ABC's email" |
| `contact.list` | Contact | List contacts | "Who are my suppliers?" |
| `contact.detail` | Contact | View contact details | "Show ABC Ltd's balance" |
| `contact.archive` | Contact | Archive a contact | "Archive old supplier" |
| `bank.import_csv` | Bank | Import CSV statement | "Import my Barclays CSV" |
| `bank.import_ofx` | Bank | Import OFX statement | "Import HSBC statement" |
| `bank.list_accounts` | Bank | List bank accounts | "What bank accounts do I have?" |
| `bank.add_account` | Bank | Add a bank account | "Add my Monzo account" |
| `bank.transactions` | Bank | List bank transactions | "Show my latest Monzo transactions" |
| `bank.categorize` | Bank | Categorise a transaction | "This £40 is for travel" |
| `recon.start` | Reconciliation | Start reconciliation | "Reconcile Barclays account" |
| `recon.match` | Reconciliation | Match bank to ledger | "Match this to invoice 0012" |
| `recon.create_and_match` | Reconciliation | Categorise and match | "This £50 is office supplies" |
| `recon.status` | Reconciliation | Check progress | "Reconciliation status?" |
| `recon.report` | Reconciliation | Generate report | "Reconciliation report for June" |
| `invoice.create` | Invoice | Create invoice | "Invoice ABC: 10 hrs at £80+VAT" |
| `invoice.send` | Invoice | Send invoice | "Send INV-2025-0012" |
| `invoice.list` | Invoice | List invoices | "Show unpaid invoices" |
| `invoice.mark_paid` | Invoice | Record payment | "Mark 0012 as paid — £960" |
| `invoice.credit_note` | Invoice | Create credit note | "Credit note £200 against 0012" |
| `invoice.overdue` | Invoice | Check overdue | "Overdue invoices?" |
| `vat.preview_return` | VAT | Preview VAT return | "Show my VAT return" |
| `vat.transaction_detail` | VAT | VAT detail per transaction | "VAT on this transaction?" |
| `vat.adjustment` | VAT | Adjust VAT entry | "Adjust VAT on this expense" |
| `vat.audit_trail` | VAT | VAT audit trail | "Show VAT audit trail" |
| `report.run` | Report | Run a report | "P&L for last quarter" |
| `report.list` | Report | List available reports | "What reports can I run?" |
| `report.schedule` | Report | Schedule a report | "Email me P&L every month" |

The registry is loaded into the LLM's context at the start of each session, enabling the model to route user requests to the correct skill without hardcoded command patterns. The safety layer enforces `max_iterations` guards, permission checks, and confirmation requirements on all destructive operations ^120^.

#### 8.2.10 Module 10: Authentication and Security (3 days)

The authentication and security module protects all API endpoints and chat sessions. It implements JWT-based API authentication (JSON Web Tokens signed with RS256, 30-minute access token expiry, rotating refresh tokens with 60-day expiry), a single-user constraint for the MVP (multi-user support with role-based access control is deferred to Phase 2), and API key generation for programmatic access by integrations or accountants.

All communications use HTTPS/TLS 1.3 externally. Database encryption at rest is provided through PostgreSQL TDE (Transparent Data Encryption) or LUKS full-disk encryption. Row-level audit logging records every create, read, update, and delete operation on financial transaction data, including the user's identity, timestamp, IP address, and the before/after state of modified records. GDPR-compliant data handling is implemented from day one: personal data is processed with consent, and a pseudonymisation layer ensures the right to erasure can be honoured without corrupting the financial audit trail.

### 8.3 MVP Quality Gates

Quality gates are automated checks that execute before any transaction is posted to the ledger. These gates form a non-negotiable validation layer that prevents the 91.67% of double-entry errors that LLMs generate without structured guidance ^5^.

#### 8.3.1 Financial Validation Gates

Table 8-8 enumerates the six financial validation gates applied to every transaction.

**Table 8-8: MVP Quality Gates**

| Gate | Check | Action on Failure |
|---|---|---|
| Double-entry balance | Total debits equal total credits to the penny | Reject transaction; return error to LLM for explanation |
| COA membership | Every account code exists in the entity's chart of accounts and is active | Reject; suggest closest matching account code |
| Period open | Transaction effective date falls within an open accounting period | Reject or route to next open period with user confirmation |
| Unique reference | Reference number (invoice ref, journal number) not already used | Flag as potential duplicate; require explicit override |
| Amount bounds | All monetary amounts are positive, non-zero, and within reasonable limits | Reject with specific field-level error |
| VAT calculation | VAT amount equals net amount multiplied by the stated rate | Reject with recalculated correct amount |

These checks execute in a deterministic validation layer that operates independently of the LLM. No transaction can reach the ledger without passing all six gates. When a gate fails, the error is returned to the LLM, which translates it into natural language for the user and either suggests a correction or requests clarification.

#### 8.3.2 Operational Quality Gates

Beyond financial validation, three operational gates govern system behaviour. First, all write operations — transaction posting, invoice sending, account modification, bank transaction categorisation — require explicit user confirmation. The LLM presents a structured summary of the proposed action and waits for affirmative confirmation before executing. Second, the MVP registers a minimum of 25 LLM skills with complete JSON schemas; this threshold ensures sufficient functional coverage for the four validated user flows. Third, four complete end-to-end user flows must pass validation before the MVP is considered complete: first-time setup, daily bookkeeping, month-end reconciliation, and quarterly VAT return.

### 8.4 MVP Timeline

Table 8-9 presents the week-by-week deliverable schedule.

**Table 8-9: MVP Timeline (Week by Week)**

| Week | Deliverables | Dependencies |
|---|---|---|
| 1 | Project scaffolding, database schema, Docker Compose environment, COA templates (8 variants), GL engine core with Numscript execution | None |
| 2 | Contact management, bank account management, CSV/OFX import engine, authentication and security foundation | Week 1 (DB schema, COA) |
| 3 | Bank reconciliation engine (matching logic, report), invoice creation/sending, PDF generation, email delivery | Week 2 (bank import, contacts) |
| 4 | VAT calculation engine, nine-box return preview, credit note workflow, invoice immutability enforcement | Week 3 (invoicing) |
| 5 | Core report engine (5-stage pipeline), P&L, Balance Sheet, Trial Balance | Week 1 (GL engine) |
| 6 | Aged AR/AP reports, LLM skill registry (25+ skills), basic chat interface with intent routing | Week 5 (report engine) |
| 7 | Multi-turn conversation flows, context management, error handling with user-friendly explanations, natural date parsing | Week 6 (chat interface) |
| 8 | End-to-end integration testing, user acceptance testing (4 flows), bug fixes, documentation | All prior weeks |

Table 8-10 specifies the complete MVP technology stack.

**Table 8-10: MVP Technical Stack**

| Layer | Technology | Rationale |
|---|---|---|
| Ledger Engine | Formance Ledger (open source, MIT-licensed) | Sum-to-zero enforcement, append-only postings, Numscript DSL, PostgreSQL-backed ^2^ ^3^|
| API Framework | FastAPI (Python) or NestJS (Node.js) | Rapid development, OpenAPI specification, async support |
| Database | PostgreSQL 16+ | ACID compliance, JSONB for metadata, window functions for reports |
| LLM Orchestration | OpenAI GPT-4o / Claude Sonnet via function calling | Function calling for skill routing, 128K context window ^222^|
| Message Queue | Redis | Async processing, session caching, pub/sub |
| Document Storage | MinIO (S3-compatible) | PDF invoices, imported bank statements, attachments |
| PDF Generation | WeasyPrint or Playwright | Invoice PDFs, report PDFs |
| Background Jobs | Celery + Redis or BullMQ | Scheduled reports, VAT calculations, email sending |
| Container | Docker + Docker Compose | Consistent development and test environment |

### 8.5 MVP User Flows

Four end-to-end user flows are validated as part of the MVP acceptance criteria.

**Flow 1: First-Time Setup.** The user opens the chat and says "Set up my business." The system asks for business name and type, VAT registration status and number, financial year end, and preferred persona. It then creates the entity, loads the appropriate COA template, sets the VAT scheme, and initialises the first VAT period. The entire setup completes in under five minutes of conversation.

**Flow 2: Daily Bookkeeping.** The user records transactions via natural language — expenses, income, transfers — each confirmed by the system with a structured breakdown (debit account, credit account, amounts, VAT split) before posting. The user can list, view, and undo transactions conversationally.

**Flow 3: Month-End Reconciliation.** The user imports a bank statement (CSV or OFX), reviews unmatched lines, matches them to existing ledger entries or creates new entries for unmatched items, and generates a reconciliation report confirming the bank balance agrees with the books.

**Flow 4: VAT Return.** At quarter end, the user requests a VAT return preview. The system calculates all nine boxes from the period's transactions, presents the figures with an audit trail showing each transaction's contribution, and notes the amount due to HMRC and the payment deadline. The user is informed that direct digital submission to HMRC will be available in Phase 2, and for now should transfer the figures to their existing MTD bridging software.

The architecture of the MVP — ten modules, 39 registered skills, six financial quality gates, and four validated user flows — establishes the foundation upon which all subsequent phases build. Phase 2 (Months 3–5) adds bank feed automation, document extraction, recurring transactions, and HMRC MTD submission, expanding the skill registry to 65+ and reducing manual data entry effort by over 70%. The 8-week MVP demonstrates that a complete bookkeeping cycle can be operated entirely through natural language conversation, with every financial invariant enforced by deterministic validation layers beneath the conversational surface ^2^ ^3^ ^22^.



---



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

The MVP establishes the architectural foundation: a headless, LLM-native accounting system built on Formance Ledger with PostgreSQL, delivering ten core modules across chart of accounts, general ledger, contact management, bank import, reconciliation, invoicing, VAT calculation, core reports, chat interface, and authentication ^2^ ^3^. These 48 engineering days produce 25+ registered LLM SKILLs and achieve approximately 60% feature parity with Xero's core accounting modules ^15^ ^16^. The team is small — two to three engineers — reflecting the focused scope and the leverage provided by Formance's built-in double-entry enforcement and Numscript transaction modeling.

Xero parity progresses non-linearly across phases. The jump from 60% to 75% (MVP to Phase 2) is driven by bank feed automation, document extraction, and MTD (Making Tax Digital) VAT submission — capabilities that dramatically reduce manual data entry but are technically additive rather than structurally complex. The 75% to 88% leap (Phase 2 to Phase 3) requires foundational changes: a multi-currency layer compliant with IAS 21, a multi-tax jurisdiction engine, UK payroll with Real Time Information (RTI) submission, and inventory tracking — each introducing new data models and compliance surfaces. The final 88% to 95%+ gain (Phase 3 to Phase 4) comes from multi-entity consolidation, project tracking, a public API platform, an app marketplace, ML-powered reconciliation, and white-label capabilities — features that position the system as infrastructure rather than application ^45^ ^223^.

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

Team composition evolves with each phase. The MVP requires one backend/ledger engineer, one API/integration engineer, and one LLM/chat specialist. Phase 2 adds a bank feed integration engineer. Phase 3 adds a payroll specialist (critical given HMRC RTI compliance requirements) ^50^ ^55^. Phase 4 adds an ML engineer for the reconciliation engine and a DevOps/integrations specialist for the API platform and marketplace. Peak headcount of 5–7 occurs only in the final months; the average across 15 months is 3–4 engineers.

## 9.2 Phase 2: Automation (Months 3–5)

Phase 2 reduces manual data entry effort by 70% or more through three automation vectors: automatic data ingestion (bank feeds, document upload), intelligent categorization (rules engine), and workflow collaboration (multi-user, approvals). The 65 engineering days are distributed across seven major feature areas, with bank feed integration and HMRC MTD VAT submission carrying the highest complexity.

### 9.2.1 Month 3: Bank Feeds, Rules Engine, and Recurring Transactions

Bank feed integration is the highest-impact feature of Phase 2. The aggregator strategy uses a tiered failover chain: TrueLayer as the primary UK provider (PSD2-compliant, FCA-regulated), Plaid as secondary (broader coverage across 12,000+ institutions), Salt Edge for EU multi-country support, and Yodlee as fallback ^179^ ^48^ ^180^ ^31^. Each connection uses Open Banking APIs with Strong Customer Authentication (SCA), supports daily polling with configurable frequency (hourly, daily, weekly), and provides historical backfill of 12–24 months on initial connection ^153^. The ingestion pipeline — POLL from aggregator → NORMALIZE to canonical schema → DEDUPLICATE via persistent transaction IDs → QUEUE via message broker → PROCESS with automatic categorization triggering — runs asynchronously, allowing real-time webhook notifications without blocking the chat interface ^181^ ^182^. The canonical transaction schema normalizes across all aggregators, capturing transaction_id, account_id, amount, currency, transaction_date, description, merchant_name (97% fill rate from Plaid), reference, transaction_type, status, and raw original data for audit purposes ^157^.

The bank rules engine implements Xero-style automatic categorization. Each rule comprises conditions (description contains/equals/regex, amount between/equals/greater_than, reference matching, bank account filtering, direction) combined with AND/OR logic, and actions (assign contact, general ledger account, VAT rate, tracking category) ^185^ ^166^ ^186^. Three execution modes govern risk: Suggest (pre-fills categorization for user confirmation, recommended default), Auto-apply (automatically categorizes and posts, available only after a rule has proven reliable), and Disabled (stored but not evaluated). A pre-built library of 50+ common patterns covers recurring merchants such as Stripe payouts, AWS charges, council tax payments, and subscription services. Rule effectiveness analytics track the percentage of transactions auto-matched versus suggested versus missed, enabling continuous refinement.

Recurring transactions and invoices complete Month 3. Templates support weekly, bi-weekly, monthly, quarterly, and annual schedules with end conditions (never, after N occurrences, until date). Auto-post and draft-for-review modes accommodate varying risk tolerances. Pre-built templates cover rent, insurance, subscriptions, loan repayments, and depreciation. Recurring invoices extend the template architecture with auto-send via email, optional automatic payment collection via Stripe or GoCardless integration, failed payment retry logic, and the ability to pull unbilled time or expenses onto generated invoices ^187^ ^44^ ^192^.

### 9.2.2 Month 4: Recurring Invoices, Document Extraction, and Multi-User Support

Document upload and OCR (Optical Character Recognition) extraction transforms receipt and invoice images into structured transaction data. The pipeline runs: Document Upload → Preprocessing (deskew, enhance contrast) → OCR (Tesseract or DocTR) → LLM Extraction (GPT-4o Vision or Claude) → Validation Rules → Structured Output → Draft Transaction or Bill ^53^ ^172^. Validation enforces amount consistency (sum of line items equals subtotal equals total minus VAT), date validity (invoice date precedes or equals due date), VAT calculation verification (VAT amount equals net multiplied by rate), and duplicate detection (same vendor, number, and amount flagged). Low-confidence extractions (below 90%) route to human-in-the-loop review with side-by-side document and extracted data display. End-to-end extraction accuracy reaches 95–97% with validation rules, reducing human intervention by 80% compared to manual entry ^172^.

Multi-user support introduces role-based access control with five roles: Owner (full access including entity deletion and billing), Admin (full access except deletion), Bookkeeper (transaction recording, reconciliation, report generation), Accountant (read-only access to all data plus report execution), and Viewer (read-only, no transaction details). Features include email-based user invitation, activity logging, concurrent editing protection, and user-specific preferences for date format, currency display, and timezone.

### 9.2.3 Month 5: Approval Workflows and HMRC MTD VAT Submission

Approval workflows implement multi-step chains for invoices, bills, and journal entries. Configuration supports 1–3 approval levels with threshold-based routing (for example, under GBP 500 auto-approved, GBP 500–2,000 requires manager approval, over GBP 2,000 requires director approval). Approval types cover invoice approval, bill payment approval, and journal entry approval. Delegation during absence, automatic escalation after N days of inaction, and approval via natural language chat or email link provide operational flexibility. The status flow — Draft → Submitted for Approval → Approved → Posted/Sent, with a rejection path back to Draft — integrates with the Phase 2 notification system to alert approvers via chat and email.

HMRC MTD VAT submission is the compliance milestone of Phase 2. Requirements include HMRC Developer account registration, VAT registration number linked to MTD, OAuth2 authentication, mandatory fraud prevention headers (Gov-Client-Connection-Method, Public-IP, Device-ID, and others), and digital link compliance ensuring no manual re-keying between source data and submitted return ^22^ ^49^ ^23^. The submission flow — one-click VAT submission from chat, pre-submission validation of all nine boxes, HMRC obligation sync so the system knows which periods are due, status tracking from Submitted through Acknowledged to Accepted, and parsed error explanations for HMRC rejections — completes the compliance chain that began with MVP digital record keeping. Correction workflows support additional VAT returns for amendments.

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

Multi-currency support implements a three-currency architecture: functional currency (the primary economic environment, typically GBP for UK businesses), transaction currency (the denomination of individual invoices or payments), and presentation currency (the currency used for reporting). The system supports 150+ currencies per ISO 4217, with exchange rate sources from the European Central Bank (ECB, EUR-based), XE.com, and Open Exchange Rates. Daily automatic updates keep rates current. Transaction-level currency recording preserves the original transaction currency alongside the functional currency equivalent ^45^.

FX (Foreign Exchange) gain and loss handling complies with IAS 21. When an invoice is issued in a foreign currency, it is recorded at the spot rate on the invoice date. When payment is received, the spot rate on the payment date determines realized FX gain or loss. At period end, revaluation using the closing rate calculates unrealized gain or loss on open foreign currency positions. This three-stage treatment — transaction date, payment date, period-end — matches IAS 21 requirements for monetary items and ensures accurate financial reporting for businesses operating across borders.

The multi-tax jurisdiction engine expands the MVP's UK VAT support to encompass VAT, GST (Goods and Services Tax), US Sales Tax, and Digital Services Tax. The tax rule engine stores jurisdiction-specific rates, thresholds, exemptions, and place-of-supply rules. For EU operations, reverse charge handling for cross-border B2B transactions and OSS (One-Stop Shop) reporting are implemented ^150^. US sales tax includes economic nexus tracking post-Wayfair (2018) with destination-based sourcing, monitoring the relevant thresholds. The place of supply engine determines tax jurisdiction based on supply category, party types (B2B versus B2C), customer location, and applicable specific and general rules. Tax registration threshold monitoring provides Green, Amber, Orange, and Red alert levels as a business approaches registration requirements in each jurisdiction ^117^ ^118^.

### 9.3.2 Month 7: Inventory and Fixed Assets

Inventory and stock tracking introduces product catalog management with SKU, name, description, category, and unit of measure. Quantity tracking covers on-hand, committed, and available stock. FIFO (First-In, First-Out) is the default cost method, with average cost as an alternative. Stock adjustments handle write-offs, damage, and count corrections. Purchase orders flow through the full procurement cycle: creation, transmission to supplier, goods receipt (partial or full), bill matching, and payment. Cost of Goods Sold (COGS) is calculated automatically on sale through the inventory transaction flow — purchase order generates a liability, goods receipt increases inventory, sales invoice triggers COGS recognition and inventory reduction.

The fixed asset register tracks assets with automatic depreciation calculation. Asset categories carry default useful lives: Buildings (50 years), Vehicles (4 years), IT Equipment (3 years), Furniture (5 years), and Machinery (10 years). Two depreciation methods are supported: straight-line (default, equal charge per period) and diminishing value (reducing balance, higher charge in early years) ^224^ ^225^. Automatic monthly depreciation journals are posted to the general ledger: debit Depreciation Expense, credit Accumulated Depreciation. Asset disposal calculates gain or loss and removes the asset from the register. The Xero-style integrated approach — asset register with automatic GL posting — avoids the need for separate depreciation software.

### 9.3.3 Month 8: UK Payroll with RTI and Advanced Reporting

UK payroll with RTI integration is the most complex feature of Phase 3. Employee records store personal details, National Insurance number, tax code, salary or hourly rate, and start date. Pay elements include basic pay, overtime, bonuses, and commissions. Deductions cover PAYE (Pay As You Earn) income tax, employee National Insurance contributions (NICs), student loan repayments, and pension contributions. Employer costs include employer NICs, pension contributions, and apprenticeship levy. Payslip generation produces PDF documents. Pay runs support monthly, weekly, fortnightly, and four-weekly cycles ^50^ ^55^.

RTI submissions are mandatory for all UK employers. FPS (Full Payment Submission) reports employee payments, tax, NICs, and deductions on or before each payday. EPS (Employer Payment Summary) provides monthly adjustments, statutory payment reclaims, and other corrections by the 19th of each month. Late submission penalties scale from GBP 100 per month (1–9 employees) to GBP 400 (250+ employees) ^55^. Additional payroll features include starters and leavers processing (P45, starter checklist), statutory payments (SMP, SPP, SAP, SSP), Employment Allowance claim, P60 year-end generation, and auto-enrolment pension compliance ^54^ ^226^.

The advanced report library adds 15+ reports across six categories: Core Statements (Cash Flow Statement, Statement of Changes in Equity), Management (General Ledger Detail, Executive Summary, Cash Summary), Tax (Corporation Tax Computation), Variance (Budget vs Actual, Period-over-Period Comparison), KPI (Profitability Ratios, Liquidity Ratios, Burn Rate and Runway), and Audit (Audit Trail, Journal Entry Report) ^227^ ^228^.

### 9.3.4 Month 9: Custom Reports, Purchase Orders, and Tracking Categories

The custom report builder provides drag-and-drop (API-configurable) report design with column selection, filtering by any field with conditions (equals, contains, greater than, between), grouping by account, contact, date period, or tracking category, and sorting. Custom reports can be saved as templates and scheduled for daily, weekly, or monthly generation with email delivery in PDF, CSV, Excel, or JSON formats.

Purchase orders and bills implement a three-way matching workflow: Purchase Order → Goods Receipt → Bill ^187^. PO status flows from Draft through Sent, Partially Received, Received, Billed, to Closed. Bill creation auto-populates from received goods. Bill approval leverages Phase 2 workflows. Payment scheduling allows pay-now or pay-later with A/P aging and payment forecasting.

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

Multi-entity management supports multiple legal entities — companies, subsidiaries, branches — within a single account. Each entity maintains its own chart of accounts, bank accounts, tax settings, and reporting currency. Entity switching operates via natural language ("Switch to Acme UK Ltd"). Shared COA templates ensure consistency across entities. The five non-negotiable capabilities for multi-entity accounting are all implemented: automated intercompany elimination (intercompany sales and purchases netted to zero in consolidated reports), entity-level and consolidated reporting from the same underlying data, shared services allocation (central costs distributed to entities), multi-currency per entity with cumulative translation adjustments, and per-entity audit trails with access controls ^45^ ^223^.

Intercompany transactions generate automatic double-entry pairs. When Entity A invoices Entity B, the system simultaneously creates a receivable in Entity A and a payable in Entity B, auto-matches them as an intercompany pair, and eliminates both in consolidated reports. This eliminates the manual elimination journals that consume significant time in traditional group accounting and that are a common source of consolidation errors.

### 9.4.2 Project Tracking and Expense Claims (Months 11–12)

Project tracking provides time tracking, job costing, and project profitability analysis. Projects carry name, client, dates, budget, and status (Planning → Active → On Hold → Completed → Archived). Time entries log hours by project, task, and user. Expenses allocate to projects via receipt capture and direct assignment. Invoices link to projects for revenue tracking. Project P&L reports income versus costs per project with budget variance alerts. Utilization reports compare billable to non-billable hours. Margin analysis calculates gross profit margin per project.

Expense claims handle employee expense submission, approval, and reimbursement. Receipt capture uses the Phase 2 OCR pipeline. Mileage tracking applies HMRC approved rates (45p per mile for the first 10,000 miles, 25p thereafter). Per diem and subsistence claims follow standard categories. Multi-level approval workflows route from submitter through manager to finance. Reimbursement tracking schedules and records payments, with integration to payroll for on-payslip reimbursements. Policy enforcement enforces category limits, daily limits, and receipt requirements.

### 9.4.3 API Platform and Developer Ecosystem (Months 12–13)

The API platform exposes all system operations via a RESTful API with OpenAPI 3.0 specification and auto-generated documentation. Webhook subscriptions cover ten event types: entity.created, transaction.posted, invoice.created, invoice.paid, invoice.overdue, bank.transaction.imported, bank.reconciled, vat.return.submitted, contact.created, and report.generated ^21^. Tiered rate limiting supports free (100 requests per hour), pro (10,000 per hour), and enterprise (unlimited) tiers. URL-based versioning (/v1/, /v2/) ensures backward compatibility. OAuth2 authentication supports both client credentials and authorization code flows. Bulk operations enable batch transaction creation and contact updates. SDKs in five languages — JavaScript/TypeScript, Python, PHP, Java, and Go — lower integration barriers. The developer portal provides an interactive API explorer (Swagger UI), code examples in all SDK languages, a webhook testing endpoint, and a sandbox environment with pre-loaded test data.

### 9.4.4 App Marketplace (Months 13–14)

The app marketplace provides a directory of third-party integrations organized into eight categories: Banking (TrueLayer, Plaid, Yodlee), Payments (Stripe, GoCardless, PayPal), E-commerce (Shopify, WooCommerce, Square), CRM (HubSpot, Salesforce), Time Tracking (Toggl, Harvest), Expenses (Pleo, Soldo), Document (Dext, Hubdoc), and Analytics (Syft, Fathom). Each integration uses OAuth2 one-click installation with scoped permissions. An app review process ensures quality and security before listing. Developer analytics track installs, active users, and API calls. Featured and verified app badges highlight quality integrations. User reviews and ratings provide social proof. Billing integration supports subscription management for paid apps.

### 9.4.5 ML-Powered Reconciliation (Month 14)

ML-powered reconciliation implements a Xero JAX-inspired four-layer intelligence architecture: Rule layer (user-defined bank rules from Phase 2), Match layer (transaction-to-document matching), Memory layer (learning from the user's historical reconciliation patterns), and Prediction layer (suggestions based on anonymized aggregate behavior) ^43^ ^229^ ^44^ ^152^. A per-organization Random Forest model is trained on 12 months of historical reconciliation data. The feature vector includes amount, day of week, hour, merchant name, description keywords, and historical category distribution ^190^. Auto-reconcile targets 80%+ of bank lines in real-time, with confidence scoring ensuring only high-confidence matches auto-process. Suggested match accuracy targets 97%+ ^44^. Continuous learning retrains models periodically with new data, and confidence calibration adjusts probability outputs per organization.

### 9.4.6 White-Label and Industry Modules (Months 14–15)

White-label capabilities enable rebrandable deployment for banks, fintechs, and vertical SaaS companies. Features include custom branding (logo, colors, domain), embeddable chat widget and report viewer components, multi-tenant data isolation per deployment, a partner portal for managing multiple white-label deployments, usage-based billing for partners, custom onboarding flows, per-region regulatory compliance, and SSO integration. Target partners include challenger banks seeking built-in bookkeeping, vertical SaaS platforms (property management, hospitality, retail), fintech lending and payments platforms, and accounting practices wanting branded client portals.

Industry-specific modules provide specialized functionality for four verticals. The Construction Industry Scheme (CIS) module handles contractor registration, CIS deductions on subcontractor payments (20% for registered, 30% for unregistered), monthly CIS300 returns to HMRC, and CIS deduction statements to subcontractors ^54^. The Property/Landlord module supports property portfolio tracking with per-property P&L, rent roll management, tenant deposit handling, service charge apportionment, and mortgage interest tracking. The SaaS/Subscription Business module provides MRR/ARR tracking, churn analysis, customer cohort reporting, revenue recognition per IFRS 15 and ASC 606, and burn rate and runway calculation ^230^ ^231^. The Practice Management module (for accountants) offers client management with multiple entities per client, bulk operations, practice-level reporting, time tracking and WIP, client billing, and AML compliance checks.

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

HMRC MTD VAT progresses through all four phases. The MVP establishes digital record keeping and nine-box return calculation with preview-only display — sufficient for a business to use the system for bookkeeping while submitting via existing MTD software ^22^ ^23^. Phase 2 enables full API submission to HMRC with OAuth2 authentication and fraud prevention headers, making the system a complete MTD-compliant solution ^49^. Phase 3 extends to multi-scheme support (cash accounting, accrual, flat rate scheme). Phase 4 adds group VAT and partial exemption handling for larger businesses.

RTI payroll arrives in Phase 3 with FPS and EPS submission capabilities, PAYE and NICs calculation, and pension auto-enrolment compliance. This aligns with the payroll module's delivery in Month 8. Companies House iXBRL (inline eXtensible Business Reporting Language) filing is introduced as a preview in Phase 3 and as full submission capability in Phase 4, ahead of the mandatory digital filing requirement ^232^.

### 9.5.2 International Expansion

International tax support begins in Phase 3 with three jurisdictions: EU VAT OSS (One-Stop Shop) registration and intra-community supply handling, US Sales Tax with economic nexus tracking and destination-based sourcing, and Australia GST with BAS (Business Activity Statement) reporting ^150^ ^117^. Phase 4 extends to full multi-state filing in the US, local VAT filings per EU country, and full ATO (Australian Taxation Office) integration. Canada GST/HST with GST34 calculation and CRA (Canada Revenue Agency) integration also lands in Phase 4.

### 9.5.3 Critical External Deadlines

Three external deadlines impose hard constraints on the delivery timeline. The EU AI Act's full high-risk system obligations take effect on August 2, 2026, with penalties up to EUR 35 million or 7% of global turnover. The system's Phase 2 delivery (Month 5) coincides with this window, and the built-in EU AI Act compliance — decision logging, human oversight, transparency, and accuracy certification — becomes a competitive differentiator against established players who must retrofit their architectures ^51^. IFRS 18 (Presentation and Disclosure in Financial Statements) becomes effective January 2027, mandating the five-category P&L structure (Operating, Investing, Financing, Income Taxes, Discontinued Operations) and Management Performance Measure disclosures. Phase 3's advanced reporting module (Month 8–9) delivers native IFRS 18 support, positioning the system as ready before the mandatory effective date. UK Companies House digital filing via iXBRL becomes mandatory in April 2028; Phase 4's iXBRL filing capability (Month 10–11) ensures readiness well ahead of this deadline.

**Table 9-6** maps the compliance progression across all phases.

| Regulation / Deadline | MVP | Phase 2 | Phase 3 | Phase 4 |
|:---|:---|:---|:---|:---|
| HMRC MTD VAT | Digital records, 9-box preview ^22^| Full API submission ^49^| Multi-scheme (cash/accrual/flat rate) | Group VAT, partial exemption |
| HMRC RTI Payroll | — | — | FPS + EPS submission ^50^| Full PAYE, auto-enrolment |
| Companies House iXBRL | — | — | iXBRL preview | Full filing (mandatory Apr 2028) ^232^|
| IFRS 18 (Jan 2027) | — | — | Five-category P&L, MPM disclosures ^51^| Full reporting suite |
| EU VAT OSS | — | — | Registration, intra-community ^150^| Local filings per country |
| US Sales Tax | — | — | Economic nexus, destination sourcing ^117^| Multi-state filing |
| Australia GST | — | — | BAS reporting | Full ATO integration |
| EU AI Act (Aug 2026) | — | High-risk system compliance ^22^| Post-market monitoring | Full conformity assessment |

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
| Payroll | HMRC PAYE API credentials | High | Parallel-run beta for 3 months before GA ^55^|
| Custom reports | Report engine (MVP) | Low | Extends existing pipeline |
| **Phase 4** | | | |
| Multi-entity | GL engine (entity isolation) | Medium | Per-tenant Formance ledgers from MVP |
| Project tracking | Invoicing, time tracking | Low | Builds on existing modules |
| API platform | All existing API endpoints | Low | Formalizes and extends current interfaces |
| Marketplace | API platform, OAuth2 | Low | Depends on API platform release |
| ML reconciliation | Bank feeds + 12 months data | Medium | Bank feeds accumulate data from Month 3 |
| White-label | Multi-tenant architecture | Medium | Schema isolation built incrementally |

**Table 9-8: Technical dependencies and blocker risk by phase — critical path identification and mitigations.**



---



## 10. Risk Assessment and Mitigation

A headless LLM-native accounting platform confronts a distinctive risk profile: it must defend against conventional software failures (data loss, API instability, scaling bottlenecks) alongside novel risks specific to LLM-driven financial processing (hallucinated transactions, prompt injection, model cost escalation). This chapter inventories risks across four categories, identifies ten coverage gaps in the current design, and assesses the architectural consistency of the overall solution.

The risk register draws on empirical data where available—academic benchmarks for LLM double-entry accuracy, vendor throughput claims, and LangGraph production metrics—while candidly flagging estimates that rest on single-source figures. Where quantitative data is absent, the assessment relies on likelihood × impact matrices and maps each risk to a concrete mitigation already embedded in the roadmap.

### 10.1 Risk Register

#### 10.1.1 Technical Risks

The most significant technical risk is LLM hallucination in transaction generation. Research by Weber et al. (2025) found that multiple LLM models achieved only 8.33% accuracy when generating raw double-entry bookkeeping without guidance, with 40% of cases producing missing transactions and 23.33% generating balance errors ^2^. This figure was measured against Beancount DSL rather than Numscript, and it did not include the template-based generation and deterministic validation layers that the present architecture employs. The 50+ template library in dim03 constrains the LLM to variable substitution within pre-validated Numscript structures—an approach that raises valid-output rates above 95% when combined with deterministic validation. The six-stage pipeline (parse → template select → populate → validate → confirm → post) includes confirmation gates for all postings, full audit trail logging, and one-command undo via reversing entries ^3^. The residual risk—an unvalidated posting slipping through—is rated medium likelihood with high impact, further mitigated by the immutable append-only ledger that prevents deletion and preserves complete correction history.

Formance Ledger integration introduces a second risk. The documented throughput of approximately 1,000 transactions per second per ledger on commodity PostgreSQL hardware originates from vendor documentation and has not been independently load-tested with accounting workloads ^2^. PostgreSQL benchmarking suggests a write ceiling of ~2,000 requests per second on strong hardware, placing the claim in a plausible range but leaving a validation gap. Mitigation is threefold: comprehensive integration testing during MVP, a fallback to a custom PostgreSQL ledger if Formance proves insufficient, and horizontal ledger sharding for multi-entity deployments. The supervisor pattern introduces cost risk: LangGraph data indicates supervisor routing costs ~$0.061 per task versus $0.022 for single-agent—a 3× increase delivering an 18-point accuracy lift (89% versus 71% end-to-end success) ^222^. For accounting transactions where an error could cost hundreds of pounds, this trade-off is justified but requires monitoring at scale.

Document extraction accuracy varies by methodology: LlamaExtractor achieved 94% in one comparative study, while hybrid LLM-plus-OCR pipelines report 97–98.5% document-level accuracy ^233^. The 97% claim for Xero JAX reconciliation is a vendor figure that practitioners note holds only for businesses with consistent patterns ^43^. Mitigation is a human-in-the-loop (HITL) gate with graduated autonomy: extractions below 90% confidence route to human review, and the system learns from corrections through episodic memory (Mem0) ^120^.

| Risk ID | Risk Description | Likelihood | Impact | Mitigation Strategy | Evidence Basis |
|:---|:---|:---|:---|:---|:---|
| T-01 | LLM hallucination generates incorrect double-entry transactions | Medium | High | Template-based Numscript generation (50+ templates); 6-stage deterministic validation; confirmation gates; immutable ledger with reversing-entry undo | Weber et al. (2025): 8.33% raw accuracy ^2^; template mitigation from dim03 |
| T-02 | Formance Ledger throughput insufficient at scale | Low | High | Integration testing; fallback to custom PostgreSQL ledger; horizontal sharding | Vendor claim: ~1,000 tx/s ^2^; independent PostgreSQL ceiling ~2,000 rps |
| T-03 | Supervisor pattern cost escalation (3× single-agent) | Medium | Medium | Phased agent rollout (4 core specialists for MVP); cost-per-task monitoring; single-agent fallback for low-value queries | LangGraph: $0.061 vs $0.022 per task ^222^|
| T-04 | Document extraction accuracy below production threshold | Medium | Medium | HITL review for <90% confidence; hybrid LLM+OCR pipeline; per-organization model learning | 94–97% range across studies ^233^; vendor claims require validation |
| T-05 | LLM context window exceeded for large reports | Medium | Medium | Streaming report generation; pagination; summary-first approach; chunked bulk processing | GPT-4o 128K context ^222^; pattern from dim01 |

The technical risk profile is dominated by LLM reliability concerns. All five risks have mitigations either built into the architecture (validation pipeline, confirmation gates, immutable ledger) or scheduled for MVP (integration testing, HITL thresholds). Residual risk after mitigation is low for T-02 and T-03, and medium-low for T-01, where template constraints plus deterministic validation provide defense in depth.

#### 10.1.2 Compliance Risks

The EU AI Act presents the most significant compliance exposure. High-risk system rules take full effect in August 2026, with penalties reaching 7% of global annual revenue ^23^. The system's AI-driven categorization, automated reconciliation, and document extraction all qualify as high-risk financial AI applications. Three research dimensions independently converge on the approach: agent decision provenance logging per Article 12, 6-month minimum audit retention, human oversight per Article 14, and model transparency through human-readable Numscript outputs ^22^. Residual risk is regulatory interpretation uncertainty—whether the European Commission will issue supplementary guidance imposing additional requirements. Mitigation centers on a modular compliance architecture that absorbs new requirements without structural change, plus formal legal review in Q2 2026.

IFRS 18, effective January 2027, replaces IAS 1 with a five-category P&L structure (Operating, Investing, Financing, Income Tax, Discontinued Operations) and introduces Management Performance Measure disclosures ^51^. The current COA uses traditional categories (4000–4999 revenue, 5000–6999 expenses) that do not map one-to-one to IFRS 18. Mitigation is a metadata-driven presentation layer: the COA remains unchanged, but report SKILLs map accounts to IFRS 18 categories at generation time through configurable metadata flags, enabling simultaneous IFRS, UK GAAP, and US GAAP compliance without parallel books.

HMRC MTD for VAT represents a third risk. While VAT calculation and nine-box preview are MVP features, direct API submission depends on OAuth 2.0 integration and HMRC error handling that are acknowledged but not fully specified ^49^. Mitigation is an abstraction layer around the HMRC API, preview-only operation in MVP, and full submission in Phase 2 after deep integration testing.

| Risk ID | Risk Description | Likelihood | Impact | Mitigation Strategy | Timeline |
|:---|:---|:---|:---|:---|:---|
| C-01 | EU AI Act interpretation imposes unanticipated requirements | Medium | High | Modular compliance architecture; legal review Q2 2026; Art. 12 logging, Art. 13 transparency, Art. 14 HITL built in from MVP | Enforcement: August 2026 ^23^|
| C-02 | IFRS 18 category mapping requires structural COA changes | Medium | Medium | Metadata-driven presentation layer; IFRS 18 report SKILLs with account-to-category mapping | Effective: January 2027 ^51^|
| C-03 | HMRC MTD API changes break VAT submission pipeline | Medium | High | Adapter pattern abstraction layer; preview-only in MVP; monitored integration in Phase 2; manual fallback | Ongoing; MTD VAT mandatory ^22^|
| C-04 | HMRC RTI payroll submission errors trigger penalties | Low | Very High | Testing against HMRC calculators; beta with volunteers; phased rollout (salary-only first) | Phase 3 (Month 8) ^50^ ^55^|

The compliance risk profile is shaped by external regulatory timelines. The EU AI Act and IFRS 18 deadlines align favorably with the roadmap: compliance features are delivered in Phase 2 (Months 3–5) and IFRS 18 SKILLs in Phase 3 (Months 6–9), providing 6–12 months of buffer. HMRC risks are operational—the three-layer tax architecture (Rule Store, Execution Engine, Override Workflow) is sound, but the API integration layer requires deeper specification.

#### 10.1.3 Business Risks

User adoption risk arises from the headless, chat-only model that replaces familiar accounting interfaces with natural language. Small business owners are accustomed to visual dashboards and spreadsheet-like grids. Mitigation is graduated autonomy: the system begins with 100% human approval for AI-generated transactions, transitions to sampled review once accuracy is demonstrated, and reaches exception-only approval for routine transactions ^120^. The skill registry exposes familiar concepts (invoices, reconciliations, VAT returns) through natural language, reducing conceptual migration cost. The 8-week MVP targets UK freelancers already comfortable with technology, validating product-market fit before broader rollout.

Resource constraint risk reflects the tension between a 15-month roadmap and a team peaking at 5–7 engineers. The MVP requires 48 engineering days (2–3 engineers over 8 weeks at 75% velocity), with Phases 2–4 adding 65, 80, and 105 days respectively for a cumulative 298 days ^3^. Mitigation is strict phasing with go/no-go gates, prioritizing revenue-generating and compliance-critical features. The MVP is designed as a standalone product that can generate paid users before Phase 2 begins.

#### 10.1.4 External Risks

External risks center on third-party service dependencies. Open Banking aggregator downtime is mitigated by a four-provider failover chain: TrueLayer (UK/EU primary, PSD2-regulated), Plaid (12,000+ institutions), Salt Edge (60+ countries), and Yodlee (17,000+ institutions) ^48^ ^179^ ^180^ ^31^. If TrueLayer is unavailable, the system promotes Plaid to primary; Salt Edge and Yodlee provide tertiary coverage. A manual CSV/OFX import fallback ensures bank data entry even during simultaneous aggregator outages—a low-probability scenario with elevated impact at month-end and quarter-end.

Exchange rate API failure presents lower risk. Daily rates from the European Central Bank are cached with 30-day retention; manual override supports backdated transactions; secondary providers (XE.com, Open Exchange Rates) provide fallback. Impact is limited because target-market SMEs operate predominantly in GBP; multi-currency support is a Phase 3 feature where the exchange rate infrastructure will be fully hardened ^45^.

### 10.2 Coverage Gaps and Resolutions

Cross-dimensional analysis of 18 research dimensions identified ten topics with insufficient coverage for production readiness. These are not architectural flaws but areas requiring additional design work.

The two highest-severity gaps are production load testing and disaster recovery. No dimension provides independent load test data for Formance Ledger; vendor claims of ~1,000 tx/s remain unvalidated ^2^. Disaster recovery is mentioned only briefly with no Recovery Time Objective (RTO), Recovery Point Objective (RPO), or multi-region strategy. Both gaps directly threaten production readiness.

Medium-severity gaps cluster around integration depth and operational tooling. HMRC MTD API integration lacks detailed OAuth 2.0 specifications and error handling ^49^. LLM cost modeling has no Total Cost of Ownership (TCO) model at scale—current estimates cite $0.061 per supervisor-routed task ^222^but lack projections for 100× or 1,000× growth. Payroll has Numscript templates but no deep design for PAYE/NI calculations or RTI submission workflows ^50^ ^55^. Migration tooling from Xero/QBO is limited to CSV adapters with no API-based path. Mobile architecture, operations tooling (admin dashboard, monitoring), multi-tenant isolation at scale, and pricing strategy round out the ten gaps.

| Gap ID | Coverage Gap | Severity | Impact if Unaddressed | Resolution Phase | Resolution Approach |
|:---|:---|:---|:---|:---|:---|
| G-01 | Production load testing & scalability validation | High | Cannot validate 1,000 tx/s claim; production bottleneck risk | Phase 2 (M3) | Independent throughput test with realistic workloads; PostgreSQL query analysis; sharding prototype |
| G-02 | Disaster recovery & business continuity | High | No RTO/RPO; single point of failure; blocks enterprise adoption | Phase 2 (M4) | RTO <4 hours, RPO <1 hour; automated daily backups; multi-region k8s spec; annual DR drill |
| G-03 | HMRC MTD API deep integration | Medium-High | VAT submission failure; UK market entry blocked | Phase 2 (M5) | OAuth 2.0 flow design; endpoint mapping; error taxonomy; retry with backoff; sandbox testing |
| G-04 | LLM cost modeling at scale | Medium-High | Business model unviable if LLM costs exceed revenue per user | Phase 2 (M3) | Token usage instrumentation per workflow; cost model at 10×/100×/1,000×; provider cost comparison |
| G-05 | Payroll module deep design | Medium | Cannot offer UK payroll; competitive disadvantage | Phase 3 (M8) | PAYE/NI engine spec; RTI FPS/EPS workflow; HMRC PAYE API integration; beta with volunteers |
| G-06 | Migration tooling from Xero/QBO | Medium | Manual migration friction slows customer acquisition | Phase 3 (M7) | Xero API OAuth export pipeline; data validation engine; COA auto-mapping; migration dashboard |
| G-07 | Mobile application architecture | Medium | No field access for receipt capture, approvals | Phase 3 (M9) | PWA or React Native; offline receipt capture; push notifications |
| G-08 | Operations tooling & monitoring | Medium | Cannot operate multi-tenant service reliably | Phase 3 (M6) | Multi-tenant admin dashboard; Prometheus/Grafana; PagerDuty alerting; support workflow |
| G-09 | Multi-tenant isolation at scale | Medium | Noisy neighbor risk; data leakage between tenants | Phase 4 (M10) | Database-per-tenant validation at 100+ scale; resource quotas; tenant provisioning automation |
| G-10 | Competitive pricing strategy | Low-Medium | Risk of pricing below cost or above market willingness-to-pay | Phase 4 (M12) | Cost-plus analysis with LLM overhead; competitive benchmarking vs Xero/QBO; freemium design |

Resolution follows severity rather than roadmap chronology. The two highest-severity gaps (G-01, G-02) are pulled into Phase 2 because they block production readiness. G-03 (HMRC integration) is also Phase 2 because it is on the critical path for UK market validation. Medium gaps (G-04 through G-08) distribute across Phases 2 and 3 based on dependencies: LLM cost modeling (G-04) begins once MVP users generate real token traffic, while migration tooling (G-06) requires a stable data model. Lower-severity gaps (G-09, G-10) defer to Phase 4, when operational data informs tenant architecture and pricing decisions.

### 10.3 Architectural Consistency Assessment

An architectural consistency assessment across 12 subsystem categories scores each on a 0–100 scale based on cross-dimensional agreement, evidence strength, and absence of contradictions. The overall system scores 87/100.

| Category | Score | Key Strength | Primary Weakness |
|:---|:---|:---|:---|
| Backend technology | 95/100 | Formance + PostgreSQL agreed across 4 dimensions; sum-to-zero, Numscript, immutability native ^2^ ^3^| NATS choice has only 2 confirming dimensions; Kafka viable at scale |
| Data model (COA/GL) | 92/100 | 4-digit gap-friendly scheme; metadata-driven multi-standard support without parallel books ^15^| IFRS 18 mapping requires presentation-layer implementation |
| Agent architecture | 90/100 | Supervisor pattern with LangGraph empirical data (89% vs 71% success) ^222^| 3× cost; no accounting-specific cost benchmark |
| Multi-currency (IAS 21) | 90/100 | 3-currency architecture with full SQL schemas; spot/closing/average rates; CTA in OCI ^45^| No independent FX calculation validation against IFRS test cases |
| Transaction processing | 88/100 | 50+ Numscript templates; 6-stage pipeline catches 91.67% of LLM errors | 8.33% figure not replicated on Numscript ^2^|
| Reporting | 88/100 | 33+ report SKILLs with deterministic JSON schemas; IFRS 18 support designed ^51^| Custom report builder in Phase 3; XBRL output untested |
| Tax engine | 85/100 | 3-layer architecture (Rule Store, Execution Engine, Override) across 4 dimensions ^150^| HMRC API integration details missing |
| Security / compliance | 82/100 | Hash-chained ledger, WORM storage; EU AI Act and GDPR addressed ^23^| DR missing; no RTO/RPO; no penetration test results |
| Bank feeds | 80/100 | 4-aggregator failover to 17,000+ institutions; PSD2 SCA ^48^| Actual aggregator integration untested |
| Document processing | 78/100 | Hybrid LLM+OCR pipeline agreed; local vs cloud resolution path ^233^| Local vs cloud tension unresolved for sensitive docs |
| DevOps / deployment | 75/100 | Docker Compose + k8s specs; Kong gateway, NATS, Redis all specified ^222^| No multi-region; no DR plan; no CI/CD spec |
| Cost / business model | 55/100 | Unit cost data ($0.061/task) enables economics modeling ^222^| No pricing model; no cost-plus analysis; no freemium design |

The score distribution reveals a clear pattern: highest scores are in backend technology, data model, and agent architecture—areas where multiple independent dimensions converge with strong evidence. Lowest scores are in cost/business model (55) and DevOps/deployment (75), reflecting the research's technical focus over commercial and operational concerns. This is an intentional artifact of scope rather than an architectural deficiency, but it signals that business modeling and operational readiness require dedicated attention.

The 87-point overall score measures internal consistency—how well components agree with each other—not market success or implementation ease. A system can be architecturally consistent and still fail if its business model is unviable. The coverage gaps and the low cost/business model score together highlight the highest-priority remediation: closing the loop between technical design and commercial viability through LLM cost modeling, competitive pricing analysis, and operational readiness planning before the MVP exits validation.



---

