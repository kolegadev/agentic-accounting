## 8. MVP Requirements Specification

This chapter defines the complete Minimum Viable Product (MVP) scope for the headless, LLM-native accounting system. The MVP delivers a functional single-entity accounting system for a UK VAT-registered small business, operated entirely through natural language conversation with an LLM. Eight weeks of development, 48 engineering days, and a team of 2–3 engineers produce a system that completes the full bookkeeping cycle — from transaction recording through VAT return preview — without the user writing code or opening a spreadsheet.

### 8.1 MVP Scope and Success Criteria

#### 8.1.1 Target Profile

The MVP serves a single business entity: a UK-based freelancer, sole trader, or limited company with 0–10 employees, VAT-registered, operating in a single currency (GBP). This profile was selected because it represents the largest addressable market of UK small businesses (over 5.5 million SMEs as of 2024) while constraining complexity to a tractable eight-week build [^264^]. The constraint to a single entity, single currency, and single VAT jurisdiction eliminates the engineering surface area of multi-currency revaluation, intercompany elimination, and multi-tax jurisdiction rule engines — each of which is a significant module in its own right reserved for later phases.

The user interacts with the system exclusively via natural language chat. There is no traditional graphical user interface (GUI), no spreadsheet import wizard, and no report builder canvas. Every function — recording a transaction, creating an invoice, importing a bank statement, running a report — is accessed through conversational text. This is the defining architectural constraint of the MVP and the differentiator from incumbent platforms.

#### 8.1.2 Success Criteria

The MVP is deemed successful when a user can complete the following end-to-end bookkeeping cycle entirely via chat, with every step producing validated accounting data:

1. **Record transactions** via natural language (e.g., "Paid £120 to Acme Consulting for marketing services plus VAT"), with the system parsing the utterance into a balanced double-entry transaction.
2. **Create and send an invoice** to a customer, with line items, VAT calculation, PDF generation, and email delivery.
3. **Import a bank statement** (CSV or OFX format) with automatic column mapping and duplicate detection.
4. **Reconcile** imported bank transactions against ledger entries through conversational matching.
5. **Run a VAT return** for the quarter, with automatic nine-box calculation and MTD-compliant preview.
6. **Generate a Profit & Loss statement and Balance Sheet**, with period comparison, delivered in the user's preferred output format (JSON, HTML, PDF, or CSV).

A non-negotiable quality gate requires that **all data passes double-entry validation** — total debits must equal total credits on every transaction, enforced at the database constraint level [^45^]. Additionally, the HMRC MTD (Making Tax Digital) VAT nine-box return must be calculable and previewable, though actual digital submission to HMRC is deferred to Phase 2.

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

The 55-day estimate inflates to approximately 48 effective days at 75% velocity (accounting for context switching, code review, and integration testing), confirming the feasibility of the 8-week schedule [^45^][^213^]. Modules 2 (Core General Ledger) and 9 (LLM Chat Interface) together consume 20 of the 48 days (42%), reflecting their centrality to the system's value proposition. The schedule assumes a Docker Compose development environment with PostgreSQL 16+, Formance Ledger, Redis, and MinIO running locally on each engineer's workstation.

### 8.2 MVP Module Specifications

#### 8.2.1 Module 1: Chart of Accounts (3 days)

The Chart of Accounts (COA) is the hierarchical account structure that forms the backbone of the general ledger. The MVP provides eight pre-loaded COA templates, each tailored to a specific UK business structure and VAT status [^264^][^405^]:

- UK Sole Trader — No VAT (40 accounts)
- UK Sole Trader — VAT Registered (55 accounts)
- UK Limited Company — No VAT (50 accounts)
- UK Limited Company — VAT Registered (65 accounts)
- UK Partnership — No VAT (45 accounts)
- UK Partnership — VAT Registered (60 accounts)
- Micro-Entity Simplified (30 accounts)
- Property/Landlord — VAT Registered (45 accounts)

All templates follow a standard five-category, four-digit numbering scheme: Assets (1000–1999), Liabilities (2000–2999), Equity (3000–3999), Revenue (4000–4999), and Expenses (5000–6999). Within each range, account codes are spaced at intervals of 10 (e.g., 1010, 1020, 1030) to allow future insertion without renumbering [^264^]. Each account is typed as one of nine categories: Bank, Current Asset, Fixed Asset, Current Liability, Long-term Liability, Equity, Revenue, Direct Cost, or Expense.

