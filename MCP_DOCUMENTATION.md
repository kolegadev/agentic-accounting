# Agentic Accounting — MCP Documentation

**Version:** 0.1.0  
**Protocol:** Model Context Protocol (MCP)  
**Transport:** Server-Sent Events (SSE)  
**Port:** 3112  
**Last Updated:** 2026-06-27  

---

## 1. MCP Gateway Overview

### What Is MCP?

The **Model Context Protocol (MCP)** is an open protocol standardised by Anthropic that enables AI agents (LLMs) to interact with external tools, data sources, and services through a well-defined JSON-RPC 2.0 interface. Instead of requiring every AI agent to have custom integrations, MCP provides a universal "USB-C for AI"—a single protocol that any compatible agent can use to discover and call tools.

### Why Agentic Accounting Uses MCP

Agentic Accounting is a **headless, LLM-native double-entry accounting system** designed for UK small businesses. The system has no traditional UI; instead, every accounting operation—recording expenses, creating invoices, running VAT returns, reconciling bank statements—is exposed as an **MCP tool**. This means:

- **Claude Code**, **OpenClaw**, **Kolega Code**, or any MCP-compatible agent can act as your accounting interface.
- The AI agent discovers tools automatically via `tools/list` and calls them via `tools/call`.
- No API keys, no custom SDKs, no manual integration work.

### How the Gateway Bridges AI Agents to Accounting Functions

```
┌─────────────────────┐      SSE + JSON-RPC       ┌─────────────────────┐      HTTP/REST       ┌─────────────────────┐
│   AI Agent          │ ◄───────────────────────► │   MCP Gateway       │ ◄──────────────────► │   Accounting API    │
│  (Claude, OpenClaw, │     port 3112             │   (FastAPI)         │     port 8000        │   (FastAPI)         │
│   Kolega, etc.)     │                           │                     │                      │                     │
└─────────────────────┘                           └─────────────────────┘                      └─────────────────────┘
```

The MCP Gateway:
1. Maintains a persistent **SSE connection** with the AI agent.
2. Receives **JSON-RPC requests** on `/message`.
3. Validates tool names and parameters against the **tool registry** (loaded from `skills/registry.yaml`).
4. Proxies validated calls to the **Accounting API** on port 8000.
5. Returns results in MCP-compliant format.

### SSE Transport on Port 3112

The gateway uses **Server-Sent Events (SSE)** for transport. The agent opens a long-lived GET connection to `/sse`, which streams:
- An `endpoint` event telling the agent where to POST JSON-RPC messages.
- A `server_info` event with server metadata and tool count.
- Periodic `heartbeat` events every 30 seconds.

This transport was chosen for the MVP because it works over plain HTTP, requires no WebSocket libraries, and is supported by all major MCP client implementations.

### No API Keys Required (Local Trust Model)

MVP runs entirely on `localhost`. All services are containerised and intended to run on a single machine. There is **no authentication**, **no API keys**, and **no external network calls** after initial Docker image pulls. Data never leaves the machine. This is suitable for MVP evaluation; OAuth 2.0 + PKCE will be added in Phase 2+.

### Katra Cognitive Memory Integration

The Agentic Accounting system also integrates with **Katra-Agentic-Memory** (Apache 2.0) — a separate cognitive memory MCP server running on port 3113. While the accounting MCP gateway exposes accounting *tools* (create transactions, run reports, etc.), Katra provides cognitive memory *primitives* (store memories, semantic search, temporal recall) that persist conversation context across agent sessions.

**Two MCP servers, one system:**
| Server | Port | Purpose |
|--------|------|---------|
| Accounting MCP Gateway | 3112 | 40+ accounting tools (ledger, invoicing, VAT, reports) |
| Katra Cognitive Memory | 3113 | Episodic, semantic, knowledge graph, and temporal memory |

Both speak the same MCP protocol — any MCP-compatible agent can connect to either or both. The accounting API automatically uses Katra for conversation persistence when available, falling back to Redis-only mode when unavailable.

---

## 2. Connection

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Service information (name, version, tools count, endpoints) |
| `/health` | GET | Health check — returns `{"status":"ok"}` |
| `/sse` | GET | SSE connection endpoint (persistent, long-lived) |
| `/message` | POST | JSON-RPC 2.0 message handler — all RPC calls go here |
| `/docs` | GET | Interactive OpenAPI/Swagger documentation |

### Health Check

```bash
curl http://localhost:3112/health
```

**Response:**
```json
{"status": "ok"}
```

The health endpoint returns HTTP 200 when the gateway is running. It does not depend on the accounting API being available—it simply confirms the gateway process is alive.

### SSE Connection

The SSE endpoint establishes a persistent connection. The gateway streams events to the client.

```bash
curl -N http://localhost:3112/sse
```

**Typical stream output:**

```
event: endpoint
data: {"uri":"/message"}

event: server_info
data: {"name":"agentic-accounting-mcp","version":"0.1.0","tools":40,"connected_at":"2026-06-27T18:00:00Z"}

event: heartbeat
data: {"timestamp":"2026-06-27T18:00:30Z"}

event: heartbeat
data: {"timestamp":"2026-06-27T18:01:00Z"}
```

**Events explained:**

| Event | Payload | Meaning |
|-------|---------|---------|
| `endpoint` | `{"uri":"/message"}` | Tells the agent where to POST JSON-RPC requests |
| `server_info` | Server metadata + tool count | Confirms connection and provides context |
| `heartbeat` | `{"timestamp":"..."}` | Keep-alive sent every 30 seconds |

The `Cache-Control: no-cache` and `Connection: keep-alive` headers are set. Heartbeats continue indefinitely until the client disconnects. If the connection drops, the client should reconnect and re-initialise.

---

## 3. MCP Protocol Methods

All MCP communication uses **JSON-RPC 2.0** sent as HTTP POST to `/message`. Every request and response includes `"jsonrpc":"2.0"` and an `id` field for request/response correlation.

### 3.1 `initialize`

The agent must call `initialize` first to discover server capabilities.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "0.1.0",
    "clientInfo": {
      "name": "claude-code",
      "version": "1.0"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "0.1.0",
    "serverInfo": {
      "name": "agentic-accounting-mcp",
      "version": "0.1.0"
    },
    "capabilities": {
      "tools": {},
      "resources": {}
    }
  }
}
```

The `capabilities` object tells the agent that this server supports both `tools/list` + `tools/call` and `resources/list` + `resources/read`.

### 3.2 `tools/list`

Returns all available tools with their names, descriptions, and JSON Schema input specifications.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}
```

