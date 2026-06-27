## 2. Core Ledger and Data Model

The preceding chapter established the system's five-layer architecture and the rationale for building on Formance Ledger. This chapter descends into the layer immediately above the ledger substrate: the core accounting data model that gives structure to every financial event the system processes. Section 2.1 examines Formance Ledger's built-in guarantees -- sum-to-zero enforcement, append-only immutability, bi-temporal timestamps, and hash chaining -- and explains why these properties are non-negotiable for a system in which an LLM (Large Language Model) generates transactions. Section 2.2 presents the Chart of Accounts (COA) architecture: a five-category, 4-digit gap-friendly numbering scheme, eight pre-loaded templates for UK business structures, and metadata-driven multi-standard support that allows a single COA to serve IFRS, US GAAP, and UK GAAP simultaneously. Section 2.3 details the transaction processing pipeline, from entity-relationship structure through VAT-aware Numscript generation to a three-layer validation stack that catches over 91% of LLM-generated errors before they reach the ledger [^412^]. Section 2.4 completes the picture with supporting data models for contacts, invoices, and bank accounts.

---

### 2.1 Formance Ledger Foundation

#### 2.1.1 Double-Entry Properties

Formance Ledger is an open-source, programmable financial ledger released under the MIT licence [^169^]. At its core, it is a purpose-built double-entry engine that stores transactions as sets of postings -- directional movements between accounts -- and enforces the fundamental accounting invariant that every transaction must sum to zero. This enforcement occurs at the database constraint level, not merely in application code, which means a malformed transaction cannot reach persistent storage even if all upstream validation were bypassed [^45^].

Four properties of Formance are foundational to the system's design. **Sum-to-zero enforcement**: each Formance transaction contains postings specifying source account, destination account, asset code, and amount. A `CHECK` constraint at insert time rejects any transaction whose postings do not balance to zero [^45^]. For the LLM-native system, this functions as a final circuit breaker: even if the LLM produces an unbalanced draft and the business-rule layer fails to catch it, the ledger itself refuses the write. **Append-only postings**: Formance does not provide `UPDATE` or `DELETE` on postings. Once committed, a transaction becomes immutable [^363^][^367^]; corrections are handled by posting compensating transactions that leave a complete audit trail. This property is essential for HMRC Making Tax Digital (MTD), which requires digital records to be preserved without alteration for six years [^124^], and for the EU AI Act, which mandates non-repudiable logs for high-risk automated decision-making systems. **Bi-temporal timestamps**: every transaction carries `effective_date` (when the business event occurred) and `recorded_at` (when the system committed it) [^260^], enabling back-dated entries, period-lock queries, and idempotent retries. **Idempotency keys**: Formance natively supports client-supplied idempotency keys via the `ik` field [^366^]. A deterministic key such as `SALE_INV:INV-2024-0042:2024-06` prevents duplicate transactions on network retry; resubmission with an identical payload returns the original response, while a differing payload returns `409 Conflict`.

| Property | Mechanism | Accounting Purpose | LLM-Native Purpose |
|----------|-----------|-------------------|-------------------|
| Sum-to-zero | PostgreSQL `CHECK` constraint on postings [^45^] | Debits = credits invariant | Final circuit breaker for LLM errors |
| Append-only | No `UPDATE`/`DELETE`; compensating entries only [^363^] | Immutable audit trail | MTD and EU AI Act retention compliance |
| Bi-temporal | `effective_date` + `recorded_at` timestamps [^260^] | Period accuracy, back-dating | Idempotency and retry safety |
| Idempotency | Client `ik` field with server-side dedup [^366^] | Duplicate prevention | Safe retry of LLM-generated transactions |
| Hash chain | SHA-256 per-transaction hash linking [^dim11^] | Tamper evidence | Cryptographic AI decision audit trail |

The interplay of these five properties creates what the cross-dimensional analysis identified as a "conversational audit trail": every natural language request, LLM reasoning step, Numscript generation, and human approval is cryptographically linked to its resulting ledger entry in a tamper-evident chain [^insight1^]. Traditional systems log *what* happened; the Formance substrate enables this system to log *why* it happened, *how* the AI reasoned, and *who* approved it, all in one immutable sequence. In an EU AI Act enforcement action or SOX audit, producing this complete provenance chain -- "the user said X, the AI reasoned Y, the supervisor approved Z, the ledger recorded W" -- is a capability that retrofitted competitors cannot easily match. The patent opportunity around natural language intent preservation in immutable financial ledgers derives directly from this architectural property.

