---
name: agentic-accounting
version: "0.1.0"
description: |
  Agentic Accounting — a headless, LLM-native double-entry accounting system 
  for UK small businesses. Exposes 40+ MCP tools for chart of accounts 
  management, general ledger, contacts, bank statement import, reconciliation, 
  invoicing, VAT returns, and financial reporting.
server:
  url: http://localhost:3112/sse
  transport: sse
  headers:
    Content-Type: application/json
---

# Agentic Accounting — MCP SKILL.md

## Overview

Agentic Accounting is a fully headless, LLM-native double-entry accounting system 
designed for UK small businesses. This MCP server (port 3112, SSE transport) 
exposes **40+ tools** across 8 domains that any MCP-compatible agent can invoke 
to manage real business finances.

All financial data is stored in a PostgreSQL database with full audit trails 
(immutable transactions, digital-link VAT records, reconciliation logs).

## Quick Start

```bash
# Clone and start all services
git clone <repo-url> && cd agentic-accounting
docker compose up -d

# Verify health
curl http://localhost:3112/health
# → {"status":"ok"}

# Verify tools available
curl -X POST http://localhost:3112/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## Tool Reference

### Chart of Accounts (COA) — 4 tools

| Tool ID | Description | Required Parameters |
|---------|-------------|---------------------|
| `coa.list` | List all accounts in the chart of accounts | _(none)_ |
| `coa.add_account` | Create a new account (e.g., 5210 Marketing) | `code`, `name`, `category`, `type` |
| `coa.edit_account` | Update an existing account's name, code, or category | `account_id` |
| `coa.set_vat_rate` | Set/update the default VAT rate on an account | `account_id`, `vat_rate` |

**Examples:**
```
"Show me my chart of accounts"
"Add a new expense account 5210 for Marketing"
"Rename account 5210 to 'Digital Marketing'"
"Set VAT rate to 20% on the marketing account"
```

**Categories:** Asset, Liability, Equity, Revenue, Expense  
**VAT Rates:** `20%`, `5%`, `0%`, `exempt`

### General Ledger (GL) — 7 tools

| Tool ID | Description | Required Parameters |
|---------|-------------|---------------------|
| `gl.record_expense` | Record a business expense with VAT | `description`, `amount` |
| `gl.record_income` | Record revenue/income received | `description`, `amount` |
| `gl.record_transfer` | Transfer between bank accounts | `from_account`, `to_account`, `amount` |
| `gl.journal_entry` | Create a manual journal entry with debits/credits | `date`, `postings` |
| `gl.list_transactions` | Browse/search recent transactions | _(none)_ |
| `gl.transaction_detail` | Get full detail of a specific transaction | `transaction_id` |
| `gl.undo_transaction` | Reverse/delete a previously recorded transaction | `transaction_id` |

**Examples:**
```
"Paid £50 for office supplies at Tesco"
"Received £1,200 from Acme Ltd for consulting"
"Transfer £500 from current account to savings"
"Create a journal entry to correct depreciation"
"Show me all transactions from last month"
"Undo the last expense I recorded"
```

**Postings format:**
```json
{
  "date": "2025-06-15",
  "reference": "JE-2025-001",
  "description": "Correct depreciation for Q2",
  "postings": [
    {"account_id": "uuid-here", "amount": 50000, "side": "debit"},
    {"account_id": "uuid-here", "amount": 50000, "side": "credit"}
  ]
}
```

### Contacts — 5 tools

| Tool ID | Description | Required Parameters |
|---------|-------------|---------------------|
| `contact.create` | Add a new customer, supplier, or other contact | `name`, `type` |
| `contact.edit` | Update an existing contact's details | `contact_id` |
| `contact.list` | List all contacts, filterable by type | _(none)_ |
| `contact.detail` | Get full details of a specific contact | `contact_id` |
| `contact.archive` | Archive (soft-delete) a contact | `contact_id` |

**Contact Types:** `customer`, `supplier`, `both`, `other`

**Examples:**
```
"Add a new supplier called 'Office Supplies Ltd'"
"Update Acme Ltd's phone number to 020 7946 0000"
"Show me all my customers"
"Archive the old supplier XYZ Corp"
```

### Bank Statement Import — 6 tools

| Tool ID | Description | Required Parameters |
|---------|-------------|---------------------|
| `bank.import_csv` | Import a CSV bank statement | `bank_account_id`, `file_path` |
| `bank.import_ofx` | Import an OFX/QFX bank statement | `bank_account_id`, `file_path` |
| `bank.list_accounts` | List connected bank accounts | _(none)_ |
| `bank.add_account` | Add a new bank account to track | `name` |
| `bank.transactions` | List imported bank transactions | `bank_account_id` |
| `bank.categorize` | Assign a bank transaction to an account/category | `bank_transaction_id`, `account_id` |

**Supported CSV Formats:** Monzo, Revolut, Starling, HSBC, Barclays, Lloyds, NatWest, Generic  
**Supported OFX Versions:** 1.02, 2.1, 2.2

**Examples:**
```
"Import my Monzo bank statement CSV"
"Import my HSBC OFX statement"
"Show me my bank accounts"
"Show unmatched transactions from my current account"
"Categorize this transaction as marketing expense"
```

### Reconciliation — 5 tools

| Tool ID | Description | Required Parameters |
|---------|-------------|---------------------|
| `recon.start` | Start a new bank reconciliation session | `bank_account_id` |
| `recon.match` | Match a bank transaction to a GL transaction | `reconciliation_id`, `bank_transaction_id`, `transaction_id` |
| `recon.create_and_match` | Create a new GL transaction AND match to bank line | `reconciliation_id`, `bank_transaction_id` |
| `recon.status` | Check reconciliation session progress | `reconciliation_id` |
| `recon.report` | Generate reconciliation summary report | `reconciliation_id` |

**Examples:**
```
"Start a bank reconciliation for my current account"
"Match this bank transaction to the recorded expense"
"Create an expense for this bank transaction and match it"
"How's my reconciliation going?"
"Show me the reconciliation report"
```

### Invoices — 6 tools

| Tool ID | Description | Required Parameters |
|---------|-------------|---------------------|
| `invoice.create` | Create a new sales invoice for a customer | `contact_id`, `lines` |
| `invoice.send` | Send a draft invoice to the customer | `invoice_id` |
| `invoice.list` | List invoices, filterable by status | _(none)_ |
| `invoice.mark_paid` | Mark an invoice as paid | `invoice_id` |
| `invoice.credit_note` | Issue a credit note against an invoice | `invoice_id` |
| `invoice.overdue` | List all overdue invoices | _(none)_ |

**Invoice Statuses:** `draft`, `sent`, `viewed`, `paid`, `overdue`

**Line items format:**
```json
{
  "contact_id": "uuid-here",
  "issue_date": "2025-06-15",
  "due_date": "2025-07-15",
  "lines": [
    {"description": "Website design", "quantity": 1, "unit_price": 250000, "vat_rate": "20%"},
    {"description": "Hosting setup", "quantity": 1, "unit_price": 25000, "vat_rate": "20%"}
  ],
  "notes": "Payment due within 30 days"
}
```

**Examples:**
```
"Create an invoice for Acme Ltd for £2,500 for website design"
"Send invoice INV-001 to the customer"
"Show me all unpaid invoices"
"Mark invoice INV-001 as paid"
"Issue a credit note for £100 on INV-001 due to overcharge"
"Which invoices are overdue?"
```

### VAT — 4 tools

| Tool ID | Description | Required Parameters |
|---------|-------------|---------------------|
| `vat.preview_return` | Preview VAT return before filing (9-box UK format) | `start_date`, `end_date` |
| `vat.transaction_detail` | See which transactions are in a VAT return | `vat_period_id` |
| `vat.adjustment` | Add a manual adjustment to a VAT return box | `vat_period_id`, `amount`, `reason` |
| `vat.audit_trail` | View the MTD digital-link audit trail | `vat_period_id` |

**9-Box UK VAT Return:**
- Box 1: VAT due on sales (output VAT)
- Box 2: VAT due on EU acquisitions
- Box 3: Total output VAT (Box 1 + Box 2)
- Box 4: VAT reclaimed on purchases (input VAT)
- Box 5: Net VAT (Box 3 - Box 4)
- Box 6: Total sales excluding VAT
- Box 7: Total purchases excluding VAT
- Box 8: EU sales
- Box 9: EU acquisitions

**Examples:**
```
"Show me my VAT return for Q2 2025"
"What transactions are in my Q2 VAT return?"
"Add a £50 adjustment for fuel scale charge on my VAT return"
"Show me the audit trail for my VAT return"
```

### Reports — 3 tools

| Tool ID | Description | Required Parameters |
|---------|-------------|---------------------|
| `report.run` | Generate a financial report | `report_type` |
| `report.list` | List available report types | _(none)_ |
| `report.schedule` | Schedule a recurring report (daily/weekly/monthly/quarterly) | `report_type`, `frequency` |

**Report Types:** `profit_and_loss`, `balance_sheet`, `trial_balance`, `aged_receivables`, `aged_payables`

**Examples:**
```
"Run a Profit & Loss for last month"
"What reports can I run?"
"Send me a P&L report every month"
```

## Server Configuration

The MCP agent should connect to:

```
URL: http://localhost:3112/sse
Transport: SSE (Server-Sent Events)
```

### YAML Configuration (for agents that support SKILL.md)

```yaml
servers:
  - name: agentic-accounting
    url: http://localhost:3112/sse
    transport: sse
