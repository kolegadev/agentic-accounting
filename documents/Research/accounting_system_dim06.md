# Dimension 06: Bank Feed Integration & Reconciliation System Design

## Executive Summary

This document provides a comprehensive design for the bank feed ingestion and reconciliation system. The system integrates with multiple bank feed aggregators (Plaid, TrueLayer, Salt Edge, Yodlee) covering 17,000+ institutions globally, implements a robust ingestion pipeline, multi-layered transaction matching engine, configurable bank rules, structured reconciliation workflows, exception handling, multi-currency reconciliation, manual statement import fallbacks, reconciliation reporting with drift detection, and AI-powered matching with confidence scoring.

---

## 1. Feed Aggregation Strategy

### 1.1 Aggregator Comparison Matrix

| Provider | Founded | HQ | Coverage | Institutions | Regions | Connection Method | PSD2 AISP |
|----------|---------|-----|----------|-------------|---------|-------------------|-----------|
| **Plaid** | 2013 | San Francisco, US | 12,000+ live [^258^] | 9,706 tracked | US, CA, UK, EU (20 markets) | OAuth + screen-scraping fallback | Yes [^258^] |
| **Yodlee (Envestnet)** | 1999 | US | 17,000+ [^254^] | 17,000+ | US, CA, UK, EU, AU, India, others | Screen-scraping + direct API | Yes [^254^] |
| **Salt Edge** | — | EU | 3,000+ [^265^] | 3,000+ | 60+ countries | PSD2 Open Banking gateway | Yes [^265^] |
| **TrueLayer** | 2016 | London, UK | Strong UK/EU [^261^] | 1,000s | UK, DE, FR, ES, IT (14 EU countries) | PSD2 Open Banking APIs | FCA-regulated [^261^] |

### 1.2 Regional Coverage Strategy

#### North America (US & Canada)
- **Primary**: Plaid — dominant US coverage with 12,000+ institutions including all major banks (Chase, BofA, Wells Fargo, Citi, Capital One) [^258^]. Supports Auth, Balance, Transactions, Identity, and Investments products.
- **Secondary**: Yodlee — broadest US coverage for smaller institutions and credit unions that Plaid may not cover [^254^].
- **Connection methods**: OAuth where available, screen-scraping fallback, FDX standard in US [^258^]

#### Europe (UK & EU)
- **Primary**: TrueLayer — purpose-built for UK/EU Open Banking, FCA-regulated, PSD2 licensed [^261^]. Instant bank payments and recurring billing support.
- **Secondary**: Salt Edge — PSD2 gateway aggregating all EU banks via single API, 60+ countries [^265^]. Strong for multi-country operations.
- **Tertiary**: Plaid — growing UK/EU footprint with Transactions, Auth, Balance, Identity live; Payment Initiation in UK/EU [^258^]
- **Connection methods**: PSD2 AISP APIs with Strong Customer Authentication (SCA) [^261^]

#### Asia-Pacific
- **Primary**: Yodlee — strongest APAC coverage including Australia and India [^254^]
- **Secondary**: Plaid — limited APAC coverage
- **Tertiary**: Salt Edge — 60+ country coverage including APAC markets [^265^]

#### Africa & Middle East
- **Primary**: Salt Edge — 60+ country coverage [^265^]
- **Secondary**: Yodlee — international coverage including these markets [^254^]
- **Note**: Many banks in these regions only provide CSV/PDF exports, requiring manual import fallback [^283^]

### 1.3 Aggregator API Capabilities by Region

| Product | US | CA | UK | EU | Notes |
|---------|----|----|----|----|-------|
| Transactions | Live | Live | Live | Live | All regions supported [^258^] |
| Auth (routing) | Live | Live | Live | Live | Account verification [^258^] |
| Balance | Live | Live | Live | Live | Real-time balance checks [^258^] |
| Identity | Live | Live | Live | Live | Account owner verification [^258^] |
| Income | Live | Limited | Beta | Beta | Income verification [^258^] |
| Payment Initiation | — | — | Live | Live | Open Banking payments [^258^] |
| Investments | Live | Live | — | — | Brokerage/wealth [^258^] |

### 1.4 Architecture: Multi-Aggregator Abstraction Layer

