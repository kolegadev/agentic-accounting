## Facet: Financial Reporting & Report Generation Architecture

> **Research Date:** June 2025
> **Searches Conducted:** 12 independent web searches across core financial statements, management reports, VAT/GST returns, custom report builders, report templating, chart of accounts design, period comparison reporting, SME KPIs, report automation, XBRL/iXBRL standards, and LLM agent architectures.

---

## Key Findings

### Core Financial Statements

- **IFRS 18 (effective January 2027)** introduces a revised structure for the statement of profit or loss, requiring classification of all income and expenses into operating, investing, financing, income tax, and discontinued operations categories, with mandatory subtotals for "operating profit or loss," "profit or loss before financing and income tax," and "profit or loss" [^178^]. The standard also brings "management-defined performance measures" (MPMs) into the spotlight with new disclosure requirements [^178^].

- **IFRS Balance Sheet (Statement of Financial Position)** requires minimum line items including: property/plant/equipment, investment property, intangible assets, goodwill, financial assets, investments in associates/joint ventures, biological assets, inventories, trade receivables, cash and cash equivalents, assets held for sale, trade payables, provisions, financial liabilities, current/deferred tax assets/liabilities, non-controlling interests, and issued capital/reserves [^41^] [^43^].

- **IFRS Income Statement (Statement of Profit or Loss)** requires line items for: revenue (presenting interest revenue separately using effective interest method), gains/losses on derecognition of financial assets, finance costs, impairment losses, share of profit/loss of associates/joint ventures, tax expense, and discontinued operations — plus items required by other IFRS standards [^43^].

- **GAAP (ASC 205/220)** does not prescribe a standard income statement format; either single-step (expenses by function) or multiple-step (operating/non-operating separated) is acceptable [^177^]. SEC Regulation S-X Rule 5-03 requires specific line items where applicable for public companies [^177^]. GAAP requires three years of income statements and cash flow statements vs. two years under IFRS [^180^].

- **Cash Flow Statement** under both frameworks presents operating, investing, and financing activities. GAAP (ASC 230) encourages the direct method (reporting major classes of gross operating cash receipts/payments) but the indirect method is predominantly used in practice [^42^] [^46^]. IFRS allows more discretion: interest/dividends can be classified in operating, investing, or financing depending on the entity's policy [^177^] [^179^].

### Management Reports

- **Trial Balance** is the foundational verification report: a three-column layout (account names, debit balances, credit balances) that confirms debits equal credits before financial statements are prepared [^137^] [^142^]. Three types exist: unadjusted (initial data capture), adjusted (after corrections and accruals), and post-closing (after temporary accounts are closed) [^137^].

- **Aged Receivables/Payables** reports categorize outstanding balances into time buckets (Current, 1-30 days, 31-60 days, 61-90 days, 91+ days) by customer or vendor [^81^] [^86^]. These are critical for cash flow management, collection prioritization, and vendor payment timing [^81^].

- **General Ledger Detail Report** provides a line-by-line view of every transaction within each account, including date, journal reference, description, counter account, debit/credit amounts, and running balance [^161^] [^163^] [^166^]. GL reports serve as reference documents for preparing end-of-period financial statements [^166^].

### VAT/GST Returns

- **UK VAT Return** is a nine-box structure: Box 1 (VAT due on sales), Box 2 (VAT due on acquisitions from EU), Box 3 (total output VAT = Box 1 + Box 2), Box 4 (VAT reclaimed on purchases/input VAT), Box 5 (net VAT position = Box 3 - Box 4), Box 6 (total value of sales ex-VAT), Box 7 (total value of purchases ex-VAT), Box 8 (EU sales), Box 9 (EU acquisitions) [^79^] [^85^].

- **Making Tax Digital (MTD)** requires digital record-keeping, digital links between source data and return figures, and submission through MTD-compatible software via HMRC's API [^79^]. Copy-and-paste between systems is not an acceptable digital link [^79^].

- **Xero VAT Returns** organize transactions by VAT box (Section 1) and by VAT rate (Section 2), with subheadings for each tax rate, plus sections for Adjustments and Late Claims [^149^]. UAE VAT returns follow a similar box-based approach with Box 1 (standard-rated supplies), Box 3 (reverse charge supplies), and Box 14 (net VAT payable/refundable) [^146^].

### Custom Report Builders

- **Xero** offers 50+ reports organized into categories: Financial Performance, Financial Statements, Payables and Receivables, Reconciliations, Taxes and Balances, and Transactions [^107^]. Xero's API exposes key reports (Balance Sheet, P&L, Trial Balance, Aged Receivables/Payables, Executive Summary, Bank Summary, Budget Summary, and region-specific tax reports like BAS and GST) [^109^].

- **QuickBooks Online Advanced** provides a Custom Report Builder with a "modern view" that combines high-speed performance with features like auto-refresh, zero-balance drilldowns, Excel integration, and a report creation wizard [^40^]. Users can add, remove, and drag columns to reorder.

