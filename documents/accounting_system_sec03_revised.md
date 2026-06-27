## 3. Agentic Interface and LLM Chat

The preceding chapters established the system's five-layer architecture and the ledger data model that sits at its core. This chapter turns to the layer that makes the system *LLM-native*: the agentic interface. In a conventional accounting system, an LLM might be bolted on as a chat assistant that queries an existing database. Here, the agent ensemble is the primary interface — every user interaction flows through a supervisor agent that reasons about intent, routes to specialist agents, and coordinates with human approvers before any ledger state changes. This inversion — agents first, API second — is the defining architectural decision of the system.

The chapter proceeds through five sections. Section 3.1 defines the supervisor-plus-specialist topology now restructured around the Model Context Protocol (MCP), Section 3.2 details both the direct WebSocket chat interface and the MCP-first agentic installation interface, Section 3.3 presents the graduated autonomy framework for human oversight, Section 3.4 specifies the dual SKILL registry system, and Section 3.5 closes with safety and reliability mechanisms.

### 3.1 Agent Architecture

#### 3.1.1 MCP-First Supervisor Agent

All user requests enter through a single supervisor agent implementing the ReAct (Reasoning + Acting) pattern [^480^]. The supervisor does not perform accounting work itself; its purpose is to understand what the user wants, decompose the request into discrete tasks, and route each task to the appropriate specialist [^16^]. This separation of routing from execution prevents the supervisor from "doing specialist work itself," a failure mode that degrades routing accuracy and produces un-auditable reasoning chains [^16^].

The supervisor runs GPT-4o-2024-08-06 at temperature = 0, ensuring identical inputs produce identical routing decisions with no stochastic variation [^16^]. The `max_iterations` parameter is set to 20, preventing runaway loops while allowing sufficient depth for multi-step decomposition. In production, the supervisor operates in `last_message` mode, passing only each specialist's final output back into the supervisor's context rather than the full execution trace [^16^]. Full traces are retained in LangSmith for observability but do not consume the supervisor's limited context window.

The supervisor's responsibilities span five domains: intent classification, task decomposition, routing (exactly one specialist per subtask), escalation to humans when confidence falls below threshold, and response synthesis combining specialist outputs into a coherent user-facing response. The target routing accuracy is 95% on the evaluation test set.

**MCP as the universal routing layer.** The supervisor routes to specialists via MCP tool calls (`tools/call`), not through direct function invocation. Each specialist agent exposes its capabilities as an MCP server with a well-defined tool schema. When the supervisor classifies a task as belonging to the Posting domain, it issues an MCP `tools/call` request to the Posting Agent's MCP server with the validated journal entry as parameters. The MCP Gateway handles transport, authentication, and request dispatch across the agent ensemble. Every inter-agent communication is standardized through MCP: the supervisor discovers specialist tools via `tools/list`, invokes them via `tools/call`, and receives structured JSON responses through a single, consistent protocol.

Using MCP for inter-agent routing provides three structural advantages over internal function calls or ad-hoc service meshes. First, MCP is an open protocol — any specialist agent can be implemented in any language as long as it speaks MCP over stdio or HTTP/SSE, eliminating the need for language-specific client libraries, generated stubs, or versioned service definitions. Second, MCP's built-in resource and prompt template primitives provide first-class support for the context-passing patterns accounting workflows require: the Validation Agent can expose a trial balance as an MCP resource via `resources/read`, and downstream specialists can reference the same resource without data duplication. Third, the same MCP tools exposed to the supervisor are discoverable and callable by external agentic clients (Claude Code, Codex CLI, Kolega Code), enabling the system to serve as a tool-equipped backend for any MCP-compatible client without protocol translation layers.

#### 3.1.2 Eight Specialist Agents

The supervisor delegates to eight specialist agents, each responsible for a discrete accounting domain [^16^]. The specialists are composed of a system prompt, a set of MCP tool schemas, and access to both the skill registry (Section 3.4) and the Katra-Agentic-Memory store. Each specialist operates within its own scope and defers out-of-domain requests back to the supervisor.

