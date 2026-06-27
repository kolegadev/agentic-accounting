# Facet: Formance Ledger Technical Architecture

> Research conducted: 2026-06-25
> Sources consulted: 15+ independent searches, 50+ distinct sources including official docs, GitHub repos, blog posts, and third-party analyses. All citations use [^number^] format.

---

## Key Findings

### Core Data Model: Double-Entry Immutable Ledger
- **Formance Ledger uses a classical double-entry data model** with three core resources: Accounts, Transactions, and Logs (immutable log entries). Every transaction involves two or more accounts in compensating directions, and balances are derived from an immutable append-only log [^102^].
- **Each transaction produces a hash** from its data combined with the previous transaction's hash, creating a tamper-evident chain "similar to a blockchain mechanism" [^102^]. This provides regulatory-grade traceability and auditability.
- **The postings table is append-only**: corrections are made via compensating postings, not updates or deletes. A database-layer constraint rejects any transaction where postings do not sum to zero [^45^].
- **Accounts use colon-delimited multi-segment paths** (e.g., `users:1234:wallet`, `platform:fees`) that create a hierarchical namespace enabling wildcard queries without a separate analytics schema [^45^].
- **Metadata is first-class** — structured metadata can be attached to any transaction or account, typed as Number, String, Asset, Monetary, Account, or Portion, and queried directly [^95^].
- **Resources are fully isolated per ledger** — two ledgers can have accounts with the same name without interference, enabling multi-tenant isolation [^102^].

### Numscript DSL: Declarative Financial Transaction Language
- **Numscript is a purpose-built DSL** for modeling financial transactions. It replaces imperative API calls with declarative scripts that describe intent once and execute atomically [^79^].
- **Core syntax** revolves around `send [ASSET/PRECISION AMOUNT] ( source = @account destination = @account )` statements [^86^].
- **Percentage splits with `remaining` keyword** handle fractional distribution cleanly: `destination = { 85% to @drivers:042 remaining to { 10% to @charity remaining to @platform:fees } }` [^86^].
- **Multi-source transactions** pull from several accounts to fund a single payment, with precise overdraft control (bounded, unbounded, or denied) [^186^].
- **Uses only integer math with built-in rounding rules** combined with "Unambiguous Monetary Notation" (e.g., `USD/2 599` means $5.99) to ensure deterministic rounding without floating-point errors [^79^].
- **Metadata can be set within scripts** via `set_tx_meta("key", value)` for attaching business context like payment method, card scheme, or authorization IDs [^107^].
- **Variable substitution** enables dynamic scripts: `vars { monetary $payment }` allows runtime parameter injection [^107^].
- **Functions available**: `balance(@account, asset)` reads account balances; `overdraft()` checks negative balances on asset accounts; `meta()` reads structured account metadata into variables [^95^][^108^].
- **VSCode extension and online playground** available at playground.numscript.org for development and testing [^200^].
- **Limitation**: The standard `balance()` function only works with non-negative balances; for negative balances, the experimental `overdraft()` function is required [^108^].

### API Surface: REST-First with Multi-Language SDKs
- **REST API v1 and v2** with comprehensive endpoints for Ledger, Payments (V1/V3), Wallets, Reconciliation, Orchestration, Auth, and Webhooks [^188^].
- **Six official SDKs** generated programmatically via Speakeasy: Go (`formance-sdk-go`), TypeScript (`@formance/formance-sdk`), Python (`formance-sdk-python`), Java (`com.formance:formance-sdk`), C# (`FormanceSDK`), and PHP (`formance/formance-sdk`) [^194^].
- **SDKs are in beta** — Formance recommends pinning to a specific package version as breaking changes may occur without major version updates [^197^].
- **No native GraphQL support** — Formance does not expose a GraphQL API; all access is REST-based. Third-party Fragment ($10.8M raised, backed by Stripe) differentiates by offering a GraphQL-based ledger API [^80^].
- **Webhooks module (Enterprise Edition)** provides configurable webhook endpoints with signing secrets for event delivery [^188^].
- **fctl CLI** is the primary developer tool for stack management, ledger operations, and workflow orchestration. Installable via Homebrew [^124^].
- **Authentication**: OAuth 2.0 client credentials flow and personal tokens supported [^77^].
- **Key Ledger V2 endpoints**: CreateLedger, CreateTransaction, ListAccounts, ListTransactions, GetBalancesAggregated, GetVolumesWithBalances, RevertTransaction, AddMetadataOnTransaction, CreateBulk, ExportLogs, plus pipeline and schema management [^188^].