- **Sage** provides 150 built-in financial reports with multi-dimensional visibility into income statements, balance sheets, cash flow statements, and operational comparisons [^47^].

- **Xero Management Report Pack** bundles: Executive Summary, Cash Summary, P&L, Balance Sheet, and Aged Receivables/Payables — though it lacks automated distribution and multi-entity consolidation [^110^] [^107^].

### Chart of Accounts Design

- **Standard five-category COA structure**: Assets (1000-1999), Liabilities (2000-2999), Equity (3000-3999), Revenue (4000-4999), Expenses (5000-5999) [^77^] [^76^]. This numbering convention is the most common across accounting systems.

- **Hierarchical design** enables subcategories within each range — e.g., current assets (1000-1499) vs. fixed assets (1500-1999), COGS expenses (5000-5999) vs. operating expenses (6000-8999) [^77^]. Strategic number gaps (e.g., 4010, 4020, 4030 instead of consecutive) allow future insertion without renumbering [^77^].

- **Balance sheet accounts** (Assets, Liabilities, Equity) feed the balance sheet; **income statement accounts** (Revenue, Expenses) feed the P&L [^80^]. The fundamental accounting equation (Assets = Liabilities + Equity) must always balance [^77^].

### Period Comparison Reporting

- **Xero P&L report formats** include: Current and previous 3 months, Current financial year by month, Month-to-date comparison, Year-to-date comparison, and Compare by tracking category (e.g., region) [^107^]. Balance Sheet comparisons include monthly, quarterly, and yearly formats [^110^].

- **Common comparison periods**: Current period vs. prior period (month-over-month, quarter-over-quarter), current period vs. same period prior year (year-over-year), year-to-date (YTD) cumulative, and trailing twelve months (TTM) for smoothing seasonality [^107^] [^106^].

- **Xero "More" menu options** include: Cash vs. Accrual toggle, Account Codes display, Decimals toggle, Percentage of Turnover column, Totals column, and Year-to-Date column [^106^].

### SME KPIs and Dashboard Metrics

- **Five essential KPI categories**: Profitability (gross margin, net margin, operating margin), Liquidity (current ratio, quick ratio, operating cash flow ratio), Efficiency (accounts receivable turnover, inventory turnover), Valuation (EPS, P/E), and Leverage (debt-to-equity, return on equity) [^140^] [^148^].

- **Key formulas**: Gross Profit Margin = (Revenue - COGS) / Revenue x 100; Net Profit Margin = Net Income / Revenue x 100; Current Ratio = Current Assets / Current Liabilities; Quick Ratio = Liquid Assets / Current Liabilities [^144^] [^143^] [^148^].

- **Startup-specific metrics**: Gross Burn Rate = total monthly cash outflows; Net Burn Rate = Gross Burn - Monthly Revenue; Cash Runway = Cash on Hand / Net Burn Rate [^156^] [^157^]. Burn multiples (Net Burn / Net New ARR) around 1-1.5 are considered healthy for SaaS startups [^157^].

- **A good UK SaaS board pack** includes: one-page executive summary (cash position, runway, top KPI movements), P&L with variance commentary, 13-week rolling cash forecast, SaaS metrics dashboard (MRR waterfall, NRR, gross margin, CAC payback, LTV:CAC, burn multiple), cohort retention curves, and strategic priorities/decisions required [^158^].

### Report Scheduling & Distribution

- **Automated report distribution** systems provide: automatic scheduling (daily, weekly, monthly, or custom frequency via job queues), powerful date formulas for time-based filtering, flexible output formats (PDF, ZIP bundles), and multiple delivery options (email, SharePoint, archive) [^139^].

- **Best practice reporting calendar**: Run preliminary reports on day -2, generate final reports by day 3 after month-end, distribute board packs by day 5 [^110^]. Xero supports scheduled reports with recurring emails [^114^].

- **Financial reporting automation** is a "stack problem": ERP/FP&A for data, BI tools for analytics, and delivery tools for formatted output [^145^]. SoFi's finance team cut report prep from six hours to 45 minutes per cycle after automating their workflow [^145^].

### XBRL and Digital Reporting

- **HMRC** has required iXBRL (inline XBRL) for company tax returns (CT600) since April 2011 [^159^]. The tagged accounts must conform to an approved taxonomy — FRS 102 for most UK companies or FRS 105 for micro-entities [^159^].

- **iXBRL data files** must contain: all tags as required in the List of Mandatory Items, financial statements and tax computation data either tagged or non-tagged as HTML text, and a covering page for tax computations [^75^]. Files must not exceed 20MB and must not contain JavaScript [^75^].

- **Companies House** is moving toward mandatory structured data: from April 2027, paper filing will no longer be accepted and software must produce structured (tagged) data [^159^].