| Agent | Domain | Primary MCP Tools | HITL Gate |
|-------|--------|-------------------|-----------|
| Intake | Document and transaction ingestion | `parse_invoice`, `parse_receipt`, `parse_bank_statement`, `extract_metadata` | Review for low-confidence extractions |
| Categorization | COA classification | `lookup_coa`, `suggest_category`, `match_vendor_to_account` | Escalate when confidence < 0.80 |
| Validation | Pre-posting compliance checks | `check_debit_credit_balance`, `validate_coa_membership`, `check_duplicate` | Block posting on any failure |
| Posting | General ledger writes | `create_journal_entry`, `post_to_ledger`, `create_reversing_entry` | 100% human approval required |
| Reconciliation | Transaction matching | `match_transactions`, `identify_discrepancies`, `suggest_matches` | Human review for discrepancies |
| Reporting | Financial report generation | `generate_trial_balance`, `generate_pnl`, `generate_balance_sheet` | Exception-only (5% sampled) |
| Tax | Tax calculation and filing | `calculate_vat`, `calculate_income_tax`, `generate_tax_report` | 100% approval for all filings |
| Audit | Anomaly detection and compliance | `generate_audit_trail`, `detect_anomalies`, `explain_transaction` | Human review for flagged anomalies |

The topology follows a star pattern: the supervisor routes to one specialist at a time via MCP `tools/call`, receives the result, and either routes to another specialist for downstream work or returns the response to the user [^16^] [^478^]. For a routine invoice payment, the workflow might traverse Intake → Categorization → Validation → Posting in sequence, with the supervisor orchestrating each handoff and maintaining state across the chain. This sequential routing ensures that each step's output becomes the next step's input under deterministic control.

The Intake Agent handles the document processing pipeline, using a hybrid LLM-plus-OCR architecture to extract structured data from invoices, receipts, and bank statements with 97–98.5% document-level accuracy [^498^] [^525^]. The Categorization Agent applies confidence scoring: at or above 0.95 it auto-categorizes, between 0.80 and 0.94 it proposes for confirmation, and below 0.80 it escalates to a human accountant. The Validation Agent enforces the fundamental accounting equation on every proposed entry, confirming total debits equal total credits within a $0.01 tolerance, all account codes exist in the active COA, the posting period is open, and no duplicate reference numbers are present [^500^].

Most specialists use the ReAct pattern — interleaving reasoning steps with tool invocations — which yields a 34% improvement on decision benchmarks compared to single-shot calling [^480^]. The Posting Agent, however, uses Plan-and-Execute because accounting transactions require auditable, predetermined execution plans rather than dynamic reasoning chains [^485^]. When the Posting Agent receives a validated journal entry, it constructs a complete execution plan (a directed acyclic graph of posting operations) before performing any writes, making the sequence reviewable and deterministic [^485^]. This distinction between ReAct and Plan-and-Execute is not merely stylistic — it ensures that a regulator examining a posted transaction can reconstruct the exact planned sequence of operations rather than inferring it from a chain of opaque reasoning steps.

#### 3.1.3 Katra-Agentic-Memory

Specialist agents do not operate from a blank slate on every request. The Katra-Agentic-Memory subsystem provides three persistent memory layers accessible through dedicated MCP tools.

**Episodic memory** stores timestamped decision records via `memory/storeEpisodic`. When the Categorization Agent classifies an invoice from "Acme Supplies Inc." to account 6100, that decision is recorded as an episodic entry scoped to the entity. Future invoices from the same vendor trigger `memory/retrieveEpisodic` calls, enabling higher-confidence categorization with fewer lookups. Correction events are also stored — when a user changes a categorization from 6100 to 6200, the correction creates a learning signal for future decisions [^503^]. Entity scoping is enforced at retrieval: memories from one legal entity are never visible to agents operating on another, preventing cross-entity data leakage that would violate both data governance policies and auditor expectations.

**Semantic search** via `memory/semanticSearch` provides vector-based retrieval across all stored memories. The supervisor and specialists can query with natural language intent descriptions — "how did we categorize construction equipment purchases last quarter?" — and receive ranked results from episodic records, prior conversation summaries, and knowledge graph nodes. This enables agents to answer questions that require synthesizing information across multiple prior interactions.

**Knowledge graphs** via `memory/queryKnowledgeGraph` maintain structured relationships between entities, vendors, accounts, and decisions. When the Categorization Agent encounters a new vendor, it queries the graph for relationships to similar vendors and associated accounts, enabling informed categorization even for first-time transactions. The graph is continuously updated as new transactions are processed, creating an emergent organizational knowledge base that progressively reduces the need for human intervention on routine transactions.

All three memory layers are scoped by entity and by user role, with access control enforced at the MCP tool boundary: `memory/storeEpisodic` requires an entity ID and rejects writes without it; `memory/semanticSearch` filters results by the caller's entity memberships; `memory/queryKnowledgeGraph` enforces role-based visibility on sensitive vendor and account relationships.

