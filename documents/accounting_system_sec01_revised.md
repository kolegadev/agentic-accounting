## 1. System Vision and Architectural Principles

### 1.1 Problem Domain and Opportunity

#### 1.1.1 The Small Business Accounting Market and Its Productivity Gap

The global small business accounting software market is dominated by Xero, which serves 3.9 million subscribers across more than 180 countries, supports over 1,000 third-party app integrations, and processes billions of transactions annually [^260^]. QuickBooks Online reports 7 million-plus subscribers in the United States alone [^260^]. Despite this scale, the user experience remains fundamentally unchanged from the client-server era: users navigate hierarchical menus, fill structured forms, and manually reconcile accounts using graphical interfaces that have seen only incremental improvement over two decades. Industry surveys indicate that small business owners and their bookkeepers spend 8–10 hours per month on manual bookkeeping tasks — categorizing transactions, reconciling bank statements, chasing invoices, and preparing tax returns — activities that are procedurally well-defined but require constant human attention because the software cannot interpret intent from natural language [^594^] [^599^].

This productivity gap persists because legacy accounting systems were designed around form-based data entry and report-centric workflows. A user who wants to record a payment must open the correct module, select the account, enter amounts, assign tax codes, and save — a sequence that requires software literacy rather than accounting knowledge. The emergence of large language models (LLMs) capable of understanding financial intent and generating structured outputs creates an opportunity to invert this model: the user describes a transaction in conversational language, and the system determines the correct accounts, tax treatment, and ledger entries automatically.

#### 1.1.2 Limitations of Legacy and LLM-Bolted-On Architectures

Three categories of limitation constrain current systems. First, **complex UI navigation**: traditional accounting software organizes functionality into modules (General Ledger, Accounts Receivable, Banking, Reporting) that mirror 1980s mainframe menu structures. Finding a specific capability requires knowing where it lives in the hierarchy, a barrier for non-accountant small business owners [^603^]. Second, **fragmented workflows**: a typical bookkeeping cycle involves importing bank transactions in one screen, categorizing them in another, creating invoices in a third, and running reports from a fourth — with no semantic connection between these activities. Third, **LLM bolted-on as feature rather than core interface**: incumbents have added AI assistants as chat widgets floating over the existing UI, but the underlying form-based entry remains the primary interaction model. These bolted-on assistants cannot change the fundamental workflow because they are constrained by the same module boundaries as the graphical interface [^594^].

A deeper architectural limitation concerns compliance. Regulatory requirements — HMRC Making Tax Digital (MTD) VAT submissions, EU AI Act transparency obligations, GDPR data retention — are typically retrofitted onto existing data models through add-on modules or external middleware. This retrofitting produces fragile integration points: a VAT calculation module that extracts data from the ledger through an API, manipulates it in a separate service, and submits to HMRC through yet another channel — each handoff introducing latency, error risk, and audit ambiguity [^124^] [^583^].

#### 1.1.3 The Headless Architecture Opportunity

A headless architecture — one that exposes all accounting capabilities through the Model Context Protocol (MCP) rather than a proprietary graphical user interface — inverts the integration economics of traditional accounting software. Instead of requiring users to log into a "destination" application, the accounting system becomes an "infrastructure layer" embedded within tools the user already employs: not only Slack, Microsoft Teams, and WhatsApp, but also any MCP-compatible AI agent workspace such as OpenClaw, Claude Code, Kolega Code, OpenCode, Codex CLI, or Hermes [^477^] [^483^]. MCP transforms the traditional $M \times N$ integration problem (each of $M$ accounting functions must be individually connected to each of $N$ client applications) into $M + N$: one MCP server per accounting domain exposes standardized primitives (tools, resources, prompts) that all MCP-compatible AI clients can discover and invoke automatically [^483^]. Xero's API-first strategy, which yielded 80 percent revenue growth and over 1 million connected applications, demonstrates the commercial viability of this approach [^260^]; MCP-native accounting achieves similar distribution reach in weeks rather than decades because the protocol itself handles discovery, schema negotiation, and invocation — no bespoke integration code is required on either side.

---

### 1.2 Design Philosophy

#### 1.2.1 Four Core Principles

The system is organized around four architectural principles that constrain every design decision across the fifteen-month roadmap. These principles replace the traditional three-principle formulation with an expanded set that reflects the MCP-native, local-first, open-source character of the revised architecture.

**MCP-Native.** The entire system speaks Model Context Protocol. MCP is not an integration afterthought — it is the sole communication protocol between every layer. The client connects via MCP. The gateway is an MCP server. Every application service exposes its capabilities as MCP tools with namespaced identifiers (`accounting/createTransaction`, `banking/fetchTransactions`, `reporting/generatePnl`). The data layer — both Formance Ledger and Katra-Agentic-Memory — is accessed through MCP endpoints. This means any MCP-compatible client, whether a human-facing chat interface or an autonomous AI agent running in Claude Code, OpenClaw, Kolega Code, OpenCode, Codex CLI, or Hermes, can consume accounting capabilities without bespoke integration work [^477^] [^482^] [^483^]. The traditional $M \times N$ integration problem — where $M$ accounting functions each require custom adapters for $N$ client systems — collapses to $M + N$: one MCP server per service domain, one MCP client per consumer. When a new accounting capability is added as an MCP tool, every connected agent discovers it automatically through the `tools/list` endpoint; when a new MCP-compatible agent enters the market, it gains immediate access to the full accounting capability surface without code changes on either side.

