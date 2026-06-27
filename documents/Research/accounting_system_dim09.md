# Dimension 09: Agentic Workflow Architecture

## Accounting System LLM Agent — Complete Architecture Design

**Version:** 1.0  
**Status:** Design Specification  
**Classification:** Architecture  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Agent Topology](#2-agent-topology)
3. [SKILL Registry](#3-skill-registry)
4. [Chat Interface](#4-chat-interface)
5. [Tool Calling](#5-tool-calling)
6. [Human-in-the-Loop](#6-human-in-the-loop)
7. [Memory & Context](#7-memory--context)
8. [Safety Guardrails](#8-safety-guardrails)
9. [Error Handling](#9-error-handling)
10. [Observability](#10-observability)
11. [EU AI Act Compliance](#11-eu-ai-act-compliance)
12. [Implementation Roadmap](#12-implementation-roadmap)
13. [References](#13-references)

---

## 1. Executive Summary

This document specifies the complete agentic workflow architecture for the accounting system's LLM-based conversational interface. The architecture adopts a **supervisor pattern** with 8 specialist agents, OpenClaw-compatible skill registry, WebSocket-based chat interface, and comprehensive safety guardrails designed for financial data integrity.

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent Topology | Supervisor + 8 specialists | Optimal for 4-8 specialists: 89% success rate vs 71% single-agent [^16^] |
| Skill Format | OpenClaw SKILL.md + YAML frontmatter | Local-first, metadata-driven, 250K+ GitHub stars ecosystem [^65^] |
| Orchestration Pattern | ReAct within each agent; Supervisor for routing | 34% improvement on decision benchmarks [^480^] |
| Execution Plan | Plan-and-Execute for posting workflows | Auditable DAGs required for accounting traceability [^485^] |
| Memory Framework | Mem0 (episodic + semantic) + Redis (short-term) | Multi-store architecture with adaptive updates [^501^] |
| HITL Model | Graduated autonomy with 6 approval gates | 100% high-risk approval required, sampled for low-risk [^499^] |
| Compliance Target | EU AI Act high-risk system readiness | 7% revenue fines effective August 2026 [^469^] |
| Structured Output | JSON Schema with strict mode + constrained decoding | 100% schema adherence on supported models [^488^] |

---

## 2. Agent Topology

### 2.1 Architecture Overview

The system employs a **supervisor pattern** — a star topology where a central supervisor agent routes user requests to one of eight specialist agents. Each specialist handles a discrete accounting domain and returns results to the supervisor for synthesis and delivery [^16^] [^478^].

```
                     +-------------------+
                     |    Supervisor     |
                     |    (Router/Orchestrator)  |
                     +---------+---------+
                               |
            +--------+---------+---------+--------+
            |        |         |         |        |
    +-------v--+ +---v----+ +--v-----+ +--v-----+ +--v-----+
    |  Intake  | |Categorize| |Validate| | Posting | |Reconcile|
    +-------+--+ +---+----+ +--+-----+ +--+-----+ +--+-----+
            |        |         |         |        |
            +--------+---------+---------+--------+
                               |
                     +---------v---------+
                     |  Reporting  |  Tax  |  Audit  |
                     +-------------------+
```

### 2.2 Supervisor Agent

The supervisor is the sole entry point for all user requests. It uses the ReAct pattern (Reasoning + Acting) to decompose tasks and route to specialists [^480^].

**Responsibilities:**
- Intent classification and task decomposition
- Routing to single specialist (one at a time)
- Synthesizing multi-step workflow results
- Managing conversation flow and termination
- Escalation to human when confidence is low

**Configuration:**
```yaml
supervisor:
  model: gpt-4o-2024-08-06      # Production routing model
  temperature: 0                  # Deterministic routing decisions
  output_mode: last_message       # Keep context windows controlled
  max_iterations: 20              # Prevent runaway loops
  routing_accuracy_target: 0.95   # 95% correct routing eval threshold
```

**Production Notes:**
- Supervisor temperature MUST be 0 for deterministic routing [^16^]
- Supervisor prompt must explicitly forbid doing specialist work itself
- Worker prompts must include "if asked X outside your scope, defer to supervisor"
- Full history logged to LangSmith; `last_message` mode used in production [^16^]

### 2.3 Cost-Benefit Analysis

| Approach | Avg Tokens | Avg Cost | E2E Success | When It Wins |
|----------|-----------|----------|-------------|--------------|
| Single mega-agent | 4,200 | $0.022 | 71% | Simple tasks; one persona |
| ReAct agent + many tools | 6,800 | $0.038 | 79% | Medium complexity |
| **Supervisor + 4-8 specialists** | **11,400** | **$0.061** | **89%** | **Heterogeneous tasks; specialist tools** |
| Hierarchical (supervisor of supervisors) | 18,200 | $0.097 | 91% | Only past 8+ specialists [^16^] |

The supervisor pattern is **3x the cost of a single agent for an 18-point lift in success rate**. For accounting operations where accuracy is critical and errors carry regulatory risk, this tradeoff is justified.

### 2.4 Specialist Agents

#### 2.4.1 Intake Agent

| Attribute | Specification |
|-----------|--------------|
| **Purpose** | Initial document and transaction ingestion |
| **Tools** | `parse_invoice`, `parse_receipt`, `parse_bank_statement`, `extract_metadata` |
| **Input** | Raw documents (PDF, image, CSV), manual entry text |
| **Output** | Structured transaction records with extracted fields |
| **ReAct Pattern** | Reason about document type, extract fields via OCR/parser tools, verify completeness |

```python
# Intake Agent Tool Schema Example
{
  "name": "parse_invoice",
  "description": "Extract structured data from an invoice document",
  "parameters": {
    "type": "object",
    "properties": {
      "document_url": {"type": "string", "format": "uri"},
      "vendor_name": {"type": "string"},
      "invoice_number": {"type": "string"},
      "invoice_date": {"type": "string", "format": "date"},
      "due_date": {"type": "string", "format": "date"},
      "line_items": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "description": {"type": "string"},
            "quantity": {"type": "number"},
            "unit_price": {"type": "number"},
            "amount": {"type": "number"},
            "account_code": {"type": "string"}
          },
          "required": ["description", "quantity", "unit_price", "amount"]
        }
      },
      "subtotal": {"type": "number"},
      "tax_amount": {"type": "number"},
      "total_amount": {"type": "number"},
      "currency": {"type": "string", "enum": ["USD", "EUR", "GBP"]}
    },
    "required": ["document_url", "vendor_name", "invoice_number", "total_amount"]
  }
}
```

#### 2.4.2 Categorization Agent

| Attribute | Specification |
|-----------|--------------|
| **Purpose** | Classify transactions to Chart of Accounts (COA) entries |
| **Tools** | `lookup_coa`, `suggest_category`, `match_vendor_to_account`, `learn_categorization` |
| **Input** | Structured transaction records |
| **Output** | Proposed COA codes with confidence scores |
| **Memory Dependency** | Episodic: past categorization decisions; Semantic: COA hierarchy |

#### 2.4.3 Validation Agent

| Attribute | Specification |
|-----------|--------------|
| **Purpose** | Validate transactions against accounting rules before posting |
| **Tools** | `check_debit_credit_balance`, `validate_coa_membership`, `check_duplicate`, `verify_vendor_exists`, `run_compliance_check` |
| **Input** | Categorized transactions |
| **Output** | Validation report with pass/fail status and remediation suggestions |
| **Critical Checks** | Balance validation (debits = credits), COA membership, duplicate detection |

#### 2.4.4 Posting Agent

| Attribute | Specification |
|-----------|--------------|
| **Purpose** | Execute journal entries to the general ledger |
| **Tools** | `create_journal_entry`, `post_to_ledger`, `create_reversing_entry`, `batch_post` |
| **Input** | Validated transactions |
| **Output** | Posted journal entries with transaction IDs |
| **Execution Pattern** | Plan-and-Execute with auditable DAG [^485^] |
| **HITL Gate** | ALL posting operations require human approval |

The Posting Agent uses **Plan-and-Execute** rather than pure ReAct because accounting transactions require auditable, predetermined execution plans — not dynamic reasoning chains [^485^] [^467^].

#### 2.4.5 Reconciliation Agent

| Attribute | Specification |
|-----------|--------------|
| **Purpose** | Match transactions across ledgers and bank statements |
| **Tools** | `match_transactions`, `identify_discrepancies`, `suggest_matches`, `auto_reconcile` |
| **Input** | Ledger entries + external statements |
| **Output** | Reconciliation reports with matched/unmatched items |
| **HITL Gate** | Discrepancies above threshold require human review |

#### 2.4.6 Reporting Agent

| Attribute | Specification |
|-----------|--------------|
| **Purpose** | Generate financial reports and analytics |
| **Tools** | `generate_trial_balance`, `generate_pnl`, `generate_balance_sheet`, `generate_cashflow`, `custom_report` |
| **Input** | Posted ledger data, reporting period, filters |
| **Output** | Structured financial reports in requested format |
| **HITL Gate** | Exception-only (auto-generated reports sampled at 5%) |

#### 2.4.7 Tax Agent

| Attribute | Specification |
|-----------|--------------|
| **Purpose** | Calculate tax obligations and prepare filings |
| **Tools** | `calculate_vat`, `calculate_income_tax`, `generate_tax_report`, `check_tax_compliance` |
| **Input** | Posted transactions, tax jurisdiction, period |
| **Output** | Tax calculations and filing-ready reports |
| **HITL Gate** | ALL tax filings require human approval (100%) |

#### 2.4.8 Audit Agent

| Attribute | Specification |
|-----------|--------------|
| **Purpose** | Provide audit trails, anomaly detection, and compliance verification |
| **Tools** | `generate_audit_trail`, `detect_anomalies`, `run_compliance_check`, `explain_transaction` |
| **Input** | Ledger data, audit period, focus areas |
| **Output** | Audit reports with evidence chains and anomaly flags |
| **HITL Gate** | Anomaly investigation requires human review |

### 2.5 Multi-Agent Patterns by Industry Context

Financial services uses multiple multi-agent coordination approaches for regulatory compliance, including workflow patterns (with sequential and parallel execution), swarm patterns for distributed reasoning, and graph patterns (hierarchical structures), supplemented by iterative loop patterns for refinement. Insurance underwriting uses parallel patterns where agents simultaneously analyze property, liability, and financial stability, processing risks concurrently with auditable trails [^464^].

---

## 3. SKILL Registry

### 3.1 Design Philosophy

The skill registry follows the **OpenClaw SKILL.md format** — a folder-based, metadata-driven system where each skill is a directory containing a `SKILL.md` file with YAML frontmatter and markdown instructions [^65^] [^73^]. This approach is:

- **Local-first**: Skills load from workspace, user, and bundled paths
- **SDK-free**: No compilation, no special runtime — just structured text
- **Discoverable**: Vector-based semantic search across skill descriptions
- **Versioned**: Skills support version pinning and update control

### 3.2 Skill Loading Precedence

Skills load in strict precedence order (highest wins on name conflict):

1. **Workspace skills** (`<workspace>/skills/`) — project-specific overrides
2. **User skills** (`~/.openclaw/skills/`) — personal managed skills
3. **Bundled skills** — system defaults

### 3.3 SKILL.md Format Specification

```markdown
---
name: accounting-categorize
description: Categorize financial transactions to the Chart of Accounts
version: 2.1.0
author: accounting-system
tags: [accounting, categorization, coa]
metadata:
  accounting:
    domain: general_ledger
    risk_level: medium
    requires_approval: false
    audit_trail: true
    coa_version: "2024.3"
  requires:
    env:
      - GL_DATABASE_URL
      - COA_API_KEY
    bins: []
  dependencies:
    - skill: accounting-validate
      version: ">=2.0.0"
---

## Purpose

Categorize incoming financial transactions by matching them to the appropriate
Chart of Accounts (COA) codes. This skill handles vendor mapping, amount-based
rules, and learned categorization patterns.

## When to Use

- User uploads an invoice or receipt that needs COA classification
- Bulk categorization of uncategorized transactions
- Vendor-to-account mapping suggestions
- COA code lookups by description or keyword

## Instructions

1. Extract vendor name, amount, and description from the transaction
2. Use `lookup_coa` to find candidate account codes
3. Check episodic memory for past categorization decisions with this vendor
4. Apply confidence scoring:
   - >= 0.95: Auto-categorize
   - 0.80 - 0.94: Propose to user for confirmation
   - < 0.80: Escalate to human accountant
5. Record the decision in episodic memory for future learning
6. Return structured result with account_code, confidence, and reasoning

## Rules

- NEVER categorize to a suspense account without explicit user approval
- ALWAYS verify COA code exists in the current chart before assignment
- When confidence is below 0.80, explain what additional info would help
- Respect entity boundaries — never mix transactions across legal entities
- Log all categorization decisions to the audit trail

## Error Handling

- If `lookup_coa` returns no matches: Use `suggest_category` with broader terms
- If vendor is unknown: Flag for vendor master data creation
- If amount exceeds entity threshold: Route to supervisor for approval routing
```

### 3.4 Metadata Schema

The YAML frontmatter uses an extended metadata schema for accounting-specific requirements:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique skill identifier (kebab-case) |
| `description` | string | Human-readable description (<160 chars) |
| `version` | semver | Semantic version |
| `metadata.accounting.domain` | string | Accounting domain (general_ledger, ap, ar, tax, etc.) |
| `metadata.accounting.risk_level` | enum | low / medium / high — determines approval requirements |
| `metadata.accounting.requires_approval` | boolean | Whether this skill always requires human approval |
| `metadata.accounting.audit_trail` | boolean | Whether to record all invocations |
| `metadata.requires.env` | array | Required environment variables |
| `metadata.dependencies` | array | Cross-skill dependencies |

### 3.5 Security: Lessons from ClawHavoc

The ClawHavoc incident in February 2026 demonstrated critical security vulnerabilities in skill-based agent systems [^507^] [^512^]:

**Attack Summary:**
- 341+ malicious skills discovered on ClawHub (20% of packages compromised) [^65^]
- Attack vectors: C2 callbacks, credential harvesting, data exfiltration, prompt injection
- Root cause: No cryptographic signing, no sandboxing by default, no verification

**Security Measures for Accounting System:**

| Layer | Control | Implementation |
|-------|---------|----------------|
| **Upload Scanning** | SHA-256 hash + VirusTotal scan | All skills scanned before activation |
| **Daily Rescanning** | Continuous monitoring | Existing skills rescanned for delayed attacks |
| **Code Signing** | Cryptographic signature verification | All skills signed by trusted authority |
| **Sandboxing** | Docker container isolation | Skill execution in restricted containers |
| **Permission Model** | Least-privilege access | Skills only access declared resources |
| **Audit Trail** | Complete invocation logging | Every skill call logged with parameters and results |
| **Network Restrictions** | Deny-by-default egress | Skills cannot make outbound network calls unless explicitly allowed |

### 3.6 Skill Discovery and Registry API

```python
# Skill Registry Interface
class SkillRegistry:
    def register(self, skill_path: str) -> SkillMetadata:
        """Register a skill after validation and security scanning."""
    
    def discover(self, query: str, filter: SkillFilter) -> list[SkillMetadata]:
        """Vector-search skills by description and tags."""
    
    def get(self, name: str, version: str = "latest") -> Skill:
        """Retrieve a skill by name, with version pinning support."""
    
    def validate_dependencies(self, skill: Skill) -> DependencyReport:
        """Check that all declared dependencies are satisfied."""
    
    def audit_log(self, skill_name: str) -> list[AuditRecord]:
        """Return complete invocation audit trail for a skill."""
```

---

## 4. Chat Interface

### 4.1 WebSocket Architecture

The chat interface uses **WebSocket-based bidirectional communication** for real-time conversational interaction [^474^].

```
Client (Browser)                    Server (FastAPI)
     |                                     |
     |---- WebSocket /ws/chat/{session_id} ->|
     |<--- Connection Accepted --------------|
     |<--- Conversation History (if exists) --|
     |                                     |
     |---- {type: "message", content: "..."} ->|
     |                                     |---> Supervisor Agent
     |                                     |     ... Processing ...
     |<--- {type: "stream_token", token: "..."} |
     |<--- {type: "stream_token", token: "..."} |
     |<--- {type: "stream_end", result: {...}}--|
     |                                     |
     |---- {type: "approval", decision: "..."} ->|
     |                                     |
```

### 4.2 Message Protocol

All messages use a typed JSON protocol:

```typescript
// Client -> Server
interface ClientMessage {
  type: "message" | "approval" | "rejection" | "clear_history" | "upload";
  session_id: string;
  content?: string;              // For type: "message"
  decision?: ApprovalDecision;    // For type: "approval" | "rejection"
  document?: UploadedDocument;    // For type: "upload"
  metadata?: Record<string, any>;
}

// Server -> Client
interface ServerMessage {
  type: "stream_start" | "stream_token" | "stream_end" 
       | "approval_request" | "history" | "error" | "status";
  content?: string;              // Text content or token
  result?: AgentResult;           // Structured result (stream_end)
  approval_request?: ApprovalRequest; // Human-in-the-loop gate
  history?: ChatMessage[];        // Conversation history
  error?: ErrorDetails;           // Error information
  agent_name?: string;            // Which agent is handling the request
}

interface ApprovalRequest {
  request_id: string;
  action_type: "post_journal" | "modify_entry" | "delete_entry" 
               | "generate_report" | "tax_filing" | "bulk_operation";
  description: string;
  proposed_action: Record<string, any>;
  risk_level: "low" | "medium" | "high" | "critical";
  required_approver_role: string;
  timeout_seconds: number;
}
```

### 4.3 Session Management

Sessions are managed via a `ConnectionManager` class that supports:

- **Multi-connection sessions**: A single session can have multiple WebSocket connections (e.g., multiple browser tabs)
- **Persistent history**: Conversation history stored in Redis for cross-session continuity
- **Streaming responses**: Real-time token streaming for responsive UX
- **Graceful reconnection**: Clients receive conversation history on reconnect

```python
class ConnectionManager:
    """Manages WebSocket connections for multi-user chat sessions."""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.session_history: Dict[str, List[dict]] = {}
        self.session_metadata: Dict[str, SessionContext] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str, 
                     user_context: UserContext):
        """Accept connection and load session context."""
    
    async def handle_message(self, session_id: str, 
                           message: ClientMessage) -> AsyncIterator[ServerMessage]:
        """Route message through supervisor agent and stream responses."""
```

### 4.4 Context Management

Each session maintains a `SessionContext` that persists across connections:

| Context Layer | Storage | Lifetime | Purpose |
|--------------|---------|----------|---------|
| Conversation history | Redis | Session | Message thread for context window |
| User preferences | PostgreSQL | Permanent | Business rules, display preferences |
| Episodic memory | Mem0 | Permanent | Past decisions, learned patterns |
| Working state | In-memory | Session | Pending approvals, draft operations |
| Entity context | Redis | Session | Active company/entity/book |

---

## 5. Tool Calling

### 5.1 JSON Schema Function Definitions

All tools are defined using **JSON Schema** for structured, validated interactions between agents and the accounting system [^462^] [^466^].

**Key Principles:**
- Each tool has a single, well-defined responsibility
- Schemas include clear descriptions for every parameter
- Tool names follow `domain_action` convention (e.g., `gl_create_journal_entry`)
- All schemas use `additionalProperties: false` for strict validation

### 5.2 Example Tool Definitions

#### 5.2.1 General Ledger Tools

```json
{
  "name": "gl_create_journal_entry",
  "description": "Create a balanced journal entry in the general ledger. Total debits must equal total credits. Each line must reference a valid COA account code.",
  "strict": true,
  "parameters": {
    "type": "object",
    "properties": {
      "entity_id": {
        "type": "string",
        "description": "Legal entity identifier for the posting"
      },
      "book_id": {
        "type": "string", 
        "description": "Accounting book (e.g., 'general_ledger', 'tax')"
      },
      "period": {
        "type": "string",
        "format": "date",
        "description": "Accounting period in YYYY-MM format"
      },
      "reference": {
        "type": "string",
        "description": "External reference number (e.g., invoice number)"
      },
      "description": {
        "type": "string",
        "description": "Human-readable description of the transaction"
      },
      "lines": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "account_code": {
              "type": "string",
              "description": "Valid Chart of Accounts code"
            },
            "debit": {
              "type": "number",
              "minimum": 0,
              "description": "Debit amount (0 if credit)"
            },
            "credit": {
              "type": "number",
              "minimum": 0,
              "description": "Credit amount (0 if debit)"
            },
            "description": {
              "type": "string",
              "description": "Line-level description"
            },
            "cost_center": {
              "type": "string",
              "description": "Optional cost center code"
            }
          },
          "required": ["account_code", "debit", "credit", "description"]
        },
        "minItems": 2,
        "description": "Journal entry lines (minimum 2: at least one debit and one credit)"
      },
      "attachments": {
        "type": "array",
        "items": {"type": "string", "format": "uri"},
        "description": "URLs to supporting documents"
      }
    },
    "required": ["entity_id", "book_id", "period", "reference", "description", "lines"]
  }
}
```

#### 5.2.2 Chart of Accounts Tools

```json
{
  "name": "coa_lookup",
  "description": "Look up a Chart of Accounts entry by code, name, or keyword. Returns account details including type, parent, and active status.",
  "strict": true,
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Account code, name, or keyword to search"
      },
      "account_type": {
        "type": "string",
        "enum": ["asset", "liability", "equity", "revenue", "expense"],
        "description": "Optional filter by account type"
      },
      "entity_id": {
        "type": "string",
        "description": "Legal entity to scope the COA lookup"
      }
    },
    "required": ["query", "entity_id"]
  }
}
```

#### 5.2.3 Validation Tools

```json
{
  "name": "validate_journal_entry",
  "description": "Validate a journal entry against accounting rules: (1) debits equal credits, (2) all account codes exist in COA, (3) accounts are active, (4) posting period is open, (5) entity matches, (6) no duplicate reference numbers.",
  "strict": true,
  "parameters": {
    "type": "object",
    "properties": {
      "journal_entry": {
        "$ref": "#/definitions/JournalEntry"
      },
      "validation_level": {
        "type": "string",
        "enum": ["basic", "standard", "strict"],
        "description": "Validation thoroughness level"
      }
    },
    "required": ["journal_entry", "validation_level"]
  }
}
```

### 5.3 Cross-Provider Compatibility via MCP

The Model Context Protocol (MCP) provides cross-vendor standardization for tool calling [^477^] [^482^] [^483^].

**Why MCP Matters:**

| Dimension | OpenAI | Anthropic | Google |
|-----------|--------|-----------|--------|
| Terminology | Function calling | Tool use | Function calling |
| Request field | `tools` array | `tools` array | `function_declarations` |
| Response field | `tool_calls` | `tool_use` in content | `function_call` |
| Schema definition | `parameters` (JSON Schema) | `input_schema` (JSON Schema) | `parameters` (OpenAPI-style) |
| Arguments format | JSON string | Dictionary/object | Dictionary/object |
| Reliability score | 6.3/10 | 8.4/10 | 7.9/10 [^462^] |

MCP transforms the MxN integration problem into M+N: one MCP server per business system works with all MCP-compatible AI clients through standardized primitives (tools, resources, prompts) [^483^].

**MCP Architecture for Accounting:**

```
+------------+     +------------------+     +-------------------+
|  Supervisor |---->|  MCP Client      |---->|  MCP Server (GL)  |
|  Agent      |     |  (per server)    |     |  - create_journal |
+------------+     +------------------+     |  - post_to_ledger |
                            |               +-------------------+
                            |               +-------------------+
                            |------------->|  MCP Server (COA) |
                            |               |  - lookup_account |
                            |               |  - validate_code  |
                            |               +-------------------+
                            |               +-------------------+
                            +------------->|  MCP Server (Tax) |
                                            |  - calculate_vat  |
                                            +-------------------+
```

### 5.4 Provider Selection Strategy

Given Anthropic's lead in function calling reliability (8.4/10 vs OpenAI's 6.3/10) [^462^], the architecture uses a **capability router** that selects the optimal provider per task:

| Task Type | Primary Provider | Fallback Provider | Rationale |
|-----------|-----------------|-------------------|-----------|
| Tool calling (complex schemas) | Anthropic Claude | OpenAI GPT-4o | Highest reliability on structured output |
| Routing decisions | OpenAI GPT-4o-mini | Anthropic Haiku | Cost-effective, temperature=0 |
| Content generation | Anthropic Claude | OpenAI GPT-4o | Superior reasoning quality |
| Document parsing | OpenAI GPT-4o | Anthropic Claude | Better multimodal capabilities |

---

## 6. Human-in-the-Loop

### 6.1 Graduated Autonomy Model

The system implements a **graduated autonomy** model where agent freedom increases with demonstrated reliability [^499^]:

```
Phase 1 (Weeks 1-4):    Supervised          100% human approval
Phase 2 (Weeks 5-12):   Sampled             20% sampled approval
Phase 3 (Months 3-6):   Exception-only      Auto-approve unless flagged
Phase 4 (Months 6+):    Full autonomy       Exception-only with policy triggers
```

### 6.2 Approval Decision Matrix

| Action Type | Cost of Error | Reversibility | Required Approver | SLA |
|-------------|--------------|---------------|-------------------|-----|
| **Post journal entry** | High | Low | Finance manager + accountant | 15-60 min |
| **Modify posted entry** | Very High | Low (requires reversal) | Dual approval | Same-day |
| **Delete entry** | Very High | Very Low | Controller + CFO notification | 1-4 hours |
| **Bulk posting** | Very High | Low | Controller review | 1-24 hours |
| **Generate standard report** | Low | High | None (exception-only) | Real-time |
| **Generate regulatory report** | High | Medium | Finance manager | 1-4 hours |
| **Tax calculation** | High | Medium | Tax manager | 1-24 hours |
| **Tax filing submission** | Very High | Very Low | Controller + external review | 1-7 days |
| **COA modification** | High | Medium | Controller | 1-24 hours |
| **Vendor master change** | Medium | Medium | AP manager | 1-4 hours |
| **Reconciliation auto-match** | Low | High | None (exception-only) | Real-time |
| **Reconciliation discrepancy** | Medium | Medium | Accountant | 1-24 hours |

### 6.3 Approval Workflow Patterns

#### Pattern 1: Action-Level Gate (Tool Call Approval)

The agent proposes a tool call and waits for approval before executing [^499^]:

```python
class ApprovalGate:
    async def propose_action(self, action: ProposedAction) -> ApprovalResult:
        """
        1. Generate structured proposal with:
           - Action type and parameters
           - Risk assessment
           - Rollback plan
           - Confidence score
        2. Store in approval queue with timeout
        3. Notify approver via WebSocket + (email/Slack for non-realtime)
        4. Wait for approval, rejection, or timeout
        5. Execute only after explicit approval
        """
        proposal = self.create_proposal(action)
        await self.approval_queue.enqueue(proposal)
        await self.notify_approver(proposal)
        
        decision = await self.wait_for_decision(
            proposal.request_id, 
            timeout_seconds=proposal.sla_seconds
        )
        
        if decision == ApprovalStatus.APPROVED:
            return await self.execute_with_idempotency(proposal)
        elif decision == ApprovalStatus.REJECTED:
            return ApprovalResult(status="rejected", reason=decision.reason)
        else:
            return ApprovalResult(status="timeout", requires_escalation=True)
```

#### Pattern 2: Draft Approval (Content Review)

The agent drafts content (journal entry, report) and human reviews/edits before execution.

#### Pattern 3: Dual Approval (Two-Person Rule)

High-risk operations require two separate approvers — no single person can approve their own action.

#### Pattern 4: Exception-Only Review

The agent auto-approves unless a policy trigger fires: low confidence, unusual amounts, sensitive accounts, high risk score.

### 6.4 Proposed Action Schema

Every approval request generates a structured `ProposedAction` that is fully auditable:

```json
{
  "request_id": "apr_2vR9kL7mN3pQ",
  "timestamp": "2025-01-15T09:23:17Z",
  "agent_name": "posting_agent",
  "agent_version": "2.1.0",
  "action_type": "post_journal",
  "risk_level": "high",
  "proposed_action": {
    "entity_id": "ENT_001",
    "book_id": "general_ledger",
    "period": "2025-01",
    "reference": "INV-2025-0042",
    "description": "Vendor invoice payment - Acme Supplies",
    "lines": [
      {"account_code": "6100", "debit": 5000.00, "credit": 0, "description": "Office Supplies Expense"},
      {"account_code": "2100", "debit": 0, "credit": 5000.00, "description": "Accounts Payable"}
    ]
  },
  "validation_result": {
    "debit_credit_balance": true,
    "coa_valid": true,
    "period_open": true,
    "no_duplicate": true,
    "confidence_score": 0.97
  },
  "rollback_plan": {
    "method": "reversing_entry",
    "description": "Reverse journal entry ENT_001-202501-0042"
  },
  "idempotency_key": "idemp_aB3cD4eF5gH6",
  "required_approver_role": "finance_manager",
  "timeout_seconds": 3600
}
```

---

## 7. Memory & Context

### 7.1 Memory Architecture

The system implements a **three-tier memory model** inspired by cognitive architectures [^470^] [^501^]:

```
+---------------------+     +---------------------+     +---------------------+
|   Short-Term Memory |     |   Episodic Memory   |     |   Semantic Memory   |
|   (Working Context) |     |   (Event History)   |     |   (Domain Knowledge) |
+---------------------+     +---------------------+     +---------------------+
| Redis (in-memory)   |     | Mem0 (vector+graph) |     | PostgreSQL + Mem0   |
| - Conversation msg  |     | - Past decisions    |     | - COA hierarchy     |
| - Session state     |     | - Transaction history|    | - Business rules    |
| - Working drafts    |     | - User preferences  |     | - Vendor mappings   |
| - Pending approvals |     | - Categorization patterns| | - Accounting policies|
+---------------------+     +---------------------+     +---------------------+
       TTL: Session                Persistent                  Persistent
       < 10MB/agent                ~ GB scale                  ~ GB scale
```

### 7.2 Short-Term Memory (Conversation Context)

Managed via Redis with sub-millisecond latency. Stores the active conversation thread within the LLM's context window [^504^].

**Contents:**
- Recent conversation messages (last N turns)
- Active session state (pending approvals, draft operations)
- Working context (current entity, book, period)
- Tool call history within the current task

**Management:**
- Sliding window: Keep last 20 message pairs (configurable)
- Token budget: Max 8K tokens for conversation context
- Automatic summarization when budget exceeded
- Session TTL: 24 hours with heartbeat refresh

### 7.3 Episodic Memory (Event History)

Managed via Mem0 — stores specific events with temporal markers [^501^] [^503^].

**Contents:**
- Past categorization decisions ("Invoice from Acme Supplies -> 6100 Office Supplies")
- Correction history ("User corrected 6100 to 6200 for IT equipment")
- Approval patterns ("Controller typically approves under $10K within 30 min")
- Reconciliation matches ("Bank transaction XYZ matched to ledger entry ABC")
- Error events and recovery outcomes

**Retrieval:**
- Vector similarity search on vendor name, description, amount patterns
- Temporal recency weighting (recent events more relevant)
- Entity-scoped (never mix across legal entities)

**Schema:**
```json
{
  "memory_id": "mem_7xK2pL9m",
  "type": "categorization_decision",
  "timestamp": "2025-01-10T14:23:00Z",
  "entity_id": "ENT_001",
  "context": {
    "vendor_name": "Acme Supplies Inc.",
    "description": "Monthly office supply delivery",
    "amount_range": "4000-6000",
    "currency": "USD"
  },
  "decision": {
    "account_code": "6100",
    "account_name": "Office Supplies Expense",
    "confidence": 0.96,
    "approved_by": "auto"
  },
  "outcome": "accepted",
  "user_feedback": null
}
```

### 7.4 Semantic Memory (Domain Knowledge)

Stores generalized knowledge without event-specific context [^504^].

**Contents:**
- Chart of Accounts hierarchy and relationships
- Business rules and accounting policies
- Vendor-to-account mapping rules
- Tax jurisdiction rules and rates
- Regulatory reporting requirements

**Storage:** PostgreSQL for structured data + Mem0 vector search for semantic retrieval.

### 7.5 Procedural Memory (Learned Patterns)

Encodes behavioral patterns learned from successful operations [^504^].

**Contents:**
- Optimal categorization strategies by vendor type
- Common journal entry templates by transaction type
- Effective reconciliation match parameters
- User-specific formatting and communication preferences

### 7.6 Memory Framework Comparison

| Framework | Strengths | Best For |
|-----------|-----------|----------|
| **Mem0** | Universal personalization, adaptive updates, 50K GitHub stars, multi-store (vector+graph+KV) | Episodic + semantic memory for personalization [^501^] |
| **Zep** | Temporal knowledge graphs, high-performance relational retrieval | Complex relationship queries across time |
| **LangMem** | Native developer integration, procedural learning | Agent skill learning and tool optimization |
| **Redis** | Sub-millisecond performance, pub/sub, #1 for agent storage (43% adoption) | Short-term memory, real-time coordination [^464^] |

**Selected Architecture:** Mem0 for episodic/semantic + Redis for short-term.

---

## 8. Safety Guardrails

### 8.1 Input Validation Pipeline

All user inputs pass through a multi-layer validation pipeline before reaching any agent:

| Layer | Validation | Action on Failure |
|-------|-----------|-------------------|
| **1. Syntax** | JSON/schema validation | Reject with parse error |
| **2. Semantic** | Type checking, range validation | Reject with specific error message |
| **3. Authorization** | User permissions, entity access | Reject with 403, log security event |
| **4. Content Safety** | PII detection, prompt injection scan | Sanitize or reject, alert security |
| **5. Business Rules** | Entity match, period open, COA valid | Reject with business rule explanation |

### 8.2 Output Validation Pipeline

All agent outputs are validated before any system modification:

| Layer | Validation | Action on Failure |
|-------|-----------|-------------------|
| **1. Schema** | JSON Schema strict validation | Retry with corrected prompt (max 3) |
| **2. Accounting Rules** | Debit = Credit, COA membership | Reject, return to agent with error |
| **3. Balance Check** | Trial balance integrity | Block posting, alert accounting team |
| **4. Duplicate Check** | Reference number uniqueness | Reject with duplicate detection result |
| **5. Anomaly Detection** | Statistical outlier detection | Flag for human review, allow with warning |

### 8.3 Accounting-Specific Validations

#### 8.3.1 Debit-Credit Balance Check

Every journal entry MUST satisfy: **Total Debits = Total Credits** [^500^].

```python
def validate_debit_credit_balance(lines: list[JournalLine]) -> ValidationResult:
    total_debits = sum(line.debit for line in lines)
    total_credits = sum(line.credit for line in lines)
    difference = abs(total_debits - total_credits)
    
    if difference > Decimal("0.01"):
        return ValidationResult(
            valid=False,
            error=f"Imbalanced entry: debits={total_debits}, credits={total_credits}, diff={difference}",
            severity="critical"
        )
    return ValidationResult(valid=True)
```

#### 8.3.2 COA Membership Check

Every account code used MUST exist in the current Chart of Accounts and be active [^500^]:

```python
def validate_coa_membership(account_code: str, entity_id: str, period: str) -> ValidationResult:
    account = coa_lookup(account_code, entity_id)
    
    if not account:
        return ValidationResult(valid=False, error=f"Account code '{account_code}' not found in COA")
    
    if not account.is_active:
        return ValidationResult(valid=False, error=f"Account '{account_code}' is inactive")
    
    if account.effective_date and account.effective_date > period:
        return ValidationResult(valid=False, error=f"Account '{account_code}' not yet effective")
    
    return ValidationResult(valid=True)
```

#### 8.3.3 Double-Entry Rules

Per standard double-entry accounting [^510^]:

| Account Type | Increase | Decrease |
|-------------|----------|----------|
| Assets | Debit | Credit |
| Liabilities | Credit | Debit |
| Equity | Credit | Debit |
| Revenue | Credit | Debit |
| Expenses | Debit | Credit |

The Validation Agent applies these rules to flag entries that violate account-type conventions.

### 8.4 Content Safety Guardrails

- **PII Detection**: Scan inputs/outputs for exposed personal information
- **Prompt Injection Detection**: Pattern matching for known injection techniques
- **SQL Injection Prevention**: Parameterized queries only; no dynamic SQL generation
- **Data Exfiltration Prevention**: Rate limiting on outbound data; network restrictions
- **Output Moderation**: Check for harmful, biased, or non-compliant content

### 8.5 Validation Agent: Pre-Posting Checklist

Before ANY journal entry is posted, the Validation Agent confirms:

- [ ] Debits equal credits (difference <= $0.01)
- [ ] All account codes exist in the active COA
- [ ] Posting period is open for the entity
- [ ] Entity ID matches the context
- [ ] Reference number is unique (or identified as intentional duplicate)
- [ ] All required fields are populated
- [ ] Amounts are positive and within reasonable bounds
- [ ] Cost centers are valid (if provided)
- [ ] Currency matches entity base currency (or valid foreign currency)
- [ ] No conflicting entries exist for the same reference
- [ ] Approval workflow completed (if required by risk level)

---

## 9. Error Handling

### 9.1 Error Taxonomy

Agent failures are classified into three categories, each with distinct handling strategies [^490^]:

#### Category 1: Hard Failures

**Definition**: Execution terminates abnormally with an explicit error.

**Examples**: API timeout, rate limit (429), database connection failure, malformed LLM response, authentication failure.

**Response Strategy**: Retry with exponential backoff (max 3 retries), then degrade or escalate.

```python
retry_config = {
    "max_retries": 3,
    "backoff_strategy": "exponential_with_jitter",
    "base_delay_seconds": 2,
    "max_delay_seconds": 30,
    "retryable_errors": [429, 500, 502, 503, 504],
    "non_retryable_errors": [400, 401, 403, 404]
}
```

#### Category 2: Structural Failures

**Definition**: Agent completes execution but output does not meet structural requirements.

**Examples**: Invalid JSON, missing required fields, schema validation failure, tool called with invalid parameters.

**Response Strategy**: Retry with clearer formatting instructions, fall back to simpler output format.

#### Category 3: Semantic Failures

**Definition**: Output is structurally valid but factually wrong or nonsensical.

**Examples**: Hallucinated account codes, incorrect categorization, confident assertion of wrong information.

**Response Strategy**: Flag as uncertain, add verification step, escalate to human review.

### 9.2 Graceful Degradation Strategy

When full-capability response is not possible, the agent provides reduced functionality [^487^]:

| Degradation Level | Trigger | Agent Behavior |
|-------------------|---------|----------------|
| **Level 0: Full** | All systems operational | Normal operation with all tools |
| **Level 1: Cached** | API rate limit or timeout | Use cached COA data, stale but valid |
| **Level 2: Restricted** | LLM API unavailable | Deterministic rule-based responses only |
| **Level 3: Human-only** | Critical system failure | Immediate human escalation, no automated action |

### 9.3 Circuit Breakers

Circuit breakers prevent cascading failures in multi-agent systems [^490^] [^494^]:

```python
class AgentCircuitBreaker:
    """Circuit breaker for external service calls in agents."""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout_seconds: int = 60,
                 half_open_max_calls: int = 3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_seconds
        self.half_open_max = half_open_max_calls
        self.state = CircuitState.CLOSED  # CLOSED -> OPEN -> HALF_OPEN -> CLOSED
        self.failure_count = 0
        self.last_failure_time = None
    
    def call(self, operation: Callable) -> Result:
        if self.state == CircuitState.OPEN:
            if time.now() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                return Result.failure(CircuitOpenError())
        
        try:
            result = operation()
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise
```

### 9.4 Compensation Transactions (Saga Pattern)

For multi-step accounting workflows, the Saga pattern with compensating transactions ensures eventual consistency [^467^] [^476^]:

```python
class AccountingSaga:
    """
    Saga orchestrator for multi-step accounting workflows.
    Each step has a forward action and a compensating (undo) action.
    """
    
    async def execute(self, steps: list[SagaStep]) -> SagaResult:
        completed_steps = []
        
        for step in steps:
            try:
                result = await step.forward()
                completed_steps.append((step, result))
            except Exception as e:
                # Execute compensating transactions in reverse order
                for completed_step, _ in reversed(completed_steps):
                    await completed_step.compensate()
                return SagaResult(status="compensated", failed_step=step.name)
        
        return SagaResult(status="completed", steps=completed_steps)

# Example: Invoice processing saga
invoice_saga = [
    SagaStep(
        name="create_payable",
        forward=lambda: gl.create_journal_entry(debit_expense, credit_ap),
        compensate=lambda: gl.create_reversing_entry(original_entry)
    ),
    SagaStep(
        name="update_vendor_balance",
        forward=lambda: vendor.increment_balance(amount),
        compensate=lambda: vendor.decrement_balance(amount)
    ),
    SagaStep(
        name="schedule_payment",
        forward=lambda: payment.schedule(vendor_id, amount, due_date),
        compensate=lambda: payment.cancel(scheduled_payment_id)
    )
]
```

**Key Principles** [^476^]:
- Compensation need not reverse in exact original order
- Compensation steps may run in parallel where independent
- Business rules apply (e.g., cancellation may not entitle full refund)
- Progress must be recorded so compensation can resume after failure
- Each compensating step must be idempotent

### 9.5 Human Escalation Policy

| Escalation Trigger | Routing | SLA | Auto-Action |
|-------------------|---------|-----|-------------|
| Validation failure (critical) | On-call accountant | 15 min | Block posting |
| Balance mismatch detected | Senior accountant | 30 min | Block period close |
| Duplicate reference | AP manager | 1 hour | Hold for review |
| Amount > entity threshold | Controller | 1 hour | Require dual approval |
| Tax jurisdiction ambiguity | Tax manager | 4 hours | Do not calculate |
| Confidence score < 0.60 | Human accountant | 1 hour | Do not auto-categorize |
| LLM hallucination detected | System admin | 4 hours | Log incident, disable auto-mode |
| Circuit breaker open | Engineering | 1 hour | Use fallback, alert on-call |

---

## 10. Observability

### 10.1 Tracing Architecture

Full tracing captures every agent decision, tool call, and LLM interaction in a hierarchical trace tree [^461^] [^463^].

**Trace Structure:**
```
Trace: "Process invoice INV-2025-0042"
├── Span: Supervisor.route (duration: 120ms, tokens: 450)
│   ├── Span: IntakeAgent.parse_invoice (duration: 2.3s, tokens: 890)
│   │   ├── Span: OCR.extract_text (duration: 1.8s)
│   │   └── Span: LLM.extract_fields (duration: 0.4s, tokens: 890)
│   ├── Span: CategorizationAgent.suggest (duration: 800ms, tokens: 340)
│   │   ├── Span: coa_lookup (duration: 50ms)
│   │   └── Span: memory.retrieve (duration: 120ms)
│   ├── Span: ValidationAgent.validate (duration: 200ms, tokens: 180)
│   │   ├── Span: check_balance (duration: 20ms)
│   │   ├── Span: validate_coa (duration: 30ms)
│   │   └── Span: check_duplicate (duration: 40ms)
│   └── Span: ApprovalGate.request (duration: 45min human)
│       └── Span: PostingAgent.post (duration: 300ms, tokens: 220)
```

### 10.2 Metrics Dashboard

| Metric Category | Key Metrics | Target |
|-----------------|-------------|--------|
| **Routing Quality** | Routing accuracy, tool selection quality | > 95% |
| **Task Completion** | E2E success rate, steps per task, retry rate | > 90% |
| **Latency** | Time to first token, E2E response time, approval wait time | < 5s agent, < 1h approval |
| **Cost** | Tokens per task, cost per task, daily spend | Track, optimize |
| **Quality** | Validation pass rate, human rejection rate, error rate | < 5% rejection |
| **Reliability** | API failure rate, circuit breaker trips, uptime | > 99.9% |

### 10.3 Cost Tracking

Per-task cost attribution by agent:

| Agent | Avg Tokens | Avg Cost | Primary Cost Driver |
|-------|-----------|----------|---------------------|
| Supervisor | 800 | $0.004 | Routing decisions |
| Intake | 2,500 | $0.013 | Document parsing (multimodal) |
| Categorization | 1,200 | $0.006 | COA lookup + memory retrieval |
| Validation | 600 | $0.003 | Rule validation (deterministic) |
| Posting | 1,000 | $0.005 | Journal entry generation |
| Reconciliation | 3,000 | $0.015 | Match analysis |
| Reporting | 2,000 | $0.010 | Report generation |
| Tax | 2,500 | $0.013 | Tax calculation + compliance |
| Audit | 1,500 | $0.008 | Anomaly detection |

### 10.4 Continuous Improvement Loop

The most effective teams build a continuous improvement cycle connecting observability to action [^461^]:

```
Production Traces → Insights Analysis → Evaluation Dataset → Targeted Improvement → Regression Testing
       ↑                                                                                |
       +--------------------------------------------------------------------------------+
```

1. **Monitor**: Track every agent decision, tool call, routing choice
2. **Debug**: Trace through entire chain when things go wrong
3. **Improve**: Make targeted fixes based on actual data
4. **Evaluate**: Create evaluation datasets from production failures
5. **Test**: Regression testing to ensure fixes stay fixed

### 10.5 Observability Tool Selection

| Tool | Role | Overhead | Free Tier |
|------|------|----------|-----------|
| **LangSmith** | Primary tracing and debugging | ~0% latency overhead | 5K traces/month |
| **Langfuse** | Prompt observability, cost tracking | ~15% overhead | 100K observations/month |
| **OpenTelemetry** | Integration with existing infrastructure | Minimal | Open source |
| **Guardrails AI** | Safety and compliance validation | Variable | Available |

**Recommendation**: LangSmith as primary (framework-native, ~0% overhead), Langfuse for detailed prompt/cost analysis.

---

## 11. EU AI Act Compliance

### 11.1 Risk Classification

The accounting AI system is classified as a **high-risk AI system** under Annex III, Section 5(b) of the EU AI Act: "AI systems intended to be used to evaluate the creditworthiness of natural persons or establish their credit score" extends to systems that assess financial health and make decisions affecting access to financial resources [^471^] [^475^].

**Key Compliance Dates:**
- **2 February 2025**: Prohibited practices enforceable + AI literacy requirement
- **2 August 2025**: GPAI model obligations; supervisory authority designation
- **2 August 2026**: Full high-risk system obligations enforceable [^468^] [^469^]
- **Penalties**: Up to EUR 35 million or 7% of global annual turnover [^469^]

### 11.2 High-Risk System Requirements

| Requirement | Article | Implementation |
|-------------|---------|----------------|
| **Risk Management System** | Art. 9 | Continuous risk assessment lifecycle with documented risk register |
| **Data Governance** | Art. 10 | High-quality, unbiased training data; data quality management system |
| **Technical Documentation** | Art. 11 | Complete technical documentation for conformity assessment |
| **Record-Keeping** | Art. 12 | Automatic logging of all events; 6+ year retention |
| **Transparency** | Art. 13 | Users informed they are interacting with AI; clear capability disclosure |
| **Human Oversight** | Art. 14 | Meaningful human oversight with ability to intervene; graduated autonomy model |
| **Accuracy** | Art. 15 | Certified accuracy with regular assessment; accuracy metrics published |
| **Cybersecurity** | Art. 15 | Strong cybersecurity measures; regular penetration testing |
| **Conformity Assessment** | Art. 43 | Third-party conformity assessment before deployment |
| **Registration** | Art. 71 | Registration in EU database before deployment |
| **Post-Market Monitoring** | Art. 72 | Continuous monitoring after deployment; incident reporting |

### 11.3 Human Oversight Implementation (Article 14)

The system's graduated autonomy model directly implements Article 14 requirements [^498^] [^499^]:

- **Meaningful oversight**: Humans can review, approve, reject, or modify every AI decision
- **Intervention capability**: Circuit breakers and kill-switches for immediate halt
- **Competent oversight**: Approver roles matched to required expertise level
- **Oversight by design**: HITL gates are structural, not optional

### 11.4 Transparency Implementation (Article 13 & 50)

- **AI disclosure**: Chat interface clearly indicates AI involvement
- **Capability disclosure**: Users informed of system capabilities and limitations
- **Decision explanation**: Every agent decision includes reasoning trace
- **Audit trail**: Complete decision history available for inspection

### 11.5 Documentation Requirements

| Document | Content | Owner |
|----------|---------|-------|
| **Technical Documentation** | System architecture, algorithms, data sources, training methodology | Engineering |
| **Risk Management Plan** | Identified risks, mitigations, residual risk assessment | Risk/Compliance |
| **Quality Management System** | Data quality processes, validation procedures, accuracy metrics | Data/QA |
| **Human Oversight Protocol** | Oversight procedures, escalation paths, approver qualifications | Operations |
| **Conformity Assessment Report** | Third-party assessment results, compliance certification | Compliance |
| **Post-Market Monitoring Plan** | Monitoring procedures, incident reporting, update procedures | Product |
| **User Instructions** | System capabilities, limitations, proper use, known risks | Product |

### 11.6 Incident Reporting

Serious incidents must be reported to national competent authorities within **15 days** of becoming aware [^472^]. The system implements:

- Automatic detection of serious incidents (balance corruption, unauthorized access)
- Immediate alert to designated responsible person
- Structured incident report generation
- Automated submission to competent authority

---

## 12. Implementation Roadmap

### 12.1 Phase 1: Foundation (Weeks 1-4)

| Deliverable | Description | Success Criteria |
|-------------|-------------|------------------|
| Supervisor agent | Core routing with 8 specialist definitions | > 90% routing accuracy on test set |
| SKILL.md registry | Registry service with 10 initial skills | CRUD operations, discovery, version control |
| WebSocket chat | Real-time chat with session management | < 200ms latency for message delivery |
| Basic HITL | Approval gates for all write operations | 100% of write operations gated |
| Input/output validation | Schema validation + basic accounting checks | All invalid inputs rejected before processing |

### 12.2 Phase 2: Intelligence (Weeks 5-8)

| Deliverable | Description | Success Criteria |
|-------------|-------------|------------------|
| Episodic memory | Mem0 integration for learning categorizations | 80% accuracy on vendor categorization recall |
| Semantic memory | COA knowledge base + business rules | < 100ms COA lookup latency |
| Tool calling (full) | 40+ tools across all accounting domains | All tools with JSON Schema + MCP compatibility |
| Error handling | Circuit breakers, retries, graceful degradation | < 0.1% unhandled errors |
| Observability | LangSmith tracing + metrics dashboard | 100% trace coverage, real-time dashboards |

### 12.3 Phase 3: Production (Weeks 9-12)

| Deliverable | Description | Success Criteria |
|-------------|-------------|------------------|
| HITL graduation | Sampled approvals for low-risk operations | < 5% rejection rate on auto-approved actions |
| Saga pattern | Compensation transactions for multi-step workflows | 100% recoverability tested |
| EU AI Act readiness | Documentation + conformity assessment prep | All Art. 9-15 requirements addressed |
| Performance optimization | Latency < 3s, cost <$0.05 per average task | Benchmarked against Phase 1 baseline |
| Security hardening | Skill signing, sandboxing, penetration testing | Pass security audit |

### 12.4 Phase 4: Scale (Months 4-6)

| Deliverable | Description | Success Criteria |
|-------------|-------------|------------------|
| Multi-entity support | Cross-entity operations with proper isolation | Zero entity data leakage |
| Advanced reporting | Custom report builder with natural language | 20+ report types supported |
| Audit automation | Full audit trail with anomaly detection | > 95% anomaly detection precision |
| Compliance certification | Third-party conformity assessment | EU AI Act high-risk certification |

---

## 13. References

[^16^] CallSphere. "LangGraph Supervisor Pattern: Orchestrating Multi-Agent Teams in 2026." 2026. https://callsphere.ai/blog/langgraph-supervisor-multi-agent-orchestration-2026

[^65^] FindSkill. "OpenClaw Skills: The Complete Guide to Installing, Building, and Securing Custom Skills." 2026. https://findskill.ai/blog/openclaw-skills-guide/

[^73^] OpenClaw Documentation. "Creating skills." https://docs.openclaw.ai/tools/creating-skills

[^461^] LangChain. "AI Agent Observability: Tracing, Testing, and Improving Agents." 2026. https://www.langchain.com/resources/agent-observability

[^462^] QVeris. "Function Calling: OpenAI vs Anthropic vs Google (2026)." 2026. https://qveris.ai/guides/function-calling/

[^463^] AIMultiple. "15 AI Agent Observability Tools in 2026: AgentOps & Langfuse." 2026. https://aimultiple.com/agentic-monitoring

[^464^] Redis. "AI Agent Architecture Patterns: Single & Multi-Agent Systems." 2026. https://redis.io/blog/ai-agent-architecture-patterns/

[^465^] OpenClaw. "ClawHub: Skill + Plugin Registry for OpenClaw." GitHub. https://github.com/openclaw/clawhub

[^467^] Orkes. "Compensation Transaction Patterns - The Key to Handling Failures in Distributed Applications." 2026. https://orkes.io/blog/compensation-transaction-patterns/

[^468^] Banking.Vision. "2025: The first year of AI regulation in Europe." 2026. https://banking.vision/en/2025-the-first-year-of-ai-regulation-in-europe/

[^469^] SpeedNet Software. "How the EU AI Act will change mobile banking apps." 2026. https://speednetsoftware.com/how-the-eu-ai-act-will-change-mobile-banking-apps-on-your-phone/

[^470^] Analytics Vidhya. "Architecture and Orchestration of Memory Systems in AI Agents." 2026. https://www.analyticsvidhya.com/blog/2026/04/memory-systems-in-ai-agents/

[^471^] Eurofi. "AI Act: key measures and implications for financial services." 2024. https://www.eurofi.net/wp-content/uploads/2024/12/ii.2-ai-act-key-measures-and-implications-for-financial-services.pdf

[^472^] European Banking Authority. "AI Act: implications for the EU banking and payments sector." 2025. https://www.eba.europa.eu/sites/default/files/2025-11/

[^473^] Fetch.ai Innovation Lab. "LangGraph Agent | Financial Analysis AI Agent." https://innovationlab.fetch.ai/resources/docs/1.0.1/other-frameworks/financial-analysis-ai-agent

[^474^] OneUptime. "How to Build Chat Applications with LangChain." 2026. https://oneuptime.com/blog/post/2026-02-02-langchain-chat-applications/view

[^475^] Bank of Latvia. "Regulating artificial intelligence in the financial sector." 2025. https://www.bank.lv/en/operational-areas/supervision/ict-security-and-cyber-risks/regulating-artificial-intelligence-in-the-financial-sector

[^476^] Microsoft Azure. "Compensating Transaction Pattern." 2026. https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction

[^477^] Wang et al. "Model Context Protocol (MCP): Landscape, Security..." arXiv:2503.23278. https://arxiv.org/pdf/2503.23278

[^478^] Sharma. "Architecting Multi-Agent Systems with LangGraph: Patterns, Trade-offs, and Real-World Design." Medium, 2026. https://medium.com/@timarkanta.sharma/architecting-multi-agent-systems-with-langgraph-patterns-trade-offs-and-real-world-design-ba8c535c6b35

[^479^] Brenndoerfer. "ReAct Pattern: Interleaving Reasoning and Action for LLM Agents." 2026. https://mbrenndoerfer.com/writing/react-pattern-llm-reasoning-action-agents

[^480^] Yao et al. "Synergizing Reasoning and Acting in Language Models." arXiv:2210.03629, 2022. https://arxiv.org/abs/2210.03629

[^481^] PromptingGuide. "ReAct Prompting." https://www.promptingguide.ai/techniques/react

[^482^] Humanloop. "Model Context Protocol (MCP) Explained." 2025. https://humanloop.com/blog/mcp

[^483^] Schmid. "Model Context Protocol (MCP) an overview." 2025. https://www.philschmid.de/mcp-introduction

[^484^] Galileo. "How to Continuously Improve Your LangGraph Multi-Agent System." 2025. https://galileo.ai/blog/evaluate-langgraph-multi-agent-telecom

[^485^] Li. "ReAct vs Plan-and-Execute: A Practical Comparison of LLM Agent Patterns." Dev.to, 2024. https://dev.to/jamesli/react-vs-plan-and-execute-a-practical-comparison-of-llm-agent-patterns-4gh9

[^487^] Upadhyay. "Exception Handling and Recovery in Agentic AI." 2026. https://atalupadhyay.wordpress.com/2026/03/16/exception-handling-and-recovery-in-agentic-ai/

[^488^] OpenAI. "Structured model outputs." https://developers.openai.com/api/docs/guides/structured-outputs

[^490^] Hannecke. "Resilience Circuit Breakers for Agentic AI." Medium, 2026. https://medium.com/@michael.hannecke/resilience-circuit-breakers-for-agentic-ai-cc7075101486

[^496^] Tan. "AI Agent Error Handling: 5 Patterns to Catch Silent Failures." 2026. https://blog.jztan.com/ai-agent-error-handling-patterns/

[^498^] Hyperbots. "What is Human-in-the-Loop?" 2026. https://www.hyperbots.com/glossary/human-in-the-loop

[^499^] StackAI. "Human-in-the-Loop AI Agents: Approval Workflows." 2026. https://www.stackai.com/insights/human-in-the-loop-ai-agents-how-to-design-approval-workflows-for-safe-and-scalable-automation

[^500^] Hyperbots. "What is Debit Credit Validation?" 2026. https://www.hyperbots.com/glossary/debit-credit-validation

[^501^] MemU. "Mem0 Provides a Universal Memory Layer for AI Personalization." https://memu.pro/blog/mem0-ai-memory-layer-agent-personalization

[^502^] Natoma. "Model Context Protocol: Eliminate Months of Integrating AI." 2025. https://natoma.ai/blog/model-context-protocol-how-one-standard-eliminates-months-of-ai-integration-work

[^503^] AG2 Documentation. "Mem0: Long-Term Memory and Personalization for Agents." https://docs.ag2.ai/latest/docs/ecosystem/mem0/

[^504^] Mem0. "The AI Memory Layer: What It Is, How It Works and Why Agents Need It." 2026. https://mem0.ai/blog/ai-memory-layer-guide

[^507^] Snyk. "From SKILL.md to Shell Access in Three Lines of Markdown." 2026. https://snyk.io/articles/skill-md-shell-access/

[^509^] Ocrolus. "Machine Learning and AI in Lending: Key Applications." 2026. https://www.ocrolus.com/blog/key-applications-human-in-the-loop-machine-learning-lending/

[^510^] Inkle. "Complete Guide to Journal Entry in Accounting." 2024. https://www.inkle.ai/blog/journal-entry-accounting

[^512^] ClawSecure. "ClawHavoc Explained: The Malware Family Targeting OpenClaw Agents." 2026. https://www.clawsecure.ai/blog/clawhavoc-explained

---

*End of Document*
