# Dimension 08: Financial Reporting SKILLs Architecture

## Executive Summary

This document designs a complete, production-ready financial reporting system using repeatable, testable SKILLs. The architecture encompasses 30+ report types organized across 7 categories, a parameterized report engine that can produce GAAP or IFRS output, and full support for the IFRS 18 standard effective January 2027 [^301^]. The system handles output in JSON (API), HTML (web), PDF (document), and CSV (spreadsheet) formats, with automated scheduling, email distribution, and XBRL/iXBRL submission-ready output [^260^] [^315^].

**Key Design Decisions:**
- All report SKILLs are registered with JSON schemas for deterministic, parameterized execution
- IFRS 18's five-category P&L structure (Operating, Investing, Financing, Income Taxes, Discontinued Operations) is supported natively [^301^] [^325^]
- XBRL/iXBRL taxonomy mapping is built into the output layer for compliance with UK Companies House digital filing from April 2028 [^313^] [^319^]
- The same SKILL produces GAAP or IFRS output via framework parameterization
- Management-defined performance measures (MPMs) are supported per IFRS 18 requirements [^308^]

---

## Table of Contents

1. [SKILL Taxonomy: 30+ Report Types](#1-skill-taxonomy)
2. [Report Engine Architecture](#2-report-engine-architecture)
3. [Core Statement SKILLs](#3-core-statement-skills)
4. [Management Report SKILLs](#4-management-report-skills)
5. [Tax Report SKILLs](#5-tax-report-skills)
6. [KPI SKILLs](#6-kpi-skills)
7. [Variance SKILLs](#7-variance-skills)
8. [Framework Parameterization](#8-framework-parameterization)
9. [Output Format Layer](#9-output-format-layer)
10. [Report Scheduling & Distribution](#10-report-scheduling)
11. [XBRL/iXBRL Layer](#11-xbrl-ixbrl-layer)
12. [Implementation Roadmap](#12-implementation-roadmap)

---

## 1. SKILL Taxonomy: 30+ Report Types Across 7 Categories

### 1.1 Report Type Registry

Every report SKILL is registered with a deterministic JSON schema that defines its inputs, parameters, data model, and output format. The registry enables programmatic discovery, validation, and execution of any report.

### 1.2 Complete Report Type Catalog

| # | Category | Report SKILL ID | Report Name | Framework |
|---|----------|----------------|-------------|-----------|
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

### 1.3 Base SKILL Schema Template

Every report SKILL conforms to this base schema:

```json
{
  "$schema": "https://schemas.accountingsystem.io/report-skill/v1",
  "skill_id": "string (unique identifier)",
  "skill_version": "string (semver)",
  "category": "enum: core | verify | mgmt | tax | var | kpi | audit | compliance",
  "report_name": "string (human-readable name)",
  "description": "string (detailed description)",
  "framework": {
    "supported": ["gaap_us", "gaap_uk", "ifrs", "tax_uk", "tax_au", "tax_us"],
    "default": "ifrs",
    "parameterized": true
  },
  "parameters": {
    "$ref": "#/definitions/parameter_schema"
  },
  "data_model": {
    "query_interface": "sql | graphql | rest",
    "required_views": ["string array"],
    "dependencies": ["skill_id array"]
  },
  "output": {
    "supported_formats": ["json", "html", "pdf", "csv", "xbrl", "ixbrl"],
    "default_format": "json",
    "schema_validation": true
  },
  "execution": {
    "deterministic": true,
    "cacheable": true,
    "cache_ttl_seconds": 300,
    "max_execution_ms": 30000
  }
}
```

---

## 2. Report Engine Architecture

### 2.1 Pipeline Overview

The report engine follows a 5-stage pipeline that transforms raw accounting data into formatted, validated report output:

```
Stage 1: Parameter Ingestion & Validation
    |
    v
Stage 2: Query Layer Execution (Data Acquisition)
    |
    v
Stage 3: Data Model Transformation (Business Logic)
    |
    v
Stage 4: Rule Application (Framework / GAAP / IFRS / Tax Rules)
    |
    v
Stage 5: Output Formatting (JSON / HTML / PDF / CSV / XBRL)
```

### 2.2 Stage 1: Parameter Ingestion & Validation

All report SKILLs accept a standardized parameter envelope:

```json
{
  "report_request": {
    "skill_id": "core.pl",
    "version": "1.0.0",
    "request_id": "uuid",
    "requested_at": "2025-01-15T10:00:00Z"
  },
  "parameters": {
    "entity_id": "string (company/entity identifier)",
    "period": {
      "start_date": "YYYY-MM-DD",
      "end_date": "YYYY-MM-DD",
      "comparison_period": {
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD"
      }
    },
    "framework": "gaap_us | gaap_uk | ifrs",
    "currency": "ISO 4217 code (default: entity base currency)",
    "reporting_dimensions": {
      "tracking_categories": ["string array"],
      "departments": ["string array"],
      "projects": ["string array"],
      "regions": ["string array"]
    },
    "filters": {
      "accounts_include": ["pattern array"],
      "accounts_exclude": ["pattern array"],
      "minimum_amount": "decimal",
      "tags": ["string array"]
    },
    "output": {
      "format": "json | html | pdf | csv | xbrl | ixbrl",
      "locale": "en-US",
      "number_format": "decimal_separator, thousands_separator",
      "date_format": "YYYY-MM-DD",
      "page_size": "A4 | Letter",
      "orientation": "portrait | landscape",
      "include_charts": true,
      "include_comparatives": true,
      "rounding": "none | cents | thousands | millions"
    },
    "execution": {
      "priority": "high | normal | low",
      "async": false,
      "callback_url": "string (optional webhook)"
    }
  }
}
```

### 2.3 Stage 2: Query Layer Execution

The query layer translates validated parameters into database queries against the accounting data model:

| Data Source | Query Interface | Purpose |
|-------------|----------------|---------|
| General Ledger | SQL | Transaction-level data |
| Chart of Accounts | SQL | Account metadata, hierarchies |
| Journal Entries | SQL | Double-entry postings |
| Contacts | SQL | Customer/Supplier master data |
| Tax Transactions | SQL | VAT/GST/Sales tax movements |
| Budget/Forecast | SQL | Planned vs actual comparison |
| Tracking Categories | SQL | Dimensional analysis |
| Audit Log | SQL | Full audit trail |
| Exchange Rates | REST | Multi-currency conversion |
| XBRL Taxonomy | GraphQL | Tagging and validation |

### 2.4 Stage 3: Data Model Transformation

The data model layer applies business logic to raw query results:

- **Aggregation**: Roll up transactions to account, category, or dimension level
- **Period logic**: Handle fiscal year variations, 4-4-5 calendars, multi-period rollups
- **Currency conversion**: Apply period-end, average, or historical exchange rates
- **Intercompany elimination**: Remove intra-group transactions for consolidated reports
- **Reclassification**: Map internal account codes to standard reporting categories
- **Dimensional slicing**: Apply tracking category, department, project filters

### 2.5 Stage 4: Rule Application

The rule engine applies framework-specific accounting rules:

| Rule Type | Description | Example |
|-----------|-------------|---------|
| Classification Rules | Map accounts to categories per framework | IFRS 18: Operating/Investing/Financing [^325^] |
| Aggregation Rules | How line items are grouped and subtotaled | IFRS 18 mandatory subtotals [^301^] |
| Disclosure Rules | Required notes and supplementary information | MPM disclosures under IFRS 18 [^308^] |
| Tax Rules | Jurisdiction-specific tax calculations | UK VAT 9-box scheme [^254^] |
| Validation Rules | Cross-checks and balance verifications | Trial balance debit=credit [^299^] |
| Sign Conventions | How debits/credits are displayed | GAAP vs IFRS sign conventions |

### 2.6 Stage 5: Output Formatting

The output layer serializes the processed data model into the requested format:

| Format | Use Case | Implementation |
|--------|----------|----------------|
| JSON | API responses, downstream processing | Structured with embedded metadata |
| HTML | Web viewing, dashboards | Responsive templates with CSS |
| PDF | Document distribution, filing | Headless browser + print CSS |
| CSV | Spreadsheet import, analysis | Flattened with header metadata |
| XBRL | Machine-readable regulatory filing | Taxonomy-mapped elements |
| iXBRL | Human + machine readable filing | HTML with embedded XBRL tags [^260^] |

---

## 3. Core Statement SKILLs

### 3.1 P&L Statement SKILL (`core.pl`)

#### IFRS 18 Ready Implementation

IFRS 18 (effective January 2027) introduces the most significant change to income statement presentation in over two decades [^301^]. The P&L SKILL natively supports IFRS 18's five-category structure:

**IFRS 18 Five Categories [^325^]:**

| Category | Description | Typical Items |
|----------|-------------|---------------|
| **Operating** | Core business activities (default/catch-all) | Revenue, COGS, SGA, R&D, depreciation of operating assets |
| **Investing** | Returns from investments | Interest income, dividends, gains on disposal of investments, share of JV profits |
| **Financing** | Cost of raising finance | Interest expense on debt, FX differences on financing liabilities |
| **Income Taxes** | Tax per IAS 12 | Current tax, deferred tax |
| **Discontinued Operations** | Per IFRS 5 | Results of disposed components |

**IFRS 18 Required Subtotals [^301^] [^325^]:**

```
Revenue
Operating Expenses (by nature or function)
  |
  v
Operating Profit or Loss  [MANDATORY SUBTOTAL]
  + Share of associates/JVs (Investing category)
  + Interest income (Investing category)
  + Gains on investments (Investing category)
  |
  v
Profit or Loss before Financing and Income Taxes  [MANDATORY SUBTOTAL]
  - Interest expense (Financing category)
  - Other financing costs (Financing category)
  |
  v
Profit or Loss before Tax
  - Income Tax Expense
  |
  v
Profit or Loss (Net Income)  [MANDATORY TOTAL]
```

#### P&L SKILL Parameter Schema

```json
{
  "skill_id": "core.pl",
  "parameters": {
    "period": { "start_date": "2027-01-01", "end_date": "2027-12-31" },
    "framework": "ifrs",
    "ifrs18_options": {
      "compliance_level": "full | transitional",
      "expense_presentation": "by_nature | by_function | mixed",
      "include_mpm_note": true,
      "mpm_measures": ["adjusted_ebitda", "underlying_profit"]
    },
    "operating_expense_detail": {
      "depreciation": true,
      "amortization": true,
      "employee_benefits": true,
      "impairment_losses": true
    },
    "output": { "format": "json", "include_comparatives": true }
  }
}
```

#### IFRS 18 MPM Support

Management-defined performance measures (MPMs) are subtotals of income and expenses used in public communications outside the financial statements [^301^]. Under IFRS 18, MPM disclosures are mandatory and fall within audit scope [^308^]. The P&L SKILL supports MPM reconciliation:

```json
{
  "mpm_disclosure": {
    "measure_name": "Adjusted EBITDA",
    "description": "Management uses Adjusted EBITDA to assess core operating performance",
    "reconciliation": {
      "operating_profit_ifrs": 1500000,
      "add_back": {
        "depreciation": 200000,
        "amortization": 100000,
        "impairment_losses": 50000
      },
      "adjusted_ebitda": 1850000,
      "tax_effect_of_reconciling_items": -52500,
      "nci_effect": 0
    }
  }
}
```

### 3.2 Balance Sheet SKILL (`core.bs`)

#### Balance Sheet Structure

The balance sheet SKILL produces a statement of financial position structured per the accounting equation: Assets = Liabilities + Equity [^326^]:

```
ASSETS
  Current Assets:
    Cash and Cash Equivalents
    Accounts Receivable (net of allowance)
    Inventory
    Prepaid Expenses
    Short-term Investments
    Other Current Assets
  Non-Current Assets:
    Property, Plant & Equipment (net of depreciation)
    Intangible Assets (net of amortization)
    Goodwill [IFRS 18: presented as single line item] [^303^]
    Long-term Investments
    Deferred Tax Assets
    Other Non-Current Assets
  TOTAL ASSETS

LIABILITIES
  Current Liabilities:
    Accounts Payable
    Short-term Debt
    Current Portion of Long-term Debt
    Accrued Expenses
    Deferred Revenue
    Tax Payable
    Other Current Liabilities
  Non-Current Liabilities:
    Long-term Debt
    Bonds Payable
    Deferred Tax Liabilities
    Pension Obligations
    Lease Liabilities
    Other Non-Current Liabilities
  TOTAL LIABILITIES

EQUITY
  Share Capital
  Share Premium
  Treasury Shares
  Retained Earnings
  Other Reserves
  Non-controlling Interests
  TOTAL EQUITY

TOTAL LIABILITIES AND EQUITY
```

#### IFRS 18 Balance Sheet Changes

IFRS 18 makes specific amendments to balance sheet presentation [^303^]:
- **Goodwill**: Must be presented as a single line item (not grouped with other intangibles)
- **Current/non-current classification**: Carried forward from IAS 1 with clearer guidance

#### Balance Sheet SKILL Parameter Schema

```json
{
  "skill_id": "core.bs",
  "parameters": {
    "as_of_date": "2027-12-31",
    "framework": "ifrs",
    "include_comparatives": true,
    "comparative_date": "2026-12-31",
    "detail_level": "standard | detailed",
    "breakdown": {
      "ar_by_aging_bucket": false,
      "inventory_by_category": false,
      "fixed_assets_by_type": true,
      "liabilities_by_maturity": true
    },
    "output": { "format": "json" }
  }
}
```

### 3.3 Cash Flow Statement SKILL (`core.cf`)

#### Direct vs Indirect Method

The Cash Flow SKILL supports both methods per IAS 7 and GAAP requirements [^289^] [^291^]:

**Direct Method:**
```
Cash flows from operating activities:
  Cash receipts from customers            $XXX
  Cash paid to suppliers                  ($XXX)
  Cash paid to employees                  ($XXX)
  Cash paid for operating expenses        ($XXX)
  Interest paid                           ($XXX)
  Income taxes paid                       ($XXX)
  Net cash from operating activities      $XXX
```

**Indirect Method (most common) [^289^]:**
```
Cash flows from operating activities:
  Net income (starting point)             $XXX
  Adjustments for:
    Depreciation and amortization         $XXX
    Impairment losses                     $XXX
    Gain/loss on disposal of assets       ($XXX)
  Changes in working capital:
    Increase/Decrease in receivables      ($XXX)
    Increase/Decrease in inventory        ($XXX)
    Increase/Decrease in payables         $XXX
  Interest paid                           ($XXX)
  Income taxes paid                       ($XXX)
  Net cash from operating activities      $XXX
```

**IFRS 18 Changes to Cash Flow Statement [^303^]:**
- Indirect method now starts from **Operating Profit or Loss** (not Net Income)
- Interest paid → Financing activities
- Dividends paid → Financing activities
- Interest received → Investing activities
- Dividends received → Investing activities

#### Cash Flow SKILL Parameter Schema

```json
{
  "skill_id": "core.cf",
  "parameters": {
    "period": { "start_date": "2027-01-01", "end_date": "2027-12-31" },
    "framework": "ifrs",
    "method": "indirect | direct",
    "ifrs18_compliant": true,
    "classifications": {
      "interest_received": "investing",
      "interest_paid": "financing",
      "dividends_received": "investing",
      "dividends_paid": "financing"
    },
    "include_supplemental_disclosures": true,
    "output": { "format": "json" }
  }
}
```

### 3.4 Trial Balance SKILL (`core.tb`)

#### Trial Balance Structure

The trial balance lists all account balances at a specific point in time, ensuring debits equal credits [^302^] [^309^]:

```
TRIAL BALANCE
As of [Date]

| Account Code | Account Name           | Debit ($) | Credit ($) |
|--------------|------------------------|-----------|------------|
| 1000         | Cash                   | 50,000    |            |
| 1100         | Accounts Receivable    | 25,000    |            |
| 1200         | Inventory              | 15,000    |            |
| 2000         | Accounts Payable       |           | 20,000     |
| 2100         | Accrued Expenses       |           | 10,000     |
| 3000         | Share Capital          |           | 50,000     |
| 3100         | Retained Earnings      |           | 5,000      |
| 4000         | Revenue                |           | 100,000    |
| 5000         | Cost of Goods Sold     | 60,000    |            |
| 6000         | Operating Expenses     | 35,000    |            |
|--------------|------------------------|-----------|------------|
| TOTALS       |                        | 185,000   | 185,000    |
```

#### Three Types of Trial Balance [^305^]

| Type | Purpose | When Used |
|------|---------|-----------|
| Unadjusted | Initial data capture, reveals obvious errors | Before adjusting entries |
| Adjusted | Includes corrections and accruals | After adjusting entries, before financial statements |
| Post-Closing | Verifies ledger ready for next period | After closing entries |

#### Trial Balance SKILL Parameter Schema

```json
{
  "skill_id": "core.tb",
  "parameters": {
    "as_of_date": "2027-12-31",
    "type": "unadjusted | adjusted | post_closing",
    "include_zero_balance_accounts": false,
    "group_by": "account_type | account_category | none",
    "show_activity": true,
    "opening_balance": true,
    "net_change": true,
    "closing_balance": true,
    "output": { "format": "json" }
  }
}
```

---

## 4. Management Report SKILLs

### 4.1 Aged Accounts Receivable SKILL (`mgmt.ar_aging`)

#### Aging Buckets

Standard aging buckets group outstanding invoices by how long they have been unpaid [^287^] [^288^]:

| Aging Bucket | Range | Collection Priority | Typical Action |
|-------------|-------|-------------------|----------------|
| Current | Not yet due | Low | Monitor |
| 1-30 days | Recently overdue | Medium | Gentle reminder email |
| 31-60 days | Moderately overdue | High | Formal follow-up call |
| 61-90 days | Significantly overdue | Urgent | Escalate to decision-maker |
| 90+ days | Seriously overdue | Critical | Legal action consideration |

**Key Metrics:**
- **Days Sales Outstanding (DSO)**: Should ideally stay under 45 days [^287^]
- **90+ Day Percentage**: Should remain below 20% of total AR
- **Collection Rate by Bucket**: 69.6% for 90+ days [^287^]

#### AR Aging SKILL Parameter Schema

```json
{
  "skill_id": "mgmt.ar_aging",
  "parameters": {
    "as_of_date": "2027-12-31",
    "aging_buckets": ["current", "1-30", "31-60", "61-90", "90+"],
    "days_per_bucket": 30,
    "group_by": "customer | due_date | invoice",
    "include_metrics": {
      "dso": true,
      "collection_rate_by_bucket": true,
      "total_ar_balance": true,
      "overdue_percentage": true
    },
    "filters": {
      "customers_include": [],
      "customers_exclude": [],
      "minimum_balance": 0,
      "currency": "USD"
    },
    "output": { "format": "json" }
  }
}
```

### 4.2 Aged Accounts Payable SKILL (`mgmt.ap_aging`)

#### AP Aging Structure

Similar to AR aging but tracks money owed to suppliers [^287^]:

| Aging Bucket | Purpose |
|-------------|---------|
| Current | Due now or upcoming |
| 1-30 days | Recent invoices, take advantage of early payment discounts |
| 31-60 days | Approaching due date, ensure payment scheduled |
| 61-90 days | Overdue, risk of late payment penalties |
| 90+ days | Seriously overdue, risk supplier relationship damage |

#### AP Aging SKILL Parameter Schema

```json
{
  "skill_id": "mgmt.ap_aging",
  "parameters": {
    "as_of_date": "2027-12-31",
    "aging_buckets": ["current", "1-30", "31-60", "61-90", "90+"],
    "group_by": "supplier | due_date | invoice",
    "include_metrics": {
      "days_payable_outstanding": true,
      "total_ap_balance": true,
      "overdue_percentage": true,
      "early_payment_discount_opportunity": true
    },
    "output": { "format": "json" }
  }
}
```

### 4.3 General Ledger Detail SKILL (`mgmt.gl_detail`)

#### GL Detail Report Structure [^161^] [^316^]

The GL Detail report shows every transaction posted to the general ledger for a selected period:

```
GENERAL LEDGER DETAIL REPORT
Period: 2027-01-01 to 2027-01-31

Account: 6100 - Office Expenses
| Date       | Ref    | Description           | Debit   | Credit  | Balance |
|------------|--------|----------------------|---------|---------|---------|
| 2027-01-01 | OB     | Opening Balance      |         |         | 2,500   |
| 2027-01-05 | INV-01 | Office Supplies      | 350     |         | 2,850   |
| 2027-01-12 | INV-02 | Stationery Order     | 120     |         | 2,970   |
| 2027-01-18 | JE-05  | Accrual Reversal     |         | 200     | 2,770   |
| 2027-01-31 | TOTAL  | Period Total         | 470     | 200     | 2,770   |
```

#### GL Detail SKILL Parameter Schema

```json
{
  "skill_id": "mgmt.gl_detail",
  "parameters": {
    "period": { "start_date": "2027-01-01", "end_date": "2027-01-31" },
    "accounts": {
      "include": ["6*"],
      "exclude": []
    },
    "dimensions": {
      "tracking_categories": [],
      "departments": [],
      "projects": []
    },
    "show_columns": [
      "date", "reference", "description", "source",
      "debit", "credit", "running_balance",
      "journal_entry_id", "user", "created_at"
    ],
    "sort_by": "date | reference | amount",
    "output": { "format": "json" }
  }
}
```

### 4.4 General Ledger Summary SKILL (`mgmt.gl_summary`)

The GL Summary report rolls up transaction activity to account balance level:

```json
{
  "skill_id": "mgmt.gl_summary",
  "parameters": {
    "period": { "start_date": "2027-01-01", "end_date": "2027-01-31" },
    "group_by": "account | account_category | account_type | tracking_category",
    "show": {
      "opening_balance": true,
      "total_debits": true,
      "total_credits": true,
      "net_change": true,
      "closing_balance": true,
      "year_to_date": true
    },
    "output": { "format": "json" }
  }
}
```

### 4.5 Executive Summary SKILL (`mgmt.executive`)

The Executive Summary combines key metrics from multiple reports into a decision-ready overview [^300^]:

```
EXECUTIVE SUMMARY
Period: January 2027
Prepared: 2027-02-05

FINANCIAL HIGHLIGHTS
  Revenue:                    $1,200,000  (+15% vs prior period)
  Gross Profit:                 $720,000  (60% margin)
  Operating Profit:             $180,000  (15% margin)
  Net Profit:                   $135,000  (11.3% margin)

BALANCE SHEET SNAPSHOT
  Total Assets:               $2,500,000
  Total Liabilities:          $1,000,000
  Equity:                     $1,500,000
  Current Ratio:                  2.1x

CASH POSITION
  Cash Balance:                 $450,000
  Operating Cash Flow:          $220,000
  Burn Rate (Net):              $35,000/month
  Runway:                       12.9 months

KEY METRICS
  DSO:                            38 days
  DPO:                            45 days
  Inventory Turnover:             6.2x
  AR > 90 days:                    8%

ALERTS
  [WARNING] AR > 90 days increased to 8% (target: <5%)
  [OK] Cash runway above 6-month threshold
```

#### Executive Summary SKILL Parameter Schema

```json
{
  "skill_id": "mgmt.executive",
  "parameters": {
    "period": { "start_date": "2027-01-01", "end_date": "2027-01-31" },
    "sections": [
      "financial_highlights",
      "balance_sheet_snapshot",
      "cash_position",
      "kpi_summary",
      "variance_alerts",
      "aging_summary"
    ],
    "alert_thresholds": {
      "minimum_runway_months": 6,
      "maximum_dso_days": 45,
      "maximum_overdue_ar_percent": 20,
      "minimum_current_ratio": 1.5
    },
    "comparison_periods": ["prior_month", "prior_year_same_month", "ytd"],
    "output": { "format": "json" }
  }
}
```

---

## 5. Tax Report SKILLs

### 5.1 VAT Return (UK 9-box) SKILL (`tax.vat_uk`)

#### UK VAT 9-Box Structure

The UK VAT return follows the Making Tax Digital (MTD) 9-box format submitted via HMRC's JSON API [^254^] [^256^]:

| Box | Description | Source |
|-----|-------------|--------|
| **Box 1** | VAT due on sales and other outputs | Sum of output VAT on taxable supplies |
| **Box 2** | VAT due on acquisitions from EU (Northern Ireland only) | EU acquisitions VAT |
| **Box 3** | Total VAT due (Box 1 + Box 2) | Automatically calculated |
| **Box 4** | VAT reclaimed on purchases and inputs | Sum of input VAT on eligible purchases |
| **Box 5** | Net VAT payable or reclaimable (Box 3 - Box 4) | Automatically calculated |
| **Box 6** | Total value of sales excluding VAT | Net value of outputs |
| **Box 7** | Total value of purchases excluding VAT | Net value of inputs |
| **Box 8** | Value of EU supplies (Northern Ireland only) | Goods to EU |
| **Box 9** | Value of EU acquisitions (Northern Ireland only) | Goods from EU |

#### MTD Compliance [^254^]

- All VAT-registered businesses must file digitally since April 2022
- Submission via HMRC's JSON API platform [^256^]
- Digital records must be kept with specified data points
- Records must be preserved for 6 years

#### VAT UK SKILL Parameter Schema

```json
{
  "skill_id": "tax.vat_uk",
  "parameters": {
    "vat_period": {
      "start_date": "2027-01-01",
      "end_date": "2027-03-31",
      "scheme": "standard | cash_accounting | flat_rate | annual"
    },
    "mtd_compliance": {
      "digital_links_required": true,
      "api_submission": true,
      "fraud_prevention_headers": true
    },
    "boxes": {
      "box_1_output_vat": "auto_calculated",
      "box_2_eu_acquisitions_vat": "auto_calculated",
      "box_3_total_vat_due": "auto_calculated",
      "box_4_input_vat": "auto_calculated",
      "box_5_net_vat": "auto_calculated",
      "box_6_total_sales_net": "auto_calculated",
      "box_7_total_purchases_net": "auto_calculated",
      "box_8_eu_supplies": "auto_calculated",
      "box_9_eu_acquisitions": "auto_calculated"
    },
    "output": {
      "format": "json",
      "hmrc_api_payload": true,
      "human_readable": true
    }
  }
}
```

### 5.2 BAS (Australia) SKILL (`tax.bas_au`)

#### BAS Reporting Structure [^307^] [^310^]

The Business Activity Statement reports GST and other tax obligations to the Australian Tax Office:

| Field | Description |
|-------|-------------|
| G1 | Total sales (GST-inclusive or exclusive, must indicate) |
| 1A | GST on sales |
| 1B | GST on purchases |
| 2A | Wine equalization tax |
| 2B | Luxury car tax |
| 3A | PAYG withholding |
| 4 | PAYG instalment |

#### BAS SKILL Parameter Schema

```json
{
  "skill_id": "tax.bas_au",
  "parameters": {
    "reporting_period": {
      "frequency": "monthly | quarterly",
      "start_date": "2027-01-01",
      "end_date": "2027-03-31"
    },
    "gst_accounting_method": "accrual | cash",
    "sales_classification": {
      "taxable_sales": true,
      "gst_free_sales": true,
      "input_taxed_sales": true
    },
    "include_payg": true,
    "output": { "format": "json" }
  }
}
```

### 5.3 GST Return (Generic) SKILL (`tax.gst`)

A jurisdiction-agnostic GST report that can be parameterized for any GST-implementing country:

```json
{
  "skill_id": "tax.gst",
  "parameters": {
    "jurisdiction": "SG | NZ | CA | IN | etc",
    "period": { "start_date": "2027-01-01", "end_date": "2027-03-31" },
    "tax_rates": [0, 5, 7, 8, 9, 10, 12, 18, 28],
    "return_format": "jurisdiction_specific",
    "output": { "format": "json" }
  }
}
```

### 5.4 Sales Tax by Jurisdiction SKILL (`tax.sales_tax`)

For US state sales tax and Canadian provincial tax:

```json
{
  "skill_id": "tax.sales_tax",
  "parameters": {
    "period": { "start_date": "2027-01-01", "end_date": "2027-03-31" },
    "jurisdictions": ["CA", "NY", "TX", "FL"],
    "nexus_type": "physical | economic | both",
    "tax_basis": "origin | destination",
    "breakdown_level": "state | county | city | district",
    "output": { "format": "json" }
  }
}
```

---

## 6. KPI SKILLs

### 6.1 Profitability Ratios SKILL (`kpi.profitability`)

| KPI | Formula | Benchmark |
|-----|---------|-----------|
| Gross Profit Margin | (Revenue - COGS) / Revenue | Varies by industry |
| Operating Profit Margin | Operating Profit / Revenue | 10-15% typical |
| Net Profit Margin | Net Income / Revenue | 5-10% typical |
| Return on Assets (ROA) | Net Income / Total Assets | Industry dependent |
| Return on Equity (ROE) | Net Income / Shareholders' Equity | 15%+ desirable |
| EBITDA Margin | EBITDA / Revenue | 20%+ healthy |

### 6.2 Liquidity Ratios SKILL (`kpi.liquidity`)

| KPI | Formula | Benchmark |
|-----|---------|-----------|
| Current Ratio | Current Assets / Current Liabilities | > 2.0 ideal, > 1.0 minimum [^286^] |
| Quick Ratio | (Current Assets - Inventory) / Current Liabilities | > 1.0 healthy |
| Cash Ratio | Cash / Current Liabilities | > 0.2 minimum |
| Working Capital | Current Assets - Current Liabilities | Positive |

### 6.3 Efficiency Ratios SKILL (`kpi.efficiency`)

| KPI | Formula | Purpose |
|-----|---------|---------|
| Inventory Turnover | COGS / Average Inventory | Higher = more efficient |
| Days Sales Outstanding | (AR / Revenue) x 365 | < 45 days healthy [^287^] |
| Days Payable Outstanding | (AP / COGS) x 365 | Balance with DSO |
| Cash Conversion Cycle | DSO + DIO - DPO | Shorter = better |
| Asset Turnover | Revenue / Total Assets | Higher = better utilization |
| Receivables Turnover | Revenue / Average AR | Higher = faster collection |

### 6.4 Solvency Ratios SKILL (`kpi.solvency`)

| KPI | Formula | Benchmark |
|-----|---------|-----------|
| Debt-to-Equity | Total Debt / Total Equity | < 1.0 conservative |
| Debt-to-Assets | Total Debt / Total Assets | < 0.5 healthy |
| Interest Coverage | EBIT / Interest Expense | > 3.0 minimum |
| Equity Ratio | Total Equity / Total Assets | > 0.5 strong |

### 6.5 Startup Metrics SKILL (`kpi.startup`)

Startup-specific KPIs derived from financial data [^160^] [^318^]:

| KPI | Formula | Purpose |
|-----|---------|---------|
| Gross Burn Rate | Total Monthly Expenses | Cash consumption [^160^] |
| Net Burn Rate | Gross Burn - Monthly Revenue | Actual cash depletion |
| Runway | Cash Balance / Net Burn Rate | Months until cash out [^322^] |
| CAC | Sales & Marketing / New Customers | Customer acquisition cost |
| LTV | ARPU x Gross Margin / Churn | Customer lifetime value |
| LTV:CAC Ratio | LTV / CAC | > 3:1 healthy |
| MRR | Monthly Recurring Revenue | Growth indicator |
| ARR | Annual Recurring Revenue | Annualized growth |
| Net Revenue Retention | Starting MRR + Expansion - Churn / Starting MRR | > 100% healthy |

#### Startup KPI SKILL Parameter Schema

```json
{
  "skill_id": "kpi.startup",
  "parameters": {
    "as_of_date": "2027-01-31",
    "metrics": [
      "gross_burn_rate",
      "net_burn_rate",
      "runway_months",
      "cash_balance",
      "mrr",
      "arr",
      "net_revenue_retention",
      "ltv_cac_ratio"
    ],
    "cash_balance": 2400000,
    "monthly_revenue": 180000,
    "monthly_expenses": 420000,
    "scenario_modeling": {
      "enabled": true,
      "scenarios": ["optimistic", "base_case", "pessimistic"]
    },
    "alert_thresholds": {
      "minimum_runway_months": 6,
      "maximum_burn_rate_increase_percent": 10
    },
    "output": { "format": "json" }
  }
}
```

---

## 7. Variance SKILLs

### 7.1 Period-over-Period Comparison SKILL (`var.period`)

Compares financial results across two or more periods:

```json
{
  "skill_id": "var.period",
  "parameters": {
    "base_period": { "start_date": "2027-01-01", "end_date": "2027-01-31" },
    "comparison_periods": [
      { "label": "prior_month", "start_date": "2026-12-01", "end_date": "2026-12-31" },
      { "label": "prior_year", "start_date": "2026-01-01", "end_date": "2026-01-31" }
    ],
    "variance_calculation": {
      "absolute": true,
      "percentage": true,
      "direction_indicator": true
    },
    "group_by": "account | account_category | tracking_category",
    "variance_threshold": {
      "absolute_minimum": 100,
      "percentage_minimum": 5
    },
    "output": { "format": "json" }
  }
}
```

### 7.2 Budget vs Actual SKILL (`var.budget`)

Compares actual results against budget/forecast:

```json
{
  "skill_id": "var.budget",
  "parameters": {
    "period": { "start_date": "2027-01-01", "end_date": "2027-01-31" },
    "budget_version": "approved_2027 | revised_q4_2026 | latest_forecast",
    "variance_columns": [
      "budget_amount",
      "actual_amount",
      "absolute_variance",
      "percentage_variance",
      "favorable_unfavorable"
    ],
    "group_by": "account | department | project | tracking_category",
    "variance_analysis": {
      "explain_threshold_percent": 10,
      "auto_explanation": false
    },
    "output": { "format": "json" }
  }
}
```

### 7.3 Tracking Category Analysis SKILL (`var.tracking`)

Analyzes financial performance across tracking categories (dimensions):

```json
{
  "skill_id": "var.tracking",
  "parameters": {
    "period": { "start_date": "2027-01-01", "end_date": "2027-01-31" },
    "dimension": "tracking_category | department | region | project",
    "dimension_values": ["all"],
    "measures": ["revenue", "expenses", "profit", "margin"],
    "comparison_type": "none | prior_period | budget",
    "pivot_layout": {
      "rows": "dimension_values",
      "columns": "measure"
    },
    "output": { "format": "json" }
  }
}
```

### 7.4 Year-End Comparison SKILL (`var.year_end`)

Multi-year trend analysis:

```json
{
  "skill_id": "var.year_end",
  "parameters": {
    "fiscal_years": ["2024", "2025", "2026", "2027"],
    "compare_on": "full_year | ytd",
    "metrics": [
      "revenue", "gross_profit", "operating_profit", "net_profit",
      "total_assets", "total_equity", "cash_flow_from_operations"
    ],
    "growth_rates": {
      "year_over_year": true,
      "cagr": true
    },
    "output": { "format": "json" }
  }
}
```

---

## 8. Framework Parameterization

### 8.1 How the Same SKILL Produces GAAP or IFRS Output

The framework parameterization system enables a single report SKILL to produce output compliant with different accounting standards through configuration-driven rule application:

```
Parameter: framework = "gaap_us" | "gaap_uk" | "ifrs"
                    |
                    v
Framework Ruleset Engine loads the appropriate rule bundle
                    |
                    v
Rules applied during Stage 4 of the pipeline:
  - Account classification mapping
  - Line item ordering and grouping
  - Required subtotals and totals
  - Disclosure requirements
  - Sign conventions
  - Terminology (e.g., "Income Statement" vs "Profit & Loss Account")
                    |
                    v
Framework-specific output generated
```

### 8.2 Framework Rule Bundle Structure

Each framework is defined by a JSON rule bundle:

```json
{
  "framework_id": "ifrs",
  "framework_version": "2025",
  "rules": {
    "pl_structure": {
      "categories": ["operating", "investing", "financing", "income_taxes", "discontinued"],
      "mandatory_subtotals": ["operating_profit", "profit_before_financing_and_tax"],
      "expense_presentation": ["by_nature", "by_function", "mixed"],
      "mpm_disclosure_required": true
    },
    "bs_structure": {
      "sections": ["current_assets", "non_current_assets", "current_liabilities", "non_current_liabilities", "equity"],
      "goodwill_separate_line": true,
      "current_non_current_basis": true
    },
    "cf_structure": {
      "categories": ["operating", "investing", "financing"],
      "indirect_starting_point": "operating_profit",
      "interest_classification": {
        "interest_received": "investing",
        "interest_paid": "financing",
        "dividends_received": "investing",
        "dividends_paid": "financing"
      }
    },
    "terminology": {
      "income_statement": "Statement of Profit or Loss",
      "balance_sheet": "Statement of Financial Position",
      "cash_flow": "Statement of Cash Flows"
    }
  }
}
```

### 8.3 Key GAAP vs IFRS Differences Handled

| Area | GAAP (US) | IFRS |
|------|-----------|------|
| P&L Format | No prescribed format | IFRS 18: 5 categories, mandatory subtotals [^301^] |
| Inventory | LIFO permitted | LIFO prohibited (FIFO or weighted average) |
| Development Costs | Expensed as incurred | Capitalized if criteria met |
| Reversal of Impairment | Prohibited | Allowed |
| Extraordinary Items | Permitted | Prohibited |
| Terminology | "Income Statement" | "Statement of Profit or Loss" |
| Balance Sheet | Current/Non-current or liquidity-based | Current/Non-current basis |
| Cash Flow | Indirect method most common | IFRS 18: starts from operating profit |

---

## 9. Output Format Layer

### 9.1 JSON (API) Format

```json
{
  "report_metadata": {
    "skill_id": "core.pl",
    "generated_at": "2027-02-15T10:30:00Z",
    "request_id": "uuid",
    "framework": "ifrs",
    "entity_id": "COMP-001",
    "currency": "USD",
    "period": { "start_date": "2027-01-01", "end_date": "2027-01-31" }
  },
  "sections": [
    {
      "category": "operating",
      "line_items": [
        { "account": "Revenue", "amount": 1200000, "category": "operating" },
        { "account": "Cost of Sales", "amount": -480000, "category": "operating" }
      ],
      "subtotals": [
        { "label": "Gross Profit", "amount": 720000 }
      ]
    }
  ],
  "totals": [
    { "label": "Operating Profit", "amount": 180000 }
  ]
}
```

### 9.2 HTML Format

Responsive web-based report with:
- CSS-styled tables with alternating row colors
- Collapsible sections for detailed line items
- Embedded charts (Chart.js or similar)
- Print-friendly styles (`@media print`)
- Framework-specific branding

### 9.3 PDF Format

Generated via headless browser (Puppeteer/Playwright):
- Page headers with entity name, report title, period
- Page footers with generation timestamp and page numbers
- Professional typography and layout
- Table of contents for longer reports
- Digital signature support

### 9.4 CSV Format

Flattened data with header metadata row:

```csv
# Report: Profit & Loss Statement
# Entity: ABC Company
# Period: 2027-01-01 to 2027-01-31
# Framework: IFRS
# Generated: 2027-02-15T10:30:00Z
Category,Line Item,Amount,Category Tag
Operating,Revenue,1200000,operating
Operating,Cost of Sales,-480000,operating
Operating,Gross Profit,720000,subtotal
```

### 9.5 Format Selection Logic

```
if format == "json":
    return structured_data_with_metadata
elif format == "html":
    return render_html_template(structured_data)
elif format == "pdf":
    html = render_html_template(structured_data)
    return generate_pdf(html)
elif format == "csv":
    return flatten_to_csv(structured_data)
elif format == "xbrl":
    return apply_xbrl_taxonomy(structured_data)
elif format == "ixbrl":
    html = render_html_template(structured_data)
    return embed_xbrl_in_html(html, structured_data)
```

---

## 10. Report Scheduling & Distribution

### 10.1 Scheduling Engine

The scheduling system enables automated report generation and distribution [^290^] [^292^]:

| Schedule Type | Description | Example |
|--------------|-------------|---------|
| **Time-based** | Run at fixed intervals | Daily, weekly, monthly, quarterly, annual |
| **Event-driven** | Triggered by system events | On period close, on threshold breach |
| **Data-driven** | Triggered by data conditions | When burn rate exceeds threshold |
| **On-demand** | User-initiated | Ad-hoc report request |

#### Schedule Configuration

```json
{
  "schedule_id": "monthly_pl_distribution",
  "schedule": {
    "type": "time_based",
    "frequency": "monthly",
    "day_of_month": 5,
    "time": "08:00",
    "timezone": "Europe/London"
  },
  "report_request": {
    "skill_id": "core.pl",
    "parameters": {
      "period": { "reference": "prior_month" },
      "framework": "ifrs",
      "output": { "format": "pdf" }
    }
  },
  "distribution": {
    "recipients": [
      { "email": "cfo@company.com", "format": "pdf" },
      { "email": "board@company.com", "format": "pdf" },
      { "email": "finance-team@company.com", "format": "xlsx" }
    ],
    "subject_template": "Monthly P&L Report - {{period_label}}",
    "body_template": "Please find attached the P&L report for {{period_label}}.",
    "security": {
      "password_protection": true,
      "encryption": "pgp"
    }
  },
  "alerts": {
    "on_success": { "notify_admin": false },
    "on_failure": { "notify_admin": true, "retry_count": 3 }
  }
}
```

### 10.2 Distribution Channels

| Channel | Use Case | Configuration |
|---------|----------|---------------|
| Email | Standard distribution | SMTP with TLS, PDF attachment |
| SFTP | Secure file transfer | Encrypted connection, scheduled upload |
| API/Webhook | System integration | POST to endpoint with auth token |
| SharePoint/Teams | Collaboration | Microsoft Graph API integration |
| Slack | Team notifications | Slack webhook with summary |
| Dashboard | Real-time viewing | Embedded in BI tool |

### 10.3 Triggered Alerts

Alerts can be configured based on report output:

```json
{
  "alert_rules": [
    {
      "name": "low_runway_warning",
      "condition": "kpi.runway_months < 6",
      "severity": "warning",
      "notify": ["cfo@company.com", "ceo@company.com"],
      "message": "Cash runway has fallen to {{runway_months}} months"
    },
    {
      "name": "high_overdue_ar",
      "condition": "ar_aging.90_plus_percent > 20",
      "severity": "critical",
      "notify": ["cfo@company.com", "collections@company.com"],
      "message": "AR > 90 days exceeds 20% threshold: {{90_plus_percent}}%"
    }
  ]
}
```

---

## 11. XBRL/iXBRL Layer

### 11.1 XBRL/iXBRL Overview

XBRL (eXtensible Business Reporting Language) embeds machine-readable tags into financial reports. iXBRL combines human-readable HTML with embedded XBRL tags for dual-purpose documents [^260^].

**UK Mandate Timeline [^313^] [^319^]:**
- **April 2028**: All UK companies must file accounts via software-only iXBRL [^313^]
- **HMRC**: iXBRL mandated for company tax returns since 2011 [^314^]
- **ECCTA**: Economic Crime and Corporate Transparency Act drives digital transformation

**EU Context [^257^]:**
- ESMA's ESEF (European Single Electronic Format) mandates iXBRL for listed companies
- IFRS Taxonomy 2025 incorporates IFRS 18 changes [^260^]

### 11.2 Taxonomy Mapping

The XBRL layer maps report line items to taxonomy elements:

```json
{
  "taxonomy_mapping": {
    "taxonomy_id": "ifrs_2025",
    "taxonomy_version": "2025-03-01",
    "mappings": [
      {
        "report_line_item": "Revenue",
        "taxonomy_element": "ifrs-full:Revenue",
        "element_id": "I-659",
        "data_type": "xbrli:monetaryItemType",
        "balance_type": "credit"
      },
      {
        "report_line_item": "Operating Profit (IFRS 18)",
        "taxonomy_element": "ifrs-full:OperatingProfitLoss",
        "element_id": "I-NEW-2025",
        "data_type": "xbrli:monetaryItemType",
        "balance_type": "credit"
      },
      {
        "report_line_item": "Profit Before Financing and Tax",
        "taxonomy_element": "ifrs-full:ProfitLossBeforeFinancingAndIncomeTaxes",
        "element_id": "I-NEW-2025-02",
        "data_type": "xbrli:monetaryItemType",
        "balance_type": "credit"
      }
    ]
  }
}
```

### 11.3 iXBRL Generation Pipeline

```
Stage 1: Generate HTML report (human-readable)
    |
    v
Stage 2: Map line items to XBRL taxonomy elements
    |
    v
Stage 3: Embed XBRL tags as HTML attributes
    |
    v
Stage 4: Generate XBRL context (entity, period, units)
    |
    v
Stage 5: Validate against taxonomy schema
    |
    v
Stage 6: Output .html file with embedded iXBRL
```

### 11.4 Validation Requirements

Per ESMA and HMRC requirements [^255^] [^261^]:

| Validation | Description |
|------------|-------------|
| Schema Validation | Structural integrity against taxonomy schema |
| Calculation Consistency | Mathematical relationships between elements [^257^] |
| Business Rule Validation | Regulatory compliance rules |
| Mandatory Item Check | All required tags present [^255^] |
| Data Type Validation | Correct XBRL data types for each element [^261^] |
| Duplicate Detection | No inconsistent duplicate facts [^261^] |

### 11.5 XBRL/iXBRL SKILL Parameter Schema

```json
{
  "skill_id": "compliance.xbrl",
  "parameters": {
    "base_report": {
      "skill_id": "core.pl",
      "period": { "start_date": "2027-01-01", "end_date": "2027-12-31" }
    },
    "taxonomy": {
      "name": "ifrs_2025",
      "source": "https://xbrl.ifrs.org/taxonomy/2025/",
      "auto_map": true,
      "custom_extensions": []
    },
    "filing_jurisdiction": "uk_companies_house | uk_hmrc | eu_esef | us_sec",
    "output": {
      "format": "ixbrl",
      "include_xbrl_xml": true,
      "validate_before_output": true
    },
    "entity_info": {
      "lei": "529900T8BM49AURSDO55",
      "reporting_period": { "start": "2027-01-01", "end": "2027-12-31" },
      "currency": "USD"
    }
  }
}
```

---

## 12. Implementation Roadmap

### 12.1 Phase 1: Foundation (Months 1-3)

| Deliverable | Description |
|-------------|-------------|
| Report Engine Core | 5-stage pipeline implementation |
| Base SKILL Framework | Schema validation, parameter ingestion |
| Core Statement SKILLs | P&L, Balance Sheet, Cash Flow, Trial Balance |
| JSON + HTML Output | Primary API and web formats |

### 12.2 Phase 2: Management & Variance (Months 4-5)

| Deliverable | Description |
|-------------|-------------|
| Management SKILLs | AR/AP Aging, GL Detail/Summary, Executive Summary |
| Variance SKILLs | Period comparison, Budget vs Actual, Tracking analysis |
| CSV + PDF Output | Spreadsheet and document formats |

### 12.3 Phase 3: Tax & KPI (Months 6-7)

| Deliverable | Description |
|-------------|-------------|
| Tax SKILLs | VAT (UK 9-box), BAS, GST, Sales Tax |
| KPI SKILLs | Profitability, Liquidity, Efficiency, Startup metrics |
| Framework Parameterization | GAAP/IFRS rule bundles |

### 12.4 Phase 4: Compliance & Automation (Months 8-9)

| Deliverable | Description |
|-------------|-------------|
| XBRL/iXBRL Layer | Taxonomy mapping, iXBRL generation, validation |
| Report Scheduling | Automated generation, email distribution |
| Triggered Alerts | Threshold-based alerting |
| IFRS 18 Full Support | Complete IFRS 18 compliance (effective Jan 2027) |

### 12.5 Phase 5: Production Hardening (Months 10-12)

| Deliverable | Description |
|-------------|-------------|
| Performance Optimization | Sub-second report generation for standard reports |
| Caching Layer | Redis-based result caching |
| Audit Logging | Complete execution trail |
| Multi-tenancy | Entity isolation, data security |
| API Rate Limiting | Production-grade traffic management |

---

## References

| Citation | Source | Key Information |
|----------|--------|-----------------|
| [^254^] | EDICOM | UK MTD VAT 9-box structure and compliance |
| [^255^] | IRD Hong Kong | iXBRL tagging requirements and validation |
| [^256^] | Sovos | MTD VAT filing via JSON API |
| [^257^] | Aditum (XBRL) | XBRL taxonomy mapping, validation, global adoption |
| [^258^] | AbraTax | UK VAT return box descriptions |
| [^259^] | ACS MTD Guide | MTD digital record keeping requirements |
| [^260^] | Dawgen Global | IFRS Accounting Taxonomy 2025, iXBRL, IFRS 18 |
| [^261^] | ESMA ESEF Manual | iXBRL validation rules, data types |
| [^263^] | Inkle | GAAP vs IFRS parameterization approaches |
| [^286^] | Dania Accounting | Financial KPI definitions and formulas |
| [^287^] | Invoice Butler | AR aging report buckets, DSO benchmarks |
| [^288^] | Zone & Co | AR aging structure and 30-60-90-90+ buckets |
| [^289^] | Indeed | Direct vs Indirect cash flow comparison table |
| [^290^] | Smart Report Organizer | Report scheduling and distribution automation |
| [^291^] | ICAEW | Cash flow direct vs indirect method under IAS 7 |
| [^292^] | PBRS/ChristianSteven | BI report automation features |
| [^293^] | ResolutAI | AR aging benchmarks and collection actions |
| [^294^] | Aico | AR aging report structure and standard buckets |
| [^295^] | Nomentia | Direct vs indirect cash flow methods comparison |
| [^296^] | Allianz Trade | Direct vs indirect cash flow highlights |
| [^297^] | Hougaard | Automated financial report distribution |
| [^298^] | Stripe | Trial balance report structure |
| [^299^] | HighRadius | Trial balance format and structure |
| [^300^] | Monday.com | Executive summary structure and components |
| [^301^] | Trullion | IFRS 18 comprehensive guide, MPMs, effective date |
| [^302^] | Xero | Trial balance definition and types |
| [^303^] | Fidugius | IFRS 18 practice implementation, subtotals, cash flow changes |
| [^304^] | Asana | Executive summary writing guide |
| [^305^] | Investopedia | Trial balance types (unadjusted, adjusted, post-closing) |
| [^306^] | KPMG Finland | IFRS 18 overview and key changes |
| [^307^] | UNSW | BAS (Australia) structure and reporting |
| [^308^] | IFRS Foundation | IFRS 18 Effects Analysis, MPM disclosures |
| [^309^] | Sage | Trial balance three-column layout |
| [^310^] | ATO Australia | Simpler BAS GST bookkeeping guide |
| [^312^] | ACT Tax Group | Monthly vs quarterly BAS reporting |
| [^313^] | GOV.UK | Companies House iXBRL filing from April 2028 |
| [^314^] | Hawksford | UK software-only filing preparation |
| [^315^] | XBRL.org | UK digital reporting commitment |
| [^316^] | Sage UK | General ledger report components |
| [^317^] | Geckoboard | Burn rate KPI definition |
| [^318^] | Afino | 10 essential startup financial reports |
| [^319^] | Changes to UK Company Law | Software-only filing from April 2028 |
| [^322^] | Parikh Financial | Burn rate and runway calculation |
| [^325^] | Houseblend | IFRS 18 income statement categories and subtotals |
| [^326^] | CFI | Balance sheet format, structure, examples |
| [^329^] | KPMG | IFRS 18 presentation and disclosure details |
| [^331^] | DataSnipper | Four types of audit reports |
| [^332^] | PCAOB | Audit reporting standards (AS 3105) |
| [^333^] | Diligent | Audit report types and opinions |
| [^334^] | OAG BC | Audit opinion types (unmodified, qualified, adverse, disclaimer) |
| [^335^] | AUASB | COVID-19 modified audit opinions guidance |
| [^336^] | IFEC | Auditor opinion types for investors |
| [^337^] | ICAEW | Modified audit opinions explained |

---

*Document generated: 2025-01-15*
*Version: 1.0.0*
*Skill Framework Version: v1*