**Response (abbreviated — all 40 tools returned):**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "coa.list",
        "description": "Use when the user wants to see all accounts in their chart of accounts, or asks 'what accounts do I have'.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "include_inactive": { "type": "boolean", "default": false }
          }
        }
      },
      {
        "name": "coa.add_account",
        "description": "Use when the user wants to create a new account in the chart of accounts.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "code": { "type": "string", "description": "Account code (e.g. 5210)" },
            "name": { "type": "string", "description": "Account name" },
            "category": { "type": "string", "enum": ["Asset","Liability","Equity","Revenue","Expense"] },
            "type": { "type": "string", "description": "Account type (e.g. Bank, Expense, CurrentAsset)" },
            "vat_rate": { "type": "string", "enum": ["20%","5%","0%","exempt"] },
            "parent_id": { "type": "string", "format": "uuid" }
          },
          "required": ["code", "name", "category", "type"]
        }
      },
      {
        "name": "gl.record_expense",
        "description": "Use when the user has paid for something and wants to record it as a business expense.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "description": { "type": "string" },
            "amount": { "type": "integer" },
            "vat_rate": { "type": "string", "enum": ["20%","5%","0%","exempt"] },
            "contact": { "type": "string" },
            "date": { "type": "string" }
          },
          "required": ["description", "amount"]
        }
      },
      {
        "name": "invoice.create",
        "description": "Use when the user wants to create a new sales invoice for a customer.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "contact_id": { "type": "string", "format": "uuid" },
            "issue_date": { "type": "string" },
            "due_date": { "type": "string" },
            "lines": {
              "type": "array",
              "items": {
                "type": "object",
                "properties": {
                  "description": { "type": "string" },
                  "quantity": { "type": "integer" },
                  "unit_price": { "type": "integer" },
                  "vat_rate": { "type": "string", "enum": ["20%","5%","0%","exempt"] }
                }
              }
            },
            "notes": { "type": "string" }
          },
          "required": ["contact_id", "lines"]
        }
      },
      {
        "name": "report.run",
        "description": "Use when the user wants to generate a financial report (P&L, balance sheet, trial balance, aged receivables/payables).",
        "inputSchema": {
          "type": "object",
          "properties": {
            "report_type": {
              "type": "string",
              "enum": ["profit_and_loss","balance_sheet","trial_balance","aged_receivables","aged_payables"]
            },
            "start_date": { "type": "string" },
            "end_date": { "type": "string" },
            "as_at_date": { "type": "string" }
          },
          "required": ["report_type"]
        }
      },
      {
        "name": "vat.preview_return",
        "description": "Use when the user wants to see their VAT return before filing.",
        "inputSchema": {
          "type": "object",
          "properties": {
            "start_date": { "type": "string" },
            "end_date": { "type": "string" }
          },
          "required": ["start_date", "end_date"]
        }
      }
    ]
  }
}
```

> **Note:** The response includes all 40+ tools. The above shows representative examples from each category. See [Section 4](#4-complete-tool-reference-40-tools) for the full listing.

### 3.3 `tools/call`

The agent calls a specific tool by name with arguments. The gateway validates the tool name and proxies the request to the accounting API.

#### Example: Recording an Expense (`gl.record_expense`)

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "method": "tools/call",
  "params": {
    "name": "gl.record_expense",
    "arguments": {
      "description": "Office supplies at Tesco",
      "amount": 5000,
      "vat_rate": "20%",
      "contact": "Tesco",
      "date": "2026-06-27"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 10,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"id\":\"txn-uuid-1234\",\"description\":\"Office supplies at Tesco\",\"amount\":5000,\"vat_rate\":\"20%\",\"vat_amount\":833,\"net_amount\":4167,\"date\":\"2026-06-27\",\"status\":\"recorded\",\"postings\":[{\"account_id\":\"exp-account-uuid\",\"amount\":4167,\"side\":\"debit\"},{\"account_id\":\"vat-input-uuid\",\"amount\":833,\"side\":\"debit\"},{\"account_id\":\"bank-account-uuid\",\"amount\":5000,\"side\":\"credit\"}]}"
      }
    ]
  }
}
```

#### Example: Listing Accounts (`coa.list`)

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 11,
  "method": "tools/call",
  "params": {
    "name": "coa.list",
    "arguments": {
      "include_inactive": false
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 11,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "[{\"id\":\"uuid-1000\",\"code\":\"1000\",\"name\":\"Current Account\",\"category\":\"Asset\",\"type\":\"Bank\",\"vat_rate\":null,\"is_active\":true},{\"id\":\"uuid-4000\",\"code\":\"4000\",\"name\":\"Sales\",\"category\":\"Revenue\",\"type\":\"Revenue\",\"vat_rate\":\"20%\",\"is_active\":true},{\"id\":\"uuid-5000\",\"code\":\"5000\",\"name\":\"Office Expenses\",\"category\":\"Expense\",\"type\":\"Expense\",\"vat_rate\":\"20%\",\"is_active\":true}]"
      }
    ]
  }
}
```

#### Example: Creating an Invoice (`invoice.create`)

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 12,
  "method": "tools/call",
  "params": {
    "name": "invoice.create",
    "arguments": {
      "contact_id": "contact-uuid-acme",
      "issue_date": "2026-06-27",
      "due_date": "2026-07-27",
      "lines": [
        {
          "description": "Website design",
          "quantity": 1,
          "unit_price": 250000,
          "vat_rate": "20%"
        },
        {
          "description": "Hosting setup",
          "quantity": 1,
          "unit_price": 25000,
          "vat_rate": "20%"
        }
      ],
      "notes": "Payment due within 30 days"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 12,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"id\":\"inv-uuid-5678\",\"invoice_number\":\"INV-001\",\"contact_id\":\"contact-uuid-acme\",\"status\":\"draft\",\"issue_date\":\"2026-06-27\",\"due_date\":\"2026-07-27\",\"lines\":[{\"description\":\"Website design\",\"quantity\":1,\"unit_price\":250000,\"vat_rate\":\"20%\",\"line_total\":250000,\"vat_amount\":50000},{\"description\":\"Hosting setup\",\"quantity\":1,\"unit_price\":25000,\"vat_rate\":\"20%\",\"line_total\":25000,\"vat_amount\":5000}],\"net_total\":275000,\"vat_total\":55000,\"gross_total\":330000}"
      }
    ]
  }
}
```

#### Example: Running a Report (`report.run`)

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 13,
  "method": "tools/call",
  "params": {
    "name": "report.run",
    "arguments": {
      "report_type": "profit_and_loss",
      "start_date": "2026-04-01",
      "end_date": "2026-06-30"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 13,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"report_type\":\"profit_and_loss\",\"period\":\"2026-04-01 to 2026-06-30\",\"revenue\":{\"sales\":12000000,\"other_income\":0,\"total\":12000000},\"cost_of_sales\":0,\"gross_profit\":12000000,\"expenses\":{\"office_expenses\":350000,\"marketing\":200000,\"software\":150000,\"total\":700000},\"net_profit\":11300000}"
      }
    ]
  }
}
```

#### Example: Previewing VAT (`vat.preview_return`)

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 14,
  "method": "tools/call",
  "params": {
    "name": "vat.preview_return",
    "arguments": {
      "start_date": "2026-04-01",
      "end_date": "2026-06-30"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 14,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"period_id\":\"vat-period-uuid\",\"period\":{\"id\":\"vat-period-uuid\",\"start_date\":\"2026-04-01\",\"end_date\":\"2026-06-30\",\"scheme\":\"standard\"},\"boxes\":{\"box1\":2400000,\"box2\":0,\"box3\":2400000,\"box4\":140000,\"box5\":2260000,\"box6\":12000000,\"box7\":700000,\"box8\":0,\"box9\":0}}"
      }
    ]
  }
}
```

### 3.4 `resources/list`

Returns static resources available through the MCP server. Agentic Accounting exposes **COA templates** (Chart of Accounts) and **bank statement templates** as MCP resources.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "resources/list",
  "params": {}
}
```

**Response (abbreviated):**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "resources": [
      {
        "uri": "coa://templates/uk_sole_trader_no_vat",
        "name": "COA Template: uk_sole_trader_no_vat",
        "description": "Chart of Accounts template: Uk Sole Trader No Vat",
        "mimeType": "application/json"
      },
      {
        "uri": "coa://templates/uk_sole_trader_vat",
        "name": "COA Template: uk_sole_trader_vat",
        "description": "Chart of Accounts template: Uk Sole Trader Vat",
        "mimeType": "application/json"
      },
      {
        "uri": "coa://templates/uk_limited_company_no_vat",
        "name": "COA Template: uk_limited_company_no_vat",
        "description": "Chart of Accounts template: Uk Limited Company No Vat",
        "mimeType": "application/json"
      },
      {
        "uri": "coa://templates/uk_limited_company_vat",
        "name": "COA Template: uk_limited_company_vat",
        "description": "Chart of Accounts template: Uk Limited Company Vat",
        "mimeType": "application/json"
      },
      {
        "uri": "coa://templates/uk_partnership_no_vat",
        "name": "COA Template: uk_partnership_no_vat",
        "description": "Chart of Accounts template: Uk Partnership No Vat",
        "mimeType": "application/json"
      },
      {
        "uri": "coa://templates/uk_partnership_vat",
        "name": "COA Template: uk_partnership_vat",
        "description": "Chart of Accounts template: Uk Partnership Vat",
        "mimeType": "application/json"
      },
      {
        "uri": "coa://templates/micro_entity_simplified",
        "name": "COA Template: micro_entity_simplified",
        "description": "Chart of Accounts template: Micro Entity Simplified",
        "mimeType": "application/json"
      },
      {
        "uri": "coa://templates/property_landlord_vat",
        "name": "COA Template: property_landlord_vat",
        "description": "Chart of Accounts template: Property Landlord Vat",
        "mimeType": "application/json"
      },
      {
        "uri": "bank://templates/barclays",
        "name": "Bank Template: barclays",
        "description": "Bank statement import template for Barclays",
        "mimeType": "application/json"
      },
      {
        "uri": "bank://templates/hsbc",
        "name": "Bank Template: hsbc",
        "description": "Bank statement import template for Hsbc",
        "mimeType": "application/json"
      },
      {
        "uri": "bank://templates/lloyds",
        "name": "Bank Template: lloyds",
        "description": "Bank statement import template for Lloyds",
        "mimeType": "application/json"
      },
      {
        "uri": "bank://templates/natwest",
        "name": "Bank Template: natwest",
        "description": "Bank statement import template for Natwest",
        "mimeType": "application/json"
      },
      {
        "uri": "bank://templates/monzo",
        "name": "Bank Template: monzo",
        "description": "Bank statement import template for Monzo",
        "mimeType": "application/json"
      },
      {
        "uri": "bank://templates/starling",
        "name": "Bank Template: starling",
        "description": "Bank statement import template for Starling",
        "mimeType": "application/json"
      },
      {
        "uri": "bank://templates/revolut",
        "name": "Bank Template: revolut",
        "description": "Bank statement import template for Revolut",
        "mimeType": "application/json"
      }
    ]
  }
}
```