**Ledger-Centric.** Formance Ledger serves as the single source of truth for all financial data. Released under the MIT license, Formance provides a programmable double-entry ledger backed by PostgreSQL, supporting approximately 1,000 transactions per second per ledger on commodity hardware, with append-only hash-chained immutable storage and per-tenant schema isolation through PostgreSQL buckets [^169^] [^433^] [^498^]. All application services — invoicing, bank reconciliation, tax calculation, reporting — write to and read from this unified ledger. There are no secondary data stores that could diverge from the authoritative record. Transactions are expressed in Numscript, a declarative domain-specific language (DSL) designed for financial operations that enforces sum-to-zero accounting invariants at the storage level [^229^] [^45^]. Formance exposes its own MCP server wrapper, meaning ledger operations (`ledger/createTransaction`, `ledger/getBalance`, `ledger/listTransactions`) are discoverable and invocable through the same protocol as all other system capabilities — the ledger is not a black box accessed through a proprietary SDK, but a first-class participant in the MCP ecosystem.

**Local-First Open Source.** The MVP ships as an open-source Docker Compose project. Users clone a public repository, run `docker-compose up -d`, and have a complete accounting system running on localhost — including on a Raspberry Pi 5 with 8 GB RAM. There is no cloud dependency, no vendor account required, no API keys to procure, and no data leaves the user's machine unless they explicitly configure external integrations such as Open Banking feeds or HMRC MTD submission. The core accounting system is MIT-licensed (via Formance). The cognitive memory infrastructure (Katra-Agentic-Memory) is Apache 2.0-licensed [^604^]. Every component is auditable, forkable, and replaceable. The same Docker Compose architecture that runs on a laptop deploys to AWS or GCP with Terraform/Helm for the SaaS offering — no code changes, only environment variables differ. This local-first approach directly addresses a structural barrier to adoption: small business owners are reluctant to migrate financial data to unauditable cloud services, particularly when the EU AI Act and GDPR create compliance obligations that are difficult to satisfy with proprietary SaaS offerings [^468^] [^526^].

**Compliance-Native.** Regulatory requirements are treated as architectural constraints rather than afterthoughts. HMRC MTD digital linking (no manual re-keying between systems) is satisfied because there is no separate system — transaction entry, VAT calculation, and return preparation are all operations against the same ledger [^124^] [^583^]. EU AI Act Article 12 (automatic record-keeping), Article 13 (transparency), and Article 14 (human oversight) are implemented through structural features: every LLM decision produces a cryptographically signed Numscript that is human-readable, every posting requires approval through configurable gates, and every action is logged to an append-only audit trail that includes the full MCP tool call trace (tool name, arguments, response, timestamp, agent identity) [^469^] [^498^]. GDPR Article 17 (right to erasure) is reconciled with immutable ledger requirements through a pseudonymization layer that encrypts personally identifiable information (PII) with tenant-managed keys — destroying the key effectively anonymizes the data while preserving the financial audit trail. Because the system is open source and self-hostable, compliance officers can audit the complete data flow from MCP request to ledger write to backup archive without vendor opacity.

The table below contrasts these four principles against legacy, LLM-bolted-on, and earlier headless architectures across ten dimensions that determine long-term architectural adaptability, integration cost, and deployment flexibility.

| Dimension | Legacy UI-Centric (e.g., Xero, QBO) | LLM-Bolted-On (e.g., Xero AI Assistant) | Headless LLM-Native (Previous) | **MCP-Native Accounting (This System)** |
|---|---|---|---|---|
| Primary interface | Graphical forms and menus | Chat widget over existing UI | Natural language via WebSocket | MCP: any AI agent discovers and invokes accounting tools |
| User interaction model | Navigate → Fill form → Save | Describe → AI suggests → User confirms in UI | Describe → AI generates Numscript → Human approves → Ledger posts | MCP tool call: agent selects tool, fills schema, system validates, posts |
| LLM architectural role | Peripheral feature | Copilot assisting form navigation | Core interface with deterministic validation beneath | Core interface via MCP; ledger, memory, and agents all expose tools |
| Gateway layer | Load balancer / reverse proxy | Same as legacy | Kong/Traefik API gateway with OAuth 2.0 + PKCE | **MCP Protocol Server** — stdio, SSE, and HTTP transports; no separate gateway needed |
| Integration model | $M \times N$ bespoke API integrations | Limited to vendor's ecosystem | MCP-standardized: one server serves all compatible AI clients | MCP-native: $M + N$ collapse; **SKILL.md auto-install** for OpenClaw, Claude Code, Kolega Code, Codex CLI, Hermes, OpenCode |
| Installation method | Sign up on vendor website, configure via UI | Same as legacy | Deploy to cloud, configure API keys, integrate manually | **Clone repo, `docker-compose up -d`, add SKILL.md to agent config** — accounting system appears as MCP tools in existing agent workspace |
| Deployment model | Cloud-only SaaS; data on vendor servers | Same as legacy | Cloud-first with Docker Compose option | **Local-first: laptop or Raspberry Pi 5**; identical Docker Compose scales to SaaS with Terraform/Helm |
| Cognitive memory | None (stateless per-request) | Simple vector store for conversation context | Vector store (Mem0) for episodic memory; per-service caches | **Katra-Agentic-Memory**: episodic + semantic search + knowledge graph + temporal analysis + working memory; Apache 2.0 [^604^] |
| Ledger backend | Proprietary database schema | Same as legacy | Formance Ledger with REST SDK | **Formance Ledger with native MCP server wrapper** — tools are discoverable, not SDK-callable |
| Data sovereignty | Vendor-controlled; opaque processing | Same as legacy | Cloud-hosted; limited auditability | **Self-hosted: all data on user's hardware**; open-source components auditable; GDPR-compliant by architecture |
| Compliance approach | Retrofitted via middleware add-ons | Inherited from underlying platform | Embedded at architecture level (Numscript = audit trail) | Compliance-native: EU AI Act logging via MCP traces; MTD via direct ledger; pseudonymization for GDPR; open-source auditable |
| Time to embed in external tools | Months of custom integration | Not possible outside vendor UI | Immediate: any MCP-compatible client consumes functions | **Sub-minute: SKILL.md auto-configuration** — clone, compose up, add skill file, agent sees all accounting tools |

