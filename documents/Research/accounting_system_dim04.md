# Dimension 04: Multi-Currency & Foreign Exchange Management

## Executive Summary

This document presents the complete architectural design for a multi-currency accounting system compliant with IAS 21 *The Effects of Changes in Foreign Exchange Rates*. The system supports functional currency per entity, transaction currency recording, presentation currency translation, automated exchange rate feeds from ECB/XE/Open Exchange Rates, period-end revaluation of monetary items, realized/unrealized FX gain/loss tracking, multi-currency bank accounts, and cryptocurrency holdings under IAS 38. All design decisions are evidence-based with citations to authoritative sources.

---

## 1. Currency Model

### 1.1 Three-Currency Architecture (IAS 21 Framework)

IAS 21 establishes a three-layer currency model that every transaction and entity must navigate [^88^][^432^]:

| Currency Type | Definition | Determination |
|---------------|------------|---------------|
| **Functional Currency** | The currency of the primary economic environment in which the entity operates | Determined by primary/secondary indicators; not freely chosen |
| **Transaction Currency** | The currency in which a transaction is denominated or requires settlement | The actual currency of the invoice, payment, or contract |
| **Presentation/Reporting Currency** | The currency in which financial statements are presented | May differ from functional currency; chosen for reporting purposes |

#### 1.1.1 Functional Currency Determination

Per IAS 21 paragraphs 9-14, the functional currency is determined through a hierarchical assessment of indicators [^239^][^246^][^250^]:

**Primary Indicators** (given priority):
1. The currency that mainly influences sales prices for goods and services
2. The currency of the country whose competitive forces and regulations mainly determine sales prices
3. The currency that mainly influences labour, material, and other costs

**Secondary Indicators** (supporting evidence):
1. The currency in which financing activities are denominated
2. The currency in which receipts from operating activities are usually retained

**Additional Factors** (when indicators are mixed):
- Whether the foreign operation's activities are carried out as an extension of the reporting entity
- The proportion of transactions with the reporting entity
- Whether cash flows are directly available to the reporting entity

```sql
-- Functional currency determination stored per entity
CREATE TABLE entity_functional_currency (
    entity_id              UUID PRIMARY KEY REFERENCES entities(id),
    functional_currency    CHAR(3) NOT NULL,           -- ISO 4217 code
    determination_basis    TEXT NOT NULL,               -- Documentation of rationale
    primary_indicators     JSONB NOT NULL,              -- {"revenue_currency": "USD", "cost_currency": "USD", ...}
    secondary_indicators   JSONB,                       -- {"financing_currency": "USD", ...}
    effective_from         DATE NOT NULL,
    effective_to           DATE,                        -- NULL = current
    changed_by_user_id     UUID REFERENCES users(id),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_iso_currency CHECK (functional_currency ~ '^[A-Z]{3}$')
);
```

A change in functional currency is permitted only when there is a change in the underlying transactions, events, and conditions. It is applied prospectively from the date of change -- no restatement of prior periods [^246^].

### 1.2 Currency Registry

The system maintains a master currency registry based on ISO 4217, extended to support crypto-assets:

