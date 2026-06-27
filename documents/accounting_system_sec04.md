## 4. Financial Reporting SKILLs

The preceding chapter described the agentic interface that interprets user intent and routes execution to specialized capabilities. This chapter details the largest and most heavily regulated capability domain: financial reporting. The system delivers 33 distinct report SKILLs organized across seven categories, all executing through a deterministic five-stage pipeline that guarantees identical inputs produce identical outputs. Every SKILL is registered with a JSON schema that defines its parameter envelope, data dependencies, and output structure, enabling programmatic discovery and validation [^301^]. The architecture treats accounting standards --- GAAP, IFRS, and jurisdiction-specific tax regimes --- as interchangeable rule bundles applied during pipeline execution, so a single SKILL produces framework-compliant output without code changes.

### 4.1 Report Engine Architecture

#### 4.1.1 Five-Stage Pipeline

All report SKILLs execute through a uniform five-stage pipeline. This design ensures that every report --- from a simple trial balance to a multi-entity consolidated cash flow statement --- follows the same deterministic path from parameter ingestion to formatted output. The pipeline guarantees that the same parameter envelope submitted twice, assuming no underlying data changes, produces byte-identical output [^290^]. This property is essential for audit reliability and regulatory acceptance.

| Stage | Name | Function | Key Operations |
|-------|------|----------|----------------|
| 1 | Parameter Ingestion | Validate and normalize input | Schema validation, default application, period resolution, currency normalization |
| 2 | Query Layer Execution | Acquire raw data | SQL queries against GL, COA, journal entries, contacts, tax transactions; REST calls for exchange rates |
| 3 | Data Model Transformation | Apply business logic | Aggregation, period logic, currency conversion, intercompany elimination, reclassification, dimensional slicing |
| 4 | Rule Application | Apply framework-specific rules | Account classification, line ordering, subtotals, disclosure requirements, sign conventions |
| 5 | Output Formatting | Serialize to target format | JSON structuring, HTML templating, PDF rendering, CSV flattening, XBRL taxonomy mapping |

The deterministic guarantee rests on two architectural decisions. First, Stage 1 resolves all relative date references ("last month," "prior quarter") to absolute ISO dates against a known system time, so the same natural-language request always resolves to the same period boundaries. Second, Stage 2 queries use READ COMMITTED isolation with a snapshot timestamp derived from the request time, ensuring that concurrent transactions do not introduce non-determinism. Each SKILL declares its maximum execution time (default 30,000 ms) and cache time-to-live (default 300 seconds) within its schema, allowing the execution engine to apply resource limits predictably [^302^].

The query layer in Stage 2 interfaces with multiple data sources through a unified abstraction. General ledger transactions, chart of accounts metadata, journal entries, contact master data, tax transactions, budget and forecast data, tracking categories, and audit logs are accessed via SQL against the primary PostgreSQL store. Exchange rates require REST calls to external rate providers, while XBRL taxonomy data is queried through GraphQL to support flexible element resolution. The query planner analyzes parameter dependencies and executes independent queries in parallel where possible, reducing latency for reports that draw from multiple sources.

Stage 3 applies the core business logic that transforms raw query results into a structured report data model. This stage handles aggregation (rolling transactions up to account, category, or dimension level), period logic (fiscal year variations, 4-4-5 calendars, multi-period rollups), currency conversion (applying period-end, average, or historical exchange rates depending on the report type), intercompany elimination (removing intra-group transactions for consolidated reports), account reclassification (mapping internal account codes to standard reporting categories), and dimensional slicing (filtering by tracking category, department, project, or region). Each transformation operation is logged with its input hash and output hash, creating a verifiable audit trail [^270^].

Stage 4, Rule Application, is where framework-specific accounting rules are applied. Classification rules map each account to its appropriate reporting category --- under IFRS 18, accounts must be classified into Operating, Investing, Financing, Income Taxes, or Discontinued Operations categories [^325^]. Aggregation rules define how line items group into subtotals and totals. Disclosure rules determine which supplementary notes and Management Performance Measure (MPM) reconciliations must appear [^308^]. Validation rules enforce cross-checks such as the accounting equation (Assets = Liabilities + Equity) on balance sheets and the debit-credit balance requirement on trial balances [^299^]. Sign conventions differ between GAAP and IFRS for certain presentation elements, and the rule engine applies the appropriate convention based on the framework parameter.