#### 3.1.4 Agent Selection Rationale

The supervisor-plus-specialist topology is driven by empirical performance data and the economics of accounting errors.

| Approach | Avg Tokens | Avg Cost | E2E Success | Optimal For |
|----------|-----------|----------|-------------|-------------|
| Single mega-agent | 4,200 | $0.022 | 71% | Simple tasks; single persona |
| ReAct agent + many tools | 6,800 | $0.038 | 79% | Medium complexity |
| **Supervisor + 4–8 specialists** | **11,400** | **$0.061** | **89%** | **Heterogeneous tasks; specialist tools** |
| Hierarchical (supervisor of supervisors) | 18,200 | $0.097 | 91% | Only past 8+ specialists [^16^] |

The supervisor pattern achieves an 89% end-to-end success rate compared to 71% for a single agent — an 18-percentage-point improvement from LangGraph production data [^16^]. This comes at approximately 3x the per-task cost ($0.061 versus $0.022). For accounting, where a mis-posted entry can require hours of reconciliation and carry regulatory risk, the cost differential is justified by error avoidance. The hierarchical alternative achieves 91% at nearly 5x cost; the diminishing return makes it worthwhile only past eight specialists, which is not the case here [^16^]. The 18-point accuracy lift directly reduces the incidence of ledger errors requiring human correction — a single prevented error can save more in accountant time than the marginal cost difference across thousands of transactions.

The single-agent failure mode is particularly acute for accounting. Weber et al. (2025) demonstrated that LLMs generate fully correct double-entry transactions only 8.33% of the time without guided templates. The multi-agent architecture addresses this by separating categorization from validation from posting, with deterministic checks between each stage. Each specialist can be independently evaluated, improved, and replaced without disrupting the overall workflow — a property that monolithic architectures cannot replicate.

### 3.2 Chat Interface

The system provides two distinct interaction surfaces: a direct WebSocket chat window for human users and an MCP-native agentic interface for agentic users who install and operate the system via SKILL.md. These serve different user profiles — the direct chat for human accountants and business owners, the agentic interface for AI agents, coding assistants, and automation scripts. Both surfaces use the same underlying agent ensemble and skill registry; the difference is in transport and discovery protocol.

#### 3.2a Direct Chat Window

##### WebSocket Protocol

The conversational interface for human users uses a WebSocket connection at `/ws/chat/{session_id}` for full-duplex, bidirectional streaming [^474^]. WebSocket is chosen over Server-Sent Events or long polling because the interaction is genuinely bidirectional: the server streams tokens as the LLM generates its response, while the client sends approval decisions, corrections, or uploaded documents mid-conversation.

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

The protocol supports multi-connection sessions — a single `session_id` can have multiple concurrent WebSocket connections — and automatic history replay on reconnection so users do not lose conversational state. The streaming token design means users see responses build in real time, with latency from first token targeted at under 200 milliseconds for routing decisions and under 5 seconds for end-to-end task completion [^474^]. The typed protocol ensures that both client and server can validate message structure before processing, preventing malformed messages from propagating through the agent pipeline. Session IDs are UUIDv4 values generated by the client and validated by the server on connection.

##### Context Management

Each session maintains a five-layer context model:

| Context Layer | Storage | Lifetime | Purpose |
|--------------|---------|----------|---------|
| Conversation history | Redis | Session | Active message thread; sliding window of last 20 pairs with 8K token budget |
| User preferences | PostgreSQL | Permanent | Business rules, display preferences, default entity and book |
| Episodic memory | Katra-Agentic-Memory | Permanent | Past categorization decisions, correction history, vendor mappings [^501^] |
| Working state | In-memory | Session | Pending approvals, draft operations, tool call history |
| Entity context | Redis | Session | Active company, ledger, accounting period, COA version |

The short-term conversational layer uses Redis for sub-millisecond latency. A sliding window keeps the last 20 message pairs within an 8,000-token budget; when exceeded, older messages are summarized rather than dropped. Sessions have a 24-hour TTL with heartbeat refresh, so idle sessions expire while active sessions persist [^504^]. This tiered storage architecture balances performance against persistence cost: ephemeral conversational data lives in high-speed cache, while durable organizational knowledge lives in persistent stores with appropriate backup and recovery procedures.

