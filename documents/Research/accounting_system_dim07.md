# Dimension 07: Invoicing, AR/AP & Approval Workflows

## Executive Summary

This document designs the complete invoice-to-cash (AR) and purchase-to-pay (AP) workflow system for a next-generation accounting platform. Our research benchmarks against Xero, QuickBooks Online Advanced, Sage Intacct, FreshBooks, Stripe, GoCardless, and specialized tools like ApprovalMax. Key competitive differentiators identified include: multi-step approval workflows (Xero only offers single-step), intelligent document extraction achieving 94-97% accuracy with LLM-based systems [^55^][^263^], and deeply integrated payment collection via Stripe and GoCardless.

---

## 1. Invoice Lifecycle

### 1.1 Standard Invoice Status Flow

The invoice lifecycle tracks a sales invoice from creation through archival. Based on industry-standard implementations from PayPal, Stripe, Monite, and OpenMeter [^268^][^267^][^266^], the recommended status flow is:

```
DRAFT --> APPROVED --> SENT --> VIEWED --> PAID --> RECONCILED --> ARCHIVED
  |          |          |         |         |           |             |
  |          |          |         |         |           |             |
  |       (internal   (email/  (customer  (payment   (bank      (retention
  |       review)      portal)   opens     received)   feed       period
  |                             payment             match)     expired)
  |                             link)
  |
  v
CANCELLED/Voided (at any stage before PAID)
```

### 1.2 Status Definitions

| Status | Description | Editable? | Key Triggers |
|--------|-------------|-----------|--------------|
| **Draft** | Invoice created but not yet finalized. All fields editable. | Yes | Manual creation, recurring template generation, quote conversion |
| **Approved** | Internal approval obtained (if required). Ready to send. | Partial | Approval workflow completion, auto-approval for small amounts |
| **Sent** | Invoice delivered to customer via email/portal/QR code. | No (lifecycle-protected) [^264^] | Email sent, customer portal notification |
| **Viewed** | Customer has opened/clicked the invoice link. | No | Email tracking pixel, portal pageview event |
| **Paid** | Full payment received and matched. | No | Stripe webhook, bank feed match, manual payment entry |
| **Partially Paid** | Some payment received, balance outstanding. | No | Partial Stripe payment, partial bank transfer |
| **Overdue** | Past due date without full payment. | No | Time-based auto-transition from Sent status |
| **Uncollectible** | Marked as bad debt/write-off. | No | Manual designation, dunning process completion |
| **Reconciled** | Payment matched to bank transaction. | No | Bank reconciliation process |
| **Archived** | Retention period complete, read-only access. | No | Retention policy (e.g., 7+ years) |

### 1.3 Lifecycle Protection

Modern accounting platforms implement lifecycle protection: after an invoice is sent, paid, or exported, customer-facing document fields (customer, line items, totals, tax, currency, sent PDF contents) become protected and immutable. Safe internal operations like notes and approved payment reconciliation can still occur. [^264^] If an invoice was sent with incorrect contents, the correct workflow is to create a correction or cancellation document rather than editing the committed invoice history.

### 1.4 Status Transition Matrix

| From / To | Draft | Approved | Sent | Viewed | Paid | Overdue | Cancelled |
|-----------|-------|----------|------|--------|------|---------|-----------|
| **Draft** | -- | Yes | Yes | -- | -- | -- | Yes |
| **Approved** | -- | -- | Yes | -- | -- | -- | Yes |
| **Sent** | -- | -- | -- | Yes | Yes | Yes | Yes |
| **Viewed** | -- | -- | -- | -- | Yes | Yes | Yes |
| **Paid** | -- | -- | -- | -- | -- | -- | No |
| **Overdue** | -- | -- | -- | -- | Yes | -- | Yes* |

*Cancellation of overdue invoices should require elevated permissions.

---

## 2. Quote-to-Invoice Workflow

### 2.1 Xero's Current Approach

Xero provides a basic quote-to-invoice workflow where accepted quotes can be converted to invoices with pricing details transferred automatically. [^281^] However, Xero does not support payment collection on quotes directly -- customers can "accept" a quote but cannot pay on the spot. [^278^] Users have long requested that the "accept" button either trigger auto-conversion to an invoice with immediate payment or at minimum collect an email address for invoicing.

### 2.2 Recommended Quote-to-Cash Flow

```
CREATE QUOTE --> SEND QUOTE --> CUSTOMER ACCEPTS --> CONVERT TO INVOICE
                                                                    |
    (include optional deposit)                                       v
                                                         +------------------+
                                                         |  Deposit Invoice |
                                                         |  (if applicable) |
                                                         +---------+--------+
                                                                   |
                                                                   v
                                               +-----------------------------------+
                                               |         Full Invoice             |
                                               |  (balance after deposit applied)  |
                                               +-----------------+-----------------+
                                                                 |
                                                                 v
                                               +-----------------------------------+
                                               |    Customer pays via Stripe/      |
                                               |    GoCardless/Apple Pay/Google Pay|
                                               +-----------------+-----------------+
                                                                 |
                                                                 v
                                               +-----------------------------------+
                                               |    Receipt generated & sent       |
                                               |    (auto-generated on payment)    |
                                               +-----------------------------------+
```

### 2.3 Quote Status States

| Status | Description |
|--------|-------------|
| **Draft** | Being prepared, not yet sent |
| **Sent** | Delivered to customer |
| **Viewed** | Customer has opened the quote |
| **Accepted** | Customer has accepted (with optional e-signature) |
| **Declined** | Customer has declined |
| **Expired** | Past expiry date without response |
| **Converted** | Successfully converted to invoice(s) |

### 2.4 Acceptance Options

The system should support multiple acceptance modes:

- **Simple acceptance**: Customer clicks "Accept" -- triggers notification to sales team
- **Acceptance with e-signature**: Customer digitally signs the quote for legally binding acceptance
- **Acceptance + deposit payment**: Customer accepts AND pays a configurable deposit percentage immediately via Stripe Payment Link [^365^]
- **Acceptance + full payment**: Customer accepts and pays the full amount (converts to paid invoice instantly)

### 2.5 Receipt Generation

Upon payment receipt, the system should automatically generate and send a payment receipt via email. This can be implemented using Stripe's webhook system: on `invoice.payment_succeeded` event, retrieve receipt HTML from Stripe and send via email, or generate a custom receipt document from the platform. [^368^]