```
┌─────────────────────────────────────────────────────────────┐
│                    Account Connector                        │
│                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │  Plaid   │ │ TrueLayer│ │ SaltEdge │ │  Yodlee  │       │
│  │ Adapter  │ │ Adapter  │ │ Adapter  │ │ Adapter  │       │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘       │
│       │            │            │            │              │
│       └────────────┴────────────┴────────────┘              │
│                          │                                  │
│              ┌───────────┴───────────┐                      │
│              │  Aggregator Router     │                      │
│              │  (region/institution   │                      │
│              │   → best aggregator)   │                      │
│              └───────────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

**Aggregator Selection Logic**:
1. Query institution database for supported aggregators
2. Priority: Open Banking APIs (PSD2) > OAuth > Screen-scraping
3. Failover chain: Primary → Secondary → Tertiary → Manual import
4. Track aggregator health/uptime for dynamic routing

---

## 2. Feed Ingestion Pipeline

### 2.1 Pipeline Architecture

The ingestion pipeline follows a scalable multi-stage design inspired by enterprise data pipeline patterns [^221^][^222^]:

```
┌─────────┐   ┌──────────┐   ┌─────────────┐   ┌──────────┐   ┌──────────┐
│  POLL   │ → │ NORMALIZE│ → │ DEDUPLICATE │ → │  QUEUE   │ → │ PROCESS  │
│  Stage  │   │  Stage   │   │   Stage     │   │  Stage   │   │  Stage   │
└─────────┘   └──────────┘   └─────────────┘   └──────────┘   └──────────┘
```

### 2.2 Stage 1: Poll

**Purpose**: Collect raw transaction data from aggregator APIs

**Implementation**:
- **Polling frequency**: Typically one or more times per day, institution-dependent [^348^]
- **On-demand refresh**: `/transactions/refresh` endpoint for manual updates [^348^]
- **Webhook support**: Subscribe to aggregator webhooks for real-time transaction notifications [^348^]
- **Historical backfill**: Pull up to 12 months of historical data on initial connection [^352^]
- **Rate limiting**: Respect aggregator rate limits with exponential backoff
- **Pagination**: Handle large transaction sets via cursor-based pagination (e.g., Plaid `/transactions/sync` with `next_cursor`) [^348^]

**Raw Data Schema (Plaid example)** [^358^]:
```json
{
  "transaction_id": "yhnUVvtcGGcCKU0bcz8PDQr5ZUxUXebUvbKC0",
  "account_id": "BxBXxLj1m4HMXBm9WZZmCWVbPjX16EHwv99vp",
  "amount": 28.34,
  "iso_currency_code": "USD",
  "date": "2023-09-28",
  "datetime": "2023-09-28T15:10:09Z",
  "authorized_date": "2023-09-27",
  "name": "Dd Doordash Burgerkin",
  "merchant_name": "Burger King",
  "merchant_entity_id": "mVrw538wamwdm22mK8jqpp7qd5br0eeV9o4a1",
  "personal_finance_category": {
    "primary": "FOOD_AND_DRINK",
    "detailed": "FOOD_AND_DRINK_FAST_FOOD",
    "confidence_level": "VERY_HIGH"
  },
  "payment_channel": "online",
  "pending": true,
  "location": { "city": "...", "region": "..." },
  "counterparties": [
    { "name": "DoorDash", "type": "marketplace", "confidence_level": "HIGH" }
  ]
}
```

### 2.3 Stage 2: Normalize

**Purpose**: Transform aggregator-specific schemas to our canonical transaction format

**Canonical Transaction Schema**:
| Field | Type | Description | Mapping |
|-------|------|-------------|---------|
| `transaction_id` | string | Unique ID from aggregator | Plaid: `transaction_id`, Yodlee: `id` |
| `account_id` | string | Linked internal account ID | Cross-reference via account mapping table |
| `amount` | decimal | Transaction amount (positive = credit, negative = debit) | Normalized from aggregator format |
| `currency` | string | ISO 4217 currency code | `iso_currency_code` [^358^] |
| `transaction_date` | date | Posted date | `date` field [^358^] |
| `value_date` | datetime | When funds actually moved | `datetime` or `authorized_date` [^358^] |
| `description` | string | Raw description from bank | `name` field [^358^] |
| `merchant_name` | string | Cleaned merchant name | `merchant_name` (97% fill rate) [^348^] |
| `merchant_category` | string | Business category | `personal_finance_category.detailed` [^358^] |
| `reference` | string | Transaction reference number | `payment_meta.reference_number` [^358^] |
| `transaction_type` | enum | `debit`, `credit`, `transfer`, `fee`, `interest` | Derived from amount + context |
| `payment_method` | enum | `ach`, `wire`, `card`, `check`, `transfer` | `payment_channel` [^358^] |
| `status` | enum | `pending`, `posted`, `cancelled` | `pending` boolean [^358^] |
| `counterparty_name` | string | Other party in transaction | `counterparties[].name` [^358^] |
| `raw_data` | jsonb | Original aggregator response | Stored for audit/debugging |

### 2.4 Stage 3: Deduplicate

**Purpose**: Prevent duplicate transactions from multiple ingestion sources

**Dedup Strategy**:
1. **Transaction ID uniqueness**: Enforce unique constraint on `(aggregator_transaction_id, source_aggregator)`
2. **Content-based dedup**: For transactions without stable IDs (CSV imports), compute hash of `(date, amount, description, account_id)`
3. **FITID-based dedup**: For OFX/QBO imports, use Financial Transaction ID (FITID) which is designed for duplicate prevention [^276^][^284^]
4. **Window-based detection**: Flag transactions within ±1 day with identical amounts and similar descriptions

**Plaid Duplicate Prevention** [^348^]:
- Plaid uses persistent transaction IDs that survive updates
- `pending_transaction_id` links pending to posted transactions
- Webhook-based updates ensure data freshness without re-import

### 2.5 Stage 4: Queue

**Purpose**: Buffer transactions for reliable, ordered processing

**Implementation**:
- Use message queue (e.g., RabbitMQ, Apache Kafka) for transaction buffering [^221^]
- Partition by `account_id` to maintain per-account ordering
- Implement dead-letter queue (DLQ) for failed processing
- Support replay capability for reprocessing

### 2.6 Stage 5: Process

**Purpose**: Store transactions and trigger matching engine

**Implementation**:
1. Persist normalized transaction to `bank_transactions` table
2. Emit event to trigger matching engine
3. Update account balance cache
4. Mark pending transactions as linked when posted version arrives

---

## 3. Transaction Matching Engine

### 3.1 Multi-Stage Matching Architecture

The matching engine uses a cascading approach inspired by enterprise reconciliation systems [^280^][^282^]:

```
Stage 1: Exact Match     → 100% confidence, auto-reconcile
Stage 2: Rule-Based Match → 95-99% confidence, auto-reconcile (if enabled)
Stage 3: Fuzzy Match      → 70-94% confidence, suggest
Stage 4: ML Match         → 60-89% confidence, suggest (JAX-style)
Stage 5: Exception        → <60% confidence, flag for manual review
```

### 3.2 Stage 1: Exact Match

**Criteria** (all must match):
| Field | Tolerance | Weight |
|-------|-----------|--------|
| Amount | Exact to the cent | 40% |
| Date | ±1 day | 25% |
| Reference | Exact match (case-insensitive) | 25% |
| Account | Exact match | 10% |

**Auto-reconcile threshold**: 100% — all criteria match exactly

### 3.3 Stage 2: Rule-Based Match

**Xero-Style Bank Rules Implementation** [^277^][^281^]:

Rules match on bank line fields with configurable conditions:
- **Description/Payee text**: `contains`, `equals`, `starts with`, `ends with`
- **Amount**: exact, range (`between X and Y`), percentage variance
- **Bank account**: specific account or any account
- **Direction**: spend money, receive money, transfer

**Rule Action**:
```
IF description CONTAINS "SPOTIFY" AND amount BETWEEN 5.00 AND 20.00
THEN:
  - Set contact: "Spotify"
  - Set account: "Subscriptions"
  - Set tax rate: "20% VAT on Expenses"
  - Set tracking categories: ["Marketing"] (optional split)
  - Mode: auto-apply OR suggest