#### 2.1.2 Numscript as Transaction DSL

Numscript is a domain-specific language (DSL) purpose-built for financial transactions within Formance [^200^][^228^]. It serves as the target output format for LLM-generated transactions: the LLM does not emit raw SQL or JSON postings; it produces Numscript, which is then validated and executed. This design choice follows the research finding that constraining LLM output to a validated DSL improves accuracy by approximately 40 percentage points over free-form generation [^dim03^].

Numscript's syntax is designed to be both human-readable and machine-parseable. The core pattern `send [GBP/2 10000] ( source = @user:world destination = @bank:checking )` moves GBP 100.00 from the `world` account (Formance's built-in source of funds) to the checking account. The asset notation `GBP/2` indicates two decimal places, meaning the amount `10000` represents 100.00 pounds -- this integer-math design eliminates floating-point rounding errors entirely. The language supports variables for reusable templates (`vars { monetary $amount; account $dest }`), split destinations for VAT splits and multi-party payments, ordered sources with overdraft protection, the `save` statement for earmarking funds, account interpolation for dynamic resolution, and metadata attachment via `set_tx_meta()` [^232^][^233^][^235^].

The atomicity guarantee is Numscript's most important property for this system. Each execution produces either all postings or none; if any constraint fails -- insufficient balance, invalid account, overdraft violation -- the entire transaction is rejected [^200^]. A complex payroll entry with twelve postings across six accounts either succeeds completely or rolls back entirely, eliminating the partial-write risk that plagues manual journal entry systems. Furthermore, because Numscript is human-readable, it serves as both executable code and audit documentation -- the EU AI Act requirement for transparent, explainable automated decisions is satisfied by the Numscript itself [^insight8^].

#### 2.1.3 Throughput and Scaling

Formance Ledger achieves approximately 1,000 transactions per second per ledger on commodity PostgreSQL hardware [^433^]. At this rate, a single ledger processes 86.4 million transactions per day -- a ceiling that exceeds typical small business workloads by several orders of magnitude, as most SME accounting systems process fewer than 10,000 transactions per month [^dim01^]. Scaling beyond the per-ledger limit is achieved through **ledger sharding**: each tenant receives its own Formance ledger stored in a separate PostgreSQL schema providing namespace isolation [^498^]. Ledgers are entirely independent, so aggregate throughput scales linearly with PostgreSQL instances. Row locking is applied per `(account, asset)` pair [^433^], meaning transactions touching different accounts execute in parallel, while transactions sourcing from the same account are serialised. For high-throughput scenarios such as payroll runs where many employees are paid from the same account, the system mitigates contention by staging payments through intermediate clearing accounts and posting the net movement from the bank account [^430^].

---

### 2.2 Chart of Accounts Architecture

#### 2.2.1 Five-Category, 4-Digit Gap-Friendly Numbering

The Chart of Accounts (COA) is the foundational classification scheme against which all financial transactions are recorded. Neither IFRS nor US GAAP prescribes a mandatory COA structure; both frameworks allow flexibility in account organisation while mandating specific presentation requirements for financial statements [^246^][^180^]. This flexibility enables a unified COA that adapts to multiple standards through metadata-driven configuration rather than structural duplication.

The system employs a **4-digit hierarchical numbering scheme** with intentional gaps for future expansion [^434^][^436^]. This convention provides 100 account slots per hundred-point sub-range while leaving room for insertion as businesses grow.

