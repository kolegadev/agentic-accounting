# Agentic Accounting — Headless LLM-Native Small Business Accounting

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-870%20passing-brightgreen.svg)]()

---

## Overview

**Agentic Accounting** is an open-source, local-first, MCP-native double-entry accounting system built for UK small businesses. Unlike traditional accounting software, it has no graphical UI — you operate it entirely through natural language conversation with any MCP-compatible LLM agent (Claude Code, OpenClaw, Kolega Code, etc.).

The system is designed from the ground up for LLM interaction. Every accounting operation is exposed as a discoverable MCP tool with structured schemas, validated server-side. Double-entry invariants (sum-to-zero) are enforced at three independent layers — Pydantic validators, service-layer checks, and database constraints — so the LLM cannot accidentally create an unbalanced transaction. All monetary amounts use **integer pence** exclusively; there are no floating-point values anywhere in the system.

Built for UK sole traders, limited companies, and partnerships — VAT-registered or not — Agentic Accounting gives you complete financial control running locally on your laptop or a Raspberry Pi 5. No cloud subscription, no vendor lock-in, no data leaving your machine.

---

## Quick Start

```bash
git clone https://github.com/kolegadev/agentic-accounting.git
cd agentic-accounting
docker compose up -d
# Copy SKILL.md to your MCP agent's skills directory
```

Then open your MCP agent (Claude Code, OpenClaw, Kolega Code, etc.) and say:

> **"Set up my business."**

The agent will auto-discover all 40 accounting tools and walk you through chart of accounts selection, bank account setup, and initial balances.

---

## What's Implemented

### MVP (Phase 1 — 10 Modules)

| Module | Description | Tests |
|--------|-------------|-------|
| **M1: Chart of Accounts** | 8 UK COA templates (Sole Trader, Ltd Co, Partnership, Micro-Entity, Property Landlord), 5-category 4-digit numbering, VAT rate metadata per account | 32 |
| **M2: Core General Ledger** | NL→transaction parsing, double-entry with sum-to-zero at 3 layers (Pydantic + Service + DB), append-only postings, JE-YYYY-NNNN numbering, 7 GL SKILLs | 52 |
| **M3: Contact Management** | Customer/Supplier/Both types, auto-creation from transactions, duplicate detection (name/email/VAT), AR/AP balance tracking | 56 |
| **M4: Bank Statement Import** | CSV (auto-detect columns for Monzo, Revolut, Starling, HSBC, Barclays, Lloyds, NatWest + generic) + OFX (1.02/2.1/2.2), FITID/SHA-256 dedup | 61 |
| **M5: Bank Reconciliation** | 1:1, 1:many, and partial matching, reconciliation report with balance verification | 46 |
| **M6: Basic Invoicing** | INV lifecycle (Draft → Sent → Viewed → Paid → Overdue → Cancelled), immutability after send, credit notes, PDF generation via WeasyPrint, email tracking | 79 |
| **M7: VAT & MTD Preview** | UK 9-box return (Boxes 1–9), 3 schemes (standard/cash/flat rate), MTD digital-link compliance, VAT audit trail | 60 |
| **M8: Core Financial Reports** | 5-stage report engine: Profit & Loss, Balance Sheet, Trial Balance, Aged Receivables, Aged Payables — multiple output formats | 49 |
| **M9: LLM Chat Interface** | WebSocket chat, 40-SKILL registry, rule-based intent router, 3 personas (Accountant, Bookkeeper, Business Owner), natural date parsing, conversation state in Redis | 63 |
| **M10: MCP Gateway + SKILL.md** | MCP protocol server (SSE transport, port 3200), SKILL.md auto-installer, Docker Compose orchestration | 8 |

### Phase 2: Automation (8 Features)