```sql
CREATE TABLE currencies (
    code                    CHAR(3) PRIMARY KEY,        -- ISO 4217 (e.g., USD, EUR) or custom code
    numeric_code            CHAR(3) UNIQUE,             -- ISO 4217 numeric (e.g., 840)
    name                    VARCHAR(100) NOT NULL,
    symbol                  VARCHAR(10),                -- $, EUR, GBP
    decimal_places          SMALLINT NOT NULL DEFAULT 2,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    is_fiat                 BOOLEAN NOT NULL DEFAULT TRUE,  -- FALSE for crypto/internal
    is_crypto               BOOLEAN NOT NULL DEFAULT FALSE,
    crypto_parent_chain     VARCHAR(50),                -- e.g., "Ethereum", "Bitcoin"
    rounding_unit           DECIMAL(20,10) NOT NULL DEFAULT 0.01,
    -- IAS 21 specific
    can_be_functional       BOOLEAN NOT NULL DEFAULT TRUE,
    can_be_transactional    BOOLEAN NOT NULL DEFAULT TRUE,
    can_be_presentation     BOOLEAN NOT NULL DEFAULT TRUE,
    -- Metadata
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 1.3 Entity Currency Settings

Each entity has explicit currency configuration:

```sql
CREATE TABLE entity_currency_settings (
    entity_id               UUID PRIMARY KEY REFERENCES entities(id),
    functional_currency     CHAR(3) NOT NULL REFERENCES currencies(code),
    presentation_currency   CHAR(3) REFERENCES currencies(code),  -- NULL = same as functional
    reporting_currencies    JSONB,  -- ["USD", "EUR"] for multi-reporting
    exchange_rate_type_default VARCHAR(20) DEFAULT 'SPOT',
    revaluation_method      VARCHAR(20) NOT NULL DEFAULT 'PERIOD_END',
    unrealized_gain_account_id UUID REFERENCES chart_of_accounts(id),
    unrealized_loss_account_id UUID REFERENCES chart_of_accounts(id),
    realized_gain_account_id   UUID REFERENCES chart_of_accounts(id),
    realized_loss_account_id   UUID REFERENCES chart_of_accounts(id),
    cta_account_id             UUID REFERENCES chart_of_accounts(id),  -- Cumulative Translation Adjustment
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 2. Exchange Rate Service

### 2.1 Service Architecture

The Exchange Rate Service is a dedicated microservice that provides rate lookup with caching, supporting multiple providers with failover:

```
+------------------+     +------------------+     +------------------+
|  Accounting      |     |  Exchange Rate   |     |  External APIs   |
|  System (GL)     |<--->|  Service         |<--->|  - ECB SDMX      |
|                  |     |                  |     |  - XE.com        |
|  Rate Lookup     |     |  - Cache (Redis) |     |  - Open Exchange |
|  via REST/gRPC   |     |  - Rate Database |     |  - Manual Entry  |
|                  |     |  - Provider Mgr  |     |                  |
+------------------+     +------------------+     +------------------+
```

### 2.2 Exchange Rate Types

Following SAP's proven pattern [^415^][^418^], the system supports multiple rate types for different business purposes:

| Rate Type | Code | Purpose | Source |
|-----------|------|---------|--------|
| **Spot** | SPOT | Daily market rate for transaction conversion | ECB, XE, OXR |
| **Closing** | CLOS | Period-end rate for revaluation | ECB, XE, OXR |
| **Average** | AVG | Monthly average for P&L translation | Calculated from daily rates |
| **Bank Buy** | BKBY | Bank buying rate for receipts | User-defined |
| **Bank Sell** | BKSL | Bank selling rate for payments | User-defined |
| **Corporate** | CORP | Internal group rate for intercompany | Corporate treasury |
| **Historical** | HIST | Rate at transaction date (frozen) | Transaction snapshot |
| **Budget** | BUDG | Budget/planning rate | User-defined |

```sql
CREATE TABLE exchange_rate_types (
    code            VARCHAR(10) PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    is_system       BOOLEAN NOT NULL DEFAULT FALSE,  -- Cannot be deleted
    precision_digits SMALLINT NOT NULL DEFAULT 6,
    inversion_method VARCHAR(20) NOT NULL DEFAULT 'DIRECT',  -- DIRECT or INDIRECT
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 2.3 Rate Storage

Inspired by SAP's TCURR table design [^415^][^420^]:

```sql
CREATE TABLE exchange_rates (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_currency       CHAR(3) NOT NULL REFERENCES currencies(code),
    to_currency         CHAR(3) NOT NULL REFERENCES currencies(code),
    rate_type           VARCHAR(10) NOT NULL REFERENCES exchange_rate_types(code),
    
    -- Rate value with high precision (matches SAP's DEC 9,5)
    rate_value          DECIMAL(18,10) NOT NULL,
    
    -- Scaling factors for cross-rate derivation (from_currency_units / to_currency_units)
    from_factor         DECIMAL(9,0) NOT NULL DEFAULT 1,  -- FFACT equivalent
    to_factor           DECIMAL(9,0) NOT NULL DEFAULT 1,  -- TFACT equivalent
    
    -- Temporal validity
    valid_from          DATE NOT NULL,
    valid_to            DATE NOT NULL DEFAULT '9999-12-31',
    
    -- Source tracking (audit trail)
    source_provider     VARCHAR(50) NOT NULL,  -- "ECB", "XE", "OXR", "MANUAL", "DERIVED"
    source_reference    VARCHAR(255),           -- API endpoint, batch ID, or user ID
    source_timestamp    TIMESTAMPTZ,            -- When provider published the rate
    
    -- Attribution
    created_by          UUID REFERENCES users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Cross-rate derivation metadata
    is_derived          BOOLEAN NOT NULL DEFAULT FALSE,
    derived_from_rate_1 UUID REFERENCES exchange_rates(id),
    derived_from_rate_2 UUID REFERENCES exchange_rates(id),
    
    CONSTRAINT different_currencies CHECK (from_currency <> to_currency),
    CONSTRAINT positive_rate CHECK (rate_value > 0),
    UNIQUE(from_currency, to_currency, rate_type, valid_from)
);

CREATE INDEX idx_exchange_rates_lookup 
    ON exchange_rates(from_currency, to_currency, rate_type, valid_from, valid_to);
CREATE INDEX idx_exchange_rates_validity 
    ON exchange_rates(valid_from, valid_to) WHERE valid_to = '9999-12-31';
```

### 2.4 External Provider Integration

#### 2.4.1 ECB (European Central Bank) - Free

The ECB provides daily euro foreign exchange reference rates via SDMX REST API [^224^][^225^][^227^]:

- **Endpoint**: `https://sdw-wsrest.ecb.europa.eu/service/data/EXR/D.{currency}.EUR.SP00.A`
- **Format**: SDMX-ML (XML) or JSON
- **Frequency**: Updated every working day at ~16:00 CET
- **Coverage**: ~30 currencies against EUR
- **Cost**: Free
- **Limitation**: EUR is the only base currency; cross-rates must be derived

```python
# ECB SDMX rate fetcher (simplified)
class ECBRateProvider:
    BASE_URL = "https://sdw-wsrest.ecb.europa.eu/service/data/EXR"
    
    def fetch_daily_rates(self, date: datetime.date) -> list[ExchangeRate]:
        """Fetch all EUR-based rates for a given date."""
        rates = []
        for currency in SUPPORTED_CURRENCIES:
            if currency == "EUR":
                continue
            series_key = f"D.{currency}.EUR.SP00.A"
            url = f"{self.BASE_URL}/{series_key}"
            response = requests.get(url, headers={"Accept": "application/json"})
            data = response.json()
            rate_value = parse_observation(data, date)
            rates.append(ExchangeRate(
                from_currency=currency,
                to_currency="EUR",
                rate_type="SPOT",
                rate_value=rate_value,
                source_provider="ECB",
                valid_from=date,
                source_timestamp=datetime.now(timezone.utc)
            ))
        return rates
    
    def derive_cross_rate(self, from_curr: str, to_curr: str, date: date) -> Decimal:
        """Derive non-EUR cross-rate via EUR: USD/GBP = (USD/EUR) / (GBP/EUR)"""
        if from_curr == "EUR":
            return self.get_rate("EUR", to_curr, date)
        if to_curr == "EUR":
            return self.get_rate(from_curr, "EUR", date)
        rate_via_eur = self.get_rate(from_curr, "EUR", date) / self.get_rate(to_curr, "EUR", date)
        return rate_via_eur
```

#### 2.4.2 XE.com - Premium

XE Currency Data API provides enterprise-grade rates [^272^][^449^][^451^]:

- **Coverage**: 130+ currencies
- **Frequency**: Real-time to hourly
- **Format**: JSON, XML
- **Cost**: ~$799/month (enterprise)
- **Base Currency**: Any (unlike ECB's EUR-only)
- **Features**: Historical rates, monthly averages, volatility data
- **Used by**: Xero (hourly rate updates) [^147^][^451^]

#### 2.4.3 Open Exchange Rates - Mid-Tier

Open Exchange Rates provides developer-friendly pricing [^241^][^249^]:

- **Coverage**: 200+ currencies
- **Frequency**: Hourly (free), up to real-time (paid)
- **Format**: JSON
- **Cost**: Free tier (1,000 req/month, USD base only); Paid from $12/month
- **Features**: Time-series, OHLC data, historical rates

#### 2.4.4 Provider Selection Strategy

```yaml
exchange_rate_service:
  providers:
    - name: ECB
      priority: 1
      enabled: true
      use_for: [EUR_BASED, CLOSING]
      rate_limit: "daily"  # Only weekdays
    - name: XE
      priority: 2
      enabled: true
      use_for: [ALL_CURRENCIES, REAL_TIME]
      api_key: "${XE_API_KEY}"
    - name: OpenExchangeRates
      priority: 3
      enabled: true
      use_for: [HISTORICAL, BACKUP]
      api_key: "${OXR_API_KEY}"
    - name: Manual
      priority: 99
      enabled: true
      use_for: [OVERRIDE, CORPORATE_RATES]
  
  failover:
    strategy: "priority_cascade"  # Try ECB first, then XE, then OXR
    stale_threshold_hours: 24
    alert_on_failover: true
  
  caching:
    redis_ttl_seconds: 3600  # 1 hour for current rates
    historical_ttl_days: 30
```

### 2.5 Average Rate Calculation

For IAS 21 compliance, average rates are computed from daily rates for income/expense translation [^88^][^445^]:

```sql
-- Monthly average rate calculation
CREATE OR REPLACE FUNCTION calculate_monthly_average(
    p_from_currency CHAR(3),
    p_to_currency CHAR(3),
    p_year INTEGER,
    p_month INTEGER
) RETURNS DECIMAL(18,10) AS $$
DECLARE
    v_avg_rate DECIMAL(18,10);
BEGIN
    SELECT AVG(rate_value) INTO v_avg_rate
    FROM exchange_rates
    WHERE from_currency = p_from_currency
      AND to_currency = p_to_currency
      AND rate_type = 'SPOT'
      AND EXTRACT(YEAR FROM valid_from) = p_year
      AND EXTRACT(MONTH FROM valid_from) = p_month;
    
    RETURN v_avg_rate;
END;
$$ LANGUAGE plpgsql;
```

> **IAS 21 Note**: "For practical reasons, a rate that approximates the exchange rates at the dates of the transactions, for example an average rate for the period, is often used. However, if exchange rates fluctuate significantly, the use of the average rate for a period is inappropriate." [^88^][^445^]

---

## 3. Transaction Recording

### 3.1 Initial Recognition at Spot Rate

Per IAS 21.21-22: "A foreign currency transaction shall be recorded, on initial recognition in the functional currency, by applying to the foreign currency amount the spot exchange rate between the functional currency and the foreign currency at the date of the transaction." [^88^][^412^]

**Key rules**:
- The **date of the transaction** is the date on which the transaction first qualifies for recognition under IFRS [^220^][^221^]
- Average rates may be used as a practical approximation if exchange rates do not fluctuate significantly [^88^]
- Each transaction stores both the **foreign currency amount** and the **functional currency equivalent**

### 3.2 Transaction Line Item Model

Every journal line in a foreign currency transaction stores three amounts:

```sql
CREATE TABLE journal_lines (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_id              UUID NOT NULL REFERENCES journals(id),
    line_number             INTEGER NOT NULL,
    
    -- Account reference
    account_id              UUID NOT NULL REFERENCES chart_of_accounts(id),
    
    -- Transaction currency (the original currency of the document)
    transaction_currency    CHAR(3) NOT NULL REFERENCES currencies(code),
    transaction_amount      DECIMAL(20,4) NOT NULL,
    transaction_dc          CHAR(1) NOT NULL CHECK (transaction_dc IN ('D', 'C')),
    
    -- Functional currency (entity's functional currency)
    functional_currency     CHAR(3) NOT NULL REFERENCES currencies(code),
    functional_amount       DECIMAL(20,4) NOT NULL,
    functional_dc           CHAR(1) NOT NULL CHECK (functional_dc IN ('D', 'C')),
    
    -- Conversion metadata (immutable audit trail)
    exchange_rate           DECIMAL(18,10) NOT NULL,
    exchange_rate_id        UUID REFERENCES exchange_rates(id),
    rate_date               DATE NOT NULL,       -- The transaction date
    rate_type_used          VARCHAR(10) NOT NULL DEFAULT 'SPOT',
    
    -- For reporting currency (optional third currency)
    reporting_currency      CHAR(3) REFERENCES currencies(code),
    reporting_amount        DECIMAL(20,4),
    reporting_exchange_rate DECIMAL(18,10),
    
    -- Narrative
    description             TEXT,
    
    -- Metadata
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by              UUID REFERENCES users(id),
    
    UNIQUE(journal_id, line_number)
);
```

### 3.3 Journal Entry Example: Foreign Currency Purchase

**Scenario**: UK entity (functional currency: GBP) purchases goods for EUR 100,000 when EUR/GBP = 0.85 on 2024-03-15. Payment due in 30 days.

```
Journal Entry: PI-2024-0315-001
Date: 2024-03-15
Description: Purchase of goods from European supplier

Line 1: Dr. Inventory (Non-monetary asset)
  Transaction: EUR 100,000.00 D
  Functional:  GBP 85,000.00 D  (@ 0.8500)
  
Line 2: Cr. Accounts Payable (Monetary liability)
  Transaction: EUR 100,000.00 C
  Functional:  GBP 85,000.00 C  (@ 0.8500)
```

The inventory (non-monetary) remains at GBP 85,000 permanently. The payable (monetary) will be revalued at period-end and at settlement.

### 3.4 Multi-Currency Journal Posting Process

```python
class MultiCurrencyJournalService:
    def post_foreign_currency_journal(self, journal: Journal) -> PostedJournal:
        for line in journal.lines:
            if line.transaction_currency == line.functional_currency:
                # Same currency - no conversion needed
                line.functional_amount = line.transaction_amount
                line.exchange_rate = Decimal("1.0")
            else:
                # Fetch spot rate at transaction date
                rate = self.rate_service.get_rate(
                    from_currency=line.transaction_currency,
                    to_currency=line.functional_currency,
                    rate_type="SPOT",
                    date=journal.transaction_date
                )
                line.exchange_rate = rate.rate_value
                line.exchange_rate_id = rate.id
                line.rate_type_used = "SPOT"
                
                # Convert using BigDecimal for precision
                line.functional_amount = (
                    line.transaction_amount * rate.rate_value
                ).quantize(line.functional_currency.rounding_unit)
                
                line.rate_date = journal.transaction_date
            
            # Validate: Sum of functional debits must equal sum of functional credits
            self._validate_balanced(journal)
        
        return self.ledger.post(journal)
```

---

## 4. Period-End Revaluation

### 4.1 IAS 21 Revaluation Requirements

At the end of each reporting period, IAS 21.23 requires [^88^][^412^][^416^]:

| Item Type | Translation Method | Exchange Rate |
|-----------|-------------------|---------------|
| **Monetary items** (cash, receivables, payables, loans) | Re-translated | **Closing rate** at reporting date |
| **Non-monetary items at historical cost** (PP&E, inventory at cost) | No retranslation | **Historical rate** at transaction date |
| **Non-monetary items at fair value** (investments, revalued assets) | Re-translated | Rate at date **fair value was determined** |

> "The essential feature of a monetary item is a right to receive (or an obligation to deliver) a fixed or determinable number of units of currency." [^88^][^417^][^419^]

### 4.2 Monetary vs Non-Monetary Classification

| Item | Classification | Revalued at Period-End? |
|------|---------------|------------------------|
| Cash and bank balances | Monetary | Yes - closing rate |
| Trade receivables | Monetary | Yes - closing rate |
| Trade payables | Monetary | Yes - closing rate |
| Loans receivable/payable | Monetary | Yes - closing rate |
| Prepayments (goods/services) | Non-monetary | No - historical rate |
| PP&E | Non-monetary | No - historical rate |
| Inventory | Non-monetary | No - historical rate |
| Intangible assets | Non-monetary | No - historical rate |
| Equity investments (at FV) | Non-monetary | Rate at FV measurement date |
| Contract liabilities | Non-monetary | No - historical rate |
| Provisions (cash settlement) | Monetary | Yes - closing rate |
| Goodwill | Non-monetary | No - treated as foreign op asset [^88^] |

### 4.3 Revaluation Process

```sql
-- Revaluation run tracking
CREATE TABLE revaluation_runs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id           UUID NOT NULL REFERENCES entities(id),
    revaluation_date    DATE NOT NULL,
    period_end_date     DATE NOT NULL,
    rate_type_used      VARCHAR(10) NOT NULL DEFAULT 'CLOS',
    closing_rate_date   DATE NOT NULL,
    
    status              VARCHAR(20) NOT NULL DEFAULT 'DRAFT',  -- DRAFT, POSTED, REVERSED
    
    -- Totals
    total_unrealized_gain   DECIMAL(20,4) NOT NULL DEFAULT 0,
    total_unrealized_loss   DECIMAL(20,4) NOT NULL DEFAULT 0,
    
    -- Summary by currency
    currency_breakdown      JSONB NOT NULL DEFAULT '[]',
    
    -- Journal posted
    revaluation_journal_id  UUID REFERENCES journals(id),
    
    -- Audit
    created_by              UUID NOT NULL REFERENCES users(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    posted_at               TIMESTAMPTZ,
    posted_by               UUID REFERENCES users(id),
    
    UNIQUE(entity_id, period_end_date, status) WHERE status = 'POSTED'
);

-- Individual revaluation line items
CREATE TABLE revaluation_lines (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    revaluation_run_id      UUID NOT NULL REFERENCES revaluation_runs(id),
    
    -- Source
    account_id              UUID NOT NULL REFERENCES chart_of_accounts(id),
    original_journal_line_id UUID REFERENCES journal_lines(id),
    
    -- Currency detail
    foreign_currency        CHAR(3) NOT NULL,
    foreign_currency_balance DECIMAL(20,4) NOT NULL,
    
    -- Original rate and amount
    original_rate           DECIMAL(18,10) NOT NULL,
    original_functional_amount DECIMAL(20,4) NOT NULL,
    
    -- Closing rate and revalued amount
    closing_rate            DECIMAL(18,10) NOT NULL,
    closing_rate_id         UUID REFERENCES exchange_rates(id),
    revalued_functional_amount DECIMAL(20,4) NOT NULL,
    
    -- Difference = unrealized gain/loss
    unrealized_gain         DECIMAL(20,4) NOT NULL DEFAULT 0,
    unrealized_loss         DECIMAL(20,4) NOT NULL DEFAULT 0,
    
    -- Whether this is a reversal of a prior revaluation
    is_reversal             BOOLEAN NOT NULL DEFAULT FALSE,
    prior_revaluation_line_id UUID REFERENCES revaluation_lines(id),
    
    -- Posted journal line reference
    gain_loss_journal_line_id UUID REFERENCES journal_lines(id)
);
```

### 4.4 Revaluation Journal Entry

**Continuing the example** from Section 3.3: At period-end (2024-03-31), EUR/GBP closing rate is 0.88.

```
Revaluation Run: REV-2024-Q1
Date: 2024-03-31

Analysis:
  Accounts Payable: EUR 100,000
  Original GBP value: GBP 85,000 (@ 0.8500)
  Revalued GBP value: GBP 88,000 (@ 0.8800)
  Unrealized Loss: GBP 3,000

Journal Entry:
  Dr. Unrealized FX Loss (P&L)    GBP 3,000
    Cr. Accounts Payable              GBP 3,000

[The payable is now carried at GBP 88,000 in functional currency]
```

On settlement (2024-04-15), if EUR/GBP = 0.87:
```
Settlement Entry:
  Dr. Accounts Payable            GBP 88,000  (revalued amount)
    Cr. Bank (EUR account)          EUR 100,000 -> GBP 87,000 (@ 0.8700)
    Cr. Realized FX Gain (P&L)      GBP 1,000  [88,000 - 87,000]

[Plus reversal of unrealized loss from prior period]
```

### 4.5 Reversal of Prior Period Revaluation

Following Oracle GL and Dynamics 365 patterns [^278^][^440^], prior period unrealized gains/losses are reversed at the start of the new period to avoid double-counting when the settlement occurs:

```sql
-- Reversal entry for prior period revaluation
CREATE OR REPLACE FUNCTION create_revaluation_reversal(
    p_prior_revaluation_id UUID,
    p_reversal_date DATE
) RETURNS UUID AS $$
DECLARE
    v_reversal_journal_id UUID;
BEGIN
    -- Create reversal journal that negates the prior revaluation
    INSERT INTO journals (entity_id, journal_date, description, status)
    SELECT entity_id, p_reversal_date, 
           'Reversal of revaluation ' || p_prior_revaluation_id,
           'DRAFT'
    FROM revaluation_runs WHERE id = p_prior_revaluation_id
    RETURNING id INTO v_reversal_journal_id;
    
    -- Reverse each line (swap debit/credit)
    INSERT INTO journal_lines (journal_id, account_id, ...)
    SELECT v_reversal_journal_id, account_id,
           -- Swap the gain/loss accounts and reverse amounts
           CASE WHEN unrealized_gain > 0 
                THEN -unrealized_gain  -- Reverse the prior gain
                ELSE unrealized_loss    -- Reverse the prior loss
           END
    FROM revaluation_lines
    WHERE revaluation_run_id = p_prior_revaluation_id;
    
    RETURN v_reversal_journal_id;
END;
$$ LANGUAGE plpgsql;
```

---

## 5. Realized Gains & Losses

### 5.1 Recognition Trigger

Realized FX gains/losses are recognized when a foreign currency monetary item is **settled** [^240^][^244^][^252^]. The realized gain/loss is the difference between:
- The functional currency amount at which the monetary item was **recorded** (after any revaluations)
- The functional currency amount of the **settlement proceeds/payment**

### 5.2 Settlement Journal Entry

```python
class RealizedGainLossService:
    def process_settlement(
        self,
        monetary_item_id: UUID,  # e.g., an invoice
        settlement_date: date,
        settlement_currency: str,
        settlement_amount: Decimal,
        bank_account_id: UUID
    ) -> SettlementResult:
        """Process settlement and calculate realized FX gain/loss."""
        
        # Get the current carrying amount of the monetary item
        item = self.ledger.get_monetary_item(monetary_item_id)
        carrying_fc_amount = item.functional_currency_balance
        
        # Convert settlement amount to functional currency at settlement rate
        settlement_rate = self.rate_service.get_rate(
            from_currency=settlement_currency,
            to_currency=item.functional_currency,
            rate_type="SPOT",
            date=settlement_date
        )
        settlement_fc_amount = settlement_amount * settlement_rate.rate_value
        
        # Calculate realized gain/loss
        if item.is_receivable:
            realized_gain_loss = settlement_fc_amount - carrying_fc_amount
        else:  # payable
            realized_gain_loss = carrying_fc_amount - settlement_fc_amount
        
        # Create settlement journal
        journal = SettlementJournal(
            date=settlement_date,
            entries=self._build_settlement_entries(
                item=item,
                carrying_amount=carrying_fc_amount,
                settlement_amount=settlement_fc_amount,
                realized_gain_loss=realized_gain_loss,
                bank_account_id=bank_account_id
            )
        )
        
        # Post realized gain/loss to P&L
        if realized_gain_loss > 0:
            journal.add_entry(
                account_id=self.get_realized_gain_account(item.entity_id),
                amount=realized_gain_loss,
                dc="C"  # Credit gain
            )
        elif realized_gain_loss < 0:
            journal.add_entry(
                account_id=self.get_realized_loss_account(item.entity_id),
                amount=abs(realized_gain_loss),
                dc="D"  # Debit loss
            )
        
        posted = self.ledger.post(journal)
        
        return SettlementResult(
            journal_id=posted.id,
            realized_gain_loss=realized_gain_loss,
            settlement_rate=settlement_rate,
            carrying_amount=carrying_fc_amount
        )
```

### 5.3 Realized vs Unrealized: Key Differences

| Aspect | Unrealized Gain/Loss | Realized Gain/Loss |
|--------|---------------------|-------------------|
| **Timing** | At period-end (revaluation date) | At settlement date |
| **Trigger** | Exchange rate change on open items | Actual cash conversion |
| **P&L Impact** | Period-end revaluation entry | Settlement entry |
| **Reversal** | Reversed at start of next period | Not reversed (permanent) |
| **Account** | Unrealized FX Gain/Loss | Realized FX Gain/Loss |
| **Nature** | Paper/mark-to-market gain/loss | Actual cash impact |

[^240^][^244^][^252^]

### 5.4 Example Walkthrough

**Full lifecycle of a foreign currency receivable**:

| Date | Event | EUR/USD Rate | EUR Amount | USD (Functional) | Gain/Loss |
|------|-------|-------------|------------|-----------------|-----------|
| Jan 15 | Invoice issued | 1.08 | EUR 10,000 | $10,800 | - |
| Jan 31 | Period-end revaluation | 1.10 | EUR 10,000 | $11,000 | Unrealized Gain: $200 |
| Feb 28 | Period-end revaluation | 1.09 | EUR 10,000 | $10,900 | Unrealized Loss: $100 (net $100 gain) |
| Mar 15 | Payment received | 1.12 | EUR 10,000 | $11,200 | Realized Gain: $300 (11,200 - 10,900) |

**Journal entries**:
```
Jan 15 - Initial recognition:
  Dr. Accounts Receivable (EUR)   $10,800
    Cr. Revenue                      $10,800

Jan 31 - Revaluation (closing rate 1.10):
  Dr. Accounts Receivable (EUR)     $200
    Cr. Unrealized FX Gain           $200

Feb 28 - Revaluation (closing rate 1.09):
  Dr. Unrealized FX Gain            $100
    Cr. Accounts Receivable (EUR)    $100

Mar 15 - Settlement (rate 1.12):
  Dr. Bank (USD)                  $11,200
    Cr. Accounts Receivable (EUR)  $10,900  [carrying amount]
    Cr. Realized FX Gain             $300
```

---

## 6. Multi-Currency Bank Accounts

### 6.1 Bank Account Currency Model

Each bank account operates in a specific currency. The GL tracks both the **foreign currency balance** and the **functional currency equivalent**:

```sql
CREATE TABLE bank_accounts (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id               UUID NOT NULL REFERENCES entities(id),
    
    -- Bank details
    bank_name               VARCHAR(255) NOT NULL,
    account_name            VARCHAR(255) NOT NULL,
    account_number          VARCHAR(100),
    iban                    VARCHAR(34),
    bic_swift               VARCHAR(11),
    
    -- Currency
    account_currency        CHAR(3) NOT NULL REFERENCES currencies(code),
    functional_currency     CHAR(3) NOT NULL REFERENCES currencies(code),
    
    -- GL Account mapping
    gl_account_id           UUID NOT NULL REFERENCES chart_of_accounts(id),
    
    -- For foreign currency accounts: revaluation settings
    revaluation_enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    last_revaluation_date   DATE,
    last_revaluation_run_id UUID REFERENCES revaluation_runs(id),
    
    -- Balances (denormalized for performance, derived from journal lines)
    fc_balance              DECIMAL(20,4) NOT NULL DEFAULT 0,  -- Functional currency
    txn_currency_balance    DECIMAL(20,4) NOT NULL DEFAULT 0,  -- Account currency
    
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 6.2 Bank Account Revaluation

Following Dynamics 365 and NetSuite patterns [^243^][^253^], foreign currency bank accounts are revalued at period-end:

```sql
CREATE OR REPLACE FUNCTION revaluate_bank_accounts(
    p_entity_id UUID,
    p_revaluation_date DATE,
    p_rate_type VARCHAR(10) DEFAULT 'CLOS'
) RETURNS TABLE (
    bank_account_id UUID,
    account_currency CHAR(3),
    fc_balance_before DECIMAL(20,4),
    fc_balance_after DECIMAL(20,4),
    unrealized_gain DECIMAL(20,4),
    unrealized_loss DECIMAL(20,4)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ba.id AS bank_account_id,
        ba.account_currency,
        ba.fc_balance AS fc_balance_before,
        -- Calculate revalued functional balance
        ba.txn_currency_balance * er.rate_value AS fc_balance_after,
        GREATEST(
            ba.txn_currency_balance * er.rate_value - ba.fc_balance, 
            0
        ) AS unrealized_gain,
        GREATEST(
            ba.fc_balance - ba.txn_currency_balance * er.rate_value, 
            0
        ) AS unrealized_loss
    FROM bank_accounts ba
    JOIN exchange_rates er ON er.from_currency = ba.account_currency
                           AND er.to_currency = ba.functional_currency
                           AND er.rate_type = p_rate_type
                           AND er.valid_from <= p_revaluation_date
                           AND er.valid_to >= p_revaluation_date
    WHERE ba.entity_id = p_entity_id
      AND ba.revaluation_enabled = TRUE
      AND ba.account_currency <> ba.functional_currency;
END;
$$ LANGUAGE plpgsql;
```

### 6.3 Bank Transfer Between Different Currency Accounts

When transferring between bank accounts in different currencies, two transactions are recorded:

```
Example: Transfer USD 10,000 from USD account to EUR account
  USD/EUR rate = 0.92

Journal Entry 1 - Outflow from USD account:
  Dr. Intercompany Clearing / Transfer Account   $10,000
    Cr. Bank Account - USD                         $10,000

Journal Entry 2 - Inflow to EUR account:
  Dr. Bank Account - EUR                         EUR 9,200 (10,000 * 0.92)
    Cr. Intercompany Clearing / Transfer Account   EUR 9,200

Functional currency (USD):
  Dr. Bank - EUR    $10,000  (9,200 EUR @ ~1.0870 USD/EUR)
    Cr. Bank - USD    $10,000
  
[No FX gain/loss on simultaneous transfer; difference arises 
 if rates are different or timing differs]
```

---

## 7. FX in Financial Reports

### 7.1 P&L Impact

Realized and unrealized FX gains/losses affect the income statement differently [^240^][^252^]:

```
Income Statement Presentation:

Revenue                        XXX
Cost of Sales                 (XXX)
-------------------------------
Gross Profit                    XXX

Operating Expenses            (XXX)
-------------------------------
Operating Profit                XXX

Finance Costs                 (XXX)
Finance Income                  XXX
**Realized FX Gains**           **XXX**
**Realized FX Losses**         **(XXX)**
**Unrealized FX Gains**         **XXX**
**Unrealized FX Losses**       **(XXX)**
-------------------------------
Profit Before Tax               XXX
```

**IAS 21 Disclosure Requirements** [^88^][^432^]:
- Exchange differences recognised in profit or loss (excluding FVTPL instruments)
- Net exchange differences classified in a separate component of equity (OCI)
- Reconciliation of exchange differences at beginning and end of period

### 7.2 Balance Sheet Translation

When translating an entity's financial statements into a different presentation currency (IAS 21.39) [^88^][^92^][^273^]:

| Statement Item | Translation Rate | Recognition |
|----------------|-----------------|-------------|
| Assets | Closing rate at balance sheet date | N/A |
| Liabilities | Closing rate at balance sheet date | N/A |
| Equity (share capital) | Historical rate | N/A |
| Income & Expenses | Transaction-date rate (or average) | N/A |
| **Resulting exchange differences** | N/A | **OCI (Translation Reserve)** |

```
Balance Sheet (Presentation Currency):

Assets                          XXX  [at closing rate]
Liabilities                    (XXX) [at closing rate]
-------------------------------
Net Assets                      XXX

Equity:
  Share Capital                 XXX  [at historical rate]
  Retained Earnings             XXX  [accumulated translated earnings]
  Translation Reserve (OCI)     XXX  [cumulative exchange differences]
-------------------------------
Total Equity                    XXX
```

> "All resulting exchange differences shall be recognised in other comprehensive income... The cumulative amount of the exchange differences is presented in a separate component of equity until disposal of the foreign operation." [^88^][^432^]

### 7.3 Cumulative Translation Adjustment (CTA)

The CTA is the running total of translation differences recognized in OCI:

```sql
CREATE TABLE cumulative_translation_adjustments (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id               UUID NOT NULL REFERENCES entities(id),
    parent_entity_id        UUID REFERENCES entities(id),  -- For consolidated reporting
    
    period_start            DATE NOT NULL,
    period_end              DATE NOT NULL,
    
    opening_cta_balance     DECIMAL(20,4) NOT NULL DEFAULT 0,
    
    -- Components of period change
    income_expense_translation_diff DECIMAL(20,4) NOT NULL DEFAULT 0,
    opening_net_assets_retranslation  DECIMAL(20,4) NOT NULL DEFAULT 0,
    goodwill_translation_diff       DECIMAL(20,4) NOT NULL DEFAULT 0,
    
    closing_cta_balance     DECIMAL(20,4) NOT NULL DEFAULT 0,
    
    -- On disposal, reclassified to P&L
    reclassified_to_pnl     DECIMAL(20,4) NOT NULL DEFAULT 0,
    reclassification_date   DATE,
    
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(entity_id, period_end)
);
```

### 7.4 Net Investment in Foreign Operation

Per IAS 21.32-33, exchange differences on monetary items that form part of a net investment in a foreign operation are recognized in **OCI** (not P&L) in consolidated financial statements [^88^][^429^][^430^]:

```
Example: Parent (GBP) lends EUR 1M to Subsidiary (EUR functional)
The loan is long-term, settlement neither planned nor likely

Parent's separate financial statements:
  - FX differences on the loan: P&L (IAS 21.28)

Consolidated financial statements:
  - FX differences on the loan: OCI (IAS 21.32)
  - Reclassified to P&L on disposal of subsidiary (IAS 21.48)
```

---

## 8. Historical Rates & Audit Trail

### 8.1 Rate Lookup with Date Precision

The system must support precise historical rate lookups for audit and transaction reconstruction:

```python
class HistoricalRateService:
    def get_rate_at_date(
        self,
        from_currency: str,
        to_currency: str,
        date: datetime.date,
        rate_type: str = "SPOT",
        fallback_strategy: str = "nearest"  # nearest, previous, strict
    ) -> Optional[ExchangeRate]:
        """
        Get the exchange rate effective at a specific date.
        
        Fallback strategies:
        - nearest: Find the closest rate within a window
        - previous: Use the most recent rate before or on the date
        - strict: Return None if no exact match
        """
        # Try exact match first
        rate = self.db.query(
            """SELECT * FROM exchange_rates 
               WHERE from_currency = %s AND to_currency = %s 
               AND rate_type = %s AND valid_from <= %s AND valid_to >= %s
               ORDER BY valid_from DESC LIMIT 1""",
            (from_currency, to_currency, rate_type, date, date)
        ).fetchone()
        
        if rate:
            return rate
        
        if fallback_strategy == "previous":
            return self.db.query(
                """SELECT * FROM exchange_rates
                   WHERE from_currency = %s AND to_currency = %s
                   AND rate_type = %s AND valid_from < %s
                   ORDER BY valid_from DESC LIMIT 1""",
                (from_currency, to_currency, rate_type, date)
            ).fetchone()
        
        elif fallback_strategy == "nearest":
            return self.db.query(
                """SELECT * FROM exchange_rates
                   WHERE from_currency = %s AND to_currency = %s
                   AND rate_type = %s
                   ORDER BY ABS(valid_from - %s::date) ASC LIMIT 1""",
                (from_currency, to_currency, rate_type, date)
            ).fetchone()
        
        return None
```

### 8.2 Rate Source Audit Trail

Every rate used in a transaction is immutably recorded:

```sql
-- Rate usage audit log (populated automatically via trigger)
CREATE TABLE rate_usage_audit (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exchange_rate_id    UUID NOT NULL REFERENCES exchange_rates(id),
    
    -- Where this rate was used
    usage_type          VARCHAR(50) NOT NULL,  -- TRANSACTION, REVALUATION, SETTLEMENT, TRANSLATION
    journal_line_id     UUID REFERENCES journal_lines(id),
    revaluation_line_id UUID REFERENCES revaluation_lines(id),
    
    -- Snapshot of rate at time of use (immutable)
    rate_value_snapshot DECIMAL(18,10) NOT NULL,
    from_currency_snapshot CHAR(3) NOT NULL,
    to_currency_snapshot   CHAR(3) NOT NULL,
    
    -- Full provenance
    provider_snapshot   VARCHAR(50) NOT NULL,
    source_reference_snapshot VARCHAR(255),
    
    used_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    used_by             UUID REFERENCES users(id)
);
```

### 8.3 Rate Change History Report

```sql
-- Report: All rate changes for a currency pair over a period
CREATE OR REPLACE VIEW rate_change_report AS
SELECT 
    from_currency || '/' || to_currency AS currency_pair,
    rate_type,
    valid_from,
    rate_value,
    LAG(rate_value) OVER (PARTITION BY from_currency, to_currency, rate_type 
                          ORDER BY valid_from) AS prior_rate,
    ROUND(
        ((rate_value - LAG(rate_value) OVER w) / LAG(rate_value) OVER w) * 100, 
        4
    ) AS pct_change,
    source_provider,
    source_reference
FROM exchange_rates
WINDOW w AS (PARTITION BY from_currency, to_currency, rate_type ORDER BY valid_from)
ORDER BY valid_from DESC;
```

---

## 9. Cryptocurrency Handling

### 9.1 IFRS Treatment of Cryptocurrencies

Per the IFRS Interpretations Committee June 2019 agenda decision, cryptocurrencies are accounted for under **IAS 38 Intangible Assets** [^441^][^447^]:

> "In the absence of IFRS guidance specifically for cryptocurrencies, the Committee considered IAS 38... cryptocurrencies meet the definition of an intangible asset... as they are capable of being separated from the holder and sold or transferred individually." [^441^]

**Key characteristics**:
- Cryptocurrencies are **not cash/cash equivalents** (not legal tender)
- Cryptocurrencies are **not financial assets** (no contractual right to receive cash)
- Cryptocurrencies are **intangible assets** under IAS 38

### 9.2 Initial Measurement

| Holding Purpose | IFRS Treatment | Initial Measurement |
|----------------|---------------|-------------------|
| Held for sale in ordinary course of business | IAS 2 Inventories | Lower of cost and NRV |
| Commodity broker-trader | IAS 2 (broker-trader) | FV less costs to sell |
| All other holdings | IAS 38 Intangible Assets | Cost |

### 9.3 Subsequent Measurement

Under IAS 38, cryptocurrencies are measured using one of two models [^441^][^447^]:

**Cost Model** (default):
- Carried at cost less accumulated amortization and impairment
- Impairment tested when indicators exist (IAS 36)
- No write-up allowed (no active market exception for non-revalued intangibles)

**Revaluation Model** (if active market exists):
- Carried at fair value at revaluation date
- Revaluations must be regular
- **Increases** in carrying amount: recognized in **OCI** (revaluation surplus)
- **Decreases** in carrying amount: recognized in **P&L** (impairment), except to extent of prior revaluation surplus

### 9.4 Fair Value Hierarchy for Crypto (IFRS 13)

| Level | Input Type | Crypto Example |
|-------|-----------|----------------|
| **Level 1** | Quoted prices in active markets | Bitcoin, Ethereum on major exchanges (Coinbase, Binance) with sufficient volume |
| **Level 2** | Observable inputs (indirect) | Less liquid tokens with observable prices on smaller exchanges |
| **Level 3** | Unobservable inputs | Pre-launch tokens, SAFTs, illiquid altcoins requiring model-based valuation |

[^441^][^442^][^447^][^448^]

### 9.5 Crypto Asset Data Model

```sql
-- Cryptocurrency assets (extends the intangible asset model)
CREATE TABLE crypto_holdings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id           UUID NOT NULL REFERENCES entities(id),
    
    -- Asset identification
    crypto_currency_code VARCHAR(20) NOT NULL,  -- e.g., "BTC", "ETH", "USDC"
    crypto_currency_name VARCHAR(100),
    blockchain_network    VARCHAR(50),  -- e.g., "Bitcoin", "Ethereum"
    token_contract_address VARCHAR(100),  -- For ERC-20 tokens
    
    -- Wallet
    wallet_address      VARCHAR(255),
    custodian           VARCHAR(100),   -- e.g., "Coinbase", "Metamask", "Ledger"
    
    -- Holdings (in smallest unit, e.g., satoshis or wei)
    quantity_held       DECIMAL(30,18) NOT NULL DEFAULT 0,
    quantity_precision  SMALLINT NOT NULL DEFAULT 8,  -- 8 for BTC, 18 for ETH
    
    -- Accounting (IAS 38)
    accounting_model    VARCHAR(20) NOT NULL DEFAULT 'COST',  -- COST or REVALUATION
    
    -- Cost basis (for COST model)
    total_cost_basis    DECIMAL(20,4) NOT NULL DEFAULT 0,     -- In functional currency
    average_cost_per_unit DECIMAL(30,18),                       -- In functional currency
    
    -- Fair value (for REVALUATION model or impairment testing)
    last_fair_value     DECIMAL(20,4),                          -- In functional currency
    last_fair_value_date DATE,
    fair_value_level    VARCHAR(10),    -- LEVEL_1, LEVEL_2, LEVEL_3 per IFRS 13
    
    -- Revaluation surplus (OCI)
    revaluation_surplus DECIMAL(20,4) NOT NULL DEFAULT 0,
    
    -- Impairment
    accumulated_impairment DECIMAL(20,4) NOT NULL DEFAULT 0,
    last_impairment_date   DATE,
    
    -- GL accounts
    asset_account_id    UUID NOT NULL REFERENCES chart_of_accounts(id),
    revaluation_surplus_account_id UUID REFERENCES chart_of_accounts(id),
    impairment_loss_account_id UUID REFERENCES chart_of_accounts(id),
    
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Crypto fair value feed (separate from fiat exchange rates)
CREATE TABLE crypto_fair_values (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    crypto_currency_code VARCHAR(20) NOT NULL,
    quote_currency      CHAR(3) NOT NULL,  -- Usually USD
    
    fair_value          DECIMAL(20,8) NOT NULL,
    market_cap_usd      DECIMAL(30,2),
    volume_24h_usd      DECIMAL(30,2),
    
    -- Source
    source_provider     VARCHAR(50) NOT NULL,  -- "CoinGecko", "CoinMarketCap", "Binance"
    source_exchange     VARCHAR(50),  -- Specific exchange if applicable
    
    -- Fair value hierarchy assessment
    fair_value_level    VARCHAR(10),  -- LEVEL_1, LEVEL_2, LEVEL_3
    
    snapshot_at         TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(crypto_currency_code, quote_currency, snapshot_at)
);
```

### 9.6 Crypto Revaluation Process

```python
class CryptoRevaluationService:
    def revalue_crypto_holdings(self, entity_id: UUID, revaluation_date: date):
        """Revalue crypto holdings per IAS 38 revaluation model."""
        holdings = self.get_crypto_holdings(entity_id)
        
        for holding in holdings:
            if holding.accounting_model == "COST":
                # Only test for impairment
                self._test_impairment(holding, revaluation_date)
            elif holding.accounting_model == "REVALUATION":
                # Full fair value revaluation
                self._revalue_to_fair_value(holding, revaluation_date)
    
    def _revalue_to_fair_value(self, holding: CryptoHolding, date: date):
        fair_value = self.crypto_price_service.get_fair_value(
            holding.crypto_currency_code,
            holding.entity.functional_currency,
            date
        )
        
        current_carrying = holding.total_cost_basis + holding.revaluation_surplus - holding.accumulated_impairment
        new_carrying = fair_value.fair_value * holding.quantity_held
        
        difference = new_carrying - current_carrying
        
        if difference > 0:
            # Increase -> OCI (revaluation surplus)
            journal = Journal(
                entries=[
                    JournalEntry(
                        account_id=holding.asset_account_id,
                        amount=difference,
                        dc="D"
                    ),
                    JournalEntry(
                        account_id=holding.revaluation_surplus_account_id,
                        amount=difference,
                        dc="C"
                    )
                ]
            )
        elif difference < 0:
            # Decrease -> first offset revaluation surplus, then P&L
            if holding.revaluation_surplus > 0:
                offset_amount = min(holding.revaluation_surplus, abs(difference))
                remaining = abs(difference) - offset_amount
                
                entries = [
                    # Reduce revaluation surplus
                    JournalEntry(
                        account_id=holding.revaluation_surplus_account_id,
                        amount=offset_amount,
                        dc="D"
                    ),
                    JournalEntry(
                        account_id=holding.asset_account_id,
                        amount=offset_amount,
                        dc="C"
                    )
                ]
                
                if remaining > 0:
                    # Remainder to P&L (impairment)
                    entries.extend([
                        JournalEntry(
                            account_id=holding.impairment_loss_account_id,
                            amount=remaining,
                            dc="D"
                        ),
                        JournalEntry(
                            account_id=holding.asset_account_id,
                            amount=remaining,
                            dc="C"
                        )
                    ])
            else:
                # All to P&L
                journal = Journal(
                    entries=[
                        JournalEntry(
                            account_id=holding.impairment_loss_account_id,
                            amount=abs(difference),
                            dc="D"
                        ),
                        JournalEntry(
                            account_id=holding.asset_account_id,
                            amount=abs(difference),
                            dc="C"
                        )
                    ]
                )
        
        self.ledger.post(journal)
```

---

## 10. Configuration

### 10.1 Per-Entity Functional Currency Settings

```yaml
entity_currency_config:
  # Entity: US Parent
  entity_us_parent:
    functional_currency: USD
    presentation_currency: USD
    reporting_currencies: []  # Same as functional
    exchange_rate_defaults:
      transaction_rate_type: SPOT
      revaluation_rate_type: CLOS
      translation_rate_type: AVG
    auto_revaluation:
      enabled: true
      frequency: MONTH_END
      run_at: "23:00"
      currencies: ["EUR", "GBP", "JPY"]  # Only revalue these
    unrealized_gl_accounts:
      gain: "7700-FX-Unrealized-Gain"
      loss: "7800-FX-Unrealized-Loss"
    realized_gl_accounts:
      gain: "7710-FX-Realized-Gain"
      loss: "7810-FX-Realized-Loss"
    cta_account: "3900-Cumulative-Translation-Adjustment"
  
  # Entity: German Subsidiary
  entity_de_subsidiary:
    functional_currency: EUR
    presentation_currency: USD  # Different - needs translation
    reporting_currencies: ["USD", "EUR"]
    exchange_rate_defaults:
      transaction_rate_type: SPOT
      revaluation_rate_type: CLOS
      translation_rate_type: AVG
    auto_revaluation:
      enabled: true
      frequency: MONTH_END
    # Uses group chart of accounts mapping
  
  # Entity: UK Branch
  entity_uk_branch:
    functional_currency: GBP
    presentation_currency: USD
    reporting_currencies: ["USD"]
```

### 10.2 System-Wide Exchange Rate Configuration

```yaml
exchange_rate_config:
  # Provider priority and settings
  providers:
    ecb:
      enabled: true
      priority: 1
      api_endpoint: "https://sdw-wsrest.ecb.europa.eu/service/data/EXR"
      fetch_schedule: "0 17 * * MON-FRI"  # 17:00 CET, weekdays only
      currencies: ["USD", "GBP", "JPY", "CHF", "CAD", "AUD", "SEK", "NOK"]
      base_currency: EUR
      
    xe:
      enabled: true
      priority: 2
      api_key: "${XE_API_KEY}"
      fetch_schedule: "0 * * * *"  # Every hour
      all_currencies: true
      
    open_exchange_rates:
      enabled: true
      priority: 3
      api_key: "${OXR_API_KEY}"
      fetch_schedule: "0 * * * *"  # Every hour
      plan: enterprise
      
    coingecko:
      enabled: true
      priority: 1  # For crypto
      api_endpoint: "https://api.coingecko.com/api/v3"
      fetch_schedule: "*/15 * * * *"  # Every 15 minutes
      
  # Caching
  cache:
    current_rates_ttl: 3600  # 1 hour
    historical_rates_ttl: 86400  # 24 hours
    stale_threshold: 7200  # 2 hours before alerting
    
  # Rate derivation
  cross_rate_method: "triangular_via_eur"
  allowed_cross_rate_pairs: ["*"]  # All pairs
  
  # Precision
  rate_precision: 10  # Decimal places for rates
  amount_precision: 4  # Decimal places for converted amounts
  rounding_mode: "HALF_EVEN"  # Banker's rounding
```

### 10.3 Multi-Currency Feature Flags

```sql
CREATE TABLE system_currency_features (
    feature_name        VARCHAR(50) PRIMARY KEY,
    enabled             BOOLEAN NOT NULL DEFAULT FALSE,
    config              JSONB,
    
    -- Rollout
    rollout_percentage  SMALLINT NOT NULL DEFAULT 100 CHECK (rollout_percentage BETWEEN 0 AND 100),
    allowed_entities    UUID[],  -- NULL = all entities
    
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by          UUID REFERENCES users(id)
);

-- Initial feature flags
INSERT INTO system_currency_features (feature_name, enabled, config) VALUES
    ('multi_currency_transactions', TRUE, '{}'),
    ('auto_period_end_revaluation', TRUE, '{"frequency": "MONTHLY"}'),
    ('realized_gain_loss_tracking', TRUE, '{}'),
    ('presentation_currency_translation', TRUE, '{}'),
    ('crypto_asset_accounting', FALSE, '{"model": "COST"}'),
    ('dual_currency_reporting', FALSE, '{}'),
    ('net_investment_hedge_tracking', FALSE, '{}'),
    ('average_rate_translation', TRUE, '{"method": " arithmetic_mean"}'),
    ('historical_rate_lookup', TRUE, '{"retention_years": 10}'),
    ('exchange_rate_audit_trail', TRUE, '{"immutable": true}');
```

---

## 11. Consolidation & Translation Workflow

### 11.1 Foreign Operation Translation Steps

When consolidating a foreign subsidiary, the following steps are applied per IAS 21.39-49 [^88^][^273^][^274^]:

```
Step 1: Identify functional currencies
  - Parent: USD
  - Subsidiary: EUR
  -> Translation required (different functional currencies)

Step 2: Subsidiary's individual financial statements
  - Already in EUR (functional currency)
  - Apply IAS 21 to foreign currency transactions in subsidiary's books
  - Revalue monetary items at closing rate

Step 3: Translate subsidiary's financial statements to parent's presentation currency (USD)
  
  Statement of Financial Position:
    Assets:     EUR balances * closing rate (EUR/USD at reporting date)
    Liabilities: EUR balances * closing rate
    Equity:     
      - Share capital: * historical rate (at date of investment)
      - Retained earnings: accumulated translated amounts
      - Translation reserve (CTA): balancing figure
  
  Income Statement:
    Revenue:    EUR amount * transaction-date rate (or monthly average)
    Expenses:   EUR amount * transaction-date rate (or monthly average)
    
  Result: Exchange difference -> OCI (Translation Reserve)

Step 4: Consolidation
  - Eliminate intercompany balances and transactions
  - Recognize non-controlling interest share of CTA
  - Goodwill and FV adjustments: treated as foreign operation assets,
    translated at closing rate [^88^][^432^]
```

### 11.2 Translation API

```python
class ConsolidationTranslationService:
    def translate_foreign_operation(
        self,
        subsidiary: Entity,
        parent: Entity,
        reporting_date: date,
        financial_statements: FinancialStatements
    ) -> TranslatedStatements:
        """Translate subsidiary's financial statements to parent's presentation currency."""
        
        # Step 1: Get closing rate (balance sheet date)
        closing_rate = self.rate_service.get_rate(
            subsidiary.functional_currency,
            parent.presentation_currency,
            "CLOS",
            reporting_date
        )
        
        # Step 2: Translate balance sheet at closing rate
        translated_bs = BalanceSheet()
        for item in financial_statements.balance_sheet.items:
            if item.is_monetary():
                translated = item.amount * closing_rate.rate_value
            else:
                # Non-monetary: historical rate
                hist_rate = self.rate_service.get_rate(
                    subsidiary.functional_currency,
                    parent.presentation_currency,
                    "HIST",
                    item.transaction_date
                )
                translated = item.amount * hist_rate.rate_value
            translated_bs.add(item.account, translated)
        
        # Step 3: Translate income statement at average rate
        avg_rate = self.rate_service.get_average_rate(
            subsidiary.functional_currency,
            parent.presentation_currency,
            reporting_date.year,
            reporting_date.month
        )
        
        translated_is = IncomeStatement()
        for item in financial_statements.income_statement.items:
            # For practical reasons, use average rate
            # Can override with transaction-date rate if needed
            translated = item.amount * avg_rate
            translated_is.add(item.account, translated)
        
        # Step 4: Calculate translation difference -> CTA
        net_assets_translated = translated_bs.net_assets
        equity_translated = translated_bs.equity_excluding_cta
        cta = net_assets_translated - equity_translated
        
        return TranslatedStatements(
            balance_sheet=translated_bs,
            income_statement=translated_is,
            cumulative_translation_adjustment=cta,
            rates_used={
                "closing_rate": closing_rate,
                "average_rate": avg_rate
            }
        )
```

---

## 12. Data Flow Diagrams

### 12.1 Transaction Recording Flow

```
+----------+     +----------------+     +------------------+     +----------------+
| Invoice  |---->| Rate Lookup    |---->| FX Conversion    |---->| GL Posting     |
| (EUR)    |     | (Spot rate at  |     | (Transaction +   |     | (Both txn FCY  |
|          |     |  txn date)     |     |  Functional amt) |     |  + Functional) |
+----------+     +----------------+     +------------------+     +----------------+
                    |                      |
                    v                      v
               +----------+         +-------------+
               | Rate     |         | Journal     |
               | Cache/   |         | Line stores |
               | DB       |         | both amounts|
               +----------+         +-------------+
```

### 12.2 Period-End Revaluation Flow

```
+----------------+     +-------------------+     +------------------+
| Period End     |---->| Identify Open     |---->| Fetch Closing    |
| Close Initiated|     | Monetary Items    |     | Rates            |
+----------------+     +-------------------+     +------------------+
                                                        |
                    +-----------------------------------+
                    v
             +----------------+     +------------------+
             | Calculate      |---->| Generate         |
             | Unrealized     |     | Revaluation      |
             | Gains/Losses   |     | Journal Entries  |
             +----------------+     +------------------+
                                              |
                    +---------------------------+
                    v
             +----------------+     +------------------+
             | Post to GL     |---->| Update Balances  |
             | (Unrealized    |     | & Audit Trail    |
             |  G/L accounts) |     |                  |
             +----------------+     +------------------+
```

### 12.3 Settlement & Realized Gain/Loss Flow

```
+----------------+     +-------------------+     +------------------+
| Payment        |---->| Get Carrying      |---->| Convert Payment  |
| Received       |     | Amount (post-     |     | at Settlement    |
|                |     |  revaluation)     |     | Rate             |
+----------------+     +-------------------+     +------------------+
                    |                              |
                    +--------------+---------------+
                                   v
                            +----------------+
                            | Calculate      |
                            | Realized       |
                            | Gain/Loss      |
                            +----------------+
                                   |
                    +--------------+---------------+
                    v                              v
             +----------------+            +------------------+
             | Reverse Prior  |            | Post Realized    |
             | Unrealized G/L |            | Gain/Loss to P&L |
             +----------------+            +------------------+
```

---

## 13. Implementation Checklist

### Phase 1: Core Currency Infrastructure
- [ ] Currency registry with ISO 4217 + crypto extensions
- [ ] Entity functional currency assignment
- [ ] Exchange rate types (SPOT, CLOS, AVG, CORP, etc.)
- [ ] Basic rate storage (inspired by SAP TCURR) [^415^]
- [ ] Manual rate entry UI/API
- [ ] Rate audit trail

### Phase 2: Transaction Processing
- [ ] Multi-currency journal line model (transaction + functional amounts)
- [ ] Spot rate lookup at transaction date
- [ ] Automatic FX conversion on posting
- [ ] Immutable rate snapshot per journal line
- [ ] Historical rate lookup with date precision

### Phase 3: Period-End Revaluation
- [ ] Monetary vs non-monetary item classification [^412^][^419^]
- [ ] Closing rate revaluation of monetary items [^88^]
- [ ] Unrealized gain/loss calculation
- [ ] Revaluation journal generation
- [ ] Prior period revaluation reversal [^278^]
- [ ] Revaluation run approval workflow

### Phase 4: Settlement & Realized G/L
- [ ] Settlement processing with realized G/L calculation
- [ ] Realized gain/loss posting to P&L
- [ ] Automatic reversal of prior unrealized G/L
- [ ] Gain/loss reporting by currency pair

### Phase 5: Reporting & Translation
- [ ] P&L with FX gain/loss breakdown
- [ ] Balance sheet translation at closing rate
- [ ] Cumulative Translation Adjustment tracking
- [ ] Foreign operation translation for consolidation [^88^][^273^]
- [ ] Net investment hedge tracking [^429^]

### Phase 6: Advanced Features
- [ ] Multi-currency bank account management [^243^]
- [ ] Bank revaluation automation
- [ ] Cryptocurrency asset tracking [^441^]
- [ ] Fair value hierarchy assessment (IFRS 13) [^442^]
- [ ] Crypto revaluation (cost and revaluation models)
- [ ] ECB/XE/OXR automated rate feeds [^227^][^272^]
- [ ] Cross-rate derivation via triangular arbitrage

---

## 14. References

### Standards
- [^88^] IAS 21 *The Effects of Changes in Foreign Exchange Rates* (IFRS Foundation, 2021 Issued Standard)
- [^432^] IAS 21 Summary (iasplus.com, 2023)
- [^441^] IFRS 13 *Fair Value Measurement* (IFRS Foundation)
- [^442^] IFRS 13 Fair Value Measurement (ICAEW, 2024)
- [^220^] IFRIC Interpretation - Foreign Currency Transactions and Advance Consideration (DRSC)
- [^275^] IAS 21 - Staff Paper on Monetary/Non-monetary Items (IFRS IC, 2016)

### Technical References
- [^415^] SAP TCURR Exchange Rates Table (leanx.eu)
- [^418^] SAP Currency Conversion Logic (Celonis documentation)
- [^420^] SAP TCURR Currency Logic (Snowflake/Medium, 2021)
- [^413^] Automation of Exchange Rate Feed in SAP (SAP Community, 2025)
- [^414^] Multiple Currencies for Company Code in SAP S/4HANA (SAP Community, 2024)
- [^278^] Oracle General Ledger Multi-Currency Accounting (Oracle Documentation)
- [^440^] Oracle GL Multi-Currency Overview (Oracle Documentation, 2026)

### Accounting Practice
- [^239^] IAS 21 - Moore Global (2026)
- [^246^] Functional Currency: Definition, Determination & Accounting (dualentry.com, 2025)
- [^250^] KPMG: The Effects of Changes in Foreign Exchange Rates
- [^412^] IAS 21 Effects of Changes in Foreign Exchange Rates (IFRS Community, 2025)
- [^416^] IAS 21 - CPA Ireland Study Guide
- [^417^] IAS 21 Staff Paper on Monetary/Non-monetary Items (IFRS IC, 2016)
- [^419^] Monetary or Non-Monetary? (CPDbox, 2023)
- [^419^] IFRS 13 Fair Value Hierarchy (ACCA Global, 2025)
- [^445^] IAS 21 Foreign Exchange Rates: A Practical Guide (Learnsignal, 2026)
- [^273^] Consolidated Financial Statements Foreign Subsidiary (datasights.co, 2026)
- [^274^] IAS 21 Foreign Exchange Rates Practical Guide (Learnsignal, 2026)
- [^92^] PwC Viewpoint - Foreign Currency Considerations (2024)
- [^429^] IAS 21 Net Investment in Foreign Operation (MPRA/IAS Closer Look)
- [^430^] IAS 21 Amendment - Net Investment in a Foreign Operation (EFRAG)

### System Implementations
- [^147^] Xero Multi-Currency (Jacrox, 2023)
- [^148^] Xero Multi-Currency Accounting Software (xero.com)
- [^449^] Xero Multi-Currency Made Easy (Tipalti, 2024)
- [^451^] Xero Multi-Currency (UHY, 2023)
- [^454^] Multicurrency in Xero (Xero Central)
- [^272^] XE API Pricing & Alternative (CurrencyFreaks, 2026)
- [^241^] Open Exchange Rates API Pricing & Alternative (CurrencyFreaks, 2026)
- [^249^] Open Exchange Rates Comprehensive Guide (exchangeratesapi.io)
- [^227^] ECB Euro Exchange Rates - GitHub (qqilihq, 2018)
- [^224^] ECB SDMX API Documentation (fgeerolf.com, 2024)
- [^225^] ECB Historical Exchange Rate API (Stack Overflow, 2024)
- [^223^] ECB Euro Exchange Rates OpenAPI (Apify, 2026)
- [^243^] Bank Foreign Currency Revaluation - Dynamics 365 (Microsoft, 2026)
- [^253^] NetSuite Currency Revaluation (Oracle/NetSuite)
- [^456^] Multicurrency Accounting Explained (NetSuite, 2025)
- [^242^] Understanding Multi-Currency Accounting (LiveFlow, 2026)
- [^439^] Dual Currency - Dynamics 365 (Microsoft, 2026)

### FX Gains/Losses & Revaluation
- [^240^] Foreign Exchange Gain/Loss - Realized vs Unrealized (CFI, 2026)
- [^244^] Foreign Currency Gain: A Comprehensive Guide (Hubifi, 2025)
- [^252^] How to manage FX gains and losses in financial statements (Drivetrain, 2024)
- [^247^] Gains and Losses Resulting from Exchange Rate Changes (Deltek)
- [^427^] Unrealised Currency Gains Explained Simply (Connectorly, 2026)
- [^248^] Foreign Currency Revaluation in ERP (Onfinity)

### Cryptocurrency
- [^441^] ACCA Global - IFRS 13 Fair Value Measurement (2025)
- [^442^] IFRS 13 Fair Value Measurement (ICAEW, 2024)
- [^447^] Accounting for Digital Assets: Key Considerations (ISDA)
- [^448^] How to Value Digital Tokens: A 5-Step Fair Value Framework (CFA Institute, 2025)
- [^444^] KPMG Fair Value Measurement Handbook
- [^446^] Grant Thornton - Insights into IFRS 13 (2021)

### Service Architecture
- [^452^] Design an Exchange Rate Service (Medium/Tom Tech, 2024)
- [^455^] Multi-Currency Best Practice Implementation (Stack Overflow, 2011)
- [^213^] Formance Ledger Documentation (formance.com)

---

*Document version: 1.0*
*Last updated: 2025-01*
*Compliance target: IAS 21 (2021 issued version), IFRS 13, IAS 38*