Episodic memory is managed via Katra-Agentic-Memory [^501^]. When the Categorization Agent classifies an invoice from "Acme Supplies Inc." to account 6100, that decision is recorded via `memory/storeEpisodic` scoped to the entity. Future invoices from the same vendor trigger `memory/semanticSearch` retrieval, enabling higher-confidence categorization. Correction events are also stored — when a user changes a categorization from 6100 to 6200, the correction creates a learning signal [^503^]. Over time, this episodic layer accumulates organization-specific knowledge that improves accuracy and progressively reduces the need for human intervention on routine transactions.

##### Natural Language Capabilities

The chat interface supports five categories of natural language capability. **Date parsing** resolves relative and absolute expressions ("last month," "Q2 2025," "the 15th") respecting the entity's fiscal year configuration. **Ambiguity resolution** engages clarifying dialogue when input is ambiguous — "Record a payment from Acme" could mean a customer payment or vendor refund — presenting alternatives rather than guessing. **Multi-turn workflows** maintain working state across turns, allowing incremental refinement: "Add another line," "Change line 3 to $450," "Attach the invoice PDF." The agent maintains a draft journal entry in working state, updating it with each turn until the user explicitly confirms the posting. **Error recovery** explains validation failures in natural language with suggested corrections, turning validation errors into educational moments. **Persona selection** offers three modes: *Assistant* (conversational, explanatory, for business owners), *Professional* (concise, technical, for accountants), and *Auditor* (formal, trace-heavy, for compliance work). A business owner using the Assistant persona receives plain-language explanations of why an entry was categorized a certain way, while an accountant using the Professional persona sees COA codes and accounting standards references directly. The Auditor persona includes full reasoning traces and MCP tool call logs with every response, providing the documentary evidence that external auditors and regulators require when reviewing AI-assisted accounting decisions.

#### 3.2b Agentic Interface via SKILL.md + MCP

For agentic users — AI coding assistants, automation agents, and programmatic clients — the system is installed and operated through a single SKILL.md file at the repository root. This file serves as the universal installer: YAML frontmatter defines the MCP server configuration, and markdown instructions teach any MCP-compatible agent how to use the system.

##### SKILL.md YAML Frontmatter

The installation SKILL.md begins with YAML frontmatter that defines the MCP server configuration. An MCP-compatible client reads this frontmatter and automatically registers the accounting system as an available MCP server:

```yaml
---
name: accounting-system
description: Double-entry accounting system with general ledger, AP, AR, tax, and financial reporting via Formance Ledger
version: 0.1.0
author: open-accounting
mcp:
  command: npx
  args: ["-y", "@mcp/server-accounting@latest"]
  env:
    LEDGER_URL: "http://localhost:3068"
    DATABASE_URL: "postgresql://localhost/accounting"
    MEMORY_URL: "http://localhost:7001"
skills:
  - ./skills/general-ledger
  - ./skills/accounts-payable
  - ./skills/accounts-receivable
  - ./skills/tax-calculation
  - ./skills/financial-reporting
  - ./skills/audit-compliance
---
```

The `mcp` block specifies server transport, executable, and required environment variables. The `skills` array points to `/skills/` subdirectories, each containing domain-specific internal skill definitions (see Section 3.4). An MCP client parsing this SKILL.md will: (1) start the MCP server, (2) load all referenced skills, and (3) expose the combined tool set to the agent. The markdown body following the frontmatter contains instruction-bearing content — workflow guidance, hard rules, and error handling — making the SKILL.md simultaneously an installer and a training document.

##### Per-Platform Installation

The SKILL.md is consumed by any MCP-compatible client. Installation varies by platform but follows the same pattern: register the MCP server, verify tool discovery, begin operation.

| Platform | Installation Method | Tool Discovery |
|----------|-------------------|----------------|
| OpenClaw | `openclaw skill install /path/to/SKILL.md` | Automatic via `tools/list` on first connection |
| Claude Code | Add to `.claude/mcp.json` with `command` and `args` from frontmatter | `tools/list` response drives tab completion |
| Codex CLI | Add to `codex.yaml` `mcp.servers` array | Discovers on startup; lists in `/tools` command |
| Kolega Code | Import via `kolega skill import ./SKILL.md` | Full-text search across skill descriptions |
| OpenCode | Add to `opcode.config.js` MCP server registry | Discovers on workspace load |
| Hermes | `hermes skill add --file SKILL.md` | Browseable skill catalog with auto-generated docs |