Stage 5 serializes the processed data model into the requested output format. The output layer supports six formats --- JSON, HTML, PDF, CSV, XBRL, and iXBRL --- each discussed in Section 4.4. The format selector receives the fully processed data model and applies the appropriate serializer without re-executing any upstream pipeline stage, ensuring consistent output across formats for the same underlying data.

#### 4.1.2 Framework Parameterization

A central design objective is that the same report SKILL produces compliant output for different accounting standards through configuration rather than code duplication. The `framework` parameter, accepted by every core statement SKILL, selects a rule bundle that defines how the report is constructed. Supported values are `gaap_us`, `gaap_uk`, `ifrs`, `tax_uk`, `tax_au`, and `tax_us`, with `ifrs` as the default [^263^].

Each rule bundle is a JSON document that defines five rule domains: account classification mapping, line item ordering and grouping, required subtotals and totals, disclosure requirements, and sign conventions with terminology. When a SKILL executes, the Stage 4 rule engine loads the bundle corresponding to the `framework` parameter and applies each rule in sequence.

| Reporting Element | US GAAP | IFRS |
|-------------------|---------|------|
| P&L format | No prescribed format; SEC Reg S-X guidance | IFRS 18: 5 mandatory categories with required subtotals [^301^] |
| Inventory cost method | LIFO permitted | LIFO prohibited; FIFO or weighted average only |
| Development expenditure | Expensed as incurred | Capitalized if technical and commercial feasibility criteria met |
| Impairment reversal | Prohibited | Allowed if criteria met |
| Extraordinary items | Permitted (though rare) | Prohibited |
| Balance sheet terminology | "Balance Sheet" | "Statement of Financial Position" |
| Income statement terminology | "Income Statement" | "Statement of Profit or Loss" |
| Cash flow indirect start | Net income | Operating Profit (IFRS 18) [^303^] |
| Goodwill presentation | May combine with intangibles | Must be separate line item [^303^] |

The differences in the table above are handled granularly: a SKILL applies only the rules relevant to its report type and the data present in the current period. This avoids the combinatorial explosion that would result from maintaining separate report templates per framework. Under this architecture, the underlying chart of accounts and general ledger entries remain unchanged; only the presentation-layer mapping differs [^263^].

### 4.2 Core Financial Statement SKILLs

#### 4.2.1 P&L Statement (core.pl)

The Profit & Loss Statement SKILL produces the primary report of financial performance over a period. Under IFRS 18, effective January 2027, this statement adopts a fundamentally new structure representing the most significant change to income statement presentation in over two decades [^301^]. The P&L SKILL natively supports this structure through the `ifrs18_options` parameter, enabling full or transitional compliance, expense presentation by nature or by function, and mandatory MPM disclosure [^308^].

IFRS 18 introduces five mandatory categories for classifying income and expenses. Every item must fall into exactly one category, replacing the current practice of presenting a single block of revenue and expenses [^325^].

| IFRS 18 Category | Scope | Typical Line Items |
|------------------|-------|--------------------|
| Operating | Core business activities; default/catch-all | Revenue, cost of sales, SGA expenses, R&D, depreciation of operating assets |
| Investing | Returns from investments and investment-related items | Interest income, dividend income, gains/losses on disposal of investments, share of JV profits |
| Financing | Cost of raising and servicing finance | Interest expense, foreign exchange differences on financing liabilities |
| Income Taxes | Tax per IAS 12 | Current tax expense, deferred tax expense |
| Discontinued Operations | Components disposed of or held for sale per IFRS 5 | Post-tax results of disposed segments |

Between these categories, IFRS 18 mandates specific subtotals. The first is **Operating Profit or Loss**, appearing after all operating income and expenses. Investing category items (share of associates, interest income) are added to arrive at **Profit or Loss before Financing and Income Taxes**. After deducting financing costs and income taxes, the final mandatory total is **Profit or Loss (Net Income)** [^325^]. The P&L SKILL enforces this hierarchy and validates that the arithmetic progression from revenue to net income is mathematically consistent.