| Range | Category | Sub-Ranges | Example Accounts |
|-------|----------|------------|-----------------|
| 1000 -- 1999 | **Assets** | 1000--1099: Cash & Equivalents; 1100--1199: Receivables; 1200--1499: Inventory & Current Assets; 1500--1799: Fixed Assets; 1800--1999: Intangible Assets | 1000 Cash -- Operating; 1100 Accounts Receivable; 1200 Inventory; 1400 Office Equipment |
| 2000 -- 2999 | **Liabilities** | 2000--2099: Accounts Payable; 2100--2199: Tax Liabilities; 2200--2299: Short-Term Debt; 2300--2499: Deferred Revenue; 2500--2799: Long-Term Debt; 2800--2999: Provisions | 2000 Accounts Payable; 2100 VAT Output Tax; 2200 Short-Term Loans; 2300 Deferred Revenue -- Current |
| 3000 -- 3999 | **Equity** | 3000--3099: Share Capital; 3100--3199: Retained Earnings; 3200--3499: Reserves; 3500--3999: Other Equity | 3000 Common Stock; 3100 Retained Earnings; 3200 Revaluation Surplus (IFRS only) |
| 4000 -- 4999 | **Revenue** | 4000--4099: Product/Service Revenue; 4100--4199: Subscription/Recurring; 4200--4499: Other Revenue; 4500--4999: Contra-Revenue | 4000 Product Sales; 4010 Service Revenue; 4020 Subscription Revenue; 4900 Sales Returns |
| 5000 -- 6999 | **Expenses** | 5000--5099: Direct Materials; 5100--5199: Direct Labour; 5200--5299: Subcontractors; 5300--5499: Other Direct Costs; 5500--5999: Reserved; 6000--6999: Operating Expenses | 5000 Cost of Goods Sold; 6000 R&D Salaries; 6100 Payroll Taxes; 6200 Rent & Occupancy |

Three gap-friendly rules govern account creation [^436^]: leave 10-point gaps between major groups (1000, 1010, 1020), reserve 100-point blocks for sub-categories (1100--1199 for all receivables), and insert new accounts at midpoints of existing gaps. The maximum hierarchy depth is **two levels**: parent accounts are non-posting summary accounts that aggregate child balances, and deeper nesting is handled through external tracking categories to prevent "exponential account explosion" [^435^][^434^]. Tracking categories -- independent dimensions such as Department, Location, Project, and Product Line -- attach to postings as metadata rather than being embedded in account numbers, enabling flexible reporting without COA bloat [^435^].

#### 2.2.2 Eight Pre-Loaded COA Templates

The system ships with eight pre-loaded COA templates corresponding to the most common UK small business structures. Each extends a universal base COA with structure-specific accounts, eliminating the configuration burden that typically consumes the first hours of accounting system setup.

| Template | Legal Structure | VAT Status | Accounts | Distinctive Features |
|----------|----------------|------------|----------|---------------------|
| UK Sole Trader -- No VAT | Sole trader | Unregistered | 40 | No VAT control accounts; owner draw instead of dividends; simplified equity |
| UK Sole Trader -- VAT | Sole trader | Standard scheme | 55 | Full VAT control trio (2100/2110/2120); MTD-ready metadata |
| UK Limited Company -- No VAT | Private limited | Unregistered | 50 | Share capital (3000); directors' loan account; corporation tax payable |
| UK Limited Company -- VAT | Private limited | Standard scheme | 65 | Complete VAT + CT combination; dividends declared account (3110) |
| UK Partnership -- No VAT | Partnership | Unregistered | 45 | Partners' capital accounts; profit share allocation; no share capital |
| UK Partnership -- VAT | Partnership | Standard scheme | 60 | VAT control + partner current accounts; drawings tracking |
| Micro-Entity Simplified | Any micro-entity | Either | 30 | Minimal COA under FRS 105; aggregated expense categories |
| Property/Landlord VAT | Property rental | Option to tax | 45 | Rent receivable; service charge accounts; capital improvements; CIS deductions |

Template selection occurs during entity creation through conversational onboarding. When a user states "Acme Consulting Ltd, limited company, VAT registered, standard rate," the system loads the "UK Limited Company -- VAT" template (65 accounts), configures the VAT control accounts with the user's GB VAT number, and sets the first VAT period based on the financial year end. This reduces first-day configuration from hours of manual account creation to a single natural language exchange. Each account maps to a Formance colon-delimited path following the pattern `{coa_type}:{standard}:{account_number}:{dimension_path}` [^45^], enabling programmable double-entry with regulatory-grade traceability.

#### 2.2.3 Metadata-Driven Multi-Standard Support