On OpenClaw, `openclaw skill install` parses the YAML frontmatter, starts the MCP server subprocess, and makes all tools immediately available. The supervisor's routing decisions are accessible as OpenClaw skill calls — "post this invoice" resolves to the same Intake → Categorization → Validation → Posting chain whether invoked through WebSocket chat or OpenClaw's skill interface. On Claude Code, the developer adds the MCP server to `.claude/mcp.json`; Claude Code calls `tools/list` on connection and surfaces accounting tools through its `/tools` command. The SKILL.md is not locked to any single platform — a user can install the accounting system into Claude Code for interactive development, switch to Codex CLI for CI/CD automation, and use Hermes for documentation browsing, all referencing the same SKILL.md and the same underlying MCP server.

##### Tool, Resource, and Prompt Discovery

Once registered, the agent discovers capabilities through three standard MCP primitives:

**Tool discovery** via `tools/list` returns all available tools with JSON Schema parameter definitions. The system exposes approximately 40–50 tools across eight specialist domains, organized by MCP naming convention: `intake/parseInvoice`, `categorization/suggestCategory`, `posting/createJournalEntry`, `reporting/generateTrialBalance`, etc. Each tool listing includes description, parameter schema, and optional annotation flags (`readOnly`, `destructive`, `idempotent`).

**Resource templates** via `resources/list` expose structured data sources the agent can read but not modify: the trial balance (`ledger://trial-balance/{ledger}`), chart of accounts (`ledger://coa/{entity}`), open posting periods (`ledger://periods/{entity}/open`), and audit trails (`audit://trail/{entity}?from={date}&to={date}`). Resources follow URI template syntax, allowing agents to construct identifiers from context variables.

**Prompt templates** via `prompts/list` provide reusable prompt patterns for complex workflows: "Post a journal entry," "Reconcile this bank statement," "Generate month-end close," and "Explain this transaction." Each template defines required arguments and produces a structured prompt the supervisor can execute, reducing the need for agents to construct multi-step instructions from scratch.

This three-primitive model (tools, resources, prompts) means an agentic user never needs to read API documentation. They install the SKILL.md, the client discovers all capabilities automatically, and the agent can begin posting journal entries, generating reports, and reconciling accounts through natural language intent routed to the appropriate MCP tools.

### 3.3 Human-in-the-Loop Framework

#### 3.3.1 Graduated Autonomy Model

The system implements a graduated autonomy model in which agent freedom increases as reliability is demonstrated [^499^]. Phase 1 (Weeks 1–4, "Supervised") requires 100% human approval for all ledger-modifying actions. Phase 2 (Weeks 5–12, "Sampled") maintains 100% approval for high-risk actions while reducing low-risk actions to 20% sampled approval. Phase 3 (Months 3–6, "Exception-only") auto-approves low-risk actions and approves medium-risk actions only when exception triggers fire. Phase 4 (Months 6+, "Full autonomy") operates on exception-only approval for all actions, with policy triggers defining exceptions: amounts above entity thresholds, transactions to sensitive accounts, activity outside business hours, or pattern-based anomaly flags [^499^].

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

The matrix reflects a fundamental principle: the more costly and irreversible an action, the more stringent its approval. Posting a journal entry is high-cost and low-reversibility because a reversing entry creates audit trail complexity and may affect period-end balances. Generating a report is low-cost because reports are read-only — a bad report can be regenerated in seconds. Tax filing submission carries the highest rating because an incorrect filing can trigger penalties, interest charges, and regulatory scrutiny extending far beyond the accounting department. This matrix is enforced by the Validation Agent programmatically: every proposed action is checked against the matrix, and the agent cannot proceed until the required approvals are recorded in the system.

#### 3.3.3 Four Approval Workflow Patterns

The framework implements four approval patterns selected by action type and risk level [^499^].

**Pattern 1: Action-level gate.** The agent proposes a specific tool call with full parameters and waits for explicit approval. Used for all posting operations and tax filings. The proposal includes action type, parameters, risk assessment, rollback plan, and confidence score. If the approval timeout expires (15–60 minutes for posting), the action escalates to a senior approver.

**Pattern 2: Draft approval.** The agent produces a draft — a journal entry, report, or reconciliation proposal — for human review and editing. The human can edit any field or reject the draft; the agent incorporates feedback and resubmits.

**Pattern 3: Dual approval.** High-risk operations require two separate approvers with different roles, implementing separation-of-duties required by SOX and internal controls. Deleting a posted entry, modifying a closed period, or submitting a tax return all require dual approval — for example, a finance manager and a controller.

