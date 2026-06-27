## Facet: Multi-Entity, Multi-Tax & Domicile Architecture

---

### Key Findings

- **UK VAT MTD is now universal and API-mandatory.** As of April 2022, all VAT-registered businesses must use Making Tax Digital (MTD) compatible software that connects to HMRC's APIs. The VAT registration threshold remains at £85,000. [^90^] [^93^] "Making Tax Digital for VAT is now mandatory for all VAT-registered businesses as of April 2022" [^132^]

- **EU OSS/IOSS processes €33+ billion annually.** In 2024, total VAT declared through OSS/IOSS schemes reached €33.1 billion (26% increase over 2023), with €24 billion via Union OSS, €2.8 billion via Non-Union OSS, and €6.3 billion via Import OSS (IOSS). [^41^]

- **EU VAT e-commerce threshold is €10,000 EU-wide.** The previous per-country distance selling thresholds were replaced by a single EU-wide €10,000 threshold for B2C intra-EU distance sales and TBE services. Above this, VAT must be charged at the customer's country rate. [^33^] [^34^]

- **IOSS €150 limit will be withdrawn by March 2028.** EU Customs reforms propose scrapping the €150 import consignment threshold, requiring VAT on all import B2C consignments to be charged at sale in checkout. Marketplaces will become liable as deemed suppliers for VAT and customs charges. [^36^]

- **US economic nexus creates extreme compliance complexity.** Post-Wayfair (2018), 45 states plus DC now have economic nexus laws. Thresholds vary from $10,000 (Washington, historically) to $500,000 (California, Texas, New York). Most states use $100,000 in sales or 200 transactions, but a growing trend removes transaction thresholds entirely. [^23^] [^24^] Indiana removed its 200-transaction threshold effective January 1, 2024; Illinois will remove its January 1, 2026. [^26^]

- **GST registration thresholds vary significantly by jurisdiction.** Australia: AU$75,000 (non-profits AU$150,000). [^116^] New Zealand: NZD $60,000. [^151^] [^153^] Canada: CAD $30,000 in a single calendar quarter. [^130^] Filing frequencies also differ: Australia uses monthly (>$20M), quarterly (<$20M), or annual; [^118^] NZ uses monthly (>$24M), two-monthly (<$24M), or six-monthly (<$500K); [^153^] Canada uses monthly (>$6M), quarterly ($1.5M-$6M), or annual (<$1.5M). [^131^] [^134^]

- **Configurable tax engine architecture separates rules from code.** A proper tax rules engine has three layers: (1) the Rule Store (structured repository with rule type, applicability conditions, tax output, effective dates, statutory basis, priority, and approval status); (2) the Execution Engine (rules interpreter that queries the store at runtime); and (3) the Override Workflow (mandatory approval with segregation of duties). [^84^] "Rate changes, RCM triggers, exemption conditions, cross-border rules, override workflows, and place-of-supply mappings are all managed through an interface built for tax professionals -- not software engineers." [^84^]

- **UPU S42 standard defines international address formats.** The Universal Postal Union's S42 standard comprises a generic list of address elements used in all 192 UPU member countries plus country-specific templates that define how to transform elements into accurately formatted addresses. [^86^] [^87^] Address formats differ dramatically: China uses big-endian (province first) in Chinese but little-endian in English; Belgium places street number after the thoroughfare name; Iran has 4 distinct address types (urban, rural, PO Box, Post Restante). [^91^]

- **Intercompany eliminations are legally required under both GAAP and IFRS.** ASC 810 (US GAAP) and IFRS 10 both require full elimination of all intragroup balances and transactions. "The complete elimination of the intra-entity income or loss is consistent with the underlying assumption that consolidated financial statements represent the financial position and operating results of a single economic entity." [^105^] Four elimination types exist: intercompany debt, revenue/expenses, stock ownership, and unrealized profit in inventory. [^99^]

