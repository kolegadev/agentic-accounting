## 6. Document Processing and Workflow Automation

The transition from manual data entry to automated document processing represents one of the highest-impact capabilities in modern accounting systems. For a headless, LLM-native platform, document processing and workflow automation serve as the bridge between the physical world of paper invoices, emailed bills, and bank statements and the structured digital ledger. This chapter defines the requirements for document ingestion and extraction, bank feed integration, reconciliation workflows, recurring transactions, and approval routing — all designed to operate through natural language conversation rather than traditional graphical interfaces.

The economic case for automation is substantial. Research on the Multi-Agent Document Processing (MADP) architecture demonstrates that AI-powered extraction combined with human-in-the-loop (HITL) validation achieves 98.5% document-level accuracy while reducing full-time equivalent (FTE) requirements by 70% compared to manual processing [^525^]. At a volume of 100,000 invoices per year, the savings amount to approximately $995,000 annually [^525^]. These figures justify the architectural investment required to build a robust, production-grade document processing pipeline.

### 6.1 Document Ingestion and Extraction

#### 6.1.1 Document Types and Ingestion Channels

The system processes four primary document categories, each with distinct structural characteristics and extraction requirements. Supplier invoices (bills), customer invoices, receipts, and bank statements represent the overwhelming majority of documents that a small or medium-sized enterprise (SME) handles on a recurring basis. The system must accept these documents through multiple ingestion channels to accommodate diverse user workflows.

| Document Type | Supported Formats | Primary Extraction Fields | Typical Source |
|-------------|-----------------|------------------------|--------------|
| Supplier invoice / Bill | PDF, JPG, PNG, TIFF | Vendor, date, due date, line items, subtotal, VAT, total [^62^] | Email attachment, upload, mobile capture |
| Sales invoice | PDF, JPG, PNG | Customer, invoice number, date, line items, amounts, tax [^500^] | Email, customer portal, upload |
| Receipt | JPG, PNG, PDF | Merchant, date, items, total, payment method, tip [^523^] | Mobile camera, email, upload |
| Bank statement | PDF, CSV, OFX, QBO | Account number, period, opening/closing balance, transactions [^276^] | Upload, bank feed (see Section 6.2) |
| Credit note | PDF, JPG, PNG | Original invoice reference, credit amount, reason, date [^279^] | Email attachment, upload |

The ingestion layer supports four distinct channels, mirroring the multi-channel approach used by production document processing systems [^490^]. Email polling monitors dedicated accounting inboxes via webhook triggers, processing PDF and image attachments in real time as they arrive. The upload API accepts direct file submissions via RESTful endpoints with chunked upload support for files up to 50MB, batch upload for multiple documents, and idempotency keys to prevent duplicate processing. Cloud storage webhooks integrate with Google Drive, Dropbox, AWS S3, Azure Blob Storage, and SharePoint through native event notification mechanisms, triggering processing pipelines when new files appear in designated folders [^490^]. Mobile capture provides native SDKs for iOS and Android that perform quality assessment, auto-enhancement (deskewing, contrast adjustment, noise reduction), and edge detection before transmission [^566^].

All documents, regardless of ingestion channel, are stored immutably with SHA-256 checksums and a complete processing history trail. Raw documents are encrypted at rest using AES-256-GCM and tagged with a retention class of `financial_7_years` to comply with UK tax record-keeping requirements [^124^]. The processing pipeline assigns each document a unique identifier that persists through extraction, validation, and eventual linkage to ledger transactions, creating the unbroken digital link chain required by HMRC Making Tax Digital (MTD) regulations.

#### 6.1.2 Extraction Pipeline Architecture

The extraction pipeline follows a hybrid OCR-plus-LLM design inspired by the MADP multi-agent architecture [^498^] and recent research on combining structural awareness from optical character recognition with semantic understanding from large language models [^486^][^494^]. The pipeline operates in six sequential stages, each with defined inputs, outputs, and error handling.