VAT rate assignment is stored as account metadata. Each account can be tagged with a default VAT rate (20% standard, 5% reduced, 0% zero-rated, or exempt). When a transaction is posted to that account, the system applies the rate automatically unless the user overrides it in the natural language instruction. Accounts support soft delete via an enabled/disabled flag — disabled accounts remain in historical transactions but cannot be selected for new entries.

Each COA account maps to a Formance ledger account address using the pattern `gl:{account_code}:{entity_id}`, ensuring namespace isolation per business entity [^213^].

The LLM SKILLs exposed for this module are: `coa.list` ("Show me my chart of accounts"), `coa.add_account` ("Add a new account called Marketing Expenses under code 5210"), `coa.edit_account` ("Rename account 6100 to Software Subscriptions"), and `coa.set_vat_rate` ("Set VAT rate on account 4000 to zero-rated").

#### 8.2.2 Module 2: Core General Ledger (10 days)

The Core General Ledger is the highest-complexity module in the MVP. It converts natural language utterances into structurally validated, double-entry transactions backed by a Formance-style programmable ledger [^45^][^213^].

**Natural language parsing** accepts inputs such as "Paid £120 to Acme Consulting for marketing services plus VAT" and decomposes them into structured transactions with identified accounts, amounts, and VAT splits (£100 net + £20 VAT at 20%). The parsing pipeline uses an LLM with structured output constraints (JSON Schema) to guarantee parseable output, followed by a deterministic validation layer that catches the 91.67% of errors that raw LLM generation produces without guidance [^412^].

Transactions are modelled in Numscript-style syntax with sum-to-zero enforcement at the storage level. Every transaction enforces total debits equal total credits via a database constraint that rejects any unbalanced entry [^45^]. The transaction data model consists of three core tables: `transaction` (id, date, description, reference, contact_id, total_amount, currency, status, metadata, created_at), `posting` (id, transaction_id, account_id, debit_amount, credit_amount, description), and `vat_line` (id, posting_id, vat_rate, vat_amount, net_amount, vat_type as input or output).

The module supports simple two-sided entries (one debit, one credit), multi-line splits (multiple debits and/or credits within a single transaction), and both VAT-inclusive and VAT-exclusive amount entry. Journal entry numbering follows an auto-sequential format `JE-YYYY-NNNN` (e.g., JE-2025-0042). Transaction status flows through three states: **Draft** (editable, not yet posted to the ledger), **Posted** (immutable ledger entry), and **Reversed** (compensating entry created via a reversing journal). A full audit trail records created_at, created_by, and ip_address for every transaction [^45^].

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

The bank statement import module enables manual ingestion of bank transactions from CSV and OFX files. CSV import supports flexible column mapping — the system attempts to auto-detect date, description, amount (or separate debit/credit columns), reference, and type columns, and prompts the user to confirm or correct the mapping when ambiguity exists. OFX file parsing supports versions 1.02, 2.1, and 2.2, covering the overwhelming majority of UK bank export formats [^276^][^284^].

Seven pre-built bank templates ship with the MVP, each with known CSV column layouts: Barclays, HSBC, Lloyds, NatWest, Monzo, Starling, and Revolut. These templates eliminate the column-mapping step for users of these institutions. Duplicate detection uses FITID (Financial Institution Transaction ID) for OFX files and a SHA-256 hash of date + amount + description for CSV files, ensuring the same transaction is never imported twice [^276^].

The bank account entity stores account name, sort code, account number, IBAN, currency, opening balance, and current balance. Multiple bank accounts are supported per entity. Imported transactions flow through a three-stage status: **Imported** (raw from file), **Categorized** (matched to a GL account or existing invoice/bill), and **Reconciled** (confirmed against a ledger entry).

Table 8-3 shows the supported file formats and their priority levels.

**Table 8-3: File Format Support**

| Format | Version(s) | Priority | Notes |
|---|---|---|---|
| CSV | Any (flexible column mapping) | P0 | Universal fallback for all banks |
| OFX | 1.02, 2.1, 2.2 | P0 | Standard format; includes FITID for deduplication [^276^] |
| QIF | Quicken Interchange | P1 | Post-MVP; lower adoption in UK |

The bank module SKILLs are: `bank.import_csv`, `bank.import_ofx`, `bank.list_accounts`, `bank.add_account`, `bank.transactions`, and `bank.categorize`.

#### 8.2.5 Module 5: Manual Bank Reconciliation (5 days)