| Feature | Description | Tests |
|---------|-------------|-------|
| **Formance Ledger** | Production-grade double-entry ledger (MIT-licensed) running as Docker service, API adapter for hybrid operation | 15 |
| **Multi-User Auth** | 5 roles (Owner/Admin/Accountant/Bookkeeper/Viewer), JWT RS256 tokens, bcrypt password hashing, RBAC middleware on all endpoints | 40 |
| **Approval Workflows** | Threshold-based routing (<£500 auto, £500–£2k single approver, >£2k dual approver), 1–3 level approval chains, role enforcement | 30 |
| **HMRC MTD Submission** | OAuth 2.0 to HMRC, fraud prevention headers (Gov-Client-*), retry with exponential backoff, obligation checking before submission | 36 |
| **Bank Rules Engine** | 96 pre-built UK merchant/pattern rules, priority-ordered first-match execution, 6 condition operators (equals/contains/starts_with/regex/amount_gt/amount_lt), 3 action types (categorize/flag/ignore) | 38 |
| **Recurring Transactions** | 6 frequencies (daily/weekly/monthly/quarterly/biannually/annually), 3 end conditions (after N occurrences/on date/never), skip/pause/resume lifecycle, auto-generation with idempotency | 44 |
| **Open Banking Feeds** | Multi-provider abstraction layer (TrueLayer/Plaid/SaltEdge/Yodlee), mock provider with 25 realistic UK merchant profiles for testing | 39 |
| **Document OCR** | Upload support (JPEG/PNG/PDF), simulated extraction for 17 UK suppliers (Tesco, Sainsbury's, Amazon Business, etc.), human review confirmation step | 40 |

**Total: 870 tests pass, 40 SKILLs, 15 database migrations, 110+ source files**

---

## Architecture

Agentic Accounting follows a clean modular architecture designed for headless LLM operation:

- **Python 3.11+ / FastAPI** — async API server with SQLAlchemy 2.0 + PostgreSQL 16 for the primary ledger
- **MCP Gateway** (port 3200) — exposes all 40 accounting tools via the Model Context Protocol using SSE transport
- **Katra-Agentic-Memory** — cognitive memory layer positioned between the API services and the data layer, providing cross-session conversation persistence with episodic, semantic, knowledge graph, and temporal memory stores. Conversations started in one MCP agent can continue in another without loss of context. Katra is an optional profile: `docker compose --profile memory up -d`
- **Docker Compose** — 9 containerized services: `postgres`, `redis`, `minio`, `formance-postgres`, `formance-ledger`, `accounting-api`, `mcp-gateway`, `katra-memory` (optional, `--profile memory`), `chat-ui` (optional, profile-activated)
- **Double-entry invariants** enforced at 3 independent layers:
  1. **Pydantic validators** — reject unbalanced or zero-amount postings at the API boundary
  2. **Service-layer checks** — validate account existence, period integrity, and business rules
  3. **Database constraints** — CHECK constraints guarantee `debit_amount > 0 XOR credit_amount > 0` per posting row
- **All monetary amounts in INTEGER PENCE** — no floats, no decimals, no rounding errors
- **Append-only postings** — transactions are never updated or deleted; corrections are made via reversing journal entries preserving a complete audit trail
- **40 SKILLs** registered in `skills/registry.yaml`, automatically discovered by MCP agents via `tools/list`

```
          ┌─────────────┐
          │  MCP Agent  │  (Claude Code, OpenClaw, Kolega Code…)
          └──────┬──────┘
                 │ SSE (port 3200)
          ┌──────▼──────┐
          │ MCP Gateway │  SKILL.md + registry.yaml → 40 tools
          └──────┬──────┘
                 │ HTTP
          ┌──────▼──────┐
          │ Accounting  │  FastAPI (port 8000)
          │    API      │  Routes → Services → Models → DB
          └──────┬──────┘
                 │
    ┌────────────▼────────────────────────┐
    │      Katra-Agentic-Memory           │
    │  episodic · semantic · knowledge    │
    │  graph · temporal memory            │
    └──┬────────────┬───────────┬─────────┘
       │            │           │
  ┌────▼────┐ ┌─────▼────┐ ┌───▼──────────┐
  │Postgres │ │  Redis   │ │  Formance    │
  │   16    │ │    7     │ │  Ledger v2   │
  └─────────┘ └──────────┘ └──────────────┘
```

---

## Xero Feature Parity

| Feature | Xero | This System | Status |
|---------|------|-------------|--------|
| Chart of Accounts | ✅ Templates + custom | ✅ 8 UK templates + CRUD | **MVP** |
| Double-Entry GL | ✅ | ✅ 3-layer validation, append-only | **MVP** |
| Bank Reconciliation | ✅ Auto + manual | ✅ Manual (MVP) + rules engine | **MVP** |
| Bank Feeds | ✅ Direct feeds | ✅ Open Banking abstraction | **Phase 2** |
| Invoicing | ✅ Full lifecycle | ✅ Full lifecycle + credit notes | **MVP** |
| VAT Returns | ✅ MTD submission | ✅ 9-box + MTD submission | **Phase 2** |
| Financial Reports | ✅ P&L, BS, TB, Ageing | ✅ P&L, BS, TB, AR/AP Ageing | **MVP** |
| Multi-Currency | ✅ 160+ currencies | ❌ (Phase 3) | **Roadmap** |
| Payroll | ✅ UK RTI | ❌ (Phase 3) | **Roadmap** |
| Inventory | ✅ | ❌ (Phase 3) | **Roadmap** |
| Fixed Assets | ✅ | ❌ (Phase 3) | **Roadmap** |
| Purchase Orders | ✅ | ❌ (Phase 3) | **Roadmap** |
| Multi-User | ✅ 5+ roles | ✅ 5 roles, JWT, RBAC | **Phase 2** |
| Approval Workflows | ✅ | ✅ Threshold-based, 1–3 levels | **Phase 2** |
| Document OCR | ✅ Hubdoc | ✅ Simulated (17 suppliers) | **Phase 2** |
| Open API | ✅ | ✅ MCP protocol (40 tools) | **MVP** |
| Mobile App | ✅ | ❌ (web chat only) | **Roadmap** |
| AI Assistant | ❌ (bolt-on) | ✅ Native LLM chat | **MVP** |
| Local-First | ❌ (cloud-only) | ✅ Docker Compose, offline | **MVP** |
| Open Source | ❌ (proprietary) | ✅ MIT + Apache 2.0 | **MVP** |
| Self-Hosted | ❌ | ✅ Laptop or Raspberry Pi 5 | **MVP** |

**Xero parity: ~75%** (MVP + Phase 2 combined)

---

## Development Roadmap

```
Phase 1 (MVP) ✅ — 10 modules, 8 weeks
Phase 2 (Automation) ✅ — 8 features, Open Banking / HMRC / Document / Recurring
Phase 3 (Scale) 🔜 — Multi-currency (150+), UK Payroll RTI, Inventory,
                    Fixed Assets, Purchase Orders/Bills, IFRS 18 P&L,
                    Advanced Reports, Custom Report Builder,
                    ML-Powered Reconciliation
Phase 4 (Enterprise) 🔮 — Multi-Entity consolidation, Project Tracking,
                          API Platform (OpenAPI 3.0, SDKs), App Marketplace,
                          White-Label, XBRL/iXBRL Filing, CIS,
                          Property Management
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.11+ |
| **API Framework** | FastAPI (async) |
| **ORM** | SQLAlchemy 2.0 (async) |
| **Database** | PostgreSQL 16 |
| **Cache / Sessions** | Redis 7 |
| **Cognitive Memory** | Katra-Agentic-Memory (Apache 2.0) |
| **Object Storage** | MinIO |
| **Production Ledger** | Formance Ledger v2 (MIT) |
| **Containerization** | Docker Compose |
| **Agent Protocol** | MCP (SSE transport, port 3200) |
| **PDF Generation** | WeasyPrint |
| **Templating** | Jinja2 |
| **OFX Parsing** | ofxparse |
| **PDF/Image OCR** | Simulated extraction engine (17 UK supplier profiles) |

---

## Contributing

We welcome contributions! Here's how to get started:

1. **Fork the repository** and clone it locally
2. **Start the services**: `docker compose up -d`
3. **Run the tests**: `docker compose exec accounting-api pytest -v`
4. **Read the contracts**: Module contracts live in `documents/CONTRACT_M*.md`
5. **Pick an issue**: Check the GitHub Issues for bugs and features labeled `good first issue`
6. **Follow the patterns**: Modules follow a consistent structure — `models/` → `services/` → `routes/` → `validators/` → `tests/`

All contributions must pass the existing 870-test suite and include tests for new functionality. Code is formatted with Ruff (line-length 100) and type-checked with mypy (strict mode).

---

## License

- **Application code**: [MIT License](https://opensource.org/licenses/MIT)
- **Katra-Agentic-Memory** (if used): [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)
- **Formance Ledger**: [MIT License](https://github.com/formancehq/ledger/blob/main/LICENSE)

See the `LICENSE` file in the repository root for full terms.