| Stage | Component | Function | Key Metrics |
|------|-----------|----------|-------------|
| 1. Preprocessing | Adaptive preprocessing module | Deskew, denoise, binarize, normalize to 300 DPI [^486^] | +5–10% OCR accuracy improvement |
| 2. Classification | ResNet-18 CNN + LLM verification | Classify document type (invoice, receipt, statement) | 95.3% classification accuracy [^525^] |
| 3. Parsing | Docling (IBM Research) | Layout analysis, table recognition, reading order | +17.5 pp document accuracy contribution; 35% token reduction [^525^] |
| 4. OCR | Mistral OCR 3 / Tesseract / DocTR | Character recognition for scanned documents | 2.1% CER (Mistral OCR 3) [^577^] |
| 5. LLM Extraction | GPT-4o Vision / Claude 3.5 Sonnet | Structured field extraction with schema validation | 92.9% F1 (Mistral-Small-3.2), 91.5% (GPT-4o) [^525^] |
| 6. Validation | Custom rules engine | Mathematical cross-checks, duplicate detection, confidence scoring | Catches 91.67% of extraction errors [^498^] |

The preprocessing stage is critical for maximizing downstream accuracy. Documents undergo noise reduction to eliminate scan artifacts, skew correction via Hough Transform alignment, contrast stretching to recover faded thermal paper text (essential for receipts), and resolution normalization to 300 DPI across all inputs [^486^]. The classification stage uses a ResNet-18 convolutional neural network fine-tuned on document header regions to categorize incoming documents, with LLM-based semantic verification providing a cross-check on the CNN prediction [^525^].

The parsing stage employs Docling, IBM Research's open-source document processing toolkit, to convert documents into structured Markdown or JSON representations. Docling's layout analysis model (RT-DETR, trained on DocLayNet) identifies text regions, tables, and figures, while its TableFormer component reconstructs tabular structure from visually presented data [^526^]. Docling reduces token count by 35% compared to raw OCR output, significantly reducing downstream LLM inference costs [^525^].

For the extraction stage, the system selects a processing path based on document characteristics. Born-digital PDFs with text layers undergo text-first extraction (faster, cheaper, 92%+ accuracy), while scanned documents and images are processed through vision-first multimodal LLM pipelines that achieve 92.71% accuracy versus only 64.03% for text-only pipelines on scanned content [^499^]. The LLM processes documents at temperature 0.0 to ensure deterministic, consistent outputs, with structured output schemas enforced through Pydantic validation [^496^][^500^]. For high-value invoices, a two-pass verification step performs primary extraction followed by a validation challenge pass to catch errors before they propagate downstream [^269^].

#### 6.1.3 Key Performance Metrics

The extraction pipeline targets specific accuracy metrics at each stage. OCR accuracy at the character level ranges from 92–95% for production engines, with Mistral OCR 3 achieving a character error rate (CER) of 2.1% on complex layouts [^577^]. End-to-end extraction accuracy — defined as the percentage of documents where all critical fields are extracted correctly without human intervention — reaches 95–97% when validation rules are applied [^602^].

At the document level, the MADP architecture reports 97–98.5% accuracy when combining AI extraction with human-in-the-loop validation, compared to 85% for pure AI without human review [^525^]. The system achieves an 80% reduction in human intervention versus fully manual data entry, with the remaining 20% of documents requiring review concentrated in low-confidence extractions and complex multi-page documents [^525^]. The human review time per flagged document averages approximately 45 seconds, compared to 120 seconds for full manual processing [^498^].

Documents with any field scoring below 90% confidence are automatically flagged for human review. The confidence scoring system uses a calibrated per-field approach: financial totals require ≥0.95 confidence for auto-approval, invoice numbers and dates require ≥0.90, line items ≥0.85, and descriptive fields ≥0.70 [^580^][^581^]. This tiered threshold reflects the differential cost of errors across field types — an incorrect total amount has far greater downstream impact than a misspelled vendor description.

#### 6.1.4 Validation Rules and Silent Failure Prevention

The validation layer is the most critical component for preventing silent failures — situations where incorrect data passes through the pipeline undetected and propagates into financial reports, tax calculations, and payment instructions [^507^][^510^]. The system implements four categories of validation rules.