---

## 3. Recurring Invoices

### 3.1 Template-Based System

Based on QuickBooks Online and FreshBooks implementations, recurring invoices use a template + schedule architecture: [^220^][^349^]

**Template Components:**
- Customer details (with default billing/shipping contacts)
- Line items (products, services, descriptions, quantities, rates)
- Tax settings (per-line and summary tax)
- Payment terms (due on receipt, Net 30, etc.)
- Payment options (which payment methods to accept)
- Custom messages, notes, and footer text
- Branding (logo, color scheme, font)

### 3.2 Schedule Configuration

| Setting | Options |
|---------|---------|
| **Frequency** | Weekly, Bi-weekly, Monthly, Quarterly, Semi-annual, Annual, Custom (e.g., every 6 weeks) |
| **Start Date** | Immediate or specific future date |
| **End Condition** | Infinite, specific number of invoices, or end date |
| **Delivery Mode** | Auto-send (email on generation) or Draft (create for review) |
| **Payment Collection** | None, AutoPay (opt-in), AutoCollect (require card on file) [^350^] |

### 3.3 Auto-Send with Payment Collection

FreshBooks demonstrates an advanced pattern where recurring templates can be configured to:
- Generate invoices automatically and email them to clients
- Automatically charge saved payment methods (AutoPay for opt-in, AutoCollect for required) [^350^]
- Pull unbilled time entries and expenses onto generated invoices automatically [^349^]
- Support payment schedules with up to 12 installments on a single invoice [^353^]

**Failed Payment Handling:**
When a recurring payment fails, the system should:
1. Send failure notification email to customer
2. Enter "Retry" status -- automatically retry in 24 hours
3. Retry a second time if first retry fails
4. After second failure, mark invoice as "Declined" and stop auto-retrying
5. Allow manual retry by customer updating payment info or merchant triggering retry [^350^]

### 3.4 Payment Schedule Support

Payment schedules allow clients to pay invoices in multiple installments on dates chosen by the business. Key features: [^353^]
- Configure percentage-based or flat amount installments
- Up to 12 payment installments per invoice
- Client can pay one scheduled payment at a time or select multiple to pay together
- Invoice status is NOT affected by the payment schedule (recommend setting due date to match last payment)

### 3.5 Template Management

Recurring template statuses should include: [^349^]
- **Auto-Draft**: Generates draft invoices for review
- **Auto-Sent**: Generates and emails invoices automatically
- **Card/Account Saved**: Auto-generates, auto-charges saved payment, sends payment notification
- **Inactive**: Paused or completed, no longer generating

---

## 4. Supplier Bill Lifecycle

### 4.1 Bill Status Flow

```
RECEIPT --> DATA EXTRACTION --> CODING --> APPROVAL --> PAYMENT SCHEDULING --> PAID --> RECONCILED
   |            |                |            |              |               |          |
   |            |                |            |              |               |          |
(email,     (OCR + LLM       (GL        (workflow     (selected     (payment     (bank
 upload,       extraction)      account,    routing)      into batch    executed)    feed
 portal,                       cost         |               |               |          match)
 scan)                         centre,      v               v               |          |
                               project   APPROVED    PAYMENT RUN    v          |
                                          |          created &      CLEARED     |
                                          v          authorized)    ( funds      |
                                       REJECTED                       debited)   |
                                       (back to                       |          |
                                       sender with                    v          |
                                       reason)                   RECONCILED      |
                                                                               |
                                                                               v
                                                                           ARCHIVED
```

### 4.2 Receipt Capture Channels

Bills can arrive through multiple channels that must all be supported: [^271^][^223^]

| Channel | Method | Notes |
|---------|--------|-------|
| **Email** | Forward to unique inbox address | Auto-extract attachments, auto-classify |
| **File Upload** | Drag-and-drop or file picker | Web UI, mobile app, bulk upload |
| **Supplier Portal** | API integration or web scraping | For major suppliers with portals |
| **Scan/Mobile Photo** | Mobile app camera capture | OCR + image enhancement |
| **Bank Feed** | Bank statement line items | Match to bills for reconciliation |

### 4.3 Data Extraction Pipeline

#### 4.3.1 LLM-Based Invoice Extraction

Modern invoice extraction combines OCR with Large Language Models. A production-grade pipeline works as follows: [^263^][^55^]

**Stage 1: OCR Text Extraction**
- Convert PDF/images to text using OCR (PyMuPDF, pdfplumber for digital PDFs; vision OCR for scanned documents)
- Pre-process: deskew, denoise, enhance contrast
- Bad files flagged for manual review

**Stage 2: LLM Structured Extraction**
- Feed OCR text to LLM with strict JSON schema (using Zod or Pydantic models)
- Schema-enforced output ensures consistent field mapping
- Example extracted fields: vendor_name, invoice_number, invoice_date, due_date, line_items (array), subtotal, tax, grand_total, currency, PO_number

**Stage 3: Validation & Enrichment**
- Cross-validate: line item totals sum to subtotal, tax is reasonable percentage (0-30%), dates are within valid ranges
- Deduplication check against existing bills
- Vendor matching against vendor master data
- GL coding suggestions based on historical patterns

**Stage 4: Confidence Scoring & Routing**
- High confidence (>= 85%): Auto-route to approval workflow
- Low confidence (< 85%): Route to human review queue [^221^]

#### 4.3.2 Accuracy Benchmarks

| Method | Overall Accuracy | Line Item Accuracy | Consistency | Processing Time |
|--------|-----------------|-------------------|-------------|-----------------|
| OCR + Regex (traditional) | ~60-70% | ~50% | Low | Fast |
| Docling (OCR-based) | 63% | Lower | 80% pass | 10s/doc |
| **LLamaExtractor (LLM-based)** | **94%** | **91%** | **93%** pass | 30s/doc |
| OCR + Gemini 2.5 Flash | 97% | ~95% | High | Fast-moderate |

The LlamaExtractor achieved 94% overall accuracy with 93% consistency check pass rate and zero mathematical validation errors. [^55^] Production implementations using OCR + LLM pipelines report line-item recall improvements from 88% (OCR alone) to 97% (OCR + LLM), with compute costs reduced by 70% when using Gemini 2.5 Flash. [^263^]