```

**Rule Types** [^281^]:
- **Spend Money Rules**: Automate expense categorization
- **Receive Money Rules**: Automate income categorization
- **Transfer Rules**: Detect and assign inter-account transfers

**Rule Confidence Scoring**:
- Exact amount + exact description = 99%
- Range amount + partial description = 95%
- Multiple conditions met = 97%

### 3.4 Stage 3: Fuzzy Match

**Fuzzy Date Tolerance** [^339^][^341^]:
| Transaction Type | Date Tolerance | Rationale |
|------------------|---------------|-----------|
| ACH transfers | ±2 business days | Settlement delay |
| Wire transfers | ±1 business day | Same-day or next-day |
| Checks | ±7 calendar days | Mail + clearing time |
| Card payments | ±1 day | Usually same day |
| International wires | ±3 business days | Correspondent banking |
| Deposits in transit | ±3 business days | Processing delay [^344^] |

**Fuzzy Reference Matching**:
- Use Levenshtein distance for string similarity
- Threshold: ≥85% similarity for reference matching
- Normalize: remove spaces, dashes, special characters before comparison

**Fuzzy Amount Matching**:
- Exact amount = 100%
- Within rounding difference ($0.01) = 99%
- Within known fee offset = 95%
- Partial payment (invoice partially paid) = configurable

**Weighted Scoring Formula**:
```
confidence = (amount_score * 0.40) + (date_score * 0.25) + (reference_score * 0.20) + (description_score * 0.15)
```

### 3.5 Stage 4: Machine Learning Match (JAX-Style)

**Xero JAX Architecture** [^345^][^346^][^349^][^351^]:

JAX uses four layers of intelligence:
1. **Rule**: One of the user's bank rules is applied
2. **Match**: Transaction matches an existing document (invoice, bill, payment)
3. **Memory**: Learns from how user has reconciled similar transactions historically
4. **Prediction**: Suggests based on how other users reconciled similar transactions (crowd-sourced)

**Key Technical Details** [^345^][^352^]:
- **Per-organization model**: JAX trains a separate ML model for each organization based on their specific coding history — not a shared generic model [^345^]
- **Training data**: Uses 12 months of historical reconciliation data [^352^]
- **Accuracy claim**: 97%+ accuracy on suggested matches for consistent transaction patterns [^349^]
- **Auto-reconcile target**: Over 80% of bank statement lines in real-time [^347^]
- **Confidence threshold**: Only auto-reconciles when highly confident; flags lower-confidence matches for review [^351^]

**Implementation Strategy**:
- Feature vector per transaction: amount, day_of_week, hour, merchant_name, description keywords, historical category distribution
- Model: Random Forest classifier handles mixed feature types well [^280^]
- String similarity: FuzzyWuzzy for typos and vendor name variations [^280^]
- Confidence scoring: Probability output from classifier, calibrated per organization

### 3.6 Matching Workflow Summary

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Bank Transaction│ → │  Ledger Entries  │ → │  Match Score    │
│  Arrives         │    │  (invoices,      │    │  Computed       │
│                  │    │   bills, journals│    │                 │
└─────────────────┘    └─────────────────┘    └────────┬────────┘
                                                       │
                              ┌────────────────────────┼────────────────────────┐
                              ▼                        ▼                        ▼
                        ┌──────────┐            ┌──────────┐            ┌──────────────┐
                        │ ≥90%     │            │ 60-89%   │            │ <60%         │
                        │ Auto     │            │ Suggest  │            │ Exception    │
                        │ (config) │            │ for review│           │ manual review │
                        └──────────┘            └──────────┘            └──────────────┘
```

---

## 4. Bank Rules Engine

### 4.1 Rule Structure

Inspired by Xero's bank rules engine [^277^][^279^][^281^]:

```json
{
  "rule_id": "uuid",
  "rule_name": "Spotify Subscription",
  "bank_account_id": "uuid-or-all",
  "rule_type": "spend_money",
  "conditions": [
    {
      "field": "description",
      "operator": "contains",
      "value": "SPOTIFY"
    },
    {
      "field": "amount",
      "operator": "between",
      "min": 5.00,
      "max": 20.00
    }
  ],
  "condition_logic": "AND",
  "actions": {
    "contact_id": "spotify-contact-uuid",
    "account_id": "subscriptions-expense-uuid",
    "tax_rate_id": "vat-20-expense-uuid",
    "tracking_categories": [
      { "category_id": "dept-uuid", "option_id": "marketing-uuid" }
    ],
    "split_lines": [
      { "account_id": "...", "percentage": 70 },
      { "account_id": "...", "percentage": 30 }
    ]
  },
  "auto_apply": false,
  "priority": 10,
  "active": true,
  "created_by": "user-uuid",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### 4.2 Condition Operators

| Field Type | Operators | Examples |
|------------|-----------|----------|
| Description | `equals`, `contains`, `starts_with`, `ends_with`, `regex` | "contains SPOTIFY" |
| Payee/Merchant | `equals`, `contains`, `starts_with` | "equals Stripe" |
| Amount | `equals`, `between`, `greater_than`, `less_than` | "between 5.00 and 20.00" |
| Reference | `equals`, `contains`, `regex` | "matches INV-[0-9]+" |
| Date | `day_of_week`, `day_of_month` | "day_of_week = Monday" |
| Bank Account | `equals`, `in` | "in [checking, savings]" |
| Direction | `is` | "is spend" or "is receive" |

### 4.3 Execution Modes

| Mode | Description | Risk Level |
|------|-------------|------------|
| **Suggest** | Pre-fills reconciliation form, user confirms | Low — recommended for new rules [^277^] |
| **Auto-apply** | Automatically reconciles without human intervention | Medium — only after rule proven reliable [^277^] |
| **Disabled** | Rule stored but not evaluated | None |

**Best Practice**: Start with "Suggest" mode, promote to "Auto-apply" after the rule has correctly matched for several cycles [^277^].

### 4.4 Rule Priority & Conflicts

- Rules evaluated in priority order (lowest number first)
- First matching rule wins
- Ambiguity detection: flag if multiple rules match same transaction
- Users can manually reorder rules via drag-and-drop interface

### 4.5 Bulk Operations

**Cash Coding (Xero-style)** [^277^]:
- Spreadsheet-like grid view of multiple transactions
- Select multiple lines, assign same account/tax rate in one action
- Useful for backlogs and high-volume accounts (e.g., card terminal deposits all going to "Sales")
- Creates new transactions and reconciles in one step

---

## 5. Reconciliation Workflow

### 5.1 Status Flow

```
                    ┌─────────────────────────────────────────┐
                    │                                         │
  ┌──────────┐   ┌──▼─────────┐   ┌──────────────┐   ┌──────▼───┐
  │ IMPORTED │ → │ UNMATCHED  │ → │  SUGGESTED   │ → │ CONFIRMED│
  │ (raw)    │   │ (no match) │   │ (candidate   │   │ (user/   │
  └──────────┘   └────────────┘   │  found)      │   │  rule ok)│
                                  └──────┬───────┘   └────┬─────┘
                                         │                │
                               ┌─────────▼────────┐       │
                               │  AUTO-MATCHED    │◄──────┘
                               │  (rule/AI)       │
                               └─────────┬────────┘
                                         │
                                         ▼
                                ┌────────────────┐
                                │   RECONCILED   │
                                │   (final)      │
                                └────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
              ┌──────────┐       ┌──────────┐       ┌──────────┐
              │ EXCLUDED │       │  VOIDED  │       │ TRANSFER │
              │          │       │          │       │ MATCHED  │
              └──────────┘       └──────────┘       └──────────┘