- **IAS 21 distinguishes functional currency from presentation currency.** An entity's functional currency reflects its primary economic environment; the presentation currency can be any currency chosen. Assets/liabilities translate at closing rate; income/expenses at transaction-date rates (or average); exchange differences go to OCI (translation reserve). [^117^] [^119^] Monetary items create FX exposure in profit or loss; non-monetary items at historical cost do not. [^117^]

- **Withholding tax rates vary dramatically across jurisdictions.** OECD data covering 146 jurisdictions shows: average standard WHT on dividends is 15.5% in high-income countries vs. 11.5% in low/middle-income; average WHT on interest is 12.6% vs. 14.7%; average WHT on royalties is 16.2% vs. 16.8%. Investment hubs levy significantly lower rates: 5.2% on dividends, 4.3% on interest, and 2.8% on royalties. [^125^] Over 5,100 bilateral tax treaties are in effect as of 2025, and treaty-based rates are substantially lower than statutory rates. [^125^]

- **Transfer pricing follows the arm's length principle.** OECD Transfer Pricing Guidelines (originally 1995, regularly revised) require that related-party transactions be priced as if between unrelated parties. Approved methods include comparable uncontrolled price, cost plus, resale price, transactional net margin, and profit split. Documentation requirements include a master file, local file, and Country-by-Country Reporting (CbCR) for large MNEs. [^103^]

- **Place of supply rules determine tax jurisdiction.** The OECD International VAT/GST Guidelines (2015) establish: for B2B supplies, tax jurisdiction is the customer's location (destination principle); for B2C "on-the-spot" supplies, it's where physically performed; for other B2C supplies, it's the customer's usual residence. [^150^] The EU VAT Directive provides extensive specific rules for services connected to immovable property, event admission, transport, short-term hire, and telecommunications/electronic services. [^152^]

---

### Tax System Comparison Matrix

| Jurisdiction | Tax Type | Registration Threshold | Standard Rate | Return Frequency | Key Rules |
|---|---|---|---|---|---|
| **United Kingdom** | VAT (MTD) | £85,000 | 20% | Quarterly (standard); Monthly (large) | API-only submission via MTD; digital records mandatory; [^90^] [^93^] |
| **EU (OSS)** | VAT | €10,000 (EU-wide for B2C distance sales) | 15%-27% (by member state) | Quarterly via OSS | One registration covers all 27 member states; IOSS for imports ≤€150; [^33^] [^34^] |
| **Australia** | GST | AU$75,000 (AU$150K non-profits) | 10% | Monthly (>$20M); Quarterly (<$20M); Annual (voluntary) | BAS reporting; ABN required; input tax credits available; [^116^] [^118^] |
| **New Zealand** | GST | NZD $60,000 | 15% | Monthly (>$24M); Two-monthly (<$24M); Six-monthly (<$500K) | Payments or invoice basis; cash basis for turnover <$2M; GST number = IRD number; [^151^] [^153^] |
| **Canada** | GST/HST | CAD $30,000/quarter | 5% GST + provincial HST | Monthly (>$6M); Quarterly ($1.5M-$6M); Annual (<$1.5M) | HST harmonized in some provinces; Quick Method available for small suppliers; [^130^] [^131^] [^134^] |
| **United States** | Sales Tax | Varies by state ($0-$500,000) | 0%-10.75% (combined state+local) | Monthly/Quarterly/Annual | Economic nexus post-Wayfair; 45 states + DC have laws; no federal sales tax; [^23^] [^24^] [^25^] |

---

### Trends & Signals

- **Digital tax reporting is becoming mandatory globally.** The UK's MTD for VAT (API-only submission) is a model being replicated. MTD for Income Tax Self Assessment launches April 2026 for sole traders/landlords with income >£50,000, and April 2027 for >£30,000. [^93^] Australia's Standard Business Reporting (SBR) enables direct digital transmission to the ATO. Similar digital-first approaches are emerging across OECD countries.