**Key Engineering Practices:**
- Temperature 0.0 for extraction tasks (consistency over creativity)
- Strict JSON schema enforcement (Zod/Pydantic) to eliminate malformed responses
- Two-pass verification for high-value invoices: primary extraction + validation challenge pass [^269^]
- Hybrid approach: traditional OCR for text extraction, LLM for reasoning and structuring [^263^]

### 4.4 Bill Data Model

| Field | Type | Source |
|-------|------|--------|
| vendor_id | UUID | Matched from vendor master |
| bill_number | String | Extracted from document |
| bill_date | Date | Extracted from document |
| due_date | Date | Extracted or calculated from terms |
| po_number | String | Extracted or matched |
| currency | Currency code | Document or vendor default |
| exchange_rate | Decimal | For multi-currency |
| line_items | Array | Extracted + editable |
| subtotal | Decimal | Calculated |
| tax_amount | Decimal | Extracted or calculated |
| total_amount | Decimal | Extracted (validated) |
| gl_account | Account reference | Suggested from history |
| cost_centre | String | From vendor rules or manual |
| project | String | From PO matching or manual |
| status | Enum | Workflow state |
| confidence_score | Decimal (0-1) | Extraction quality |
| approval_status | Enum | Pending/Approved/Rejected |

---

## 5. Approval Workflows

### 5.1 Xero's Limitation: Single-Step Only

Xero's built-in approval is limited to a single step: one approver reviews and either approves or rejects. This is insufficient for organizations with tiered approval requirements (e.g., manager -> finance director -> CFO for large amounts).

### 5.2 QuickBooks Online Advanced: Multi-Level (with Gaps)

QuickBooks Online Advanced introduced multi-condition/multi-level approval in April 2024, but with important limitations: [^222^][^224^]

**What works:**
- Sequential approval chains (Approver 1 -> Approver 2 -> Approver 3)
- Amount-based routing (different thresholds trigger different approvers)
- Email and mobile app approvals
- Auto-denial after 30 days of inactivity

**Key limitations:**
- Only ONE active bill approval workflow at a time [^224^]
- Bulk uploads via third-party tools may bypass the workflow
- Bill Pay payment approval is separate from bill approval
- No approval delegation or out-of-office support [^222^]
- Limited custom fields on bills
- Locked behind the most expensive plan tier ($200+/month)

### 5.3 Sage Intacct: Strong Native Workflows

Sage Intacct provides robust approval workflows: [^223^]
- Multi-level routing based on amount thresholds, department, or location
- Sequential or parallel approval chains
- Delegation rules for out-of-office scenarios
- Segregation of duties between invoice entry and payment authorization
- Limitation: conditional branching based on multiple simultaneous criteria is less flexible than dedicated tools

### 5.4 ApprovalMax: The Gold Standard

ApprovalMax extends Xero and QuickBooks with comprehensive approval automation: [^283^]

**Capabilities:**
- Multi-role and multi-tiered approval workflows
- X-way bill-to-PO matching
- Automatic matching of bills and purchase orders
- Reminder, email, and push notifications to avoid delays
- Mobile apps for iOS and Android
- Each approval decision is audit-ready with complete approval history and comments

### 5.5 Recommended Multi-Step Approval Architecture

#### 5.5.1 Approval Rule Engine

| Rule Type | Description | Example |
|-----------|-------------|---------|
| **Amount Threshold** | Route based on bill total | < $500: auto-approve; $500-$5K: manager; > $5K: manager + CFO |
| **Vendor Category** | Different rules per vendor type | Contractor invoices always require PM approval |
| **Department/Cost Centre** | Route to department head | Marketing spend -> Marketing Director |
| **Project Code** | Route to project manager | Project-specific bills -> Project lead |
| **Expense Category** | Different rules by GL account | CapEx > $1K requires CFO; OpEx > $5K requires CFO |
| **First-Time Vendor** | Extra scrutiny for new vendors | New vendors always require finance review |

#### 5.5.2 Approval Chain Configuration

```
SEQUENTIAL (all must approve in order):
  Step 1: Department Head
  Step 2: Finance Director  (only if amount > $threshold)
  Step 3: CFO               (only if amount > $higher_threshold)

PARALLEL (any can approve simultaneously):
  Step 1: Department Head + Finance Analyst (both review, either can approve)
  Step 2: CFO (final sign-off if amount > threshold)

CONDITIONAL:
  IF amount < $500 AND vendor in approved-vendor-list:
    -> Auto-approve
  ELSE IF amount < $5,000:
    -> Department Head
  ELSE:
    -> Department Head -> Finance Director -> CFO
```

#### 5.5.3 Delegation & Out-of-Office

| Feature | Description |
|---------|-------------|
| **Delegation** | Approver can delegate approval authority to a substitute for a defined period |
| **Out-of-Office** | Automatic delegation when calendar integration shows OOO status |
| **Escalation** | If approver doesn't respond within configurable timeframe (e.g., 48h), escalate to their manager or alternate approver |
| **Reminder Cadence** | Initial notification + reminder at 24h, 48h, 72h before escalation |

#### 5.5.4 Approval Actions

| Action | Effect |
|--------|--------|
| **Approve** | Advances to next step or marks as fully approved |
| **Reject** | Returns to submitter with rejection reason; bill enters Rejected status |
| **Request Changes** | Returns to submitter with specific change requests; stays in Pending |
| **Delegate** | Forwards to designated alternate approver |
| **Add Comment** | Adds note without changing approval status |
| **View Attachment** | Opens linked PDF invoice for review |

#### 5.5.5 Audit Trail

Every approval action must be logged with:
- Timestamp (UTC)
- Approver identity
- Action taken (approve/reject/delegate/comment)
- IP address and device info
- Comments/reasoning
- Full before/after state for rejections

---

## 6. Payment Collection

### 6.1 Stripe Integration

Stripe provides comprehensive invoicing and payment collection capabilities: [^358^][^359^][^365^]

#### 6.1.1 Invoice Creation API

```
POST /v1/invoices
- customer: Customer ID (required)
- collection_method: "charge_automatically" | "send_invoice"
- auto_advance: boolean (controls automatic collection)
- metadata: key-value pairs for order tracking
- due_date: payment due date
```