**COA Templates Available:**

| URI | Applicable To |
|-----|---------------|
| `coa://templates/uk_sole_trader_no_vat` | UK sole traders not VAT-registered |
| `coa://templates/uk_sole_trader_vat` | UK sole traders VAT-registered |
| `coa://templates/uk_limited_company_no_vat` | UK limited companies not VAT-registered |
| `coa://templates/uk_limited_company_vat` | UK limited companies VAT-registered |
| `coa://templates/uk_partnership_no_vat` | UK partnerships not VAT-registered |
| `coa://templates/uk_partnership_vat` | UK partnerships VAT-registered |
| `coa://templates/micro_entity_simplified` | Micro-entities (FRS 105) simplified |
| `coa://templates/property_landlord_vat` | Property landlords VAT-registered |

**Bank Templates Available:**

| URI | Bank |
|-----|------|
| `bank://templates/barclays` | Barclays |
| `bank://templates/hsbc` | HSBC |
| `bank://templates/lloyds` | Lloyds |
| `bank://templates/natwest` | NatWest |
| `bank://templates/monzo` | Monzo |
| `bank://templates/starling` | Starling |
| `bank://templates/revolut` | Revolut |

### 3.5 `resources/read`

Reads a specific resource by URI.

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "resources/read",
  "params": {
    "uri": "coa://templates/uk_limited_company_vat"
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "contents": [
      {
        "uri": "coa://templates/uk_limited_company_vat",
        "mimeType": "application/json",
        "text": "Resource: coa://templates/uk_limited_company_vat\n\nThis resource is available through the accounting API."
      }
    ]
  }
}
```

> **Note:** In the MVP, `resources/read` returns a placeholder. Full resource content (the actual template JSON) is available through the accounting API's `/api/v1/coa/templates/{template_id}` endpoint.

---

## 4. Complete Tool Reference (40 Tools)

All amounts are in **pence** (integer). All dates use **ISO 8601** format (`YYYY-MM-DD`). All IDs are **UUID v4** strings.

### 4.1 Chart of Accounts (COA)

#### `coa.list` — List Chart of Accounts

- **Category:** COA
- **Description:** Use when the user wants to see all accounts in their chart of accounts, or asks "what accounts do I have."
- **Endpoint:** `GET /api/v1/coa/`
- **Method:** GET

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "include_inactive": { "type": "boolean", "default": false }
  }
}
```

**Example Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "coa.list",
    "arguments": { "include_inactive": false }
  }
}
```

**Example Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{ "type": "text", "text": "[{\"id\":\"...\",\"code\":\"1000\",\"name\":\"Current Account\",\"category\":\"Asset\",\"type\":\"Bank\",\"vat_rate\":null,\"is_active\":true},...]" }]
  }
}
```

---

#### `coa.add_account` — Add Account

- **Category:** COA
- **Description:** Use when the user wants to create a new account in the chart of accounts.
- **Endpoint:** `POST /api/v1/coa/`
- **Method:** POST

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "code": { "type": "string", "description": "Account code (e.g. 5210)" },
    "name": { "type": "string", "description": "Account name" },
    "category": { "type": "string", "enum": ["Asset","Liability","Equity","Revenue","Expense"] },
    "type": { "type": "string", "description": "Account type (e.g. Bank, Expense, CurrentAsset)" },
    "vat_rate": { "type": "string", "enum": ["20%","5%","0%","exempt"] },
    "parent_id": { "type": "string", "format": "uuid" }
  },
  "required": ["code", "name", "category", "type"]
}
```

**Example Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "coa.add_account",
    "arguments": { "code": "5210", "name": "Marketing", "category": "Expense", "type": "Expense", "vat_rate": "20%" }
  }
}
```

**Example Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{ "type": "text", "text": "{\"id\":\"uuid...\",\"code\":\"5210\",\"name\":\"Marketing\",\"category\":\"Expense\",\"type\":\"Expense\",\"vat_rate\":\"20%\",\"is_active\":true}" }]
  }
}
```

---

#### `coa.edit_account` — Edit Account

- **Category:** COA
- **Description:** Use when the user wants to update an existing account's name, code, category, or other fields.
- **Endpoint:** `PATCH /api/v1/coa/{account_id}`
- **Method:** PATCH

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "account_id": { "type": "string", "format": "uuid" },
    "code": { "type": "string" },
    "name": { "type": "string" },
    "category": { "type": "string", "enum": ["Asset","Liability","Equity","Revenue","Expense"] },
    "type": { "type": "string" },
    "is_active": { "type": "boolean" }
  },
  "required": ["account_id"]
}
```

---

#### `coa.set_vat_rate` — Set VAT Rate on Account

- **Category:** COA
- **Description:** Use when the user wants to change the default VAT rate on an account.
- **Endpoint:** `PUT /api/v1/coa/{account_id}/vat-rate`
- **Method:** PUT

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "account_id": { "type": "string", "format": "uuid" },
    "vat_rate": { "type": "string", "enum": ["20%","5%","0%","exempt"] }
  },
  "required": ["account_id", "vat_rate"]
}
```

---

### 4.2 General Ledger (GL)

#### `gl.record_expense` — Record Expense

- **Category:** GL
- **Description:** Use when the user has paid for something and wants to record it as a business expense.
- **Endpoint:** `POST /api/v1/transactions/`
- **Method:** POST

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "description": { "type": "string" },
    "amount": { "type": "integer", "description": "Amount in pence" },
    "vat_rate": { "type": "string", "enum": ["20%","5%","0%","exempt"] },
    "contact": { "type": "string" },
    "date": { "type": "string", "format": "date" }
  },
  "required": ["description", "amount"]
}
```

---

#### `gl.record_income` — Record Income

- **Category:** GL
- **Description:** Use when the user received payment from a client or recorded revenue.
- **Endpoint:** `POST /api/v1/transactions/`
- **Method:** POST

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "description": { "type": "string" },
    "amount": { "type": "integer", "description": "Amount in pence" },
    "vat_rate": { "type": "string", "enum": ["20%","5%","0%","exempt"] },
    "contact": { "type": "string" },
    "date": { "type": "string", "format": "date" }
  },
  "required": ["description", "amount"]
}
```

---

#### `gl.record_transfer` — Record Transfer

- **Category:** GL
- **Description:** Use when the user wants to record a transfer between bank accounts.
- **Endpoint:** `POST /api/v1/transactions/`
- **Method:** POST

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "from_account": { "type": "string" },
    "to_account": { "type": "string" },
    "amount": { "type": "integer", "description": "Amount in pence" },
    "date": { "type": "string", "format": "date" },
    "description": { "type": "string" }
  },
  "required": ["from_account", "to_account", "amount"]
}
```

---

#### `gl.journal_entry` — Create Journal Entry

- **Category:** GL
- **Description:** Use when the user wants to record a manual journal entry with debits and credits.
- **Endpoint:** `POST /api/v1/transactions/`
- **Method:** POST

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "date": { "type": "string", "format": "date" },
    "reference": { "type": "string" },
    "description": { "type": "string" },
    "postings": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "account_id": { "type": "string", "format": "uuid" },
          "amount": { "type": "integer" },
          "side": { "type": "string", "enum": ["debit", "credit"] }
        }
      }
    }
  },
  "required": ["date", "postings"]
}
```

---

#### `gl.list_transactions` — List Transactions

- **Category:** GL
- **Description:** Use when the user wants to browse or search recent transactions.
- **Endpoint:** `GET /api/v1/transactions/`
- **Method:** GET

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "start_date": { "type": "string", "format": "date" },
    "end_date": { "type": "string", "format": "date" },
    "account_id": { "type": "string", "format": "uuid" },
    "contact_id": { "type": "string", "format": "uuid" },
    "limit": { "type": "integer", "default": 50 }
  }
}
```