- **IFRS 18** (effective 2027) and FASB's ASU 2024-03 (Disaggregation of Income Statement Expenses) will introduce new presentation and disclosure differences between IFRS and US GAAP [^182^].

### Report SKILL Architecture

- **Function calling** (also known as tool calling) is the core capability enabling LLMs to perform actions rather than just generate text [^116^]. The LLM scans available tools and generates structured JSON responses requesting function execution, with the agent scaffolding handling the actual call [^116^].

- **Key architecture components**: Agent (manages state and orchestration), Registry (handles tool management with function schemas), and LLM (handles decision-making) [^112^]. Safety mechanisms like `max_iterations` guards prevent infinite loops [^112^].

- **Critical design practices**: Clear tool descriptions written from the LLM's perspective ("Get current weather conditions for a city. Use when user asks about weather..."), iteration limits to detect loops, context window management via summarization, and proper error handling [^115^].

- **For financial reporting**, this architecture maps naturally: each report type (P&L, Balance Sheet, Cash Flow, etc.) becomes a registered SKILL with a JSON schema defining its parameters (period start/end, comparison periods, accounting basis, tracking categories, output format). The LLM selects the appropriate SKILL based on user intent and populates parameters from natural language.

---

## Complete Report Taxonomy

### 1. Core Financial Statements (Regulatory Required)

| Report | Description | Key Line Items / Structure |
|--------|-------------|---------------------------|
| **Profit & Loss / Income Statement** | Shows revenue, expenses, and profit/loss over a period | Revenue, COGS, Gross Profit, Operating Expenses, Operating Income, Finance Costs, Tax Expense, Net Income [^43^] |
| **Balance Sheet / Statement of Financial Position** | Snapshot of assets, liabilities, and equity at a point in time | Current/Non-current Assets, Current/Non-current Liabilities, Equity (issued capital, reserves, retained earnings) [^43^] [^41^] |
| **Cash Flow Statement** | Tracks cash inflows/outflows across three activity categories | Operating (direct: cash from customers, paid to suppliers, interest/tax paid; or indirect: net income + adjustments), Investing, Financing [^42^] [^46^] |
| **Statement of Changes in Equity** | Tracks movements in equity accounts over the period | Opening balance, comprehensive income, dividends, share issuances, closing balance [^43^] |

### 2. Internal Verification Reports

| Report | Description | Structure |
|--------|-------------|-----------|
| **Trial Balance** | Lists all GL account balances to verify debits = credits | Account name, Debit balance, Credit balance, YTD Debit, YTD Credit [^137^] [^142^] |
| **Unadjusted Trial Balance** | Initial capture before corrections | Raw closing balances from GL [^137^] |
| **Adjusted Trial Balance** | After accruals, depreciation, corrections | Includes all period-end adjustments [^137^] |
| **Post-Closing Trial Balance** | After closing temporary accounts | Only permanent accounts (assets, liabilities, equity) [^137^] |

### 3. Management / Operational Reports

| Report | Description | Key Data |
|--------|-------------|----------|
| **Aged Receivables Summary** | Outstanding customer balances by aging bucket | Current, 1-30, 31-60, 61-90, 91+ days; total per customer [^81^] |
| **Aged Receivables Detail** | Invoice-level breakdown of outstanding amounts | Invoice number, due date, amount, aging per invoice [^86^] |
| **Aged Payables Summary** | Outstanding supplier balances by aging bucket | Current, 1-30, 31-60, 61-90, 91+ days; total per vendor [^81^] |
| **Aged Payables Detail** | Invoice-level breakdown of amounts owed | Bill number, due date, amount, aging per bill [^86^] |
| **General Ledger Detail** | Every transaction within each account | Date, journal ref, description, counter account, debit, credit, running balance [^163^] [^166^] |
| **General Ledger Summary** | High-level account balances for a period | Opening balance, total debits, total credits, closing balance per account [^166^] |
| **Executive Summary** | One-page overview of key financial metrics | Cash position, runway, top KPI movements, decisions needed [^158^] |
| **Cash Summary** | Movement of cash in and out for a period | Operating, investing, financing cash movements [^107^] |

### 4. Tax / Compliance Reports

| Report | Description | Structure |
|--------|-------------|-----------|
| **VAT Return (UK)** | Nine-box VAT submission | Box 1-5: Output/input/net VAT; Box 6-7: Sales/purchase values ex-VAT; Box 8-9: EU transactions [^79^] [^85^] |
| **BAS Report (Australia)** | Business Activity Statement | W1-W5 (PAYG), GST amounts, deferred instalments [^109^] |
| **GST Report (New Zealand)** | Goods and Services Tax return | GST collected, GST paid, net position [^109^] |
| **1099 Report (US)** | Vendor payment reporting for tax purposes | Payments by vendor, threshold tracking [^109^] |
| **Sales Tax Report** | Multi-jurisdiction sales tax collection | Tax collected by jurisdiction, taxable/exempt sales [^107^] |