**Collection Methods:**
- `charge_automatically`: Stripe attempts payment using customer's default payment method
- `send_invoice`: Stripe emails invoice to customer with payment link to hosted invoice page [^358^]

#### 6.1.2 Invoice Lifecycle via API

| API Call | Purpose |
|----------|---------|
| `POST /v1/invoices` | Create draft invoice |
| `POST /v1/invoiceitems` | Add line items |
| `POST /v1/invoices/:id/finalize` | Finalize (make non-editable) |
| `POST /v1/invoices/:id/send` | Email to customer |
| `POST /v1/invoices/:id/pay` | Attempt payment immediately |
| `POST /v1/invoices/:id/void` | Void the invoice |
| `POST /v1/invoices/:id/mark_uncollectible` | Mark as bad debt |

#### 6.1.3 Payment Methods Supported

Stripe-hosted invoice pages support: [^365^]
- **Credit/debit cards** (Visa, Mastercard, Amex, Discover)
- **Apple Pay** (Safari on iOS/macOS with Touch ID/Face ID) [^274^]
- **Google Pay** (Android devices, Chrome browser) [^274^]
- **Bank transfers** (ACH, BACS, SEPA)
- **Direct Debit** (BECS, SEPA, Bacs)
- **Buy Now Pay Later** (Klarna)
- **135+ currencies** supported

**Apple Pay/Google Pay Setup:**
- Apple Developer Account with domain verification
- Google Pay API merchant registration
- SSL certificate (HTTPS required)
- Enable in Stripe Dashboard
- Use Express Checkout Element (recommended) or Payment Request API (legacy) [^274^]

#### 6.1.4 Hosted Invoice Page

Each Stripe invoice generates a hosted page with:
- Custom branding (logo, colors, fonts)
- Responsive design for mobile/tablet/desktop
- PDF download option
- Custom email domain support (e.g., invoices@yourcompany.com)
- Multi-language support (25+ languages)

#### 6.1.5 Customer Email Automation

Stripe automatically sends emails for: [^363^]
- Invoice finalized
- Payment failed (with retry link)
- Payment succeeded (receipt)
- Card expiration warning
- Unpaid invoice reminders (configurable: before due, on due date, after due)
- Credit note created
- Refund issued

### 6.2 GoCardless Integration

GoCardless specializes in Direct Debit collection: [^225^][^226^]

| Feature | Details |
|---------|---------|
| **Payment Type** | Bank debit (Direct Debit / BECS) |
| **Transaction Fee** | 1% + 20p (UK, capped at GBP 4); 2% + fixed fee (international) |
| **Settlement** | 3-5 business days |
| **Customer Base** | 75,000+ businesses worldwide |
| **Integrations** | 350+ including Xero, QuickBooks, Chargebee, Salesforce |
| **Failed Payment Handling** | Smart automatic retry logic |
| **Bank Verification** | Instant via Open Banking |
| **Best For** | Recurring billing, subscriptions, retainers |
| **Not Ideal For** | Instant/retail transactions |

**Comparison: Stripe vs GoCardless**

| Factor | Stripe | GoCardless |
|--------|--------|------------|
| Primary Method | Card payments | Direct Debit |
| Currencies | 135+ | 30+ countries |
| Settlement Speed | 2-7 days (varies) | 3-5 days |
| Recurring Fees | Higher (card fees) | Lower (direct debit) |
| Cash Flow Predictability | Moderate | High (known collection dates) |
| Integration Complexity | Rich API, more setup | Simpler, purpose-built |
| Apple/Google Pay | Yes | No |
| Best Use Case | One-off, e-commerce, global | Recurring, subscriptions, B2B |

### 6.3 Recommended Payment Architecture

```
┌─────────────────────────────────────────────────────┐
│                 Payment Orchestration Layer           │
├─────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │   STRIPE     │  │  GoCardless  │  │   PayPal  │ │
│  │  (primary)   │  │  (recurring) │  │  (option) │ │
│  └──────┬───────┘  └──────┬───────┘  └─────┬─────┘ │
│         │                   │                  │      │
│  Cards, Apple Pay     Direct Debit      Alternative  │
│  Google Pay, ACH      (BACS, SEPA)      payment     │
│  Bank transfer                               method │
│         │                   │                  │      │
│         └───────────────────┼──────────────────┘      │
│                             │                         │
│                      Webhook Handler                   │
│                   (payment succeeded/failed)           │
│                             │                         │
│                             v                         │
│              ┌──────────────────────────┐             │
│              │  Invoice Status Updates  │             │
│              │  Receipt Generation      │             │
│              │  Bank Reconciliation     │             │
│              └──────────────────────────┘             │
└─────────────────────────────────────────────────────┘
```

---

## 7. Payment Runs

### 7.1 Payment Run Workflow

A payment run is the batch process of selecting approved bills, generating payment instructions, and executing payment. Based on HedgeFlows and Sage Intacct patterns: [^265^][^223^]

```
SELECT BILLS --> REVIEW & APPROVE --> GENERATE PAYMENT FILE --> AUTHORIZE --> EXECUTE --> RECONCILE
     |               |                        |                    |           |           |
     |               |                        |                    |           |           |
  (filter by     (final sign-off         (ACH file,           (2-eye      (send to  (auto-match
   due date,       by authorized           check run,           principle)  bank)     to bank
   vendor,         payment                wire batch                      |     feed)
   amount)         authority)                                     v          v
                                                                  v      FUNDS
                                                              PAYMENT     CLEARED
                                                              RUN          |
                                                              STATUS       v
                                                                    RECONCILED
```

### 7.2 Bill Selection

**Selection Criteria:**
- Due date range (e.g., next 7 days, next 15 days)
- Vendor(s) or vendor group
- Currency
- Amount range
- Approval status (must be fully approved)
- Exclude bills already in another payment run
- Exclude bills on payment hold

### 7.3 Payment Run Approval

| Step | Action | Required Role |
|------|--------|---------------|
| 1 | Select bills for payment run | AP Clerk |
| 2 | Review payment run summary | AP Manager |
| 3 | Approve payment run (amount-dependent workflow) | Authorized approver |
| 4 | Generate payment file | System |
| 5 | Final authorization ("second pair of eyes") | CFO / Finance Director |
| 6 | Transmit to bank | System or manual upload |

### 7.4 Payment Methods