**Note:** Parameters are mapped: `start_date` → `date_from`, `end_date` → `date_to` in the API call.

---

#### `gl.transaction_detail` — Transaction Detail

- **Category:** GL
- **Description:** Use when the user asks for details about a specific transaction.
- **Endpoint:** `GET /api/v1/transactions/{transaction_id}`
- **Method:** GET

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "transaction_id": { "type": "string", "format": "uuid" }
  },
  "required": ["transaction_id"]
}
```

---

#### `gl.undo_transaction` — Undo Transaction

- **Category:** GL
- **Description:** Use when the user wants to reverse or delete a previously recorded transaction.
- **Endpoint:** `POST /api/v1/transactions/{transaction_id}/reverse`
- **Method:** POST

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "transaction_id": { "type": "string", "format": "uuid" }
  },
  "required": ["transaction_id"]
}
```

---

### 4.3 Contacts

#### `contact.create` — Create Contact

- **Category:** Contact
- **Description:** Use when the user wants to add a new customer, supplier, or other contact.
- **Endpoint:** `POST /api/v1/contacts/`
- **Method:** POST

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "name": { "type": "string" },
    "type": { "type": "string", "enum": ["customer","supplier","both","other"] },
    "email": { "type": "string", "format": "email" },
    "phone": { "type": "string" },
    "address_line1": { "type": "string" },
    "city": { "type": "string" },
    "postcode": { "type": "string" },
    "notes": { "type": "string" }
  },
  "required": ["name", "type"]
}
```

---

#### `contact.edit` — Edit Contact

- **Category:** Contact
- **Description:** Use when the user wants to update an existing contact's details.
- **Endpoint:** `PATCH /api/v1/contacts/{contact_id}`
- **Method:** PATCH

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "contact_id": { "type": "string", "format": "uuid" },
    "name": { "type": "string" },
    "type": { "type": "string", "enum": ["customer","supplier","both","other"] },
    "email": { "type": "string", "format": "email" },
    "phone": { "type": "string" }
  },
  "required": ["contact_id"]
}
```

---

#### `contact.list` — List Contacts

- **Category:** Contact
- **Description:** Use when the user wants to see all contacts or filter by type.
- **Endpoint:** `GET /api/v1/contacts/`
- **Method:** GET

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "type": { "type": "string", "enum": ["customer","supplier","both","other"] },
    "search": { "type": "string" }
  }
}
```

---

#### `contact.detail` — Contact Detail

- **Category:** Contact
- **Description:** Use when the user wants full details about a specific contact.
- **Endpoint:** `GET /api/v1/contacts/{contact_id}`
- **Method:** GET

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "contact_id": { "type": "string", "format": "uuid" }
  },
  "required": ["contact_id"]
}
```

---

#### `contact.archive` — Archive Contact

- **Category:** Contact
- **Description:** Use when the user wants to archive (soft-delete) a contact.
- **Endpoint:** `POST /api/v1/contacts/{contact_id}/archive`
- **Method:** POST

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "contact_id": { "type": "string", "format": "uuid" }
  },
  "required": ["contact_id"]
}
```

---

### 4.4 Bank Statement Import

#### `bank.import_csv` — Import Bank CSV

- **Category:** Bank
- **Description:** Use when the user wants to import a CSV bank statement.
- **Endpoint:** `POST /api/v1/bank/import/csv`
- **Method:** POST_FILE (multipart file upload)

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "bank_account_id": { "type": "string", "format": "uuid" },
    "file_path": { "type": "string", "description": "Absolute path to CSV file" },
    "format": { "type": "string", "enum": ["auto","monzo","revolut","starling","hsbc","generic"], "default": "auto" }
  },
  "required": ["bank_account_id"]
}
```

**Note:** `file_path` must be accessible from within the Docker container. Use a mounted volume (e.g., `./data` directory). The `format` parameter maps to the `template` query parameter in the API.

---

#### `bank.import_ofx` — Import Bank OFX

- **Category:** Bank
- **Description:** Use when the user wants to import an OFX/QFX bank statement.
- **Endpoint:** `POST /api/v1/bank/import/ofx`
- **Method:** POST_FILE (multipart file upload)

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "bank_account_id": { "type": "string", "format": "uuid" },
    "file_path": { "type": "string", "description": "Absolute path to OFX/QFX file" }
  },
  "required": ["bank_account_id"]
}
```

---

#### `bank.list_accounts` — List Bank Accounts

- **Category:** Bank
- **Description:** Use when the user wants to see their connected bank accounts.
- **Endpoint:** `GET /api/v1/bank/accounts`
- **Method:** GET

**inputSchema:**
```json
{
  "type": "object",
  "properties": {}
}
```

---

#### `bank.add_account` — Add Bank Account

- **Category:** Bank
- **Description:** Use when the user wants to add a new bank account to track.
- **Endpoint:** `POST /api/v1/bank/accounts`
- **Method:** POST

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "name": { "type": "string" },
    "account_number": { "type": "string" },
    "sort_code": { "type": "string" },
    "currency": { "type": "string", "default": "GBP" },
    "opening_balance": { "type": "integer", "default": 0 }
  },
  "required": ["name"]
}
```

---

#### `bank.transactions` — Bank Transactions

- **Category:** Bank
- **Description:** Use when the user wants to list imported bank transactions.
- **Endpoint:** `GET /api/v1/bank/transactions`
- **Method:** GET

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "bank_account_id": { "type": "string", "format": "uuid" },
    "start_date": { "type": "string", "format": "date" },
    "end_date": { "type": "string", "format": "date" },
    "status": { "type": "string", "enum": ["unmatched","matched","all"], "default": "all" }
  },
  "required": ["bank_account_id"]
}
```

**Note:** Parameter mapping: `bank_account_id` → `account_id`, `start_date` → `date_from`, `end_date` → `date_to`.

---

#### `bank.categorize` — Categorize Bank Transaction

- **Category:** Bank
- **Description:** Use when the user wants to assign a bank transaction to an account/category.
- **Endpoint:** `PATCH /api/v1/bank/transactions/{bank_transaction_id}/categorize`
- **Method:** PATCH

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "bank_transaction_id": { "type": "string", "format": "uuid" },
    "account_id": { "type": "string", "format": "uuid" },
    "contact_id": { "type": "string", "format": "uuid" },
    "vat_rate": { "type": "string", "enum": ["20%","5%","0%","exempt"] }
  },
  "required": ["bank_transaction_id", "account_id"]
}
```

---

### 4.5 Reconciliation

#### `recon.start` — Start Reconciliation

- **Category:** Reconciliation
- **Description:** Use when the user wants to start a new bank reconciliation session.
- **Endpoint:** `POST /api/v1/reconciliation/start`
- **Method:** POST

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "bank_account_id": { "type": "string", "format": "uuid" },
    "statement_date": { "type": "string", "format": "date" },
    "statement_balance": { "type": "integer" }
  },
  "required": ["bank_account_id"]
}
```

---

#### `recon.match` — Match Transaction

- **Category:** Reconciliation
- **Description:** Use when the user wants to match a bank transaction to a GL transaction.
- **Endpoint:** `POST /api/v1/reconciliation/{reconciliation_id}/match`
- **Method:** POST

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "reconciliation_id": { "type": "string", "format": "uuid" },
    "bank_transaction_id": { "type": "string", "format": "uuid" },
    "transaction_id": { "type": "string", "format": "uuid" }
  },
  "required": ["reconciliation_id", "bank_transaction_id", "transaction_id"]
}
```

---

#### `recon.create_and_match` — Create & Match

- **Category:** Reconciliation
- **Description:** Use when the user wants to create a new GL transaction AND match it to a bank transaction in one step.
- **Endpoint:** `POST /api/v1/reconciliation/{reconciliation_id}/create-and-match`
- **Method:** POST

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "reconciliation_id": { "type": "string", "format": "uuid" },
    "bank_transaction_id": { "type": "string", "format": "uuid" },
    "description": { "type": "string" },
    "amount": { "type": "integer" },
    "vat_rate": { "type": "string", "enum": ["20%","5%","0%","exempt"] },
    "account_id": { "type": "string", "format": "uuid" },
    "contact_id": { "type": "string", "format": "uuid" }
  },
  "required": ["reconciliation_id", "bank_transaction_id"]
}
```

---

#### `recon.status` — Reconciliation Status

- **Category:** Reconciliation
- **Description:** Use when the user wants to check the status of an ongoing reconciliation.
- **Endpoint:** `GET /api/v1/reconciliation/{reconciliation_id}/status`
- **Method:** GET

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "reconciliation_id": { "type": "string", "format": "uuid" }
  },
  "required": ["reconciliation_id"]
}
```