```

### 5.2 Status Definitions

| Status | Description | Next States |
|--------|-------------|-------------|
| `imported` | Raw transaction from feed/import | `unmatched` |
| `unmatched` | No matching ledger entry found | `suggested`, `excluded` |
| `suggested` | One or more candidate matches found | `confirmed`, `unmatched` |
| `confirmed` | User or rule accepted the match | `reconciled` |
| `auto_matched` | Automatically matched by rule or AI | `reconciled` |
| `reconciled` | Final state — balanced and posted | `unmatched` (on undo) |
| `excluded` | Intentionally not reconciled (e.g., personal expense on biz card) | — |
| `voided` | Transaction reversed or cancelled | — |

### 5.3 Workflow Steps

Based on established reconciliation best practices [^220^][^338^][^344^]:

**Step 1: Collect Financial Data**
- Gather bank transactions from feeds and general ledger entries
- Ensure completeness and cut-off dates are correct [^338^]
- Pull GL balances for same date range as bank statements [^339^]

**Step 2: Match Transactions**
- Run multi-stage matching engine (Section 3)
- Auto-match high-confidence items (≥90%)
- Present suggestions for medium-confidence items (60-89%)
- Flag low-confidence items as exceptions

**Step 3: Identify Timing Differences**
- Outstanding checks (issued not cleared)
- Deposits in transit (recorded not banked)
- Pending electronic transfers [^339^][^340^]
- Items outstanding >30-60 days require investigation [^344^]

**Step 4: Investigate and Resolve**
- Research unmatched items by reviewing source documents [^338^]
- Determine if discrepancy is genuine error, timing difference, or requires adjustment
- Apply correcting journal entries where needed [^342^]

**Step 5: Document and Finalize**
- Prepare reconciliation worksheet: opening balance, reconciling items, closing balance [^220^]
- Generate reconciliation report with full audit trail
- Manager-level approval for material adjustments [^220^]

---

## 6. Exception Handling

### 6.1 Exception Categories

| Category | Description | Resolution | Prevention |
|----------|-------------|------------|------------|
| **Unmatched items** | Bank transaction has no corresponding ledger entry | Create new ledger entry or match manually | Bank rules for recurring items [^277^] |
| **Duplicates** | Same transaction recorded twice | Reverse duplicate entry [^342^] | FITID dedup for imports, validation rules [^338^] |
| **Missing transactions** | Transaction in GL but not on bank statement | Verify timing, check next period statement | Real-time feeds reduce occurrence [^338^] |
| **Timing differences** | Same transaction, different dates in bank vs GL | Document, no adjustment needed [^340^] | Date tolerance rules (Section 3.4) |
| **Amount mismatches** | Same transaction, different amounts | Check fees, FX, partial payments | Fee rules, FX adjustment automation |
| **Bank errors** | Double-posted, incorrect amounts by bank | Contact bank, document correction [^340^] | Regular reconciliation catches early |
| **Unrecorded auto-transactions** | Direct debits, fees, interest not in GL | Create journal entry [^340^] | Rules for known recurring charges |
| **Stale outstanding checks** | Checks uncleared >90 days | Stop payment and reissue [^344^] | Aging reports, alerts |

### 6.2 Transposition Error Detection

**Diagnostic rule**: If a discrepancy amount is divisible by 9, suspect a transposition error (e.g., recording $1,234 as $1,243). Divide the discrepancy by 9, then search for a transaction matching that quotient amount [^340^][^344^].

### 6.3 Duplicate Detection Algorithm

```python
def is_duplicate(txn, existing_txns, window_days=2):
    """Check if transaction is a duplicate of an existing one."""
    candidates = existing_txns.where(
        date_within(txn.date, existing_txns.date, days=window_days) &
        abs(txn.amount - existing_txns.amount) < 0.01 &
        (txn.description == existing_txns.description OR 
         similarity(txn.description, existing_txns.description) > 0.90)
    )
    
    # If aggregator provides stable IDs, also check FITID
    if txn.fitid and candidates.where(fitid=txn.fitid).exists():
        return True
    
    return len(candidates) > 0
```

### 6.4 Exception Workflow

```
1. Flag exception → 2. Categorize exception type → 3. Route to owner
                                              → 4. Set SLA based on materiality
                                              → 5. Track aging
                                              → 6. Escalate if overdue