| Method | Generation | Execution | Reconciliation |
|--------|------------|-----------|----------------|
| **ACH/Bank Transfer** | NACHA file or bank API | Direct bank upload or API | Bank feed match |
| **Check** | Check print file | Physical print + mail | Check clearance tracking |
| **Wire** | Wire instruction file | Bank wire portal or API | Wire confirmation |
| **Virtual Card** | Card number generation | Immediate payment | Card statement match |
| **Direct Debit** (outgoing) | Mandate-based batch | Via GoCardless/Stripe API | Settlement notification |

### 7.5 Fraud Prevention

Payment runs must include fraud prevention measures: [^265^]
- Multi-level approval process (separation of duties)
- Confirmation of Payee (CoP) checks where available
- Bank account validation before payment
- Real-time fraud monitoring and alerts
- Audit trail of all payment run actions

### 7.6 Multi-Currency Payment Runs

For international businesses, payment runs should support:
- Bills in up to 35 currencies in a single batch
- Real-time interbank FX rates
- Automated currency conversion
- FX gain/loss calculation
- Full audit trails per currency [^265^]

### 7.7 Payment Run Status States

| Status | Description |
|--------|-------------|
| **Draft** | Bills selected, under review |
| **Pending Approval** | Awaiting authorization |
| **Approved** | Authorized for payment |
| **Generated** | Payment file created |
| **Submitted** | Payment file sent to bank |
| **Processing** | Bank is processing payments |
| **Partially Paid** | Some payments cleared, others pending |
| **Completed** | All payments cleared |
| **Failed** | One or more payments failed |
| **Cancelled** | Payment run cancelled before execution |

---

## 8. Credit Notes & Adjustments

### 8.1 Credit Note Types

| Type | Trigger | Accounting Effect |
|------|---------|-------------------|
| **Full Refund** | Customer returns all goods/services | Reverse revenue, refund payment |
| **Partial Refund** | Customer returns some items | Partial revenue reversal |
| **Write-Off** | Debt deemed uncollectible | DR Bad Debt Expense, CR AR |
| **Correction** | Invoice error discovered | Reverse incorrect entry, post corrected entry |
| **Discount/Adjustment** | Price adjustment post-invoice | Revenue reduction |

### 8.2 Credit Note Workflow (Odoo Pattern)

Odoo provides a well-structured credit note workflow: [^279^][^355^]

1. **From Invoice**: Open the original invoice, click "Credit Note"
2. **Specify Reason**: Fill in reason for credit note
3. **Choose Method**:
   - **Reverse**: Creates draft credit note prefilled with original details (allows partial refund/modification)
   - **Reverse and Create Invoice**: Auto-validates credit note, reconciles with original, opens new draft invoice
4. **Confirm**: Credit note is validated and posted
5. **Register Payment**: If refunding money, register the payment
6. **Link**: Credit note is linked to original invoice (sequence starts with "R" prefix, e.g., RINV/2025/0004)

### 8.3 Write-Off Workflow (Wave Pattern)

Wave's direct write-off method demonstrates the practical accounting flow: [^347^]

**Step 1: Create Bad Debt Clearing Account**
- Account Type: Money in Transit
- Name: "Bad Debt Clearing"

**Step 2: Create Bad Debt Expense Account**
- Account Type: Operating Expense
- Name: "Bad Debt Expense"

**Step 3: Mark Invoice as Paid (via Clearing Account)**
- Add deposit transaction to Bad Debt Clearing account
- Categorize as "Payment Received for Invoice"
- Select the invoice being written off

**Step 4: Write Off the Clearing Entry**
- Add withdrawal transaction from Bad Debt Clearing
- Categorize as "Bad Debt Expense"
- Amount matches the write-off

**Result**: AR balance cleared, Bad Debt Expense recorded, Bad Debt Clearing has zero balance. [^347^]

### 8.4 Refund Processing (Wave Pattern)

For actual payment refunds: [^344^]
- Full or partial refunds supported
- Refund to original payment method only
- Processing fees refunded pro-rata by Stripe/Wave
- Refund appears on customer card in 3-5 business days (bank transfer: 12-13 days)
- Eligibility: payments within 90 days (older requires support)
- Cannot refund if chargeback in progress

### 8.5 Partial Credit Application

When a customer has credit on their account (from overpayment or credit note): [^357^]
- Credit balance tracked per customer
- Apply credit to specific invoice via "Record Payment" -> "Customer Credit"
- Can apply partial or full credit amount
- Remaining credit stays on customer account for future use

---

## 9. Reminder & Dunning System

### 9.1 Dunning Process Overview

The dunning process is the structured sequence of communications to collect payment on overdue invoices. According to industry best practices: [^273^][^275^][^277^]

**Four Components of Dunning:**
1. **Trigger**: Day invoice goes past due (or with 1-3 day grace period)
2. **Cadence**: How often you reach out and through which channels
3. **Escalation Thresholds**: What changes at each stage (owner, authority, actions)
4. **Exit Condition**: When to stop dunning and take different action (collections referral)

### 9.2 Standard Dunning Sequence

| Stage | Days Past Due | Tone | Channel | Owner | Action |
|-------|--------------|------|---------|-------|--------|
| **Pre-due Reminder** | 3 days before due | Friendly | Email | System (auto) | "Your invoice is due soon" |
| **1. Gentle Reminder** | 1-3 days overdue | Helpful, collaborative | Email | System (auto) | "Quick check on invoice #X" |
| **2. Firm Follow-up** | 7-10 days overdue | Direct, professional | Email | System (auto) | "Please confirm payment status" |
| **3. Formal Notice** | 14-17 days overdue | Serious, consequential | Email + Phone | Credit Analyst | "Payment terms referenced" |
| **4. Escalation** | 21-25 days overdue | Warning | Email + Phone + Letter | Credit Manager | Credit hold, notify sales |
| **5. Demand Letter** | 30-45 days overdue | Formal demand | Certified mail | Credit Manager | Account hold, legal warning |
| **6. Final Notice** | 60+ days overdue | Legal action threatened | Email + Mail + Phone | Credit Director | Collections referral |
| **7. Write-off/Collections** | 90+ days overdue | -- | -- | Finance/CFO | Third-party collections or write-off |

### 9.3 Escalation Framework