- **US states are simplifying economic nexus by removing transaction thresholds.** Indiana (Jan 2024), Wyoming (July 2024), Alaska (Jan 2025), Utah (July 2025), and Illinois (Jan 2026) have all removed or will remove 200-transaction thresholds, moving to revenue-only ($100,000) triggers. [^23^] [^26^] This reduces the burden on low-dollar, high-volume sellers.

- **EU VAT on imports is expanding beyond the €150 limit.** By March 2028, the EU plans to withdraw the IOSS €150 threshold entirely, requiring VAT collection at checkout for all B2C imports. Marketplaces will become deemed suppliers for all import consignments, not just those under €150. [^36^]

- **OSS/IOSS adoption is accelerating rapidly.** Total VAT declared through OSS/IOSS grew 26% from 2023 to 2024 (€26.3B to €33.1B). Cumulative VAT declared since 2021 launch approaches €88 billion. [^41^] This demonstrates the scalability of centralized digital tax reporting.

- **Tax engine configurability is replacing hardcoded rules.** Modern tax engines (Vertex O Series covers 19,000+ jurisdictions) [^88^] use rules-based architectures where tax professionals -- not developers -- update rates, rules, and effective dates through configuration interfaces. [^84^] Rate changes can be deployed same-day rather than in weeks.

- **Multi-entity accounting is moving toward real-time consolidation.** Modern systems implement continuous consolidation with systematized elimination rules, reducing month-end close from 15+ days to near-real-time. 61% of mid-market CFOs identify manual multi-currency processes as a top-three driver of close delays. [^155^]

---

### Controversies & Conflicting Claims

- **US sales tax complexity vs. federal simplification proposals.** The Tax Foundation argues that "states should reform their marketplace facilitator and remote seller rules and remove the transaction threshold altogether" to reduce disproportionate compliance burdens on small sellers. [^23^] However, states resist federal mandates due to revenue sovereignty concerns. The Streamlined Sales Tax Project (SSTP) has achieved only partial adoption (23 member states), demonstrating the tension between simplification and state autonomy.

- **EU VAT OSS: simplification or new bureaucracy?** Proponents note OSS reduces registrations by up to 95% and "lessen the burden on sellers while also reducing their administration costs." [^33^] Critics point to the 10-year record-keeping requirement, need for two non-contradictory pieces of customer location evidence, and the complexity of currency conversions as creating new compliance burdens, especially for micro-businesses.