### 5. Variance and Comparison Reports

| Report | Description | Period Options |
|--------|-------------|----------------|
| **P&L with Comparison** | Profit & Loss vs. prior periods | Current + previous 3 months, current FY by month, MTD comparison, YTD comparison [^107^] |
| **Balance Sheet Comparison** | Financial position across periods | Monthly comparison, quarterly comparison, yearly comparison [^110^] |
| **Budget Variance** | Actuals vs. budget with variance | Budget vs actual, variance amount, variance percentage [^107^] |
| **Account Variance Report** | Period-over-period account changes | Comparison across periods to highlight unexpected changes [^166^] |
| **Tracking Summary** | Activity by tracking category (department, region, etc.) | Opening/closing balances, net activity per tracking option [^107^] |

### 6. KPI and Dashboard Reports

| KPI Category | Key Metrics | Formulas |
|-------------|-------------|----------|
| **Profitability** | Gross Margin, Operating Margin, Net Margin | (Revenue-COGS)/Revenue; EBIT/Revenue; Net Income/Revenue [^140^] [^144^] |
| **Liquidity** | Current Ratio, Quick Ratio, Cash Ratio | Current Assets/Current Liabilities; Liquid Assets/Current Liabilities [^143^] [^140^] |
| **Efficiency** | DSO, Inventory Turnover, AR Turnover | Days sales outstanding; COGS/Avg Inventory [^147^] |
| **Startup Metrics** | Burn Rate, Runway, Burn Multiple | Gross/Net monthly burn; Cash/Burn; Net Burn/Net New ARR [^156^] [^157^] |
| **SaaS Metrics** | MRR, ARR, NRR, GRR, LTV:CAC, CAC Payback | Monthly/Annual Recurring Revenue; Net Revenue Retention; Lifetime Value/CAC [^158^] |

### 7. Audit and Compliance Reports

| Report | Purpose |
|--------|---------|
| **General Journal Report** | All manual journal entries for audit review [^166^] |
| **History and Notes Report** | All changes made to transactions and which user made them [^107^] |
| **Bank Reconciliation Report** | Comparison of Xero and actual bank balances [^106^] |
| **Account Summary** | Monthly account summaries for reconciling [^106^] |
| **Duplicate Statement Lines** | Identify and resolve duplicate transactions [^107^] |
| **Working Trial Balance** | TB with adjustments and notes supporting tax prep/audit [^166^] |

---

## Trends & Signals

- **IFRS 18 (effective January 2027)** represents the most significant change to financial statement presentation in decades, introducing mandatory operating/investing/financing categories, required subtotals, and new MPM disclosure requirements [^178^] [^181^]. This will require all reporting systems to restructure their P&L outputs.

- **FASB's ASU 2024-03** (Disaggregation of Income Statement Expenses) aligns timing with IFRS 18 (effective fiscal years beginning after December 15, 2026), requiring tabular footnote disclosure of specific expense categories [^182^]. The convergence trend continues but with persistent differences.

- **Companies House digital filing mandate (April 2027)** will require all UK company accounts to use structured (tagged) data formats, eliminating paper filing and accelerating XBRL/iXBRL adoption [^159^].

- **Xero's report ecosystem** demonstrates the industry standard: 50+ native reports, API-exposed report endpoints with structured row/cell output, custom report builder with drag-and-drop, tracking categories for dimensional analysis, and scheduled report distribution [^107^] [^109^] [^106^].

- **Automated reporting stacks** are converging on a three-layer architecture: ERP/FP&A for data, BI for analytics/visualization, and delivery tools for formatted output distribution [^145^]. The delivery layer remains the biggest automation gap.

- **Burn rate and runway** have become standard SME/startup metrics alongside traditional accounting ratios, reflecting the shift toward real-time financial health monitoring rather than historical reporting [^156^] [^157^].

---

## Controversies & Conflicting Claims

### GAAP vs. IFRS: Rules-Based vs. Principles-Based

- **IFRS** is principles-based, allowing greater professional judgment in presentation format and line item aggregation/disaggregation [^183^]. **GAAP** is more rules-based with specific SEC filing requirements (Regulation S-X) prescribing exact formats for public companies [^177^] [^180^].

- **Balance sheet ordering**: IFRS traditionally reports non-current assets before current assets (increasing liquidity), while US GAAP lists assets in decreasing order of liquidity (current assets first) [^179^]. However, IFRS permits either approach.

- **Interest/dividend classification in cash flows**: GAAP mandates interest expense, interest income, and dividend income in operating activities and dividends paid in financing [^179^]. IFRS provides discretion — these can be classified in operating, investing, or financing depending on policy [^177^].

### Direct vs. Indirect Cash Flow Method