| Stage | Timing | Tone | Primary Objective |
|-------|--------|------|-------------------|
| **Gentle Reminder** | 1-15 days past due | Helpful, collaborative | Resolve simple oversights [^276^] |
| **Firm Notice** | 16-30 days past due | Direct, professional | Emphasize due date |
| **Urgent Alert** | 31-60 days past due | Serious, consequential | Signal potential consequences |
| **Final Demand** | 61+ days past due | Firm, final | Set hard deadline before escalation |

### 9.4 Advanced Dunning Features

**Segmented Dunning:** [^272^]
- Tailor follow-up strategies by customer value, country, payment behavior, historical responsiveness
- Stricter handling for habitual late payers
- More flexible approaches for strategic accounts

**Two-Way Communication:** [^272^]
- Capture, classify, and route inbound customer responses
- Questions, disputes, and requests should not stall payment cycles
- AI-assisted platforms handle routine conversations end-to-end

**Promise-to-Pay Tracking:** [^272^]
- Log commitments automatically
- Monitor whether payments arrive as agreed
- Trigger follow-ups automatically when promises are broken

**Multi-Channel Orchestration:**
- Email (primary channel)
- SMS (for urgent follow-ups)
- Phone calls (stage 3+)
- Customer portal messages
- Paper mail (demand letters)

### 9.5 Automated Dunning Configuration

**Per-Customer Settings:**
- Dunning schedule override (some customers get longer grace periods)
- Communication channel preferences
- Contact person for collections
- Internal account manager to notify

**Global Settings:**
- Grace period before first reminder
- Reminder intervals and escalation timeline
- Email template library
- Auto-credit-hold threshold (days past due)
- Auto-collections-referral threshold

### 9.6 Dunning Metrics

Track these KPIs for dunning effectiveness:
- Days Sales Outstanding (DSO)
- Collection Effectiveness Index (CEI)
- Response rate by dunning stage
- Promise-to-pay fulfillment rate
- Bad debt write-off rate
- Cost of collections per dollar recovered

---

## 10. Document Attachment & Management

### 10.1 Document Types

| Document Type | Attach To | Purpose |
|--------------|-----------|---------|
| **Invoice PDF** | Customer invoice | Customer-facing invoice document |
| **Receipt** | Expense, Bill | Proof of payment/expense |
| **Delivery Note** | Invoice | Proof of goods delivered |
| **Purchase Order** | Bill, Invoice | PO matching reference |
| **Credit Note PDF** | Credit note | Customer-facing credit document |
| **Bank Statement** | Reconciliation | Monthly statement for matching |
| **Contract/Agreement** | Customer, Recurring Template | Service terms reference |
| **Photo/Scan** | Expense | Visual proof of expense |

### 10.2 Attachment Workflows

#### 10.2.1 Upload Methods

Based on Patriot Software, freee (Money Forward), and Xero implementations: [^340^][^343^][^362^]

| Method | Description |
|--------|-------------|
| **Drag & Drop** | Drag files directly onto transaction entry forms |
| **File Picker** | Browse and select files from local storage |
| **Bulk Upload** | Upload multiple files at once to a staging area |
| **Email Forward** | Forward emails with attachments to unique Xero-style email address [^362^] |
| **Mobile Camera** | Take photos directly from mobile app |
| **From File Library** | Select previously uploaded files from central library [^362^] |

#### 10.2.2 Xero File Library Pattern

Xero's file management approach: [^362^]
1. Each organization has a unique email forwarding address
2. Forward emails with invoices/receipts to this address
3. Documents appear in File Manager
4. When attaching to a reconciled transaction, select "add from file library"
5. Once attached to a transaction, document is removed from File Manager (linked instead)

#### 10.2.3 freee (Money Forward) Pattern

freee provides advanced document handling: [^343^]
- **File Box**: Central repository for all receipts and documents
- **Split Uploads**: Split multi-page PDFs or multi-receipt photos into individual documents
- **OCR Integration**: Auto-extract date, amount, invoice number from uploaded documents
- **Auto-Match**: Suggest links between documents and existing transactions based on amount/date matching
- **Dual Workflow**: Support both "document -> journal entry" and "journal entry -> document" workflows

### 10.3 Document Features

| Feature | Description |
|---------|-------------|
| **Multiple Attachments** | Link multiple documents to a single transaction |
| **Attachment Icons** | Visual indicator on transaction rows showing attached documents [^340^] |
| **Preview** | Thumbnail preview for image files; click to open full document |
| **Audit Trail** | Document attachments included in full audit trail for compliance |
| **Export with PDF** | When exporting transaction reports to PDF, optionally include linked documents [^338^] |
| **Version Control** | Track document versions if replaced |
| **OCR on Upload** | Automatic text extraction for searchability |
| **Tagging** | Categorize documents with custom tags |

### 10.4 Document Storage Architecture

```
┌──────────────────────────────────────────────────────┐
│                  Document Storage                      │
│              (S3 / Cloud Storage / On-Premise)         │
├──────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐ │
│  │  Encrypted  │  │  Organized  │  │  Versioned   │ │
│  │  at Rest    │  │  by Entity  │  │  History     │ │
│  │  & Transit  │  │  + Date     │  │              │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘ │
│         │                  │                  │       │
│         └──────────────────┼──────────────────┘       │
│                            │                          │
│                    ┌───────v────────┐                 │
│                    │  Metadata DB    │                 │
│                    │  (link to txn)  │                 │
│                    └───────┬────────┘                 │
│                            │                          │
│                    ┌───────v────────┐                 │
│                    │  Search Index   │                 │
│                    │  (OCR text)     │                 │
│                    └─────────────────┘                 │
└──────────────────────────────────────────────────────┘
```

---

## 11. Data Models & Schema

### 11.1 Invoice Entity