```

**SLA by Materiality**:
| Amount Range | Resolution SLA | Escalation |
|-------------|----------------|------------|
| > $10,000 | Same business day | Immediate to CFO [^344^] |
| $1,000 - $10,000 | 2 business days | To controller if overdue |
| $100 - $1,000 | 5 business days | Monthly review |
| < $100 | End of period | Quarterly review [^344^] |

### 6.5 Aging Management

**Reconciliation Aging** [^344^][^350^]:

Unreconciled items tracked by age buckets:
- 0-30 days: Expected — routine matching queue
- 31-60 days: Flagged for expedited resolution
- 61-90 days: Detailed investigation required
- 90+ days: Escalated to governance committee / CFO [^344^]

**Benefits of aging tracking**:
- Enhanced visibility into overdue reconciliations
- Reduced manual intervention by focusing on priority items
- Improved audit readiness [^344^]

---

## 7. Multi-Currency Reconciliation

### 7.1 Supported Currency Handling

Based on best practices from Xero, QuickBooks, NetSuite, and Gravity Software [^255^][^256^][^257^][^260^][^263^]:

**Feature Matrix**:
| Feature | Xero | QBO | NetSuite | Required |
|---------|------|-----|----------|----------|
| Currencies supported | 160+ [^256^] | 145+ [^256^] | 190+ [^263^] | 150+ |
| Live exchange rate updates | Hourly [^256^] | Daily | Real-time | Daily minimum |
| Auto FX gain/loss | Yes [^259^] | Yes [^256^] | Yes [^257^] | Yes |
| Period-end revaluation | Yes | Manual | Auto [^260^] | Auto |
| Multi-currency bank feeds | Yes [^256^] | Yes | Yes | Yes |
| Currency triangulation | No | No | Yes [^255^] | Yes |

### 7.2 Exchange Rate Management

```
┌─────────────────────────────────────────────────────────────┐
│                  Exchange Rate Service                       │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ External    │  │ Rate Cache  │  │ Override Management │ │
│  │ Provider    │  │ (daily      │  │ (user can lock      │ │
│  │ (ECB, OANDA,│  │  rates)     │  │  rates per txn)     │ │
│  │  XE)        │  │             │  │                     │ │
│  └──────┬──────┘  └─────────────┘  └─────────────────────┘ │
│         │                                                   │
│  ┌──────▼──────────────────────────────────────────────┐   │
│  │  Rate Types:                                         │   │
│  │  • Spot rate (transaction date)                      │   │
│  │  • Average rate (monthly average)                    │   │
│  │  • Historical rate (agreed/contract rate)            │   │
│  │  • Closing rate (period-end revaluation)             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Rate Update Frequency**: Daily automatic updates with manual override capability [^259^]. Lock specific rates for contracts or forward agreements.

### 7.3 FX-Adjusted Matching

For foreign currency bank accounts, matching must consider exchange rate differences:

**Matching Algorithm**:
1. Compare amounts in original currency first (exact match)
2. If original currency matches, compare functional currency equivalents
3. Allow for small FX variance (e.g., $0.50 equivalent) due to rate timing
4. Record FX gain/loss automatically for settlement differences [^255^]

### 7.4 Realized vs. Unrealized Gain/Loss

**Automatic Calculation** [^255^][^259^]:
- **Realized gain/loss**: When a foreign currency transaction settles at a different rate than originally recorded. System auto-calculates: `(Settlement Rate - Transaction Rate) × Foreign Amount`
- **Unrealized gain/loss**: At period-end, revalue open foreign currency balances using closing rate. `(Closing Rate - Transaction Rate) × Remaining Foreign Amount`

**Period-End Revaluation Process**:
1. Identify all open foreign currency transactions
2. Apply closing exchange rates to each
3. Calculate unrealized gain/loss per transaction
4. Post summary journal entry: Dr/Cr Unrealized Gain/Loss, Cr/Dr FX Revaluation Account
5. Generate reversing entry for first day of next period (optional) [^255^]

### 7.5 Currency Triangulation

Support complex scenarios [^255^]:
- UK vendor invoice in GBP
- European entity operating in EUR
- Payment from a USD bank account
- System automatically manages: bank-to-entity rates, payment-to-entity rates, payment-to-bank rates

---

## 8. Statement Import Fallback

### 8.1 Supported Import Formats

When bank feeds are unavailable, users can manually import statements. Based on compatibility analysis [^274^][^276^][^278^][^284^]:

| Format | Extension | Structure | Duplicate Prevention | Software Support |
|--------|-----------|-----------|---------------------|------------------|
| **OFX** | `.ofx` | XML/SGML standard | FITID per transaction [^276^] | Xero, QB, Quicken, Sage, Wave [^274^] |
| **QBO** | `.qbo` | OFX + Intuit headers | FITID per transaction [^276^] | QuickBooks Desktop & Online [^274^] |
| **QIF** | `.qif` | Text tags (D=date, T=amount, P=payee) | None (deprecated) [^274^] | Quicken legacy, GnuCash, Moneydance [^274^] |
| **CSV** | `.csv` | Flat table, comma-delimited | Manual (hash-based) | Universal — all software [^276^] |

### 8.2 Format Selection Guide

| Scenario | Recommended Format | Reason |
|----------|-------------------|--------|
| Importing to QuickBooks Desktop | QBO | Native import, no column mapping, auto-dedup via FITID [^276^] |
| Multi-software environment | OFX | Broadest compatibility, rich metadata, auto-mapped [^276^] |
| Universal fallback | CSV | Works everywhere, flexible, easy to inspect [^276^] |
| Automatic bank feeds | OFX | Required standard for automated feeds [^284^] |

### 8.3 CSV Import Column Mapping

Since CSV has no standardized schema [^276^], implement smart column mapping:

**Required columns** (user maps or auto-detected):
- Date — auto-detect format (DD/MM/YYYY vs MM/DD/YYYY from locale)
- Amount — positive/negative or separate Debit/Credit columns
- Description / Payee / Narrative
- Optional: Reference, Transaction Type, Running Balance

**Auto-detection heuristics**:
- Header name matching (case-insensitive): "date", "transaction date", "posted date"
- Amount detection: single column with negatives, or separate debit/credit columns
- Currency detection: from file extension hint, bank name in filename, or column content

### 8.4 Import Process

```
1. User uploads file (OFX/QBO/QIF/CSV)
2. Parse file format (auto-detect if extension unclear)
3. Extract transactions
4. Deduplicate (FITID for OFX/QBO, hash for CSV)
5. Normalize to canonical schema (Section 2.3)
6. Validate (required fields present, dates parseable, amounts numeric)
7. Preview for user confirmation
8. Import to staging
9. Run matching engine
10. Present results
```

---

## 9. Reconciliation Reports

### 9.1 Bank Reconciliation Statement