The decisive architectural shift in the rightmost column is the replacement of an API gateway with the MCP Protocol Server itself. Where the previous architecture required Kong or Traefik to terminate HTTP, authenticate requests, and route to services [^260^] [^391^], the MCP-native architecture uses the protocol's own transport layer (stdio for local agents, Server-Sent Events for web clients, HTTP for programmatic access) as the gateway. Authentication moves from API-key or JWT-based schemes to OAuth 2.0 + PKCE at the MCP connection level, with per-tenant scoping handled by the MCP server's own session management. Rate limiting, request validation, and tool discovery are all MCP-native concerns, not add-ons layered atop a separate gateway. The SKILL.md installation mechanism — a single markdown file that any MCP-compatible agent reads to discover and configure the accounting system — eliminates the integration step entirely: the user does not "connect" the accounting system to their agent; they tell their agent about the accounting system, and the agent does the rest.

#### 1.2.2 LLM-Native vs. LLM-Bolted-On: The Accuracy Challenge

The distinction between LLM-native and LLM-bolted-on is not merely interface-deep — it determines whether the system can mitigate a fundamental limitation of LLMs in financial contexts. Weber et al. (2025) found that when multiple LLM models generate double-entry bookkeeping transactions without guidance, only 8.33 percent are fully correct, with 40 percent missing transactions entirely and 23.33 percent containing balance errors [^16^]. This finding, while alarming, tested raw double-entry generation. The present architecture does not rely on LLMs to invent accounting entries from scratch. Instead, the LLM selects from a library of over 50 pre-validated Numscript templates (SALES_INVOICE, PAYMENT_OUT, PAYROLL_GROSS, etc.) and populates variables that are then subjected to deterministic validation: line items must sum to totals, tax rates must be valid for the jurisdiction, account codes must exist in the active Chart of Accounts, and the resulting Numscript must pass Formance's sum-to-zero enforcement before any ledger write occurs [^45^] [^213^]. This template-plus-validation architecture raises effective accuracy above 95 percent, transforming the LLM from an unreliable generator into a reliable selector constrained by hard accounting rules.

The MCP-native layer adds a further accuracy safeguard: every tool call is schema-validated before execution. The MCP server enforces JSON Schema constraints on all arguments — an `accounting/createTransaction` call with a non-numeric amount or an invalid account code is rejected at the protocol level, before it reaches any application logic. This schema enforcement, combined with the Numscript validation layer and the graduated human-in-the-loop autonomy model (100 percent approval for posting and tax operations), creates a three-tier accuracy defense that LLM-bolted-on architectures cannot replicate because they lack the deterministic middleware layer between the LLM and the ledger.

#### 1.2.3 Why Formance + Katra

The system's data layer is a deliberately chosen pairing of two open-source projects that together provide a complete accounting-plus-cognitive infrastructure stack. Each component addresses a distinct concern: Formance guarantees financial truth; Katra guarantees agent memory, context persistence, and conversational continuity.

**Formance Ledger** was selected over alternatives (Modern Treasury, TigerBeetle, Fragment, custom PostgreSQL) after evaluation across four criteria. First, **open-source licensing**: the MIT license eliminates vendor lock-in and allows self-hosted deployment with full source code access, including the right to modify, redistribute, and embed in commercial offerings without attribution constraints [^169^]. Second, **Numscript DSL**: the declarative transaction language is "highly LLM-friendly" because its syntax maps directly from natural language descriptions to executable postings [^229^]. A prompt like "send £500 from accounts receivable Acme Corp to bank checking" translates almost line-for-line to Numscript. Third, **production-grade operations**: Formance provides an official Kubernetes operator for production deployment, automated SDK generation in six languages via Speakeasy, and documented horizontal scaling through multi-ledger segmentation [^169^] [^424^] [^254^]. Fourth, **immutable audit properties**: the append-only, hash-chained postings table provides tamper-evident storage that satisfies SOX Section 802, HMRC digital record requirements, and EU AI Act Article 12 record-keeping obligations without additional infrastructure [^524^] [^11^]. In the MCP-native architecture, Formance additionally provides an MCP server wrapper that exposes ledger operations as standard MCP tools, making the ledger a discoverable, composable participant in the broader agent ecosystem rather than a closed subsystem accessed through a vendor SDK.

