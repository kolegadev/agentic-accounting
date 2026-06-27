# Dimension 03: Transaction Processing & Numscript Generation

## Executive Summary

This document designs a comprehensive transaction processing architecture for an AI-native accounting system built on Formance's Numscript DSL. The architecture spans pre-built Numscript templates for 50+ SME transaction types, an LLM-to-Numscript generation pipeline with structured output validation, multi-line transaction handling for complex scenarios (payroll, VAT settlement), immutable ledger correction workflows, and enterprise-grade features including idempotency, bulk processing, and transaction status lifecycle management.

Research by Weber et al. (2025) demonstrates that LLMs achieve only **8.33% accuracy** generating correct double-entry transactions without guidance, but this improves dramatically with structured patterns, few-shot examples, and constrained decoding [^76^][^412^]. This architecture addresses that gap through deterministic validation layers, template-based generation, and multi-stage verification.

---

## Table of Contents

1. [Numscript Template Library](#1-numscript-template-library)
2. [Transaction Type Taxonomy](#2-transaction-type-taxonomy)
3. [LLM-to-Numscript Pipeline](#3-llm-to-numscript-pipeline)
4. [Multi-Line Transactions](#4-multi-line-transactions)
5. [Metadata Attachment Schema](#5-metadata-attachment-schema)
6. [Transaction Validation Layer](#6-transaction-validation-layer)
7. [Correction Workflow (Immutable Ledger)](#7-correction-workflow)
8. [Bulk Transactions](#8-bulk-transactions)
9. [Transaction Status Lifecycle](#9-transaction-status-lifecycle)
10. [Idempotency Design](#10-idempotency-design)

---

## 1. Numscript Template Library

### 1.1 Foundation: Numscript DSL Overview

Numscript is a domain-specific language purpose-built for financial transactions within the Formance ledger. It provides atomic, multi-posting transactions with deterministic integer math (no floating-point rounding errors) [^200^][^228^].

**Core Syntax Pattern:**
```numscript
send [ASSET/SCALE AMOUNT] (
  source = @account
  destination = @target
)
```

**Key Language Features:** [^232^][^233^][^235^]
- **Asset notation**: `USD/2` means USD with 2 decimal places (cents); `BTC/8` means 8 decimal places (satoshis)
- **Variables**: `vars { monetary $amount; account $dest; portion $pct }` for reusable templates
- **Split destinations**: Distribute to multiple accounts with percentages or fractions
- **Ordered sources**: Pull from multiple accounts with fallback ordering and caps (`max`)
- **Overdraft controls**: `allowing overdraft up to [USD/2 100]` or `allowing unbounded overdraft`
- **Metadata**: `set_tx_meta("key", value)` and `set_account_meta(@acc, "key", value)` for attaching business context
- **Save statement**: `save [USD/2 100] from @account` earmarks funds without moving them
- **Account interpolation**: `@user:$id:pending` dynamically resolves account names
- **Remainder handling**: `remaining` keyword ensures deterministic allocation of indivisible amounts

**Atomicity Guarantee**: Each Numscript execution produces either all postings or none. If any constraint fails (insufficient balance, invalid account), the entire transaction is rejected [^200^].

### 1.2 Template: Sales Invoice

```numscript
// Template: SALES_INVOICE
// Records revenue from sale of goods/services on credit
// Variables: $amount, $customer, $invoice_ref, $tax_rate

vars {
  monetary $amount
  account $customer
  string $invoice_ref
  portion $tax_rate
}

// Record revenue (net of tax) and tax liability
send $amount (
  source = @world
  destination = {
    $tax_rate to @liabilities:tax:sales_tax
    remaining to @revenue:sales
  }
)

// Record accounts receivable from customer
send $amount (
  source = @world
  destination = $customer
)

// Metadata attachment
set_tx_meta("type", "SALES_INVOICE")
set_tx_meta("invoice_ref", $invoice_ref)
set_tx_meta("customer", $customer)
set_tx_meta("tax_rate", $tax_rate)
set_tx_meta("gross_amount", $amount)
```

**Execution Example:**
```json
{
  "script": {
    "plain": "// SALES_INVOICE template...",
    "vars": {
      "amount": "USD/2 59900",
      "customer": "customers:acme_corp",
      "invoice_ref": "INV-2024-0042",
      "tax_rate": "20/100"
    }
  },
  "timestamp": "2024-06-15T00:00:00Z"
}
```

### 1.3 Template: Purchase Bill

```numscript
// Template: PURCHASE_BILL
// Records expense from purchase of goods/services on credit
// Variables: $amount, $vendor, $bill_ref, $expense_category

vars {
  monetary $amount
  account $vendor
  string $bill_ref
  account $expense_category
  portion $tax_rate
}

send $amount (
  source = {
    $tax_rate from @liabilities:tax:input_tax
    remaining from $expense_category
  }
  destination = $vendor
)

set_tx_meta("type", "PURCHASE_BILL")
set_tx_meta("bill_ref", $bill_ref)
set_tx_meta("vendor", $vendor)
set_tx_meta("expense_category", $expense_category)
```

### 1.4 Template: Payment (Outgoing)

```numscript
// Template: PAYMENT_OUT
// Records payment to a vendor/supplier
// Variables: $amount, $vendor, $payment_ref, $bank_account

vars {
  monetary $amount
  account $vendor
  string $payment_ref
  account $bank_account
}

send $amount (
  source = $bank_account
  destination = @world
)

send $amount (
  source = $vendor
  destination = @world
)

set_tx_meta("type", "PAYMENT_OUT")
set_tx_meta("payment_ref", $payment_ref)
set_tx_meta("vendor", $vendor)
set_tx_meta("bank_account", $bank_account)
```

### 1.5 Template: Receipt (Incoming Payment)

```numscript
// Template: RECEIPT_IN
// Records payment received from a customer
// Variables: $amount, $customer, $receipt_ref, $bank_account

vars {
  monetary $amount
  account $customer
  string $receipt_ref
  account $bank_account
}

send $amount (
  source = $customer
  destination = @world
)

send $amount (
  source = @world
  destination = $bank_account
)

set_tx_meta("type", "RECEIPT_IN")
set_tx_meta("receipt_ref", $receipt_ref)
set_tx_meta("customer", $customer)
set_tx_meta("bank_account", $bank_account)
```

### 1.6 Template: Expense (Cash Basis)

```numscript
// Template: EXPENSE_CASH
// Records immediate cash expense
// Variables: $amount, $expense_category, $bank_account, $description

vars {
  monetary $amount
  account $expense_category
  account $bank_account
  string $description
}

send $amount (
  source = $bank_account
  destination = @world
)

send $amount (
  source = @world
  destination = $expense_category
)

set_tx_meta("type", "EXPENSE_CASH")
set_tx_meta("description", $description)
set_tx_meta("expense_category", $expense_category)
```

### 1.7 Template: Journal Entry (Internal Transfer)

```numscript
// Template: JOURNAL_ENTRY
// General purpose double-entry adjustment
// Variables: $amount, $debit_account, $credit_account, $description

vars {
  monetary $amount
  account $debit_account
  account $credit_account
  string $description
}

send $amount (
  source = $credit_account
  destination = $debit_account
)

set_tx_meta("type", "JOURNAL_ENTRY")
set_tx_meta("description", $description)
```

### 1.8 Template: Currency Exchange / Multi-Currency

```numscript
// Template: CURRENCY_EXCHANGE
// Records conversion between currencies
// Variables: $from_amount, $to_amount, $fx_rate, $bank_account

vars {
  monetary $from_amount
  monetary $to_amount
  string $fx_rate
  account $bank_account
}

// Remove source currency from bank
send $from_amount (
  source = $bank_account
  destination = @world
)

// Add target currency to bank
send $to_amount (
  source = @world
  destination = $bank_account
)

// Record exchange gain/loss
vars {
  monetary $difference
}

set_tx_meta("type", "CURRENCY_EXCHANGE")
set_tx_meta("fx_rate", $fx_rate)
set_tx_meta("from_amount", $from_amount)
set_tx_meta("to_amount", $to_amount)
```

### 1.9 Template: VAT/GST Settlement

```numscript
// Template: TAX_SETTLEMENT
// Remits collected tax to tax authority
// Variables: $amount, $tax_period, $tax_authority, $bank_account

vars {
  monetary $amount
  string $tax_period
  account $bank_account
}

// Pay output tax (sales tax collected)
send $amount (
  source = @liabilities:tax:sales_tax
  destination = @world
)

// Receive input tax credit (purchases tax paid)
send [USD/2 *] (
  source = @world
  destination = @liabilities:tax:input_tax
)

// Net remittance from bank
send $amount (
  source = $bank_account
  destination = @world
)

set_tx_meta("type", "TAX_SETTLEMENT")
set_tx_meta("tax_period", $tax_period)
```

### 1.10 Template: Owner Draw / Dividend

```numscript
// Template: OWNER_DRAW
// Records owner withdrawal or dividend distribution
// Variables: $amount, $owner_account, $bank_account

vars {
  monetary $amount
  account $owner_account
  account $bank_account
}

send $amount (
  source = $bank_account
  destination = @world
)

send $amount (
  source = @equity:retained_earnings
  destination = $owner_account
)

set_tx_meta("type", "OWNER_DRAW")
set_tx_meta("owner", $owner_account)
```

### 1.11 Template: Bank Transfer Between Accounts

```numscript
// Template: BANK_TRANSFER
// Internal transfer between two bank accounts
// Variables: $amount, $from_bank, $to_bank, $reference

vars {
  monetary $amount
  account $from_bank
  account $to_bank
  string $reference
}

send $amount (
  source = $from_bank
  destination = $to_bank
)

set_tx_meta("type", "BANK_TRANSFER")
set_tx_meta("reference", $reference)
```

### 1.12 Template: Deferred Revenue Recognition

```numscript
// Template: REVENUE_RECOGNITION
// Recognize deferred revenue when performance obligation met
// Variables: $amount, $contract, $revenue_period

vars {
  monetary $amount
  string $contract
  string $revenue_period
}

send $amount (
  source = @liabilities:deferred_revenue
  destination = @revenue:service
)

set_tx_meta("type", "REVENUE_RECOGNITION")
set_tx_meta("contract", $contract)
set_tx_meta("revenue_period", $revenue_period)
```

### 1.13 Template: Bad Debt Write-off

```numscript
// Template: BAD_DEBT_WRITE_OFF
// Write off uncollectible receivable
// Variables: $amount, $customer, $allowance_account

vars {
  monetary $amount
  account $customer
  string $reason
}

send $amount (
  source = @assets:allowance_doubtful_accounts
  destination = @world
)

send $amount (
  source = $customer
  destination = @world
)

set_tx_meta("type", "BAD_DEBT_WRITE_OFF")
set_tx_meta("customer", $customer)
set_tx_meta("reason", $reason)
```

### 1.14 Template: Prepayment Amortization

```numscript
// Template: PREPAYMENT_AMORTIZATION
// Recognize portion of prepaid expense
// Variables: $amount, $expense_category, $prepayment_account

vars {
  monetary $amount
  account $expense_category
  string $period
}

send $amount (
  source = @assets:prepayments
  destination = $expense_category
)

set_tx_meta("type", "PREPAYMENT_AMORTIZATION")
set_tx_meta("period", $period)
```

### 1.15 Template: Inventory Adjustment

```numscript
// Template: INVENTORY_ADJUSTMENT
// Adjust inventory for shrinkage/damage/count
// Variables: $amount, $adjustment_type, $inventory_account

vars {
  monetary $amount
  string $adjustment_type
  account $inventory_account
  string $reason
}

send $amount (
  source = $inventory_account
  destination = @expenses:inventory_adjustment
)

set_tx_meta("type", "INVENTORY_ADJUSTMENT")
set_tx_meta("adjustment_type", $adjustment_type)
set_tx_meta("reason", $reason)
```

---

## 2. Transaction Type Taxonomy

### 2.1 Complete SME Transaction Type Catalog (50+ Types)

Based on analysis of common small business accounting requirements across GAAP and IFRS frameworks [^257^][^258^][^261^][^359^][^364^], the following taxonomy categorizes all transaction types an SME requires:

#### 2.1.1 Revenue Transactions (Types 01-12)

| Code | Type | Description | Numscript Template | Debit | Credit |
|------|------|-------------|-------------------|-------|--------|
| `SALE_INV` | Sales Invoice | Credit sale of goods/services | `SALES_INVOICE` | AR, Tax Liability | Revenue |
| `SALE_CSH` | Cash Sale | Immediate cash sale | `SALES_INVOICE` + `RECEIPT_IN` | Cash, Tax Liab | Revenue |
| `SALE_RET` | Sales Return | Customer return/credit note | `SALES_REVERSAL` | Revenue, Tax Liab | AR |
| `SALE_DIS` | Sales Discount | Early payment discount given | `JOURNAL_ENTRY` | Revenue | AR |
| `SALE_DEP` | Customer Deposit | Advance payment received | `RECEIPT_IN` (modified) | Cash | Deferred Revenue |
| `SALE_REC` | Revenue Recognition | Recognize deferred revenue | `REVENUE_RECOGNITION` | Deferred Rev | Revenue |
| `INT_INC` | Interest Income | Bank interest earned | `JOURNAL_ENTRY` | Cash | Interest Revenue |
| `ROY_INC` | Royalty Income | Licensing fees received | `RECEIPT_IN` | Cash | Royalty Revenue |
| `COM_INC` | Commission Income | Agent/broker fees | `SALES_INVOICE` | AR | Commission Rev |
| `SUB_INC` | Subscription Income | Recurring subscription billing | `SALES_INVOICE` | AR | Subscription Rev |
| `MISC_INC` | Miscellaneous Income | Other operating income | `RECEIPT_IN` | Cash | Other Income |
| `GAIN_FX` | Foreign Exchange Gain | FX revaluation gain | `JOURNAL_ENTRY` | FX Gain Asset | FX Gain Income |

#### 2.1.2 Expense Transactions (Types 13-28)

| Code | Type | Description | Numscript Template |
|------|------|-------------|-------------------|
| `EXP_COGS` | Cost of Goods Sold | Direct costs of goods sold | `JOURNAL_ENTRY` |
| `EXP_PUR` | Purchase Bill | Credit purchase of goods | `PURCHASE_BILL` |
| `EXP_CSH` | Cash Expense | Immediate cash payment | `EXPENSE_CASH` |
| `EXP_PAY` | Bill Payment | Pay outstanding AP bill | `PAYMENT_OUT` |
| `EXP_RENT` | Rent Expense | Office/warehouse rent | `EXPENSE_CASH` |
| `EXP_SAL` | Salary/Wages | Gross payroll expense | `PAYROLL_GROSS` |
| `EXP_TAX` | Employer Tax | Payroll tax expense | `PAYROLL_EMPLOYER_TAX` |
| `EXP_BEN` | Benefits | Employee benefits | `PAYROLL_BENEFITS` |
| `EXP_UTL` | Utilities | Electricity, water, gas | `EXPENSE_CASH` |
| `EXP_INS` | Insurance | Business insurance | `EXPENSE_CASH` |
| `EXP_DEP` | Depreciation | Asset depreciation | `DEPRECIATION` |
| `EXP_MKT` | Marketing | Advertising, promotion | `EXPENSE_CASH` |
| `EXP_PRO` | Professional Fees | Legal, accounting, consulting | `EXPENSE_CASH` |
| `EXP_TRV` | Travel & Entertainment | Business travel, meals | `EXPENSE_CASH` |
| `EXP_OFF` | Office Supplies | Stationery, supplies | `EXPENSE_CASH` |
| `EXP_IT` | IT & Software | Software licenses, hosting | `EXPENSE_CASH` |

#### 2.1.3 Asset Transactions (Types 29-36)

| Code | Type | Description | Numscript Template |
|------|------|-------------|-------------------|
| `AST_PUR` | Asset Purchase | Capital equipment purchase | `PURCHASE_BILL` |
| `AST_DEP` | Depreciation | Periodic depreciation charge | `DEPRECIATION` |
| `AST_DSP` | Asset Disposal | Sale or retirement of asset | `ASSET_DISPOSAL` |
| `AST_INT` | Asset Impairment | Write-down of asset value | `JOURNAL_ENTRY` |
| `AST_INV` | Inventory Purchase | Stock/inventory acquisition | `PURCHASE_BILL` |
| `AST_ADJ` | Inventory Adjustment | Shrinkage, damage, count adj | `INVENTORY_ADJUSTMENT` |
| `AST_FX` | Fixed Asset Addition | Add to capital asset value | `JOURNAL_ENTRY` |
| `AST_PRE` | Prepayment | Prepaid expense recorded | `EXPENSE_CASH` (modified) |

#### 2.1.4 Liability Transactions (Types 37-44)

| Code | Type | Description | Numscript Template |
|------|------|-------------|-------------------|
| `LIAB_LOAN` | Loan Drawdown | Receive loan funds | `RECEIPT_IN` (modified) |
| `LIAB_LREP` | Loan Repayment | Repay loan principal | `PAYMENT_OUT` (modified) |
| `LIAB_LINT` | Loan Interest | Pay loan interest | `PAYMENT_OUT` |
| `LIAB_CC` | Credit Card Charge | Business card purchase | `EXPENSE_CASH` |
| `LIAB_CCP` | Credit Card Payment | Pay card balance | `PAYMENT_OUT` |
| `LIAB_ACC` | Accrual | Record unpaid expense | `JOURNAL_ENTRY` |
| `LIAB_TAX` | Tax Settlement | Remit VAT/GST/sales tax | `TAX_SETTLEMENT` |
| `LIAB_WTH` | Tax Withholding | Payroll tax remittance | `PAYMENT_OUT` (modified) |

#### 2.1.5 Equity Transactions (Types 45-50)

| Code | Type | Description | Numscript Template |
|------|------|-------------|-------------------|
| `EQ_INV` | Owner Investment | Capital injection | `RECEIPT_IN` (modified) |
| `EQ_DRW` | Owner Draw | Personal withdrawal | `OWNER_DRAW` |
| `EQ_DIV` | Dividend | Shareholder distribution | `OWNER_DRAW` (modified) |
| `EQ_RET` | Retained Earnings | Year-end close entry | `JOURNAL_ENTRY` |
| `EQ_FX` | Equity FX Adjustment | Currency translation adj | `JOURNAL_ENTRY` |
| `EQ_ADJ` | Equity Adjustment | Correction to equity | `JOURNAL_ENTRY` |

#### 2.1.6 Bank & Cash Transactions (Types 51-55)

| Code | Type | Description | Numscript Template |
|------|------|-------------|-------------------|
| `BNK_TFR` | Bank Transfer | Between bank accounts | `BANK_TRANSFER` |
| `BNK_DEP` | Bank Deposit | Cash/cheque deposit | `JOURNAL_ENTRY` |
| `BNK_FEE` | Bank Fees | Account charges | `EXPENSE_CASH` |
| `BNK_INT` | Bank Interest | Interest earned | `JOURNAL_ENTRY` |
| `BNK_FX` | Currency Exchange | FX conversion | `CURRENCY_EXCHANGE` |

#### 2.1.7 Correction Transactions (Types 56-60)

| Code | Type | Description | Numscript Template |
|------|------|-------------|-------------------|
| `COR_REV` | Reversal | Reverse incorrect entry | `REVERSAL` (compensating) |
| `COR_ADJ` | Adjustment | Correcting journal entry | `JOURNAL_ENTRY` |
| `COR_WOF` | Bad Debt Write-off | Uncollectible AR | `BAD_DEBT_WRITE_OFF` |
| `COR_REA` | Reallocation | Reclass between accounts | `JOURNAL_ENTRY` |
| `COR_YE` | Year-End Close | Closing entries | `JOURNAL_ENTRY` (batch) |

---

## 3. LLM to Numscript Pipeline

### 3.1 Problem Statement

Research demonstrates that LLMs perform poorly at generating correct double-entry transactions from scratch. Weber et al. (2025) found that across multiple models (CodeLlama, CodeQwen, Mistral, Llama 3, Qwen 2), **only 8.33% of generated transactions were fully correct** (balanced, syntactically valid, semantically consistent) without guidance [^412^]. Error distribution: 40% missing transactions, 23.33% balance errors, 17.67% unknown accounts, 10.67% semantically inconsistent despite compiling [^412^].

However, accuracy improves dramatically with structured approaches. The pipeline below implements a multi-stage architecture combining LLM generation with deterministic validation.

### 3.2 Pipeline Architecture

```
Stage 1: INTENT CLASSIFICATION         Stage 2: PARAMETER EXTRACTION
+------------------------+              +---------------------------+
| User Input (NL/Doc)    |  -------->  | Extract: amount, accounts,|
| "Record $500 invoice   |              | dates, vendor, line items |
|  from Acme for widgets"|              | tax, currency, references |
+------------------------+              +---------------------------+
          |                                         |
          v                                         v
+------------------------+              +---------------------------+
| Classify to:           |              | LLM with structured output|
| tx_type: SALE_INV      |  <---------- | (JSON Schema constrained) |
| template: SALES_INVOICE|              |                           |
| confidence: 0.97       |              | Output:                   |
+------------------------+              | { "amount": "USD/2 50000",|
                                        |   "customer": "acme",     |
                                        |   "tax_rate": "0.20" }    |
                                        +---------------------------+
          |                                         |
          v                                         v
Stage 3: TEMPLATE POPULATION           Stage 4: DETERMINISTIC VALIDATION
+---------------------------+          +-------------------------------+
| Match template from       |          | 1. Schema validation (JSON)   |
| template library          |          | 2. Account existence check    |
| Fill variable slots with  |  ----->  | 3. Balance check (debits=credits)
| extracted parameters      |          | 4. Period lock check          |
|                           |          | 5. Duplicate detection        |
| Produce Numscript AST     |          | 6. Constraint compliance      |
+---------------------------+          +-------------------------------+
                                                    |
          +-----------------------------------------+
          v
Stage 5: EXECUTION                     Stage 6: CONFIRMATION
+---------------------------+          +-------------------------------+
| Submit to Formance Ledger |          | Record tx_id, status, hash    |
| with idempotency key      |  ----->  | Update status: POSTED         |
| and timestamp             |          | Return to user with ref       |
+---------------------------+          +-------------------------------+
```

### 3.3 Stage 1: Intent Classification

**Input**: User natural language (e.g., "I paid $1200 rent for July")
**Output**: `TransactionIntent` object with:
- `tx_type_code`: One of the 60 type codes from the taxonomy
- `template_id`: Reference to template library
- `confidence`: Classification confidence score
- `primary_accounts`: Predicted accounts involved

**Implementation**: Fine-tuned classifier or few-shot prompt with the taxonomy as context. Use structured output with constrained decoding to guarantee valid type codes [^358^][^39^].

### 3.4 Stage 2: Parameter Extraction

**Input**: Raw user text + classified intent
**Output**: Structured parameters as JSON Schema:

```json
{
  "amount": { "value": 120000, "currency": "USD", "scale": 2 },
  "accounts": {
    "source": "assets:bank:checking",
    "destination": "expenses:rent"
  },
  "date": "2024-07-01",
  "description": "July office rent",
  "reference": "",
  "metadata": {
    "vendor": "ABC Properties",
    "period": "2024-07"
  }
}
```

**LLM Pattern**: Use function calling or structured output APIs (OpenAI `response_format`, Anthropic tool use) with JSON Schema constraints to guarantee parseable output [^358^][^360^].

### 3.5 Stage 3: Template Population

The template engine takes the classified intent and extracted parameters:

1. **Template lookup**: Resolve `template_id` to Numscript template from library
2. **Variable binding**: Map extracted parameters to template variables
3. **Account resolution**: Map natural language account names to chart of accounts codes
4. **Numscript generation**: Produce complete Numscript with all variables substituted

**Example**:
```
Input:  "Record $500 invoice from Acme for widgets plus 20% VAT"
Intent:  SALE_INV (confidence: 0.97)
Params:  amount=USD/2 60000, net=USD/2 50000, tax=USD/2 10000
         customer=customers:acme_corp, tax_rate=20/100
Output:  Populated SALES_INVOICE template Numscript
```

### 3.6 Stage 4: Deterministic Validation (Critical Layer)

This layer is **non-negotiable** for financial correctness. It catches the 91.67% of errors that LLMs produce [^412^].

**Validation Rules:**

| Check | Description | Failure Action |
|-------|-------------|----------------|
| **Schema Validation** | JSON conforms to expected parameter schema | Reject with detailed error |
| **Account Existence** | All `@account` references exist in COA | Suggest closest match or flag for review |
| **Balance Check** | Sum of all debits equals sum of all credits | Reject — financial invariant |
| **Period Lock** | Transaction date is in an open period | Reject or route to next open period |
| **Duplicate Detection** | Idempotency key not seen before | Return existing transaction |
| **Constraint Check** | No overdraft on non-overdraft accounts | Reject or flag for approval |
| **Tax Consistency** | Tax amount = rate * net amount | Reject with recalculated amount |
| **Currency Consistency** | All amounts in posting use same asset code | Reject with correction |
| **Reference Uniqueness** | Invoice/bill reference not already used | Flag as potential duplicate |

### 3.7 Stage 5: Execution

Submit validated Numscript to Formance Ledger API with:
- `Idempotency-Key` header for duplicate prevention [^366^]
- `timestamp` field for bi-temporal recording (business effective date vs. system date) [^260^]
- `metadata` for full audit context
- `reference` for external document linking

### 3.8 Stage 6: Confirmation

Record execution result:
- Transaction ID from Formance
- Status (POSTED, FAILED, PENDING)
- Ledger hash / log ID
- All metadata indexed for search

### 3.9 LLM Accuracy Improvement Strategies

Based on research findings [^76^][^412^]:

| Strategy | Impact | Implementation |
|----------|--------|----------------|
| Chain-of-Thought prompting | +15-20% accuracy | Force step-by-step reasoning before output |
| Few-shot examples (3-5) | +25-30% accuracy | Include correct examples in prompt context |
| Constrained decoding (JSON Schema) | +20% valid output | Use structured output APIs |
| Template-based generation | +40% accuracy | Reduce degrees of freedom to variable filling |
| Multi-stage validation | Catches 91%+ errors | Deterministic validation layer as safety net |
| Fine-tuned model | +30-40% accuracy | Train on domain-specific transaction corpus |

---

## 4. Multi-Line Transactions

### 4.1 Concept

Multi-line (compound) transactions involve more than two accounts and represent complex financial events. In Numscript, these are naturally handled through split sources, split destinations, or multiple sequential `send` statements within a single script [^200^][^234^].

### 4.2 Payroll Journal Entry (Complex Multi-Line)

Payroll is one of the most complex recurring transactions, typically requiring 3 separate journal entries with 6-10 lines each [^359^][^360^][^365^].

**Entry 1: Gross Wages and Withholdings** [^365^]
```numscript
// PAYROLL_GROSS — Record gross pay and all withholdings
// For: $12,000 gross, $1,200 FIT, $480 SIT, $918 FICA, $600 401k, $180 health

send [USD/2 1200000] (
  source = @world
  destination = {
    // Debits (expenses)
    @expenses:salaries:wages
  }
)

// Credits (liabilities for withholdings)
send [USD/2 120000] ( source = @world  destination = @liabilities:payroll:fit )
send [USD/2 48000]  ( source = @world  destination = @liabilities:payroll:sit )
send [USD/2 91800]  ( source = @world  destination = @liabilities:payroll:fica_employee )
send [USD/2 60000]  ( source = @world  destination = @liabilities:benefits:401k )
send [USD/2 18000]  ( source = @world  destination = @liabilities:benefits:health )
send [USD/2 862200] ( source = @world  destination = @liabilities:payroll:net_pay )

set_tx_meta("type", "PAYROLL_GROSS")
set_tx_meta("pay_period", "2024-W26")
set_tx_meta("gross_pay", "USD/2 1200000")
set_tx_meta("employee_count", "12")
```

**Entry 2: Employer Payroll Taxes** [^360^][^365^]
```numscript
// PAYROLL_EMPLOYER_TAX — Record employer tax obligations
// FICA match $918, FUTA $60, SUTA $270 = $1,095

send [USD/2 109500] (
  source = @world
  destination = @expenses:payroll_taxes
)

send [USD/2 91800] ( source = @world  destination = @liabilities:payroll:fica_employer )
send [USD/2 6000]  ( source = @world  destination = @liabilities:payroll:futa )
send [USD/2 27000] ( source = @world  destination = @liabilities:payroll:suta )

set_tx_meta("type", "PAYROLL_EMPLOYER_TAX")
set_tx_meta("pay_period", "2024-W26")
```

**Entry 3: Net Pay Disbursement**
```numscript
// PAYROLL_DISBURSEMENT — Pay employees and remit liabilities

// Pay net wages
send [USD/2 862200] (
  source = @liabilities:payroll:net_pay
  destination = @assets:bank:payroll
)

// Remit FICA (employee + employer)
send [USD/2 183600] (
  source = @liabilities:payroll:fica_employee
  destination = @assets:bank:payroll
)
send [USD/2 91800] (
  source = @liabilities:payroll:fica_employer
  destination = @assets:bank:payroll
)

// Remit income taxes
send [USD/2 120000] (
  source = @liabilities:payroll:fit
  destination = @assets:bank:payroll
)
send [USD/2 48000] (
  source = @liabilities:payroll:sit
  destination = @assets:bank:payroll
)

// Remit benefits
send [USD/2 60000] (
  source = @liabilities:benefits:401k
  destination = @assets:bank:payroll
)
send [USD/2 18000] (
  source = @liabilities:benefits:health
  destination = @assets:bank:payroll
)

set_tx_meta("type", "PAYROLL_DISBURSEMENT")
set_tx_meta("pay_period", "2024-W26")
```

### 4.3 VAT/GST Settlement (Multi-Line Tax)

```numscript
// TAX_SETTLEMENT — Monthly VAT remittance
// Output VAT collected: $8,500
// Input VAT paid: $3,200
// Net payable: $5,300

vars {
  monetary $output_vat
  monetary $input_vat
  monetary $net_payable
  string $tax_period
  account $bank_account
}

// Reduce output VAT liability
send $output_vat (
  source = @liabilities:tax:output_vat
  destination = @world
)

// Reduce input VAT asset (credit)
send $input_vat (
  source = @world
  destination = @assets:tax:input_vat
)

// Pay net amount to tax authority
send $net_payable (
  source = $bank_account
  destination = @world
)

set_tx_meta("type", "TAX_SETTLEMENT")
set_tx_meta("tax_period", $tax_period)
set_tx_meta("output_vat", $output_vat)
set_tx_meta("input_vat", $input_vat)
set_tx_meta("net_payable", $net_payable)
```

### 4.4 Marketplace Payment Split (Multi-Party)

Following Formance's rideshare marketplace pattern [^200^][^234^]:

```numscript
// MARKETPLACE_SETTLEMENT — Split payment between merchant, platform, delivery

vars {
  monetary $order_total
  portion $platform_fee_pct
  portion $delivery_fee_pct
  account $merchant
  account $delivery_partner
  string $order_id
}

send $order_total (
  source = @escrow:orders:$order_id
  destination = {
    $platform_fee_pct to @revenue:platform_fees
    $delivery_fee_pct to @liabilities:delivery_payouts
    remaining to @liabilities:merchant_payouts:$merchant
  }
)

set_tx_meta("type", "MARKETPLACE_SETTLEMENT")
set_tx_meta("order_id", $order_id)
set_tx_meta("merchant", $merchant)
set_tx_meta("delivery_partner", $delivery_partner)
```

### 4.5 Multi-Currency Settlement

```numscript
// MULTI_CURRENCY_SETTLEMENT — Pay EUR invoice from USD account

vars {
  monetary $eur_amount      // Amount owed: EUR 10,000
  monetary $usd_equivalent  // USD cost: ~$10,800
  string   $fx_rate         // 1.0800
  account  $vendor          // EUR supplier
  account  $bank_usd        // USD operating account
}

// Record USD outflow from bank
send $usd_equivalent (
  source = $bank_usd
  destination = @world
)

// Record EUR payable settlement
send $eur_amount (
  source = @liabilities:accounts_payable:$vendor
  destination = @world
)

// Record FX gain/loss
set_tx_meta("type", "MULTI_CURRENCY_PAYMENT")
set_tx_meta("fx_rate", $fx_rate)
set_tx_meta("usd_amount", $usd_equivalent)
set_tx_meta("eur_amount", $eur_amount)
```

---

## 5. Metadata Attachment Schema

### 5.1 Design Principles

Formance supports rich metadata on both transactions (`set_tx_meta`) and accounts (`set_account_meta`) [^386^][^260^]. Metadata can be any type: strings, numbers, monetary values, portions, or even account references. This enables powerful querying, reporting, and integration.

### 5.2 Standard Metadata Schema by Transaction Type

All transactions carry **core metadata**:

```json
{
  "tx_meta": {
    "type": "SALE_INV",
    "type_description": "Sales Invoice",
    "status": "POSTED",
    "reference": "INV-2024-0042",
    "description": "Widget sale to Acme Corp",
    "created_by": "agent:llm:v2.1",
    "source": "api",
    "idempotency_key": "ik_sale_inv_2024_0042_acme",
    "external_refs": ["quote:Q-2024-0099"],
    "bi_temporal": {
      "transaction_time": "2024-06-15T00:00:00Z",
      "request_time": "2024-06-15T14:32:18Z"
    }
  }
}
```

### 5.3 Type-Specific Metadata

| Transaction Type | Specific Metadata Fields | Purpose |
|-----------------|------------------------|---------|
| `SALE_INV` | `customer_id`, `invoice_ref`, `due_date`, `line_items`, `tax_breakdown` | AR tracking, dunning |
| `PURCHASE_BILL` | `vendor_id`, `bill_ref`, `due_date`, `po_ref`, `approval_status` | AP tracking, approval workflow |
| `PAYROLL_GROSS` | `pay_period`, `employee_count`, `gross_total`, `department_split` | Cost center allocation |
| `TAX_SETTLEMENT` | `tax_period`, `tax_authority`, `output_tax`, `input_tax`, `filing_ref` | Tax compliance |
| `BANK_TRANSFER` | `from_account`, `to_account`, `transfer_ref`, `bank_batch_id` | Reconciliation |
| `EXPENSE_CASH` | `vendor`, `expense_category`, `receipt_ref`, `budget_code` | Expense analysis |
| `JOURNAL_ENTRY` | `adjustment_type`, `period`, `reversing_entry_ref`, `approver` | Audit trail |
| `DEPRECIATION` | `asset_id`, `depreciation_method`, `useful_life`, `period` | Asset tracking |

### 5.4 Metadata-Driven Account Resolution

Numscript can read account metadata at runtime using the `meta()` function [^386^]:

```numscript
// Resolve payout account from order metadata
vars {
  account $order = @orders:1234
  account $payout_account = meta($order, "payout_account")
  monetary $amount
}

send $amount (
  source = @escrow:orders:1234
  destination = $payout_account
)
```

This enables **metadata-driven routing** where business rules are encoded in account metadata rather than hardcoded in templates.

### 5.5 Query Patterns Using Metadata

```sql
-- Find all uncollected receivables for a customer
SELECT * FROM transactions
WHERE metadata->>'type' = 'SALE_INV'
  AND metadata->>'customer_id' = 'acme_corp'
  AND metadata->>'status' = 'OUTSTANDING'

-- Calculate total payroll by department
SELECT 
  metadata->>'department' as dept,
  SUM((postings->>amount)::numeric) as total
FROM transactions
WHERE metadata->>'type' = 'PAYROLL_GROSS'
  AND metadata->>'pay_period' = '2024-W26'
GROUP BY metadata->>'department'

-- Tax liability by period
SELECT 
  metadata->>'tax_period' as period,
  SUM((postings->>amount)::numeric) as tax_collected
FROM transactions
WHERE metadata->>'type' = 'TAX_SETTLEMENT'
GROUP BY metadata->>'tax_period'
ORDER BY period
```

---

## 6. Transaction Validation Layer

### 6.1 Multi-Layer Validation Architecture

```
User Input
    |
    v
+-------------------+     +-------------------+     +-------------------+
| Layer 1: Syntax   | --> | Layer 2: Business | --> | Layer 3: Ledger   |
| Validation        |     | Rule Validation   |     | Constraint Check  |
| (Numscript parser)|     | (Domain rules)    |     | (Formance engine) |
+-------------------+     +-------------------+     +-------------------+
    |                           |                         |
    v                           v                         v
  JSON Schema                Balance check            Account exists
  Type checking              Period lock              Overdraft limit
  Required fields            Tax consistency          Colored asset rules
  Enum validation            Reference uniqueness     Volume constraints
```

### 6.2 Layer 1: Syntax Validation

Validate the generated Numscript before submission:

```python
# Pseudo-code for syntax validation
import numscript

def validate_syntax(numscript_code: str) -> ValidationResult:
    result = numscript.Parse(numscript_code)
    errors = result.GetParsingErrors()
    if errors:
        return ValidationResult(
            valid=False,
            errors=[e.message for e in errors],
            needed_vars=result.GetNeededVariables()
        )
    return ValidationResult(valid=True, needed_vars=result.GetNeededVariables())
```

The Numscript parser (ANTLR4-based) validates grammar, variable declarations, type consistency, and produces a structured AST before any execution [^231^].

### 6.3 Layer 2: Business Rule Validation

```python
class BusinessRuleValidator:
    """Domain-specific validation rules"""

    RULES = {
        "SALE_INV": [
            "amount_positive",
            "customer_exists",
            "tax_rate_valid",
            "invoice_ref_unique",
            "period_open"
        ],
        "PAYROLL_GROSS": [
            "gross_equals_net_plus_deductions",
            "tax_compliance_jurisdiction",
            "period_consistent",
            "department_codes_valid"
        ],
        "TAX_SETTLEMENT": [
            "output_tax_matches_period",
            "input_tax_matches_period",
            "net_payable_correct",
            "filing_deadline_not_passed"
        ]
    }

    def validate(self, tx_type: str, params: dict) -> ValidationResult:
        rules = self.RULES.get(tx_type, [])
        errors = []
        for rule in rules:
            validator = getattr(self, f"_rule_{rule}")
            result = validator(params)
            if not result.valid:
                errors.extend(result.errors)
        return ValidationResult(valid=len(errors) == 0, errors=errors)
```

### 6.4 Layer 3: Ledger Constraint Validation

Formance enforces constraints at the ledger level [^260^]:

| Constraint | Description | Configuration |
|-----------|-------------|---------------|
| Overdraft prevention | Account cannot go negative | `allowing overdraft up to [AMT]` |
| Balance enforcement | Sum of all postings must balance | Automatic — cannot disable |
| Asset consistency | All amounts in a posting use same asset | Automatic |
| Account existence | Referenced accounts must exist | Configurable |
| Volume limits | Maximum transaction size | Ledger configuration |

### 6.5 Period Lock Enforcement

```python
class PeriodLockValidator:
    """Prevent posting to closed accounting periods"""
    
    def validate_period_open(self, transaction_date: datetime, 
                            company_id: str) -> ValidationResult:
        """
        Check if the accounting period containing transaction_date is open.
        Closed periods require special authorization.
        """
        period = get_accounting_period(transaction_date, company_id)
        if period.status == "CLOSED":
            return ValidationResult(
                valid=False,
                errors=[f"Period {period.name} is closed. "
                       f"Reversal or adjustment entry required."]
            )
        if period.status == "PENDING_CLOSE":
            return ValidationResult(
                valid=False, 
                warnings=[f"Period {period.name} is pending close."],
                requires_approval=True
            )
        return ValidationResult(valid=True)
```

---

## 7. Correction Workflow

### 7.1 Immutable Ledger Principle

The Formance ledger is **append-only and immutable**. Once a transaction is posted, it cannot be edited or deleted [^363^][^365^][^367^]. Corrections are made by posting new compensating transactions that leave a complete audit trail.

This follows the accounting principle that "instead of updating 'payment amount from $10 to $8,' append a correcting entry or reversal" [^367^].

### 7.2 Correction Methods

#### 7.2.1 Full Reversal

Post an exact mirror of the original transaction. Formance provides a `revert_transaction` API endpoint that automates this [^188^][^259^]:

```numscript
// REVERSAL: Reverse original transaction TX-001
// The reversed transaction creates compensating postings

vars {
  string $original_tx_id
}

// Formance API: POST /api/ledger/v2/{ledger}/transactions/{id}/revert
// This creates a new transaction with inverted postings

set_tx_meta("type", "COR_REV")
set_tx_meta("original_tx_id", $original_tx_id)
set_tx_meta("reason", "Complete reversal")
```

The Formance SDK provides `RevertTransaction` which automatically generates a compensating entry [^188^].

#### 7.2.2 Partial Adjustment

When only a portion of the original transaction was incorrect:

```numscript
// ADJUSTMENT: Partial correction of original entry
// Original: $500 expense recorded as office supplies
// Correct:  $500 expense should be IT equipment

vars {
  monetary $amount
  string $original_tx_id
  string $reason
}

// Reverse the incorrect portion
send $amount (
  source = @expenses:office_supplies
  destination = @world
)

// Post to correct account
send $amount (
  source = @world
  destination = @expenses:it_equipment
)

set_tx_meta("type", "COR_ADJ")
set_tx_meta("original_tx_id", $original_tx_id)
set_tx_meta("reason", $reason)
set_tx_meta("adjustment_type", "RECLASSIFICATION")
```

#### 7.2.3 Amending Entry

When the original transaction is correct but incomplete:

```numscript
// AMENDING ENTRY: Add missing tax to original invoice
// Original invoice did not include VAT

vars {
  monetary $tax_amount
  string $original_invoice_ref
}

send $tax_amount (
  source = @world
  destination = @liabilities:tax:sales_tax
)

send $tax_amount (
  source = @revenue:sales  // Reduce net revenue
  destination = @world
)

set_tx_meta("type", "COR_AMD")
set_tx_meta("original_invoice_ref", $original_invoice_ref)
set_tx_meta("reason", "Add missing VAT")
```

### 7.3 Correction Workflow Steps

```
1. IDENTIFY
   - User flags incorrect transaction
   - System identifies transaction by ID
   - Read original transaction and metadata

2. ANALYZE
   - Determine correction type (reversal, adjustment, amendment)
   - Identify all affected accounts
   - Check period lock status
   - Calculate impact

3. AUTHORIZE
   - Route to appropriate approver based on amount
   - Record authorization decision
   - Require dual authorization for material corrections

4. EXECUTE
   - Generate compensating Numscript
   - Attach correction metadata (original_tx_id, reason, approver)
   - Post with idempotency key
   - Link original and correction transactions

5. VERIFY
   - Confirm corrected balances
   - Update any dependent transactions
   - Notify stakeholders
```

### 7.4 Correction Metadata Standard

Every correction transaction carries provenance metadata:

```json
{
  "tx_meta": {
    "type": "COR_REV",
    "correction_type": "FULL_REVERSAL",
    "original_tx_id": "TX-001",
    "original_timestamp": "2024-06-01T10:00:00Z",
    "correction_reason": "Duplicate entry",
    "requested_by": "user:jane.smith",
    "approved_by": "user:finance.manager",
    "approval_timestamp": "2024-06-02T09:15:00Z",
    "correction_sequence": 1,
    "linked_tx_ids": ["TX-001", "TX-002"]
  }
}
```

---

## 8. Bulk Transactions

### 8.1 Formance Bulk Processing

Formance provides a `_bulk` endpoint that supports batch transaction creation with several processing options [^366^]:

| Parameter | Type | Description |
|-----------|------|-------------|
| `atomic` | boolean | All succeed or all fail |
| `parallel` | boolean | Process elements in parallel |
| `continueOnFailure` | boolean | Skip failed items, continue processing |

**Constraints**: Cannot set both `parallel=true` and `atomic=true` simultaneously [^366^].

### 8.2 Batch Import Format

```json
POST /api/ledger/v2/my-ledger/_bulk?atomic=true
[
  {
    "action": "CREATE_TRANSACTION",
    "ik": "batch-001-item-001",
    "data": {
      "script": {
        "plain": "send [USD/2 50000] ( source = @world destination = @customers:acme )"
      },
      "metadata": {
        "type": "SALE_INV",
        "invoice_ref": "BATCH-001-001"
      }
    }
  },
  {
    "action": "CREATE_TRANSACTION", 
    "ik": "batch-001-item-002",
    "data": {
      "script": {
        "plain": "send [USD/2 75000] ( source = @world destination = @customers:globex )"
      },
      "metadata": {
        "type": "SALE_INV",
        "invoice_ref": "BATCH-001-002"
      }
    }
  }
]
```

### 8.3 Recurring Transactions

Recurring transactions post repeatedly over consecutive periods [^380^][^382^][^385^].

**Recurring Transaction Schema:**

```json
{
  "recurring_template": {
    "template_id": "REC-001",
    "name": "Monthly Rent",
    "template_type": "fixed_amount",
    "numscript_template": "EXPENSE_CASH",
    "variables": {
      "amount": "USD/2 500000",
      "expense_category": "expenses:rent",
      "bank_account": "assets:bank:operating",
      "description": "Monthly office rent"
    },
    "schedule": {
      "frequency": "monthly",
      "start_date": "2024-01-01",
      "end_date": "2024-12-31",
      "day_of_month": 1,
      "skip_weekends": true,
      "weekend_rule": "friday_before"
    },
    "status": "active",
    "next_run": "2024-07-01",
    "last_run": "2024-06-01",
    "run_count": 6,
    "max_runs": 12
  }
}
```

**Frequency Options** (based on industry standard ERP patterns [^380^][^384^]):
- `daily`, `weekly`, `biweekly`, `monthly`, `quarterly`, `yearly`
- `custom`: Specify day intervals

### 8.4 Bulk Payment Runs

```numscript
// BULK_PAYMENT_RUN — Pay multiple vendor bills in batch
// Variables injected via bulk API

vars {
  monetary $payment_amount
  account $vendor_account
  string $bill_ref
  string $batch_id
}

// Mark bill as paid
send $payment_amount (
  source = $vendor_account
  destination = @world
)

// Debit bank
send $payment_amount (
  source = @assets:bank:operating
  destination = @world
)

set_tx_meta("type", "BULK_PAYMENT")
set_tx_meta("bill_ref", $bill_ref)
set_tx_meta("batch_id", $batch_id)
set_tx_meta("vendor", $vendor_account)
```

### 8.5 Payroll Bulk Run

A payroll run processes hundreds of employee payments as a single batch:

```python
# Pseudo-code for payroll bulk generation
async def process_payroll_run(pay_period: str, employees: list[Employee]) -> BatchResult:
    """Generate and execute bulk payroll transactions"""
    
    # Stage 1: Calculate all payroll components
    calculations = [calculate_payroll(emp, pay_period) for emp in employees]
    
    # Stage 2: Generate Numscript bulk elements
    bulk_elements = []
    for calc in calculations:
        # Entry 1: Gross wages
        bulk_elements.append(create_gross_entry(calc))
        # Entry 2: Employer taxes
        bulk_elements.append(create_employer_tax_entry(calc))
        # Entry 3: Net pay
        bulk_elements.append(create_net_pay_entry(calc))
    
    # Stage 3: Execute as atomic batch
    result = await formance.bulk.create(
        ledger="payroll",
        elements=bulk_elements,
        atomic=True,
        continueOnFailure=False
    )
    
    return result
```

### 8.6 CSV/Excel Import Pipeline

```
CSV Upload
    |
    v
+---------------------+     +---------------------+     +---------------------+
| Parse & Validate    | --> | Map to Templates    | --> | Preview & Confirm   |
| - Column mapping    |     | - Row -> Numscript  |     | - Show impact       |
| - Type conversion   |     | - Account lookup    |     | - Error summary     |
| - Basic validation  |     | - Variable binding  |     | - User approval     |
+---------------------+     +---------------------+     +---------------------+
                                                              |
                                                              v
                                                     +---------------------+
                                                     | Execute Bulk        |
                                                     | - Atomic batch      |
                                                     | - Idempotency keys  |
                                                     | - Progress tracking |
                                                     +---------------------+
```

---

## 9. Transaction Status Lifecycle

### 9.1 State Machine

Based on standard accounting document lifecycle patterns [^362^] and adapted for immutable ledger operations:

```
                    +-----------+
                    |   DRAFT   |<-------------------+
                    | (editable)|                     |
                    +-----+-----+                     |
                          |                           |
                    validate()                        |
                          |                           |
                          v                           |
                    +-----------+                     |
         +--------->|  PENDING  |                     |
         |          |(approval) |                     |
         | reject() +-----+-----+                     |
         |                | approve()                 |
         |                v                           |
         |          +-----------+   correction()      |
         |          |  POSTED   |---------------------+
         |          | (immutable)|                     |
         |          +-----+-----+                     |
         |                |                           |
         |          reconcile()                       |
         |                |                           |
         |                v                           |
         |          +-----------+                     |
         |          |RECONCILED |                     |
         |          +-----+-----+                     |
         |                |                           |
         |          lock()                            |
         |                |                           |
         |                v                           |
         |          +-----------+                     |
         +----------|  LOCKED   |                     |
                    |(archive)  |                     |
                    +-----------+                     |
                                                      |
         correction() always creates new transaction  |
         that references original, status -> POSTED    |
```

### 9.2 State Definitions

| State | Description | Mutability | Visible in Reports |
|-------|-------------|-----------|-------------------|
| `DRAFT` | Being created/edited, not yet validated | Fully editable | No |
| `PENDING` | Awaiting approval | Editable by approver | No |
| `POSTED` | Immutable ledger entry | Append-only corrections | Yes |
| `RECONCILED` | Matched to external statement | Immutable | Yes |
| `LOCKED` | Period closed, archived | Immutable, permanent | Yes (historical) |

### 9.3 State Transitions

| From | To | Trigger | Authorization |
|------|-----|---------|---------------|
| DRAFT | PENDING | Submit for approval | Creator |
| PENDING | POSTED | Approval | Approver (amount-based) |
| PENDING | DRAFT | Rejection | Approver |
| POSTED | RECONCILED | Bank reconciliation match | System/Operator |
| RECONCILED | LOCKED | Period close | Admin |
| POSTED | (new) POSTED | Correction entry | Authorized user |

### 9.4 Approval Matrix

| Transaction Type | Amount Threshold | Approver Level |
|-----------------|-----------------|----------------|
| Standard journal | <$1,000 | Self-approve |
| Standard journal | $1,000-$10,000 | Manager |
| Standard journal | >$10,000 | Director |
| Correction entry | Any amount | Manager+ |
| Payroll | Any amount | HR + Finance |
| Tax settlement | Any amount | Finance Director |

---

## 10. Idempotency Design

### 10.1 Core Principle

Idempotency guarantees that executing the same operation multiple times produces the same result as executing it once [^361^][^363^][^367^]. In financial systems, this prevents duplicate charges, double-booked entries, and phantom transactions.

### 10.2 Idempotency Key Strategy

Following Stripe's proven pattern [^361^][^367^]:

```python
# Idempotency key storage
class IdempotencyStore:
    """
    Stores: (idempotency_key) -> (request_hash, response, status)
    
    Same key + same payload = return original response
    Same key + different payload = return 409 Conflict
    """
    
    async def check_idempotency(
        self, 
        key: str, 
        payload_hash: str
    ) -> IdempotencyResult:
        existing = await self.store.get(key)
        
        if existing is None:
            # New request — store intent, proceed
            await self.store.set(key, {
                "request_hash": payload_hash,
                "status": "IN_PROGRESS",
                "created_at": datetime.utcnow()
            })
            return IdempotencyResult(proceed=True)
        
        if existing["request_hash"] != payload_hash:
            # Same key, different payload — conflict
            return IdempotencyResult(
                proceed=False,
                error=IdempotencyConflictError(
                    "Idempotency key used with different payload"
                )
            )
        
        # Same key, same payload — return cached response
        return IdempotencyResult(
            proceed=False,
            cached_response=existing["response"],
            idempotency_hit=True
        )
```

### 10.3 Idempotency in Formance

Formance natively supports idempotency keys [^366^]:

**Numscript Stream Format:**
```numscript
//script ik=invoice-payment-acme-2024-06
send [USD/2 50000] (
  source = @customers:acme
  destination = @assets:bank:operating
)
//end
```

**JSON Format:**
```json
{
  "action": "CREATE_TRANSACTION",
  "ik": "invoice-payment-acme-2024-06",
  "data": {
    "postings": [
      {
        "source": "customers:acme",
        "destination": "assets:bank:operating",
        "amount": 50000,
        "asset": "USD/2"
      }
    ]
  }
}
```

**API Headers:**
```http
POST /api/ledger/v2/my-ledger/transactions
Idempotency-Key: invoice-payment-acme-2024-06
Content-Type: application/json
```

**Duplicate Detection Response:**
```http
HTTP/1.1 200 OK
Idempotency-Hit: true

{ /* original response */ }
```

The `Idempotency-Hit: true` header allows clients to distinguish between new and replayed requests [^366^].

### 10.4 Key Generation Strategy

```python
def generate_idempotency_key(
    transaction_type: str,
    entity_ref: str,      # invoice_ref, bill_ref, employee_id
    period: str,          # pay period, tax period
    sequence: int = 0
) -> str:
    """Generate deterministic, unique idempotency key.
    
    Format: {type}:{entity_ref}:{period}[:{sequence}]
    Example: SALE_INV:INV-2024-0042:2024-06
    Example: PAYROLL:GROSS:2024-W26:001
    """
    key = f"{transaction_type}:{entity_ref}:{period}"
    if sequence > 0:
        key += f":{sequence:03d}"
    return key
```

### 10.5 Idempotency Across Bulk Operations

Each element in a bulk request carries its own idempotency key [^366^]:

```python
# Bulk with per-element idempotency
bulk_request = [
    {
        "action": "CREATE_TRANSACTION",
        "ik": f"payroll-2024w26-{emp.id}-gross",
        "data": gross_entry(emp)
    }
    for emp in employees
]

# If the bulk partially fails, replay with same keys
# Already-processed elements return Idempotency-Hit: true
# Failed elements are retried
```

### 10.6 At-Least-Once Delivery Pattern

In distributed systems, combine idempotent writes with at-least-once message delivery [^367^]:

```
Message Queue (Kafka/SQS)
    |
    v
+----------------------+     +----------------------+
| Consumer             | --> | Ledger Writer        |
| - Parse message      |     | - Check idempotency  |
| - Extract tx params  |     | - Write transaction  |
| - Generate Numscript |     | - Ack message        |
+----------------------+     +----------------------+
         |                            |
         | fail()                     |
         v                            v
  +------------------+      +------------------+
  | Dead Letter Queue|      | Idempotency Store|
  | (manual review)  |      | (Redis/Postgres) |
  +------------------+      +------------------+
```

### 10.7 Idempotency TTL

| Key Type | Retention Period | Rationale |
|----------|-----------------|-----------|
| Standard transactions | 24 hours | Covers retry windows |
| Bulk operations | 7 days | Bulk may span multiple retry sessions |
| Payroll runs | Until next pay period + 7 days | Prevents duplicate payroll |
| Tax settlements | Until filing deadline + 30 days | Tax corrections window |

---

## 11. Implementation Architecture

### 11.1 System Components

```
+------------------------+      +------------------------+      +------------------------+
|     API Gateway        |----->|  Transaction Service   |----->|   Template Engine      |
|  - Auth/Rate Limit     |      |  - Orchestration       |      |  - Numscript templates |
+------------------------+      |  - Validation          |      |  - Variable binding    |
                                |  - Status management   |      |  - Account resolution  |
                                +------------------------+      +------------------------+
                                          |
                                +---------+---------+
                                |                   |
                       +--------v-------+  +--------v--------+
                       |  LLM Service   |  | Formance Ledger |
                       |  - Intent      |  | - Numscript     |
                       |  - Extraction  |  |   execution     |
                       |  - Generation  |  | - Immutability  |
                       +----------------+  +-----------------+
```

### 11.2 Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Template approach | Parameterized Numscript | Reduces LLM error surface from full generation to variable filling |
| Validation layer | Multi-stage (syntax + business + ledger) | Catches 91%+ of LLM-generated errors [^412^] |
| Ledger engine | Formance (append-only) | Immutable audit trail, built-in idempotency |
| Idempotency | Client-generated keys + server store | Proven pattern from Stripe and Formance |
| Corrections | Compensating entries only | Maintains immutable ledger invariant |
| Bulk processing | Formance `_bulk` endpoint | Atomic batches, per-element idempotency |
| Recurring | Template + scheduler | Industry standard pattern [^380^][^385^] |
| Status lifecycle | DRAFT -> PENDING -> POSTED -> RECONCILED -> LOCKED | Standard accounting workflow [^362^] |

### 11.3 Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Single transaction latency | <200ms | End-to-end with validation |
| Bulk throughput | 1,000 tx/sec | Per-ledger, Formance baseline [^46^] |
| Horizontal scaling | Multi-ledger | Parallel ledgers for >1K tx/sec [^46^] |
| LLM generation | <2s | Template population with structured output |
| Validation | <50ms | Deterministic rules, no LLM in validation path |

---

## 12. References

[^46^] Formance Documentation, "Architecting for Scale" — https://docs.formance.com/modules/ledger/advanced/architecting-for-scale

[^76^] Beancount.io, "Using LLMs to Automate and Enhance Bookkeeping with Beancount" — https://beancount.io/docs/Solutions/using-llms-to-automate-and-enhance-bookkeeping-with-beancount

[^169^] Formance GitHub Repository, "formancehq/ledger" — https://github.com/formancehq/ledger

[^176^] Formance GitHub, "numscript" — https://github.com/formancehq/numscript

[^188^] Formance SDK Go, Ledger API Reference — https://github.com/formancehq/formance-sdk-go

[^200^] Formance Documentation, "Numscript" — https://docs.formance.com/modules/numscript

[^213^] Formance Documentation, "Ledger" — https://docs.formance.com/modules/ledger

[^228^] Formance Blog, "What is Numscript and Why is it Awesome?" — https://www.formance.com/blog/engineering/numscript

[^229^] Go Package Documentation, "ledger command" — https://pkg.go.dev/github.com/formancehq/ledger

[^230^] GitHub, "formance-numscript-generator" — https://github.com/NathanFirmo/formance-numscript-generator

[^231^] Hanzo Documentation, "Hanzo Numscript" — https://docs.hanzo.ai/docs/skills/hanzo-numscript

[^232^] Formance GitHub, "numscript/differences-with-machine.md" — https://github.com/formancehq/numscript/blob/main/differences-with-machine.md

[^233^] Formance Documentation, "Numscript Program Structure" — https://docs.formance.com/modules/numscript/program-structure

[^234^] Formance Blog, "Building an Uber Eats Clone" — https://dev.to/formance/building-an-uber-eats-clone-38j8

[^235^] Formance Documentation, "Numscript Variables" — https://docs.formance.com/modules/numscript/reference/variables

[^259^] Formance Python SDK — https://github.com/formancehq/formance-sdk-python

[^260^] Formance Documentation, "Examples Introduction" — https://docs.formance.com/examples/introduction

[^258^] Invoice Data Extraction, "Types of Receipts in Accounting" — https://invoicedataextraction.com/blog/types-of-receipts-in-accounting

[^257^] MUBS, "The Business Sales Process" — https://mubsep.mubs.ac.ug/mod/resource/view.php?id=48964

[^261^] B2BE, "Types of Invoices" — https://www.b2be.com/types-of-invoices/

[^358^] Agentic Patterns, "Structured Output Specification" — https://agentic-patterns.com/patterns/structured-output-specification/

[^359^] Deel Blog, "Payroll Journal Entry Guide" — https://www.deel.com/blog/payroll-journal-entry/

[^360^] Ramp Blog, "Payroll Journal Entry" — https://ramp.com/blog/payroll-journal-entry

[^361^] ByteDoodle, "Idempotency in Distributed Transaction Systems" — https://blog.bytedoodle.com/idempotency-in-distributed-transaction-systems/

[^362^] Light Help Center, "Accounting Document Types and Lifecycle" — https://help.light.inc/general-ledger/document-types-lifecycle

[^363^] Hacker News, "Books: Immutable Double-Entry Accounting" — https://news.ycombinator.com/item?id=21276984

[^364^] WPERP, "15 Different Types of Accounts" — https://wperp.com/148693/different-types-of-accounts/

[^365^] Accounting AI Tutor, "Payroll Journal Entries" — https://www.accountingaitutor.com/study-guides/payroll-journal-entries-gross-pay-withholdings-employer-taxes-worked-examples

[^366^] Formance Documentation, "Bulk Processing" — https://docs.formance.com/modules/ledger/working-with/bulk-processing

[^367^] Prachub, "Payment Systems: Ledgers, Idempotency, and Reconciliation" — https://prachub.com/concepts/payment-systems-ledgers-idempotency-and-reconciliation

[^368^] ADP, "Accounting for Payroll" — https://www.adp.com/resources/articles-and-insights/articles/a/accounting-for-payroll.aspx

[^369^] Sage Intacct, "Capture Tax in Journal Entry" — https://www.intacct.com/ia/docs/en_US/help_action/General_Ledger/Journal_Entries/Create_or_edit_journal_entries/capture-tax-in-a-journal-entry.htm

[^380^] e5 Documentation, "GL Journal Transactions" — https://nhprod.cloudfinancials.oneadvanced.com/e5h5/e5h5help/mergedProjects/modules/modules/gl/gl_journal_transactions.htm

[^382^] Dynamics GP, "Working with Recurring Batches" — https://community.dynamics.com/blogs/post/?postid=7e035268-f0f4-4a7d-b8d0-a024910a3ed2

[^385^] Sage KB, "How do I process Recurring Journals?" — https://za-kb.sage.com/portal/app/portlets/results/viewsolution.jsp?solutionid=200116123959675

[^386^] Formance Documentation, "Numscript Metadata" — https://docs.formance.com/modules/numscript/reference/metadata

[^39^] TECHSY, "Reliable JSON from Any LLM" — https://techsy.io/en/blog/llm-structured-outputs-guide

[^359^] InvoiceFly, "Types of Accounting Transactions" — https://invoicefly.com/academy/transactions/

[^360^] Medium, "Structured Output Generation in LLMs" — https://medium.com/@emrekaratas-ai/structured-output-generation-in-llms-json-schema-and-grammar-based-decoding-6a5c58b698a6

[^361^] Dev.to, "LLM Structured Output in 2026" — https://dev.to/pockit_tools/llm-structured-output-in-2026-stop-parsing-json-with-regex-and-do-it-right-34pk

[^362^] ACL Anthology, "SLOT: Structuring the Output of LLMs" — https://arxiv.org/html/2505.04016v1

[^363^] GeeksforGeeks, "Avoiding Double Payments in Distributed Systems" — https://www.geeksforgeeks.org/system-design/airbnb-idempotency-avoiding-double-payments-in-a-distributed-payments-system/

[^365^] FinOps School, "What is General Ledger?" — https://finopsschool.com/blog/general-ledger/

[^412^] Weber et al., "Evaluating Financial Literacy of Large Language Models" (FinNLP 2025) — https://aclanthology.org/2025.finnlp-1.6.pdf