Bank reconciliation matches imported bank transactions to ledger entries (invoices, bills, and manually recorded transactions). The MVP implements a conversational reconciliation workflow where the LLM presents unmatched items to the user and guides them through matching decisions [^220^][^338^].

The reconciliation workflow follows six steps: (1) import the bank statement, (2) review unmatched bank lines, (3) match to existing invoices, bills, or ledger entries, (4) create new ledger entries for unmatched items, (5) confirm the reconciliation balance agrees, and (6) generate a reconciliation report.

Matching supports three patterns. **One-to-one**: a single bank transaction matches a single ledger entry (e.g., a bank deposit matches one invoice payment). **One-to-many**: a single bank deposit matches multiple invoice payments (e.g., a customer pays three invoices in one lump sum). **Partial matching**: the bank amount differs from the ledger entry amount, with the system prompting the user to explain the difference (commonly bank fees deducted before deposit) [^338^].

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

The invoice status lifecycle comprises six states: **Draft** (editable), **Sent** (delivered to customer, core fields become immutable), **Viewed** (customer opened the email), **Paid** (payment recorded against the invoice), **Overdue** (past due date, auto-transitioned by time-based detection), and **Cancelled** (voided, requires a credit note if amounts were posted) [^268^][^267^].

Critical immutability rules apply: after an invoice is Sent, core fields — customer, line items, amounts, and VAT — become unmodifiable. Corrections require a credit note workflow (negative invoice referencing the original) followed by re-issuance. Payment recording is the only safe post-send operation [^264^].

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

The VAT module automatically tracks VAT on every transaction. Output VAT (liability to HMRC) is recorded on sales and purchase invoices; input VAT (recoverable from HMRC) is recorded on expense transactions and purchase bills. Each VAT line is traceable back to its originating transaction, creating a complete audit trail per VAT return box [^79^][^85^].

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

In the MVP, the system produces an MTD-compliant preview of the nine-box return but does not submit digitally to HMRC — that capability requires HMRC developer account registration and OAuth2 integration deferred to Phase 2 [^124^][^583^]. However, the MVP already enforces MTD digital link compliance: every figure in the VAT return flows automatically from source transaction through to the return preview via formula-driven digital links, with no manual re-keying or copy-paste at any step [^124^]. Digital records are preserved for the statutory six-year period from the date of creation.

The VAT SKILLs are: `vat.preview_return`, `vat.transaction_detail`, `vat.adjustment`, and `vat.audit_trail`.

#### 8.2.8 Module 8: Core Financial Reports (5 days)

The reporting module generates the four essential financial reports that every UK small business requires, plus two ageing reports for receivables and payables management. All reports are implemented as deterministic, cacheable SKILLs with defined JSON schemas, processed through a five-stage report engine pipeline: (1) Parameter Ingestion, (2) Query Execution, (3) Data Transformation, (4) Rule Application, and (5) Output Formatting.

Table 8-6 describes the five MVP reports.

**Table 8-6: Core Financial Reports (MVP)**

| Report | Skill ID | Description | Key Sections |
|---|---|---|---|
| Profit & Loss | `report.pl` | Revenue minus expenses over a period | Revenue, Direct Costs, Gross Profit, Operating Expenses, Net Profit [^43^] |
| Balance Sheet | `report.bs` | Assets, liabilities, and equity at a point in time | Current Assets, Fixed Assets, Current Liabilities, Long-term Liabilities, Equity [^41^] |
| Trial Balance | `report.tb` | All account balances verifying debits equal credits | Account, Debit, Credit, YTD Debit, YTD Credit [^137^][^142^] |
| Aged Receivables | `report.ar_aging` | Outstanding customer balances by time bucket | Current, 1–30, 31–60, 61–90, 91+ days [^81^] |
| Aged Payables | `report.ap_aging` | Outstanding supplier balances by time bucket | Current, 1–30, 31–60, 61–90, 91+ days [^81^] |

Report parameters include: period (start_date, end_date), comparison mode (prior period or prior year), accounting basis (accrual default, cash optional), output format (JSON for API consumers, HTML for readable rendering, PDF for document distribution, CSV for spreadsheet import), and number format (GBP with pence). The IFRS 18 five-category Profit & Loss structure is reserved for Phase 3, effective January 2027 [^301^].

The reporting SKILLs are: `report.run`, `report.list`, and `report.schedule`.

#### 8.2.9 Module 9: LLM Chat Interface (10 days)