### Multi-Currency and Multi-Asset Support
- **Native multi-asset support** — a single account can hold balances in multiple assets (USD, EUR, BTC, custom tokens) simultaneously [^211^].
- **Universal Monetary Notation**: `USD/2 10000` means $100.00 (currency code + decimal precision + integer amount) [^124^]. This eliminates floating-point precision issues.
- **Currency conversion strategies**: The ledger supports both funded exchanges (trading against a reserve account with limited supply) and non-funded conversions (trading against `@world` which introduces unbounded units) [^211^].
- **Single-stage and multi-stage conversions**: For simple conversions, a single transaction suffices. For swaps requiring multiple legs, Formance recommends using a swap account intermediate [^211^].
- **No built-in exchange rate service**: Formance does not provide live exchange rates; the application layer must supply conversion rates. This is consistent with Formance's design philosophy of being a "system of record" rather than a market data provider.
- **Accounts are multi-asset by default** — "The same account structure and Numscripts work across USD, EUR, GBP, stablecoins, or any asset you define" [^107^].

### Scalability and Performance
- **Single-ledger throughput: ~1,000 writes/second** on commodity PostgreSQL hardware [^46^]. This is explicitly documented as the optimization target for the latest stable version.
- **Horizontal scaling via ledger segmentation**: Applications requiring more than 1K writes/second should create multiple ledgers and write to them in parallel [^46^].
- **Multi-ledger, single-writer, sequential writes architecture** designed for auditability and easy reasoning about transaction trails [^46^].
- **Primary bottleneck: PostgreSQL row-level locks** on the `accounts_volumes` table. Locks are applied per `(account, asset)` pair. High concurrency on a single source account (e.g., `@world`) causes transactions to serialize [^46^].
- **Mitigation strategies**: (1) Spread load across multiple source accounts using dynamic identifiers like `@world:<random_id>`; (2) Disable or async log hashing to remove PostgreSQL advisory lock overhead (tradeoff: lose cryptographic immutability proof); (3) Spread across different assets to leverage per-asset parallelization [^46^].
- **Ledger schemas and chart of accounts** can be enforced for structural validation, ensuring transactions only use valid account structures [^46^].
- **Bi-temporal timestamps**: Every posting records both effective date (when the event occurred) and insertion date (when the system recorded it), enabling point-in-time historical queries [^45^].
- **Context**: 1,000 sustained transactional writes/second = 86.4 million writes/day. As one benchmarking analysis notes, "Most mid-size fintech companies never sustain more than a few hundred transactional writes per second" [^137^].

### Deployment Options
- **Three deployment modes**: Formance Cloud (fully managed SaaS), Self-Hosted Community Edition, and Self-Hosted Enterprise Edition [^198^].
- **Production support only via Kubernetes operator**: "Production usage of the Formance Ledger is (only) supported through the official k8s operator deployment mode" [^169^].
- **Community Edition** (open-source, free): Includes Ledger, Payments, Gateway modules. Community-supported [^198^].
- **Enterprise Edition** (commercial license): Adds Auth, Wallets, Flows, Reconciliation, Webhooks, Web Console, SSO/OIDC, RBAC, Audit Logs, and direct Formance support [^198^].
- **Local development**: All-in-one Docker Compose available (`docker compose -f examples/standalone/docker-compose.yml up`) that starts PostgreSQL, Gateway (Caddy), Ledger server, Ledger worker, and Console UI on localhost [^169^].
- **Architecture stack**: PostgreSQL (main storage), Kafka/NATS (cross-service async communication), Traefik (HTTP gateway). The platform is transitioning to a unified monorepo structure [^131^].
- **Artifacts**: Standalone binaries, Docker images on GHCR, and Helm charts for Kubernetes deployment [^169^].