- ASC 230-10-45-25 "encourages" the direct method (listing gross cash receipts/payments) but the indirect method is "predominantly used" in practice because it's easier to prepare from existing financial statements [^42^] [^46^]. IFRS also prefers the direct method but accepts the indirect [^45^]. This creates a tension between transparency (direct method shows actual cash movements) and practicality (indirect method is simpler to produce).

### Extraordinary Items

- Both IFRS [^43^] and US GAAP [^177^] prohibit presenting items as "extraordinary" on the face of financial statements. However, unusual or infrequent items must still be disclosed separately if material, creating interpretive judgment about what qualifies.

---

## Recommended Deep-Dive Areas

### 1. IFRS 18 Implementation Impact (Critical — effective 2027)

**Why it warrants depth:** IFRS 18 fundamentally restructures the income statement with mandatory categories (operating, investing, financing, income tax, discontinued operations), required subtotals, and new MPM disclosures [^181^]. Every report generation SKILL that produces a P&L will need redesign. The standard also amends IAS 7 (cash flows), IAS 8, and IAS 33 with consequential changes.

### 2. XBRL/iXBRL Taxonomy Mapping

**Why it warrants depth:** HMRC already mandates iXBRL for UK corporation tax returns [^159^], and Companies House will require structured data from April 2027 [^159^]. The taxonomy defines which tags map to which financial statement line items. A report generation system needs a taxonomy-aware tagging layer that can convert any report output into iXBRL-compliant format.

### 3. Multi-Entity Consolidation Reporting

**Why it warrants depth:** Xero's Management Report Pack explicitly lacks multi-entity consolidation [^110^], which is the #1 gap cited by CFOs. Consolidation requires intercompany elimination, currency translation, and minority interest calculation — complex logic that must be built into report SKILLs.

### 4. Real-Time vs. Period-End Reporting

**Why it warrants depth:** Xero and modern cloud accounting provide real-time report data [^110^], but traditional accounting closes periods with lock dates to prevent alteration [^114^]. The system must support both modes: real-time "draft" reports and locked "final" reports with audit trail.

### 5. GAAP/IFRS Dual Reporting

**Why it warrants depth:** Companies with international operations or investor bases may need to produce reports under both frameworks. Key differences in presentation (balance sheet ordering, cash flow classification, extraordinary items, number of comparative periods) require the report generation system to parameterize the reporting framework [^177^] [^179^].

### 6. Report Distribution and Governance

**Why it warrants depth:** The "last mile" of report delivery (formatting for board presentation, email distribution, version control, approval workflows) remains the most manual part of the process [^145^]. Automated distribution with role-based access, delivery audit trails, and archival is a major automation opportunity.

---

## Report SKILL Architecture Recommendations

### Design Principles

1. **Each report is a registered SKILL** with a JSON schema defining its parameters, not ad-hoc LLM generation
2. **SKILLs are composable** — base reports (Trial Balance → P&L/Balance Sheet) feed derived reports (KPIs, comparisons)
3. **SKILLs are testable** — deterministic output given fixed inputs, with golden reference files for regression testing
4. **SKILLs are framework-aware** — parameterized for GAAP vs. IFRS, cash vs. accrual, direct vs. indirect
5. **SKILLs are period-aware** — support any date range, comparison periods, YTD, TTM, fiscal year

### Core SKILL Taxonomy