```

### JSON Configuration Example

```json
{
  "mcpServers": {
    "agentic-accounting": {
      "url": "http://localhost:3112/sse",
      "transport": "sse"
    }
  }
}
```

## Setup Instructions

### Prerequisites

- Docker and Docker Compose v2
- 4 GB RAM minimum (8 GB recommended)
- Ports 5432, 6379, 8000, 9000, 9001, 3112 available

### Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd agentic-accounting

# 2. (Optional) Configure environment variables
cp .env.example .env
# Edit .env to set DB_PASSWORD, MINIO_PASSWORD, etc.

# 3. Start all services
docker compose up -d

# 4. Wait for services to be healthy
docker compose ps

# 5. Verify the gateway
curl http://localhost:3112/health
```

### Service Architecture

| Service | Port | Purpose |
|---------|------|---------|
| Postgres 16 | 5432 | Primary database (double-entry ledger) |
| Redis 7 | 6379 | Caching & session store |
| MinIO | 9000/9001 | Document & statement storage |
| accounting-api | 8000 | Headless REST API (FastAPI) |
| **MCP Gateway** | **3112** | **MCP protocol gateway (this service)** |
| chat-ui | 3000 | Optional chat interface (profile: ui) |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_PORT` | 3112 | Gateway listen port |
| `API_BASE_URL` | `http://accounting-api:8000` | Accounting API URL |
| `SKILL_REGISTRY_PATH` | `/app/skills/registry.yaml` | Tool registry path |
| `MCP_TRANSPORT` | `sse` | MCP transport method |