Standard report comparing bank statement to ledger balance [^357^]:

```
BANK RECONCILIATION STATEMENT
Account: [Bank Account Name] | Currency: [USD]
Period: [Start Date] to [End Date]

BANK STATEMENT BALANCE:                          $XX,XXX.XX

Add: Deposits in Transit
  [Date] [Description]                            $X,XXX.XX
  [Date] [Description]                            $X,XXX.XX
                                                  ─────────
Total Deposits in Transit                         $X,XXX.XX

Less: Outstanding Checks
  [Date] [Check #] [Payee]                        ($XXX.XX)
  [Date] [Check #] [Payee]                        ($XXX.XX)
                                                  ─────────
Total Outstanding Checks                         ($X,XXX.XX)

Less: Unreconciled Bank Items
  [Date] [Description] [Reason]                   ($XXX.XX)
                                                  ─────────
Adjusted Bank Balance                             $XX,XXX.XX

BOOK BALANCE (GL):                                $XX,XXX.XX

Add: Unreconciled Book Items
  [Date] [Description] [Reason]                    $XXX.XX
Less: Timing Differences                          ($XXX.XX)
                                                  ─────────
Adjusted Book Balance                             $XX,XXX.XX

═══════════════════════════════════════════════════════════════
RECONCILED: ✓ (or Variance: $XX.XX if not balanced)
═══════════════════════════════════════════════════════════════
```

### 9.2 Unreconciled Items Report (Aging)

Track outstanding items by age bucket [^344^][^350^]:

| Age Bucket | Count | Amount | % of Total | Trend vs Last Period |
|------------|-------|--------|------------|---------------------|
| 0-30 days | XXX | $XX,XXX | XX% | ↑/↓ |
| 31-60 days | XX | $X,XXX | XX% | ↑/↓ |
| 61-90 days | XX | $X,XXX | XX% | ↑/↓ |
| 90+ days | X | $XXX | X% | ↑/↓ |
| **Total** | **XXX** | **$XX,XXX** | **100%** | |

### 9.3 Drift Detection

**Purpose**: Identify reconciliation quality degradation over time

**Metrics to Track**:
| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| Auto-match rate | % transactions auto-reconciled | <70% triggers review |
| Exception rate | % transactions flagged as exceptions | >15% triggers review |
| Average time to reconcile | Mean hours from import to reconcile | >48h for high-volume accounts |
| Unreconciled aging | Items >30 days as % of total | >10% triggers escalation |
| Duplicate rate | Duplicates found per 1,000 transactions | >5 triggers review |
| FX variance | Average FX gain/loss per foreign txn | >2% of transaction value |

### 9.4 Cash in Transit Report

All unreconciled items from the system side (checks, transfers, deposits, payroll) that are temporary and will clear once transactions appear on bank statements [^357^].

### 9.5 GL to Bank Reconciliation Report

Compares GL cash account balance against bank account balance, displaying unreconciled GL journal entries and unreconciled bank statement lines [^357^]. One unique GL cash account should be assigned per bank account.

---

## 10. AI Matching System

### 10.1 Architecture Overview

Based on Xero JAX [^345^][^346^][^349^], With Otto SmartMatch [^282^], and ChatFin AI reconciliation agents [^280^]:

```
┌──────────────────────────────────────────────────────────────┐
│                    AI Matching Engine                         │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Feature      │  │ ML Model     │  │ Confidence       │   │
│  │ Engineering  │  │ (per-org)    │  │ Scoring          │   │
│  │              │  │              │  │                  │   │
│  │ • Amount     │  │ RandomForest │  │ • 90%+ = Auto    │   │
│  │ • Date       │  │ Classifier   │  │ • 60-89% =       │   │
│  │ • Merchant   │  │              │  │   Suggest        │   │
│  │ • Desc       │  │ Trained on   │  │ • <60% = Flag    │   │
│  │ • History    │  │ 12 months    │  │                  │   │
│  │ • Context    │  │ historical   │  │ • Multiple       │   │
│  │ • User       │  │ data [^352^] │  │   candidates =   │   │
│  │   patterns   │  │              │  │   ranked         │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Explainability Layer (Xero-style)                    │    │
│  │  Each match shows: "Rule", "Match", "Memory",         │    │
│  │  or "Prediction" with reasoning [^345^][^351^]        │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### 10.2 Feature Engineering

| Feature Category | Features | Weight |
|------------------|----------|--------|
| **Amount** | Exact match, proportional difference, rounding patterns | High |
| **Temporal** | Day difference, day of week, time of day, seasonality | Medium |
| **Text** | Description similarity (Levenshtein), merchant match, keyword overlap | High |
| **Reference** | Exact/partial reference number match, pattern matching | High |
| **Historical** | How user categorized similar transactions before [^345^] | Very High |
| **Contextual** | Broader patterns from anonymized user data (crowd-sourced) [^356^] | Medium |
| **Structural** | Transaction type, payment method, pending vs posted | Low |

### 10.3 Confidence Scoring

**Scoring Tiers** [^282^][^345^]:

| Score Range | Action | Explanation |
|-------------|--------|-------------|
| 95-100% | Auto-reconcile (if enabled) | Strong match on all dimensions |
| 90-94% | Auto-reconcile (conservative mode only) | Strong match, minor uncertainty |
| 75-89% | Suggest to user | Good match, needs review |
| 60-74% | Suggest with caveat | Possible match, flag for attention |
| <60% | Exception / no suggestion | Insufficient confidence |

**With Otto SmartMatch approach**: Only auto-reconciles when confidence ≥90%, flags lower-confidence for human review [^282^].

### 10.4 Per-Organization Model Training

Following Xero JAX's approach [^345^][^352^]:

1. **Collect historical data**: Download up to 12 months of past reconciliation decisions
2. **Feature extraction**: Transform raw transaction data into feature vectors
3. **Label creation**: Successful manual reconciliations = positive labels; incorrect suggestions = negative labels
4. **Model training**: Random Forest classifier per organization
5. **Calibration**: Calibrate probability outputs to confidence scores
6. **Continuous learning**: Model retrains periodically as new reconciliation decisions are made

**Why per-organization**: A trades business buying from the same suppliers weekly gets accurate suggestions fast. A business with irregular, varied spending takes longer for the model to learn [^345^].

### 10.5 Explainability

Every AI match must be explainable (following Xero's pattern [^345^][^351^]):

| Match Type | Explanation Pattern |
|------------|-------------------|
| **Rule** | "Matched bank rule 'Spotify Subscription': description contains 'SPOTIFY' and amount between $5-$20" |
| **Match** | "Matched existing Bill #1234 from Spotify: same amount ($15.99) and reference 'INV-5678'" |
| **Memory** | "You usually categorize transactions from 'ACME Corp' to 'Office Supplies' (94% historical rate)" |
| **Prediction** | "Similar businesses categorize this type of transaction to 'Software Subscriptions'" |

### 10.6 LLM Integration for Ambiguous Matches

For transactions that don't match traditional patterns, use LLM-powered analysis:

**Prompt Engineering Strategy**:
```
Given this bank transaction:
- Description: "ACH DEBIT XYZ PROCESSING 0927"
- Amount: $1,247.50
- Date: 2024-09-27
- Account: Business Checking