**Pattern 4: Exception-only review.** The agent auto-approves low-risk actions unless a policy trigger fires: amount above threshold, transaction to a sensitive account, unknown vendor, activity outside business hours, or anomaly score above threshold. This pattern is used for standard report generation, reconciliation auto-matches, and low-value categorizations where the cost of human review exceeds the cost of an occasional error.

### 3.4 SKILL Registry

The system maintains two skill registries that serve different purposes: the **installation SKILL.md** at the repository root defines how agentic clients install and discover the accounting system, while the **internal skill registry** in the `/skills/` directory defines the accounting operations that specialist agents execute. Both follow the OpenClaw SKILL.md format — a folder-based system where each skill is a directory containing a `SKILL.md` file with YAML frontmatter and markdown instructions [^65^] [^73^]. The format is local-first (skills load from filesystem without compilation), SDK-free (no special runtime), discoverable via vector search, and versioned [^65^].

#### 3.4.1 Installation SKILL.md (Repository Root)

The SKILL.md file at the repository root is the universal installer for agentic users. Its YAML frontmatter contains MCP server configuration — command, arguments, environment variables — that tells any MCP-compatible client how to start the accounting system's MCP server. The `skills` array within the frontmatter points to subdirectories under `/skills/`, establishing the connection between the installation manifest and the internal skill registry.

The markdown body serves as instruction-bearing content for agentic clients: an overview of system capabilities in natural language, common workflow descriptions that help agents map user intent to accounting operations, hard rules that apply across all skills (e.g., "ALWAYS check the posting period is open before creating a journal entry," "NEVER delete a posted entry — always create a reversing entry"), and error handling guidance for common failure modes (closed period, unbalanced entry, duplicate reference).

When a user installs this SKILL.md into Claude Code, Codex CLI, or OpenClaw, the client: parses the frontmatter to start the MCP server, calls `tools/list` to discover all tools, calls `resources/list` for data sources, calls `prompts/list` for workflow templates, and reads the markdown body to learn how to use the system. The installation is complete in seconds — no Docker containers, no API keys, no manual configuration beyond the initial MCP server connection.

#### 3.4.2 Internal Skill Registry (/skills/ Directory)

The internal skill registry in `/skills/` defines the accounting operations that specialist agents execute. Each subdirectory contains a `SKILL.md` with YAML frontmatter and markdown instructions specific to an accounting domain.

| Field | Type | Purpose |
|-------|------|---------|
| `metadata.accounting.domain` | string | Domain: `general_ledger`, `ap`, `ar`, `tax`, `reporting` |
| `metadata.accounting.risk_level` | enum | `low` / `medium` / `high` — determines approval workflow |
| `metadata.accounting.requires_approval` | boolean | Whether this skill always requires human approval |
| `metadata.accounting.audit_trail` | boolean | Whether every invocation is logged |
| `metadata.requires.env` | array | Required environment variables |
| `metadata.dependencies` | array | Cross-skill dependencies with version constraints |

Skills load in strict precedence: workspace skills (`<workspace>/skills/`) override user skills (`~/.openclaw/skills/`), which override bundled system defaults. Discovery uses vector search: the supervisor embeds the intent description and searches for semantically similar skills, loading the top-$k$ results into the specialist's context. This decouples capability from code — adding a skill makes new functionality available immediately without redeployment.

The internal registry is organized by domain, mirroring the eight specialist agents:

| Directory | Domain | Example Skills |
|-----------|--------|---------------|
| `/skills/general-ledger/` | Core ledger operations | `post-journal-entry`, `create-reversing-entry`, `close-period` |
| `/skills/accounts-payable/` | Vendor and payment management | `process-invoice`, `schedule-payment`, `vendor-onboarding` |
| `/skills/accounts-receivable/` | Customer and collection workflows | `create-invoice`, `record-payment`, `dunning-process` |
| `/skills/tax-calculation/` | Tax computation and filing | `calculate-vat`, `calculate-income-tax`, `generate-tax-report` |
| `/skills/financial-reporting/` | Report generation | `trial-balance`, `profit-and-loss`, `balance-sheet`, `cash-flow` |
| `/skills/audit-compliance/` | Audit and anomaly detection | `generate-audit-trail`, `detect-anomalies`, `explain-transaction` |
| `/skills/bank-reconciliation/` | Reconciliation workflows | `match-transactions`, `identify-discrepancies`, `suggest-matches` |
| `/skills/multi-currency/` | Foreign exchange operations | `record-fx-transaction`, `revalue-currency`, `translation-adjustment` |