### Integration Patterns: Connectivity Module
- **Formance Connectivity** (formerly "Payments") is a unified API that abstracts multiple payment providers including Stripe, Adyen, Wise, Mangopay, Banking Circle, Modulr, Fireblocks, and Kraken [^45^].
- **Connector framework**: Extensible architecture where each connector translates PSP-specific formats to a generalized Formance format. Organizations can build custom connectors [^144^].
- **Connectivity does NOT auto-create Ledger entries**: It is a "normalized data store of your external providers" that syncs accounts, balances, and transactions. It is separate from the Ledger — the application or Flows module must explicitly create Ledger transactions based on Connectivity events [^186^].
- **Some providers support initiating transfers and payouts**, not just data ingestion [^186^].
- **Reconciliation module** compares Ledger balances against Connectivity cash pool balances to detect drift [^165^].

### Security Model
- **Enterprise Edition includes Auth module** with OIDC well-knowns, client management, user listing, and secret management [^197^].
- **Enterprise Edition includes RBAC** (Role-Based Access Control) and **SSO/OIDC** integration [^198^].
- **Enterprise Edition includes Audit Logs** — complete audit trail of all operations [^198^].
- **OAuth 2.0** is the primary authentication mechanism for API access [^197^].
- **Data immutability at the storage layer**: Hash-chained transactions provide tamper detection. Formance describes this as "regulatory-grade traceability" [^218^].
- **Webhook security**: The webhooks module supports signing secrets for payload verification [^188^].

### Comparison with Alternatives

| Dimension | Formance | Modern Treasury | TigerBeetle | Fragment |
|---|---|---|---|---|
| **License** | MIT (open-source) | Proprietary | MIT (open-source) | Proprietary |
| **Deployment** | Self-hosted or Cloud | Fully managed SaaS only | Self-hosted | Managed hosted |
| **Ledger model** | Double-entry, programmable | Double-entry | Double-entry | Schema-driven |
| **DSL** | Numscript | None (API-only) | None (API-only) | GraphQL-based |
| **Payment rails** | Via Connectivity connectors | Direct (40+ banks) | N/A | N/A |
| **Throughput** | ~1K tx/s per ledger | Not disclosed | 1M+ tx/s claimed | Not disclosed |
| **Primary use case** | Product ledger, wallets | Payment operations | High-volume transfers | Developer ledger API |
| **Funding** | $21M Series A (Jan 2025) | $183M raised (Series C) | $30.5M Series A | $10.8M Seed |
| **Notable customers** | Doctolib, Liberis, Booksy, Shares, Newton | Gusto, Robinhood, ClassPass | Not publicly disclosed | Pleo, NALA |

**Key distinctions**:
- **Modern Treasury** owns the full pipeline including compliance, bank connectivity, and money movement. Formance provides the ledger engine and lets customers choose their own rails and infrastructure [^105^].
- **TigerBeetle** operates at a lower layer — a "purpose-built, open-source financial transactions database claiming 1,000x throughput versus general-purpose databases" with production customers processing 100M+ transactions monthly [^80^]. It is a database, not a complete platform.
- **Fragment** offers a GraphQL-based ledger API with a visual fund flow designer, positioning itself as a "database for money" [^80^].

### Community and Ecosystem
- **GitHub**: `formancehq/ledger` has **1,300+ stars**, **167 forks**, **35 contributors**, **325 releases** (latest v2.3.21, June 2026), **5 open issues**, **12 open PRs**. Written in Go (96.2%) with PLpgSQL (2.7%) [^169^].
- **Active development**: Last commit ~3 days ago at time of research. Regular releases with active dependency updates and security patches [^169^].
- **Community support via GitHub Discussions** (migrated from Slack) [^169^].
- **Documentation**: Comprehensive docs at docs.formance.com, includes interactive API playground with fctl proxy support [^77^].
- **MIT Licensed** — permissive open-source license [^175^].
- **Founded 2021 in France**. Raised **$21M Series A in January 2025** co-led by PayPal Ventures and Portage Ventures, with Y Combinator participation. Named customers include Doctolib, Liberis, and Booksy, with ~20 customers and 10x revenue growth over prior 12 months as of early 2025 [^105^].