- **Withholding tax rates: source vs. residence taxation.** The OECD Model Convention suggests maximum withholding rates of 5% for qualifying dividends, 15% for portfolio dividends, 10% for interest, and 0% for royalties -- effectively assigning exclusive taxing rights to the residence country for royalties. [^127^] The UN Model Convention favors source taxation (higher rates, lower thresholds for participation dividends at 10% vs. OECD's 25%). [^128^] Developing countries argue the OECD approach erodes their tax base on intellectual property and technical service payments.

- **Transaction count thresholds: protective or harmful?** Tax Foundation research shows that in Arkansas, "selling 200 of the same item at a price of $5 for a total of $1,000 would be sufficient to require the seller to comply with the Arkansas sales tax collection and remittance rules, even though the total revenue was dramatically less than the $100,000 sales threshold." [^23^] This creates situations where "compliance costs associated with collection and remittance requirements could be greater than the business transacted."

---

### Recommended Deep-Dive Areas

- **EU VAT 2028 Customs Reforms**: The proposed removal of the €150 IOSS threshold and introduction of "deemed importer" concepts will fundamentally change cross-border e-commerce VAT collection. Any system architecture must account for customs duty + VAT combined collection at checkout. [^36^]

- **US Economic Nexus Real-Time Monitoring**: With 45+ different state regimes, a headless accounting system needs automated nexus threshold tracking. The trend toward revenue-only thresholds simplifies detection but marketplace sales inclusion/exclusion rules still vary by state. [^24^] [^27^]

- **Configurable Tax Rule Engine Design**: The three-layer architecture (Rule Store / Execution Engine / Override Workflow) with effective-date-aware rules, priority-based conflict resolution, and mandatory approval workflows is critical for a global accounting system. [^84^] Vertex's approach of covering 19,000+ jurisdictions with continually updated content demonstrates the scale required. [^88^]

- **Intercompany Elimination Automation**: ASC 810 and IFRS 10 require 100% elimination regardless of ownership percentage. [^105^] The four elimination types (debt, revenue/expense, ownership, unrealized inventory profit) must be supported with proper audit trails and matching logic for timing/amount/description mismatches. [^98^] [^99^]

- **Multi-Currency Translation per IAS 21**: The distinction between functional currency, presentation currency, and transaction currency; the handling of monetary vs. non-monetary items; the treatment of FX gains/losses (P&L for monetary items, OCI for translation reserves); and the special rules for net investment hedges all require careful architectural consideration. [^117^] [^119^]

- **UPU S42 Address Standard Integration**: Country-specific address templates with mandatory/optional elements, different scripts (Latin, Hanzi, Arabic, Cyrillic, Thai), and rendering rules must be incorporated into customer/vendor master data. The S42 standard covers templates for 30+ countries with formal XML descriptions. [^86^] [^89^]

- **Transfer Pricing Documentation & CbCR**: OECD BEPS Action 13 requires three-tier documentation (master file, local file, CbCR) for MNEs with consolidated revenue ≥€750 million. The accounting system must support arm's length pricing documentation and country-by-country reporting data collection. [^103^]

---

### Architecture Implications for Global Accounting System

#### 1. Tax Engine Core
- Implement a **three-layer configurable architecture**: Rule Store (structured repository with effective dates, priorities, statutory references), Execution Engine (runtime rules interpreter), and Override Workflow (approval with segregation of duties). [^84^]
- Support **jurisdiction hierarchies**: Country → State/Province → Local, with override capability at each level
- Store rules with **effective date ranges** to support retroactive amendments and historical queries
- Implement **priority-based conflict resolution** when multiple rules match a transaction
- Cache active rules at runtime but support hot-reload for emergency rate changes

#### 2. Tax Type Registry
Design the system to handle these tax types at minimum:
- **VAT** (UK, EU): Destination-based, input tax credits, MTD API submission
- **GST** (AU, NZ, CA, SG, IN): Origin/destination hybrid, input tax credits, varying thresholds
- **Sales Tax** (US): Origin-based (some states), destination-based (others), no input credits, nexus-driven
- **Withholding Tax** (dividends, interest, royalties): Treaty-rate-aware, cross-border payments
- **Digital Services Tax** (various): Separate from VAT/GST in some jurisdictions

#### 3. Multi-Entity Architecture
- Each legal entity is a **separate accounting entity** with its own functional currency, chart of accounts, and tax registrations
- **Intercompany transactions** must be tagged at source with IC accounts (e.g., "IC-SALE", "IC-LOAN") [^99^]
- **Consolidation layer** supports four elimination types with automated journal entries: debt, revenue/expense, ownership, unrealized profit in inventory [^99^] [^101^]
- **Translation engine** implements IAS 21: closing rate for balance sheet, transaction-date rate (or average) for P&L, OCI reserve for translation differences [^117^] [^155^]
- Support **non-controlling interest (NCI)** calculation for partially owned subsidiaries

#### 4. Domicile-Aware Address Management
- Store addresses using **UPU S42 components** (recipient, delivery service, thoroughfare, locality, administrative areas, postcode, country) [^86^]
- Apply **country-specific rendering templates** for display and postal output
- Maintain **ISO 3166 country codes** and subdivision codes for jurisdiction detection
- Support multiple address formats per country (e.g., China's Hanzi vs. English formats) [^89^] [^91^]
- Validate addresses against country-specific rules (e.g., Belgium: street number after name, no punctuation; Iran: 4 address types) [^91^]

#### 5. Currency & Exchange Rate Management
- Support **three currency concepts**: transaction currency, functional/base currency, and reporting currency [^155^]
- Use **spot rate** at transaction date for initial recording; **closing rate** for period-end revaluation; **average rate** for P&L translation [^155^]
- Automatically calculate **realized FX gains/losses** at settlement and **unrealized gains/losses** at period-end revaluation
- Track **exchange rate sources** (ECB, XE, central bank rates) with audit trail
- Support **net investment hedging** for intercompany loans denominated in non-functional currencies [^119^]

#### 6. Tax Jurisdiction Detection Engine
- **Place of supply determination** based on transaction characteristics: [^150^] [^152^]
  - Physical goods: destination country (delivery location)
  - B2B services: customer's VAT-registered establishment
  - B2C digital services: customer's usual residence (with 2+ evidence items)
  - On-the-spot services: place of physical performance
  - Property-related services: location of immovable property
- **Economic nexus tracking** for US sales tax: monitor rolling revenue/transaction counts per state
- **Registration threshold monitoring** across all jurisdictions with proactive alerts
- Evidence collection for customer location: billing address, IP address, bank BIN country, SIM country code [^35^]

#### 7. Digital Reporting & API Integration
- **HMRC MTD for VAT**: API-enabled software with digital links between products; quarterly updates; mandatory from first VAT return period [^93^]
- **EU OSS/IOSS**: Quarterly returns via Member State of Identification portal; record retention 10 years [^34^]
- **Australian BAS**: Integrated reporting for GST, PAYG withholding, and other taxes; SBR-enabled digital submission [^118^]
- Support **webhook-based status updates** for filing confirmations and payment receipts

#### 8. Data Model Considerations
- **Entity dimension**: Legal entity, functional currency, domicile country, tax registrations (multiple per entity)
- **Transaction dimension**: Tax type, tax rate, tax jurisdiction, place of supply evidence, OSS/IOSS flags
- **Currency dimension**: Transaction currency, base currency amount, exchange rate, rate source, rate date
- **Address dimension**: S42 components, country template, validated flag, multiple addresses per party
- **Intercompany dimension**: Counterparty entity, IC account type, elimination status, matching reference

---

### Verbatim Excerpts

> "The complete elimination of the intra-entity income or loss is consistent with the underlying assumption that consolidated financial statements represent the financial position and operating results of a single economic entity." -- ASC 810-10-45-18 [^105^]

> "In the preparation of consolidated financial statements, intra-entity balances and transactions shall be eliminated. This includes intra-entity open account balances, security holdings, sales and purchases, interest, dividends, and so forth." -- ASC 810-10-45-1 [^105^]

> "OSS scheme allows distance sellers to maintain one single VAT registration and only one VAT return is to be submitted quarterly for sales in all countries." [^33^]

> "A configurable tax rules engine solves this. Instead of embedding tax logic in code that only developers can change, the engine reads its rules from a structured configuration layer that business and tax administrators can update directly." [^84^]

> "States should reform their marketplace facilitator and remote seller rules and remove the transaction threshold altogether. Indiana recently became the latest state to make the switch, a positive and pro-growth tax reform that others should follow." [^23^]

> "An entity's functional currency is the currency of the primary economic environment in which the entity operates (ie the environment in which it primarily generates and expends cash). Any other currency is a foreign currency." -- IAS 21 [^121^]

> "The S42 international addressing standard comprises of a generic list of address elements (used in all UPU member countries) and country-specific templates that tell users how to transform address elements into an accurately formatted address." [^86^]

---

*Research compiled from 12+ independent web searches across authoritative sources including HMRC, OECD, UPU, IASB, PwC, European Commission, ATO, CRA, Tax Foundation, and industry documentation. All citations use [^number^] format referencing search results.*