---

#### `recon.report` — Reconciliation Report

- **Category:** Reconciliation
- **Description:** Use when the user wants a summary report of a completed reconciliation.
- **Endpoint:** `GET /api/v1/reconciliation/{reconciliation_id}/report`
- **Method:** GET

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "reconciliation_id": { "type": "string", "format": "uuid" }
  },
  "required": ["reconciliation_id"]
}
```

---

### 4.6 Invoices

#### `invoice.create` — Create Invoice

- **Category:** Invoice
- **Description:** Use when the user wants to create a new sales invoice for a customer.
- **Endpoint:** `POST /api/v1/invoices/`
- **Method:** POST

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "contact_id": { "type": "string", "format": "uuid" },
    "issue_date": { "type": "string", "format": "date" },
    "due_date": { "type": "string", "format": "date" },
    "lines": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "description": { "type": "string" },
          "quantity": { "type": "integer" },
          "unit_price": { "type": "integer", "description": "In pence" },
          "vat_rate": { "type": "string", "enum": ["20%","5%","0%","exempt"] }
        }
      }
    },
    "notes": { "type": "string" }
  },
  "required": ["contact_id", "lines"]
}
```

---

#### `invoice.send` — Send Invoice

- **Category:** Invoice
- **Description:** Use when the user wants to send a draft invoice to the customer.
- **Endpoint:** `POST /api/v1/invoices/{invoice_id}/send`
- **Method:** POST

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "invoice_id": { "type": "string", "format": "uuid" }
  },
  "required": ["invoice_id"]
}
```

---

#### `invoice.list` — List Invoices

- **Category:** Invoice
- **Description:** Use when the user wants to see all invoices or filter by status.
- **Endpoint:** `GET /api/v1/invoices/`
- **Method:** GET

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "status": { "type": "string", "enum": ["draft","sent","viewed","paid","overdue","all"], "default": "all" },
    "contact_id": { "type": "string", "format": "uuid" }
  }
}
```

---

#### `invoice.mark_paid` — Mark Invoice as Paid

- **Category:** Invoice
- **Description:** Use when the user has received payment for an invoice.
- **Endpoint:** `POST /api/v1/invoices/{invoice_id}/mark-paid`
- **Method:** POST

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "invoice_id": { "type": "string", "format": "uuid" }
  },
  "required": ["invoice_id"]
}
```

---

#### `invoice.credit_note` — Create Credit Note

- **Category:** Invoice
- **Description:** Use when the user wants to issue a credit note against an invoice.
- **Endpoint:** `POST /api/v1/invoices/{invoice_id}/credit-note`
- **Method:** POST

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "invoice_id": { "type": "string", "format": "uuid" },
    "reason": { "type": "string" },
    "amount": { "type": "integer", "description": "In pence" }
  },
  "required": ["invoice_id"]
}
```

---

#### `invoice.overdue` — List Overdue Invoices

- **Category:** Invoice
- **Description:** Use when the user asks about overdue or late payments.
- **Endpoint:** `GET /api/v1/invoices/overdue`
- **Method:** GET

**inputSchema:**
```json
{
  "type": "object",
  "properties": {}
}
```

---

### 4.7 VAT

#### `vat.preview_return` — Preview VAT Return

- **Category:** VAT
- **Description:** Use when the user wants to see their VAT return before filing. Multi-step operation: creates a VAT period, then calculates the 9-box return.
- **Endpoint:** `POST /api/v1/vat/preview` (special multi-step handler)
- **Method:** POST (gateway performs two API calls: create period + calculate)

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "start_date": { "type": "string", "format": "date" },
    "end_date": { "type": "string", "format": "date" }
  },
  "required": ["start_date", "end_date"]
}
```

**9-Box UK VAT Return format:**

| Box | Description |
|-----|-------------|
| Box 1 | VAT due on sales (output VAT) |
| Box 2 | VAT due on EU acquisitions |
| Box 3 | Total output VAT (Box 1 + Box 2) |
| Box 4 | VAT reclaimed on purchases (input VAT) |
| Box 5 | Net VAT (Box 3 − Box 4) |
| Box 6 | Total sales excluding VAT |
| Box 7 | Total purchases excluding VAT |
| Box 8 | EU sales |
| Box 9 | EU acquisitions |

---

#### `vat.transaction_detail` — VAT Transaction Detail

- **Category:** VAT
- **Description:** Use when the user wants to see which transactions are included in a VAT return.
- **Endpoint:** `GET /api/v1/vat/returns/{vat_period_id}/audit`
- **Method:** GET

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "vat_period_id": { "type": "string", "format": "uuid" }
  },
  "required": ["vat_period_id"]
}
```

**Note:** `vat_period_id` is mapped to `return_id` in the API call.

---

#### `vat.adjustment` — VAT Adjustment

- **Category:** VAT
- **Description:** Use when the user needs to make a manual adjustment to their VAT return.
- **Endpoint:** `POST /api/v1/vat/returns/{vat_period_id}/adjustment`
- **Method:** POST

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "vat_period_id": { "type": "string", "format": "uuid" },
    "amount": { "type": "integer", "description": "In pence" },
    "reason": { "type": "string" }
  },
  "required": ["vat_period_id", "amount", "reason"]
}
```

**Note:** `vat_period_id` is mapped to `return_id` in the API call.

---

#### `vat.audit_trail` — VAT Audit Trail

- **Category:** VAT
- **Description:** Use when the user wants to see the audit trail or history of VAT changes.
- **Endpoint:** `GET /api/v1/vat/returns/{vat_period_id}/audit`
- **Method:** GET

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "vat_period_id": { "type": "string", "format": "uuid" },
    "limit": { "type": "integer", "default": 100 }
  },
  "required": ["vat_period_id"]
}
```

**Note:** `vat_period_id` is mapped to `return_id` in the API call.

---

### 4.8 Reports

#### `report.run` — Run Report