The LLM Chat Interface is the sole user interface of the system. It is a WebSocket-based conversational layer that orchestrates all accounting functions through natural language dialogue [^400^]. This module consumes the second-largest effort allocation (10 days) because it integrates every other module's capabilities into a coherent conversational experience.

**Conversational transaction entry** allows multi-turn dialogue for complex transactions. For example, the user might say "Create an invoice" and the system responds with "Who is this for?" → the user names the customer → "What items?" → the user describes the services → "What payment terms?" → the user specifies Net 30 → the system presents a confirmation summary before posting. This multi-turn pattern is essential for transactions with multiple parameters that cannot be expressed in a single natural language utterance.

**Context memory** maintains entity state across the conversation: the current VAT period, recent transactions, open invoices, unreconciled bank lines, and selected bank account. The system remembers that the user's VAT quarter ends on March 31st and references it automatically when the user asks "Show me my VAT return."

**Intent routing** uses the supervisor pattern: the LLM classifies the user's intent, selects the appropriate SKILL, populates its parameters from the utterance, and executes it [^16^]. If execution fails, the LLM translates the API error into a user-friendly explanation and suggests a correction. Destructive actions (reversing a transaction, cancelling a sent invoice) require explicit confirmation gates.

**Natural date parsing** supports expressions such as "last month," "yesterday," "Q2 2025," and "this financial year," converting them to precise date ranges for report and query parameters. **Ambiguity resolution** handles cases where the user's instruction could match multiple objects — "You mentioned two invoices for ABC Ltd — did you mean INV-0012 or INV-0015?"

Three persona options tailor the conversational tone: **Professional Accountant** (formal, precise language), **Friendly Advisor** (conversational, proactive suggestions), and **Minimal** (terse, data-focused responses). The user selects their preferred persona during first-time setup and can change it at any time via chat.

The Skill Registry is central to this module: 25+ MVP skills are registered with JSON schema definitions, each containing a description written from the LLM's perspective so the model knows when and how to invoke it [^115^][^112^]. Table 8-7 presents the consolidated MVP skill registry.

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

The registry is loaded into the LLM's context at the start of each session, enabling the model to route user requests to the correct skill without hardcoded command patterns. The safety layer enforces `max_iterations` guards, permission checks, and confirmation requirements on all destructive operations [^112^].

#### 8.2.10 Module 10: Authentication and Security (3 days)

The authentication and security module protects all API endpoints and chat sessions. It implements JWT-based API authentication (JSON Web Tokens signed with RS256, 30-minute access token expiry, rotating refresh tokens with 60-day expiry), a single-user constraint for the MVP (multi-user support with role-based access control is deferred to Phase 2), and API key generation for programmatic access by integrations or accountants.

All communications use HTTPS/TLS 1.3 externally. Database encryption at rest is provided through PostgreSQL TDE (Transparent Data Encryption) or LUKS full-disk encryption. Row-level audit logging records every create, read, update, and delete operation on financial transaction data, including the user's identity, timestamp, IP address, and the before/after state of modified records. GDPR-compliant data handling is implemented from day one: personal data is processed with consent, and a pseudonymisation layer ensures the right to erasure can be honoured without corrupting the financial audit trail.

### 8.3 MVP Quality Gates

Quality gates are automated checks that execute before any transaction is posted to the ledger. These gates form a non-negotiable validation layer that prevents the 91.67% of double-entry errors that LLMs generate without structured guidance [^412^].

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
| Ledger Engine | Formance Ledger (open source, MIT-licensed) | Sum-to-zero enforcement, append-only postings, Numscript DSL, PostgreSQL-backed [^45^][^213^] |
| API Framework | FastAPI (Python) or NestJS (Node.js) | Rapid development, OpenAPI specification, async support |
| Database | PostgreSQL 16+ | ACID compliance, JSONB for metadata, window functions for reports |
| LLM Orchestration | OpenAI GPT-4o / Claude Sonnet via function calling | Function calling for skill routing, 128K context window [^116^] |
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

The architecture of the MVP — ten modules, 39 registered skills, six financial quality gates, and four validated user flows — establishes the foundation upon which all subsequent phases build. Phase 2 (Months 3–5) adds bank feed automation, document extraction, recurring transactions, and HMRC MTD submission, expanding the skill registry to 65+ and reducing manual data entry effort by over 70%. The 8-week MVP demonstrates that a complete bookkeeping cycle can be operated entirely through natural language conversation, with every financial invariant enforced by deterministic validation layers beneath the conversational surface [^45^][^213^][^124^].