IFRS 18 also introduces mandatory disclosure requirements for Management Performance Measures (MPMs) --- subtotals of income and expenses that management uses in public communications outside the financial statements [^301^]. Common examples include Adjusted EBITDA, underlying profit, and free cash flow. Under IFRS 18, MPM disclosures are mandatory, must appear within the financial statements, and fall within audit scope [^308^]. The P&L SKILL supports MPM reconciliation through a dedicated parameter block recording the measure name, description, and line-by-line reconciliation from the nearest IFRS-defined total to the MPM figure.

#### 4.2.2 Balance Sheet (core.bs)

The Balance Sheet SKILL produces a statement of financial position per the accounting equation: Assets = Liabilities + Equity [^326^]. The SKILL supports three format options via the `detail_level` parameter: **standard** (standard line items with subtotals), **detailed** (additional breakdowns such as AR by aging bucket and fixed assets by type), and **comparative** (current period alongside prior period with variance columns).

The balance sheet organizes assets into current and non-current categories. Current assets include cash, accounts receivable (net of allowance), inventory, prepaid expenses, and short-term investments. Non-current assets include property, plant and equipment (net), intangible assets (net), goodwill (which IFRS 18 requires as a separate line item) [^303^], long-term investments, deferred tax assets, and other non-current items. Liabilities follow the same split, with current liabilities covering accounts payable, short-term debt, accrued expenses, deferred revenue, and tax payable; non-current liabilities include long-term debt, bonds payable, deferred tax liabilities, pension obligations, and lease liabilities. Equity presents share capital, share premium, treasury shares, retained earnings, other reserves, and non-controlling interests [^326^].

The SKILL validates the accounting equation on every execution: Total Assets must equal Total Liabilities plus Total Equity. Any deviation triggers a validation error preventing output generation and routing the failure to the reconciliation agent for investigation.

#### 4.2.3 Cash Flow Statement (core.cf)

The Cash Flow Statement SKILL supports both the direct and indirect methods per IAS 7, selected via the `method` parameter [^289^] [^291^]. Under the direct method, operating cash flows are presented as major classes of gross cash receipts and payments. Under the indirect method --- the more common approach --- the statement begins with net income (or, under IFRS 18, operating profit) and adjusts for non-cash items and changes in working capital [^289^].

IFRS 18 makes specific changes that the SKILL implements when `ifrs18_compliant` is true [^303^]. The indirect method starting point shifts from Net Income to Operating Profit. Interest paid moves from operating activities to financing activities; interest received and dividends received move from operating to investing activities; dividends paid must be classified as financing. These changes align the cash flow statement categories with the P&L categories under IFRS 18. The SKILL's `classifications` parameter block allows explicit override of each classification, with IFRS 18-compliant defaults when the framework is IFRS.

#### 4.2.4 Trial Balance (core.tb)

The Trial Balance SKILL lists all general ledger account balances at a specific point in time and provides the fundamental verification that total debits equal total credits [^302^] [^309^]. An unbalanced trial balance indicates a data integrity issue that must be resolved before any financial statement can be considered reliable [^299^].

The SKILL produces three variants, selected via the `type` parameter, each serving a different point in the accounting cycle [^305^].

| Variant | Timing | Purpose | Key Characteristics |
|---------|--------|---------|---------------------|
| Unadjusted | Before adjusting entries | Initial data capture; reveals obvious errors | Raw ledger balances; may contain accrual mismatches and period-cutoff errors |
| Adjusted | After adjusting entries, before financial statements | Includes corrections, accruals, and deferrals | Reflects all period-end adjustments; basis for financial statement preparation |
| Post-Closing | After closing entries | Verifies ledger is ready for next period | Temporary accounts show zero balances; only permanent accounts remain |

The unadjusted trial balance captures raw ledger balances and serves as the starting point for the adjustment process. The adjusted trial balance includes all correcting entries, accruals, and deferrals, and is the direct input to financial statement generation. The post-closing trial balance confirms that all temporary accounts have been closed to retained earnings, leaving only permanent accounts with non-zero balances [^305^]. The SKILL enforces the debit-credit balance requirement for all three variants: if total debits do not equal total credits, execution fails with a detailed error identifying the variance and suggesting accounts where the discrepancy may originate [^299^].