- **Category:** Report
- **Description:** Use when the user wants to generate a financial report (P&L, balance sheet, trial balance, aged receivables/payables).
- **Endpoint:** `POST /api/v1/reports/run`
- **Method:** POST

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "report_type": {
      "type": "string",
      "enum": ["profit_and_loss","balance_sheet","trial_balance","aged_receivables","aged_payables"]
    },
    "start_date": { "type": "string", "format": "date" },
    "end_date": { "type": "string", "format": "date" },
    "as_at_date": { "type": "string", "format": "date", "description": "For balance sheet (point-in-time)" }
  },
  "required": ["report_type"]
}
```

---

#### `report.list` — List Available Reports

- **Category:** Report
- **Description:** Use when the user wants to see what reports are available.
- **Endpoint:** `GET /api/v1/reports/templates`
- **Method:** GET

**inputSchema:**
```json
{
  "type": "object",
  "properties": {}
}
```

---

#### `report.schedule` — Schedule Report

- **Category:** Report
- **Description:** Use when the user wants to schedule a recurring report.
- **Endpoint:** `POST /api/v1/reports/schedules`
- **Method:** POST

**inputSchema:**
```json
{
  "type": "object",
  "properties": {
    "report_type": {
      "type": "string",
      "enum": ["profit_and_loss","balance_sheet","trial_balance","aged_receivables","aged_payables"]
    },
    "frequency": { "type": "string", "enum": ["daily","weekly","monthly","quarterly"] },
    "email_to": { "type": "string", "format": "email" }
  },
  "required": ["report_type", "frequency"]
}
```

---

### Tool Summary by Category

| Category | Tools Count | Tool IDs |
|----------|:----------:|----------|
| Chart of Accounts (COA) | 4 | `coa.list`, `coa.add_account`, `coa.edit_account`, `coa.set_vat_rate` |
| General Ledger (GL) | 7 | `gl.record_expense`, `gl.record_income`, `gl.record_transfer`, `gl.journal_entry`, `gl.list_transactions`, `gl.transaction_detail`, `gl.undo_transaction` |
| Contacts | 5 | `contact.create`, `contact.edit`, `contact.list`, `contact.detail`, `contact.archive` |
| Bank Statement Import | 6 | `bank.import_csv`, `bank.import_ofx`, `bank.list_accounts`, `bank.add_account`, `bank.transactions`, `bank.categorize` |
| Reconciliation | 5 | `recon.start`, `recon.match`, `recon.create_and_match`, `recon.status`, `recon.report` |
| Invoices | 6 | `invoice.create`, `invoice.send`, `invoice.list`, `invoice.mark_paid`, `invoice.credit_note`, `invoice.overdue` |
| VAT | 4 | `vat.preview_return`, `vat.transaction_detail`, `vat.adjustment`, `vat.audit_trail` |
| Reports | 3 | `report.run`, `report.list`, `report.schedule` |
| **Total** | **40** | |

---

## 5. Error Handling

### JSON-RPC Error Codes

The gateway returns standard JSON-RPC 2.0 error responses. All errors follow this format:

```json
{
  "jsonrpc": "2.0",
  "id": null,
  "error": {
    "code": -32601,
    "message": "Method not found: nonexistent.method",
    "data": null
  }
}
```

| Code | Name | When It Occurs |
|------|------|----------------|
| `-32700` | Parse error | Invalid JSON in request body |
| `-32600` | Invalid request | Request does not conform to JSON-RPC 2.0 spec |
| `-32601` | Method not found | Unknown method (not `initialize`, `tools/list`, `tools/call`, `resources/list`, or `resources/read`) or unknown tool name |
| `-32602` | Invalid params | Missing required parameters (e.g., no `name` in `tools/call`, or missing required fields in arguments) |
| `-32603` | Internal error | Unexpected exception in handler |
| `-32000` | Tool execution failed | The accounting API returned an error or the proxy call failed |

### HTTP Error Mapping

| HTTP Status | Meaning |
|-------------|---------|
| `200` | All JSON-RPC responses use HTTP 200 (errors are in the JSON body) |
| `400` | Parse error (invalid JSON in request body) |
| `404` | Non-existent HTTP endpoint (e.g., `GET /nonexistent`) |
| `405` | Wrong HTTP method (e.g., `GET /message`) |
| `500` | Unhandled server error |

> **Important:** MCP protocol errors are returned as HTTP 200 with the error in the JSON-RPC body. HTTP error codes are only used for transport-level issues.

### Example Error Responses

**Unknown tool:**
```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "error": {
    "code": -32601,
    "message": "Unknown tool: nonexistent.tool"
  }
}
```

**Missing parameters:**
```json
{
  "jsonrpc": "2.0",
  "id": 6,
  "error": {
    "code": -32602,
    "message": "Missing tool name"
  }
}
```

**Unknown MCP method:**
```json
{
  "jsonrpc": "2.0",
  "id": 7,
  "error": {
    "code": -32601,
    "message": "Method not found: some.unknown.method"
  }
}
```

**Parse error (malformed JSON):**
```json
{
  "jsonrpc": "2.0",
  "id": null,
  "error": {
    "code": -32700,
    "message": "Parse error"
  }
}
```

**Tool execution failure (API error):**
```json
{
  "jsonrpc": "2.0",
  "id": 8,
  "error": {
    "code": -32000,
    "message": "Tool execution failed: API returned 404: Not Found"
  }
}
```

---

## 6. SKILL.md Auto-Installation

### What Is SKILL.md?

`SKILL.md` is a Markdown file with **YAML frontmatter** that MCP-compatible agents read to auto-discover and auto-configure themselves to connect to the Agentic Accounting MCP server. It is the primary mechanism for "zero-config" agent setup.

The file lives at the **repository root** (`agentic-accounting/SKILL.md`) and contains:

1. **YAML frontmatter** with server URL, transport, version, and description.
2. **Tool reference** in markdown tables describing every available tool, its parameters, and examples.
3. **Setup instructions** for Docker Compose, health checks, and environment variables.
4. **Agent compatibility matrix** for Claude Code, OpenClaw, Kolega Code, and others.

### Where to Place SKILL.md for Each Agent

| Agent | Location | Auto-Discovery? |
|-------|----------|:---------------:|
| **Claude Code / Claude Desktop** | Add `mcpServers` entry to `claude_desktop_config.json` or `mcp.json` in project root | Manual config only |
| **OpenClaw** | Place at repository root; OpenClaw reads `SKILL.md` frontmatter automatically | ✅ Yes |
| **Kolega Code** | Place at repository root; Kolega Code discovers MCP servers from `SKILL.md` YAML frontmatter | ✅ Yes |
| **Continue.dev** | Add to `mcpServers` in `config.json`; reference `SKILL.md` for tool descriptions | Manual config |
| **Cursor** | MCP server configuration via settings UI; use `SKILL.md` as reference | Manual config |

### How the Agent Discovers Tools Automatically

When an agent that supports `SKILL.md` starts up in the project directory:

1. It reads the YAML frontmatter from `SKILL.md`.
2. It extracts the `server.url` (`http://localhost:3112/sse`) and `server.transport` (`sse`).
3. It opens an SSE connection to `/sse` and receives the `endpoint` event.
4. It calls `initialize` to negotiate protocol capabilities.
5. It calls `tools/list` to discover all 40 available tools with their schemas.
6. The agent is now ready to invoke any accounting tool.

### SKILL.md Structure

```yaml
---
name: agentic-accounting
version: "0.1.0"
description: |
  Agentic Accounting — a headless, LLM-native double-entry accounting system 
  for UK small businesses. Exposes 40+ MCP tools...
server:
  url: http://localhost:3112/sse
  transport: sse
  headers:
    Content-Type: application/json
---
```

Followed by markdown sections:
- Overview
- Quick Start
- Tool Reference (8 tables, one per category)
- Server Configuration (YAML, JSON examples)
- Setup Instructions (Docker, prerequisites, architecture)
- Health Verification (curl commands)
- Troubleshooting
- Data Privacy Notice
- Agent Compatibility Matrix

### YAML Configuration (for agents that support mcpServers config)

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

---

## 7. Katra Memory Protocol

The Katra cognitive memory server exposes 35+ MCP tools organized across four memory modalities. These are separate from the accounting tools — they handle conversation persistence, not bookkeeping operations.

### 7.1 Episodic Memory

| Tool | Description |
|------|-------------|
| `store_memory` | Store a conversation turn or event with tags, session_id, and source |
| `get_memory` | Retrieve a specific memory by ID |
| `temporal_recall` | Retrieve events within a time range (default: 7 days) |

**Example: Store a conversation turn**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "store_memory",
    "arguments": {
      "content": "User asked about Q2 VAT return",
      "user_id": "accounting-agent",
      "category": "event",
      "session_id": "session-abc123",
      "source": "accounting-chat",
      "tags": ["conversation", "vat", "user"]
    }
  }
}
```

### 7.2 Semantic Search

| Tool | Description |
|------|-------------|
| `vector_search` | Semantic search across all stored memories |
| `add_semantic_fact` | Store a context snapshot as a searchable fact |

**Example: Search for past VAT conversations**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "vector_search",
    "arguments": {
      "query": "VAT return calculations Q2 2025",
      "user_id": "accounting-agent",
      "limit": 5
    }
  }
}
```

### 7.3 Knowledge Graph

| Tool | Description |
|------|-------------|
| `explore_graph` | Query entity relationships (contacts→invoices→transactions) |
| `add_graph_relationship` | Link two entities with a relationship type |

### 7.4 Katra Connection

Katra is an optional profile in the Docker Compose stack:
```bash
# Enable Katra
docker compose --profile memory up -d

# Katra MCP endpoint
curl http://localhost:3113/health
```

The accounting API connects to Katra automatically when `KATRA_MCP_URL` is set. No manual configuration is required — the `ChatService` detects Katra's presence and uses it as the primary conversation persistence layer.

### 7.5 Graceful Degradation

If Katra is unreachable or `KATRA_ENABLED=false`, the system falls back to Redis-only conversation storage with a 1-hour TTL. No errors are raised — conversation history is simply not persisted across restarts when Katra is unavailable.

---

## 8. Tool-to-API Mapping

The following table shows exactly how each MCP tool maps to the internal Accounting API endpoint. The gateway performs parameter mapping (renaming, path substitution, query vs body placement) transparently.