Each skill maps directly to one or more MCP tools exposed by the specialist agents. The skill `post-journal-entry` in `/skills/general-ledger/` corresponds to the Posting Agent's `posting/createJournalEntry` MCP tool. This bidirectional mapping ensures that skill documentation, agent capabilities, and client-discoverable tools remain synchronized.

#### 3.4.3 Security Model (Post-ClawHavoc)

The ClawHavoc incident in February 2026 — 341+ malicious skills discovered on ClawHub, 20% of packages compromised — demonstrated that skill-based systems face supply chain risks comparable to traditional software dependencies [^507^] [^512^]. Attack vectors included command-and-control callbacks, credential harvesting, data exfiltration, and prompt injection. The root cause was the absence of cryptographic signing, sandboxing, or verification [^65^].

| Layer | Control | Implementation |
|-------|---------|----------------|
| Upload scanning | SHA-256 + VirusTotal | All skills scanned for known malware before activation |
| Daily rescanning | Continuous monitoring | Existing skills rescanned against updated threat signatures |
| Code signing | Cryptographic verification | All skills signed by a trusted authority; unsigned skills rejected |
| Sandboxing | Docker isolation | Skill execution in restricted containers |
| Permission model | Least-privilege | Skills access only resources declared in `metadata.requires` |
| Network restrictions | Deny-by-default | No outbound network calls unless whitelisted |

These controls ensure a compromised skill cannot exfiltrate data (deny-by-default network egress), access unauthorized resources (least-privilege), or persist on the system (daily rescanning). Docker sandboxing prevents host system escape even if the skill execution runtime is exploited. Every skill invocation is logged with skill name, version, parameters, output, and execution duration, satisfying EU AI Act Article 12 requirements for automatic event logging [^469^]. The security model transforms skill management from an uncontrolled distribution channel into a governed, auditable capability lifecycle.

#### 3.4.4 Skill Growth Trajectory

The registry grows across four phases. Phase 1 (MVP) ships with 25+ skills covering core workflow: transaction entry, invoice processing, payment recording, bank reconciliation, trial balance, and basic tax calculation. Phase 2 (Months 3–5) expands to 65+ skills with advanced reporting, multi-currency handling, intercompany transactions, and accrual management. Phase 3 (Months 6–9) reaches 120+ skills with industry-specific packs (retail, professional services, construction, e-commerce) and audit automation. Phase 4 (Year 2+) targets 190+ skills with custom report builder skills, regulatory compliance packs for additional jurisdictions, and third-party integrations. Each skill is a `SKILL.md` file that domain experts (accountants, tax specialists) can author without writing code, making skill growth a parallel activity to core engineering.

### 3.5 Safety and Reliability

#### 3.5.1 Five-Layer Input and Output Validation

Every user input passes through a five-layer validation pipeline before reaching any agent, and every agent output passes through a complementary five-layer pipeline before any system modification.

The **input pipeline** proceeds: Syntax (JSON/schema validation), Semantic (type checking and range validation), Authorization (user permissions and entity access, logging security events on violation), Content Safety (PII detection and prompt injection scanning), and Business Rules (entity match, period open, COA valid, amounts within bounds).

The **output pipeline** proceeds: Schema (JSON Schema strict validation, retrying up to 3 times on failure) [^488^], Accounting Rules (debits equal credits, valid COA membership, double-entry conventions) [^500^], Balance Check (trial balance integrity after proposed posting), Duplicate Check (reference number uniqueness) [^514^], and Anomaly Detection (statistical outlier detection flagging unusual entries for review).

The Validation Agent executes the full output pipeline before any journal entry reaches the Posting Agent. It confirms: debits equal credits within $0.01, all codes exist in the active COA, the period is open, entity ID matches context, reference is unique, required fields are populated, amounts are positive and within bounds, and the approval workflow for the entry's risk level is complete.

#### 3.5.2 Error Taxonomy and Graceful Degradation

Agent failures fall into three categories [^490^]. **Hard failures** (API timeout, rate limit, database failure, malformed LLM response) trigger retry with exponential backoff (max 3 retries, 2–30 second range), then escalation. **Structural failures** (invalid JSON, missing fields, schema violation, invalid tool parameters) trigger retry with clearer formatting instructions, then fallback to a simpler output format. **Semantic failures** (hallucinated account codes, incorrect categorizations, confident falsehoods) are the most dangerous because they can pass validation and reach the ledger; the strategy is to flag as uncertain and escalate to human review. The anomaly detection layer (Layer 5 of output validation) specifically catches semantic failures by identifying statistically unusual outputs — for instance, a journal entry with an amount three standard deviations above the entity's historical average, or an account combination that has never appeared in prior transactions.