### 4.3 Management and Tax Report SKILLs

#### 4.3.1 Management Reports

Management reports provide operational visibility beyond regulatory financial statements. The Aged Accounts Receivable SKILL (`mgmt.ar_aging`) groups outstanding invoices into buckets: Current, 1--30 days, 31--60 days, 61--90 days, and 90+ days [^287^] [^288^]. It computes Days Sales Outstanding (DSO) as (Accounts Receivable / Total Credit Sales) multiplied by days in the period. Industry benchmarks suggest DSO should remain below 45 days [^287^]. The 90+ day percentage serves as an early warning indicator: values exceeding 20% of total AR trigger escalation to collections [^293^].

The Aged Accounts Payable SKILL (`mgmt.ap_aging`) applies the same bucket structure to amounts owed suppliers, computing Days Payable Outstanding (DPO) and identifying early payment discount opportunities. The General Ledger Detail SKILL (`mgmt.gl_detail`) produces transaction-level listings showing date, reference, description, debit, credit, and running balance [^316^]. The GL Summary SKILL rolls this data up to account balance level. The Executive Summary SKILL (`mgmt.executive`) combines P&L highlights, balance sheet snapshot, cash position, KPI summary, and variance alerts into a single decision-ready overview [^300^].

| Management Report | SKILL ID | Key Metrics | Primary Users |
|-------------------|----------|-------------|---------------|
| Aged AR | `mgmt.ar_aging` | DSO, 90+ day %, collection rate by bucket | Collections, CFO |
| Aged AP | `mgmt.ap_aging` | DPO, early payment discount opportunity | Treasury, AP manager |
| GL Detail | `mgmt.gl_detail` | Transaction-level drill-down, running balance | Accountant, auditor |
| GL Summary | `mgmt.gl_summary` | Opening/closing balances, net change, YTD | Management accountant |
| Executive Summary | `mgmt.executive` | P&L highlights, BS snapshot, burn rate, KPIs | Board, investors, CEO |

#### 4.3.2 Tax Reports

Tax report SKILLs produce jurisdiction-specific returns from the same underlying transaction data. The VAT Return (UK) SKILL (`tax.vat_uk`) implements the nine-box structure required by HMRC's Making Tax Digital (MTD) framework [^254^] [^256^]. All nine boxes auto-calculate from transaction-level tax data. Box 1 contains VAT due on sales; Box 2 VAT on EU acquisitions (Northern Ireland only post-Brexit); Box 3 the sum of Boxes 1 and 2; Box 4 VAT reclaimed on purchases; Box 5 the net position (Box 3 minus Box 4); Box 6 total sales ex-VAT; Box 7 total purchases ex-VAT; Boxes 8 and 9 EU supplies and acquisitions [^269^]. The SKILL produces both human-readable and HMRC API payload formats. MTD compliance requires digital links from source data to submitted return with no manual re-keying [^124^].

The Australian BAS SKILL (`tax.bas_au`) follows the ATO's G-label format for sales, purchases, PAYG withholding, and instalments [^307^] [^310^]. The generic GST SKILL (`tax.gst`) provides jurisdiction-agnostic output parameterized for any GST-implementing country. The Sales Tax SKILL (`tax.sales_tax`) addresses US state and Canadian provincial tax, tracking nexus status and multi-level jurisdiction breakdowns [^234^] [^236^].

| Tax Report | SKILL ID | Jurisdiction | Key Output |
|------------|----------|-------------|------------|
| VAT Return (UK 9-box) | `tax.vat_uk` | UK HMRC | 9-box VAT return; MTD API payload [^254^] |
| BAS | `tax.bas_au` | Australian Tax Office | G1--G20 labels; GST and PAYG summary [^307^] |
| GST (generic) | `tax.gst` | Multi-jurisdiction | Jurisdiction-specific return; configurable rates |
| Sales Tax | `tax.sales_tax` | US/Canada | Tax by state/county/city; nexus tracking [^234^] |
| Corporation Tax | `tax.corporation_tax` | UK | Taxable profit; capital allowances |