## Health Verification

```bash
# Gateway health check
curl http://localhost:3112/health
# → {"status":"ok"}

# Service info
curl http://localhost:3112/
# → Returns service info, tools count, endpoints

# MCP Initialize
curl -X POST http://localhost:3112/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'

# MCP Tools List (returns all 40+ tools)
curl -X POST http://localhost:3112/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'

# SSE Connection Test
curl -N http://localhost:3112/sse
# Should stream SSE events
```

## Troubleshooting

### Gateway won't start

```bash
# Check logs
docker compose logs mcp-gateway

# Verify the skills registry is mounted
docker compose exec mcp-gateway ls -la /app/skills/

# Check API connectivity
docker compose exec mcp-gateway curl -s http://accounting-api:8000/health
```

### Tools return 404 errors

The accounting-api service may not be ready. Wait for all services:
```bash
docker compose ps  # All services should show "healthy"
```

### SSE connection drops

SSE connections have a 30-second heartbeat. Ensure your client handles reconnection:
- The `endpoint` event provides the message POST URL
- Reconnect on connection loss

### File imports fail

File paths must be accessible from within the container:
- Mount files in a shared volume (`./data:/app/data`)
- Use absolute paths or paths relative to `/app/`

## Data Privacy Notice

- All financial data is stored locally in PostgreSQL
- No data is transmitted to external services
- MinIO stores documents/statements locally
- The system operates entirely offline after initial setup
- Database backups should be configured as per your data retention policy
- UK VAT data is stored with full MTD digital-link audit trails