When full-capability response is not possible, the system degrades through four levels [^487^]: Level 0 (Full — all systems operational), Level 1 (Cached — API rate limit; uses stale but valid cached data), Level 2 (Restricted — LLM unavailable; deterministic rule-based responses only), and Level 3 (Human-only — critical failure; immediate human escalation). The progression from Level 0 to Level 3 is automatic and reversible — when the LLM API recovers from an outage, the system transitions from Level 2 back to Level 0 without manual intervention. Circuit breakers on each external service prevent cascading failures: a failure threshold of 5 consecutive errors opens the circuit, which enters half-open after 60 seconds and permits 3 test calls before returning to full operation [^490^] [^494^].

For multi-step workflows, the Saga pattern with compensating transactions ensures eventual consistency [^467^] [^476^]. Each step has a forward action and compensating undo. If step 3 of a 5-step workflow fails, compensating transactions for steps 2 and 1 execute in reverse order, returning the ledger to its pre-workflow state. Every compensating step is idempotent — executing it twice produces the same result as once — so the system can safely retry compensation after a partial failure. The Saga pattern is essential for accounting workflows where partial completion would leave the ledger in an inconsistent state, such as an invoice processing workflow that creates a payable, updates vendor balance, and schedules a payment — if the payment scheduling fails, the prior steps must be undone to maintain balance integrity. Without compensating transactions, a failed workflow could leave a payable recorded without the corresponding vendor balance update, creating a discrepancy that would surface only at month-end reconciliation. The Saga coordinator logs every step and compensation attempt, producing an auditable trail of the recovery process that satisfies both operational debugging needs and regulatory examination requirements.

#### 3.5.3 EU AI Act Compliance

The system is classified as a high-risk AI system under Annex III, Section 5(b) of the EU AI Act, covering AI systems that assess financial health and affect access to financial resources [^471^] [^475^]. The full enforcement deadline is August 2, 2026, with penalties up to EUR 35 million or 7% of global turnover [^469^].

| Requirement | Article | Implementation |
|-------------|---------|----------------|
| Risk management | Art. 9 | Continuous risk assessment with documented register; quarterly review |
| Data governance | Art. 10 | Training data quality management; bias detection in models |
| Technical documentation | Art. 11 | Complete architecture docs; algorithm descriptions; data inventories |
| Record-keeping | Art. 12 | Automatic logging of all decisions, tool calls, approvals; 6+ year retention |
| Transparency | Art. 13 | AI disclosure in chat; capability statements; decision explanations |
| Human oversight | Art. 14 | Graduated autonomy with meaningful review; circuit breakers; competent approvers [^498^] [^499^] |
| Accuracy | Art. 15 | Certified accuracy metrics per release; regular validation |
| Cybersecurity | Art. 15 | Defense-in-depth; penetration testing; skill supply chain scanning |
| Conformity assessment | Art. 43 | Third-party assessment before EU deployment |
| Post-market monitoring | Art. 72 | Continuous monitoring; incident reporting within 15 days [^472^] |

The Article 12 record-keeping requirement is satisfied architecturally. Every agent decision is logged: the natural language request, the supervisor's routing decision with reasoning trace, specialist MCP tool calls with parameters and responses, validation results, human approval decisions, and the final ledger posting with transaction ID. Because Formance Ledger is append-only and hash-chained, the ledger entry serves as tamper-evident proof of final state while the agent decision log provides the explanatory provenance the EU AI Act requires [^469^].

Article 14 human oversight is implemented through the graduated autonomy model (Section 3.3.1): humans review every AI decision before it affects the ledger, can reject or modify any proposed action, circuit breakers enable immediate system halt, and approver roles match required expertise levels [^498^] [^499^]. The approval framework governing AI posting of a journal entry is the same framework enforcing CFO approval for payments over $5,000 — one trust interface serves both AI safety and financial control. This convergence eliminates the need for separate "AI oversight" and "financial approval" systems, reducing engineering effort while providing approvers with both financial context and AI decision context (confidence score, alternative options, reasoning trace) in a single screen.

Serious incidents (balance corruption, unauthorized access, regulatory filing errors) must be reported to the national competent authority within 15 days [^472^]. The August 2026 deadline creates a compliance window: competitors without AI audit trails face a 12–18 month rebuild, while this system enters the EU market with compliance embedded from the ground up [^469^].
