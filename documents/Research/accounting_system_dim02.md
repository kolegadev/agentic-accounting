# Dimension 02: Chart of Accounts & General Ledger Data Model

> **Version:** 1.0 | **Date:** 2025-06-26 | **Classification:** Research & Design Specification
> **Scope:** Complete COA structure and GL data model for a multi-standard accounting system supporting IFRS, US GAAP, and VAT/GST regimes.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Research Foundation](#2-research-foundation)
3. [Standard COA Templates](#3-standard-coa-templates)
4. [Account Numbering Scheme](#4-account-numbering-scheme)
5. [Formance Account Mapping](#5-formance-account-mapping)
6. [Account Metadata Schema](#6-account-metadata-schema)
7. [Multi-Standard Support](#7-multi-standard-support)
8. [Control Accounts](#8-control-accounts)
9. [Tracking Categories](#9-tracking-categories)
10. [Opening Balances](#10-opening-balances)
11. [Historical Migration](#11-historical-migration)
12. [Account Lifecycle](#12-account-lifecycle)
13. [GL Data Model Specification](#13-gl-data-model-specification)
14. [Implementation Guide](#14-implementation-guide)
15. [References](#15-references)

---

## 1. Executive Summary

This document provides the complete design specification for the Chart of Accounts (COA) and General Ledger (GL) data model of a multi-standard accounting system. Neither IFRS nor US GAAP prescribes a mandatory COA structure -- both frameworks allow flexibility in account organization while mandating specific presentation requirements for financial statements [^246^][^180^]. This flexibility enables the design of a unified COA that adapts to multiple accounting standards through metadata-driven configuration rather than structural duplication.

**Key Design Decisions:**

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Numbering scheme | 4-digit with gap-friendly allocation | Standard practice; leaves room for 100 accounts per sub-range [^434^][^436^] |
| Standard categories | 5 categories (Assets, Liabilities, Equity, Revenue, Expenses) | Aligns with both IFRS and US GAAP presentation requirements |
| Dimension strategy | External tracking categories (not embedded in account numbers) | Prevents "exponential account explosion" [^435^]; aligns with NetSuite/Xero best practices [^434^] |
| Ledger backend | Formance-compatible colon-delimited paths | Enables programmable double-entry with regulatory-grade traceability [^45^] |
| Tax control | Dedicated VAT/GST control accounts per regime | Required for multi-jurisdiction compliance [^268^] |
| Migration support | Xero/QuickBooks CSV + IIF import adapters | Over 80% of SME migrations use these formats [^239^] |

---

## 2. Research Foundation

### 2.1 IFRS Requirements (IAS 1)

IAS 1 *Presentation of Financial Statements* sets out the overall requirements for financial statement presentation but does **not** prescribe a specific chart of accounts format [^246^]. Key requirements affecting COA design:

- **Minimum financial statements:** Statement of financial position, statement of profit/loss and OCI, statement of changes in equity, statement of cash flows, and notes
- **Comparative information:** Required for the preceding period
- **Materiality and aggregation:** Items of similar nature may be aggregated; items of dissimilar nature must be presented separately
- **Offsetting prohibition:** Assets/liabilities and income/expenses cannot be offset unless permitted by another standard

IFRS uses the term **"reserves"** broadly to describe all equity components except paid-in capital, encompassing retained earnings and revaluation accounts [^410^].

### 2.2 US GAAP Requirements (ASC 205)

ASC 205 *Presentation of Financial Statements* provides baseline authoritative guidance for US GAAP reporting entities [^180^]:

- Required financial statements: Financial position, earnings (net income), comprehensive income, cash flows, and investments by/distributions to owners
- US GAAP allows changes in shareholders' equity to be presented **in the notes** (unlike IFRS which requires a separate statement) [^408^]
- **Revaluation is prohibited** except for impairment testing [^177^]
- Uses "Accumulated Other Comprehensive Income (AOCI)" rather than IFRS-style reserves [^409^]

### 2.3 IFRS for SMEs

IFRS for SMEs (Section 3) provides simplified presentation requirements for smaller entities [^518^]:
- Permits single *Statement of Income and Retained Earnings* if the only changes to equity result from profit/loss, dividends, errors, and policy changes
- Substantially fewer disclosure requirements (230 pages vs 3,000+ for full IFRS)
- Built on full IFRS foundation with cost-benefit simplifications

### 2.4 Formance Ledger Architecture

Formance uses a multi-segment account namespace with colon-delimited paths creating hierarchical addresses [^45^]:

```
{domain}:{entity_id}:{sub_account}
```

Core data model tables:

| Table | Key Columns |
|-------|-------------|
| accounts | id, address (e.g., `users:1234:wallet`), metadata |
| transactions | id, timestamp, reference (idempotency key) |
| postings | id, transaction_id (FK), source, destination, asset, amount |

Balances are computed at read time by aggregating postings per account. Metadata attached to any transaction or account is queryable directly [^45^].

---

## 3. Standard COA Templates

### 3.1 Universal Base Template

The base COA provides the foundation for all industry-specific templates. Each template builds on this structure.

#### Assets (1000-1999)

| Code | Account Name | Type | Notes |
|------|-------------|------|-------|
| 1000 | Cash - Operating | Bank | Primary checking account |
| 1010 | Cash - Savings | Bank | Reserve/savings account |
| 1020 | Cash - Petty Cash | Current Asset | Physical cash on hand |
| 1100 | Accounts Receivable | Current Asset | Trade receivables |
| 1110 | Allowance for Doubtful Accounts | Contra-Asset | Credit balance expected uncollectible |
| 1120 | Notes Receivable | Current Asset | Short-term notes |
| 1200 | Inventory | Current Asset | For retail/manufacturing |
| 1210 | Raw Materials Inventory | Current Asset | Manufacturing only |
| 1220 | Work in Progress | Current Asset | Manufacturing/construction |
| 1230 | Finished Goods Inventory | Current Asset | Manufacturing/retail |
| 1300 | Prepaid Expenses | Current Asset | Insurance, rent, subscriptions |
| 1310 | Prepaid Insurance | Current Asset | Insurance premiums paid in advance |
| 1400 | Office Equipment | Fixed Asset | Computers, furniture |
| 1410 | Accumulated Depreciation - Equipment | Contra-Asset | |
| 1500 | Property & Building | Fixed Asset | Owned real estate |
| 1510 | Accumulated Depreciation - Building | Contra-Asset | |
| 1600 | Vehicles | Fixed Asset | Company vehicles |
| 1610 | Accumulated Depreciation - Vehicles | Contra-Asset | |
| 1700 | Intangible Assets | Fixed Asset | Patents, trademarks |
| 1710 | Accumulated Amortization | Contra-Asset | |
| 1800 | Capitalized Software Development | Fixed Asset | SaaS: ASC 350-40 / IAS 38 [^262^] |
| 1810 | Accumulated Amortization - Software | Contra-Asset | |

#### Liabilities (2000-2999)

| Code | Account Name | Type | Notes |
|------|-------------|------|-------|
| 2000 | Accounts Payable | Current Liability | Trade payables |
| 2010 | Accrued Expenses | Current Liability | Accrued costs not yet invoiced |
| 2020 | Wages Payable | Current Liability | Earned but not yet paid |
| 2030 | Payroll Tax Payable | Current Liability | Employer tax obligations |
| 2100 | Sales Tax/VAT Payable | Current Liability | Output tax collected |
| 2110 | Input VAT Recoverable | Current Asset | VAT on purchases (debit balance) |
| 2120 | VAT Control Account | Current Liability | Net VAT position to remit [^89^] |
| 2130 | GST Payable | Current Liability | For GST jurisdictions |
| 2200 | Short-Term Loans | Current Liability | < 12 months maturity |
| 2210 | Current Portion of Long-Term Debt | Current Liability | Principal due within 12 months |
| 2300 | Deferred Revenue - Current | Current Liability | Revenue to be recognized < 12 mo [^262^] |
| 2310 | Deferred Revenue - Long-Term | Long-Term Liability | Revenue > 12 months |
| 2400 | Line of Credit | Current Liability | Revolving credit facility |
| 2500 | Long-Term Loans | Long-Term Liability | > 12 months maturity |
| 2510 | Mortgage Payable | Long-Term Liability | Property loans |
| 2600 | Lease Liability | Long-Term Liability | ASC 842 / IFRS 16 |
| 2700 | Deferred Tax Liability | Long-Term Liability | Temporary differences |

#### Equity (3000-3999)

| Code | Account Name | Type | Notes |
|------|-------------|------|-------|
| 3000 | Common Stock / Share Capital | Equity | Par value of issued shares [^409^] |
| 3010 | Additional Paid-In Capital / Share Premium | Equity | Amount above par value [^409^] |
| 3020 | Treasury Stock | Contra-Equity | Repurchased shares (US GAAP) |
| 3100 | Retained Earnings | Equity | Accumulated profits/losses |
| 3110 | Dividends Declared | Contra-Equity | Distributions to owners |
| 3200 | Revaluation Surplus | Equity | IFRS: PPE revaluation reserve [^177^] |
| 3210 | Foreign Currency Translation Reserve | Equity | IAS 21 translation differences |
| 3300 | Opening Balance Equity | Equity | System account for migration |
| 3400 | Accumulated OCI | Equity | US GAAP: unrealized gains/losses [^409^] |

#### Revenue (4000-4999)

| Code | Account Name | Type | Notes |
|------|-------------|------|-------|
| 4000 | Product Sales Revenue | Revenue | Core product income |
| 4010 | Service Revenue | Revenue | Professional services |
| 4020 | Subscription Revenue | Revenue | Recurring SaaS revenue [^262^] |
| 4030 | Implementation Revenue | Revenue | One-time setup fees |
| 4040 | Professional Services Revenue | Revenue | Consulting/training |
| 4050 | Usage/Overage Revenue | Revenue | Consumption-based billing [^262^] |
| 4060 | Contract Income | Revenue | Construction: percentage completion |
| 4070 | Interest Income | Other Income | Bank interest |
| 4080 | Gain on Asset Sale | Other Income | Disposal of fixed assets |
| 4900 | Sales Returns & Allowances | Contra-Revenue | Deduction from gross sales |

#### Cost of Goods Sold (5000-5499)

| Code | Account Name | Type | Notes |
|------|-------------|------|-------|
| 5000 | Cost of Goods Sold | COGS | Direct product costs |
| 5010 | Raw Materials Costs | COGS | Manufacturing [^404^] |
| 5020 | Direct Labor Costs | COGS | Factory/production wages [^404^] |
| 5030 | Factory Overhead | COGS | Utilities, indirect materials [^404^] |
| 5100 | Hosting & Infrastructure | COGS | SaaS: AWS, GCP, Azure [^262^] |
| 5110 | Customer Support Salaries | COGS | SaaS: direct support |
| 5120 | Payment Processing Fees | COGS | Merchant fees on revenue |
| 5130 | Third-Party Software (Embedded) | COGS | APIs in product delivery |
| 5200 | Direct Project Costs | COGS | Consulting: billable staff [^521^] |
| 5210 | Subcontractor Costs | COGS | Outsourced project labor |
| 5300 | Freight-In | COGS | Shipping to receive goods |

#### Operating Expenses (5500-8999)

| Code | Account Name | Type | Notes |
|------|-------------|------|-------|
| 6000 | Salaries & Wages - R&D | Expense | Engineering/product salaries [^262^] |
| 6010 | Salaries & Wages - Sales | Expense | Sales team compensation |
| 6020 | Salaries & Wages - G&A | Expense | Admin/finance/HR salaries [^521^] |
| 6100 | Payroll Taxes | Expense | Employer social security, etc. |
| 6110 | Employee Benefits | Expense | Health insurance, 401k match |
| 6200 | Rent & Occupancy | Expense | Office/facility lease |
| 6210 | Utilities | Expense | Electricity, water, internet |
| 6300 | Professional Fees | Expense | Legal, audit, consulting |
| 6400 | Marketing & Advertising | Expense | Paid ads, content, events |
| 6410 | Software & Subscriptions | Expense | Internal tools (Slack, etc.) |
| 6500 | Travel & Entertainment | Expense | Business travel, meals |
| 6600 | Insurance | Expense | D&O, general liability, cyber |
| 6700 | Office Supplies | Expense | Stationery, consumables |
| 6800 | Depreciation Expense | Expense | Non-COGS depreciation |
| 6810 | Amortization Expense | Expense | Intangible amortization |
| 6900 | Bad Debt Expense | Expense | Write-offs of uncollectible AR |
| 7000 | Research & Development | Expense | Non-capitalized R&D |
| 7100 | Bank Charges | Expense | Account fees, wire charges |
| 7200 | Foreign Exchange Losses | Other Expense | Transaction/currency losses |
| 7300 | Interest Expense | Other Expense | Loan interest |

#### Tax Accounts (8000-8999)

| Code | Account Name | Type | Notes |
|------|-------------|------|-------|
| 8000 | Corporate Income Tax Expense | Tax | Current tax provision |
| 8010 | Deferred Income Tax | Tax | Temporary difference movement |
| 8100 | Penalties & Fines | Expense | Non-deductible penalties |

---

### 3.2 Retail & E-Commerce Template

Retail-specific accounts extending the base template [^264^][^266^]:

| Code | Account Name | Type | Rationale |
|------|-------------|------|-----------|
| 1200 | Inventory - Retail | Current Asset | Goods available for sale |
| 1210 | Inventory - Returns | Current Asset | Customer returns pending inspection |
| 1240 | Inventory Shrinkage | Expense | Theft, damage, loss |
| 1250 | Freight-In | COGS | Shipping costs to receive inventory |
| 4000 | Sales Revenue - In-Store | Revenue | Physical retail sales |
| 4010 | Sales Revenue - Online | Revenue | E-commerce sales |
| 4020 | Sales Revenue - Wholesale | Revenue | B2B sales |
| 4030 | Shipping Revenue | Revenue | Delivery fees charged |
| 4040 | Gift Card Revenue (Liability) | Current Liability | Unredeemed gift cards |
| 4100 | Merchant Processing Fees | Expense | Credit card processing |
| 4110 | Marketplace Fees | Expense | Amazon, eBay commissions |
| 4120 | Advertising - Digital | Expense | Google, Meta, TikTok ads |

### 3.3 Service Company Template

Professional services/consulting firm template [^514^][^521^][^520^]:

| Code | Account Name | Type | Rationale |
|------|-------------|------|-----------|
| 4010 | Strategy Consulting Revenue | Revenue | Service line separation [^514^] |
| 4015 | Implementation Revenue | Revenue | System deployment fees |
| 4020 | Operations Consulting Revenue | Revenue | Process improvement |
| 4025 | Change Management Revenue | Revenue | Organizational change |
| 4030 | Retainer Revenue | Revenue | Recurring monthly fees |
| 4035 | Project-Based Revenue | Revenue | Fixed-scope engagements |
| 4040 | Hourly Revenue | Revenue | Time & materials billing |
| 4050 | Reimbursable Revenue | Revenue | Pass-through travel/expenses [^514^] |
| 5200 | Direct Labor - Billable Staff | COGS | Project delivery salaries [^521^] |
| 5210 | Subcontractor Costs | COGS | External consultants |
| 5220 | Travel - Direct Project | COGS | Client-site travel |

**Key structural principle:** Payroll costs follow the employee's work. Billable staff = COGS; admin staff = G&A; business development = Sales & Marketing [^521^]. Target gross margin: 60-75% for consulting [^514^].

### 3.4 SaaS Company Template

Software-as-a-Service template with subscription-specific accounts [^262^][^263^]:

| Code | Account Name | Type | Rationale |
|------|-------------|------|-----------|
| 1020 | Cash - Reserve | Bank | Runway visibility [^262^] |
| 1800 | Capitalized Software Development | Fixed Asset | ASC 350-40 costs [^262^] |
| 1810 | Accumulated Amortization - Software | Contra-Asset | 3-5 year useful life |
| 2200 | Deferred Revenue - Current | Current Liability | Subscriptions < 12 months |
| 2210 | Deferred Revenue - Long-Term | Long-Term Liability | Multi-year contracts [^262^] |
| 2600 | Deferred Commission Liability | Current Liability | ASC 340-40 sales commissions |
| 4000 | Subscription Revenue | Revenue | Core SaaS revenue (ASC 606) |
| 4100 | Implementation Revenue | Revenue | Setup/onboarding |
| 4200 | Professional Services Revenue | Revenue | Training, custom dev |
| 4300 | Usage/Overage Revenue | Revenue | Consumption above base |
| 5000 | Hosting & Infrastructure | COGS | AWS, GCP, Azure [^262^] |
| 5010 | Customer Support Salaries | COGS | Direct support team |
| 5020 | Third-Party Software (Embedded) | COGS | APIs, data providers |
| 5030 | Payment Processing Fees | COGS | Stripe, etc. |
| 5040 | Amortization of Capitalized Software | COGS | Dev cost amortization |
| 6000 | R&D - Salaries & Wages | Expense | Engineering team [^262^] |
| 6100 | R&D - Software & Tools | Expense | Dev tools, CI/CD |
| 7000 | Sales - Salaries & Commissions | Expense | Including variable comp |
| 7100 | Marketing - Advertising | Expense | Paid acquisition |
| 8000 | G&A - Salaries | Expense | Finance, HR, legal |

**SaaS-specific guidance:**
- Seed stage (pre-revenue): 30-40 accounts [^262^]
- Series A ($1M-$5M ARR): 50-70 accounts with revenue breakouts
- Series B+ ($5M-$50M ARR): 80-100+ accounts with multi-entity support
- IPO-track ($50M+): 100-150+ accounts with SOX compliance and multi-book [^262^]
- Target subscription gross margin: 75-85% [^262^]

### 3.5 Manufacturing Template

Manufacturing-specific accounts [^404^][^405^]:

| Code | Account Name | Type | Rationale |
|------|-------------|------|-----------|
| 1100 | Raw Materials Inventory | Current Asset | Unprocessed materials |
| 1110 | Work in Progress (WIP) | Current Asset | Partially finished goods |
| 1120 | Finished Goods Inventory | Current Asset | Completed products |
| 1130 | Factory Supplies | Current Asset | Indirect materials |
| 1210 | Manufacturing Equipment | Fixed Asset | Production machinery |
| 1220 | Factory Building | Fixed Asset | Production facilities |
| 5010 | Direct Materials Cost | COGS | Raw materials consumed |
| 5020 | Direct Labor Cost | COGS | Factory floor wages |
| 5030 | Manufacturing Overhead | COGS | Indirect production costs |
| 5040 | Quality Control Costs | COGS | Testing/inspection |
| 6010 | Factory Rent | Expense | Production facility lease |
| 6020 | Factory Utilities | Expense | Production energy/water |
| 6030 | Maintenance & Repairs | Expense | Equipment upkeep |

### 3.6 Construction Template

Construction-specific accounts with percentage-of-completion support [^261^][^265^]:

| Code | Account Name | Type | Rationale |
|------|-------------|------|-----------|
| 1150 | Construction In Progress | Current Asset | CIP/WIP for uncompleted contracts |
| 1160 | Retentions Receivable | Current Asset | Held by clients until completion |
| 1170 | Estimated Earnings in Excess of Billings | Current Asset | Under-billings (percentage completion) |
| 1180 | Billings in Excess of Costs | Current Liability | Over-billings |
| 4000 | Contract Income | Revenue | Core construction revenue |
| 4010 | Variations & Change Orders | Revenue | Approved contract modifications |
| 4020 | Hire & Rebill Income | Revenue | Equipment rental pass-through |
| 5100 | Direct Materials | COGS | Permanent materials |
| 5110 | Direct Labor - Site | COGS | Field/construction wages |
| 5120 | Subcontractors | COGS | Trade packages (CIS-aligned) |
| 5130 | Plant & Equipment Hire | COGS | Hired machinery/scaffolding |
| 5140 | Small Tools & Consumables | COGS | PPE, fixings, hand tools |
| 5150 | Site Utilities | Expense | Temporary power/water |
| 5160 | Site Accommodation | Expense | Site offices, welfare |
| 5170 | Waste & Skips | Expense | Disposal costs |

---

## 4. Account Numbering Scheme

### 4.1 Core Numbering Convention

The system uses a **4-digit hierarchical numbering scheme** with intentional gaps for future expansion [^434^][^436^]. This is the most widely adopted convention across accounting platforms.

```
NNNN
|  |
|  +-- Detail identifier (00-99)
+----- Category identifier (1-8)
```

### 4.2 Standard Number Ranges

| Range | Category | Sub-Ranges |
|-------|----------|------------|
| 1000 - 1999 | **Assets** | 1000-1099: Cash & Equivalents; 1100-1199: Receivables; 1200-1499: Inventory & Current Assets; 1500-1799: Fixed Assets; 1800-1999: Intangible Assets |
| 2000 - 2999 | **Liabilities** | 2000-2099: Accounts Payable; 2100-2199: Tax Liabilities; 2200-2299: Short-Term Debt; 2300-2499: Deferred Revenue; 2500-2799: Long-Term Debt; 2800-2999: Provisions |
| 3000 - 3999 | **Equity** | 3000-3099: Share Capital; 3100-3199: Retained Earnings; 3200-3499: Reserves; 3500-3999: Other Equity |
| 4000 - 4999 | **Revenue** | 4000-4099: Product/Service Revenue; 4100-4199: Subscription/Recurring; 4200-4499: Other Revenue; 4500-4999: Contra-Revenue |
| 5000 - 5499 | **Cost of Goods Sold** | 5000-5099: Direct Materials; 5100-5199: Direct Labor; 5200-5299: Subcontractors; 5300-5499: Other Direct Costs |
| 5500 - 5999 | *(Reserved for future COGS expansion)* | |
| 6000 - 6999 | **Operating Expenses - R&D** | 6000-6099: Salaries; 6100-6199: Payroll Taxes; 6200-6299: Facilities; 6300-6399: Professional Fees |
| 7000 - 7999 | **Operating Expenses - S&M & G&A** | 7000-7099: Sales; 7100-7199: Marketing; 7200-7499: G&A; 7500-7999: Other OpEx |
| 8000 - 8999 | **Tax & Other** | 8000-8099: Income Tax; 8100-8199: Other Tax; 8200-8499: Other Income; 8500-8999: Other Expenses |
| 9000 - 9999 | **System & Control Accounts** | 9000-9099: Suspense; 9100-9199: Clearing; 9200-9399: Intercompany; 9900-9999: System |

### 4.3 Gap-Friendly Numbering Rules

1. **Leave 10-point gaps** between major account groups within a range (e.g., 1000, 1010, 1020 rather than 1000, 1001, 1002) [^436^]
2. **Reserve 100-point blocks** for sub-categories (e.g., 1100-1199 for all receivables)
3. **New accounts are inserted** at the midpoint of gaps (e.g., new cash account between 1000 and 1010 gets 1005)
4. **Maximum depth:** 2 levels of parent-child hierarchy; deeper nesting handled via tracking categories [^434^]

### 4.4 Parent-Child Hierarchy

Sub-accounts use a dotted notation in display (only):

```
6000 Research & Development Expenses (parent)
  6000.10 R&D - Engineering Salaries
  6000.20 R&D - Software & Tools
  6000.30 R&D - Contractors
```

The stored account number remains `6000` for the parent, `6010`, `6020` for children. Parent accounts are **non-posting** summary accounts that aggregate child balances [^434^].

---

## 5. Formance Account Mapping

### 5.1 Path Structure

Each COA account maps to a Formance colon-delimited path following the pattern [^45^]:

```
{coa_type}:{standard}:{account_number}:{dimension_path}
```

Where:
- `coa_type`: The high-level category (`assets`, `liabilities`, `equity`, `revenue`, `expenses`)
- `standard`: The accounting standard context (`gaap`, `ifrs`, `sme`)
- `account_number`: The 4-digit COA code
- `dimension_path`: Optional dimensional qualifier

### 5.2 Account Path Examples

| COA Code | Account Name | Formance Path |
|----------|-------------|---------------|
| 1000 | Cash - Operating | `assets:universal:1000:bank:operating` |
| 1100 | Accounts Receivable | `assets:universal:1100:receivables:trade` |
| 1800 | Capitalized Software | `assets:gaap:1800:intangibles:software` |
| 1800 | Capitalized Software (IFRS) | `assets:ifrs:1800:intangibles:software` |
| 2100 | VAT Output Tax | `liabilities:universal:2100:tax:vat:output` |
| 2110 | VAT Input Tax | `assets:universal:2110:tax:vat:input` |
| 2120 | VAT Control Account | `liabilities:universal:2120:tax:vat:control` |
| 2200 | Deferred Revenue | `liabilities:universal:2200:deferred:current` |
| 4000 | Product Sales | `revenue:universal:4000:sales:product` |
| 5000 | COGS | `expenses:universal:5000:cogs:product` |
| 6000 | R&D Salaries | `expenses:universal:6000:opex:rd:salaries` |
| 9000 | Suspense Account | `system:universal:9000:suspense:general` |
| 9100 | Clearing Account | `system:universal:9100:clearing:general` |

### 5.3 Dimensional Path Encoding

Tracking categories are encoded as additional path segments rather than embedded in account numbers:

```
# Transaction with department and project dimensions
expenses:universal:6000:opex:rd:salaries?department=engineering&project=prj_001

# Query all R&D expenses across departments
GET /v2/ledger/{ledger}/accounts?address=expenses:universal:6*:opex:rd:*

# Query by department dimension
GET /v2/ledger/{ledger}/transactions?metadata[department]=engineering
```

### 5.4 Multi-Entity Path Structure

For multi-entity organizations:

```
{coa_type}:{entity_code}:{standard}:{account_number}:{detail}

# Example: UK subsidiary VAT account
liabilities:uk001:ifrs:2100:tax:vat:output

# Example: US subsidiary sales
revenue:us001:gaap:4000:sales:product
```

### 5.5 Formance Posting Examples

```json
{
  "reference": "INV-2024-001",
  "metadata": {
    "document_type": "sales_invoice",
    "entity": "uk001",
    "department": "sales",
    "tax_code": "VAT_20"
  },
  "postings": [
    {
      "source": "assets:universal:1100:receivables:trade",
      "destination": "world",
      "asset": "GBP",
      "amount": 1200
    },
    {
      "source": "world",
      "destination": "revenue:universal:4000:sales:product",
      "asset": "GBP",
      "amount": 1000
    },
    {
      "source": "world",
      "destination": "liabilities:universal:2100:tax:vat:output",
      "asset": "GBP",
      "amount": 200
    }
  ]
}
```

---

## 6. Account Metadata Schema

### 6.1 Core Metadata Fields

Every COA account carries the following metadata:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `coa_code` | string | Yes | 4-digit account number (e.g., "1000") |
| `name` | string | Yes | Human-readable account name |
| `category` | enum | Yes | `asset`, `liability`, `equity`, `revenue`, `expense` |
| `subcategory` | enum | Yes | e.g., `current_asset`, `fixed_asset`, `current_liability` |
| `account_type` | enum | Yes | `bank`, `receivable`, `payable`, `revenue`, `expense`, `equity`, `non_posting` |
| `standard` | array | Yes | `["gaap", "ifrs", "sme"]` - standards this account applies to |
| `tax_category` | string | No | Tax treatment code (e.g., `VAT_20`, `EXEMPT`, `ZERO_RATED`) |
| `tax_report_line` | string | No | Mapping to tax form line item |
| `department` | string | No | Default department allocation |
| `location` | string | No | Default location/branch |
| `currency` | string | No | Functional currency for the account |
| `is_control_account` | boolean | No | Whether this is a system control account |
| `is_bank_account` | boolean | No | Whether this is a bank/cash account |
| `is_active` | boolean | Yes | Account availability for new transactions |
| `is_archive_eligible` | boolean | No | Can be archived (no transactions in N periods) |
| `parent_account` | string | No | Parent COA code (for hierarchy) |
| `description` | string | No | Detailed account description |
| `notes` | string | No | Free-form accounting notes |
| `created_at` | timestamp | Yes | Account creation timestamp |
| `updated_at` | timestamp | Yes | Last modification timestamp |
| `created_by` | string | Yes | User/system that created the account |
| `version` | integer | Yes | Metadata version for optimistic locking |

### 6.2 Standard-Specific Metadata

```json
{
  "standard_mapping": {
    "gaap": {
      "asc_reference": "ASC 205-10",
      "presentation_order": 100,
      "statement_line": "Current Assets"
    },
    "ifrs": {
      "ias_reference": "IAS 1.54",
      "presentation_order": 100,
      "statement_line": "Current Assets"
    },
    "sme": {
      "section_reference": "Section 4",
      "simplified_presentation": true
    }
  }
}
```

### 6.3 Tax Metadata

```json
{
  "tax_metadata": {
    "vat": {
      "jurisdiction": "GB",
      "standard_rate": 0.20,
      "reduced_rate": 0.05,
      "zero_rate": 0.00,
      "output_account": "2100",
      "input_account": "2110",
      "control_account": "2120"
    },
    "gst": {
      "jurisdiction": "AU",
      "standard_rate": 0.10,
      "output_account": "2130",
      "input_account": "2110",
      "control_account": "2120"
    }
  }
}
```

### 6.4 Migration Metadata

```json
{
  "migration": {
    "source_system": "xero",
    "source_account_code": "610",
    "source_account_name": "Revenue Received in Advance",
    "mapping_date": "2024-06-01",
    "mapped_by": "migration_script_v1",
    "confidence": 0.95
  }
}
```

---

## 7. Multi-Standard Support

### 7.1 Standard Adaptation Strategy

The same COA adapts to different standards through **metadata-driven presentation mapping** rather than structural duplication. The underlying account codes remain constant; only the presentation metadata and financial statement mappings change.

### 7.2 Key GAAP vs IFRS Presentation Differences

| Aspect | US GAAP | IFRS | Impact on COA |
|--------|---------|------|---------------|
| **Equity section** | Common Stock + APIC + AOCI + Retained Earnings [^408^] | Share Capital + Share Premium + Reserves + Retained Earnings [^410^] | Equity accounts 3000-3999 map to different presentation lines |
| **PPE valuation** | Historical cost only; no revaluation [^177^] | Revaluation model permitted (IAS 16) | Account 3200 (Revaluation Surplus) is IFRS-only |
| **OCI presentation** | Presented in statement of changes in equity OR notes [^408^] | Must be presented as separate statement [^408^] | Metadata flag `requires_separate_oci_statement` |
| **Share-based payments** | ASC 718 (fair value at grant) | IFRS 2 (similar but different measurement) | Same COA account; different calculation metadata |
| **R&D costs** | Expensed as incurred (ASC 730) | Research expensed; development capitalized (IAS 38) | Account 1800 (Capitalized Software) available under both; metadata controls eligibility |
| **Terminology** | "Stockholders' Equity", "Common Stock" [^409^] | "Shareholders' Equity", "Share Capital" [^409^] | Display name localization via metadata |
| **Extraordinary items** | Prohibited (ASC 225-20) | Not prohibited | Account range 8500-8999 filtered out under GAAP |
| **LIFO inventory** | Permitted | Prohibited (IAS 2) | Inventory method stored as account metadata |

### 7.3 Account-Level Standard Flags

```json
{
  "standard_eligibility": {
    "gaap": {
      "applicable": true,
      "presentation_group": "Current Assets",
      "display_name": "Inventory",
      "notes": "Measured at lower of cost or NRV"
    },
    "ifrs": {
      "applicable": true,
      "presentation_group": "Current Assets",
      "display_name": "Inventories",
      "notes": "Measured at lower of cost or NRV; LIFO prohibited"
    },
    "sme": {
      "applicable": true,
      "presentation_group": "Current Assets",
      "display_name": "Inventories",
      "notes": "Section 13 simplifications apply"
    }
  }
}
```

### 7.4 Financial Statement Mapping

The system generates financial statements by applying standard-specific presentation rules to the same underlying COA:

```
IFRS Statement of Financial Position:
  Assets (current → non-current)
    → 1000-1999 accounts with ifrs.applicable=true
  Liabilities (current → non-current)
    → 2000-2999 accounts with ifrs.applicable=true
  Equity
    → 3000-3999 accounts with ifrs.applicable=true
      → 3200 "Revaluation Surplus" included
      → "Share Capital" display name for 3000

US GAAP Balance Sheet:
  Assets (current → non-current)
    → 1000-1999 accounts with gaap.applicable=true
  Liabilities (current → long-term)
    → 2000-2999 accounts with gaap.applicable=true
  Stockholders' Equity
    → 3000-3999 accounts with gaap.applicable=true
      → 3200 "Revaluation Surplus" excluded (gaap.applicable=false)
      → "Common Stock" display name for 3000
      → 3400 AOCI included
```

---

## 8. Control Accounts

### 8.1 VAT/GST Control Accounts

VAT/GST control accounts manage the timing difference between when tax is collected/paid and when it is remitted to the tax authority [^268^][^89^].

#### Standard VAT Account Setup

| Code | Account | Type | Purpose |
|------|---------|------|---------|
| 2100 | VAT Output Tax | Current Liability | Tax charged on sales (owed to authority) |
| 2110 | VAT Input Tax | Current Asset | Tax paid on purchases (recoverable) |
| 2120 | VAT Control Account | Current Liability | Net position; amount to remit/refund |
| 2130 | GST Output Tax | Current Liability | GST jurisdiction equivalent |
| 2140 | Reverse Charge VAT | Current Liability | Self-accounted reverse charge [^268^] |
| 2150 | VAT Penalties & Interest | Expense | Late filing/payment penalties |

#### VAT Journal Entries

```
Sale of goods for £1,000 + 20% VAT:
  Dr  Accounts Receivable        1,200
  Cr  Revenue                     1,000
  Cr  VAT Output Tax (2100)         200

Purchase of supplies for £500 + 20% VAT:
  Dr  Office Supplies              500
  Dr  VAT Input Tax (2110)         100
  Cr  Accounts Payable              600

Monthly VAT settlement (Output > Input):
  Dr  VAT Output Tax (2100)        200
  Cr  VAT Input Tax (2110)         100
  Cr  VAT Control Account (2120)   100

Payment to HMRC:
  Dr  VAT Control Account (2120)   100
  Cr  Bank                         100
```

#### Reverse Charge VAT [^268^]

```
Receipt of service from non-UK vendor, £1,000 + 20% VAT:
  Dr  Professional Fees          1,000
  Dr  VAT Input Tax (2110)         200
  Cr  Reverse Charge VAT (2140)    200
  Cr  Accounts Payable           1,000
```

### 8.2 Suspense Accounts

Suspense accounts temporarily hold transactions requiring investigation before proper classification [^427^][^431^].

| Code | Account | Type | Use Case |
|------|---------|------|----------|
| 9000 | General Suspense | Suspense | Unidentified receipts/payments |
| 9010 | Bank Reconciliation Suspense | Suspense | Timing differences |
| 9020 | Intercompany Suspense | Suspense | Unmatched intercompany items |
| 9030 | Tax Suspense | Suspense | Tax treatment pending determination |

**Best practice:** Resolve suspense items within **30 days** maximum [^431^].

### 8.3 Clearing Accounts

Clearing accounts are planned aggregation points for routine transactions in transition [^430^][^431^].

| Code | Account | Type | Use Case |
|------|---------|------|----------|
| 9100 | General Clearing | Clearing | Multi-step transaction staging |
| 9110 | Payroll Clearing | Clearing | Net pay distribution [^430^] |
| 9120 | Credit Card Clearing | Clearing | Card receipts pending allocation |
| 9130 | Intercompany Clearing | Clearing | Cross-entity settlements [^431^] |
| 9140 | FX Clearing | Clearing | Multi-currency settlement [^431^] |

#### Payroll Clearing Example [^430^]

```
Transfer payroll funds:
  Dr  Payroll Clearing           50,000
  Cr  Bank                       50,000

Individual employee payment:
  Dr  Salary Expense             3,000
  Cr  Payroll Clearing           3,000

# Payroll Clearing should net to zero after all distributions
```

### 8.4 System Accounts

| Code | Account | Type | Purpose |
|------|---------|------|---------|
| 9900 | Opening Balance Equity | Equity | Migration balance offset |
| 9910 | Retained Earnings (System) | Equity | Year-end closing target |
| 9920 | Historical Adjustment | Equity | Prior period corrections |
| 9999 | Rounding Differences | System | Currency rounding < 0.01 |

---

## 9. Tracking Categories

### 9.1 Dimensional Reporting Strategy

Rather than embedding operational detail into account codes (which causes "exponential account explosion" [^435^]), the system uses independent tracking dimensions similar to Xero's tracking categories [^429^][^432^] and NetSuite's segments [^434^].

**Core principle:** One COA account + multiple dimensions = flexible reporting without COA bloat.

### 9.2 Available Dimensions

| Dimension | Type | Cardinality | Use Case |
|-----------|------|-------------|----------|
| Department | Standard | ~10-20 | Functional cost centers |
| Location | Standard | ~5-50 | Geographic branches/stores |
| Project | Standard | ~100s | Job-level profitability |
| Cost Center | Custom | ~20-100 | Budget responsibility centers |
| Product Line | Custom | ~5-20 | Revenue segmentation |
| Entity | System | ~1-100 | Multi-company consolidation |
| Tax Jurisdiction | System | ~1-50 | VAT/GST regime compliance |

### 9.3 Department Dimension (Default)

| Code | Department | Typical Expense Accounts |
|------|-----------|-------------------------|
| DEPT-001 | Executive | 6020, 6300, 6600 |
| DEPT-002 | Finance | 6020, 6300, 6410 |
| DEPT-003 | Sales | 6010, 6500, 6400 |
| DEPT-004 | Marketing | 6400, 6410, 6500 |
| DEPT-005 | Engineering | 6000, 6100, 6410 |
| DEPT-006 | Customer Support | 5110, 6020 |
| DEPT-007 | Operations | 6020, 6200, 6700 |
| DEPT-008 | Legal | 6020, 6300 |
| DEPT-009 | HR | 6020, 6110 |
| DEPT-010 | IT/Infrastructure | 5100, 6020, 6410 |

### 9.4 Transaction-Level Dimension Assignment

```json
{
  "transaction": {
    "reference": "INV-2024-001",
    "postings": [
      {
        "source": "world",
        "destination": "revenue:universal:4000:sales:product",
        "asset": "USD",
        "amount": 5000,
        "metadata": {
          "department": "DEPT-003",
          "location": "US-WEST",
          "project": "PRJ-2024-015",
          "product_line": "PL-SAAS-ENTERPRISE"
        }
      }
    ]
  }
}
```

### 9.5 Reporting by Dimension

```sql
-- Profit & Loss by Department
SELECT 
  t.metadata->>'department' as department,
  a.coa_code,
  a.name,
  SUM(CASE WHEN p.destination LIKE 'revenue:%' THEN p.amount ELSE 0 END) as credits,
  SUM(CASE WHEN p.source LIKE 'expenses:%' OR p.source LIKE 'cogs:%' THEN p.amount ELSE 0 END) as debits
FROM transactions t
JOIN postings p ON t.id = p.transaction_id
JOIN accounts a ON p.destination = a.formance_address
WHERE t.date BETWEEN '2024-01-01' AND '2024-12-31'
GROUP BY t.metadata->>'department', a.coa_code, a.name
ORDER BY department, a.coa_code;
```

### 9.6 Xero Tracking Category Compatibility

The system maps Xero's two tracking categories as follows [^429^][^432^]:

| Xero Concept | System Mapping | Limitation |
|-------------|----------------|------------|
| Tracking Category 1 | Dimension 1 (default: Department) | |
| Tracking Category 2 | Dimension 2 (default: Location) | |
| Tracking Options | Dimension values/codes | |
| Active/Archived | Dimension value status | |

---

## 10. Opening Balances

### 10.1 Establishing Opening Balances

Opening balances are established through a **system-generated journal entry** posted to the Opening Balance Equity account (9900) [^428^][^516^]. This approach is used by QuickBooks, Xero, and Sage 300.

#### New Company (No Prior System)

```
Initial capital contribution of $100,000:
  Dr  Bank (1000)              100,000
  Cr  Common Stock (3000)       10,000    [par value]
  Cr  Additional Paid-In Capital 90,000    [excess over par]

# No Opening Balance Equity entry needed
```

#### Migration from Prior System

```
Opening balances as of 2024-01-01 (from prior system trial balance):
  Dr  Bank (1000)               50,000
  Dr  Accounts Receivable (1100) 25,000
  Dr  Inventory (1200)          30,000
  Dr  Fixed Assets (1400)       80,000
  Dr  Input VAT (2110)           2,000
  Cr  Accumulated Depreciation  20,000
  Cr  Accounts Payable (2000)   15,000
  Cr  Deferred Revenue (2300)    5,000
  Cr  Long-Term Loan (2500)     40,000
  Cr  Opening Balance Equity    107,000    [balancing figure]

# Opening Balance Equity is then closed to Retained Earnings:
  Dr  Opening Balance Equity    107,000
  Cr  Retained Earnings (3100)  107,000
```

### 10.2 Opening Balance Data Model

```json
{
  "opening_balance_entry": {
    "id": "obe-2024-001",
    "effective_date": "2024-01-01",
    "source_system": "xero",
    "migration_id": "mig-2024-q1-001",
    "status": "posted",
    "entries": [
      {
        "coa_code": "1000",
        "account_name": "Cash - Operating",
        "debit": 50000.00,
        "credit": 0.00,
        "source_balance": 50000.00,
        "source_currency": "USD",
        "verification_status": "confirmed"
      }
    ],
    "balancing_entry": {
      "coa_code": "9900",
      "account_name": "Opening Balance Equity",
      "auto_calculated": true
    },
    "closing_entry": {
      "coa_code": "3100",
      "account_name": "Retained Earnings",
      "posted_date": "2024-01-01"
    }
  }
}
```

### 10.3 Balance Verification

Before opening balances are finalized:

1. **Trial balance reconciliation:** Sum of all opening entries must equal zero
2. **Source system comparison:** Balances must match the source system's closing trial balance
3. **Currency verification:** Multi-currency balances converted at opening rate
4. **Approval workflow:** Accounting manager sign-off required

### 10.4 Period-Specific Balances

For mid-year migrations, the system supports **period-specific net changes** [^428^]:

```
Option A: Full transaction history (import all transactions period by period)
Option B: Net changes per period (import period totals)
Option C: Opening balances only (simplest; loses historical period detail)
```

---

## 11. Historical Migration

### 11.1 Migration Strategy Overview

The system supports migration from Xero, QuickBooks (Desktop and Online), and generic CSV sources. Over **80% of SME migrations** use IIF or CSV formats [^239^].

### 11.2 Xero CSV Import Format

Xero's chart of accounts CSV export includes [^242^][^245^]:

| Field | Required | Description |
|-------|----------|-------------|
| Account Code | Yes | Unique code (up to 10 characters) |
| Account Name | Yes | Description (up to 150 characters) |
| Account Type | Yes | Asset, Liability, Equity, Revenue, Expense |
| Tax Type | No | GST/VAT code for automatic calculations |
| Description | No | Additional details |
| Balance | No | Opening balance amount |
| Status | No | Active or Archived |

**Xero CSV Import Mapping:**

```python
xero_to_system_mapping = {
    "Account Code": "coa_code",
    "Account Name": "name",
    "Account Type": "category",  # Mapped to system category enum
    "Tax Type": "tax_category",  # Mapped via tax code lookup
    "Description": "description",
    "Balance": "opening_balance",
    "Status": "is_active"  # "Active" → true, "Archived" → false
}
```

### 11.3 QuickBooks IIF Import Format

QuickBooks Desktop uses IIF (Intuit Interchange Format) -- a tab-separated values file with header rows [^239^][^240^]:

```
!ACCNT	NAME	ACCNTTYPE	DESC	ACCNUM	EXTRA
ACCNT	Checking	BANK	Primary Operating	1000	
ACCNT	Accounts Receivable	AR	Trade Receivables	1100	
ACCNT	Inventory	OCASSET	Product Inventory	1200	
```

**IIF Header Definitions [^240^]:**

| Header | Field | System Mapping |
|--------|-------|----------------|
| `!ACCNT` | Account record type indicator | Entry type |
| `NAME` | Account name | `name` |
| `ACCNTTYPE` | Account type (BANK, AR, AP, INC, COGS, EXP, etc.) | `category` + `account_type` |
| `DESC` | Account description | `description` |
| `ACCNUM` | Account number | `coa_code` |
| `EXTRA` | Extra field | Ignored / `notes` |

### 11.4 Generic CSV Import Format

The system accepts a generic CSV with these columns:

```csv
coa_code,name,category,subcategory,account_type,parent_code,tax_category,opening_balance,opening_balance_date,currency,description,is_active
1000,Cash - Operating,asset,current_asset,bank,,,50000.00,2024-01-01,USD,Primary checking account,true
1100,Accounts Receivable,asset,current_asset,receivable,,,,,,Trade receivables from customers,true
```

### 11.5 Migration Data Model

```json
{
  "migration_job": {
    "id": "mig-2024-q1-001",
    "source_system": "xero",  // xero | quickbooks_desktop | quickbooks_online | csv
    "source_file": "xero_coa_export.csv",
    "target_ledger": "main-ledger",
    "status": "in_progress",
    "steps": [
      {
        "step": "validate_source",
        "status": "completed",
        "records_found": 145,
        "errors": 3
      },
      {
        "step": "map_accounts",
        "status": "completed",
        "auto_mapped": 128,
        "manual_review_required": 14
      },
      {
        "step": "import_accounts",
        "status": "in_progress",
        "accounts_created": 128,
        "accounts_skipped": 0
      },
      {
        "step": "import_opening_balances",
        "status": "pending"
      }
    ],
    "mapping_rules": [
      {
        "source_code": "610",
        "source_name": "Revenue Received in Advance",
        "target_code": "2200",
        "target_name": "Deferred Revenue - Current",
        "mapping_type": "auto",
        "confidence": 0.98
      }
    ]
  }
}
```

### 11.6 Migration Checklist

1. **Pre-migration**
   - [ ] Export COA from source system
   - [ ] Export trial balance (for opening balances)
   - [ ] Export chart of accounts with tax codes
   - [ ] Archive unused accounts in source system [^245^]
   - [ ] Clean up duplicate or near-duplicate accounts
   - [ ] Verify account code consistency (leading zeros) [^242^]

2. **Mapping**
   - [ ] Auto-map accounts using name/code similarity
   - [ ] Review low-confidence mappings manually
   - [ ] Map source tax codes to system tax categories
   - [ ] Identify accounts requiring dimensional tracking

3. **Import**
   - [ ] Import COA structure first
   - [ ] Validate trial balance = zero after opening entries
   - [ ] Import opening balances
   - [ ] Import historical transactions (if applicable)

4. **Verification**
   - [ ] Compare source system P&L to new system
   - [ ] Compare source system Balance Sheet to new system
   - [ ] Verify bank reconciliation positions
   - [ ] Sign-off from accounting team

---

## 12. Account Lifecycle

### 12.1 Lifecycle States

| State | Description | Transactions Allowed? |
|-------|-------------|----------------------|
| `draft` | Account created but not yet active | No |
| `active` | Normal operational state | Yes |
| `restricted` | Account active but requires approval for postings | Conditional |
| `inactive` | Account hidden from selection but visible in reports | No (new) |
| `archived` | Account removed from COA view; historical data preserved | No |
| `merged` | Account merged into another; redirects to target | No |

### 12.2 Account Creation

```json
{
  "account_creation": {
    "workflow": "standard",
    "steps": [
      {
        "step": "propose",
        "actor": "accounting_user",
        "required_fields": ["coa_code", "name", "category", "subcategory", "account_type"],
        "optional_fields": ["parent_code", "tax_category", "description"]
      },
      {
        "step": "validate",
        "automated_checks": [
          "code_uniqueness",
          "code_range_validity",
          "parent_child_type_compatibility",
          "standard_eligibility_consistency"
        ]
      },
      {
        "step": "approve",
        "actor": "accounting_manager",
        "required": true
      },
      {
        "step": "activate",
        "automated": true,
        "side_effects": ["create_formance_account", "set_metadata_defaults"]
      }
    ]
  }
}
```

**Validation rules:**
- COA code must be unique across all entities
- COA code must fall within valid range for its category
- Parent and child must share the same `category`
- Maximum hierarchy depth: 2 levels [^434^]
- Cannot create account with code within 5 numbers of existing (enforces gaps)

### 12.3 Account Archiving

Archiving removes an account from active use while preserving historical data [^519^][^522^].

**Prerequisites for archiving:**
- Account balance must be zero [^516^]
- No open transactions (unreconciled items)
- Not referenced by active products/services
- Not a system account or default account [^519^]
- No active sub-accounts (must archive children first) [^516^]

**Archive process:**
```
1. Verify prerequisites
2. Move sub-accounts to new parent (if applicable)
3. Set is_active = false
4. Set is_archive_eligible = false
5. Set archived_at = now()
6. Set archived_by = current_user
7. Log archive event to audit trail
8. Hide from COA dropdowns and transaction entry
9. Preserve in financial statement history
```

### 12.4 Account Merging

Merging combines two accounts into one. This is **irreversible** [^517^][^519^].

**Merge rules:**
- Source and target must have the same `category` and `account_type`
- All historical transactions are re-attributed to the target account
- Source account enters `merged` state with `merged_into` pointer
- Merge journal entry transfers any remaining balance

**Merge process:**
```
Pre-merge:
  Account A (source): Balance = $500
  Account B (target): Balance = $2,000

Merge journal entry:
  Dr  Account B (target)         500
  Cr  Account A (source)         500

Post-merge:
  Account A: Status = merged, merged_into = Account B
  Account B: Balance = $2,500
  All historical transactions from Account A now show Account B
```

### 12.5 Account Lifecycle API

```json
{
  "account_lifecycle_event": {
    "account_id": "acc-1000",
    "from_state": "active",
    "to_state": "archived",
    "triggered_by": "user:acc_mgr_001",
    "triggered_at": "2024-06-15T10:30:00Z",
    "reason": "Account no longer needed; function consolidated into 6100",
    "prerequisites_check": {
      "balance_zero": true,
      "no_open_transactions": true,
      "no_active_subaccounts": true,
      "not_system_account": true
    },
    "reversible": false
  }
}
```

---

## 13. GL Data Model Specification

### 13.1 Entity Relationship Diagram (Logical)

```
+------------------+     +------------------+     +------------------+
|     Account      |     |   Transaction    |     |    Posting       |
+------------------+     +------------------+     +------------------+
| id (PK)          |<----| id (PK)          |     | id (PK)          |
| coa_code (UQ)    |     | reference (UQ)   |     | transaction_id   |
| name             |     | timestamp        |     | account_id (FK)  |
| category         |     | source_system    |---->| amount           |
| subcategory      |     | source_doc_id    |     | currency         |
| account_type     |     | status           |     | debit_credit     |
| parent_id (FK)   |     | total_amount     |     | fx_rate          |
| is_active        |     | fx_rate          |     | fx_amount        |
| is_control       |     | metadata (JSON)  |     | metadata (JSON)  |
| standard_flags   |     +------------------+     +------------------+
| metadata (JSON)  |
| formance_address |
+------------------+
         |
         | 1:N
         v
+------------------+     +------------------+     +------------------+
| AccountBalance   |     | TrackingCategory |     |  MigrationJob    |
+------------------+     +------------------+     +------------------+
| id (PK)          |     | id (PK)          |     | id (PK)          |
| account_id (FK)  |     | name             |     | source_system    |
| period           |     | type             |     | status           |
| opening_balance  |     | is_active        |     | steps (JSON)     |
| closing_balance  |     +------------------+     | mappings (JSON)  |
| debits           |              |               | started_at       |
| credits          |              | 1:N            | completed_at     |
| currency         |              v               +------------------+
+------------------+     +------------------+
                         | TrackingValue    |
                         +------------------+
                         | id (PK)          |
                         | category_id (FK) |
                         | code             |
                         | name             |
                         | is_active        |
                         +------------------+
```

### 13.2 Account Entity

```sql
CREATE TABLE accounts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coa_code        VARCHAR(10) NOT NULL UNIQUE,
    name            VARCHAR(150) NOT NULL,
    category        account_category NOT NULL,  -- asset|liability|equity|revenue|expense|system
    subcategory     account_subcategory NOT NULL,
    account_type    account_type NOT NULL,       -- bank|receivable|payable|revenue|expense|equity|non_posting
    parent_id       UUID REFERENCES accounts(id),
    
    -- Standard support
    gaap_applicable BOOLEAN DEFAULT true,
    ifrs_applicable BOOLEAN DEFAULT true,
    sme_applicable  BOOLEAN DEFAULT true,
    
    -- Control flags
    is_control_account  BOOLEAN DEFAULT false,
    is_bank_account     BOOLEAN DEFAULT false,
    is_system_account   BOOLEAN DEFAULT false,
    is_active           BOOLEAN DEFAULT true,
    is_archive_eligible BOOLEAN DEFAULT false,
    
    -- Formance integration
    formance_address    VARCHAR(255) NOT NULL UNIQUE,
    
    -- Metadata
    metadata            JSONB DEFAULT '{}',
    
    -- Lifecycle
    status              account_status DEFAULT 'draft',  -- draft|active|restricted|inactive|archived|merged
    merged_into_id      UUID REFERENCES accounts(id),
    
    -- Audit
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),
    created_by          VARCHAR(50),
    updated_by          VARCHAR(50),
    version             INTEGER DEFAULT 1
);

-- Indexes
CREATE INDEX idx_accounts_category ON accounts(category);
CREATE INDEX idx_accounts_formance_address ON accounts(formance_address);
CREATE INDEX idx_accounts_parent ON accounts(parent_id);
CREATE INDEX idx_accounts_metadata ON accounts USING GIN (metadata);
```

### 13.3 Transaction Entity

```sql
CREATE TABLE transactions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reference       VARCHAR(100) NOT NULL UNIQUE,
    ledger_id       VARCHAR(50) NOT NULL DEFAULT 'main',
    
    -- Timing
    transaction_date    DATE NOT NULL,
    posting_date        DATE NOT NULL,
    fiscal_year         INTEGER NOT NULL,
    fiscal_period       INTEGER NOT NULL,
    
    -- Amounts
    total_amount        DECIMAL(18,4) NOT NULL,
    currency            VARCHAR(3) NOT NULL DEFAULT 'USD',
    
    -- Source tracking
    source_system       VARCHAR(50),      -- xero|quickbooks|manual|api
    source_document_id  VARCHAR(100),
    source_document_type VARCHAR(50),     -- invoice|bill|journal|payment
    
    -- Status
    status              transaction_status DEFAULT 'draft',  -- draft|pending|posted|reversed|voided
    
    -- Reversal
    reversal_of_id      UUID REFERENCES transactions(id),
    is_reversing_entry  BOOLEAN DEFAULT false,
    auto_reverse        BOOLEAN DEFAULT false,  -- Accruals reversed next period
    
    -- Migration
    migration_job_id    UUID,
    
    -- Metadata
    metadata            JSONB DEFAULT '{}',
    
    -- Audit
    created_at          TIMESTAMPTZ DEFAULT now(),
    posted_at           TIMESTAMPTZ,
    posted_by           VARCHAR(50),
    
    -- Constraint: Every transaction must have at least 2 postings
    CONSTRAINT check_positive_amount CHECK (total_amount >= 0)
);
```

### 13.4 Posting Entity (Formance-Compatible)

```sql
CREATE TABLE postings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id  UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
    
    -- Formance-style source/destination
    source          VARCHAR(255) NOT NULL,
    destination     VARCHAR(255) NOT NULL,
    
    -- Account reference (resolved from source/destination)
    source_account_id       UUID REFERENCES accounts(id),
    destination_account_id  UUID REFERENCES accounts(id),
    
    -- Amount
    amount          DECIMAL(18,4) NOT NULL,
    currency        VARCHAR(3) NOT NULL,
    
    -- FX
    fx_rate         DECIMAL(18,10) DEFAULT 1.0,
    fx_amount       DECIMAL(18,4),
    
    -- Dimensional tracking
    department      VARCHAR(50),
    location        VARCHAR(50),
    project         VARCHAR(50),
    cost_center     VARCHAR(50),
    
    -- Metadata
    metadata        JSONB DEFAULT '{}',
    
    -- Audit
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Constraint: Sum of all postings in a transaction must equal zero
-- Enforced at application level and via database trigger
```

### 13.5 Account Balance Entity

```sql
CREATE TABLE account_balances (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id      UUID NOT NULL REFERENCES accounts(id),
    
    -- Period
    fiscal_year     INTEGER NOT NULL,
    fiscal_period   INTEGER NOT NULL,  -- 1-12, plus 13=adjustments, 14=closing
    
    -- Balances
    opening_balance DECIMAL(18,4) DEFAULT 0,
    closing_balance DECIMAL(18,4) DEFAULT 0,
    period_debits   DECIMAL(18,4) DEFAULT 0,
    period_credits  DECIMAL(18,4) DEFAULT 0,
    
    -- Currency
    currency        VARCHAR(3) NOT NULL,
    
    -- Quantity (for unit-based accounts)
    opening_quantity DECIMAL(18,4),
    closing_quantity DECIMAL(18,4),
    
    UNIQUE(account_id, fiscal_year, fiscal_period, currency)
);
```

### 13.6 Double-Entry Invariant

The system enforces the fundamental double-entry invariant at multiple levels:

```
For every transaction: SUM(debits) = SUM(credits)
For every account:    Opening + Debits - Credits = Closing
For the ledger:       SUM(all account balances) = 0
```

Enforcement:
1. **Application level:** Transaction validation before persistence
2. **Database trigger:** `BEFORE INSERT` on postings verifies balance per transaction
3. **Periodic reconciliation:** Ledger integrity check compares sum of balances to zero

---

## 14. Implementation Guide

### 14.1 Setup Order

1. **Configure fiscal calendar** (year start, periods, adjustment period)
2. **Load base COA template** (universal accounts)
3. **Apply industry-specific extensions** (retail/service/SaaS/manufacturing/construction)
4. **Configure tracking categories** (departments, locations, projects)
5. **Configure tax regimes** (VAT/GST rates, control accounts)
6. **Set accounting standard** (GAAP/IFRS/SME presentation rules)
7. **Import opening balances** (from prior system)
8. **Verify trial balance** (must equal zero)
9. **Enable transaction processing**

### 14.2 Configuration Priority

| Priority | Task | Dependencies |
|----------|------|-------------|
| P0 | Fiscal calendar | None |
| P0 | Base COA template | Fiscal calendar |
| P0 | Tax regime config | Base COA |
| P1 | Industry extensions | Base COA |
| P1 | Tracking categories | Base COA |
| P1 | Standard selection | Base COA |
| P2 | Opening balances | All P0/P1 |
| P2 | User permissions | All P0 |
| P3 | Migration jobs | Opening balances |

### 14.3 Key Design Decisions Summary

| Decision | Choice | Authority |
|----------|--------|-----------|
| 4-digit vs 5-digit numbering | 4-digit with 10-point gaps | Best practice [^434^][^436^] |
| Dimensions in account numbers | No - external tracking categories | Prevents COA explosion [^435^] |
| Parent-child depth limit | 2 levels | NetSuite guidance [^434^] |
| VAT control account structure | 3-account (output/input/control) | HMRC/VAT digital best practice [^89^] |
| Suspense resolution SLA | 30 days | Accounting best practice [^431^] |
| Account merge reversibility | Irreversible | QuickBooks pattern [^517^] |
| Archive prerequisites | Zero balance, no open items | QuickBooks/Xero pattern [^516^] |
| Opening balance method | Opening Balance Equity account | Universal practice [^428^] |
| Formance path structure | `{type}:{entity}:{standard}:{code}:{detail}` | Adapted from Formance docs [^45^] |

---

## 15. References

| Citation | Source | Description |
|----------|--------|-------------|
| [^45^] | Formance Engineering Blog | Double-entry accounting for engineers; multi-segment account paths |
| [^89^] | PastPaperHero (ACCA) | VAT output/input tax postings and control account mechanics |
| [^177^] | Grant Thornton | IFRS vs US GAAP comparison guide |
| [^180^] | PwC Viewpoint | ASC 205 financial statement presentation requirements |
| [^239^] | Cloudvara | IIF file format complete guide |
| [^240^] | QuickBooks (Intuit) | Official IIF import kit documentation |
| [^242^] | SheetXAI | Xero chart of accounts CSV export fields and structure |
| [^245^] | Murray Nankivell | Xero chart of accounts transfer guide |
| [^246^] | IFRS Foundation | IAS 1 Presentation of Financial Statements |
| [^261^] | Knowify | Construction chart of accounts with percentage of completion |
| [^262^] | DualEntry | SaaS chart of accounts complete template |
| [^263^] | NetSuite | SaaS chart of accounts design guide |
| [^264^] | Ramp | Free chart of accounts template by industry |
| [^265^] | Planyard | Construction chart of accounts for Xero |
| [^268^] | VAT Digital | VAT accounting in P&L and balance sheet |
| [^405^] | NetSuite | Chart of accounts definition, best practices, examples |
| [^406^] | KPMG | IFRS compared to US GAAP 2024 handbook |
| [^407^] | PwC | IFRS and US GAAP similarities and differences |
| [^408^] | EY | US GAAP versus IFRS accounting standards |
| [^409^] | Breaking Into Wall Street | IFRS vs US GAAP on financial statements |
| [^410^] | Pearson | GAAP vs IFRS stockholders' equity summary |
| [^427^] | Numeric | Suspense account definition and matching principle |
| [^428^] | Sage 300 | General Ledger user's guide (opening balances) |
| [^429^] | Planyard | Xero tracking categories for contractors |
| [^430^] | HighRadius | Clearing accounts: examples, types, and benefits |
| [^431^] | Complete Controller | Suspense vs clearing accounts comparison |
| [^432^] | FHP Accounting | Xero projects and tracking categories guide |
| [^433^] | UC Davis Finance | Best practices for clearing, default, and suspense accounts |
| [^434^] | House Blend | NetSuite chart of accounts best practices |
| [^435^] | Rand Group | Chart of accounts structure best practices |
| [^436^] | Custom CPA | Chart of accounts setup foundation |
| [^437^] | Cube Software | Chart of accounts how it works |
| [^514^] | Numetrix AI | Chart of accounts for consulting profitability |
| [^516^] | QuickBooks Community | Making chart of accounts entries inactive |
| [^517^] | Keep Financial | How to merge chart of accounts in QuickBooks |
| [^518^] | ICMA International | IFRS for SMEs presentation |
| [^519^] | Ignite Spot | Clean chart of accounts for new year |
| [^520^] | Remote.com | Sample chart of accounts for service businesses |
| [^521^] | Milestone | Setting up chart of accounts for professional services |
| [^522^] | FreshBooks | Chart of accounts management guide |
| [^534^] | Formance GitHub | Open source infrastructure for financial internet |

---

*Document generated from comprehensive research including IFRS Foundation standards, FASB ASC guidance, Big 4 comparison publications, Formance technical documentation, Xero/QuickBooks operational patterns, and industry-specific accounting literature.*