Mathematical validation enforces amount consistency across every document. The sum of line items must equal the stated subtotal (±$0.01 tolerance). The subtotal plus tax minus discount must equal the total amount due (±0.5% tolerance for rounding). Per-line validation confirms that quantity multiplied by unit price minus discount equals the stated line total. For receipts, subtotal plus tax plus tip must equal the total [^567^][^568^][^573^].

Date validation ensures that invoice date precedes due date, that neither date is in the future, and that invoice dates fall within the last five years. VAT calculation verification confirms that stated tax amounts equal the net amount multiplied by the applicable rate (with tolerance for rounding differences across jurisdictions). Duplicate detection operates at three layers: exact matching on normalized invoice number plus vendor plus amount catches 30–40% of duplicates; fuzzy matching on amount, date proximity, and string similarity catches 60–80% of near-duplicates; and AI-powered multi-dimensional analysis achieves 95–99% duplicate detection accuracy at scale [^514^].

The system assigns confidence scores to every extracted field and flags any document with a validation failure for priority review. A periodic random sampling of 5% of auto-approved documents provides ongoing quality monitoring. Downstream anomaly tracking — such as unexpected payment disputes or vendor complaints — serves as a final safety net for catching extraction errors that evade upstream validation [^507^].

### 6.2 Bank Feed Integration

#### 6.2.1 Multi-Aggregator Strategy

Bank feed integration eliminates the most tedious aspect of bookkeeping: manual transaction entry. The system connects to banks through a multi-aggregator abstraction layer that routes connections based on geographic region, institution, and API availability. This approach maximizes coverage while minimizing single-provider dependency risk.

| Provider | Primary Region | Institution Coverage | Connection Method | PSD2 AISP | Priority |
|---------|---------------|---------------------|-------------------|-----------|----------|
| TrueLayer | UK, EU (14 countries) | 1,000s | Open Banking APIs, FCA-regulated [^261^] | FCA-licensed | Primary (UK/EU) |
| Plaid | US, CA, UK, EU (20 markets) | 12,000+ live [^258^] | OAuth + screen-scraping fallback | Yes [^258^] | Secondary (UK/EU), Primary (US/CA) |
| Salt Edge | 60+ countries | 3,000+ [^265^] | PSD2 Open Banking gateway | Yes [^265^] | Tertiary (EU multi-country) |
| Yodlee (Envestnet) | Global | 17,000+ [^254^] | Screen-scraping + direct API | Yes [^254^] | Fallback (specialist institutions) |

The aggregator selection logic follows a priority chain. For UK connections, TrueLayer serves as the primary provider because it is purpose-built for UK and EU Open Banking, holds FCA regulation as an Account Information Service Provider (AISP), and supports instant bank payments through PSD2 APIs [^261^]. Plaid provides secondary coverage with 12,000+ live institutions across 20 markets and supports additional product lines including identity verification and income verification [^258^]. Salt Edge offers tertiary coverage for businesses operating across multiple EU countries, aggregating access to 3,000+ institutions in 60+ countries through a single PSD2 gateway [^265^]. Yodlee provides fallback coverage for smaller institutions and credit unions that other aggregators may not support, with the broadest global footprint at 17,000+ institutions [^254^].

All EU and UK connections operate under PSD2 with Strong Customer Authentication (SCA), requiring multi-factor customer consent that expires after 90 days and must be renewed. The system manages this consent lifecycle automatically, sending renewal prompts before expiry and maintaining connection health monitoring with automatic retry on transient failures.

#### 6.2.2 Feed Ingestion Features

The ingestion pipeline follows a five-stage design: Poll → Normalize → Deduplicate → Queue → Process [^221^][^222^]. During the Poll stage, the system performs daily automatic polling for new transactions (configurable to hourly for high-volume accounts), with on-demand refresh available via API. On initial connection, the system backfills up to 12–24 months of historical transaction data [^352^], enabling immediate reconciliation against existing ledger entries. Real-time webhook subscriptions from supported aggregators trigger instant processing when new transactions post to the connected account.