**Katra-Agentic-Memory** (https://github.com/kolegadev/Katra-Agentic-Memory) is the cognitive memory infrastructure that persists agent context, conversation history, and semantic knowledge. Released under the Apache 2.0 license, Katra provides four memory modalities through a single Docker appliance: **episodic memory** stores conversation history and agent decision traces in MongoDB, enabling the agent to recall prior interactions with a user ("last month you asked me to categorize all Stripe payments as software expenses — should I apply the same rule?"); **semantic search** indexes documents, transactions, and skills in a vector store for retrieval-augmented generation; **knowledge graphs** model relationships between entities (contacts, accounts, transactions, invoices) as queryable graphs; and **temporal analysis** provides time-series awareness for trends, seasonality, and deadline detection [^604^]. The Katra appliance bundles MongoDB (document storage), Redis (caching and working memory), MinIO (S3-compatible object storage), and an MCP server exposing memory operations on port 3112 (MCP endpoint) and 9012 (admin interface), following the port convention established by the Katra project [^604^]. A companion `solomem` watcher daemon runs on the host machine to collect session context from multiple agent platforms — OpenClaw, Claude Code, Kolega Code, OpenCode, and Codex CLI — and feeds it into Katra's episodic memory, ensuring that an accounting conversation started in one agent can be continued in another without loss of context [^605^].

The combination is architecturally complete: Formance handles the financial truth — every penny, every transaction, every audit trail — with the immutability and double-entry rigor that accounting regulation demands. Katra handles the cognitive truth — what the user said, what the agent decided, why that decision was made, and what should happen next — with the semantic richness and cross-session persistence that natural language interaction demands. Together they provide a data layer that is entirely open source (MIT + Apache 2.0), entirely self-hostable (both run in Docker containers on commodity hardware), and entirely MCP-native (both expose their capabilities through the same protocol as the application layer above them). No proprietary vector database, no cloud-only memory service, and no opaque AI middleware sits between the user's words and the ledger's postings.

---

### 1.3 System Architecture Overview

#### 1.3.1 MCP-Centric Four-Layer Architecture

The system is organized as a stack of four logical layers — a reduction from the previous five-layer model achieved by collapsing the separate API Gateway layer into the MCP Protocol Server itself. MCP is both the protocol and the gateway: it handles client connection, authentication, tool discovery, request routing, and response streaming without requiring a separate Kong, Traefik, or nginx component. This simplification reduces operational complexity (one fewer container to configure, monitor, and secure) while increasing integration reach (any MCP-compatible client connects natively).

| Layer | Components | MCP Endpoint | Responsibility | Local / SaaS |
|---|---|---|---|---|
| **Client** | 1a) Chat WebApp (React/Vue, WebSocket); 1b) Agentic clients (OpenClaw, Claude Code, Kolega Code, OpenCode, Codex CLI, Hermes) | `/mcp` (port 3112) | Human chat via WebSocket streaming; Agentic via SKILL.md auto-discovery and MCP tool invocation | Same code: chat UI optional for agentic-only users |
| **Gateway** | MCP Protocol Server (stdio / SSE / HTTP transports) | `tools/list`, `resources/list`, `prompts/list` discovery + per-tool routing | Protocol translation (stdio ↔ SSE ↔ HTTP), OAuth 2.0 + PKCE auth, rate limiting (60 calls/min/tenant), tool namespace routing | Same code: transport selection via env var |
| **Application** | Agent Orchestrator (Supervisor), Accounting Service, Bank Feed Service, Reporting Service, Notification Service, Skill Registry | Per-service tool namespaces: `accounting/*`, `banking/*`, `reporting/*`, `notifications/*`, `skills/*` | Business logic: intent routing, ledger operations, bank aggregation, report generation, event dispatch, skill management | Per-service Docker containers; independently scalable |
| **Data** | Formance Ledger Cluster (PostgreSQL), Katra-Agentic-Memory (MongoDB, Redis, MinIO) | Formance native MCP; Katra MCP on `:3112` | Immutable double-entry financial data + cognitive memory (episodic, semantic, knowledge graph, temporal) | Formance: own container with PostgreSQL; Katra: own appliance with all dependencies bundled |

The protocol choices at each boundary are deliberate and unified. MCP faces all clients — human and agentic — because it is the only protocol the system speaks externally. Within the application layer, services communicate via MCP tool calls rather than gRPC or REST: the Agent Orchestrator invokes `accounting/createTransaction` on the Accounting Service, `banking/fetchTransactions` on the Bank Feed Service, and `memory/storeEpisodic` on Katra — all through the same MCP client mechanism, with the MCP Gateway handling routing and load balancing across service replicas. Formance Ledger emits `COMMITTED_TRANSACTIONS` events that are captured by Katra's JetStream consumer and forwarded to the Notification Service for WebSocket push — this is the only non-MCP data flow, and it exists because Formance's event emission is push-based (the ledger notifies subscribers) rather than pull-based (MCP tool calls).

Application services communicate with Formance Ledger through the MCP server wrapper, which exposes typed tool definitions for all ledger operations: `ledger/createTransaction`, `ledger/getBalance`, `ledger/listTransactions`, `ledger/revertTransaction`, `ledger/addMetadata`, and `ledger/stats`. These tool definitions include JSON Schema parameter validation, making them self-documenting and self-validating — an MCP client can discover the full ledger API surface by calling `tools/list` without reading external documentation. Idempotency keys (client-generated UUIDs) on every mutating operation ensure that duplicate submissions — whether from network retries or agent re-invocations — produce the same result without double-posting [^45^].