And these unmatched ledger entries:
1. Bill #INV-4421: ACME Supplies, $1,247.50, due 2024-09-25
2. Bill #INV-4403: Global Services, $1,247.50, due 2024-09-20

Analyze:
1. Which ledger entry is most likely to match this transaction?
2. What is your confidence level (HIGH/MEDIUM/LOW)?
3. What signals support your conclusion?
```

**LLM Confidence Calibration**:
- Use LLM as a feature in the ML model, not a replacement
- Combine traditional signal scores with LLM semantic understanding
- Validate LLM suggestions against hard constraints (exact amount matches)

---

## 11. Formance Platform Integration Reference

### 11.1 Formance Architecture

Formance provides an open-source programmable ledger with complementary services [^172^]:

- **Ledger**: Core financial tracking with built-in bi-temporality
- **Connectivity**: Networks connectivity layer for payment rails and bank integrations
- **Flows**: Customizable flow-of-funds orchestration
- **Native Reconciliation**: Integrated account-based reconciliation monitoring

### 11.2 Key Differences from This Design

| Aspect | Formance | This Design |
|--------|----------|-------------|
| Open source | Yes (ledger) | Hybrid (core open, matching proprietary) |
| Bank connectivity | Separate module | Integrated pipeline |
| Auto-posting | Syncs but doesn't auto-post [^172^] | Full auto-reconciliation with rules |
| Reconciliation | Account-based monitoring | Transaction-level matching engine |
| AI matching | Not built-in | Per-organization ML model |

---

## 12. API Design

### 12.1 Key Endpoints

```
# Bank Connections
POST   /api/v1/bank-connections                    # Connect bank via aggregator
GET    /api/v1/bank-connections                    # List connections
DELETE /api/v1/bank-connections/:id                # Disconnect
POST   /api/v1/bank-connections/:id/refresh        # Force refresh

# Bank Transactions
GET    /api/v1/bank-accounts/:id/transactions      # List transactions
POST   /api/v1/bank-accounts/:id/import            # Import statement file
GET    /api/v1/transactions/:id                    # Get transaction detail

# Reconciliation
POST   /api/v1/transactions/:id/match              # Find matches
POST   /api/v1/transactions/:id/confirm            # Confirm match
POST   /api/v1/transactions/:id/create-entry       # Create ledger entry
GET    /api/v1/bank-accounts/:id/reconciliation     # Get reconciliation status
POST   /api/v1/bank-accounts/:id/reconcile         # Run reconciliation

# Bank Rules
GET    /api/v1/bank-rules                          # List rules
POST   /api/v1/bank-rules                          # Create rule
PUT    /api/v1/bank-rules/:id                      # Update rule
DELETE /api/v1/bank-rules/:id                      # Delete rule
POST   /api/v1/bank-rules/reorder                  # Reorder rules