### Production Readiness and Case Studies
- **Shares** (social investment platform): +1,000 stocks/assets on Formance ledger, -50% dedicated engineers vs in-house, deployed UK operations in 8 weeks, 150,000+ users [^216^].
- **Newton** (Canadian crypto exchange): 70+ assets, $10M+ daily transactions, 700K users. As a FINTRAC-regulated platform, uses Formance for "accurately track every asset and money movement" [^217^].
- **Other named customers**: Doctolib, Liberis, Booksy, Stables, Bastion, Payflip, Getmomo [^218^][^105^].
- **Production deployment** requires Kubernetes operator. Production "is (only) supported through the official k8s operator deployment mode" [^169^].

---

## Major Players & Sources

| Entity | Role/Relevance |
|---|---|
| **Formance (formance.com)** | Primary subject — programmable open-source core ledger for fintech, MIT-licensed, France-based, PayPal Ventures-backed |
| **formancehq/ledger (GitHub)** | Core ledger repository — 1.3k stars, Go-based, PostgreSQL-backed, active development |
| **formancehq/stack (GitHub)** | Platform monorepo with unified infrastructure layer |
| **formancehq/numscript (GitHub)** | Numscript DSL interpreter and CLI tooling |
| **Modern Treasury** | Primary proprietary competitor — full-stack payment operations, $2B valuation, $400B+ processed |
| **TigerBeetle** | Lower-layer alternative — purpose-built financial transactions database, extreme throughput |
| **Fragment** | Competitor — GraphQL-based ledger API, Stripe-backed |
| **PayPal Ventures / Portage Ventures / YC** | Formance investors — signals market validation |
| **Doctolib, Liberis, Booksy, Shares, Newton** | Named production customers validating real-world usage |

---

## Trends & Signals

- **Convergence of ledger, payments, and banking infrastructure** is accelerating. Modern Treasury added ledgers and stablecoins; Formance added connectivity and orchestration; the category boundaries are blurring [^80^].
- **Open-source vs. proprietary fault line**: Formance, TigerBeetle, Blnk, and Moov bet that open-source community drives adoption. Modern Treasury and Fragment counter that proprietary systems proven at scale carry less risk [^80^].
- **LLM-native infrastructure appetite**: Formance's documentation exposes an `llms.txt` endpoint (https://docs.formance.com/llms.txt), suggesting awareness of AI-assisted development workflows [^77^].
- **10x revenue growth in 12 months** as of early 2025 signals strong product-market fit in the fintech infrastructure space [^105^].
- **Regulatory demands driving adoption**: Newton's FINTRAC-regulated use case and Shares' multi-country expansion demonstrate Formance's suitability for regulated environments requiring audit trails and immutability [^217^][^216^].
- **Community-led support model**: Migration from Slack to GitHub Discussions suggests a maturing open-source project with sustainable community engagement [^169^].

---

## Controversies & Conflicting Claims

- **Throughput expectations**: Some PostgreSQL benchmarking posts claim 100K+ writes/second, but Formance explicitly documents ~1K writes/second for realistic transactional workloads with full durability. Independent analysis confirms: "The realistic write ceiling on strong hardware is ~2,000 rps" for genuine transactional writes with fsync on and indexes [^137^]. Formance's number is honest and realistic.
- **Single-writer bottleneck**: The explicit single-writer architecture per ledger means horizontal scaling requires ledger sharding. This is a conscious tradeoff for auditability and simplicity over raw throughput.
- **Open-source completeness**: The core Ledger is fully open-source, but Wallets, Flows, Reconciliation, Webhooks, RBAC, and Audit Logs are Enterprise Edition only. For a headless accounting system, the Ledger + Numscript provide the core functionality, but advanced features require commercial licensing [^198^].
- **No GraphQL**: Unlike Fragment, Formance does not offer a GraphQL API. For LLM-native applications that might benefit from flexible querying, this could be a constraint — though the REST API is comprehensive.
- **SDK maturity**: SDKs are auto-generated and marked beta. Breaking changes may occur without major version bumps. Production users may need to pin versions [^197^].

