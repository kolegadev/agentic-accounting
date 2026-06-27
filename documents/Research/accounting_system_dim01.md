# Dimension 01: System Architecture & Technology Stack

## Headless LLM-Native Small Business Accounting System on Formance Ledger

**Version:** 1.0.0  
**Date:** 2025-07-10  
**Status:** Draft for Review

---

## Executive Summary

This document defines the complete technical architecture for a headless, LLM-native small business accounting system built on Formance Ledger. The system combines Formance's programmable financial ledger (MIT-licensed, ~1K tx/s per ledger, Numscript DSL) [^169^] with modern multi-agent LLM orchestration (supervisor pattern, SKILL.md-based skills) [^256^] [^269^], event-driven microservices, and cloud-native deployment patterns. The architecture targets small business accounting workloads (typically <10K transactions/month) with headroom to scale to mid-market (<1M transactions/month) via horizontal ledger segmentation.

The architecture is informed by primary research across 15+ authoritative sources, including official Formance documentation [^433^] [^498^] [^514^] [^524^], academic surveys on multi-agent orchestration [^269^], and fintech infrastructure best practices [^369^] [^418^].

---

## Table of Contents

1. [Service Topology](#1-service-topology)
2. [Data Flow Architecture](#2-data-flow-architecture)
3. [Database Strategy](#3-database-strategy)
4. [API Design](#4-api-design)
5. [Deployment Model](#5-deployment-model)
6. [SDK/Client Strategy](#6-sdkclient-strategy)
7. [Message Queue & Event Streaming](#7-message-queue--event-streaming)
8. [File Storage](#8-file-storage)
9. [Security Model](#9-security-model)
10. [Scalability Architecture](#10-scalability-architecture)

---

## 1. Service Topology

### 1.1 Architecture Overview

The system follows a **layered microservices architecture** with five distinct layers:

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Web App    │  │  Mobile App │  │  Third-Party Integ.     │  │
│  │  (React/Vue)│  │  (React Nat)│  │  (Accountants, Banks)   │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                  API GATEWAY LAYER                               │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Kong / Traefik API Gateway                      │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │ │
│  │  │  REST    │  │ WebSocket│  │  Auth    │  │ Rate Limit │  │ │
│  │  │  Router  │  │ Handler  │  │ (OAuth)  │  │ (Xero-like)│  │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
          │                │
          ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                 APPLICATION SERVICES LAYER                       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │  Agent       │ │  Accounting  │ │  Bank Feed /             │ │
│  │  Orchestrator│ │  Service     │ │  Reconciliation Service  │ │
│  │  (Supervisor)│ │  (REST API)  │ │  (Async Workers)         │ │
│  └──────┬───────┘ └──────┬───────┘ └────────────┬─────────────┘ │
│  ┌──────┴───────┐ ┌──────┴───────┐ ┌────────────┴─────────────┐ │
│  │  Skill       │ │  Reporting   │ │  Notification            │ │
│  │  Registry    │ │  Service     │ │  Service                 │ │
│  │  (SKILL.md)  │ │  (Async)     │ │  (Email/Push)            │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  CORE LEDGER LAYER                               │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Formance Ledger Cluster                         │ │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐    │ │
│  │  │ Ledger API │  │  Numscript │  │  Event Publisher   │    │ │
│  │  │  Server    │  │  Engine    │  │  (HTTP/Kafka)      │    │ │
│  │  └────────────┘  └────────────┘  └────────────────────┘    │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
          │                │
          ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│              DATA & INFRASTRUCTURE LAYER                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────┐  │
│  │PostgreSQL│ │  Redis   │ │  NATS/   │ │  MinIO (S3-Compat) │  │
│  │ (Primary)│ │  (Cache) │ │  Kafka   │ │  (File Storage)    │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Service Definitions

#### 1.2.1 API Gateway (`api-gateway`)

| Property | Value |
|----------|-------|
| **Technology** | Kong or Traefik |
| **Role** | Entry point for all client traffic; authentication termination; rate limiting; request routing |
| **Protocols** | HTTP/2 (REST), WebSocket |
| **Key Functions** | OAuth 2.0 token validation, Xero-like rate limiting (60 calls/min per tenant) [^260^], request routing, SSL termination, audit logging |

#### 1.2.2 Agent Orchestrator (`agent-orchestrator`)

| Property | Value |
|----------|-------|
| **Technology** | TypeScript/Node.js with LangGraph or custom supervisor implementation |
| **Role** | Central supervisor agent that receives natural language accounting requests, delegates to specialist agents, and synthesizes responses |
| **Pattern** | Hierarchical supervisor-worker (89% success rate with 4-8 specialists) [^255^] |
| **Key Functions** | Intent classification, agent delegation, context management, response synthesis, skill registry loading |

#### 1.2.3 Accounting Service (`accounting-service`)

| Property | Value |
|----------|-------|
| **Technology** | TypeScript/Node.js (NestJS) |
| **Role** | Core business logic for accounting operations; primary interface to Formance Ledger |
| **Key Functions** | Chart of accounts management, transaction CRUD, journal entries, balance queries, period closing, GST/VAT calculations |
| **Formance SDK** | `@formance/formance-sdk` (TypeScript) [^194^] |

#### 1.2.4 Bank Feed Service (`bank-feed-service`)

| Property | Value |
|----------|-------|
| **Technology** | TypeScript/Node.js + Python (for ML categorization) |
| **Role** | Async service for importing, categorizing, and reconciling bank transactions |
| **Key Functions** | OFX/CSV import, bank API integration (Open Banking), auto-categorization ML, reconciliation matching, feed scheduling |

#### 1.2.5 Reporting Service (`reporting-service`)

| Property | Value |
|----------|-------|
| **Technology** | TypeScript/Node.js + Python (Pandas/NumPy for calculations) |
| **Role** | Async report generation and financial analytics |
| **Key Functions** | P&L reports, Balance Sheet, Cash Flow, Aged Receivables/Payables, BAS/GST returns, custom report templates |

#### 1.2.6 Notification Service (`notification-service`)

| Property | Value |
|----------|-------|
| **Technology** | TypeScript/Node.js |
| **Role** | Multi-channel notification delivery |
| **Key Functions** | Email (SendGrid/AWS SES), push notifications, webhook delivery, in-app notifications, alert routing |

#### 1.2.7 Skill Registry (`skill-registry`)

| Property | Value |
|----------|-------|
| **Technology** | File-based (SKILL.md) + Vector store (PGVector or Pinecone) |
| **Role** | Stores and serves LLM agent skills in open SKILL.md format |
| **Format** | Anthropic AgentSkills spec (agentskills.io) [^258^] |
| **Key Functions** | Skill discovery, skill loading, version management, embedding-based retrieval |

### 1.3 Inter-Service Communication Matrix

| Source | Destination | Protocol | Pattern | Purpose |
|--------|-------------|----------|---------|---------|
| `api-gateway` | All services | HTTP/2 | Reverse proxy | Request routing |
| `api-gateway` | `agent-orchestrator` | WebSocket | Full-duplex | Chat streaming |
| `agent-orchestrator` | `accounting-service` | gRPC | Request/response | Ledger operations |
| `agent-orchestrator` | `skill-registry` | gRPC | Request/response | Skill loading |
| `accounting-service` | Formance Ledger | HTTP/REST | Request/response | Transaction posting |
| `bank-feed-service` | Formance Ledger | HTTP/REST | Async batch | Bulk transaction import |
| `bank-feed-service` | `accounting-service` | gRPC | Request/response | Reconciliation |
| `reporting-service` | Formance Ledger | HTTP/REST | Query | Data retrieval |
| All services | NATS/Kafka | NATS Protocol | Pub/Sub | Event streaming |
| All services | Redis | Redis Protocol | Cache/Queue | Session/state caching |

### 1.4 Communication Patterns

**External (Client-Facing):**
- **REST API** (`/api/v1/*`): All CRUD operations for accounting entities
- **WebSocket** (`/ws/chat`): LLM chat interface with streaming responses [^400^]
- **Webhooks** (`/webhooks/*`): Async notifications to external systems

**Internal (Service-to-Service):**
- **gRPC**: Synchronous calls between application services (3-4x faster than REST, binary Protocol Buffers, type-safe) [^272^] [^273^]
- **NATS**: Asynchronous event streaming (sub-millisecond latency, millions of messages/sec) [^376^]
- **REST**: Calls to Formance Ledger via official SDK

---

## 2. Data Flow Architecture

### 2.1 Primary Flow: Chat-Based Transaction Entry

```
User: "Record a $500 payment from Acme Corp for Invoice INV-001"

  │
  ▼
┌────────────────────────────────────────────────────────────────┐
│  STEP 1: WebSocket Connection                                  │
│  Client ──WebSocket──▶ API Gateway ──WebSocket──▶ Agent        │
│  Connection established with JWT auth                          │
│  (OAuth 2.0 access token validated at gateway) [^391^]         │
└────────────────────────────────────────────────────────────────┘
  │
  ▼
┌────────────────────────────────────────────────────────────────┐
│  STEP 2: Intent Classification (Supervisor Agent)               │
│  Agent Orchestrator receives message                            │
│  ├── LLM call: classify intent → "create_transaction"           │
│  ├── Extract entities: {amount: 50000, currency: "USD/2",       │
│  │                      customer: "acme_corp",                  │
│  │                      invoice: "INV-001"}                     │
│  └── Load relevant SKILL.md: "transaction-entry"                │
│      (from skill-registry, loaded via vector search) [^256^]    │
└────────────────────────────────────────────────────────────────┘
  │
  ▼
┌────────────────────────────────────────────────────────────────┐
│  STEP 3: Skill Execution (Specialist Agent)                     │
│  Supervisor delegates to Transaction Specialist Agent           │
│  ├── Load Numscript template from SKILL.md                      │
│  │   (Declarative: "send [USD/2 {amount}] from @ar:acme_corp   │
│  │    to @bank:checking with reference {invoice}") [^229^]      │
│  ├── Validate: Check Acme Corp receivable balance ≥ $500        │
│  ├── Resolve: Map "Acme Corp" → account "acme_corp"             │
│  └── Prepare: Build Formance transaction payload                  │
└────────────────────────────────────────────────────────────────┘
  │
  ▼
┌────────────────────────────────────────────────────────────────┐
│  STEP 4: Ledger Write                                           │
│  accounting-service ──gRPC──▶ Formance Ledger API               │
│  POST /api/ledger/v2/{ledger}/transactions                      │
│  {                                                               │
│    "postings": [{                                                │
│      "source": "ar:acme_corp",                                   │
│      "destination": "bank:checking",                             │
│      "amount": 50000,  // $500.00 in cents                       │
│      "asset": "USD/2"                                            │
│    }],                                                           │
│    "metadata": {                                                 │
│      "invoice_ref": "INV-001",                                   │
│      "description": "Payment from Acme Corp",                    │
│      "entered_via": "llm_chat"                                   │
│    }                                                             │
│  }                                                               │
│  [Formance v2 API via TypeScript SDK] [^197^]                    │
└────────────────────────────────────────────────────────────────┘
  │
  ▼
┌────────────────────────────────────────────────────────────────┐
│  STEP 5: Event Propagation                                      │
│  Formance Ledger emits COMMITTED_TRANSACTIONS event [^524^]      │
│  │                                                                │
│  ├──▶ NATS: "ledger.transactions.committed"                     │
│  │    ├── bank-feed-service: Mark feed item as reconciled         │
│  │    ├── reporting-service: Invalidate cached reports            │
│  │    └── notification-service: "Payment recorded: $500"          │
│  │                                                                │
│  └──▶ WebSocket: Push update to client                           │
│       "✅ Payment recorded. Acme Corp balance: $0.00"            │
└────────────────────────────────────────────────────────────────┘
  │
  ▼
┌────────────────────────────────────────────────────────────────┐
│  STEP 6: Response Streaming (WebSocket)                         │
│  Agent Orchestrator ──WebSocket──▶ Client                       │
│  Streaming response:                                            │
│  "I've recorded the $500 payment from Acme Corp against          │
│   Invoice INV-001. The accounts receivable balance for           │
│   Acme Corp is now $0.00. Would you like me to send a           │
│   payment receipt?"                                              │
└────────────────────────────────────────────────────────────────┘
```

### 2.2 Secondary Flow: Bank Feed Processing (Async)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Scheduler  │     │  Bank Feed   │     │  Categorize  │     │  Formance    │
│   (Cron/     │────▶│  Importer    │────▶│  + Match     │────▶│  Ledger      │
│    Temporal) │     │  (Python)    │     │  (ML+Rules)  │     │  Write       │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                              │
                                                              ▼
                                                       ┌──────────────┐
                                                       │  Reconcile   │
                                                       │  Matched tx  │
                                                       └──────────────┘
                                                              │
                                                              ▼
                                                       ┌──────────────┐
                                                       │  Emit Events │
                                                       │  (NATS)      │
                                                       └──────────────┘
```

Bank feed processing runs as a **Temporal workflow** [^418^] for durability:
1. Scheduled trigger (every 4 hours or on-demand)
2. Fetch transactions from bank API (Open Banking/OFX)
3. Categorize using ML model (Python/scikit-learn)
4. Match against existing ledger transactions
5. Post unmatched items as new transactions to Formance
6. Emit reconciliation events

### 2.3 Tertiary Flow: Report Generation (Async)

```
User: "Generate my P&L for last quarter"

  │
  ▼
Agent Orchestrator ──▶ reporting-service (gRPC)
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ reporting-service                                             │
│ ├── Validate permissions (RBAC)                               │
│ ├── Enqueue report job (NATS JetStream)                       │
│ ├── Worker picks up job                                       │
│ ├── Query Formance Ledger: GET /v2/{ledger}/transactions      │
│ │   (with date filter, aggregated balances)                   │
│ ├── Calculate P&L in Python (Pandas)                          │
│ ├── Generate PDF/Excel output                                 │
│ ├── Store in MinIO (S3-compatible)                            │
│ └── Emit: "report.completed" event                            │
│                                                               │
│ notification-service ──▶ Email with download link               │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Database Strategy

### 3.1 Data Stores Overview

| Store | Technology | Purpose | Persistence |
|-------|-----------|---------|-------------|
| **Primary Ledger** | PostgreSQL 16+ | Formance Ledger transactional data | Persistent (SSD/NVMe) |
| **Application DB** | PostgreSQL 16+ | Accounting metadata, users, orgs, settings | Persistent (SSD/NVMe) |
| **Cache** | Redis 7+ | Session store, rate limiting, query cache, pub/sub | Ephemeral + AOF |
| **Vector Store** | PGVector (PostgreSQL extension) | Skill embeddings, document search | Persistent |
| **Object Store** | MinIO | Receipts, invoices, reports, attachments | Persistent (erasure coding) |

### 3.2 PostgreSQL for Formance Ledger

Formance Ledger uses PostgreSQL as its **main transactional storage layer** [^169^]. Each ledger is stored within a PostgreSQL schema (bucket), providing namespace isolation [^498^].

**Key characteristics:**
- **Write throughput**: ~1,000 transactions/second per ledger on commodity hardware [^433^]
- **Row locking**: Locks applied per `(account, asset)` pair; high concurrency on a single source account serializes transactions [^433^]
- **Bucketing**: Each bucket maps to a PostgreSQL schema, enabling per-tenant data isolation [^498^]
- **Transaction cost**: O(N) + W where N = number of source accounts read, W = write overhead [^514^]

**Performance optimizations for our use case:**

```sql
-- Strategy 1: Multiple source accounts to reduce contention
-- Instead of always using @world, use @world:<pool_id>
-- Pool size: ~20 accounts for small business workloads

-- Strategy 2: Async log hashing for higher throughput
-- Trade-off: Lose cryptographic proof of log immutability
-- Acceptable for small business tier; required for enterprise
```

### 3.3 PostgreSQL for Application Metadata

Separate database instance (or separate schema on same cluster for small deployments) storing:

```
app_db schema:
├── organizations        -- Multi-tenant org records
├── users                -- User accounts (linked to org)
├── organization_members -- Org membership + RBAC roles
├── chart_of_accounts    -- Custom COA definitions
├── bank_connections     -- Open Banking credentials (encrypted)
├── rules                -- Auto-categorization rules
├── report_templates     -- Saved report configurations
├── audit_log            -- All admin/operator actions
└── webhooks             -- Configured webhook endpoints
```

### 3.4 Redis Caching Strategy

| Cache Type | Key Pattern | TTL | Purpose |
|------------|-------------|-----|---------|
| **Session** | `session:{jwt_sub}` | 24h | WebSocket session state |
| **Rate Limit** | `rl:{org_id}:{endpoint}` | 1min | Per-tenant rate limiting (60/min) |
| **Balance** | `bal:{ledger}:{account}:{asset}` | 30s | Cached account balances |
| **Chart of Accounts** | `coa:{org_id}` | 1h | Chart of accounts structure |
| **Ledger Info** | `ledger:{ledger_id}` | 5min | Ledger metadata |
| **Report** | `report:{hash}` | 1h | Cached report outputs |

### 3.5 PGVector for Skill Embeddings

Skills stored as vector embeddings for semantic retrieval:

```sql
-- Skill embedding table
CREATE TABLE skill_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_name TEXT NOT NULL,
    description TEXT NOT NULL,
    embedding VECTOR(1536),  -- OpenAI text-embedding-3-small
    skill_path TEXT NOT NULL,  -- Path to SKILL.md file
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW index for fast similarity search
CREATE INDEX idx_skill_embeddings_hnsw 
ON skill_embeddings 
USING hnsw (embedding vector_cosine_ops);
```

---

## 4. API Design

### 4.1 External API: REST + WebSocket

#### 4.1.1 REST API (Xero-Inspired Design)

Following Xero's API-first design patterns [^260^] with these characteristics:

| Aspect | Specification |
|--------|--------------|
| **Base URL** | `https://api.ledger accounting.io/v1` |
| **Authentication** | OAuth 2.0 + PKCE (RFC 9700) [^391^] |
| **Rate Limiting** | 60 calls/min per tenant (Xero benchmark) [^260^] |
| **Content-Type** | `application/json` |
| **Pagination** | Cursor-based (`?cursor=xxx&limit=100`) |
| **BigInt Handling** | `X-Bigint-As-String: true` header (Formance pattern) [^514^] |
| **Idempotency** | `Idempotency-Key: {uuid}` header for all POST/PUT |

**Endpoint Groups:**

```
/api/v1/
├── /auth                 # OAuth 2.0 flows
│   ├── POST /token
│   └── POST /refresh
│
├── /organizations        # Multi-tenant org management
│   ├── GET    /          # List orgs
│   ├── POST   /          # Create org
│   ├── GET    /:id       # Get org
│   └── PATCH  /:id       # Update org
│
├── /ledger               # Core ledger operations
│   ├── GET    /transactions           # List transactions
│   ├── POST   /transactions           # Create transaction
│   ├── GET    /transactions/:id       # Get transaction
│   ├── POST   /transactions/:id/revert # Revert transaction
│   ├── GET    /accounts               # List accounts
│   ├── GET    /accounts/:id           # Get account + balance
│   ├── GET    /balances/aggregated    # Aggregated balances
│   └── POST   /bulk                   # Bulk operations [^188^]
│
├── /chat                 # LLM chat interface
│   ├── WS     /stream    # WebSocket streaming endpoint
│   └── GET    /history   # Chat history
│
├── /bank-feeds           # Bank integration
│   ├── GET    /connections           # List bank connections
│   ├── POST   /connections           # Connect bank
│   ├── GET    /transactions          # List feed transactions
│   ├── POST   /import                # Manual import (CSV/OFX)
│   └── POST   /:id/reconcile         # Trigger reconciliation
│
├── /reports              # Reporting
│   ├── GET    /templates             # List report templates
│   ├── POST   /generate              # Generate report (async)
│   ├── GET    /:id/status            # Check generation status
│   └── GET    /:id/download          # Download completed report
│
├── /contacts             # Customers/Suppliers
│   ├── GET    /          # List contacts
│   ├── POST   /          # Create contact
│   ├── GET    /:id       # Get contact
│   └── GET    /:id/transactions      # Contact transaction history
│
├── /webhooks             # Webhook management
│   ├── GET    /          # List webhooks
│   ├── POST   /          # Register webhook
│   └── DELETE /:id       # Remove webhook
│
└── /documents            # File attachments
    ├── POST   /upload    # Upload file
    ├── GET    /:id       # Get file metadata
    └── GET    /:id/download  # Download file
```

#### 4.1.2 WebSocket API (Chat Streaming)

```javascript
// Connection
const ws = new WebSocket('wss://api.ledgeraccounting.io/v1/chat/stream');
ws.onopen = () => {
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'eyJhbGciOiJSUzI1NiIs...'  // OAuth access token
  }));
};

// Client → Server
ws.send(JSON.stringify({
  type: 'message',
  id: 'msg_abc123',
  content: 'Record a $500 payment from Acme Corp',
  context: {
    ledger: 'org_123_main',
    current_view: 'accounts_receivable',
    selected_account: 'ar:acme_corp'
  }
}));

// Server → Client (streaming)
// Response 1: Status
{ "type": "status", "message": "Processing...", "agent": "transaction-specialist" }

// Response 2: Thinking/Reasoning
{ "type": "thought", "content": "User wants to record payment..." }

// Response 3: Confirmation (if needed)
{ "type": "confirm", "message": "Record $500 payment from Acme Corp?", "action_id": "act_456" }

// Response 4: Result
{ "type": "result", "content": "✅ Payment recorded...", "transaction_id": "tx_789" }

// Response 5: Follow-up suggestion
{ "type": "suggestion", "content": "Would you like to send a receipt?" }
```

### 4.2 Internal API: gRPC

```protobuf
// accounting_service.proto
syntax = "proto3";

service AccountingService {
  // Transactions
  rpc CreateTransaction(CreateTransactionReq) returns (Transaction);
  rpc GetTransaction(GetTransactionReq) returns (Transaction);
  rpc ListTransactions(ListTransactionsReq) returns (TransactionList);
  rpc RevertTransaction(RevertTransactionReq) returns (Transaction);
  rpc CreateBulk(BulkRequest) returns (BulkResponse);

  // Accounts
  rpc GetAccount(GetAccountReq) returns (Account);
  rpc ListAccounts(ListAccountsReq) returns (AccountList);
  rpc GetBalance(GetBalanceReq) returns (Balance);

  // Chart of Accounts
  rpc GetChartOfAccounts(GetCOAReq) returns (ChartOfAccounts);
  rpc UpdateChartOfAccounts(UpdateCOAReq) returns (ChartOfAccounts);
}

service AgentService {
  rpc ExecuteSkill(ExecuteSkillReq) returns (stream SkillOutput);
  rpc GetAvailableSkills(GetSkillsReq) returns (SkillList);
  rpc LoadSkillContext(LoadContextReq) returns (ContextLoaded);
}

service BankFeedService {
  rpc ImportTransactions(ImportReq) returns (ImportJob);
  rpc GetImportStatus(GetImportStatusReq) returns (ImportStatus);
  rpc TriggerReconciliation(ReconcileReq) returns (ReconciliationJob);
  rpc GetReconciliationStatus(GetReconcileStatusReq) returns (ReconciliationStatus);
}

service ReportService {
  rpc GenerateReport(GenerateReportReq) returns (ReportJob);
  rpc GetReportStatus(GetReportStatusReq) returns (ReportStatus);
  rpc GetReportDownloadUrl(GetDownloadReq) returns (DownloadUrl);
}
```

### 4.3 Formance Ledger API Integration

The system communicates with Formance Ledger via its **official TypeScript SDK** (`@formance/formance-sdk`) [^194^] [^423^], which wraps the REST API v2:

```typescript
import { Formance } from "@formance/formance-sdk";

const formance = new Formance({
  serverURL: process.env.FORMANCE_API_URL,
  security: {
    clientID: process.env.FORMANCE_CLIENT_ID,
    clientSecret: process.env.FORMANCE_CLIENT_SECRET,
  },
});

// Create a transaction
const result = await formance.ledger.v2.createTransaction({
  ledger: "org_123_main",  // Per-tenant ledger
  v2PostTransaction: {
    postings: [{
      amount: BigInt(50000),  // $500.00 in cents
      asset: "USD/2",
      source: "ar:acme_corp",
      destination: "bank:checking",
    }],
    metadata: {
      invoice_ref: "INV-001",
      description: "Payment from Acme Corp",
      entered_via: "llm_chat",
    },
  },
});
```

**Key Formance v2 API endpoints used:** [^197^] [^188^]

| Operation | SDK Method | Formance Endpoint |
|-----------|-----------|-------------------|
| Create transaction | `ledger.v2.createTransaction()` | `POST /v2/{ledger}/transactions` |
| Create bulk | `ledger.v2.createBulk()` | `POST /v2/{ledger}/bulk` |
| List transactions | `ledger.v2.listTransactions()` | `GET /v2/{ledger}/transactions` |
| Get transaction | `ledger.v2.getTransaction()` | `GET /v2/{ledger}/transactions/{id}` |
| Revert transaction | `ledger.v2.revertTransaction()` | `POST /v2/{ledger}/transactions/{id}/revert` |
| List accounts | `ledger.v2.listAccounts()` | `GET /v2/{ledger}/accounts` |
| Get account | `ledger.v2.getAccount()` | `GET /v2/{ledger}/accounts/{id}` |
| Get balances | `ledger.v2.getBalancesAggregated()` | `GET /v2/{ledger}/balances-aggregated` |
| Add metadata | `ledger.v2.addMetadataToAccount()` | `POST /v2/{ledger}/accounts/{id}/metadata` |
| Create ledger | `ledger.v2.createLedger()` | `POST /v2/_/ledgers` |
| Get ledger info | `ledger.v2.getLedgerInfo()` | `GET /v2/{ledger}/info` |
| Read stats | `ledger.v2.readStats()` | `GET /v2/{ledger}/stats` |

---

## 5. Deployment Model

### 5.1 Development Environment: Docker Compose

For local development, a single Docker Compose file brings up the entire stack:

```yaml
# docker-compose.dev.yml
version: "3.9"

services:
  # ─── API Gateway ───
  gateway:
    image: traefik:v3.1
    ports:
      - "80:80"
      - "8080:8080"  # Dashboard
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command:
      - --api.insecure=true
      - --providers.docker=true
      - --entrypoints.web.address=:80

  # ─── Application Services ───
  agent-orchestrator:
    build: ./services/agent-orchestrator
    environment:
      - REDIS_URL=redis://redis:6379
      - NATS_URL=nats://nats:4222
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SKILL_REGISTRY_PATH=/skills
    volumes:
      - ./skills:/skills:ro
    labels:
      - "traefik.http.routers.agent.rule=PathPrefix(`/v1/chat`)"

  accounting-service:
    build: ./services/accounting-service
    environment:
      - DATABASE_URL=postgresql://app:app@app-db:5432/accounting
      - FORMANCE_API_URL=http://formance-ledger:3068
      - FORMANCE_CLIENT_ID=dev-client
      - FORMANCE_CLIENT_SECRET=dev-secret
      - REDIS_URL=redis://redis:6379
      - NATS_URL=nats://nats:4222
    labels:
      - "traefik.http.routers.accounting.rule=PathPrefix(`/v1/ledger`,`/v1/accounts`,`/v1/contacts`)"

  bank-feed-service:
    build: ./services/bank-feed-service
    environment:
      - DATABASE_URL=postgresql://app:app@app-db:5432/accounting
      - FORMANCE_API_URL=http://formance-ledger:3068
      - NATS_URL=nats://nats:4222
    # No traefik routing - internal service only

  reporting-service:
    build: ./services/reporting-service
    environment:
      - DATABASE_URL=postgresql://app:app@app-db:5432/accounting
      - FORMANCE_API_URL=http://formance-ledger:3068
      - MINIO_ENDPOINT=minio:9000
      - NATS_URL=nats://nats:4222
    # No traefik routing - internal service only

  notification-service:
    build: ./services/notification-service
    environment:
      - DATABASE_URL=postgresql://app:app@app-db:5432/accounting
      - NATS_URL=nats://nats:4222
      - SMTP_HOST=${SMTP_HOST}

  # ─── Formance Ledger (Single Instance) ───
  formance-ledger:
    image: ghcr.io/formancehq/ledger:v2.x
    environment:
      - NUMARY_STORAGE_DRIVER=postgres
      - NUMARY_STORAGE_POSTGRES_CONN_STRING=postgresql://formance:formance@ledger-db:5432/formance
      - NUMARY_SERVER_HTTP_BIND_ADDRESS=0.0.0.0:3068
      - NUMARY_AUTH_BASIC_ENABLED=true
      - NUMARY_AUTH_BASIC_CREDENTIALS=dev:dev
      - PUBLISHER_HTTP_ENABLED=true
      - PUBLISHER_TOPIC_MAPPING=*=nats://nats:4222
    depends_on:
      - ledger-db
    labels:
      - "traefik.http.routers.ledger.rule=PathPrefix(`/api/ledger`)"

  # ─── Core Infrastructure ───
  app-db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=app
      - POSTGRES_PASSWORD=app
      - POSTGRES_DB=accounting
    volumes:
      - app-db-data:/var/lib/postgresql/data

  ledger-db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=formance
      - POSTGRES_PASSWORD=formance
      - POSTGRES_DB=formance
    volumes:
      - ledger-db-data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

  nats:
    image: nats:2.10-alpine
    command: "-js"  # Enable JetStream
    volumes:
      - nats-data:/data/jetstream

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    ports:
      - "9000:9000"   # S3 API
      - "9001:9001"   # Console
    volumes:
      - minio-data:/data

volumes:
  app-db-data:
  ledger-db-data:
  redis-data:
  nats-data:
  minio-data:
```

**Start command:**
```bash
docker compose -f docker-compose.dev.yml up -d
```

### 5.2 Production Environment: Kubernetes

Formance Ledger's **production deployment is officially supported only through the k8s operator** [^169^] [^424^]. The full production architecture uses the Formance Operator for ledger management plus custom application services.

```yaml
# Simplified production k8s architecture
#
# Namespace: ledger-accounting-prod
#
# ┌──────────────────────────────────────────────────────────────┐
# │  Ingress (Cloud LB + cert-manager)                            │
# │  ├── api.ledgeraccounting.io        → api-gateway            │
# │  └── ws.ledgeraccounting.io         → agent-orchestrator WS   │
# └──────────────────────────────────────────────────────────────┘
#                           │
#                    ┌──────┴──────┐
#                    ▼             ▼
#              ┌─────────┐   ┌──────────┐
#              │ API GW  │   │  WS GW   │
#              │ (Kong)  │   │(custom)  │
#              └───┬─────┘   └────┬─────┘
#                  │              │
#      ┌───────────┼──────────────┼───────────┐
#      ▼           ▼              ▼           ▼
# ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐
# │Accounting│ │BankFeed │ │Reporting │ │Notify    │
# │Service   │ │Service  │ │Service   │ │Service   │
# │(3 repl.) │ │(2 repl.)│ │(2 repl.) │ │(2 repl.) │
# └─────────┘ └─────────┘ └──────────┘ └──────────┘
#      │           │            │            │
#      └───────────┴─────┬──────┴────────────┘
#                        ▼
#              ┌─────────────────────┐
#              │   NATS Cluster      │
#              │   (3-node JetStream)│
#              └─────────────────────┘
#                        │
#      ┌─────────────────┼─────────────────┐
#      ▼                 ▼                 ▼
# ┌──────────┐   ┌──────────────┐   ┌──────────┐
# │Formance  │   │  PostgreSQL  │   │  Redis   │
# │Operator  │   │  HA Cluster  │   │ Cluster  │
# │(managed) │   │  (Patroni)   │   │ (6-node) │
# └──────────┘   └──────────────┘   └──────────┘
#                        │
#                        ▼
#               ┌──────────────┐
#               │    MinIO     │
#               │  (Distributed│
#               │   4+ nodes)  │
#               └──────────────┘
```

**Production components:**

| Component | Replicas | Resource Class | Notes |
|-----------|----------|----------------|-------|
| API Gateway (Kong) | 2 | Medium | SSL termination, rate limiting |
| Agent Orchestrator | 3 | Large | LLM calls are memory-intensive |
| Accounting Service | 3 | Medium | CPU-bound for Numscript validation |
| Bank Feed Service | 2 | Medium-Large | Python ML component |
| Reporting Service | 2 | Medium | Async workers |
| Notification Service | 2 | Small | Lightweight |
| Formance Ledger | 2 | Medium | HA via operator |
| PostgreSQL | 3 (1 primary + 2 replicas) | Large | Patroni HA |
| Redis | 6 (3 master + 3 replica) | Small | Cluster mode |
| NATS | 3 | Medium | JetStream enabled |
| MinIO | 4 | Large | Distributed mode, erasure coding |

---

## 6. SDK/Client Strategy

### 6.1 Server-Side SDK Usage

| Service | Language | Formance SDK | Purpose |
|---------|----------|-------------|---------|
| `accounting-service` | TypeScript/Node.js | `@formance/formance-sdk` | Ledger operations |
| `bank-feed-service` | TypeScript/Node.js | `@formance/formance-sdk` | Transaction posting |
| `reporting-service` | TypeScript/Node.js | `@formance/formance-sdk` | Data queries |
| `agent-orchestrator` | TypeScript/Node.js | `@formance/formance-sdk` | Skill validation |
| `bank-feed-ml` | Python | `formance-sdk-python` | ML categorization + ledger ops |

**Formance SDK Coverage** [^194^]:
- Go: `github.com/formancehq/formance-sdk-go/v3`
- TypeScript: `@formance/formance-sdk`
- Python: `formance-sdk-python`
- Java: `com.formance:formance-sdk`
- C#: `FormanceSDK`
- PHP: `formance/formance-sdk`

Formance uses **Speakeasy** for automated SDK generation, maintaining 6 languages with CI/CD integration [^254^].

### 6.2 Client SDKs (for Third-Party Integrations)

| Platform | Package | Auth |
|----------|---------|------|
| TypeScript/JavaScript | `@ledgeraccounting/sdk` | OAuth 2.0 PKCE |
| Python | `ledgeraccounting-sdk` | OAuth 2.0 |
| Go | `github.com/ledgeraccounting/sdk-go` | OAuth 2.0 |

### 6.3 Language Strategy Summary

| Layer | Primary Language | Secondary |
|-------|-----------------|-----------|
| API Gateway | Lua (Kong plugins) | - |
| Application Services | TypeScript/Node.js | - |
| ML/Categorization | Python | - |
| Infrastructure Config | YAML/Helm | HCL (Terraform) |
| Client SDKs | TypeScript, Python, Go | - |
| Ledger DSL | Numscript | - |

---

## 7. Message Queue & Event Streaming

### 7.1 Technology Selection: NATS + JetStream

**NATS** is selected as the primary message broker for its lightweight footprint, performance characteristics, and suitability for our scale [^376^] [^373^]:

| Characteristic | NATS | Kafka |
|---------------|------|-------|
| **Throughput** | Millions msg/sec | 100K-1M+ msg/sec |
| **Latency** | Sub-millisecond | 10-100ms typical |
| **Footprint** | Single binary, ~20MB | JVM-based, complex cluster |
| **Complexity** | Low | High |
| **Persistence** | JetStream add-on | Native (core feature) |
| **Exactly-Once** | Supported (JetStream) | Native |
| **Our Use Case** | Perfect fit (<10K tx/month/tenant) | Overkill for initial scale |
| **Resource Usage** | Minimal | Significant |

**Decision:** NATS with JetStream for persistence. Kafka can be adopted later if volume exceeds NATS comfortable limits (which is unlikely for small business accounting).

### 7.2 Topic Design

```
ledger.{tenant_id}.transactions.created     # New transaction posted
ledger.{tenant_id}.transactions.reverted    # Transaction reverted
ledger.{tenant_id}.accounts.balance.changed  # Balance update
ledger.{tenant_id}.metadata.changed          # Metadata update

bankfeed.{tenant_id}.import.started         # Import job started
bankfeed.{tenant_id}.import.completed       # Import job done
bankfeed.{tenant_id}.transaction.matched    # Reconciliation match
bankfeed.{tenant_id}.transaction.unmatched  # Needs manual review

reports.{tenant_id}.generation.requested    # Report generation request
reports.{tenant_id}.generation.completed    # Report ready
reports.{tenant_id}.generation.failed       # Report failed

notifications.{tenant_id}.email             # Email notification
notifications.{tenant_id}.push              # Push notification
notifications.{tenant_id}.webhook           # Webhook delivery

agents.{tenant_id}.skill.executed          # Skill execution log
agents.{tenant_id}.conversation.turn       # Conversation turn
```

### 7.3 Formance Event Integration

Formance Ledger emits events that are captured and forwarded to NATS:

| Formance Event | NATS Topic | Consumer Action |
|---------------|------------|-----------------|
| `COMMITTED_TRANSACTIONS` | `ledger.{id}.transactions.created` | Update caches, notify users |
| `REVERTED_TRANSACTION` | `ledger.{id}.transactions.reverted` | Reverse downstream effects |
| `SAVED_METADATA` | `ledger.{id}.metadata.changed` | Sync metadata to app DB |
| `DELETED_METADATA` | `ledger.{id}.metadata.changed` | Sync metadata to app DB |

**Formance event configuration:** [^524^]
```bash
# Enable HTTP publisher to push to NATS
PUBLISHER_HTTP_ENABLED=true
PUBLISHER_TOPIC_MAPPING=*=http://nats-bridge:8080/publish
```

Alternatively, use Formance's **data streaming** feature with a custom exporter [^278^]:
```bash
# Create exporter pointing to NATS
curl -X POST $FORMANCE_API_URL/api/ledger/v2/_/exporters \
  -H "Content-Type: application/json" \
  -d '{
    "driver": "http",
    "config": {
      "endpoint": "http://nats-bridge:8080/webhook",
      "format": "nats"
    }
  }'
```

### 7.4 Async Processing Patterns

**Bank Feed Import (Durable Workflow):**
```
NATS JetStream Consumer Group: "bank-feed-workers"
- Durable subscription with ack-based delivery
- Max deliver: 3 (with exponential backoff)
- Message TTL: 24 hours
- Concurrency: 2 workers per instance
```

**Report Generation (Job Queue):**
```
NATS JetStream Consumer Group: "report-workers"
- Pull-based consumer
- Max in-flight: 1 per worker (reports are CPU-intensive)
- Ack wait: 5 minutes
```

---

## 8. File Storage

### 8.1 Technology: MinIO (S3-Compatible)

MinIO provides a self-hosted, S3-compatible object storage layer [^393^] [^395^]:

| Property | Configuration |
|----------|--------------|
| **Technology** | MinIO (distributed mode, 4+ nodes) |
| **API** | S3-compatible (AWS SDKs work without changes) |
| **Protocols** | S3 API (HTTP/HTTPS), console UI |
| **Data Protection** | Erasure coding (tolerates up to N/2 drive failures) |
| **Bucket Structure** | Per-tenant buckets |

### 8.2 Bucket Organization

```
receipts-{tenant_id}/          # Expense receipts (images/PDFs)
  ├── 2024/01/{uuid}.jpg
  ├── 2024/01/{uuid}.pdf
  └── ...

invoices-{tenant_id}/          # Generated invoice PDFs
  ├── outgoing/
  └── incoming/

reports-{tenant_id}/           # Generated reports
  ├── profit-loss/
  ├── balance-sheet/
  └── tax-returns/

attachments-{tenant_id}/       # General file attachments
  └── ...

exports-{tenant_id}/           # Data exports (CSV, OFX)
  └── ...
```

### 8.3 File Upload Flow

```
Client → POST /v1/documents/upload (multipart/form-data)
  │
  ▼
api-gateway → accounting-service
  │
  ▼
┌─────────────────────────────────────────────────────┐
│ 1. Validate file (type, size ≤ 10MB)                │
│ 2. Scan for malware (ClamAV integration)             │
│ 3. Generate presigned MinIO URL                      │
│ 4. Client uploads directly to MinIO                  │
│ 5. Store metadata in app DB (filename, path, mime)   │
│ 6. Emit "document.uploaded" event                    │
│ 7. OCR service (optional) processes image → text     │
└─────────────────────────────────────────────────────┘
```

---

## 9. Security Model

### 9.1 Authentication: OAuth 2.0 + PKCE

Following RFC 9700 (OAuth 2.0 Security Best Current Practice) [^391^] and Xero's pattern [^260^]:

| Aspect | Implementation |
|--------|---------------|
| **Flow** | Authorization Code + PKCE (S256) for all clients |
| **Token Type** | JWT access tokens (RS256 signed, 30-min expiry) |
| **Refresh Tokens** | Rotating refresh tokens (60-day expiry) |
| **Storage** | HTTP-only, Secure, SameSite=Strict cookies (web); Keychain (mobile) |
| **mTLS** | Optional for server-to-server integrations |

**Token claims:**
```json
{
  "sub": "user_uuid",
  "org": "organization_uuid",
  "roles": ["admin"],
  "scope": "ledger:read ledger:write contacts:read reports:read",
  "iat": 1720600000,
  "exp": 1720601800,
  "iss": "https://auth.ledgeraccounting.io"
}
```

### 9.2 Authorization: RBAC

| Role | Permissions |
|------|------------|
| **Owner** | Full access to all resources |
| **Admin** | All except billing/org deletion |
| **Bookkeeper** | Ledger read/write, contacts, reports, no settings |
| **Accountant** | Read-only access + reports, no ledger writes |
| **Viewer** | Read-only across all resources |

**Implementation:** RBAC middleware in `accounting-service` checks `roles` claim against required permissions for each endpoint.

### 9.3 Data Encryption

| Layer | Method |
|-------|--------|
| **In Transit** | TLS 1.3 for all external traffic; mTLS for internal gRPC |
| **At Rest (DB)** | PostgreSQL TDE (Transparent Data Encryption) or filesystem-level encryption (LUKS) |
| **At Rest (Files)** | MinIO server-side encryption (AES-256) |
| **At Rest (Secrets)** | HashiCorp Vault or Kubernetes secrets + sealed secrets |
| **Sensitive Fields** | Application-level AES-256-GCM for bank credentials, tax IDs |

### 9.4 Multi-Tenant Data Isolation

| Isolation Level | Mechanism |
|-----------------|-----------|
| **Ledger Data** | Per-tenant Formance ledgers + PostgreSQL schema buckets [^498^] |
| **Application Data** | `organization_id` column on all tables, enforced by RLS policies |
| **File Storage** | Per-tenant MinIO buckets |
| **Cache** | Key prefixing: `{org_id}:{resource}` |
| **Events** | Topic namespacing: `{resource}.{org_id}.{event}` |

### 9.5 Audit Logging

All operations logged to the `audit_log` table and forwarded to a tamper-evident store:

```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    user_id UUID,
    action TEXT NOT NULL,        -- CREATE, READ, UPDATE, DELETE, LOGIN
    resource_type TEXT NOT NULL, -- transaction, account, contact, etc.
    resource_id TEXT,
    details JSONB,               -- Before/after values
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    session_id TEXT
);

-- Index for efficient querying
CREATE INDEX idx_audit_org_time ON audit_log(organization_id, timestamp DESC);
```

---

## 10. Scalability Architecture

### 10.1 Horizontal Scaling Strategy

The system scales across multiple dimensions:

**Dimension 1: Ledger Segmentation (Primary)**

Formance Ledger supports horizontal scaling through **multi-ledger segmentation** [^433^]:

```
PostgreSQL Cluster
├── Bucket: "tenant_abc" (schema)
│   ├── Ledger: "tenant_abc_main"      # Primary business ledger
│   ├── Ledger: "tenant_abc_payroll"   # Separate payroll ledger
│   └── Ledger: "tenant_abc_budget"    # Budget tracking ledger
├── Bucket: "tenant_xyz" (schema)
│   ├── Ledger: "tenant_xyz_main"
│   └── Ledger: "tenant_xyz_payroll"
└── ...
```

Each ledger supports **~1,000 writes/second** [^433^]. For small business accounting (typically <100 tx/day per tenant), a single ledger handles thousands of tenants.

**Dimension 2: Read Replicas**

```
Primary PostgreSQL
  │── Streaming replication ──▶ Read Replica 1 (reporting queries)
  │── Streaming replication ──▶ Read Replica 2 (balance lookups)
  └── Streaming replication ──▶ Read Replica 3 (analytics)
```

**Dimension 3: Service Horizontal Pod Autoscaling (HPA)**

```yaml
# Example HPA configuration
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: accounting-service
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: accounting-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

### 10.2 Performance Targets

| Metric | Target | Basis |
|--------|--------|-------|
| **Ledger write throughput** | 1,000 tx/s per ledger | Formance benchmark [^433^] |
| **API response time (p99)** | < 200ms | Xero-like SLA [^260^] |
| **LLM chat response** | < 3 seconds streaming start | OpenAI API typical |
| **Report generation** | < 30 seconds for quarterly P&L | Async processing |
| **Bank feed import** | < 5 minutes for 500 tx | Batch processing |
| **System availability** | 99.9% (8.76h downtime/year) | Cloud-native standard |
| **Concurrent chat sessions** | 100 per instance | Agent orchestrator capacity |

### 10.3 Capacity Planning

| Tenant Tier | Transactions/Month | Ledger Design | PostgreSQL |
|-------------|-------------------|---------------|------------|
| **Micro** | < 100 | Shared ledger with tenant prefix on accounts | Shared instance |
| **Small** | 100 - 10,000 | Dedicated ledger per tenant | Shared instance |
| **Medium** | 10K - 100K | Dedicated ledger + read replica | Dedicated instance |
| **Large** | 100K - 1M | Multiple segmented ledgers | Dedicated cluster |

### 10.4 Ledger Sharding for Multi-Tenant

The recommended approach for multi-tenant scaling uses **Formance buckets** mapped to PostgreSQL schemas [^498^]:

```typescript
// Tenant provisioning service
async function provisionTenant(orgId: string, tier: Tier): Promise<LedgerConfig> {
  // Create isolated bucket (PostgreSQL schema)
  const bucketName = `tenant_${orgId.substring(0, 8)}`;
  
  // Create ledger within bucket
  const ledgerName = `${bucketName}_main`;
  
  await formance.ledger.v2.createLedger({
    v2CreateLedgerRequest: {
      bucket: bucketName,
      ledger: ledgerName,
      features: {
        // Disable log hashing for small biz tier (performance)
        // Enable for enterprise tier (audit compliance)
        HASH_LOGS: tier === 'enterprise' ? 'ENABLED' : 'ASYNC'
      }
    }
  });
  
  // Initialize chart of accounts
  await initializeCOA(ledgerName, defaultAccounts);
  
  return { bucket: bucketName, ledger: ledgerName };
}
```

### 10.5 Caching Strategy for Scale

```
┌─────────────────────────────────────────────────────────┐
│                    CACHE LAYERS                          │
│                                                          │
│  L1: In-Memory (service-local)                          │
│  ├── Chart of accounts (rarely changes)                 │
│  └── Account metadata (5-min TTL)                       │
│                                                          │
│  L2: Redis (shared cluster)                             │
│  ├── Account balances (30-sec TTL, invalidate on tx)    │
│  ├── Session data (24h TTL)                             │
│  ├── Rate limit counters (1-min TTL)                    │
│  └── Report cache (1h TTL)                              │
│                                                          │
│  L3: CDN (CloudFront/CloudFlare)                        │
│  ├── Static assets (web app bundles)                    │
│  └── Generated report PDFs (signed URLs)                │
└─────────────────────────────────────────────────────────┘
```

---

## Appendix A: Technology Stack Summary

| Category | Technology | Version | License |
|----------|-----------|---------|---------|
| **Ledger Engine** | Formance Ledger | v2.x | MIT [^169^] |
| **Ledger DSL** | Numscript | v2 | MIT |
| **API Framework** | NestJS | 10.x | MIT |
| **Agent Framework** | LangGraph + OpenAI SDK | Latest | MIT |
| **API Gateway** | Kong or Traefik | 3.x | Apache 2.0 |
| **Primary Database** | PostgreSQL | 16+ | PostgreSQL License |
| **Cache** | Redis | 7+ | BSD-3 |
| **Message Broker** | NATS + JetStream | 2.10+ | Apache 2.0 |
| **File Storage** | MinIO | Latest | AGPL-3.0 |
| **Orchestration** | Temporal (optional) | Latest | MIT |
| **Container Runtime** | Docker / containerd | Latest | Apache 2.0 |
| **Orchestrator** | Kubernetes | 1.29+ | Apache 2.0 |
| **Ledger Operator** | Formance Operator | Latest | MIT |
| **Languages** | TypeScript, Python, Numscript | - | - |

## Appendix B: Glossary

| Term | Definition |
|------|-----------|
| **Formance Ledger** | Open-source programmable financial ledger using PostgreSQL for storage and Numscript for transaction modeling |
| **Numscript** | Declarative DSL for modeling financial transactions; supports multi-party transfers, percentage splits, ordered funding sources [^229^] |
| **Bucket** | A Formance data isolation unit mapped to a PostgreSQL schema |
| **Ledger (Formance)** | A named collection of accounts and transactions within a bucket |
| **SKILL.md** | Open standard format (agentskills.io) for defining LLM agent capabilities [^258^] |
| **Supervisor Pattern** | Hierarchical multi-agent orchestration where a central agent delegates to specialist agents [^269^] |
| **Posting** | A single debit/credit entry within a Formance transaction |
| **Transaction (Formance)** | An atomic, multi-posting operation that succeeds or fails as a unit |

## Appendix C: References

| Citation | Source | URL |
|----------|--------|-----|
| [^169^] | Formance Ledger GitHub | github.com/formancehq/ledger |
| [^194^] | Formance SDKs Documentation | docs.formance.com/manage/sdks |
| [^197^] | Formance TypeScript SDK | github.com/formancehq/formance-sdk-typescript |
| [^201^] | Formance Ledger Quick Start | docs.formance.com/modules/ledger/quick-start |
| [^229^] | Numscript Blog | formance.com/blog/engineering/numscript |
| [^255^] | Multi-Agent AI Systems Guide | agilesoftlabs.com/blog/2026/03/multi-agent-ai-systems-enterprise-guide |
| [^256^] | SKILL.md Pattern | bibek-poudel.medium.com/the-skill-md-pattern |
| [^258^] | AgentSkills Specification | agentskills.io/specification |
| [^260^] | Xero API Guide | bindbee.dev/feeds/blog/xero-api |
| [^269^] | LLM Multi-Agent Orchestration Survey | preprints.org/manuscript/202604.2147 |
| [^272^] | REST vs gRPC Performance | l3montree.com/blog/performance-comparison-rest-vs-grpc-vs-asynchronous-communication |
| [^273^] | gRPC vs REST for Microservices | nikujais.medium.com/grpc-vs-rest-choosing-the-right-communication-for-microservices |
| [^369^] | Apache Kafka in Finance | softwaremill.com/business-insights/7-complex-problems-apache-kafka-solves-in-finance |
| [^376^] | NATS.io | nats.io |
| [^391^] | RFC 9700 OAuth 2.0 Security | datatracker.ietf.org/doc/rfc9700 |
| [^393^] | MinIO Distributed Mode | oneuptime.com/blog/post/2026-02-09-minio-distributed-ha-storage |
| [^400^] | WebSocket vs REST for AI | cloudthat.com/resources/blog/websocket-vs-rest-api-for-ai-streaming-and-live-responses |
| [^418^] | Temporal Fintech Workflows | xgrid.co/resources/temporal-fintech-workflows-durable-long-running |
| [^421^] | Formance Self-Host Docker | senate.sh/apps/formance-ledger |
| [^423^] | Formance Connect Your App | docs.formance.com/getting-started/connect-app |
| [^433^] | Formance Scaling | docs.formance.com/modules/ledger/advanced/architecting-for-scale |
| [^498^] | Formance Data Isolation Buckets | docs.formance.com/v3.2/modules/ledger/working-with/data-isolation-buckets |
| [^514^] | Formance Performance Model | docs.formance.com/modules/ledger/advanced/performance-model |
| [^524^] | Formance Event Publishers | docs.formance.com/v3.2/modules/ledger/advanced/events-publishers |

---

*End of Document*