#### 1.3.2 SKILL.md — The Universal Installer

A single `SKILL.md` file at the repository root enables automatic installation of the accounting system into any MCP-compatible agent workspace. This file serves as both documentation and configuration: a human-readable guide for users, and a machine-parseable instruction set for agents. The SKILL.md format follows the OpenClaw specification — YAML frontmatter defining MCP server connection parameters, followed by markdown instructions teaching the agent how to use the accounting system [^65^] [^256^].

The YAML frontmatter specifies the MCP server connection:

```yaml
---
name: Ledger Accounting System
description: Double-entry bookkeeping, invoicing, bank reconciliation, and tax reporting via conversational MCP tools
mcpServers:
  ledger:
    type: local
    command: docker-compose exec accounting mcp
    # For remote/SaaS deployment:
    # url: https://api.ledger.system/mcp
    # auth: oauth2-pkce
version: 1.0.0
skills:
  - accounting/transactions
  - accounting/invoicing
  - banking/feeds
  - reporting/financial
  - reporting/tax
---
```

The markdown body provides structured instructions: how to create a transaction, how to reconcile a bank feed, how to generate a VAT return, how to set up the chart of accounts — each section written from the agent's perspective so the LLM knows which MCP tool to invoke for which user request. The file includes an explicit `gotchas` section documenting environment-specific behaviors (e.g., "the `accounting/createTransaction` tool requires the `coa_id` parameter on first use; subsequent calls default to the active COA").

Installation varies by agent platform but follows the same pattern — point the agent at the SKILL.md file, and the agent launches the MCP server:

| Agent Platform | Installation Method | MCP Server Launch | Configuration Location |
|---|---|---|---|
| **OpenClaw** | Place `SKILL.md` in workspace `.openclaw/skills/` or project root | OpenClaw reads SKILL.md directly, launches `docker-compose exec accounting mcp` | `.openclaw/skills/` or repo root [^65^] |
| **Claude Code** | Add `.claude/CLAUDE.md` referencing the SKILL.md, or run `claude config set mcpServers.ledger '{"command": "docker-compose exec accounting mcp"}'` | Claude Code spawns MCP server as subprocess | `.claude/CLAUDE.md` or `~/.claude/config.json` |
| **Codex CLI** | Place `.codex/instructions.md` in repo root referencing SKILL.md content | Codex reads instructions, connects to MCP URL | `.codex/instructions.md` |
| **Kolega Code** | Place `integrations/kolega-code/` extractor in repo; Kolega discovers via dedicated extractor | Kolega Code launches via integration shim | `integrations/kolega-code/` |
| **OpenCode** | Add to `~/.local/share/opencode/mcp.json` with server configuration | OpenCode reads MCP config, connects to local server | `~/.local/share/opencode/mcp.json` |
| **Hermes** | HITL-aware MCP gateway integration; Hermes routes accounting requests through MCP layer with human approval gates | Hermes manages MCP server lifecycle | Hermes gateway configuration |
| **Universal (any MCP client)** | Client discovers tools via `tools/list`, reads resource templates via `resources/list`, follows prompts via `prompts/list` | Client manages connection | Any MCP-compatible configuration |

The critical insight is that **no separate UI is needed for agentic users**. The agent itself — Claude Code in the terminal, OpenClaw in the IDE, Kolega Code in the editor — becomes the accounting interface. The user types "Record a £500 payment from Acme Corp" in their existing agent chat; the agent routes this to the `accounting/createTransaction` MCP tool; the tool validates, generates Numscript, and posts to Formance; the response streams back through the same channel. For human users who prefer a dedicated chat window, the optional Chat WebApp (port 3000) provides a React/Vue interface with WebSocket connection to the same MCP Gateway — both client types consume the identical tool surface through the identical protocol.

#### 1.3.3 Service Topology and Communication

All inter-service communication traverses the MCP layer. There is no direct gRPC or REST service mesh — every capability exchange is modeled as an MCP tool call, which provides built-in schema validation, automatic discovery, and uniform observability (every call is a `tools/call` request with a traceable request ID).

The Agent Orchestrator (Supervisor) is the central router. It receives natural language requests from clients, classifies intent using the ReAct pattern at temperature = 0, and dispatches to specialist agents that each invoke MCP tools on downstream services [^480^]. The communication topology is:

| Source | MCP Tool Call | Target | Purpose |
|---|---|---|---|
| Agent Orchestrator | `accounting/createTransaction`, `accounting/getAccount`, `accounting/listTransactions` | Accounting Service | General ledger operations, chart of accounts management, contact and invoice CRUD |
| Agent Orchestrator | `banking/fetchTransactions`, `banking/createRule`, `banking/updateRule` | Bank Feed Service | Open Banking aggregation (TrueLayer/Plaid/Salt Edge), bank rules engine, feed normalization |
| Agent Orchestrator | `reporting/generatePnl`, `reporting/generateVatReturn`, `reporting/generateBalanceSheet` | Reporting Service | 33+ report types, 5-stage report engine, XBRL/iXBRL export, scheduled report generation |
| Agent Orchestrator | `memory/storeEpisodic`, `memory/semanticSearch`, `memory/queryKnowledgeGraph`, `memory/temporalQuery` | Katra-Agentic-Memory | Conversation persistence, document retrieval, entity relationship queries, trend analysis |
| Agent Orchestrator | `ledger/createTransaction`, `ledger/getBalance`, `ledger/listTransactions` | Formance Ledger (via MCP wrapper) | Immutable double-entry postings, balance queries, transaction history, metadata attachment |
| Agent Orchestrator | `skills/load`, `skills/list`, `skills/reload` | Skill Registry | OpenClaw-compatible SKILL.md loading with precedence: workspace > user > bundled |
| Formance Ledger | `COMMITTED_TRANSACTIONS` event (JetStream) | Katra-Agentic-Memory | Ledger commit notifications feed into Katra's event stream for downstream reactions |
| Katra JetStream | Event routing | Notification Service | WebSocket push to clients, email dispatch, webhook delivery (10+ event types) |