```
Invoice:
  - id: UUID (primary key)
  - organization_id: UUID
  - contact_id: UUID (customer)
  - quote_id: UUID (nullable, parent quote)
  - invoice_number: String (auto-generated)
  - reference: String (customer PO reference)
  - status: Enum (draft, approved, sent, viewed, paid, partially_paid, overdue, uncollectible, cancelled, archived)
  - issue_date: Date
  - due_date: Date
  - currency: Currency code
  - exchange_rate: Decimal
  - line_items: Array[InvoiceLineItem]
  - subtotal: Decimal
  - tax_total: Decimal
  - total: Decimal
  - amount_paid: Decimal
  - amount_due: Decimal
  - payment_terms: String (e.g., "Net 30")
  - notes: String (internal)
  - customer_note: String (visible on invoice)
  - footer: String
  - branding_theme_id: UUID
  - sent_at: Timestamp (nullable)
  - viewed_at: Timestamp (nullable)
  - paid_at: Timestamp (nullable)
  - created_at: Timestamp
  - updated_at: Timestamp
  - created_by: UUID (user)
  - approved_by: UUID (user, nullable)
  - approved_at: Timestamp (nullable)
  - collection_method: Enum (charge_automatically, send_invoice)
  - stripe_invoice_id: String (nullable)
  - gocardless_payment_id: String (nullable)
  - recurring_template_id: UUID (nullable)
```

### 11.2 Bill Entity

```
Bill:
  - id: UUID (primary key)
  - organization_id: UUID
  - vendor_id: UUID
  - bill_number: String (vendor's invoice number)
  - reference: String (internal reference)
  - status: Enum (draft, pending_extraction, pending_coding, pending_approval, approved, scheduled, paid, partially_paid, overdue, disputed, cancelled)
  - bill_date: Date
  - due_date: Date
  - currency: Currency code
  - exchange_rate: Decimal
  - line_items: Array[BillLineItem]
  - subtotal: Decimal
  - tax_total: Decimal
  - total: Decimal
  - amount_paid: Decimal
  - amount_due: Decimal
  - payment_terms: String
  - notes: String
  - gl_account_id: UUID
  - cost_centre: String
  - project_id: UUID (nullable)
  - po_number: String
  - po_id: UUID (nullable)
  - extraction_confidence: Decimal (0-1)
  - extraction_data: JSON (raw OCR + LLM output)
  - document_attachments: Array[DocumentReference]
  - approval_workflow_id: UUID
  - approval_status: Enum (pending, in_review, approved, rejected)
  - created_at: Timestamp
  - updated_at: Timestamp
```

### 11.3 Approval Workflow Entity

```
ApprovalWorkflow:
  - id: UUID
  - organization_id: UUID
  - name: String
  - entity_type: Enum (bill, invoice, journal, expense)
  - is_active: Boolean
  - conditions: JSON (rules for matching)
  - steps: Array[ApprovalStep]
  - created_at: Timestamp
  - updated_at: Timestamp

ApprovalStep:
  - id: UUID
  - workflow_id: UUID
  - step_number: Integer (order)
  - step_type: Enum (sequential, parallel)
  - approvers: Array[UserReference]
  - approver_role: Enum (user, role, department_head, manager_of_requester)
  - condition: JSON (amount threshold, vendor category, etc.)
  - escalation_hours: Integer (hours before escalation)
  - escalation_target: UserReference
  - reminder_hours: Array[Integer] (reminder intervals)
```

---

## 12. Competitive Summary

| Feature | Xero | QBO Advanced | Sage Intacct | **Recommended Design** |
|---------|------|-------------|--------------|----------------------|
| Invoice lifecycle | Basic | Basic | Strong | **Full lifecycle with view tracking** |
| Quote-to-invoice | Yes (limited) | Yes | Yes | **With acceptance + payment** |
| Recurring invoices | Yes | Yes | Yes | **Templates + AutoPay + schedules** |
| Bill data extraction | Basic (OCR) | Basic | AI-powered (2026 R1) | **LLM-based, 94-97% accuracy** |
| Approval workflow | Single-step only | Multi-level (one at a time) | Multi-level, configurable | **Multi-step, conditional, parallel** |
| Delegation/OOO | No | No | Yes | **Full delegation + calendar sync** |
| Payment collection | Stripe, GoCardless | QuickBooks Payments | Sage Vendor Payments | **Stripe + GoCardless + PayPal** |
| Apple/Google Pay | Via Stripe | Limited | Limited | **Full Stripe integration** |
| Payment runs | Basic | Basic | Via add-on | **Full workflow with fraud prevention** |
| Credit notes | Good | Good | Good | **Full workflow with auto-linking** |
| Dunning system | Basic reminders | Basic | Limited | **7-stage automated dunning** |
| Document attachment | File library | Receipt capture | Good | **File library + OCR + auto-match** |
| Multi-currency | Yes | Yes | Yes | **Full multi-currency with auto-FX** |

---

## 13. Implementation Recommendations

### Phase 1: Core Invoice-to-Cash (MVP)
1. Invoice lifecycle (Draft -> Sent -> Paid)
2. Basic quote-to-invoice conversion
3. Stripe + GoCardless payment collection
4. Simple email reminders (due date + overdue)
5. Document attachment to transactions

### Phase 2: AR Automation
6. Recurring invoice templates with scheduling
7. Payment schedules (installments)
8. Full dunning system (7-stage escalation)
9. Credit notes and refunds
10. Quote acceptance with digital signature

### Phase 3: AP Automation
11. Bill receipt capture (email, upload, scan)
12. LLM-based data extraction (94%+ accuracy)
13. Multi-step approval workflows
14. Payment runs with authorization
15. Full document management with OCR search

### Critical Success Factors
- **Silent failure prevention**: All extraction and automation processes must have validation checkpoints and human review queues for low-confidence items [^3^]
- **Audit trail completeness**: Every status change, approval action, and payment event must be logged immutably
- **Separation of duties**: Invoice entry, approval, and payment authorization must be separate roles
- **Webhook reliability**: Payment webhooks from Stripe/GoCardless must be idempotent with proper retry logic
- **Data privacy**: Financial documents must be encrypted at rest and in transit; implement proper access controls

---

## References

[^3^] OpenClaw Business Use Cases - accounting intake silent failure risk. https://www.codebridge.tech/articles/openclaw-case-studies-for-business-workflows-that-show-where-autonomous-ai-creates-value-and-where-enterprises-need-guardrails

[^55^] Invoice Information Extraction: Methods and Performance Evaluation - LlamaExtractor 94% accuracy. https://arxiv.org/html/2510.15727v1

[^221^] Multi-Step Invoice Approval Workflow from Email to QuickBooks. https://www.theautomationdetective.com/cases/case-11-multi-step-invoice-approval-workflow-from-email-to-quickbooks

[^222^] How Invoice Approval Workflows Work in QuickBooks. https://ramp.com/blog/quickbooks-approval-workflow