```
REPORT_CORE_STATEMENTS/
  skill_generate_profit_loss/          # P&L / Income Statement
    params: period_start, period_end, comparison_periods[], accounting_basis, framework, tracking_category, output_format
    line_items: Revenue, COGS, Gross_Profit, OpEx, EBITDA, Depreciation, EBIT, Interest, Tax, Net_Income
    
  skill_generate_balance_sheet/        # Statement of Financial Position
    params: as_of_date, comparison_dates[], framework, detail_level, output_format
    line_items: Assets (current/non-current), Liabilities (current/non-current), Equity
    
  skill_generate_cash_flow/            # Cash Flow Statement
    params: period_start, period_end, method (direct|indirect), framework, output_format
    sections: Operating, Investing, Financing; reconciliation of net income to operating CF
    
  skill_generate_trial_balance/        # Trial Balance verification
    params: as_of_date, type (unadjusted|adjusted|post_closing), output_format
    columns: Account, Account_Code, Debit, Credit, YTD_Debit, YTD_Credit

REPORT_MANAGEMENT/
  skill_generate_aged_receivables/     # AR Aging
    params: as_of_date, aging_buckets[], customer_filter, detail_level (summary|detail)
    columns: Customer, Current, 1-30, 31-60, 61-90, 91+, Total
    
  skill_generate_aged_payables/        # AP Aging
    params: as_of_date, aging_buckets[], vendor_filter, detail_level
    columns: Vendor, Current, 1-30, 31-60, 61-90, 91+, Total
    
  skill_generate_gl_detail/            # General Ledger Detail
    params: period_start, period_end, account_filter, transaction_types[]
    columns: Date, Journal_Ref, Description, Counter_Account, Debit, Credit, Balance
    
  skill_generate_executive_summary/    # Management Dashboard
    params: period_end, comparison_periods[], kpi_list[]
    sections: Cash_Position, Profitability, Liquidity, AR_AP_Summary, Key_Variances

REPORT_TAX/
  skill_generate_vat_return/           # VAT/GST Return
    params: period_start, period_end, jurisdiction, vat_scheme
    boxes: Box1-Box9 (UK); equivalent for AU, NZ, UAE, etc.
    
  skill_generate_tax_computation/      # Corporate Tax Computation
    params: period_start, period_end, jurisdiction
    sections: Accounting_Profit, Adjustments, Taxable_Profit, Tax_Charge

REPORT_KPI/
  skill_calculate_profitability_kpis/  # Margin Analysis
    params: period_start, period_end, benchmarks[]
    kpis: Gross_Margin, Operating_Margin, Net_Margin, EBITDA_Margin
    
  skill_calculate_liquidity_kpis/      # Liquidity Analysis
    params: as_of_date
    kpis: Current_Ratio, Quick_Ratio, Cash_Ratio, Working_Capital
    
  skill_calculate_startup_metrics/     # Burn/Runway
    params: period_end, cash_balance
    kpis: Gross_Burn, Net_Burn, Runway_Months, Burn_Multiple

REPORT_COMPARISON/
  skill_generate_period_comparison/    # Multi-Period Report
    params: base_period, comparison_periods[], report_type, variance_analysis (boolean)
    columns: Period1, Period2, ..., Variance_Amt, Variance_Pct
    
  skill_generate_budget_variance/      # Budget vs. Actual
    params: period_start, period_end, budget_scenario
    columns: Budget, Actual, Variance, Variance_Pct, Commentary

REPORT_XBRL/
  skill_convert_to_ixbrl/              # iXBRL Tagging
    params: report_data, taxonomy_version, jurisdiction
    output: iXBRL-compliant HTML file with tagged facts
```

### Parameter Design Pattern

Every report SKILL should accept these common parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `period_start` / `period_end` | ISO date | Report period date range |
| `accounting_basis` | enum: [accrual, cash] | Whether to use accrual or cash basis |
| `framework` | enum: [GAAP, IFRS] | Accounting framework for presentation rules |
| `comparison_periods[]` | array of period objects | Prior periods for comparison columns |
| `output_format` | enum: [json, html, pdf, csv] | Output serialization format |
| `tracking_category` | string | Optional dimensional filter (department, region, etc.) |
| `consolidation_entity` | string | Entity/group for consolidated reports |

### Implementation Architecture

1. **Report Engine Layer**: Executes the actual data queries against the general ledger, applies accounting rules (framework-specific line item classification, sign conventions, aggregation rules), and produces a structured data model.

2. **Template Layer**: Separated from data logic. Uses a templating engine (Liquid, Handlebars, or Jinja2) to render the structured data model into HTML/PDF. Templates are framework-specific (IFRS vs. GAAP presentation rules) and user-customizable.

3. **XBRL/iXBRL Layer**: Post-processing step that maps the structured data model to taxonomy tags and wraps in iXBRL HTML format for regulatory submission.

4. **Distribution Layer**: Handles scheduling, email delivery, format conversion, and archival with full audit trail.

5. **LLM SKILL Registry**: Each report SKILL is registered with a function schema (name, description, parameters). The LLM selects the appropriate SKILL based on user intent and extracts parameters from natural language, with the Report Engine executing the actual data retrieval and computation.

---

## Sources

[^41^] IFRS Foundation, "AP21A: Principles for presentation and required line items in primary financial statements," IASB Meeting February 2022. https://www.ifrs.org/content/dam/ifrs/meetings/2022/february/iasb/ap21a-principles-for-presentation-and-required-line-items-in-primary-financial-statements.pdf

[^42^] KPMG, "Handbook: Statement of cash flows," 2024. https://kpmg.com/kpmg-us/content/dam/kpmg/frv/pdf/2024/handbook-statement-cash-flows.pdf

[^43^] AASB 101, "Presentation of Financial Statements," paragraph 54 (IFRS-aligned). https://www.aasb.gov.au/admin/file/content105/c9/AASB101_07-15.pdf

[^44^] IFRS Foundation, "Primary Financial Statements—Illustrative Examples," June 2023. https://www.ifrs.org/content/dam/ifrs/meetings/2023/june/cmac-gpf/ap2-cmac-gpf-pfs.pdf

[^45^] Investopedia, "Cash Flow Statements: How to Prepare and Read One," 2025. https://www.investopedia.com/investing/what-is-a-cash-flow-statement/

[^46^] PwC, "Format of the statement of cash flows," Financial Statement Presentation Guide, 2024. https://viewpoint.pwc.com/dt/us/en/pwc/accounting_guides/financial_statement_/financial_statement___18_US/chapter_6_statement__US/64_format_of_the_sta_US.html