The eight specialist agents (Intake, Categorization, Validation, Posting, Reconciliation, Reporting, Tax, Audit) are not separate deployable services — they are execution contexts within the Agent Orchestrator, each with its own system prompt, tool subset, and approval policy. The orchestrator loads each specialist's capabilities from the Skill Registry, which maintains SKILL.md files in a directory hierarchy with strict loading precedence: workspace-level skills (per-project customization) override user-level skills (per-user preferences), which override bundled defaults (system-provided templates) [^65^] [^256^]. This precedence enables per-organization customization without forked codebases: an accounting practice can add a custom `reporting/generatePracticeSummary` skill in their workspace directory, and all agents working on that workspace gain access without modifying the core system.

There is no direct service-to-service coupling. The Accounting Service does not call the Reporting Service; the Bank Feed Service does not call the Notification Service. All interactions are brokered through the MCP Gateway, which routes tool calls by namespace (`accounting/*` → Accounting Service, `banking/*` → Bank Feed Service, etc.) and handles concerns that would traditionally require a service mesh: load balancing across replicas, circuit breaking on failure, request logging, and per-tenant rate limiting (60 calls per minute per tenant, adjustable via configuration) [^260^] [^391^]. This topology means a service can be replaced, upgraded, or scaled independently without changing any other service's configuration — the only contract is the MCP tool namespace and schema, which are versioned and backward-compatible within major versions.

#### 1.3.4 Docker Compose — One Architecture, Two Modes

The entire system is defined by a single `docker-compose.yml` file that runs identically in local development and production SaaS deployment. The difference between modes is purely environmental: localhost URLs versus domain names, single replicas versus multiple replicas, local volumes versus managed storage, self-signed certificates versus TLS-terminating load balancers.

```yaml
services:
  # Katra Cognitive Memory Appliance (Apache 2.0)
  # Bundles MongoDB + Redis + MinIO + MCP Server
  katra:
    image: ghcr.io/kolegadev/katra-agentic-memory:latest
    ports:
      - "9012:9012"   # Admin interface
      - "3112:3112"   # MCP endpoint (Katra convention)
    volumes:
      - katra-mongo:/data/mongodb
      - katra-redis:/data/redis
      - katra-minio:/data/minio
    environment:
      - KATRA_JETSTREAM_ENABLED=true
      - KATRA_SOLOMEM_ENABLED=true   # Session collection daemon

  # Formance Ledger Cluster (MIT)
  formance-postgres:
    image: postgres:16-alpine
    volumes:
      - formance-pg:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=formance

  formance-ledger:
    image: ghcr.io/formancehq/ledger:v2
    depends_on:
      - formance-postgres
    environment:
      - STORAGE_POSTGRES_CONN_STRING=postgres://formance-postgres/formance
    # MCP server wrapper exposes ledger tools on port 8080
    # Routed through mcp-gateway as namespace "ledger/*"

  # Application Services (each in own container)
  agent-orchestrator:
    build: ./services/agent-orchestrator
    environment:
      - MCP_GATEWAY_URL=http://mcp-gateway:3112
      - KATRA_URL=http://katra:3112
      - FORNANCE_LEDGER_URL=http://formance-ledger:8080
    depends_on:
      - mcp-gateway
      - katra

  accounting-service:
    build: ./services/accounting
    environment:
      - MCP_GATEWAY_URL=http://mcp-gateway:3112

  bank-feed-service:
    build: ./services/banking
    environment:
      - MCP_GATEWAY_URL=http://mcp-gateway:3112

  reporting-service:
    build: ./services/reporting
    environment:
      - MCP_GATEWAY_URL=http://mcp-gateway:3112

  notification-service:
    build: ./services/notifications
    environment:
      - MCP_GATEWAY_URL=http://mcp-gateway:3112
      - WEBSOCKET_ENABLED=true

  skill-registry:
    build: ./services/skills
    volumes:
      - ./skills:/app/skills:ro   # SKILL.md files mounted read-only
    environment:
      - SKILLS_PATH=/app/skills
      - MCP_GATEWAY_URL=http://mcp-gateway:3112

  # MCP Gateway (the protocol server — replaces Kong/Traefik)
  mcp-gateway:
    build: ./services/mcp-gateway
    ports:
      - "3112:3112"   # Primary MCP endpoint (local Katra convention)
    environment:
      - TRANSPORT=http,sse,stdio
      - AUTH_MODE=local   # oauth2-pkce in SaaS mode
      - RATE_LIMIT=60
    depends_on:
      - katra
      - formance-ledger

  # Human Chat UI (optional — not needed for agentic-only users)
  chat-ui:
    build: ./services/chat-ui
    ports:
      - "3000:3000"
    environment:
      - MCP_GATEWAY_URL=ws://mcp-gateway:3112
    depends_on:
      - mcp-gateway
    profiles: ["ui"]   # Only started when profile "ui" is specified

volumes:
  katra-mongo:
  katra-redis:
  katra-minio:
  formance-pg:
```