| Tool ID | HTTP Method | API Endpoint | Key Parameter Mapping |
|---------|:-----------:|--------------|----------------------|
| `coa.list` | GET | `/api/v1/coa/` | `include_inactive` → query param |
| `coa.add_account` | POST | `/api/v1/coa/` | All params → JSON body |
| `coa.edit_account` | PATCH | `/api/v1/coa/{account_id}` | `account_id` → path param |
| `coa.set_vat_rate` | PUT | `/api/v1/coa/{account_id}/vat-rate` | `account_id` → path param; body_as: `vat_rate` |
| `gl.record_expense` | POST | `/api/v1/transactions/` | All params → JSON body |
| `gl.record_income` | POST | `/api/v1/transactions/` | All params → JSON body |
| `gl.record_transfer` | POST | `/api/v1/transactions/` | All params → JSON body |
| `gl.journal_entry` | POST | `/api/v1/transactions/` | All params → JSON body |
| `gl.list_transactions` | GET | `/api/v1/transactions/` | `start_date` → `date_from`, `end_date` → `date_to` (query params) |
| `gl.transaction_detail` | GET | `/api/v1/transactions/{transaction_id}` | `transaction_id` → path param |
| `gl.undo_transaction` | POST | `/api/v1/transactions/{transaction_id}/reverse` | `transaction_id` → path param |
| `contact.create` | POST | `/api/v1/contacts/` | All params → JSON body |
| `contact.edit` | PATCH | `/api/v1/contacts/{contact_id}` | `contact_id` → path param |
| `contact.list` | GET | `/api/v1/contacts/` | `type`, `search` → query params |
| `contact.detail` | GET | `/api/v1/contacts/{contact_id}` | `contact_id` → path param |
| `contact.archive` | POST | `/api/v1/contacts/{contact_id}/archive` | `contact_id` → path param |
| `bank.import_csv` | POST_FILE | `/api/v1/bank/import/csv` | `bank_account_id` → `account_id` (query); `format` → `template` (query); file multipart upload |
| `bank.import_ofx` | POST_FILE | `/api/v1/bank/import/ofx` | `bank_account_id` → `account_id` (query); file multipart upload |
| `bank.list_accounts` | GET | `/api/v1/bank/accounts` | — |
| `bank.add_account` | POST | `/api/v1/bank/accounts` | All params → JSON body |
| `bank.transactions` | GET | `/api/v1/bank/transactions` | `bank_account_id` → `account_id`, `start_date` → `date_from`, `end_date` → `date_to` (query params) |
| `bank.categorize` | PATCH | `/api/v1/bank/transactions/{bank_transaction_id}/categorize` | `bank_transaction_id` → path param; rest → JSON body |
| `recon.start` | POST | `/api/v1/reconciliation/start` | All params → JSON body |
| `recon.match` | POST | `/api/v1/reconciliation/{reconciliation_id}/match` | `reconciliation_id` → path param; rest → JSON body |
| `recon.create_and_match` | POST | `/api/v1/reconciliation/{reconciliation_id}/create-and-match` | `reconciliation_id` → path param; rest → JSON body |
| `recon.status` | GET | `/api/v1/reconciliation/{reconciliation_id}/status` | `reconciliation_id` → path param |
| `recon.report` | GET | `/api/v1/reconciliation/{reconciliation_id}/report` | `reconciliation_id` → path param |
| `invoice.create` | POST | `/api/v1/invoices/` | All params → JSON body |
| `invoice.send` | POST | `/api/v1/invoices/{invoice_id}/send` | `invoice_id` → path param |
| `invoice.list` | GET | `/api/v1/invoices/` | `status`, `contact_id` → query params |
| `invoice.mark_paid` | POST | `/api/v1/invoices/{invoice_id}/mark-paid` | `invoice_id` → path param |
| `invoice.credit_note` | POST | `/api/v1/invoices/{invoice_id}/credit-note` | `invoice_id` → path param; `reason` → query param |
| `invoice.overdue` | GET | `/api/v1/invoices/overdue` | — |
| `vat.preview_return` | POST | `/api/v1/vat/preview` | **Special handler:** Step 1: POST `/api/v1/vat/periods` (create period); Step 2: POST `/api/v1/vat/periods/{id}/calculate` (calculate) |
| `vat.transaction_detail` | GET | `/api/v1/vat/returns/{vat_period_id}/audit` | `vat_period_id` → `return_id` (path param) |
| `vat.adjustment` | POST | `/api/v1/vat/returns/{vat_period_id}/adjustment` | `vat_period_id` → `return_id` (path param); rest → JSON body |
| `vat.audit_trail` | GET | `/api/v1/vat/returns/{vat_period_id}/audit` | `vat_period_id` → `return_id` (path param) |
| `report.run` | POST | `/api/v1/reports/run` | All params → JSON body |
| `report.list` | GET | `/api/v1/reports/templates` | — |
| `report.schedule` | POST | `/api/v1/reports/schedules` | All params → JSON body |

---

## 9. Security

### Local Trust Model (MVP)

The MVP operates on a **local trust model**:

- All services run in Docker containers on a single machine.
- The MCP Gateway binds to `0.0.0.0:3112` within the Docker network but is published only as configured in `docker-compose.yml`.
- There is **no authentication**, **no API keys**, and **no user sessions** in the MVP.
- The gateway trusts any request arriving on the `/message` endpoint because it is assumed to originate from a local agent on the same machine.

### Future OAuth 2.0 + PKCE (Phase 2+)

Planned for Phase 2 and beyond:

- **OAuth 2.0 Authorization Code flow with PKCE** for agent authentication.
- Per-agent API tokens with scoped permissions (e.g., read-only, expense-only, full-access).
- Audit logging of all tool calls with agent identity.
- HTTPS/TLS termination for remote access scenarios.
- Rate limiting to prevent abuse.

### Data Never Leaves the Machine

- All financial data is stored in a local PostgreSQL database.
- Document storage uses local MinIO (S3-compatible object storage).
- Bank statement imports are processed locally.
- No telemetry, no analytics, no external API calls after initial Docker image pulls.
- VAT data is stored with full MTD digital-link audit trails locally.

### Port Binding

| Service | Internal Port | Published | Notes |
|---------|:------------:|-----------|-------|
| MCP Gateway | 3112 | `${MCP_PORT:-3112}` | To restrict to localhost only, set `MCP_PORT=127.0.0.1:3112:3112` or omit the port mapping entirely |
| Accounting API | 8000 | `${API_PORT:-8000}` | Internal to Docker network in production |
| PostgreSQL | 5432 | `${DB_PORT:-5432}` | Can be omitted if only containers need access |
| Redis | 6379 | `${REDIS_PORT:-6379}` | Can be omitted if only containers need access |
| MinIO | 9000, 9001 | Published ports | Document storage |
| Chat UI | 3000 | `${UI_PORT:-3000}` | Optional (enabled with `--profile ui`) |

---

## 10. Integration Examples

### Example 1: Claude Code / Claude Desktop

**Prerequisites:**
- Docker and Docker Compose v2 installed
- Claude Desktop or Claude Code CLI installed
- Agentic Accounting services running (`docker compose up -d`)

**Step 1: Start Agentic Accounting**

```bash
cd agentic-accounting
docker compose up -d
# Wait for all services to be healthy
docker compose ps
```

**Step 2: Verify the gateway**

```bash
curl http://localhost:3112/health
# → {"status":"ok"}
```

**Step 3: Configure Claude Desktop**

Edit or create the Claude Desktop configuration file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

Add the MCP server entry:

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

**Step 4: For Claude Code CLI**

Create or edit `.mcp.json` in your project root:

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

**Step 5: Use Claude to manage your books**

Once configured, restart Claude Desktop or start a new Claude Code session. Claude will automatically discover 40 tools. Try:

- "Show me my chart of accounts"
- "Record an expense for £50 office supplies"
- "Create an invoice for Acme Ltd"
- "Show me my VAT return for Q2"
- "Run a Profit & Loss report"

---

### Example 2: OpenClaw

**Prerequisites:**
- OpenClaw installed
- Agentic Accounting repository cloned
- Docker services running

**Step 1: Clone and start the project**

```bash
git clone <repo-url> agentic-accounting
cd agentic-accounting
docker compose up -d
```

**Step 2: Verify SKILL.md is at the repository root**

```bash
ls agentic-accounting/SKILL.md
# → SKILL.md
```

**Step 3: OpenClaw auto-discovers**

OpenClaw reads `SKILL.md` from the repository root automatically. The YAML frontmatter provides:

```yaml
server:
  url: http://localhost:3112/sse
  transport: sse
```