---

## Recommended Deep-Dive Areas

- **Numscript compilation and execution model**: Understanding how Numscript scripts are parsed, type-checked, and translated to postings would inform how LLM agents can generate valid scripts. The WASM port (`numscript-wasm`) is a promising angle for client-side validation [^85^].
- **Ledger schema enforcement and account interpolation**: Experimental features for schema validation and dynamic account paths could enable LLM-generated account structures that pass validation [^207^].
- **Bi-temporal query patterns**: The ability to query historical ledger states at any point in time (what did the system believe at 3pm Tuesday?) is critical for audit and correction workflows. Understanding the API for point-in-time queries would enable LLM agents to reason about historical state [^45^].
- **Wallets module internals**: While Wallets is Enterprise-only, understanding its hold/confirm/void model (built on top of Ledger primitives) would help design equivalent patterns using the open-source Ledger [^219^].
- **Connectivity connector development**: Building custom connectors for specific PSPs or bank feeds. The connector framework and contributing guidelines are documented [^144^].
- **Flow orchestration patterns**: The Flows module enables multi-step workflows with event triggers, delays, and retries — patterns that would need to be reimplemented in a headless LLM-native system [^186^].

---

## Technical Assessment for Headless Accounting System

### Strengths for LLM-Native Accounting

1. **Numscript as a DSL is highly LLM-friendly**: The declarative, intent-focused syntax maps well to natural language descriptions of financial transactions. An LLM agent could translate "split the $100 payment 70% to Alice and 30% to Bob" directly into Numscript. The VSCode extension and playground provide validation tooling [^200^].

2. **Immutable audit trail provides confidence**: The hash-chained, append-only transaction log means LLM agents can always verify state transitions and never worry about silent data mutations. Corrections are explicit compensating transactions — which LLMs can reason about naturally [^102^].

3. **Metadata support enables rich business context**: LLM agents can attach structured context (invoices, vendor IDs, categories) directly to transactions and accounts, then query by that metadata. This bridges the gap between low-level ledger entries and high-level accounting concepts [^95^][^107^].

4. **Multi-asset support handles real-world complexity**: A single business may have USD checking, EUR receivables, and crypto holdings. Formance handles all natively without workarounds [^211^].

5. **Self-hosted option provides data sovereignty**: For accounting data, keeping everything in-house is often a requirement. The MIT-licensed core and Kubernetes deployment option provide full control [^169^].

### Concerns and Mitigations

1. **1K writes/second ceiling per ledger**: For a small business accounting system, this is ample headroom (86M+ transactions/day). Multiple ledgers can be created per tenant if needed [^46^].

2. **No built-in chart of accounts / GL mapping**: Formance is explicitly a product ledger, not a general ledger. The application layer must map ledger accounts to standard accounting categories (Assets, Liabilities, Equity, Revenue, Expenses) for financial reporting [^102^]. An LLM agent can manage this mapping in metadata or a separate schema layer.

3. **No built-in exchange rates**: Multi-currency businesses need external rate feeds. An integration with a rate provider (XE, Open Exchange Rates) would be needed at the application layer [^211^].

4. **Enterprise features for wallets/holds**: The open-source core supports holds via creative account structures (e.g., `user:123:held` sub-accounts), but the Wallets module's built-in hold/confirm/void pattern requires Enterprise licensing [^219^].

5. **SDK beta status**: The auto-generated SDKs may have breaking changes. Pinning to specific versions and potentially generating custom thin wrappers is advisable [^197^].

### Architecture Recommendation

For a headless accounting system using Formance as the backend:

- **Use Formance Ledger (open-source)** as the immutable transaction store
- **Use Numscript** as the transaction description language — LLM agents generate Numscript and validate it via the playground or CLI before submission
- **Build a lightweight Go/TypeScript service** that receives natural language from LLM agents, generates/validates Numscript, executes via the Ledger API, and manages account-to-GL-category mappings
- **Use PostgreSQL** for both Ledger storage and application metadata
- **Deploy via Docker Compose** for development, Kubernetes operator for production
- **Start with Community Edition** and upgrade to Enterprise if Wallets, Flows, Reconciliation, or RBAC become needed

### Verdict

Formance Ledger is an **excellent fit** for a headless LLM-native accounting system. Its immutable, metadata-rich double-entry model, combined with the expressive Numscript DSL and open-source core, provides exactly the kind of transparent, auditable transaction infrastructure that LLM agents need to operate safely in the financial domain. The 1K tx/s throughput per ledger is more than sufficient for small business accounting. The main gap is the application-layer mapping to standard accounting categories (chart of accounts, GL structures), which should be built as a thin abstraction layer above the Ledger.

---

## Sources Index

| Citation | Source |
|---|---|
| [^45^] | formance.com — Double-Entry Accounting for Engineers: A Practical Guide |
| [^46^] | docs.formance.com — Architecting for scale |
| [^77^] | docs.formance.com — API Reference |
| [^79^] | formance.com — What is Numscript and Why is it Awesome? |
| [^80^] | apideck.com — Money movement infrastructure is fintech's most important layer |
| [^85^] | github.com/PagoPlus/numscript-wasm — WebAssembly port of Numscript |
| [^86^] | docs.formance.com — Numscript module documentation |
| [^95^] | docs.formance.com — Numscript metadata reference |
| [^96^] | pkg.go.dev — Formance Ledger Go package docs |
| [^102^] | docs.formance.com — Ledger module documentation |
| [^103^] | github.com/formancehq/ledger — README |
| [^105^] | apideck.com — Modern Treasury vs Formance comparison |
| [^107^] | docs.formance.com — Example implementations (multi-asset, metadata) |
| [^108^] | docs.formance.com — Numscript overdraft function reference |
| [^124^] | docs.formance.com — Platform Quick Start |
| [^125^] | docs.formance.com — Operator Setup |
| [^131^] | github.com/formancehq/stack — Platform monorepo |
| [^137^] | dev.to — PostgreSQL Write Performance: What Benchmarks Won't Tell You |
| [^139^] | janisheck.com — GitHub Year in Review 2024 |
| [^144^] | github.com/formancehq/payments — Payments/Connectivity module |
| [^159^] | kaggle.com — Open-Source GitHub Repos dataset |
| [^165^] | formance.com — Reconciliation module |
| [^169^] | github.com/formancehq/ledger — GitHub repository (1.3k stars) |
| [^172^] | formance.com — Announcing Formance Platform |
| [^175^] | github.com/formancehq/ledger/LICENSE — MIT License |
| [^184^] | docs.formance.com — Flows: Ledger to Ledger example |
| [^185^] | docs.formance.com — Flows: Workflow execution |
| [^186^] | docs.formance.com — Core Concepts |
| [^187^] | grokipedia.com — Bitemporal modeling |
| [^188^] | github.com/formancehq/formance-sdk-go — SDK operations list |
| [^194^] | docs.formance.com — SDKs listing |
| [^195^] | github.com/formancehq/formance-sdk-typescript — Wallets SDK |
| [^197^] | github.com/formancehq/formance-sdk-typescript — SDK maturity note |
| [^198^] | docs.formance.com — Deployment Overview |
| [^200^] | docs.formance.com — Numscript module (example) |
| [^201^] | docs.formance.com — Ledger Quick Start |
| [^207^] | docs.formance.com — RideShare Tutorial (schemas) |
| [^211^] | docs.formance.com — Assets & Currency conversion |
| [^213^] | docs.formance.com — Ledger module (Product vs General Ledger) |
| [^216^] | formance.com — Shares Customer Story |
| [^217^] | formance.com — Newton Customer Story |
| [^218^] | formance.com — Homepage (customers, features) |
| [^219^] | docs.formance.com — Wallets module |