[^223^] Sage Intacct AP Automation capabilities and gaps. https://www.corpay.com/resources/blog/sage-intacct-ap-automation

[^224^] Multi-Level Bill Approvals in QuickBooks Online Advanced (with Exceptions). https://peopleops.solutions/2025/10/24/multi-level-bill-approvals-in-quickbooks-online-advanced-with-exceptions/

[^225^] GoCardless Review - Direct Debit for UK businesses. https://www.comparecardfees.co.uk/payment-providers/gocardless/

[^226^] Stripe vs GoCardless 2025 comparison. https://www.airwallex.com/au/blog/comparison-stripe-vs-go-cardless

[^261^] Invoice Lifecycle Status definition. https://www.hyperbots.com/glossary/invoice-lifecycle-status

[^262^] Reducto OCR + Schema Validation & LLM Fix-Ups. https://www.typedef.ai/resources/pair-reducto-ocr-schema-validation-llm-fix-ups-typedef

[^263^] OCR vs LLM: Automated Invoice Scanning - 97% accuracy. https://www.raftlabs.com/blog/ocr-vs-llm-how-we-built-automated-invoice-scanning

[^264^] Sanka invoice object lifecycle protection. https://sanka.com/docs/invoice-object/

[^265^] Multi-Currency AP Automation - payment runs. https://hedgeflows.com/platform/payments/

[^266^] Lifecycle of a Payment Request. https://support.opensolar.com/hc/en-us/articles/9878903320463-Lifecycle-of-a-CashFlow-Invoice

[^267^] OpenMeter Invoice Lifecycle. https://openmeter.io/docs/billing/invoicing/invoice-lifecycle

[^268^] PayPal Invoice lifecycle and status flow. https://docs.paypal.ai/growth/grow-business/invoicing/lifecycle

[^269^] Building Reliable Invoice Extraction Prompts. https://thomas-wiegold.com/blog/building-reliable-invoice-extraction-prompts/

[^271^] How to Choose the Right Vendor Invoice Management System. https://www.emburse.com/resources/how-to-choose-vendor-invoice-management-system

[^272^] Dunning software for B2B collections. https://www.paraglide.ai/blog/dunning-software-for-b2b-how-to-speed-up-collections-in-2026

[^273^] Ultimate Guide to Dunning Management. https://www.highradius.com/resources/Blog/guide-to-dunning-management/

[^274^] Apple Pay / Google Pay implementation guide. https://docs.vrio.com/docs/stripe-google-apple-pay

[^275^] The Dunning Process: How It Works and When to Escalate. https://www.creditpulse.com/blog/dunning-process-guide

[^276^] Dunning Letters: Practical Guide. https://www.resolutai.com/blog/what-is-dunning-letter

[^277^] What is Dunning? Definition + Examples. https://www.transformance.ai/glossary/dunning

[^278^] Xero Quotes - Add payment link feature request. https://productideas.xero.com/forums/967115-invoices-quotes/suggestions/45559804-quotes-add-payment-link

[^279^] Odoo Credit Notes and Refunds documentation. https://www.odoo.com/documentation/19.0/applications/finance/accounting/customer_invoices/credit_notes.html

[^281^] Xero - How to convert accepted quote to invoice. https://www.youtube.com/watch?v=2Va4uS4536s

[^283^] ApprovalMax - Approval Automation platform. https://ginto.asia/platform-and-solutions/approvalmax/

[^338^] Banana Accounting - Add links to digital documents. https://www.banana.ch/doc/en/node/3352

[^340^] Patriot Software - Managing Receipts and Documents. https://www.patriotsoftware.com/accounting/training/help/managing-your-receipts-and-documents/

[^341^] Stripe homepage - financial infrastructure. https://stripe.com/en-hk

[^342^] Codat - Upload receipts as attachments. https://docs.codat.io/expenses/sync-process/uploading-receipts

[^343^] freee and Money Forward document management review. https://cpasayu.com/en/2025/07/08/cloud-accounting-review-document-attachment-and-receipt-management-in-freee-and-money-forward/

[^344^] Wave - Refund a customer payment. https://support.waveapps.com/hc/en-us/articles/115004056523-Refund-a-customer-payment

[^345^] Wafeq - Writing off an invoice. https://www.wafeq.com/en/wafeq-help/invoicing-and-receipts/writing-off-an-invoice

[^347^] Wave - Write off an invoice. https://support.waveapps.com/hc/en-us/articles/115000031243-Write-off-an-invoice

[^349^] FreshBooks - How to create a recurring template. https://support.freshbooks.com/hc/en-us/articles/222843308-How-do-I-create-a-recurring-template

[^350^] FreshBooks - How do recurring payments work. https://support.freshbooks.com/hc/en-us/articles/115003957327-How-do-recurring-payments-work

[^352^] Wave Online Accounting Credit Notes workaround. https://cloud-book.co.uk/wave/wave-online-accounting-credit-notes/

[^353^] FreshBooks - Payment schedules. https://support.freshbooks.com/hc/en-us/articles/115013879027-What-are-payment-schedules

[^355^] Odoo Credit Notes and Refunds. https://www.odoo.com/documentation/19.0/applications/finance/accounting/customer_invoices/credit_notes.html

[^357^] Wave - Apply a customer credit to an invoice. https://support.waveapps.com/hc/en-us/articles/33882324213524-Apply-a-customer-credit-to-an-invoice

[^358^] Stripe API Reference - Create an invoice. https://docs.stripe.com/api/invoices/create

[^359^] Stripe API Reference - Invoices. https://docs.stripe.com/api/invoices

[^360^] Automating Invoice Generation and Sending with Stripe. https://userjot.com/blog/automating-invoice-generation-sending-stripe

[^362^] Email Invoices or Documents Directly To Xero. https://www.dolmanbateman.com.au/blog/new-xero-feature-email-invoices-or-documents-directly-to-xero

[^363^] Stripe - Send customer emails. https://docs.stripe.com/invoicing/send-email

[^365^] Stripe Invoicing - Create and Send Invoices Online. https://stripe.com/invoicing

[^368^] Stack Overflow - How to send receipt for invoice via Stripe API. https://stackoverflow.com/questions/72375499/how-to-send-receipt-for-invoice-via-stripe-api