A single COA serves multiple accounting standards simultaneously through **presentation-layer mapping**. The underlying account codes remain constant; only the presentation metadata changes [^dim02^]. Every account carries a `standard_mapping` metadata block controlling how it appears under each framework. Under US GAAP, account 3200 (Revaluation Surplus) is marked `applicable: false` because revaluation of property, plant and equipment is prohibited except for impairment testing [^177^]. Under IFRS, the same account is `applicable: true` and presented as an equity reserve under IAS 16 [^177^]. Display names localise automatically: account 3000 appears as "Common Stock" under US GAAP and "Share Capital" under IFRS [^409^][^410^]. IFRS 18 five-category metadata (Operating, Investing, Financing, Income Taxes, Discontinued Operations) is stored on each revenue and expense account, enabling IFRS 18-compliant P&L production when the standard becomes mandatory in January 2027 [^insight13^].

This approach eliminates the "one system per jurisdiction" anti-pattern that burdens multi-standard businesses using NetSuite or Sage Intacct. A transaction posting to account 3200 is recorded once in the ledger; the reporting layer applies standard-specific filters and display rules at presentation time. When a UK company expands to the US, no COA restructuring is required -- the accountant simply enables US GAAP presentation mapping on existing accounts. The same codebase serves UK SMEs (Phase 1), US small businesses (Phase 3), and EU cross-border operations (Phase 4) without parallel system deployments [^insight5^].

---

### 2.3 Transaction Processing

#### 2.3.1 Transaction Data Model

The transaction data model follows the Entity-Account-Posting-Transaction hierarchy: one entity owns many accounts; one account accumulates many postings; each posting belongs to exactly one transaction; and each transaction contains at least two postings. This structure maps directly to Formance's core tables [^45^]:

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `accounts` | `id`, `address` (e.g., `assets:universal:1000:bank:operating`), `metadata` | COA definitions with Formance colon-delimited paths |
| `transactions` | `id`, `timestamp`, `reference` (idempotency key), `metadata` | Atomic transaction units with business context |
| `postings` | `id`, `transaction_id` (FK), `source`, `destination`, `asset`, `amount` | Directional value movements between accounts |

Balances are computed at read time by aggregating postings per account. Metadata attached to any transaction or account is queryable directly through Formance's API [^45^]. Every transaction progresses through a status lifecycle: **Draft → Posted → Reversed** [^362^]. Draft transactions exist only in the application database and have not been submitted to Formance. Once posted, a transaction becomes immutable; corrections require a new compensating transaction. Auto-numbering follows `JE-YYYY-NNNN` (for example, `JE-2025-0042`), where `YYYY` is the fiscal year and `NNNN` is a sequential counter reset annually.

#### 2.3.2 VAT-Aware Processing

The system handles VAT through account metadata rather than a separate tax engine. Each account carries a `tax_category` field: `VAT_20` (standard rate), `VAT_5` (reduced rate), `VAT_0` (zero-rated), or `EXEMPT`. When the LLM parses "Paid £156 to HMRC for corporation tax," the parameter extraction layer identifies accounts, amounts, and applicable VAT treatment. For a VAT-inclusive purchase, the pipeline extracts the gross amount (£156), reads the VAT rate from account metadata (20% standard), and computes the split: net £130.00, VAT £26.00. The Numscript template then generates postings that debit the expense account £130.00, debit input VAT (2110) £26.00, and credit the bank £156.00. This automatic splitting eliminates the manual VAT apportionment that causes errors in traditional bookkeeping.

VAT control accounts manage the timing difference between when tax is collected or paid and when it is remitted to the tax authority [^268^]. The standard trio comprises: VAT Output Tax (2100, current liability) for tax on sales; VAT Input Tax (2110, current asset) for tax on purchases; and VAT Control Account (2120, current liability) for the net position [^89^]. Monthly settlement transfers the balance from output and input accounts to the control account, and HMRC payment debits the control account and credits the bank. Reverse charge VAT for cross-border B2B services is handled through a dedicated Reverse Charge account (2140) that self-accounts for VAT the customer must declare [^268^].

#### 2.3.3 Pre-Built Numscript Templates

The system provides more than 50 pre-built Numscript templates covering the complete range of small business transaction types [^dim03^]. These templates are the structural foundation of the LLM-to-ledger pipeline. Research by Weber et al. (2025) demonstrated that LLMs achieve only 8.33% accuracy generating correct double-entry transactions from scratch, but accuracy improves dramatically with structured patterns and template-based generation [^76^][^412^]. The architecture addresses this gap by constraining the LLM to **template population** (filling variable slots in pre-validated Numscript) rather than free-form generation.

