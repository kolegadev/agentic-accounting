
# Agentic Accounting — User Manual

**Version 0.1.0 (MVP)**  
**Last updated: June 2026**

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Installation & Setup](#2-installation--setup)
   - [2a. System Requirements](#2a-system-requirements)
   - [2b. Installation](#2b-installation)
   - [2c. First-Time Setup](#2c-first-time-setup)
3. [Pathway A: User-Directed (Chat UI)](#3-pathway-a-user-directed-chat-ui)
   - [3a. Starting the Chat UI](#3a-starting-the-chat-ui)
   - [3b. Daily Bookkeeping](#3b-daily-bookkeeping)
   - [3c. Chart of Accounts](#3c-chart-of-accounts)
   - [3d. Contacts](#3d-contacts)
   - [3e. Invoicing](#3e-invoicing)
   - [3f. Bank Import & Reconciliation](#3f-bank-import--reconciliation)
   - [3g. VAT & MTD](#3g-vat--mtd)
   - [3h. Reports](#3h-reports)
4. [Pathway B: AI Agent-Directed (MCP Tools)](#4-pathway-b-ai-agent-directed-mcp-tools)
   - [4a. Setting Up Your Agent](#4a-setting-up-your-agent)
   - [4b. MCP Tool Reference](#4b-mcp-tool-reference)
   - [4c. Agent Conversation Examples](#4c-agent-conversation-examples)
5. [Multi-User Setup](#5-multi-user-setup)
6. [Approval Workflows](#6-approval-workflows)
7. [Recurring Transactions](#7-recurring-transactions)
8. [Bank Rules Engine](#8-bank-rules-engine)
9. [Troubleshooting](#9-troubleshooting)
10. [Data Privacy & Backup](#10-data-privacy--backup)
11. [Uninstall](#11-uninstall)

---

## 1. Introduction

Agentic Accounting is a **headless, LLM-native double-entry accounting system** designed for UK small businesses. It manages real business finances—chart of accounts, general ledger, contacts, bank imports, reconciliation, invoicing, VAT returns, and financial reports—all stored locally on your machine with zero cloud dependency.

### Who It's For

- **Sole traders**, **limited companies**, and **partnerships** in the UK
- Business owners who want conversational bookkeeping without learning accounting software
- Accountants and bookkeepers managing multiple clients
- Developers and power users who want to automate accounting via AI agents

### Two Operating Modes

Agentic Accounting offers two distinct pathways to the same underlying system:

| Pathway | How You Interact | Best For |
|---|---|---|
| **Pathway A: User-Directed** | Typing natural language in a chat UI (`http://localhost:3000`) | Day-to-day bookkeeping by business owners; quick lookups; anyone who prefers typing questions |
| **Pathway B: AI Agent-Directed** | An MCP-compatible AI agent (Claude Code, OpenClaw, Kolega Code) calls tools autonomously on your behalf | Complex multi-step workflows; batch operations; developers integrating accounting into agent pipelines |

Both pathways use the same MCP gateway (port 3112) and the same accounting API (port 8000). They differ only in how you issue commands—directly in a chatbox or through an AI agent that reasons and chains multiple tools together.

> **Key Concept:** You do not need an AI agent to use the system. The Chat UI (Pathway A) gives you the same conversational experience directly. Use Pathway B when you want an AI agent to handle multi-step reasoning, schedule recurring reports, or integrate accounting into your developer workflow.

---

## 2. Installation & Setup

### 2a. System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| **Operating System** | macOS, Linux, or Windows (WSL2) | macOS 14+ / Ubuntu 22.04+ |
| **RAM** | 4 GB | 8 GB |
| **Disk Space** | 2 GB free | 10 GB free (for stored documents) |
| **Docker** | Docker 24+ with Docker Compose v2 | Latest stable |
| **Python** | 3.11+ (development only) | 3.12+ |
| **Available Ports** | 3000, 3112, 5432, 6379, 8000, 9000, 9001 | These must not be in use |

**Optional (Pathway B only):**
- Claude Code (Claude Desktop or VS Code extension)
- OpenClaw agent
- Kolega Code agent
- Any MCP-compatible SSE client

### 2b. Installation

Three commands get you running:

```bash
# Step 1: Clone the repository
git clone https://github.com/kolegadev/agentic-accounting.git
cd agentic-accounting

# Step 2: (Optional) Customise environment variables
cp .env.example .env
# Edit .env to change passwords or port mappings if needed

# Step 3: Start all core services
docker compose up -d
```

**What happens:**
- PostgreSQL 16 (primary double-entry ledger)
- Redis 7 (caching & session store)
- MinIO (document & statement object storage)
- Accounting API (FastAPI on port 8000)
- MCP Gateway (port 3112 — the bridge for both pathways)
- Formance Ledger (v2, dual-entry verification engine)

**Verify everything is healthy:**

```bash
docker compose ps
# All services should show "healthy" or "running"

curl http://localhost:3112/health
# → {"status":"ok"}
```

### 2c. First-Time Setup

Before you can record anything, the system needs to know about your business. This setup works identically whether you use the Chat UI (Pathway A) or an AI agent (Pathway B).

#### The "Set Up My Business" Conversation

Start a conversation with:

> **"Set up my business"**

The system will guide you through five steps. You answer questions conversationally.

**Step 1: Business Type**

Choose one of:
- **Sole Trader** (with or without VAT registration)
- **Limited Company** (Ltd Co, with or without VAT)
- **Partnership** (with or without VAT)

Also available:
- **Micro-Entity Simplified** — minimal COA for very small businesses
- **Property Landlord** — specialised template for property rental income

This choice determines your default Chart of Accounts template (see below).

**Step 2: VAT Registration Status**

- **VAT-registered**: You charge VAT on sales and reclaim VAT on purchases. Standard, Cash Accounting, or Flat Rate scheme.
- **Not VAT-registered**: Simpler accounting; no VAT tracking needed. (Flat Rate scheme not available.)

> You can change your VAT status later. The system will handle the transition.

**Step 3: Chart of Accounts (COA) Template**

Based on your business type and VAT status, the system selects a COA template:

| Template | Accounts | Use Case |
|---|---|---|
| `uk_sole_trader_no_vat` | 40 | Sole trader below VAT threshold |
| `uk_sole_trader_vat` | 55 | VAT-registered sole trader |
| `uk_limited_company_no_vat` | 50 | Ltd Co below VAT threshold |
| `uk_limited_company_vat` | 65 | VAT-registered Ltd Co (full range) |
| `uk_partnership_no_vat` | 45 | Partnership below VAT threshold |
| `uk_partnership_vat` | 60 | VAT-registered partnership |
| `micro_entity_simplified` | 30 | Minimal accounts for micro-entities |
| `property_landlord_vat` | 45 | Property income with VAT |

All templates follow UK-standard 4-digit numbering:
- **1000–1999**: Assets (bank accounts, debtors, fixed assets)
- **2000–2999**: Liabilities (creditors, loans, VAT payable)
- **3000–3999**: Equity (capital, drawings, retained earnings)
- **4000–4999**: Revenue (sales, other income)
- **5000–6999**: Expenses (cost of sales, overheads)

You can customise the COA at any time (see Section 3c).

**Step 4: Financial Year End**

Set your financial year end date (e.g., "31 March" or "5 April"). This determines:
- Default reporting periods
- VAT quarter boundaries (if applicable)
- Year-end closing procedures

**Step 5: Preferred Persona**

Choose how the system talks to you:
- **Professional**: Formal, precise, full sentences. Best for accountants.
- **Friendly**: Warm, conversational, encouraging. Best for business owners new to bookkeeping.
- **Minimal**: Short, terse, results-only. Best for power users and developers.

You can change your persona at any time:
> **"Switch to minimal persona"**

**Step 6: Add Bank Accounts**

Add at least one bank account so you can track balances:

> **"Add my Barclays business current account, sort code 20-00-00, account number 12345678"**

You can add multiple accounts (current, savings, credit card, PayPal, etc.).

---

## 3. Pathway A: User-Directed (Chat UI)

### 3a. Starting the Chat UI

The Chat UI is an optional service (not started by default):

```bash
docker compose --profile ui up -d
```

Open your browser to:

```
http://localhost:3000
```

You will see a chat interface. The initial "Set Up My Business" flow runs automatically on first visit. After setup, you are ready to bookkeep.

**How the chat works:**
- Type natural language into the chatbox
- The system parses your intent (expense, income, invoice, report, etc.)
- It may ask clarifying questions (e.g., "Which VAT rate?")
- Confirmed actions create real accounting entries immediately

**Keyboard shortcuts:**
- `Enter` — send message
- `Shift+Enter` — new line (multi-line messages)
- `Up Arrow` — recall last message (edit & resend)

### 3b. Daily Bookkeeping

Everyday bookkeeping is conversational. Here are the patterns.

#### Recording an Expense

> **You:** Paid £50 for office supplies at Tesco  
> **System:** Got it. Recording an expense of £50.00 to Office Supplies. Is that with standard 20% VAT?  
> **You:** Yes  
> **System:** Recorded. Expense £50.00 + £10.00 VAT = £60.00 total from your current account.

**What happens:** A double-entry transaction is created:
- Debit: Office Supplies (Expense) £50.00
- Debit: VAT Input (Asset) £10.00
- Credit: Bank Current Account (Asset) £60.00

#### Recording Income

> **You:** Received £1,200 from Acme Ltd for consulting  
> **System:** Recording income of £1,200.00 from Acme Ltd. VAT rate?  
> **You:** 20%  
> **System:** Recorded. Income £1,200.00 (£1,000.00 net + £200.00 VAT) to Consulting Revenue.

#### Recording a Bank Transfer

> **You:** Transferred £1,000 from current to savings  
> **System:** Recorded. £1,000.00 transferred from Current Account to Savings Account.

#### Listing Transactions

> **You:** Show me last month's transactions  
> **System:** *[Displays a table of all transactions from the previous calendar month]*

Filtering options:
- `"Show transactions for June 2026"`
- `"Show all expenses with Acme"`
- `"Show transactions in Marketing account"`
- `"Last 20 transactions"`

#### Viewing Transaction Details

> **You:** Show me transaction JE-2026-0042  
> **System:** *[Displays the full journal entry with all postings, VAT lines, contact, and status]*

#### Undoing a Mistake

> **You:** Undo that last entry  
> **System:** You want to reverse "Office Supplies at Tesco — £50.00"? This cannot be deleted; I'll create a reversing entry. Confirm?  
> **You:** Yes  
> **System:** Reversed. New entry JE-2026-0043 cancels JE-2026-0042. Both remain in your audit trail.

> **Important:** Transactions are never deleted. Undo creates a compensating reversing entry. This preserves your full audit trail for HMRC compliance.

If you know the transaction ID:
> **You:** Undo transaction JE-2026-0042

### 3c. Chart of Accounts

#### Listing Your COA

> **You:** Show my chart of accounts  
> **System:** *[Displays all active accounts grouped by category with codes, names, types, and VAT rates]*

To see inactive accounts:
> **You:** Show all accounts including inactive ones

#### Adding an Account

> **You:** Add a new account called Marketing Expenses under 5210  
> **System:** Got it. Category: Expense, Type: Expense. What VAT rate?  
> **You:** 20% standard  
> **System:** Created. Account 5210 — Marketing Expenses (Expense, Standard VAT 20%).

You can specify everything at once:
> **You:** Add account 5210 Marketing, Expense category, 20% standard VAT

#### Editing an Account

> **You:** Rename account 6100 to Software Subscriptions  
> **System:** Updated. Account 6100 renamed to Software Subscriptions.

#### Setting VAT Rates

> **You:** Set VAT rate on account 4000 to zero-rated  
> **System:** Updated. Account 4000 (Sales) VAT rate set to 0% (zero-rated).

Valid VAT rates: `20%`, `5%`, `0%`, `exempt`

### 3d. Contacts

Contacts are customers, suppliers, or both. The system tracks balances and transaction history per contact.

#### Creating a Contact

> **You:** Add ABC Ltd as a customer, email john@abcltd.com, phone 020 7946 0000  
> **System:** Created. ABC Ltd (customer). Email: john@abcltd.com, Phone: 020 7946 0000.

> **You:** Add Office Supplies Ltd as a supplier, email orders@officesupplies.co.uk  
> **System:** Created. Office Supplies Ltd (supplier). Email: orders@officesupplies.co.uk.

Contact types: `customer`, `supplier`, `both`, `other`.

#### Listing Contacts

> **You:** Who are my suppliers?  
> **System:** *[Lists all active supplier contacts]*

> **You:** Show all contacts  
> **System:** *[Lists all active contacts of all types]*

#### Viewing Contact Details & Balance

> **You:** Show ABC Ltd's balance  
> **System:** ABC Ltd — Total Invoiced: £12,500.00 | Total Paid: £8,200.00 | Owing: £4,300.00. Status: Active.

#### Editing a Contact

> **You:** Update Acme Ltd's phone to 020 7946 1111  
> **System:** Updated. Acme Ltd phone number changed.

#### Archiving a Contact

> **You:** Archive old supplier XYZ Corp  
> **System:** Archived. XYZ Corp moved to archive. Historical transactions preserved.

Archived contacts are hidden from lists but preserved in the database. They can be unarchived if needed.

### 3e. Invoicing

#### Creating an Invoice

> **You:** Create invoice for ABC Ltd: 10 hours consulting at £80/hr plus VAT  
> **System:** Invoice INV-2026-0012 — ABC Ltd. 10 hours × £80.00 = £800.00 + £160.00 VAT (20%) = £960.00 total. Issue date today, due in 30 days. Create?  
> **You:** Yes  
> **System:** Created. INV-2026-0012 saved as Draft. Say "Send INV-2026-0012" when ready.

Multi-line invoices:
> **You:** Create invoice for Acme: Website design £2,500, Hosting setup £250, both at 20% VAT  
> **System:** *[Displays line items and total. Confirm to create.]*

Invoice statuses:
- **Draft** — editable, not yet sent
- **Sent** — immutable (cannot be edited; corrections require credit notes)
- **Viewed** — customer has opened/viewed the PDF
- **Paid** — payment received in full
- **Overdue** — past due date, not paid
- **Cancelled** — voided

#### Sending an Invoice

> **You:** Send invoice INV-2026-0012 to john@abcltd.com  
> **System:** INV-2026-0012 sent to john@abcltd.com. Status: Sent. PDF generated and attached.

> **Important:** In the MVP, emails are output to a local file rather than actually sent via SMTP. Full email delivery comes in Phase 2. You can download the PDF via `GET /api/v1/invoices/{id}/pdf`.

#### Marking an Invoice as Paid

> **You:** Mark invoice INV-2026-0012 as paid — £960 received today  
> **System:** INV-2026-0012 marked as Paid. £960.00 recorded as income against ABC Ltd. AR balance updated.

The system automatically records the corresponding income transaction in the ledger.

#### Credit Notes

> **You:** Create a credit note for £200 against invoice INV-2026-0012 — overcharge on hosting  
> **System:** Credit Note CN-2026-0005 created. £200.00 credited against INV-2026-0012. Total originally £960.00, net after credit £760.00.

Credit notes generate CN-YYYY-NNNN references, linked to the original invoice. They offset the original amount.

#### Overdue Check

> **You:** Which invoices are overdue?  
> **System:** *[Lists all invoices past due date not in Paid/Cancelled status, with days overdue and amounts]*

> **You:** Send reminders for all overdue invoices  
> **System:** *[Confirms which invoices would get reminders. Full reminder automation in Phase 2.]*

### 3f. Bank Import & Reconciliation

#### Importing Bank Statements

**CSV Import:**
> **You:** Import my Barclays CSV statement  
> **System:** Which bank account?  
> **You:** Barclays current  
> **System:** Where is the file? I need the path on your machine.  
> **You:** /Users/john/Downloads/barclays_june2026.csv  
> **System:** Imported. 47 transactions from Barclays Current Account. 3 duplicates skipped. 44 new lines ready for categorization.

**OFX Import:**
> **You:** Import my HSBC OFX statement for account HSBC current  
> **System:** Same flow — provide file path. OFX v1.02, v2.1, and v2.2 supported.

**Supported bank formats (CSV auto-detection):**

| Bank | Auto-Detected? | Notes |
|---|---|---|
| Barclays | ✅ | Date, Description, Amount columns |
| HSBC | ✅ | Date, Description, Debit, Credit columns |
| Lloyds | ✅ | Standard CSV export |
| NatWest | ✅ | Standard CSV export |
| Monzo | ✅ | Monzo export format |
| Starling | ✅ | Starling export format |
| Revolut | ✅ | Revolut export format |
| Generic | ⚠️ | Manual column mapping required |

#### Reconciliation

Reconciliation matches your imported bank statement lines against your ledger entries.

**Starting a Reconciliation:**
> **You:** Start reconciliation for Barclays current account  
> **System:** Reconciliation session opened for Barclays Current Account. 44 imported lines, 156 ledger entries in period. Let's begin matching.

**Matching Transactions:**
> **You:** Match this £240.00 bank line to invoice payment INV-2026-0012  
> **System:** Matched. £240.00 bank transaction matched to INV-2026-0012 payment in ledger.

**One-to-Many Matching:**
> **You:** Match this £5,000 bank deposit to invoices INV-0010 (£3,000) and INV-0011 (£2,000)  
> **System:** Matched. £5,000.00 split across 2 ledger transactions. £3,000.00 to INV-0010, £2,000.00 to INV-0011.

**Create & Match (New Entry):**
> **You:** This £45 bank fee isn't in my ledger — create it as Bank Charges and match it  
> **System:** Created. Bank Charges £45.00 recorded and matched to bank line.

**Reconciliation Status:**
> **You:** How's my reconciliation going?  
> **System:** Reconciliation #42 — Barclays Current. Matched: 41/44 (93%). Unmatched: 3. Status: Open.

**Reconciliation Report:**
> **You:** Generate reconciliation report for June  
> **System:** *[Displays: Opening Balance → Matched Items → Unmatched Items → Closing Balance — with verified balance equality]*

### 3g. VAT & MTD

Agentic Accounting supports three UK VAT schemes:

| Scheme | How VAT Is Calculated | Best For |
|---|---|---|
| **Standard Accrual** | VAT recognised on invoice date | Most businesses |
| **Cash Accounting** | VAT recognised on payment date | Businesses with late-paying customers |
| **Flat Rate** | Simplified % of gross turnover | Small businesses with low expenses |

#### VAT Return Preview

> **You:** Show my VAT return for Q2 2026  
> **System:** *[Displays 9-box UK VAT return]*

**The 9-box UK VAT return:**

| Box | Description | What It Contains |
|---|---|---|
| Box 1 | VAT due on sales | Output VAT from invoices and income |
| Box 2 | VAT due on EU acquisitions | 0 for most UK businesses |
| Box 3 | Total output VAT | Box 1 + Box 2 |
| Box 4 | VAT reclaimed on purchases | Input VAT from expenses |
| Box 5 | Net VAT | Box 3 − Box 4 |
| Box 6 | Total sales (excl. VAT) | Net value of all sales |
| Box 7 | Total purchases (excl. VAT) | Net value of all purchases |
| Box 8 | EU sales | 0 for most UK businesses |
| Box 9 | EU acquisitions | 0 for most UK businesses |

#### Viewing VAT Transactions

> **You:** What transactions are in my Q2 VAT return?  
> **System:** *[Lists every transaction contributing to each box, with traceable digital links]*

#### VAT Adjustments

> **You:** Add a £50 adjustment for fuel scale charge on my Q2 VAT return  
> **System:** Recorded. £50.00 fuel scale charge adjustment added to Box 1. Reason logged in audit trail.

> **You:** Adjust Box 4 by -£25 — corrected input VAT on phone bill  
> **System:** Recorded. £25.00 reduction applied to Box 4. Reason logged.

#### VAT Audit Trail

> **You:** Show VAT audit trail for Q2 2026  
> **System:** *[Displays every transaction, adjustment, and source document linked to the return — MTD digital-link compliant]*

The audit trail is **Making Tax Digital (MTD) compliant**: every figure in every box is traceable back to the source transaction. No cut-and-paste. HMRC can verify the full chain.

#### MTD Submission to HMRC (Phase 2)

When MTD submission is enabled:

> **You:** Submit my Q2 VAT return to HMRC  
> **System:** Validating digital links… All 9 boxes traceable. Submitting to HMRC… Accepted. HMRC Correlation ID: abc123-def456. Submission receipt stored.

You can also:
- Fetch VAT obligations from HMRC: `"Show my HMRC VAT obligations"`
- Check submission status: `"Check status of HMRC submission abc123"`
- Test HMRC connectivity: `"Test HMRC connection"`

### 3h. Reports

#### Profit & Loss (P&L)

> **You:** Profit & Loss for last quarter  
> **System:** *[Displays: Revenue − Cost of Sales = Gross Profit − Expenses = Net Profit]*

> **You:** P&L for June 2026 compared to June 2025  
> **System:** *[Side-by-side comparison with variance]*

#### Balance Sheet

> **You:** Show balance sheet as of 31 March 2026  
> **System:** *[Displays: Current Assets + Fixed Assets = Current Liabilities + Long-Term Liabilities + Equity]*

#### Trial Balance

> **You:** Trial balance for June  
> **System:** *[Displays every account with debit/credit totals — sum must equal zero]*

#### Aged Receivables

> **You:** Aged receivables report  
> **System:** *[Displays outstanding invoices grouped by age: 0–30 days, 31–60, 61–90, 90+]*

#### Aged Payables

> **You:** Aged payables report  
> **System:** *[Displays outstanding bills grouped by age: 0–30 days, 31–60, 61–90, 90+]*

#### Output Formats

All reports support multiple formats:
- **JSON**: Machine-readable, good for scripts
- **CSV**: Spreadsheet import
- **HTML**: View in browser
- **PDF**: Professional presentation (via WeasyPrint)

> **You:** P&L for last month as PDF

#### Scheduling Reports

> **You:** Send me a P&L report every month  
> **System:** Scheduled. Profit & Loss report will run on the 1st of each month.

Frequencies: `daily`, `weekly`, `monthly`, `quarterly`.

---

## 4. Pathway B: AI Agent-Directed (MCP Tools)

Pathway B lets an MCP-compatible AI agent invoke accounting tools directly. The agent reads `SKILL.md` from the repository root, discovers all 40+ tools, and calls them via the MCP gateway on port 3112.

### 4a. Setting Up Your Agent

The repository root contains a `SKILL.md` file that agents read for auto-discovery. Copy it to the appropriate location for your agent.

#### Claude Code (Claude Desktop)

```bash
mkdir -p ~/.claude-code/skills/accounting
cp SKILL.md ~/.claude-code/skills/accounting/
```

Then add to Claude's MCP server configuration:

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

#### OpenClaw

```bash
mkdir -p ~/.config/openclaw/skills/accounting
cp SKILL.md ~/.config/openclaw/skills/accounting/
```

OpenClaw auto-discovers the MCP server from the SKILL.md YAML frontmatter.

#### Kolega Code

```bash
mkdir -p ~/.kolega/skills/accounting
cp SKILL.md ~/.kolega/skills/accounting/
```

Kolega Code reads the SKILL.md frontmatter and connects automatically.

#### Verify Connection

```bash
# List all available tools (your agent will see these)
curl -X POST http://localhost:3112/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

### 4b. MCP Tool Reference

All tools use **SSE transport** on `http://localhost:3112/sse`. Amounts are in **pence** (integers). IDs are **UUIDs**.

---

#### Chart of Accounts (4 tools)

| Tool ID | Description | Required Parameters | Optional |
|---|---|---|---|
| `coa.list` | List all accounts in the chart of accounts | _(none)_ | `include_inactive` (bool) |
| `coa.add_account` | Create a new account | `code`, `name`, `category`, `type` | `vat_rate`, `parent_id` |
| `coa.edit_account` | Update an existing account | `account_id` | `code`, `name`, `category`, `type`, `is_active` |
| `coa.set_vat_rate` | Set/update the default VAT rate | `account_id`, `vat_rate` | — |

**Categories:** `Asset`, `Liability`, `Equity`, `Revenue`, `Expense`  
**VAT Rates:** `20%`, `5%`, `0%`, `exempt`

```
# Example: coa.add_account
{
  "name": "coa.add_account",
  "arguments": {
    "code": "5210",
    "name": "Marketing Expenses",
    "category": "Expense",
    "type": "Expense",
    "vat_rate": "20%"
  }
}
```

---

#### General Ledger (7 tools)

| Tool ID | Description | Required | Optional |
|---|---|---|---|
| `gl.record_expense` | Record a business expense with VAT | `description`, `amount` | `vat_rate`, `contact`, `date` |
| `gl.record_income` | Record revenue/income received | `description`, `amount` | `vat_rate`, `contact`, `date` |
| `gl.record_transfer` | Transfer between bank accounts | `from_account`, `to_account`, `amount` | `date`, `description` |
| `gl.journal_entry` | Create a manual journal entry | `date`, `postings` | `reference`, `description` |
| `gl.list_transactions` | Browse/search recent transactions | _(none)_ | `start_date`, `end_date`, `account_id`, `contact_id`, `limit` |
| `gl.transaction_detail` | Get full detail of a transaction | `transaction_id` | — |
| `gl.undo_transaction` | Reverse a previously recorded transaction | `transaction_id` | — |

**Postings format (journal_entry):**

```json
{
  "date": "2026-06-15",
  "reference": "JE-2026-001",
  "description": "Correct depreciation for Q2",
  "postings": [
    {"account_id": "5500-uuid", "amount": 50000, "side": "debit"},
    {"account_id": "1600-uuid", "amount": 50000, "side": "credit"}
  ]
}
```

> Amounts in pence. £500.00 = `50000`.

---

#### Contacts (5 tools)

| Tool ID | Description | Required | Optional |
|---|---|---|---|
| `contact.create` | Add a new contact | `name`, `type` | `email`, `phone`, `address_line1`, `city`, `postcode`, `notes` |
| `contact.edit` | Update an existing contact | `contact_id` | `name`, `type`, `email`, `phone` |
| `contact.list` | List all contacts | _(none)_ | `type`, `search` |
| `contact.detail` | Get full details of a contact | `contact_id` | — |
| `contact.archive` | Archive (soft-delete) a contact | `contact_id` | — |

**Contact Types:** `customer`, `supplier`, `both`, `other`

---

#### Bank (6 tools)

| Tool ID | Description | Required | Optional |
|---|---|---|---|
| `bank.import_csv` | Import a CSV bank statement | `bank_account_id` | `file_path`, `format` |
| `bank.import_ofx` | Import an OFX/QFX bank statement | `bank_account_id` | `file_path` |
| `bank.list_accounts` | List connected bank accounts | _(none)_ | — |
| `bank.add_account` | Add a new bank account | `name` | `account_number`, `sort_code`, `currency`, `opening_balance` |
| `bank.transactions` | List imported bank transactions | `bank_account_id` | `start_date`, `end_date`, `status` |
| `bank.categorize` | Assign bank transaction to account | `bank_transaction_id`, `account_id` | `contact_id`, `vat_rate` |

**CSV Formats:** `auto`, `monzo`, `revolut`, `starling`, `hsbc`, `generic`  
**Transaction Statuses:** `unmatched`, `matched`, `all`

---

#### Reconciliation (5 tools)

| Tool ID | Description | Required | Optional |
|---|---|---|---|
| `recon.start` | Start a new reconciliation session | `bank_account_id` | `statement_date`, `statement_balance` |
| `recon.match` | Match bank line to GL transaction | `reconciliation_id`, `bank_transaction_id`, `transaction_id` | — |
| `recon.create_and_match` | Create GL entry AND match to bank line | `reconciliation_id`, `bank_transaction_id` | `description`, `amount`, `vat_rate`, `account_id`, `contact_id` |
| `recon.status` | Check reconciliation session progress | `reconciliation_id` | — |
| `recon.report` | Generate reconciliation summary report | `reconciliation_id` | — |

---

#### Invoices (6 tools)

| Tool ID | Description | Required | Optional |
|---|---|---|---|
| `invoice.create` | Create a new sales invoice | `contact_id`, `lines` | `issue_date`, `due_date`, `notes` |
| `invoice.send` | Send a draft invoice to customer | `invoice_id` | — |
| `invoice.list` | List invoices | _(none)_ | `status`, `contact_id` |
| `invoice.mark_paid` | Mark an invoice as paid | `invoice_id` | — |
| `invoice.credit_note` | Issue a credit note | `invoice_id` | `reason`, `amount` |
| `invoice.overdue` | List all overdue invoices | _(none)_ | — |

**Invoice Statuses:** `draft`, `sent`, `viewed`, `paid`, `overdue`, `all`

**Line items format:**

```json
{
  "contact_id": "abc-ltd-uuid",
  "issue_date": "2026-06-15",
  "due_date": "2026-07-15",
  "lines": [
    {"description": "Website design", "quantity": 1, "unit_price": 250000, "vat_rate": "20%"},
    {"description": "Hosting setup", "quantity": 1, "unit_price": 25000, "vat_rate": "20%"}
  ],
  "notes": "Payment due within 30 days"
}
```

> £2,500.00 = `250000` pence.

---

#### VAT (4 tools)

| Tool ID | Description | Required | Optional |
|---|---|---|---|
| `vat.preview_return` | Preview 9-box VAT return | `start_date`, `end_date` | — |
| `vat.transaction_detail` | See transactions in a VAT return | `vat_period_id` | — |
| `vat.adjustment` | Add manual adjustment to a box | `vat_period_id`, `amount`, `reason` | — |
| `vat.audit_trail` | View MTD digital-link audit trail | `vat_period_id` | `limit` |

---

#### Reports (3 tools)

| Tool ID | Description | Required | Optional |
|---|---|---|---|
| `report.run` | Generate a financial report | `report_type` | `start_date`, `end_date`, `as_at_date` |
| `report.list` | List available report types | _(none)_ | — |
| `report.schedule` | Schedule a recurring report | `report_type`, `frequency` | `email_to` |

**Report Types:** `profit_and_loss`, `balance_sheet`, `trial_balance`, `aged_receivables`, `aged_payables`  
**Frequencies:** `daily`, `weekly`, `monthly`, `quarterly`

---

### 4c. Agent Conversation Examples

Here is what an agent does under the hood when you give it natural language commands. Compare with Pathway A — same outcomes, different mechanism.

#### Recording an Expense (Agent)

> **You (to agent):** Paid £50 for office supplies at Tesco

Agent tool calls:
```
tool: gl.record_expense
args: {"description": "Office supplies at Tesco", "amount": 5000, "vat_rate": "20%"}

tool: gl.transaction_detail
args: {"transaction_id": "new-txn-uuid"}
```

Agent response: "Recorded. £50.00 office supplies + £10.00 VAT = £60.00 from current account. Reference JE-2026-0042."

#### Creating an Invoice (Agent)

> **You (to agent):** Create invoice for ABC Ltd for 10 hours at £80/hr plus VAT

Agent tool calls:
```
tool: contact.list
args: {"type": "customer", "search": "ABC"}
→ returns contact_id: "abc-uuid"

tool: invoice.create
args: {
  "contact_id": "abc-uuid",
  "lines": [
    {"description": "Consulting services", "quantity": 10, "unit_price": 8000, "vat_rate": "20%"}
  ]
}
→ returns invoice_id, reference INV-2026-0014
```

Agent response: "Created INV-2026-0014 for ABC Ltd — £800.00 + £160.00 VAT = £960.00. Due in 30 days."

#### Bank Reconciliation (Agent)

> **You (to agent):** Reconcile my Barclays current account for June

Agent tool calls:
```
tool: bank.list_accounts
→ finds Barclays Current account_id

tool: bank.transactions
args: {"bank_account_id": "barclays-uuid", "start_date": "2026-06-01", "end_date": "2026-06-30", "status": "unmatched"}
→ returns 44 unmatched bank lines

tool: recon.start
args: {"bank_account_id": "barclays-uuid"}

# For each bank line, the agent tries to find matching GL transactions:
tool: recon.match (for clear 1:1 matches)
tool: recon.create_and_match (for new entries like bank fees)

tool: recon.status
→ "Matched: 41/44 (93%). Unmatched: 3."

tool: recon.report
```

Agent response: "Reconciliation complete. 41 of 44 bank lines matched. 3 unmatched items flagged for review. Report generated."

#### Complex Multi-Step (Agent)

> **You (to agent):** Get my Q2 VAT return, check for any overdue invoices, and send me a P&L for the quarter.

Agent chains multiple tools: `vat.preview_return` → `invoice.overdue` → `report.run` (P&L). All three results in a single response.

---

## 5. Multi-User Setup

Agentic Accounting supports multi-user access with five role levels. Only Owners and Admins can manage users.

### Creating Users

**Via Chat UI (Pathway A):**
> **You:** Create a user for my bookkeeper — name Sarah Jones, email sarah@example.com, role bookkeeper  
> **System:** Created. Sarah Jones (sarah@example.com) added as Bookkeeper. They'll receive setup instructions.

**Via API/Agent (Pathway B):**
```
POST /api/v1/auth/register
{
  "email": "sarah@example.com",
  "password": "secure-password-123",
  "display_name": "Sarah Jones",
  "role": "bookkeeper"
}
```

### Role Descriptions

| Role | Privileges | Can Manage Users? | Best For |
|---|---|---|---|
| **Owner** | Full system access, all modules, all actions | ✅ Yes — create, edit, delete any user | Business owner, sole practitioner |
| **Admin** | Full operational access, all modules | ✅ Partial — create & edit users; cannot delete | Practice manager, senior accountant |
| **Accountant** | Transactions, reports, VAT, reconciliation, contacts, invoices | ❌ No | Qualified accountant managing books |
| **Bookkeeper** | Transactions, reconciliation, bank imports, contacts | ❌ No | Day-to-day bookkeeping staff |
| **Viewer** | Read-only across all modules | ❌ No | Auditor, investor, external advisor |

### Permission Matrix

| Module | Owner | Admin | Accountant | Bookkeeper | Viewer |
|---|---|---|---|---|---|
| **Chart of Accounts** | CRUD | CRUD | CRUD | Read | Read |
| **General Ledger — Read** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **General Ledger — Write** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **General Ledger — Undo** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Contacts** | CRUD | CRUD | CRUD | CRUD | Read |
| **Bank Import** | ✅ | ✅ | ✅ | ✅ | Read |
| **Reconciliation** | ✅ | ✅ | ✅ | ✅ | Read |
| **Invoices — Create/Send** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Invoices — Mark Paid** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **VAT Returns** | ✅ | ✅ | ✅ | ❌ | Read |
| **MTD Submission** | ✅ | ✅ | ✅ | ❌ | Read |
| **Reports** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **User Management** | Full | Partial | ❌ | ❌ | ❌ |
| **Approval Workflows** | Full | Full | Approve | Request | View |

> **Tip for Practitioners:** Create an Owner account for yourself and Admin accounts for senior staff. Use Accountant roles for qualified staff and Bookkeeper roles for data-entry staff. Give your client a Viewer role so they can see reports without accidentally changing anything.

### Managing Users

- **Edit a user:** `"Change Sarah's role to Accountant"`
- **Deactivate a user:** `"Deactivate sarah@example.com"` (Owner only)
- **List all users:** `"Who has access to the system?"`

Deactivated users cannot log in but their historical actions remain in the audit trail.

---

## 6. Approval Workflows

For businesses that need internal controls, approval workflows add a review step before sensitive actions.

### How Approvals Work

1. A user requests an action that exceeds a threshold (e.g., expense > £500)
2. The system creates an approval request with automatic level assignments
3. Designated approvers review and either approve or reject
4. If approved at all levels, the action executes
5. If rejected at any level, the action is cancelled

### Threshold Levels

| Transaction Amount | Approval Levels |
|---|---|
| **< £500** | Auto-approved (no human review) |
| **£500 – £2,000** | 1 level: Admin or Accountant |
| **£2,000 – £10,000** | 2 levels: Accountant → Admin |
| **> £10,000** | 3 levels: Accountant → Admin → Owner |

### Approving or Rejecting

**Via Chat UI:**

> **System:** ⚠️ Approval needed: £3,200 invoice payment to ABC Ltd. Your approval is required.  
> **You:** Approve — looks correct  
> **System:** Approved. Payment processed. Advancing to next level: Admin review.

> **You:** Reject — wrong amount, should be £2,300  
> **System:** Rejected. Request cancelled. Reason: "wrong amount." Requester notified.

**Via API/Agent:**

```
POST /api/v1/approvals/{approval_id}/approve
{"comment": "Reviewed — correct amount"}

POST /api/v1/approvals/{approval_id}/reject
{"comment": "Duplicate request — already paid"}
```

### Viewing Pending Approvals

> **You:** What's waiting for my approval?  
> **System:** *[Lists all pending approval requests where you are the current approver]*

> **You:** Show all approval requests  
> **System:** *[Admin/Owner only — lists all requests with statuses]*

### Approval Statuses

- **pending** — awaiting approvals at current level
- **approved** — all levels approved, action executed
- **rejected** — rejected at some level, action cancelled

---

## 7. Recurring Transactions

Set up templates for transactions or invoices that repeat on a schedule. The system automatically processes them on their due dates.

### Setting Up a Recurring Template

**Via Chat UI:**

> **You:** Set up a recurring expense: £29.99 monthly for Adobe Creative Cloud, 20% VAT, starting 1st of next month  
> **System:** Created recurring template. £29.99/month for Adobe CC. First run: 1 July 2026. Type: transaction. Frequency: monthly.

> **You:** Create a recurring invoice for ABC Ltd: £500 retainer, monthly, no VAT, starts today for 12 months  
> **System:** Created recurring template. £500.00/month retainer invoice to ABC Ltd. First run: today. End after 12 occurrences.

**Via API:**

```
POST /api/v1/recurring/templates
{
  "template_type": "transaction",
  "frequency": "monthly",
  "start_date": "2026-07-01",
  "next_run_date": "2026-07-01",
  "transaction_detail": {
    "description": "Adobe Creative Cloud",
    "amount": 2999,
    "vat_rate": "20%",
    "account_id": "subscriptions-uuid"
  }
}
```

### Frequencies & End Conditions

**Frequencies:**
- `daily` — every day
- `weekly` — every 7 days
- `biweekly` — every 14 days
- `monthly` — same day each month
- `quarterly` — every 3 months
- `annually` — once per year

**End Conditions (optional):**
- **End date:** "until 31 December 2026"
- **Occurrences:** "12 times"
- **No end:** runs indefinitely until paused or deleted

### Processing Due Templates

Templates are processed when `next_run_date <= today`.

**Manual Trigger:**
> **You:** Process all due recurring items  
> **System:** Processed 3 due templates. 2 transactions and 1 invoice created.

**Automated:** You can set up a cron job or scheduled task to call `POST /api/v1/recurring/process` daily.

### Managing Templates

- **List templates:** `"Show my recurring transactions"`
- **View a template:** `"Show recurring template details for Adobe CC"`
- **Edit a template:** `"Change Adobe CC recurring amount to £34.99"`
- **Skip next occurrence:** `"Skip next Adobe CC payment"`
- **Pause:** `"Pause the Adobe CC recurring"`
- **Resume:** `"Resume Adobe CC recurring — it's active again"`
- **Delete:** `"Delete the ABC Ltd retainer invoice template"`

When you pause, the template stays saved but won't process. Resume sets `next_run_date` to today if it has fallen behind.

---

## 8. Bank Rules Engine

The Bank Rules Engine auto-categorises imported bank transactions based on patterns you define. Think of it as "if the transaction description contains X, categorise it as Y."

### How Auto-Categorisation Works

1. You import a bank statement (CSV or OFX)
2. Each imported line starts as **Uncategorised**
3. The rules engine checks each line against active rules (highest priority first)
4. When a rule matches (by description, amount, or reference), the transaction is auto-categorised
5. Remaining lines need manual categorisation

### Loading Default Rules

The system ships with 50+ pre-built rules covering common UK business expenses:

> **You:** Load default bank rules  
> **System:** Loaded 54 default rules. Categories include: Tesco → Office Supplies, Amazon → Sundry Expenses, Trainline → Travel, Adobe → Software Subscriptions, etc.

### Viewing Rules

> **You:** Show my bank rules  
> **System:** *[Displays all rules ordered by priority, showing match pattern, target account, and whether active]*

### Creating Custom Rules

> **You:** Create a rule: if description contains "Dropbox", categorise as Software Subscriptions at 20% VAT  
> **System:** Created. Rule #55: description contains "Dropbox" → Software Subscriptions (20% VAT). Priority: last.

> **You:** Create a rule: if amount is exactly £12.99 and description contains "Spotify", categorise as Entertainment  
> **System:** Created. Rule #56: £12.99 + "Spotify" → Entertainment.

**Available match conditions:**
- `description_contains` — partial text match
- `description_exact` — exact text match
- `amount_exact` — exact amount (in pence)
- `amount_range` — amount between min and max
- `reference_contains` — reference field match
- Any combination of the above (AND logic)

### Applying Rules

**Apply to all pending:**
> **You:** Apply rules to all uncategorised Barclays transactions  
> **System:** Applied rules. 23 of 44 transactions categorised automatically. 21 still need manual review.

**Apply to a single transaction:**
> **You:** Apply rules to this specific Barclays transaction  
> **System:** Rule matched: "Tesco Stores 2378" → Office Supplies. Categorised.

### Rule Priority

Rules are evaluated top-to-bottom by priority. The first matching rule wins. You can reorder rules by editing their priority field.

> **Tip:** Put specific rules (e.g., "Spotify £12.99") at higher priority than broad rules (e.g., "anything containing 'Ltd'").

---

## 9. Troubleshooting

### Common Issues & Solutions

#### Docker Compose Won't Start

```bash
# Check Docker is running
docker info

# Check for port conflicts
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :8000  # API
lsof -i :3112  # MCP Gateway
lsof -i :3000  # Chat UI

# If ports are in use, edit .env to remap:
#   DB_PORT=5433
#   API_PORT=8001
#   MCP_PORT=3113
#   UI_PORT=3001
```

#### Containers Start but Show "unhealthy"

```bash
# View logs for a specific service
docker compose logs postgres
docker compose logs accounting-api

# Wait longer and re-check — some services take 30-60 seconds
docker compose ps

# Restart a specific service
docker compose restart accounting-api
```

#### Chat UI Shows "Connecting..." Forever

```bash
# Verify the API is running
curl http://localhost:8000/health

# Verify the WebSocket endpoint
curl http://localhost:8000/ws/chat/test-session

# Check Chat UI logs
docker compose logs chat-ui
```

#### MCP Gateway Returns 404

```bash
# Verify gateway health
curl http://localhost:3112/health

# Check MCP tools list
curl -X POST http://localhost:3112/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# If empty tools list, check skills registry is mounted
docker compose exec accounting-gateway ls -la /app/skills/
```

#### MCP Agent Can't Connect (Pathway B)

```bash
# Verify SSE endpoint is reachable
curl -N http://localhost:3112/sse

# Check agent config points to correct URL
# The URL must be http://localhost:3112/sse (not just http://localhost:3112)

# For Docker-based agents: use host.docker.internal instead of localhost
#   url: http://host.docker.internal:3112/sse
```

#### File Imports Fail (CSV/OFX)

```bash
# File must be accessible inside the container
# Mount your downloads folder:
# Add to docker-compose.yml volumes:
#   - ~/Downloads:/app/imports:ro

# Then use path: /app/imports/statement.csv
```

#### Database Migrations Missing

```bash
# Run migrations manually
docker compose exec accounting-api alembic upgrade head

# Check migration status
docker compose exec accounting-api alembic current
```

#### "Cannot Connect to PostgreSQL"

```bash
# Reset database (DESTRUCTIVE — loses all data)
docker compose down -v postgres
docker compose up -d postgres
# Wait 10 seconds, then restart API
docker compose restart accounting-api
```

### Docker Health Checks

All services have built-in health checks:

| Service | Health Check |
|---|---|
| PostgreSQL | `pg_isready` every 5s |
| Redis | `redis-cli ping` every 5s |
| MinIO | HTTP health endpoint every 10s |
| Formance Ledger | `/_info` endpoint every 10s |
| MCP Gateway | `/health` endpoint (passive) |

```bash
# Check all service health statuses
docker compose ps

# Continuous health monitoring
watch -n 5 'docker compose ps'
```

---

## 10. Data Privacy & Backup

### Data Storage — Fully Local

- **All financial data** is stored in PostgreSQL, running locally in Docker
- **No data is transmitted** to external services (unless you use HMRC MTD submission)
- **Documents and statements** are stored in MinIO (local S3-compatible object storage)
- **Session data and caches** are stored in Redis
- **No cloud dependency** — the system operates fully offline after initial Docker image pull

### What Data Is Stored Where

| Data | Location | Format |
|---|---|---|
| Chart of Accounts | PostgreSQL (`accounts` table) | SQL |
| General Ledger | PostgreSQL (`transactions`, `postings` tables) | SQL |
| Contacts | PostgreSQL (`contacts` table) | SQL |
| Bank Accounts & Transactions | PostgreSQL (`bank_accounts`, `bank_transactions` tables) | SQL |
| Invoices & Credit Notes | PostgreSQL (`invoices`, `invoice_lines`, `credit_notes` tables) | SQL |
| VAT Returns & Audit Trail | PostgreSQL (`vat_periods`, `vat_returns` tables) | SQL |
| Users & Permissions | PostgreSQL (`users` table) | SQL |
| Uploaded CSVs/OFX/PDFs | MinIO (`/data` volume) | Binary |
| Conversation History | Redis (session store) | Key-Value |
| Generated PDFs (invoices) | MinIO | Binary |

### Backup Procedure

```bash
# 1. Backup PostgreSQL database
docker compose exec postgres pg_dump -U accounting accounting > backup_$(date +%Y%m%d).sql

# 2. Backup MinIO documents (optional — large)
docker compose exec minio mc mirror local/data /backup/minio/

# 3. Backup the entire docker-compose and your .env
cp docker-compose.yml backup_$(date +%Y%m%d)/
cp .env backup_$(date +%Y%m%d)/

# Recommended: Schedule this daily via cron
# 0 2 * * * cd /path/to/agentic-accounting && ./backup.sh
```

### Restore Procedure

```bash
# 1. Start fresh (if needed)
docker compose down -v
docker compose up -d postgres

# 2. Restore database
docker compose exec -T postgres psql -U accounting accounting < backup_20260627.sql

# 3. Restart all services
docker compose up -d

# 4. Verify
curl http://localhost:3112/health
```

### UK VAT Data Retention

HMRC requires VAT records to be kept for **6 years**. The system stores all VAT data with full MTD digital-link audit trails. Periodically back up your database to comply with this requirement.

---

## 11. Uninstall

To completely remove Agentic Accounting from your system:

```bash
# Step 1: Stop all containers
cd agentic-accounting
docker compose down

# Step 2: Remove all data volumes (DESTRUCTIVE — all data lost)
docker compose down -v

# Step 3: Remove Docker images (optional — frees disk space)
docker rmi agentic-accounting-mcp-gateway agentic-accounting-api
docker rmi ghcr.io/formancehq/ledger:v2
docker rmi postgres:16-alpine redis:7-alpine minio/minio:latest

# Step 4: Delete the repository
cd .. && rm -rf agentic-accounting
```

> **⚠️ Warning:** `docker compose down -v` permanently deletes all PostgreSQL data, MinIO files, and Redis data. Ensure you have backed up anything you need before running this command.

---

## Appendix: Quick Reference

### Port Map

| Port | Service | Pathway |
|---|---|---|
| 3000 | Chat UI | Pathway A |
| 3112 | MCP Gateway | Both A & B |
| 5432 | PostgreSQL | Internal |
| 6379 | Redis | Internal |
| 8000 | Accounting API | Internal (proxy) |
| 9000 | MinIO S3 | Internal |
| 9001 | MinIO Console | Optional admin |

### Useful Commands

```bash
# Health check
curl http://localhost:3112/health

# List all MCP tools
curl -X POST http://localhost:3112/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# API documentation (Swagger)
open http://localhost:8000/docs

# Gateway documentation
open http://localhost:3112/docs

# View service logs
docker compose logs -f accounting-api
docker compose logs -f accounting-gateway

# Restart everything
docker compose restart

# Reset everything (WARNING: destroys all data)
docker compose down -v && docker compose up -d
```

### VAT Rates Quick Reference

| Rate | When to Use |
|---|---|
| **20%** | Standard rate — most goods and services |
| **5%** | Reduced rate — domestic fuel, mobility aids, children's car seats |
| **0%** | Zero-rated — most food, children's clothing, books, new houses |
| **Exempt** | Exempt — insurance, finance, education, health services |

### Journal Entry Numbering

- Format: `JE-YYYY-NNNN` (e.g., `JE-2026-0042`)
- Sequential per year; resets each January
- Invoice references: `INV-YYYY-NNNN`
- Credit notes: `CN-YYYY-NNNN`

### Agent Compatibility

| Agent | Compatible | Notes |
|---|---|---|
| OpenClaw | ✅ | Native MCP SSE client |
| Claude Code | ✅ | Add to `mcpServers` config |
| Kolega Code | ✅ | Auto-discovers SKILL.md |
| Continue.dev | ✅ | Add to `config.json` |
| Cursor | ✅ | MCP server settings |
| Zed | ⚠️ | Partial — stdio not yet supported |

---

*Agentic Accounting v0.1.0 (MVP)*  
*For issues, feature requests, or contributions, visit the repository.*  
*License: See LICENSE file in repository root.*