**Local mode**: The user clones the repository and runs `docker-compose up -d`. All services start on localhost. The MCP Gateway is available at `http://localhost:3112/mcp`. Katra admin is at `http://localhost:9012`. The chat UI (if started with `--profile ui`) is at `http://localhost:3000`. Data persists in named Docker volumes on the host machine. A Raspberry Pi 5 with 8 GB RAM runs the full stack by omitting the Chat UI profile and running only the agentic path — the Pi hosts the MCP Gateway, Katra, Formance, and all application services, with an agent on a connected laptop communicating via `http://pi.local:3112/mcp`.

**SaaS mode**: The same `docker-compose.yml` deploys to AWS ECS or GCP Cloud Run via Terraform/Helm. Changes are purely environmental: `mcp-gateway` gets a TLS certificate and domain name (`https://api.ledger.system/mcp`); `AUTH_MODE` switches from `local` to `oauth2-pkce` with a configured identity provider; service replicas scale horizontally (2–10 pods per service via Kubernetes HPA); PostgreSQL and MongoDB replace local volumes with managed RDS/Atlas instances; a CDN serves the Chat UI at `https://app.ledger.system`; and the `chat-ui` profile is active by default. No service code changes. No container rebuilds. The exact same Docker images that ran on the developer's laptop run in production, eliminating the "works on my machine" class of deployment failures.

The `profiles: ["ui"]` declaration on the Chat UI service is architecturally significant: it makes the human-facing web interface an optional component rather than a required one. Agentic users — those running Claude Code, OpenClaw, or Kolega Code — never start the Chat UI. Their agent connects directly to the MCP Gateway and invokes accounting tools as part of its normal workflow. This reduces resource consumption (one fewer container), attack surface (one fewer exposed port), and operational complexity (one fewer service to monitor). The Chat UI exists for users who prefer a dedicated accounting chat window; it is not required for the system to function.

#### 1.3.5 Three Primary Data Flows

The chat-to-ledger flow is the primary synchronous path. A user's natural language request ("Record a £500 payment from Acme Corp for Invoice INV-001") traverses six steps: (1) MCP connection establishment with authentication (OAuth 2.0 + PKCE in SaaS mode, local trust in development); (2) intent classification by the supervisor agent extracting entities {amount: 50000, currency: "GBP/2", customer: "acme_corp", invoice: "INV-001"}; (3) the supervisor routes to the Posting specialist, which loads the appropriate Numscript template and validates that the receivable balance is sufficient via an MCP tool call to `accounting/getAccount`; (4) the Accounting Service generates the Numscript and posts to Formance Ledger via the `ledger/createTransaction` MCP tool with the postings array, metadata, and idempotency key; (5) Formance emits `COMMITTED_TRANSACTIONS` which Katra captures via JetStream, triggering downstream reactions through its event router; (6) Katra forwards the commit event to the Notification Service, which pushes a confirmation to the client via WebSocket, while the supervisor streams the result back through the MCP response channel [^197^] [^524^]. Throughout this flow, Katra stores each step in episodic memory: the user's original message, the supervisor's routing decision, the specialist's tool invocations, the Formance response, and the final confirmation — creating a complete audit trail that survives across conversations and agents.

The bank feed processing flow is asynchronous, implemented as a durable event stream rather than a Temporal workflow (the MCP-native architecture replaces Temporal with Katra JetStream for event durability). Scheduled every 4 hours by the Bank Feed Service, it fetches transactions from the bank API (Open Banking via TrueLayer/Plaid/Salt Edge, or OFX upload), normalizes to a canonical schema, categorizes using a per-organization model (Random Forest trained on 12 months of reconciliation history, achieving 97 percent accuracy on suggested matches), matches against existing ledger transactions via `accounting/listTransactions`, posts unmatched items as new transactions via `ledger/createTransaction`, and emits reconciliation events that Katra routes to the Notification Service for user alert [^345^] [^349^]. This flow demonstrates the reactive architecture: the background pipeline runs asynchronously, but MCP tool calls and JetStream events provide real-time status propagation to any connected client.

The report generation flow combines Formance data with Katra context. The Reporting Service receives a request ("Generate my Q3 P&L and compare to last year"), validates permissions via `accounting/checkPermissions`, queries Formance Ledger for the relevant transaction range via `ledger/listTransactions`, retrieves historical context and prior report preferences from Katra via `memory/semanticSearch`, calculates the report in Python (Pandas/NumPy), generates PDF/Excel output, stores it in Katra's MinIO object store (S3-compatible), and emits a completion event that the Notification Service routes to the client. The semantic search step is what distinguishes this flow from legacy reporting: the agent recalls that the user prefers P&L with five-category IFRS 18 breakdown, excludes intercompany transactions, and uses accrual basis — all from prior conversation context stored in Katra's memory, not from explicit user configuration [^471^] [^475^].

---

### 1.4 Target Users and Scope

#### 1.4.1 Primary Personas