| Template Category | Examples | Numscript Template | Posting Pattern |
|-------------------|----------|-------------------|-----------------|
| Revenue | Sales invoice, cash sale, subscription | `SALES_INVOICE` | Dr AR; Cr Revenue; Cr VAT Output |
| Expense | Purchase bill, cash expense, bill payment | `PURCHASE_BILL` | Dr Expense; Dr VAT Input; Cr AP |
| Asset | Asset purchase, depreciation, disposal | `DEPRECIATION` | Dr Depreciation Expense; Cr Accumulated Depreciation |
| Liability | Loan drawdown, repayment, tax settlement | `TAX_SETTLEMENT` | Dr VAT Control; Cr Bank |
| Equity | Owner investment, drawings, dividends | `OWNER_DRAW` | Dr Bank; Cr Equity (or reverse) |
| Bank | Transfer between accounts, FX conversion | `BANK_TRANSFER` | Dr To-Bank; Cr From-Bank |
| Correction | Full reversal, partial adjustment | `REVERSAL` | Mirror of original (all signs inverted) |
| Payroll | Gross wages, employer taxes, net pay | `PAYROLL_GROSS` | Dr Wages Expense; Cr Multiple Payables |

Each template declares typed variables at the top (`vars { monetary $amount; account $customer; string $invoice_ref; portion $tax_rate }`). The LLM's task is reduced to extracting values for these variables from natural language. An instruction such as "Invoice ABC Ltd £2,400 for website project plus VAT" populates `$amount = GBP/2 240000`, `$customer = customers:abc_ltd`, `$tax_rate = 20/100`. The template engine substitutes these into the pre-validated `SALES_INVOICE` template, improving accuracy by an estimated 40 percentage points over free-form generation [^dim03^]. Additional strategies further improve accuracy: chain-of-thought prompting (+15--20%), few-shot examples (+25--30%), constrained decoding with JSON Schema (+20%), and multi-stage validation catching 91%+ of residual errors [^dim03^].

#### 2.3.4 Three-Layer Validation

Every transaction passes through three validation layers before reaching the ledger. This architecture is the non-negotiable safety net that catches the 91.67% of errors that LLMs produce when generating double-entry without guidance [^412^].

| Layer | Name | Function | Checks Performed | Failure Action |
|-------|------|----------|-----------------|----------------|
| 1 | Syntax | Numscript parser | Grammar, type consistency, variable declaration, AST generation [^231^] | Reject with parse error |
| 2 | Business Rules | Domain validator | Balance check, COA membership, period lock, tax consistency, duplicate detection | Reject with rule violation; route to human review |
| 3 | Ledger Constraints | Formance engine | Account existence, overdraft limits, asset code consistency | Reject with Formance error; no partial writes |

**Layer 1 (Syntax)** uses the Numscript parser (ANTLR4-based) to validate grammar, variable declarations, and type consistency, producing a structured AST before execution [^231^]. A missing semicolon or type mismatch between `monetary` and `portion` is caught here and returned to the LLM with an error message enabling automated correction. **Layer 2 (Business Rules)** applies domain-specific checks through a pluggable validator: for `SALE_INV`, it verifies positive amount, customer account existence, valid tax rate, unused invoice reference, and open accounting period. For payroll, it confirms gross equals net plus all deductions [^365^]. Period lock enforcement prevents posting to closed periods; adjustments to closed periods require explicit authorisation from an accounting manager. **Layer 3 (Ledger Constraints)** is performed by Formance itself: overdraft prevention on non-overdraft accounts, automatic balance enforcement (cannot be disabled), asset consistency, and account existence [^260^]. Because Formance enforces these at the database level, they serve as the final defence against any error penetrating the first two layers.

The correction workflow follows the immutable ledger principle. Because Formance does not support edits or deletes, all corrections are compensating transactions [^363^][^365^][^367^]. The `REVERSAL` template creates an exact mirror of the original; Formance's `revert_transaction` API automates this [^188^][^259^]. Partial adjustments reverse only the incorrect portion and post to the correct account. Every correction carries provenance metadata including the original transaction ID, requesting user, approver, reason, and timestamp, creating a complete audit trail of the correction itself.