[^47^] Brysa, "Accounting Seed vs. Quickbooks vs. Sage vs. Xero," 2025. https://brysa.co.uk/insights/accounting-seed-vs-quickbooks-vs-sage-vs-xero

[^48^] PwC, "Format of the income statement," Financial Statement Presentation Guide, 2024. https://viewpoint.pwc.com/dt/us/en/pwc/accounting_guides/financial_statement_/financial_statement___18_US/chapter_3_income_sta_US/33_format_of_the_inc_US.html

[^75^] IRD Hong Kong, "iXBRL Filing," 2026. https://www.ird.gov.hk/e_ixbrl/

[^76^] Enkel, "Chart of Accounts Guide For Canadian Businesses," 2026. https://www.enkel.ca/blog/bookkeeping/chart-of-accounts-101-a-guide-for-canadian-business-owners/

[^77^] Custom CPA, "Chart of Accounts Setup: Foundation of Good Bookkeeping," 2026. https://customcpa.ca/chart-of-accounts-setup/

[^78^] AcoBloom, "How to File A VAT Return in the UK – Step-by-Step Guide," 2026. https://www.acobloom.com/blog/how-to-file-your-quarterly-hmrc-vat-return/

[^79^] BRIGHTSG, "How do I submit a Making Tax Digital VAT return to HMRC?," 2026. https://brightsg.com/blog/how-to-submit-a-making-tax-digital-vat-return-to-hmrc/

[^80^] NetSuite, "Chart of Accounts: Definition, Best Practices, and Examples," 2025. https://www.netsuite.com/portal/resource/articles/accounting/chart-of-accounts.shtml

[^81^] Bill.com, "What is an Aging Report?," 2026. https://www.bill.com/learning/aging-report

[^82^] Vena Solutions, "Chart of Accounts Explained: Types, Structure & Importance." https://www.venasolutions.com/finance-glossary/chart-of-accounts

[^83^] Investopedia, "Chart of Accounts (COA): Definition, How It Works, and Example," 2025. https://www.investopedia.com/terms/c/chart-accounts.asp

[^84^] Germanna College, "Chart of Accounts." https://germanna.edu/sites/default/files/2022-03/Chart%20of%20Accounts.pdf

[^85^] Cowgills, "How to fill out a VAT Return: Step by step guide," 2025. https://www.cowgills.co.uk/news/how-to-fill-out-a-vat-return-step-by-step-guide/

[^86^] Tipalti, "What is an Accounts Payable Aging Report?," 2026. https://tipalti.com/resources/learn/accounts-payable-aging-report/

[^106^] Stryde, "Learn How to Understand Your Financial Reports in Xero." https://www.stryde.co.uk/post/understanding-financial-reports-in-xero

[^107^] Coupler.io, "Ultimate Guide to Xero Reporting," 2026. https://blog.coupler.io/xero-reports/

[^108^] HLCA, "Top 5 Essential Xero Reports," 2026. https://hlca.co.uk/resources/top-5-essential-xero-reports-every-business-should-be-checking-regularly/

[^109^] Xero Developer, "Accounting API Reports," 2018. https://developer.xero.com/documentation/api/accounting/reports

[^110^] DataSights, "Xero Reporting Guide 2025," 2025. https://datasights.co/xero-reporting/

[^112^] Michael Brenndoerfer, "Function Calling: Structured Tool Use for Large Language Models," 2026. https://mbrenndoerfer.com/writing/function-calling-llm-structured-tools

[^114^] FHP Accounting, "Month-End in Xero: A Complete Guide," 2025. https://fhpaccounting.co.uk/month-end-in-xero-a-complete-guide-to-closing-procedures-essential-reports-and-performance-tracking/

[^115^] Pockit Tools, "Building AI Agents from Scratch: Function Calling, Tool Use, and Agentic Patterns," 2025. https://dev.to/pockit_tools/building-ai-agents-from-scratch-a-deep-dive-into-function-calling-tool-use-and-agentic-patterns-382g

[^116^] Symflower, "Function calling in LLM agents," 2025. https://symflower.com/en/company/blog/2025/function-calling-llm-agents/

[^137^] Xero, "What is a trial balance?," 2026. https://www.xero.com/us/guides/trial-balance/

[^138^] Madras Accountancy, "Essential KPIs for Small Business Financial Performance." https://madrasaccountancy.com/blog-posts/essential-kpis-for-small-business-financial-performance

[^139^] Hougaard, "User guide – Automated report distribution," Advanced Financial Reporting for Business Central. https://www.hougaard.com/advanced-financial-reporting-user-guide-automated-report-distribution/

[^140^] NetSuite UK, "30 Financial Metrics and KPIs to Measure Success in 2026," 2026. https://www.netsuite.co.uk/portal/uk/resource/articles/accounting/financial-kpis-metrics.shtml