OpenClaw:
1. Reads the frontmatter.
2. Establishes an SSE connection to `http://localhost:3112/sse`.
3. Calls `initialize`.
4. Calls `tools/list` to discover all 40 tools.
5. The tools appear in OpenClaw's tool palette.

**Step 4: Verify in OpenClaw**

OpenClaw should show `agentic-accounting` as a connected MCP server with 40 available tools. You can now ask OpenClaw natural-language questions like:

- "Record a £1,200 payment received from Acme Ltd"
- "What's my current bank balance?"
- "Import my Monzo statement from last month"
- "Reconcile my current account"

---

### Example 3: Kolega Code

**Prerequisites:**
- Kolega Code installed
- Agentic Accounting services running

**Step 1: Start the services**

```bash
cd agentic-accounting
docker compose up -d
```

**Step 2: Kolega Code auto-discovers**

Kolega Code reads the `SKILL.md` file from the repository root when you open the project directory. It extracts the server configuration from the YAML frontmatter:

```yaml
server:
  url: http://localhost:3112/sse
  transport: sse
```

Kolega Code:
1. Reads `SKILL.md` at project open.
2. Connects via SSE to port 3112.
3. Calls `initialize` → `tools/list` → ready to use all 40 tools.
4. The tools are available in Kolega Code's tool registry for any sub-agent.

**Step 3: Use Kolega Code for accounting**

Kolega Code sub-agents can be dispatched to:

- Create and manage chart of accounts
- Record expenses and income
- Import bank statements
- Reconcile transactions
- Generate invoices
- Preview and adjust VAT returns
- Run financial reports

---

### Example 4: Custom MCP Client (Python)

A minimal Python MCP client that connects to the gateway, lists tools, and calls one.

```python
"""
minimal_mcp_client.py — Minimal MCP SSE client for Agentic Accounting.

Demonstrates the full MCP lifecycle: connect → initialize → tools/list → tools/call.
"""

import json
import time
import requests

GATEWAY_URL = "http://localhost:3112"
MESSAGE_URL = f"{GATEWAY_URL}/message"


def rpc_call(method: str, params: dict | None = None, request_id: int = 1) -> dict:
    """Send a JSON-RPC 2.0 call to the MCP gateway and return the result."""
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params or {},
    }
    resp = requests.post(MESSAGE_URL, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"RPC error {data['error']['code']}: {data['error']['message']}")
    return data["result"]


def main():
    # 1. Health check
    health = requests.get(f"{GATEWAY_URL}/health", timeout=5)
    print(f"Health: {health.json()}")

    # 2. Initialize
    init_result = rpc_call("initialize", request_id=1)
    print(f"Server: {init_result['serverInfo']['name']} v{init_result['serverInfo']['version']}")
    print(f"Capabilities: {list(init_result['capabilities'].keys())}")

    # 3. List tools
    tools_result = rpc_call("tools/list", request_id=2)
    tools = tools_result["tools"]
    print(f"\nAvailable tools: {len(tools)}")
    for tool in tools[:5]:
        print(f"  • {tool['name']}: {tool['description'][:80]}...")
    print(f"  ... and {len(tools) - 5} more")

    # 4. Call a tool — list chart of accounts
    print("\nCalling coa.list...")
    coa_result = rpc_call("tools/call", params={
        "name": "coa.list",
        "arguments": {"include_inactive": False},
    }, request_id=3)
    
    content = coa_result["content"][0]["text"]
    accounts = json.loads(content)
    print(f"Chart of Accounts: {len(accounts)} accounts")
    for acct in accounts[:5]:
        print(f"  {acct['code']} — {acct['name']} ({acct['category']})")

    # 5. List resources
    resources_result = rpc_call("resources/list", request_id=4)
    resources = resources_result["resources"]
    print(f"\nResources: {len(resources)} available")
    for r in resources:
        print(f"  • {r['uri']}")


if __name__ == "__main__":
    main()
```

**Running the client:**

```bash
# Install requests if needed
pip install requests

# Run the client
python minimal_mcp_client.py
```

**Expected output:**

```
Health: {'status': 'ok'}
Server: agentic-accounting-mcp v0.1.0
Capabilities: ['tools', 'resources']

Available tools: 40
  • coa.list: Use when the user wants to see all accounts in their chart of accounts...
  • coa.add_account: Use when the user wants to create a new account in the chart of ...
  • coa.edit_account: Use when the user wants to update an existing account's name, co...
  • coa.set_vat_rate: Use when the user wants to change the default VAT rate on an acc...
  • gl.record_expense: Use when the user has paid for something and wants to record it...
  ... and 35 more

Calling coa.list...
Chart of Accounts: 25 accounts
  1000 — Current Account (Asset)
  1100 — Savings Account (Asset)
  4000 — Sales (Revenue)
  5000 — Office Expenses (Expense)
  5210 — Marketing (Expense)

Resources: 15 available
  • coa://templates/uk_sole_trader_no_vat
  • coa://templates/uk_sole_trader_vat
  ...
```

---

## Appendix A: Service Architecture

```
┌────────────────────────────────────────────────────────────┐
│                      Docker Network                         │
│                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  PostgreSQL  │  │    Redis 7   │  │  MinIO       │     │
│  │  16-alpine   │  │   (cache)    │  │  (storage)   │     │
│  │  :5432       │  │   :6379      │  │  :9000/:9001 │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │              │
│         └─────────────────┼─────────────────┘              │
│                           │                                │
│                    ┌──────┴───────┐                        │
│                    │  Formance    │                        │
│                    │  Ledger v2   │                        │
│                    └──────────────┘                        │
│                           │                                │
│         ┌─────────────────┼─────────────────┐              │
│         │                 │                 │              │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────┴───────┐     │
│  │ Accounting   │  │ MCP Gateway  │  │  Chat UI     │     │
│  │ API :8000    │◄─┤ :3112 (SSE)  │  │  :3000 (opt) │     │
│  │ (FastAPI)    │  │ (FastAPI)    │  │              │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                           │                                │
└───────────────────────────┼────────────────────────────────┘
                            │
                    ┌───────┴───────┐
                    │  AI Agent     │
                    │  (Claude,     │
                    │   OpenClaw,   │
                    │   Kolega)     │
                    └───────────────┘
```

## Appendix B: Environment Variables

| Variable | Default | Used By | Description |
|----------|---------|---------|-------------|
| `MCP_PORT` | `3112` | Gateway | Listen port for MCP gateway |
| `API_BASE_URL` | `http://accounting-api:8000` | Gateway | Accounting API URL (internal Docker) |
| `SKILL_REGISTRY_PATH` | `/app/skills/registry.yaml` | Gateway | Path to tool registry YAML |
| `MCP_TRANSPORT` | `sse` | Gateway | Transport method (SSE only in MVP) |
| `DB_USER` | `accounting` | API | PostgreSQL username |
| `DB_PASSWORD` | `accounting` | API | PostgreSQL password |
| `DB_NAME` | `accounting` | API | PostgreSQL database name |
| `DB_PORT` | `5432` | API | PostgreSQL port |
| `REDIS_PORT` | `6379` | API | Redis port |
| `MINIO_USER` | `minioadmin` | API + MinIO | MinIO access key |
| `MINIO_PASSWORD` | `minioadmin` | API + MinIO | MinIO secret key |
| `MINIO_PORT` | `9000` | MinIO | MinIO API port |
| `MINIO_CONSOLE_PORT` | `9001` | MinIO | MinIO web console port |
| `API_PORT` | `8000` | API | Accounting API port |
| `UI_PORT` | `3000` | Chat UI | Web chat interface port |
| `LOG_LEVEL` | `info` | API | Logging level |

## Appendix C: Quick Reference

### Start the system

```bash
cd agentic-accounting && docker compose up -d
```

### Stop the system

```bash
docker compose down
```

### Stop and delete all data

```bash
docker compose down -v
```

### Check all services are healthy

```bash
docker compose ps
```

### View gateway logs

```bash
docker compose logs -f mcp-gateway
```

### View API logs

```bash
docker compose logs -f accounting-api
```

### Test tools via curl

```bash
# Initialize
curl -s -X POST http://localhost:3112/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | jq .

# List all tools
curl -s -X POST http://localhost:3112/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | jq '.result.tools | length'

# Call a tool
curl -s -X POST http://localhost:3112/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"coa.list","arguments":{}}}' | jq .

# List resources
curl -s -X POST http://localhost:3112/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":4,"method":"resources/list","params":{}}' | jq .
```