---

### 2.4 Supporting Data Models

#### 2.4.1 Contact Management

The **Contact** entity represents any party with whom the business has a financial relationship: customers, suppliers, or both. Contact records are created explicitly through the chat interface ("Add a new supplier: Acme Office Supplies") or automatically when the LLM extracts a name from a transaction description that does not match an existing contact. Each contact stores: type (`Customer`, `Supplier`, or `Both`); name and company name; email and phone; billing and shipping addresses; VAT registration number; payment terms (Net 30 default); default ledger account; and currency. The system tracks AR and AP balances per contact by aggregating postings to the linked receivable or payable account. When a user asks "How much does ABC Ltd owe me?" the system queries the aggregated balance rather than scanning individual invoices.

Auto-creation from transactions is a key LLM-native feature. When the user says "Paid £50 to Spotify for subscription," the entity extraction layer identifies "Spotify" as a supplier, finds no existing contact, and creates a new supplier with name "Spotify," type `Supplier`, and default expense account `Software & Subscriptions` (6410). This eliminates the manual contact setup that interrupts transaction entry in traditional systems. Duplicate detection runs by comparing name similarity, email domain, and VAT number to prevent contact proliferation.

#### 2.4.2 Invoice Lifecycle

The **Invoice** entity represents a demand for payment from a customer. Its lifecycle follows a strict state machine enforcing accounting integrity [^268^][^267^]: **Draft → Sent → Viewed → Paid → Overdue → Cancelled**. In `DRAFT`, all fields are editable: customer, line items (description, quantity, unit price, VAT rate, line total), payment terms, and due date. Once sent, core fields become immutable to protect the audit trail. Corrections after sending require a **credit note** (negative invoice referencing the original) followed by re-issue. `VIEWED` is set when the customer opens the invoice link (tracked via email pixel or portal access log); `PAID` on bank transaction match; `OVERDUE` on automatic due-date expiry; and `CANCELLED` only via a fully reversing credit note.

VAT calculation occurs per line and in summary: a line of "10 hours consulting at £80/hr" with 20% VAT produces net £800.00, VAT £160.00, line total £960.00. The invoice totals roll up subtotal, VAT total, and grand total. Invoice numbering follows `INV-YYYY-NNNN`, auto-sequential within each fiscal year. Post-send immutability on core fields (customer, line items, amounts, VAT) ensures that once an invoice has been communicated to a customer, its financial content cannot be altered without an explicit correction trail. Payment reconciliation is a safe post-send operation that transitions the invoice to `PAID` without modifying core financial data.

#### 2.4.3 Bank Account Model

The **Bank Account** entity supports multiple accounts per entity: current, savings, and foreign currency accounts. Each stores: account name (display label); sort code and account number (UK domestic); IBAN (international); currency (ISO 4217 code, default `GBP`); opening balance; and current computed balance (aggregated from ledger postings). Bank transactions imported from CSV or OFX files follow a three-status pipeline: **Imported → Categorized → Reconciled**. `IMPORTED` means parsed from the source file but not yet matched to a ledger entry. `CATEGORIZED` means assigned a COA account and contact ("Tesco £45.60" as "Office Supplies"). `RECONCILED` means matched to one or more ledger postings with agreeing balances.

Reconciliation matching supports one-to-one, one-to-many, and partial matches. A single bank deposit of £5,000 might match five separate invoice payments. Partial matching handles cases where the bank amount differs from the invoice amount due to deducted fees: an invoice for £1,000 paid with £15 bank fee deducted appears as £985 on the bank statement; the system matches £985 to the invoice and creates a separate £15 bank charge expense. The bank model connects to the reactive event pipeline described in Chapter 1: when a Formance transaction posts, the `COMMITTED_TRANSACTIONS` event [^524^] triggers the bank feed service to check for matches, the reporting service to invalidate cached reports, and the notification service to alert the user -- all in real time within milliseconds. This reactive pattern eliminates the batch processing that makes month-end reconciliation a multi-day exercise in traditional systems [^insight7^], reducing the reconciliation workload that typically consumes 40% or more of accountant time.