#### 4.3.3 Complete SKILL Catalog

The full report catalog comprises 33 SKILLs across seven categories. This taxonomy emerged from cross-dimensional research where independent sources converged on the same seven-category organization [^115^] [^112^]. The catalog is extensible: new SKILLs register by conforming to the base schema, and the agentic interface discovers them automatically.

| # | Category | SKILL ID | Report Name | Framework |
|---|----------|----------|-------------|-----------|
| 1 | Core Statements | `core.pl` | Profit & Loss Statement | GAAP/IFRS |
| 2 | Core Statements | `core.bs` | Balance Sheet | GAAP/IFRS |
| 3 | Core Statements | `core.cf` | Cash Flow Statement | GAAP/IFRS |
| 4 | Core Statements | `core.tb` | Trial Balance | Universal |
| 5 | Internal Verification | `verify.tb_balanced` | Trial Balance Verification | Universal |
| 6 | Internal Verification | `verify.bs_cf` | Balance Sheet / Cash Flow Reconciliation | GAAP/IFRS |
| 7 | Internal Verification | `verify.intercompany` | Intercompany Elimination Check | GAAP/IFRS |
| 8 | Management | `mgmt.ar_aging` | Aged Accounts Receivable | Universal |
| 9 | Management | `mgmt.ap_aging` | Aged Accounts Payable | Universal |
| 10 | Management | `mgmt.gl_detail` | General Ledger Detail | Universal |
| 11 | Management | `mgmt.gl_summary` | General Ledger Summary | Universal |
| 12 | Management | `mgmt.executive` | Executive Summary Report | Universal |
| 13 | Management | `mgmt.chart_of_accounts` | Chart of Accounts Listing | Universal |
| 14 | Tax | `tax.vat_uk` | VAT Return (UK 9-box) | UK HMRC |
| 15 | Tax | `tax.bas_au` | BAS (Australia) | ATO |
| 16 | Tax | `tax.gst` | GST Return (Generic) | Multi-jurisdiction |
| 17 | Tax | `tax.sales_tax` | Sales Tax by Jurisdiction | US/Canada |
| 18 | Tax | `tax.corporation_tax` | Corporation Tax Computation | UK |
| 19 | Variance | `var.period` | Period-over-Period Comparison | GAAP/IFRS |
| 20 | Variance | `var.budget` | Budget vs Actual | Universal |
| 21 | Variance | `var.forecast` | Forecast vs Actual | Universal |
| 22 | Variance | `var.tracking` | Tracking Category Analysis | Universal |
| 23 | Variance | `var.year_end` | Year-End Comparison (Multi-Year) | GAAP/IFRS |
| 24 | KPI | `kpi.profitability` | Profitability Ratios | GAAP/IFRS |
| 25 | KPI | `kpi.liquidity` | Liquidity Ratios | GAAP/IFRS |
| 26 | KPI | `kpi.efficiency` | Efficiency Ratios | GAAP/IFRS |
| 27 | KPI | `kpi.solvency` | Solvency Ratios | GAAP/IFRS |
| 28 | KPI | `kpi.startup` | Startup Metrics (Burn, Runway, CAC, LTV) | Universal |
| 29 | Audit | `audit.tb_adjusted` | Adjusted Trial Balance | GAAP/IFRS |
| 30 | Audit | `audit.journal_entries` | Journal Entry Report | Universal |
| 31 | Audit | `audit.audit_trail` | Full Audit Trail | Universal |
| 32 | Compliance | `compliance.xbrl` | XBRL/iXBRL Tagging Report | Multi-jurisdiction |
| 33 | Compliance | `compliance.mpm` | Management Performance Measures (IFRS 18) | IFRS |

The Internal Verification category (SKILLs 5--7) contains cross-validation reports. The Trial Balance Verification SKILL confirms debits equal credits. The Balance Sheet / Cash Flow Reconciliation SKILL validates that net cash change reconciles to the cash balance sheet movement. The Intercompany Elimination Check verifies proper elimination for consolidated reporting. These reports execute automatically at period close and feed results into the approval workflow.

### 4.4 Output and Distribution

#### 4.4.1 Six Output Formats