The system is designed for three primary user personas, each with distinct transaction volumes, compliance requirements, and feature needs. The **UK-based freelancer or sole trader** operates as a single person with simple transactions — perhaps 20–50 per month — is likely VAT-registered (mandatory above £85,000 turnover), and needs core bookkeeping, invoicing, and VAT return capabilities without the complexity of multi-user permissions or payroll. The **small limited company** employs 2–10 people, is VAT-registered, may have multi-currency transactions, and requires approval workflows, bank feed automation, document extraction, and eventually payroll. The **accounting practice** manages multiple client entities and needs multi-entity switching, consolidated reporting, intercompany transaction handling, and practice-level analytics — this persona becomes the primary user in Phase 4.

A fourth emerging persona is the **AI-native business operator**: a user who conducts all business operations through an AI agent workspace (Claude Code, OpenClaw, Kolega Code) and expects accounting to be available as naturally as file editing or web search. For this persona, the SKILL.md installation path is the primary — often sole — interface. They do not visit a website to use accounting; they tell their agent to "set up my books" and the agent discovers, configures, and operates the accounting system through MCP tool calls. The local-first, open-source, MCP-native architecture is designed for this persona from the ground up: no vendor lock-in, no data leaving their hardware, no proprietary interface to learn.

#### 1.4.2 In-Scope Features

The following table maps capabilities to implementation phases across the fifteen-month roadmap. Features are considered in-scope once they reach production readiness within the specified phase.

| Capability Domain | MVP (Weeks 1–8) | Phase 2 (Months 3–5) | Phase 3 (Months 6–9) | Phase 4 (Months 10–15) |
|---|---|---|---|---|
| Core General Ledger | COA templates, NL transaction entry, double-entry validation, reversing entries [^45^] | Journal approval workflows, recurring transactions | Multi-currency (IAS 21), inventory, fixed assets | Multi-entity with intercompany elimination [^585^] |
| Invoicing & AR/AP | Basic invoice creation, PDF generation, credit notes, payment marking [^268^] | Recurring invoices, multi-step approval chains | Purchase orders, three-way matching, supplier bills | Project tracking, expense claims, mileage |
| Bank Reconciliation | CSV/OFX import, manual matching, reconciliation report [^276^] | Open Banking feeds (TrueLayer/Plaid), auto-categorization rules [^261^] | ML-powered matching (JAX-style, 97% accuracy) [^349^] | Real-time auto-reconciliation (80%+ auto-match) |
| Tax & Compliance | UK VAT nine-box calculation, MTD preview [^124^] | HMRC MTD VAT API submission [^579^] | Multi-tax jurisdictions (EU VAT, US sales tax), UK payroll RTI [^592^] | Full iXBRL filing, IFRS 18 native support [^301^] |
| Reporting | P&L, Balance Sheet, Trial Balance, Aged AR/AP [^43^] | Custom report templates, scheduled reports | Advanced reports (KPI, variance, cash flow), custom builder | Consolidated reporting, practice analytics |
| Document Processing | — | OCR + LLM extraction (95–97% accuracy) [^62^] | 2-pass verification for high-value invoices | Bulk processing, intelligent routing |
| AI & Agents | Basic chat via MCP, 25+ skills, Katra episodic memory | 65+ skills, semantic search, knowledge graph, full HITL | Graduated autonomy, anomaly detection, temporal analysis | Full audit automation, EU AI Act certification |
| MCP & Distribution | SKILL.md for OpenClaw/Claude Code; local Docker Compose | SKILL.md for Kolega Code, Codex CLI, OpenCode, Hermes; OAuth 2.0 + PKCE for SaaS | Custom MCP server marketplace; third-party tool publishing | White-label MCP servers; partner integration SDK |

The progression reflects a deliberate sequencing: the MVP establishes the ledger foundation, MCP infrastructure, and conversational interface with Katra episodic memory; Phase 2 adds automation (bank feeds, rules, document processing) that reduces manual effort by 70 percent-plus, alongside expanded agent support and SaaS authentication; Phase 3 introduces scale capabilities (multi-currency, payroll, inventory) and advanced Katra memory modalities (semantic search, knowledge graphs); Phase 4 delivers enterprise features (multi-entity, practice management, white-label MCP servers) that capture high-value accounting practice customers. By Phase 4, the system achieves an estimated 95 percent feature parity with Xero's core offering while maintaining the architectural advantages of MCP-native delivery, local-first deployment, and open-source licensing [^594^].

#### 1.4.3 Out-of-Scope Items

Several capability areas are explicitly excluded from scope through Phase 4. The **Construction Industry Scheme (CIS)**, which requires specialized subcontractor deduction handling and monthly CIS300 returns to HMRC, is deferred to a post-Phase 4 release targeting the UK construction sector [^598^]. **Property management** features — per-property P&L tracking, rent roll management, tenant deposit handling, and service charge apportionment — are reserved for a future landlord-focused module. **Advanced manufacturing** capabilities including bill of materials, work-in-progress tracking, and shop floor integration are not planned. **US and Canadian payroll** are excluded due to the complexity of multi-state tax withholding, benefits administration, and jurisdiction-specific compliance; the payroll scope is limited to UK PAYE/NI/RTI with HMRC-recognised submission status [^592^] [^593^]. These exclusions ensure that engineering resources are concentrated on achieving deep competency in the core UK small business market before expanding into specialized verticals or additional jurisdictions.