Normalization transforms aggregator-specific schemas into a canonical transaction format. The canonical schema includes: `transaction_id` (aggregator persistent identifier), `account_id` (internal bank account reference), `amount` (normalized with positive for credit, negative for debit), `currency` (ISO 4217 code), `transaction_date` (posted date), `description` (raw bank narrative), `merchant_name` (where available — Plad reports 97% fill rate), `reference` (transaction reference number), `transaction_type` (debit, credit, transfer, fee, interest), and `status` (pending, posted, cancelled) [^348^][^358^]. The raw aggregator response is stored in a JSONB column for audit and debugging purposes.

Deduplication operates through multiple mechanisms. Aggregator-provided persistent transaction IDs (such as Plaid's `transaction_id` field) survive updates and provide the primary deduplication key [^348^]. For transactions without stable IDs (CSV imports), the system computes a content hash of date, amount, description, and account identifier. OFX and QBO file imports use the Financial Transaction ID (FITID) designed specifically for duplicate prevention [^276^][^284^]. A sliding window detection flags transactions within ±1 day with identical amounts and similar descriptions as potential duplicates requiring review.

The system supports unlimited multi-bank connections per organization, with each connection independently monitored for health. Connection status tracking includes `active`, `disconnected`, `error`, and `consent_expired` states, with automated alerting when a connection has not successfully synced within a configurable threshold (default: 48 hours).

#### 6.2.3 Bank Rules Engine

The bank rules engine provides Xero-style automatic categorization that matches incoming bank transactions against user-defined conditions and assigns general ledger accounts, contacts, tax rates, and tracking categories without manual intervention [^277^][^281^].

| Condition Field | Supported Operators | Example |
|---------------|-------------------|---------|
| Description | `equals`, `contains`, `starts_with`, `ends_with`, `regex` | "contains SPOTIFY" |
| Payee / Merchant | `equals`, `contains`, `starts_with` | "equals Stripe" |
| Amount | `equals`, `between`, `greater_than`, `less_than` | "between 5.00 and 20.00" |
| Reference | `equals`, `contains`, `regex` | "matches INV-[0-9]+" |
| Bank Account | `equals`, `in` | "in [checking, savings]" |
| Direction | `is` | "is spend" or "is receive" |

Rules support AND/OR condition logic and are evaluated in priority order (lowest number first), with the first matching rule winning. Ambiguity detection flags transactions where multiple rules match, prompting user review to resolve conflicts.

Each rule has three possible execution modes. **Suggest** mode pre-fills the reconciliation form with the rule's assigned account, contact, and tax rate but requires explicit user confirmation — this is the recommended default for new rules [^277^]. **Auto-apply** mode automatically categorizes and reconciles matching transactions without human intervention, appropriate only after a rule has demonstrated reliable matching across multiple cycles. **Disabled** mode stores the rule without evaluating it, useful for seasonal or temporary rules.

The system ships with 50+ pre-built rule patterns covering common transaction types: Stripe payouts, AWS charges, software subscriptions (Spotify, Slack, Zoom), telecommunications (mobile and broadband), council tax, utility bills, and payroll deposits. Users can create custom rules via natural language commands to the LLM ("Whenever Spotify appears in the description for between £5 and £20, categorize it as Software Subscriptions with 20% VAT"). Rule effectiveness analytics track the percentage of transactions auto-matched versus suggested versus missed, enabling continuous refinement.

### 6.3 Reconciliation Workflows

#### 6.3.1 Manual Reconciliation (MVP)

The Minimum Viable Product delivers a manual reconciliation workflow presented through the LLM conversational interface. The six-step workflow follows established best practices [^220^][^338^][^344^]: (1) import bank transactions from feeds or file uploads; (2) review unmatched bank lines presented in priority order (highest amount first); (3) match bank transactions to existing ledger entries (invoices, bills, journal entries) using side-by-side comparison; (4) create new ledger entries for unmatched items with natural language commands ("That £56.40 charge is for office stationery from Tesco"); (5) confirm that the reconciliation balances (opening balance plus transactions minus reconciled items equals closing balance); and (6) generate a reconciliation report.

Matching supports one-to-one relationships (single bank transaction to single invoice) and one-to-many relationships (single bank deposit covering multiple invoice payments). Partial matching handles situations where the bank amount differs from the ledger amount — for example, when bank fees are deducted from a transfer. In partial match cases, the system prompts the user to explain the difference, recording the fee as a separate transaction line.

The reconciliation status flow tracks transactions through states: `imported` (raw from feed) → `unmatched` (no corresponding ledger entry found) → `suggested` (candidate match identified) → `confirmed` (user or rule accepted the match) → `reconciled` (final balanced state). Transactions can also transition to `excluded` (intentionally not reconciled, such as personal expenses on a business card) or `voided` (transaction reversed or cancelled) [^277^].

#### 6.3.2 ML-Powered Reconciliation (Phase 4)

Phase 4 introduces machine learning-powered matching modeled on Xero's JAX system, which targets 80%+ auto-reconciliation of bank statement lines in real time with 97%+ accuracy on suggested matches [^345^][^349^]. The architecture follows Xero's four-layer intelligence model:

| Layer | Function | Confidence Range | Action |
|------|----------|-----------------|--------|
| Rule | User-defined bank rules match on description, amount, reference | 95–99% | Auto-reconcile (if auto-apply enabled) [^277^] |
| Match | Transaction matches existing document (invoice, bill, payment) | 90–100% | Auto-reconcile or suggest |
| Memory | Per-organization Random Forest learns from user's historical decisions | 75–94% | Suggest for review [^345^] |
| Prediction | Anonymized crowd-sourced patterns from similar businesses | 60–74% | Suggest with caveat |
| Exception | Insufficient confidence across all layers | <60% | Flag for manual review |

The machine learning model is trained per organization using 12 months of historical reconciliation decisions [^352^], ensuring that patterns are specific to the business rather than generic across all users. The feature vector includes transaction amount, day of week, hour of day, merchant name, description keywords, historical category distribution, and reference number patterns [^280^]. A Random Forest classifier handles the mixed feature types (categorical and continuous) effectively, with FuzzyWuzzy string similarity for vendor name variation matching [^280^].

Confidence scoring follows a tiered approach. Scores of 95–100% trigger auto-reconciliation when the feature is enabled. Scores of 90–94% auto-reconcile only in conservative mode. Scores of 75–89% generate suggestions for user review. Scores of 60–74% generate suggestions with an explicit caveat flag. Scores below 60% route to the exception queue for manual investigation [^282^][^345^]. Every ML match includes an explainability statement indicating which layer produced the match — Rule, Match, Memory, or Prediction — with specific reasoning ("You usually categorize transactions from ACME Corp to Office Supplies (94% historical rate)") [^351^].

The per-organization model addresses the cold-start problem through transfer learning: new organizations benefit from anonymized patterns learned across all businesses, while existing organizations receive increasingly personalized suggestions as their reconciliation history grows [^345^]. Models retrain periodically as new reconciliation decisions are captured, with accuracy monitoring to detect degradation and trigger retraining when performance drops below thresholds.

### 6.4 Recurring Transactions and Approvals

#### 6.4.1 Recurring Transactions

Recurring transactions automate repetitive journal entries that follow predictable patterns. The system uses a template-plus-schedule architecture where each recurring transaction defines the transaction details (accounts, amounts, descriptions, VAT rates) and a schedule governing when instances are generated.

Schedules support frequencies of weekly, bi-weekly, monthly, quarterly, and annual, with custom intervals (e.g., every six weeks) available for non-standard cycles. End conditions specify when the series terminates: never (indefinite), after N occurrences, or until a specific date. Posting mode determines whether generated instances are automatically posted to the ledger or created as drafts requiring review. Pre-built templates cover common scenarios including rent, insurance premiums, loan repayments, depreciation, and subscription charges.

When a recurring transaction instance is generated, the system creates a transaction in `draft` status (if draft-for-review mode is selected) or `posted` status (if auto-post is enabled), with a reference linking back to the parent template. Missed generations — due to system downtime or configuration errors — are detected and queued for catch-up processing, with user notification via the LLM chat interface.

#### 6.4.2 Recurring Invoices and Payment Collection

Recurring invoices extend the template architecture to customer-facing billing. The template captures customer details, line items (products, services, descriptions, quantities, rates), tax settings, payment terms, accepted payment methods, and branding configuration [^220^][^349^]. On each scheduled generation, the system creates an invoice, transitions it through the standard invoice lifecycle (draft → approved → sent), and delivers it to the customer via email.

Integration with Stripe and GoCardless enables automatic payment collection. For Stripe, invoices use the `charge_automatically` collection method to attempt payment using the customer's saved default payment method [^358^]. For GoCardless, recurring mandates authorize automatic Direct Debit collection on each invoice generation, with settlement occurring in 3–5 business days at a transaction fee of 1% plus £0.20 (capped at £4 in the UK) [^225^].

Failed payment handling follows a structured retry sequence. On first failure, the system sends a notification email to the customer and enters a 24-hour retry countdown. A second automatic attempt occurs after the retry interval; if this also fails, a third and final attempt is made after another 24 hours. After three failed attempts, the invoice is marked as "declined," automatic retry stops, and the customer is directed to update their payment information or pay manually. Each retry event is logged with the failure reason (insufficient funds, expired card, bank refusal) for reporting and dunning workflow triggers [^350^].

#### 6.4.3 Approval Workflows

The approval workflow engine addresses a critical gap in mainstream small business accounting software. Xero provides only single-step approval (one approver reviews and approves or rejects). QuickBooks Online Advanced, introduced in April 2024, supports multi-level chains but allows only one active approval workflow at a time, lacks delegation for out-of-office scenarios, and locks the feature behind the most expensive plan tier ($200+ per month) [^222^][^224^]. Sage Intacct offers stronger native workflows but with limited conditional branching [^223^]. ApprovalMax, the de facto standard for Xero and QuickBooks users seeking robust approvals, demonstrates market demand for multi-step, conditional approval automation [^283^].

| Amount Threshold | Approval Route | Escalation SLA | Notification Channel |
|-----------------|----------------|---------------|---------------------|
| < GBP 500 | Auto-approved (no human review) | N/A | Log entry only |
| GBP 500 – 2,000 | Direct manager / Department head | 48 hours → escalate to finance director | LLM chat + email |
| GBP 2,000 – 10,000 | Finance director | 24 hours → escalate to CFO | LLM chat + email + push |
| > GBP 10,000 | CFO or designated executive | Same business day [^344^] | All channels + SMS |

The approval engine supports multiple routing criteria beyond amount thresholds. Vendor category rules route contractor invoices to project managers regardless of amount. Department or cost centre rules direct marketing spend to the Marketing Director. First-time vendor rules apply additional scrutiny requiring finance review for any new supplier. Rules can be combined with AND/OR logic to create sophisticated conditional routing ("If amount > GBP 5,000 AND vendor is new, route to CFO; otherwise, route to department head") [^283^].

Delegation during absence allows any approver to designate a substitute for a defined period, with optional calendar integration for automatic out-of-office detection. Escalation rules specify the timeframe within which an approver must respond (configurable per step, with 48 hours as the default) and the escalation target if the deadline is missed. Reminder cadence sends notifications at 24-hour, 48-hour, and 72-hour intervals before escalation [^222^].

Approval actions include: **Approve** (advances to next step or finalizes), **Reject** (returns to submitter with required reason), **Request Changes** (returns with specific change requests without full rejection), **Delegate** (forwards to designated alternate), and **Add Comment** (note without status change). Every approval action is logged with timestamp, approver identity, action taken, IP address, device information, and comments — forming an immutable audit trail that satisfies separation of duties requirements under SOX and internal control frameworks [^223^].

The approval workflow integrates with the LLM conversational interface. Approvers receive notifications in chat ("Invoice INV-2025-0042 from ACME Supplies for GBP 3,240 requires your approval") and can approve or reject via natural language reply ("Approve that invoice" or "Reject — the amount seems wrong, check the line items"). For users preferring email, approval links provide one-click actions that route back through the API. The approval decision itself becomes an auditable event in the ledger, linked to the underlying transaction through the same correlation ID that connects the LLM request to the Numscript generation to the ledger posting.