[^141^] HansaManuals, "Example VAT Report Definitions - Standard ERP." https://www.hansamanuals.com/main/langcode___RU/version___82/manuals/theconf___546/mailnumber___59750/hwconvindex.htm

[^142^] Sage, "What Is a Trial Balance? Definition and Types," 2025. https://www.sage.com/en-us/blog/what-is-a-trial-balance/

[^143^] PBD Business, "5 Essential Financial KPIs for SMEs to Monitor and Improve Performance," 2025. https://podbusiness.com.au/5-essential-financial-kpis-for-smes-to-monitor-and-improve-performance/

[^144^] BrizoSystem, "8 Financial Ratios Every SME Should Track." https://brizosystem.com/blog/key-financial-ratios-every-sme-should-track/

[^145^] Rollstack, "Financial Reporting Automation: How Finance Teams Automate Reporting End to End," 2026. https://www.rollstack.com/articles/financial-reporting-automation

[^146^] Alaan, "How to File a VAT Return in Xero: Step-by-Step Guide," 2025. https://www.alaan.com/blog/submit-vat-return-xero

[^147^] BBS Accounting, "Essential Financial KPIs Every Small Business Should Track," 2026. https://bbsaccounting.ca/essential-financial-kpis-every-small-business-should-track/

[^148^] Citrin Cooperman, "30 Financial KPIs Your Business Should Measure," 2024. https://www.citrincooperman.com/In-Focus-Resource-Center/30-Financial-KPIs-Your-Business-Should-Measure

[^149^] The Hospitality Accountants, "Understanding your VAT Return in Xero," 2025. https://thehospitalityaccountants.com/tax/understanding-xero-vat-return/

[^156^] Slash, "Burn Rate vs Runway: Startup Finance Metrics Explained," 2026. https://www.slash.com/blog/burn-rate-vs-runway

[^157^] Haven, "Startup Burn Rate: Metrics, Benchmarks & Tips for CEOs," 2026. https://www.usehaven.com/blog-posts/startup-burn-rate-metrics-benchmarks-tips-for-ceos

[^158^] ScaleWithCFO, "Board Pack vs Financial Reporting Package: A UK SaaS Guide," 2026. https://www.scalewithcfo.com/post/board-pack-vs-financial-reporting-package-uk-saas

[^159^] TinyTax, "What Is XBRL? The Plain-English Explanation," 2026. https://tinytax.co.uk/guides/what-is-xbrl

[^161^] DualEntry.com, "What Is a General Ledger Report? A Practical Guide," 2026. https://www.dualentry.com/blog/what-is-a-general-ledger-report

[^163^] TaxDome, "Accounting general ledger: what it is, how to use it," 2026. https://taxdome.com/blog/accounting-general-ledger

[^166^] Sage, "The general ledger report: What it is and how to read it," 2025. https://www.sage.com/en-us/blog/how-to-read-a-general-ledger-report/

[^167^] TechStartupIdeas, "Financial Report Builder: Complete Business Analysis & Market Opportunity." https://techstartupideas.app/ideas/financial-report-builder

[^177^] Grant Thornton, "Comparison between U.S. GAAP and IFRS Standards," September 2016. https://www.grantthornton.ie/globalassets/1.-member-firms/ireland/insights/publications/grant-thornton---us-gaap---ifrs-comparison-guide-september-2016.pdf

[^178^] KPMG, "IFRS compared to US GAAP," 2026. https://kpmg.com/xx/en/what-we-do/services/audit/corporate-reporting-institute/ifrs/toolkit/us-gaap-comparison.html

[^179^] Wall Street Prep, "US GAAP vs. IFRS | Differences + Cheat Sheet," 2024. https://www.wallstreetprep.com/knowledge/us-gaap-vs-ifrs-differences-similarities-examples-pdf-cheat-sheet/

[^180^] PwC, "Financial statement presentation and disclosure requirements," 2025. https://viewpoint.pwc.com/dt/us/en/pwc/accounting_guides/financial_statement_/financial_statement___18_US/chapter_1_general_pr_US/11_financial_presentat_US.html

[^181^] EY, "A closer look at IFRS 18," July 2025. https://www.ey.com/content/dam/ey-unified-site/ey-com/en-gl/technical/ifrs-technical-resources/documents/ey-gl-applying-ifrs-a-closer-look-at-ifrs-18-07-2025.pdf

[^182^] Deloitte, "IFRS compared to US GAAP — Presentation of Financial Statements," 2024. https://dart.deloitte.com/USDART/home/publications/deloitte/additional-deloitte-guidance/roadmap-ifrs-us-gaap-comparison/chapter-4-presentation/4-1-presentation-financial-statements

[^183^] Pearson, "GAAP vs. IFRS: Analysis and Income Statement Presentation," 2022. https://www.pearson.com/channels/financial-accounting/learn/brian/ch-15-gaap-vs-ifrs/gaap-vs-ifrs-analysis-and-income-statement-presentation