## Uninstall Instructions

```bash
# Stop all services and remove containers
docker compose down

# Remove all data volumes (DESTRUCTIVE)
docker compose down -v

# Remove Docker images
docker rmi agentic-accounting-mcp-gateway agentic-accounting-api

# Remove cloned repository
cd .. && rm -rf agentic-accounting
```

## Agent Compatibility

| Agent | Compatible | SSE Support | Notes |
|-------|-----------|-------------|-------|
| **OpenClaw** | ✅ Yes | ✅ | Native MCP SSE client — auto-discovers via SKILL.md |
| **Claude Code** | ✅ Yes | ✅ | Full MCP support — add to mcpServers config |
| **Kolega Code** | ✅ Yes | ✅ | Native MCP integration via SKILL.md discovery |
| **Continue.dev** | ✅ Yes | ✅ | Add to mcpServers in config.json |
| **Cursor** | ✅ Yes | ✅ | MCP server configuration via settings |
| **Zed** | ⚠️ Partial | ⚠️ | May require stdio transport (not yet supported) |
| **Copilot (VS Code)** | ⚠️ Partial | ⚠️ | Limited MCP support in current versions |

### Configuring Your Agent

#### Claude Code / Claude Desktop
```json
{
  "mcpServers": {
    "agentic-accounting": {
      "url": "http://localhost:3112/sse",
      "transport": "sse"
    }
  }
}
```

#### Kolega Code
Place this SKILL.md at the repository root. Kolega Code auto-discovers the 
MCP server from the YAML frontmatter and connects automatically.

#### OpenClaw
OpenClaw reads the SKILL.md frontmatter and establishes an SSE connection.
Once connected, all 40+ tools are available to the agent.

#### Generic MCP Client
Any MCP-compatible client can connect to `http://localhost:3112/sse` using 
the SSE transport. The `initialize`, `tools/list`, `tools/call`, and 
`resources/list` RPC methods are fully implemented.

## System Dependencies

The project uses the following system-level tools:

### Playwright (browser automation)

Playwright provides headless Chromium for PDF generation, invoice rendering, 
and browser automation. It is included in all Docker images and available as 
a dev dependency.

**Installation (local development):**
```bash
pip install playwright
python -m playwright install chromium --with-deps
```

**Available in:**
- `api/Dockerfile` — Chromium installed alongside WeasyPrint for PDF rendering
- `chat-ui/Dockerfile` — Chromium for UI testing and screenshots
- `api/pyproject.toml` — `playwright>=1.45.0` in dev dependencies
- `chat-ui/requirements.txt` — `playwright>=1.45.0`

**System packages required (apt, installed in Dockerfiles):**
```
libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2
libdbus-1-3 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3
libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2
fonts-liberation fonts-noto-color-emoji
```

### WeasyPrint (PDF generation)

Used for invoice and financial report PDF rendering.

**System packages required (apt):**
```
libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0
libffi-dev shared-mime-info
```

## API Documentation

Full OpenAPI documentation is available at:
- Gateway: http://localhost:3112/docs
- Accounting API: http://localhost:8000/docs

## License

See LICENSE file in the repository.