# Reports
GET    /api/v1/bank-accounts/:id/reconciliation-report  # Reconciliation statement
GET    /api/v1/bank-accounts/:id/unreconciled-items     # Aging report
GET    /api/v1/reconciliation/metrics                   # Drift detection metrics
```

---

## 13. Data Model

### 13.1 Core Tables

```sql
-- Bank connections via aggregators
bank_connections (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL,
  bank_name VARCHAR(255),
  account_name VARCHAR(255),
  account_type VARCHAR(50), -- checking, savings, credit_card
  account_number_masked VARCHAR(20),
  currency CHAR(3),
  aggregator VARCHAR(50), -- plaid, truelayer, salt_edge, yodlee
  aggregator_connection_id VARCHAR(255),
  aggregator_account_id VARCHAR(255),
  status VARCHAR(20), -- active, disconnected, error
  last_sync_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Raw bank transactions from feeds
bank_transactions (
  id UUID PRIMARY KEY,
  connection_id UUID REFERENCES bank_connections,
  organization_id UUID NOT NULL,
  
  -- From aggregator
  aggregator_transaction_id VARCHAR(255) NOT NULL,
  amount DECIMAL(15,2) NOT NULL,
  currency CHAR(3) NOT NULL,
  transaction_date DATE NOT NULL,
  value_date TIMESTAMP,
  description TEXT,
  merchant_name VARCHAR(255),
  merchant_category VARCHAR(100),
  reference VARCHAR(255),
  transaction_type VARCHAR(50), -- debit, credit, transfer, fee
  payment_method VARCHAR(50), -- ach, wire, card, check
  status VARCHAR(20), -- pending, posted, cancelled
  counterparties JSONB,
  raw_data JSONB,
  
  -- Matching
  match_status VARCHAR(20) DEFAULT 'unmatched', -- unmatched, suggested, confirmed, reconciled, excluded
  matched_transaction_id UUID, -- references ledger transaction
  match_confidence DECIMAL(5,2),
  match_type VARCHAR(20), -- exact, rule, fuzzy, ml, manual
  matched_by_rule_id UUID,
  matched_at TIMESTAMP,
  
  -- Deduplication
  dedup_hash VARCHAR(64),
  
  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(aggregator_transaction_id, connection_id)
);

-- Bank rules
bank_rules (
  id UUID PRIMARY KEY,
  organization_id UUID NOT NULL,
  bank_account_id UUID REFERENCES bank_connections, -- null = all accounts
  rule_name VARCHAR(255) NOT NULL,
  rule_type VARCHAR(20) NOT NULL, -- spend_money, receive_money, transfer
  conditions JSONB NOT NULL, -- array of condition objects
  condition_logic VARCHAR(10) DEFAULT 'AND', -- AND, OR
  actions JSONB NOT NULL,
  auto_apply BOOLEAN DEFAULT FALSE,
  priority INTEGER DEFAULT 100,
  active BOOLEAN DEFAULT TRUE,
  match_count INTEGER DEFAULT 0,
  created_by UUID,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Reconciliation sessions
reconciliation_sessions (
  id UUID PRIMARY KEY,
  bank_account_id UUID REFERENCES bank_connections,
  organization_id UUID NOT NULL,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  statement_balance DECIMAL(15,2),
  ledger_balance DECIMAL(15,2),
  adjusted_balance DECIMAL(15,2),
  status VARCHAR(20), -- in_progress, completed, variance
  variance_amount DECIMAL(15,2),
  completed_at TIMESTAMP,
  completed_by UUID,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Exchange rates
exchange_rates (
  id UUID PRIMARY KEY,
  from_currency CHAR(3) NOT NULL,
  to_currency CHAR(3) NOT NULL,
  rate DECIMAL(18,8) NOT NULL,
  rate_type VARCHAR(20), -- spot, average, closing, historical
  rate_date DATE NOT NULL,
  source VARCHAR(50), -- ECB, OANDA, manual
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(from_currency, to_currency, rate_type, rate_date)
);
```

---

## 14. Implementation Roadmap

### Phase 1: Foundation (Months 1-2)
- [ ] Core data model and database schema
- [ ] Plaid integration (primary for US/CA/UK/EU)
- [ ] Basic ingestion pipeline (Poll → Normalize → Store)
- [ ] Manual transaction import (CSV, OFX)
- [ ] Basic exact-match reconciliation

### Phase 2: Matching Engine (Months 3-4)
- [ ] Fuzzy matching with date tolerance
- [ ] Bank rules engine (create, manage, execute)
- [ ] Suggest/Auto-apply workflow
- [ ] Exception handling and aging
- [ ] Reconciliation reports (bank rec statement, unreconciled items)

### Phase 3: Scale & Intelligence (Months 5-6)
- [ ] Additional aggregators (TrueLayer for EU, Salt Edge for global)
- [ ] Multi-currency reconciliation with FX handling
- [ ] ML matching engine (per-organization Random Forest)
- [ ] AI matching with confidence scoring
- [ ] Drift detection and monitoring dashboards

### Phase 4: Polish & Optimization (Months 7-8)
- [ ] LLM integration for ambiguous matches
- [ ] Advanced analytics (reconciliation trends, advisor insights)
- [ ] Performance optimization (bulk operations, caching)
- [ ] Audit trail and compliance reporting

---

## 15. Key Citations

| Citation | Source | Topic |
|----------|--------|-------|
| [^172^] | Formance Platform | Open-source ledger + connectivity + reconciliation |
| [^220^] | Aico.ai | Reconciliation process steps and documentation |
| [^221^] | Databricks | Data ingestion reference architecture |
| [^222^] | Unstructured.io | Scalable data ingestion pipeline design |
| [^254^] | OpenBankingTracker | Yodlee 17,000+ institution coverage |
| [^255^] | Gravity Software | Multi-currency accounting features |
| [^256^] | Tofu Blog | Multi-currency software comparison (Xero, QBO) |
| [^257^] | AlphaBold | NetSuite multi-currency handling |
| [^258^] | OpenBankingTracker | Plaid 12,000+ institutions, 20 markets |
| [^259^] | Moneypex | Multi-currency features comparison table |
| [^260^] | DualEntry | Multi-entity consolidation accounting |
| [^261^] | Finexer Blog | Plaid vs TrueLayer vs Finexer comparison |
| [^263^] | NetSuite | Multicurrency accounting best practices |
| [^265^] | Temenos/SaltEdge | Salt Edge 3,000+ institutions in 60+ countries |
| [^266^] | Yapily Blog | TrueLayer alternatives comparison |
| [^274^] | InvoiceDataExtraction | OFX/QFX/QIF format comparison |
| [^276^] | CapyParse | QBO vs OFX vs CSV format comparison |
| [^277^] | BankReconciler | Xero bank reconciliation rules guide |
| [^278^] | MeetGlimpse | Financial file format comparison guide |
| [^279^] | Xero Official | JAX automatic bank reconciliation FAQ |
| [^280^] | ChatFin.ai | AI reconciliation agents development guide |
| [^281^] | FastLane | Xero bank rules setup guide |
| [^282^] | WithOtto | AI confidence-based reconciliation |
| [^283^] | Tofu Blog | QuickBooks Desktop import limitations |
| [^284^] | EasyBankConvert | QIF vs OFX vs CSV comparison table |
| [^338^] | Solvexia | Bank reconciliation steps and best practices |
| [^339^] | Zone&Co | Bank reconciliation process improvement |
| [^340^] | InvoiceDataExtraction | Common reconciliation discrepancies |
| [^341^] | ReconcileOS | Settlement mismatch troubleshooting |
| [^342^] | Abstra.io | Reconciliation discrepancy investigation |
| [^343^] | Irvine Bookkeeping | Common bank reconciliation errors |
| [^344^] | Numeric | Bank reconciliation steps and best practices |
| [^345^] | Digit Business | Xero JAX AI tools analysis |
| [^346^] | Xero Blog | JAX AI vision and roadmap |
| [^347^] | Finman | Xero auto bank reconciliation beta details |
| [^348^] | Plaid Docs | Transactions API introduction |
| [^349^] | Xero Official | AI accounting features |
| [^350^] | Hyperbots | Reconciliation aging definition |
| [^351^] | Xero Central | Auto bank reconciliation powered by JAX |
| [^352^] | WithOtto | Xero + AI integration technical details |
| [^356^] | Xero Press | ML-powered bank reconciliation predictions |
| [^357^] | UNDP POPP | Cash to GL reconciliation report |
| [^358^] | Plaid API Docs | Transactions API response schema |

---

*Document generated for accounting system design — Dimension 06: Bank Feed Integration & Reconciliation*