Every report SKILL can produce output in any of six formats, selected via the `output.format` parameter. The format choice determines the Stage 5 serializer but does not affect upstream pipeline stages.

| Format | Serializer | Primary Use Case | Key Properties |
|--------|-----------|-------------------|----------------|
| JSON | Native struct serializer | API responses, downstream processing, LLM consumption | Schema-validated; self-describing with embedded metadata |
| HTML | Jinja2 template engine | Web viewing, dashboards, email body | Responsive CSS; print-friendly `@media print` styles |
| PDF | Playwright headless browser | Document distribution, archival, filing | Professional pagination; headers/footers; digital signature ready |
| CSV | Pandas flattening engine | Spreadsheet import, analysis, data exchange | Header metadata rows; RFC 4180 compliant |
| XBRL | LXML taxonomy mapper | Machine-readable regulatory filing | Taxonomy-mapped elements; ESMA/HMRC compliant [^260^] |
| iXBRL | HTML + XBRL hybrid | Human-readable filing with embedded machine data | Inline XBRL tags; UK mandate from April 2028 [^313^] |

JSON is the default format and the native representation of the report data model, including metadata such as SKILL ID, request ID, framework, entity, currency, period, and generation timestamp. HTML templates are framework-aware: IFRS produces a "Statement of Profit or Loss" header, while GAAP produces "Income Statement," with terminology sourced from the active rule bundle. PDF generation uses a headless browser to render HTML templates with print-specific CSS. CSV output includes comment-prefixed header rows encoding the same metadata as JSON, so consumers can identify report provenance without external context.

#### 4.4.2 Report Scheduling

Report execution triggers through four scheduling models [^290^] [^292^]. **Time-based** scheduling runs reports at fixed intervals: daily, weekly, monthly, quarterly, or annual. **Event-driven** scheduling triggers generation in response to system events such as period close completion, threshold breach, or adjusting entry posting. **Data-driven** scheduling monitors specific conditions and triggers when met --- for example, a burn rate alert when net burn exceeds a threshold, or a DSO report when 90+ day AR crosses 20%. **On-demand** scheduling covers user-initiated requests through the chat interface or API.

The scheduling engine supports distribution via email (SMTP with TLS, password-protected PDF attachments, PGP encryption), SFTP (encrypted file transfer), API/webhook (POST to external endpoints), and collaboration platforms (Microsoft Teams via Graph API, Slack via webhooks). Date formulas such as "LastMonth," "CurrentQuarter," "YearToDate," and "Trailing12Months" resolve at execution time against the entity's fiscal calendar [^290^].

#### 4.4.3 XBRL/iXBRL Layer

XBRL (eXtensible Business Reporting Language) embeds machine-readable tags into financial reports. iXBRL (inline XBRL) combines human-readable HTML with embedded XBRL tags, producing a document readable by both humans and machines [^260^]. The XBRL/iXBRL generation pipeline operates as a six-stage process receiving JSON output from a core statement SKILL and producing a tagged regulatory filing.

Stage 1 generates HTML in human-readable form. Stage 2 maps each line item to the appropriate XBRL taxonomy element --- for example, "Revenue" maps to `ifrs-full:Revenue`. IFRS 18 introduces new elements for mandatory subtotals, including `ifrs-full:OperatingProfitLoss`, incorporated in the IFRS 2025 taxonomy [^260^]. Stage 3 embeds XBRL tags as HTML attributes using the `ix:` namespace. Stage 4 generates XBRL context elements defining the reporting entity, period, and currency unit. Stage 5 validates against taxonomy schema requirements: calculation consistency, business rules, mandatory item checks, data type validation, and duplicate detection [^255^] [^261^]. Stage 6 outputs the final `.html` file containing embedded iXBRL.

The UK mandate timeline drives prioritization. From April 2028, all UK companies must file accounts via software-only iXBRL [^313^] [^319^]. HMRC has mandated iXBRL for company tax returns since 2011 [^314^]. In the EU, ESMA's ESEF mandates iXBRL for listed companies [^260^]. The Compliance XBRL SKILL (`compliance.xbrl`) wraps any core statement SKILL and produces iXBRL output for the selected jurisdiction, making regulatory submission a one-parameter extension of standard report generation.
