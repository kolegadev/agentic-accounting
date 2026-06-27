# Dimension 10: Document Understanding & Data Extraction

## Executive Summary

This document designs a complete document understanding system for processing financial documents — invoices, receipts, bank statements, purchase orders, and expense claims. The system adopts a **hybrid LLM+OCR multi-agent pipeline** with human-in-the-loop validation, achieving 97-98.5% automation rates while maintaining 98.5% document-level accuracy [^498^][^525^]. The architecture addresses silent failure risks through per-field confidence scoring, mathematical cross-validation, and structured exception handling. A novel Prompt Fine Tuning with Feedback Inheritance (PFTFI) mechanism enables continuous improvement without model retraining [^498^], while local-first processing options ensure GDPR compliance and data sovereignty [^489^][^526^].

---

## Table of Contents

1. [Document Ingestion Layer](#1-document-ingestion-layer)
2. [Document Classification](#2-document-classification)
3. [Extraction Pipeline Architecture](#3-extraction-pipeline-architecture)
4. [Invoice Field Extraction Schema](#4-invoice-field-extraction-schema)
5. [Receipt Field Extraction Schema](#5-receipt-field-extraction-schema)
6. [Bank Statement Field Extraction](#6-bank-statement-field-extraction)
7. [Validation Layer](#7-validation-layer)
8. [Exception Handling & Human Review](#8-exception-handling--human-review)
9. [Learning Loop & Continuous Improvement](#9-learning-loop--continuous-improvement)
10. [Privacy & Compliance](#10-privacy--compliance)

---

## 1. Document Ingestion Layer

### 1.1 Overview

The ingestion layer provides multiple entry points for documents to enter the processing pipeline, ensuring that financial documents are captured regardless of source or format. The system supports **email polling, upload APIs, cloud storage webhooks, and mobile capture** — mirroring the multi-channel approach used by OpenClaw for document processing [^490^][^489^].

### 1.2 Ingestion Channels

#### 1.2.1 Email Polling

The system monitors dedicated accounting email inboxes (e.g., `accounting@company.com`, `invoices@company.com`, `receipts@company.com`) via webhook triggers or scheduled polling.

**Implementation Pattern (OpenClaw-style)** [^490^]:
```javascript
// Webhook-based email trigger
await client.webhooks.create({
  url: "https://doc-processing.company.com/invoice-webhook",
  eventTypes: ["message.received"],
  inboxIds: [accountingInbox.inboxId]
});

async function processInvoiceEmail(message) {
  const invoice = message.attachments?.find(a => 
    a.filename?.endsWith('.pdf') || 
    a.filename?.match(/\.(jpg|jpeg|png|tiff)$/i)
  );
  if (!invoice) return;
  
  // Download and queue for processing
  const { downloadUrl } = await client.inboxes.messages.getAttachment(
    message.inboxId, message.messageId, invoice.attachmentId
  );
  await queueForProcessing({
    source: 'email',
    receivedAt: new Date().toISOString(),
    sender: message.from,
    filename: invoice.filename,
    downloadUrl,
    messageId: message.messageId,
    notes: message.subject
  });
}
```

**Key Features:**
- **Webhook-triggered processing**: Real-time ingestion instead of batch polling delays [^490^]
- **Multi-format support**: PDF, PNG, JPEG, TIFF attachments
- **Sender metadata capture**: Preserves sender identity and timestamps for audit trails
- **Automatic forwarding detection**: Flags forwarded emails to prevent duplicate processing
- **Reply-thread deduplication**: Links related messages to prevent processing the same invoice multiple times

#### 1.2.2 Upload API

RESTful API endpoints support direct document uploads from internal systems, vendor portals, and partner integrations.

```python
POST /api/v1/documents/upload
Content-Type: multipart/form-data

{
  "file": <binary>,
  "document_type": "invoice" | "receipt" | "statement" | "unknown",
  "source": "vendor_portal" | "internal" | "mobile_app" | "api",
  "metadata": {
    "vendor_id": "optional",
    "purchase_order": "optional",
    "submitted_by": "user_id",
    "department": "engineering" | "sales" | "marketing"
  }
}

Response: {
  "document_id": "doc_123456",
  "status": "queued",
  "estimated_processing_time": "30s",
  "webhook_url": "https://company.com/webhooks/doc_123456"
}
```

**Upload API Features:**
- **Chunked upload support**: Handles large PDF files (up to 50MB)
- **Batch upload**: Accept multiple documents in a single request
- **Pre-upload validation**: Check file type, size, and malware before queuing
- **Idempotency keys**: Prevent duplicate processing of the same upload
- **Async webhook callbacks**: Notify calling systems when processing completes

#### 1.2.3 Cloud Storage Webhooks

Integration with cloud storage providers enables automatic processing when documents are uploaded to designated folders.

**Supported Providers:**
- **Google Drive**: Watch folder for new PDFs, trigger processing via webhook
- **Dropbox**: Webhook notifications for file additions
- **AWS S3**: Event notifications (S3 EventBridge) on object creation
- **Azure Blob Storage**: Event Grid subscriptions for blob creation events
- **SharePoint/OneDrive**: Microsoft Graph change notifications

**Processing Pattern:**
```python
# Cloud storage watcher pattern (OpenClaw cron-based) [^339^]
# Runs at configurable intervals (e.g., every 15 minutes)

async def scan_cloud_storage():
    new_files = await drive_folder.list_files(
        modified_since=last_scan_timestamp
    )
    for file in new_files:
        if is_supported_format(file):
            content = await file.download()
            await queueForProcessing({
                source: 'cloud_storage',
                provider: 'google_drive',
                file_id: file.id,
                filename: file.name,
                receivedAt: file.createdTime,
                content: content
            })
    last_scan_timestamp = now()
```

#### 1.2.4 Mobile Capture

Native mobile SDKs (iOS/Android) enable employees to capture receipts and invoices via smartphone cameras, with automatic preprocessing before transmission.

**Mobile Capture Pipeline:**
1. **Camera capture**: High-resolution photo (minimum 300 DPI equivalent) [^487^][^566^]
2. **Real-time quality assessment**: Check lighting, sharpness, orientation, and completeness
3. **Auto-enhancement**: Apply deskewing, contrast enhancement, and noise reduction
4. **Edge detection**: Automatic receipt boundary detection and cropping
5. **Local preprocessing**: Compress and optimize before upload
6. **Upload with metadata**: Send to processing API with GPS location, timestamp, and user context

**Mobile Best Practices** [^566^]:
- Prompt users to scan within 24 hours before thermal paper fades
- Use natural daylight or bright, diffused artificial light to prevent shadows
- Ensure entire receipt is captured including all edges
- Implement consistent naming: `YYYY-MM-DD_Vendor_Amount` format
- Store in at least two locations (primary cloud + backup)

### 1.3 Preprocessing Pipeline

All documents undergo adaptive preprocessing before extraction to maximize OCR accuracy [^486^]:

```
Document Input (PDF/Image)
    |
    v
[Format Detection] ──→ Image vs Text-based PDF vs Scanned
    |
    v
[Adaptive Preprocessing Module]
    ├── Noise reduction (background artifact removal)
    ├── Skew correction (Hough Transform alignment)
    ├── Background removal (extract text from complex backgrounds)
    ├── Resolution normalization (standardize to 300 DPI)
    ├── Contrast stretching and binarization
    └── Dynamic method selection based on quality assessment
    |
    v
[Output: Optimized Document for OCR/LLM Processing]
```

**Key Preprocessing Techniques** [^486^][^71^]:

| Technique | Purpose | Impact |
|-----------|---------|--------|
| Noise Reduction | Eliminate scan artifacts, speckles | +5-10% OCR accuracy |
| Skew Correction | Fix document orientation | Critical for table alignment |
| Binarization | Maximize text/background contrast | Improves character recognition |
| Resolution Norm | Standardize DPI across inputs | Consistent downstream processing |
| Contrast Stretching | Enhance faded/thermal paper text | Essential for receipts |
| Background Removal | Isolate text from complex backgrounds | Reduces OCR errors |

### 1.4 Document Store

Raw documents are stored immutably with full audit trail:

```python
{
  "document_id": "doc_abc123",
  "ingestion_metadata": {
    "source": "email" | "upload" | "webhook" | "mobile",
    "original_filename": "invoice_acme_2024.pdf",
    "file_size_bytes": 245760,
    "mime_type": "application/pdf",
    "received_at": "2024-01-15T09:23:00Z",
    "sender_email": "vendor@acme.com",
    "ip_address": "203.0.113.1",
    "checksum_sha256": "abc123..."
  },
  "storage": {
    "s3_key": "raw/2024/01/15/doc_abc123.pdf",
    "retention_class": "financial_7_years",
    "encryption": "AES-256-GCM"
  },
  "processing_history": [
    {"stage": "ingested", "timestamp": "2024-01-15T09:23:01Z"},
    {"stage": "preprocessed", "timestamp": "2024-01-15T09:23:05Z"},
    {"stage": "classified", "timestamp": "2024-01-15T09:23:10Z"},
    {"stage": "extracted", "timestamp": "2024-01-15T09:23:30Z"},
    {"stage": "validated", "timestamp": "2024-01-15T09:23:35Z"}
  ]
}
```

---

## 2. Document Classification

### 2.1 Overview

Document classification is the first AI processing step, routing incoming documents to the appropriate extraction pipeline. The system uses a **multi-tier classification approach** combining CNN-based visual classification with LLM-based semantic verification, achieving 95.3% classification accuracy on document headers [^525^].

### 2.2 Classification Architecture

Inspired by the MADP (Multi-Agent Document Processing) architecture [^498^][^525^], the classifier uses a **ResNet-18 CNN** pretrained on ImageNet, fine-tuned on document header regions:

```
Incoming Document
    |
    v
[Header Region Extraction] ──→ Top 40% of page (contains logos, doc type indicators)
    |
    v
[ResNet-18 CNN Classifier]
    ├── Frozen: First 3 convolutional blocks (general visual features)
    ├── Fine-tuned: 4th block + classification head
    └── Input: 224×224 pixel header crop
    |
    v
[Primary Classification]
    ├── Invoice (vendor invoice, proforma, credit note)
    ├── Receipt (POS receipt, digital receipt, e-receipt)
    ├── Bank Statement (checking, savings, credit card)
    ├── Purchase Order
    ├── Expense Claim (employee reimbursement form)
    └── Unknown / Unsupported
    |
    v
[LLM Semantic Verification] ──→ Cross-validate CNN prediction with text content
    |
    v
[Final Classification + Confidence Score]
```

### 2.3 Classification Categories

| Category | Subtypes | Visual Indicators | Confidence Threshold |
|----------|----------|-------------------|---------------------|
| **Invoice** | Standard, Proforma, Credit Note, Debit Note, Utility Bill, Freight | "INVOICE" header, invoice number, vendor logo, payment terms | 0.90 |
| **Receipt** | POS, Digital, E-receipt, Restaurant, Retail, Gas Station | "RECEIPT" header, merchant name, itemized list, "THANK YOU" | 0.85 |
| **Bank Statement** | Checking, Savings, Credit Card, Investment | Bank logo, statement period, transaction table, opening/closing balance | 0.90 |
| **Purchase Order** | Standard, Blanket, Emergency | "PURCHASE ORDER" header, PO number, ship-to/bill-to addresses | 0.90 |
| **Expense Claim** | Reimbursement, Mileage, Per Diem | Employee name, expense categories, approval signatures | 0.85 |

### 2.4 Multi-Page Document Handling

The **Splitter Agent** handles multi-page and batch documents [^525^]:

- **Page-level segmentation**: Analyzes page breaks, headers, and visual features to identify document boundaries within batch files
- **Context isolation**: Prevents information leakage between documents in a batch
- **Continuation detection**: Identifies when tables span multiple pages (via "continued" labels or structural analysis)

### 2.5 Azure Document Intelligence Alternative

For teams using cloud services, Azure Document Intelligence provides **built-in document classification** [^519^][^521^]:
- Prebuilt models for invoice, receipt, identity document, business card
- Custom classification models trainable on proprietary document types
- Automatic document splitting for multi-type files
- Custom generative extraction for novel field types

---

## 3. Extraction Pipeline Architecture

### 3.1 Hybrid LLM+OCR Design

The extraction pipeline follows the **MADP multi-agent architecture** [^498^][^525^] and the hybrid OCR-LLM frameworks documented in recent research [^486^][^494^]. The key principle: structural awareness from OCR + semantic understanding from LLMs = superior extraction accuracy.

```
Classified Document
    |
    v
[Parser Agent - Docling-based]
    ├── Layout analysis (identify text regions, tables, figures)
    ├── Reading order reconstruction
    ├── Table structure recognition (TableFormer)
    ├── OCR (if needed - EasyOCR/Tesseract)
    └── Output: Structured Markdown/JSON representation
    |
    v
[Extraction Agent - LLM-based]
    ├── Schema-prompted field extraction
    ├── Semantic understanding of field relationships
    ├── Multi-page context carry-forward
    └── Output: Structured JSON with extracted fields
    |
    v
[Validator Agent]
    ├── Mathematical validation (subtotal + tax = total)
    ├── Cross-field consistency checks
    ├── Confidence scoring per field
    └── Output: Validated extraction or exception flag
```

### 3.2 Parser Agent: Docling for Structure

The **Parser Agent** uses **Docling**, IBM Research's open-source document processing toolkit [^526^][^529^][^531^], to convert documents into structured representations:

**Docling Capabilities** [^526^][^530^]:
- Parses PDF, DOCX, PPTX, XLSX, HTML, images
- Exports to Markdown, JSON, HTML, Doctags
- Layout analysis via DocLayNet-trained RT-DETR model
- Table structure recognition via TableFormer (vision-transformer)
- OCR through EasyOCR integration
- **Reduces token count by 35%** compared to raw OCR output [^525^]

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("/path/to/invoice.pdf")
structured_markdown = result.document.export_to_markdown()

# The structured markdown preserves:
# - Table structure with headers and cell alignment
# - Reading order for multi-column layouts
# - Section hierarchy (headings, paragraphs, lists)
# - Figure and caption grouping
```

**Parser Agent Ablation Results** [^525^]:
- The Parser Agent alone contributes **+17.5 percentage points** improvement in document-level accuracy
- Structured markdown output is optimized for downstream LLM consumption
- Handles multi-column layouts, nested tables, and borderless tables

### 3.3 Extraction Agent: LLM with Schema Prompting

The Extraction Agent uses **multimodal LLMs** (GPT-4o, Claude, Gemini, Mistral-Small-3.2) to extract fields from the structured document representation [^499^][^500^][^506^].

**Key Design Principles:**

1. **Image-based processing for scanned documents**: Convert PDF pages to 300 DPI JPGs — this forces the LLM to perform visual OCR rather than reading potentially erroneous text metadata, improving comprehension [^487^]

2. **Sequential context for multi-page documents**: Each page receives the previous page's extracted data as context, enabling state carry-forward across page boundaries [^487^]

3. **Structured outputs with Pydantic validation**: Define extraction schemas as Pydantic models for runtime validation [^500^]

4. **Temperature 0.0 for extraction tasks**: Essential for deterministic, consistent outputs [^496^]

**Extraction Pattern:**
```python
from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal

class LineItem(BaseModel):
    description: str = Field(description="Item description")
    quantity: Optional[Decimal] = Field(description="Quantity purchased")
    unit_price: Optional[Decimal] = Field(description="Price per unit")
    line_total: Optional[Decimal] = Field(description="Total for this line")

class InvoiceExtraction(BaseModel):
    vendor_name: Optional[str] = Field(description="Name of the invoicing entity")
    vendor_tax_id: Optional[str] = Field(description="Vendor VAT/GST/Tax ID")
    invoice_number: Optional[str] = Field(description="Unique invoice identifier")
    invoice_date: Optional[str] = Field(description="Date of issue (ISO 8601)")
    due_date: Optional[str] = Field(description="Payment due date (ISO 8601)")
    currency: Optional[str] = Field(description="ISO 4217 currency code")
    subtotal: Optional[Decimal] = Field(description="Sum before tax")
    tax_amount: Optional[Decimal] = Field(description="Total tax/VAT amount")
    tax_rate: Optional[Decimal] = Field(description="Tax rate percentage")
    total_amount: Optional[Decimal] = Field(description="Total amount payable")
    line_items: List[LineItem] = Field(default_factory=list)
    payment_terms: Optional[str] = Field(description="e.g., Net 30")
    purchase_order: Optional[str] = Field(description="PO reference number")
    bank_account: Optional[str] = Field(description="Vendor bank account for payment")
    
class ExtractionResult(BaseModel):
    document_id: str
    document_type: str
    extraction: InvoiceExtraction
    confidence_scores: dict  # Per-field confidence
    processing_metadata: dict
```

### 3.4 LLM Backend Benchmarking

The MADP paper benchmarks multiple LLM backends for document extraction [^525^]:

| Model | F1 Score | Precision | Recall | Latency (s/doc) | Best For |
|-------|----------|-----------|--------|-----------------|----------|
| **Mistral-Small-3.2** | 92.9% | 92.4% | 98.2% | ~4.2 | Balanced accuracy/speed |
| **DeepSeek-OCR** | 89.5% | 96.8% | 84.2% | ~3.63 | High precision requirements |
| **Granite-Docling** | 88.2% | 91.1% | 86.3% | ~5.1 | IBM ecosystem integration |
| GPT-4o | 91.5% | 93.0% | 90.2% | ~3.8 | Complex multi-page documents |
| Claude 3.5 Sonnet | 90.8% | 92.7% | 89.1% | ~4.5 | High reasoning requirements |

### 3.5 Vision-First vs Text-First Processing

The pipeline dynamically selects the processing path based on document characteristics [^499^][^501^]:

| Document Type | Processing Path | Rationale |
|---------------|----------------|-----------|
| Born-digital PDF (text layer present) | Text-first: Extract structured text via Docling, then LLM extraction | Faster, cheaper, 92%+ accuracy |
| Scanned PDF / Image | Vision-first: Convert to 300 DPI image, multimodal LLM extraction | Layout understanding, 92.71% vs 64.03% accuracy advantage [^499^] |
| Mixed (text + scanned pages) | Hybrid: Text extraction for text pages, vision for scanned pages | Optimal cost/accuracy balance |

### 3.6 OCR Engine Selection

For scanned documents requiring OCR, the system supports multiple engines with automatic selection [^71^][^569^]:

| OCR Engine | Best For | CER | Speed | Cost |
|------------|----------|-----|-------|------|
| **Mistral OCR 3** | Complex layouts, tables, handwriting | 2.1% | Fastest | $1-2/1,000 pages [^577^] |
| **DeepSeek OCR** | Handwriting, diverse scripts | 2.3% | Fast | Self-hosted |
| **Qwen3-VL** | Multilingual, layout understanding | 2.5% | Moderate | Self-hosted |
| **Tesseract** | Simple text, local processing | 4.5% | Very fast | Free (open source) |
| **Google OCR API** | General purpose, high accuracy | 3.2% | Fast | Pay-per-use |
| **PaddleOCR** | Multilingual, high speed | 3.8% | Fastest | Free (open source) |

### 3.7 Cost Model

Based on OpenClaw operational analysis [^339^]:

| Pipeline Stage | Model | Tokens/Doc | Cost/Doc |
|----------------|-------|-----------|----------|
| Email scanning + extraction | Claude Sonnet | 30K-50K | $0.01-0.02 |
| PDF extraction (text-based) | Claude Sonnet | 5K-10K | $0.002-0.004 |
| PDF extraction (vision/scanned) | Claude Opus | 20K-40K | $0.01-0.02 |
| Field mapping + validation | Claude Haiku | 10K-15K | $0.0004-0.0006 |
| Validation pass | Claude Haiku | 5K-10K | $0.0002-0.0004 |

**Total per document (text-based): ~$0.015**
**Total per document (vision/scanned): ~$0.03-0.05**

---

## 4. Invoice Field Extraction Schema

### 4.1 Complete Invoice Schema

Based on Azure AI Document Intelligence prebuilt invoice model [^517^][^525^], GPT-4o vision extraction patterns [^499^][^502^], and production invoice processing best practices [^500^]:

```json
{
  "$schema": "https://schemas.company.com/invoice-extraction/v2",
  "document_type": "invoice",
  "extraction_version": "2.0",
  
  "vendor": {
    "name": "Acme Software Inc",
    "address": "123 Business Ave, Suite 100, San Francisco, CA 94105",
    "tax_id": "12-3456789",
    "email": "billing@acmesoftware.com",
    "phone": "+1 (555) 123-4567",
    "bank_account": "****1234",
    "bank_routing": "021000021"
  },
  
  "customer": {
    "name": "Client Company LLC",
    "address": "456 Corporate Blvd, New York, NY 10001",
    "tax_id": "98-7654321",
    "email": "ap@clientcompany.com",
    "account_number": "ACC-2024-001"
  },
  
  "invoice": {
    "number": "INV-2024-0042",
    "date": "2024-01-15",
    "due_date": "2024-02-14",
    "purchase_order": "PO-2024-0187",
    "currency": "USD",
    "language": "en",
    "payment_terms": "Net 30",
    "payment_method": "ACH Transfer"
  },
  
  "line_items": [
    {
      "line_number": 1,
      "description": "Software License - Enterprise Plan",
      "quantity": 10,
      "unit": "seats",
      "unit_price": 99.00,
      "discount_percent": 10,
      "discount_amount": 99.00,
      "tax_rate": 8.875,
      "tax_amount": 79.01,
      "line_total": 969.01
    },
    {
      "line_number": 2,
      "description": "Implementation Services",
      "quantity": 40,
      "unit": "hours",
      "unit_price": 150.00,
      "discount_percent": 0,
      "discount_amount": 0,
      "tax_rate": 8.875,
      "tax_amount": 532.50,
      "line_total": 6532.50
    }
  ],
  
  "totals": {
    "subtotal": 6490.50,
    "discount_total": 99.00,
    "taxable_amount": 6391.50,
    "tax_breakdown": [
      {"rate": 8.875, "label": "Sales Tax", "amount": 611.51}
    ],
    "tax_total": 611.51,
    "shipping": 0,
    "other_charges": 0,
    "total_due": 7003.01,
    "amount_paid": 0,
    "balance_due": 7003.01
  },
  
  "confidence": {
    "vendor_name": 0.98,
    "invoice_number": 0.97,
    "invoice_date": 0.96,
    "due_date": 0.95,
    "total_due": 0.99,
    "line_items": 0.94,
    "tax_amount": 0.93
  }
}
```

### 4.2 Field Extraction Requirements

| Field | Required | Validation Rules | LLM Prompt Strategy |
|-------|----------|-----------------|-------------------|
| **Vendor Name** | Yes | Match against vendor master file | "Extract the company name issuing this invoice" |
| **Invoice Number** | Yes | Unique per vendor; regex pattern match | "Find the invoice/ bill reference number" |
| **Invoice Date** | Yes | Not in future; within last 5 years | "Extract date of issue in YYYY-MM-DD format" |
| **Due Date** | No | After invoice date | "Extract payment due date in YYYY-MM-DD format" |
| **Line Items** | Yes | Qty x Unit Price - Discount = Line Total | "Extract all line items with quantity, price, total" |
| **Subtotal** | Yes | Must equal sum of line totals | "Sum before taxes and discounts" |
| **Tax Amount** | Yes | Break down by rate if multiple | "Total tax/VAT amount; breakdown if available" |
| **Total Amount** | Yes | Subtotal + Tax - Discount = Total | "Total amount due for payment" |
| **Currency** | Yes | ISO 4217 code | "Currency code (USD, EUR, GBP, etc.)" |
| **Purchase Order** | No | Cross-reference with PO system | "Purchase order number if present" |
| **Payment Terms** | No | e.g., Net 30, Due on Receipt | "Payment terms or due date conditions" |

### 4.3 International Tax Handling

The schema handles international tax variations [^567^]:
- **VAT** (EU/UK): Value Added Tax with multiple rate tiers (standard, reduced, zero)
- **GST** (Australia/Canada/India): Goods and Services Tax
- **Sales Tax** (US): State/local rates varying by jurisdiction
- **CGST/SGST/IGST** (India): Central, State, and Integrated GST components
- **Multiple tax rates**: Some invoices apply different rates to different line items

```json
{
  "tax_breakdown": [
    {"rate": 20.0, "label": "VAT Standard", "amount": 200.00, "category": "standard"},
    {"rate": 5.0, "label": "VAT Reduced", "amount": 15.00, "category": "reduced"},
    {"rate": 0.0, "label": "VAT Zero", "amount": 0, "category": "zero"}
  ]
}
```

---

## 5. Receipt Field Extraction Schema

### 5.1 Complete Receipt Schema

Receipts are structurally different from invoices — no standardized layout, thermal paper degradation, and diverse merchant formats [^523^]. The extraction schema accounts for these challenges:

```json
{
  "$schema": "https://schemas.company.com/receipt-extraction/v2",
  "document_type": "receipt",
  
  "merchant": {
    "name": "Starbucks Coffee",
    "address": "100 Market St, San Francisco, CA 94105",
    "phone": "(555) 987-6543",
    "store_id": "SB-1042",
    "tax_id": "12-3456789"
  },
  
  "transaction": {
    "date": "2024-01-15",
    "time": "14:32:00",
    "timezone": "America/Los_Angeles",
    "receipt_number": "TRX-20240115-003421",
    "transaction_id": "1234567890",
    "cashier": "John D",
    "register": "03"
  },
  
  "items": [
    {
      "description": "Grande Latte",
      "quantity": 1,
      "unit_price": 4.95,
      "amount": 4.95,
      "category_suggestion": "meals"
    },
    {
      "description": "Croissant",
      "quantity": 2,
      "unit_price": 3.25,
      "amount": 6.50,
      "category_suggestion": "meals"
    }
  ],
  
  "totals": {
    "subtotal": 11.45,
    "tax_rate": 8.875,
    "tax_amount": 1.02,
    "tip_amount": 2.50,
    "total": 14.97
  },
  
  "payment": {
    "method": "credit_card",
    "card_last_four": "4242",
    "card_type": "Visa",
    "approval_code": "123456"
  },
  
  "expense": {
    "category_suggestion": "meals_entertainment",
    "deductible": true,
    "requires_mileage": false,
    "requires_guest_info": false
  },
  
  "confidence": {
    "merchant_name": 0.97,
    "transaction_date": 0.98,
    "total": 0.99,
    "items": 0.85
  }
}
```

### 5.2 Receipt-Specific Extraction Challenges

Receipts present unique challenges compared to invoices [^523^]:

| Challenge | Mitigation Strategy |
|-----------|-------------------|
| **No standardized layout** | LLM semantic understanding instead of template matching |
| **Thermal paper degradation** | Image enhancement preprocessing (contrast stretching) |
| **Handwritten tips/notes** | Dedicated handwriting OCR path for tip fields |
| **Phone camera capture** | Auto-deskew, perspective correction, glare removal |
| **Abbreviated item descriptions** | LLM context expansion + merchant-specific dictionaries |
| **Multi-language receipts** | Language detection + multilingual model support |
| **Faded/lost text** | Confidence scoring → flag for manual entry |

### 5.3 Expense Category Suggestions

The system automatically suggests expense categories based on merchant type and item descriptions [^490^]:

| Category | Merchant Patterns | Items |
|----------|------------------|-------|
| **meals_entertainment** | Restaurants, cafes, catering | Food, beverages, tips |
| **travel_transportation** | Airlines, Uber, taxi, parking | Flights, rides, parking fees |
| **office_supplies** | Staples, Amazon Business, Office Depot | Paper, ink, equipment |
| **software_tech** | SaaS vendors, cloud providers | Subscriptions, licenses |
| **telecommunications** | Phone, internet providers | Monthly service bills |
| **professional_services** | Consulting, legal, accounting | Service fees, retainers |
| **fuel** | Gas stations | Gallons, fuel grade |
| **accommodation** | Hotels, Airbnb | Room charges, taxes |

### 5.4 Receipt Types

The system recognizes distinct receipt types requiring different handling [^523^]:

| Receipt Type | Key Fields | Special Handling |
|-------------|------------|-----------------|
| **Retail** | Items, quantities, prices, SKU | Product categorization |
| **Restaurant** | Items, subtotal, tip, total | Tip extraction, gratuity validation |
| **Gas Station** | Gallons, price/gal, pump number | Mileage tracking integration |
| **Hotel Folio** | Room charges, taxes, fees, dates | Multi-night breakdown |
| **Digital/E-receipt** | Clean text, structured data | Direct parsing, minimal OCR |
| **Utility Bill** | Usage, rates, period, account | Consumption tracking |

---

## 6. Bank Statement Field Extraction

### 6.1 Bank Statement Schema

Bank statements require specialized handling for transaction tables, running balances, and multi-page layouts:

```json
{
  "$schema": "https://schemas.company.com/bank-statement-extraction/v2",
  "document_type": "bank_statement",
  
  "account": {
    "account_number": "****1234",
    "account_type": "checking",
    "bank_name": "Chase Bank",
    "routing_number": "021000021",
    "currency": "USD"
  },
  
  "statement_period": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "opening_balance": 15234.56,
    "closing_balance": 18456.78
  },
  
  "summary": {
    "deposits_count": 12,
    "deposits_total": 8450.00,
    "withdrawals_count": 28,
    "withdrawals_total": 5227.78,
    "fees_count": 2,
    "fees_total": 35.00,
    "interest_earned": 95.00
  },
  
  "transactions": [
    {
      "transaction_id": "txn_001",
      "date": "2024-01-02",
      "posting_date": "2024-01-03",
      "description": "ACME SOFTWARE INC - SUBSCRIPTION",
      "original_description": "ACH DEBIT ACME SOFTWARE INC",
      "amount": -999.00,
      "balance": 14235.56,
      "transaction_type": "debit",
      "category": "software",
      "reference_number": "ACH-123456789",
      "check_number": null,
      "confidence": 0.95
    },
    {
      "transaction_id": "txn_002",
      "date": "2024-01-05",
      "posting_date": "2024-01-05",
      "description": "DEPOSIT - PAYROLL",
      "original_description": "ACH CREDIT PAYROLL COMPANY LLC",
      "amount": 5000.00,
      "balance": 19235.56,
      "transaction_type": "credit",
      "category": "payroll",
      "reference_number": "DD-987654321",
      "check_number": null,
      "confidence": 0.97
    }
  ],
  
  "confidence": {
    "account_number": 0.99,
    "opening_balance": 0.98,
    "closing_balance": 0.98,
    "transaction_count": 0.95,
    "transactions": 0.92
  }
}
```

### 6.2 Bank Statement Extraction Challenges

| Challenge | Solution |
|-----------|----------|
| **Multi-page transaction tables** | Sequential context carry-forward [^487^]; detect continuation headers |
| **Running balance validation** | Verify: Previous Balance + Credits - Debits = Current Balance |
| **Abbreviated descriptions** | LLM semantic expansion using merchant database |
| **Multiple accounts per statement** | Splitter Agent separates account sections [^525^] |
| **Credit vs debit ambiguity** | Context-aware sign detection; some banks use positive/negative, others CR/DR |
| **Check images appended** | Separate processing path for check deposits |
| **PDF text layer issues** | Docling layout model reconstructs table structure from visual cues [^526^] |

### 6.3 Transaction Categorization

The system categorizes bank transactions using a combination of:
1. **Merchant name matching**: Match against known vendor database
2. **Description keyword analysis**: "PAYROLL", "SUBSCRIPTION", "TRANSFER"
3. **Amount pattern recognition**: Regular amounts suggest recurring subscriptions
4. **Historical categorization**: Learn from user corrections on previous similar transactions

---

## 7. Validation Layer

### 7.1 Overview

The validation layer is **the most critical component** for preventing silent failures. Research shows that without systematic validation, extraction errors propagate downstream causing payment delays, inaccurate financial reports, and compliance issues [^567^][^568^][^578^].

### 7.2 Mathematical Validation

**Primary Cross-Checks** [^567^][^568^][^573^]:

```python
class InvoiceValidator:
    def validate(self, extraction: InvoiceExtraction) -> ValidationResult:
        errors = []
        warnings = []
        
        # Check 1: Line items sum to subtotal
        line_sum = sum(item.line_total for item in extraction.line_items)
        if abs(line_sum - extraction.subtotal) > 0.01:
            errors.append(ValidationError(
                field="subtotal",
                expected=line_sum,
                actual=extraction.subtotal,
                message=f"Line items sum ({line_sum}) != subtotal ({extraction.subtotal})"
            ))
        
        # Check 2: Subtotal + Tax - Discount = Total
        calculated_total = extraction.subtotal + extraction.tax_amount - extraction.discount_total
        tolerance = max(0.01, calculated_total * 0.005)  # 0.5% tolerance
        if abs(calculated_total - extraction.total_amount) > tolerance:
            errors.append(ValidationError(
                field="total_amount",
                expected=calculated_total,
                actual=extraction.total_amount,
                message=f"Subtotal ({extraction.subtotal}) + Tax ({extraction.tax_amount}) - "
                        f"Discount ({extraction.discount_total}) = {calculated_total}, "
                        f"but total is {extraction.total_amount}"
            ))
        
        # Check 3: Per-line validation (quantity * unit_price - discount = line_total)
        for i, item in enumerate(extraction.line_items):
            if item.quantity and item.unit_price and item.line_total:
                expected = (item.quantity * item.unit_price) * (1 - item.discount_percent / 100)
                if abs(expected - item.line_total) > 0.02:
                    warnings.append(ValidationWarning(
                        field=f"line_items[{i}].line_total",
                        message=f"Quantity * Price calculation mismatch: expected {expected}, got {item.line_total}"
                    ))
        
        # Check 4: Invoice date <= Due date
        if extraction.invoice_date > extraction.due_date:
            errors.append(ValidationError(
                field="due_date",
                message="Due date cannot be before invoice date"
            ))
        
        # Check 5: Invoice date not in future
        if extraction.invoice_date > today():
            errors.append(ValidationError(
                field="invoice_date",
                message="Invoice date is in the future"
            ))
        
        # Check 6: Amounts are non-negative
        for field_name in ["subtotal", "tax_amount", "total_amount"]:
            value = getattr(extraction, field_name)
            if value is not None and value < 0:
                errors.append(ValidationError(
                    field=field_name,
                    message=f"{field_name} cannot be negative"
                ))
        
        # Check 7: Vendor exists in master file (warning, not error)
        if not vendor_master.exists(extraction.vendor_name):
            warnings.append(ValidationWarning(
                field="vendor_name",
                message=f"Vendor '{extraction.vendor_name}' not found in master file"
            ))
        
        return ValidationResult(errors=errors, warnings=warnings, is_valid=len(errors) == 0)
```

### 7.3 Receipt Validation Rules

| Check | Rule | Tolerance |
|-------|------|-----------|
| Subtotal | Sum of item amounts = subtotal | +/- $0.01 |
| Tax | Subtotal x Tax Rate = Tax Amount | +/- $0.02 (rounding) |
| Total | Subtotal + Tax + Tip = Total | +/- $0.01 |
| Date | Not in future; within last 90 days | N/A |
| Tip | If present, must be >= 0 and <= 50% of subtotal | N/A |

### 7.4 Bank Statement Validation Rules

| Check | Rule | Tolerance |
|-------|------|-----------|
| Running Balance | Previous Balance + Amount = New Balance | +/- $0.01 |
| Opening Balance | Matches previous statement closing balance | +/- $0.01 |
| Transaction Sum | Sum of debits/credits matches statement summary | +/- $0.01 |
| Closing Balance | Opening + Deposits - Withdrawals = Closing | +/- $0.01 |
| Date Sequence | Transactions in chronological order | N/A |

### 7.5 Duplicate Detection

Duplicate detection operates at multiple layers [^514^][^515^][^522^]:

**Layer 1: Exact Matching (catches 30-40% of duplicates)**
```python
# Exact match on normalized invoice number + vendor + amount
def exact_duplicate_check(invoice):
    normalized_number = normalize_invoice_number(invoice.number)
    return db.query(
        "SELECT * FROM invoices "
        "WHERE normalized_number = ? AND vendor_id = ? AND total_amount = ?",
        normalized_number, invoice.vendor_id, invoice.total_amount
    )
```

**Layer 2: Fuzzy Matching (catches 60-80% of near-duplicates)**
```python
# Multi-dimensional similarity scoring
def fuzzy_duplicate_check(invoice):
    candidates = db.query_recent_invoices(days=90, vendor_id=invoice.vendor_id)
    for candidate in candidates:
        score = similarity_score(
            vendor_match = exact_match(invoice.vendor, candidate.vendor),
            amount_similarity = within_percentage(invoice.total, candidate.total, 0.5),
            date_proximity = within_days(invoice.date, candidate.date, 7),
            number_similarity = fuzzy_string_match(invoice.number, candidate.number, 0.85)
        )
        if score > 0.85:
            flag_potential_duplicate(invoice, candidate, score)
```

**Layer 3: AI-Powered Multi-Dimensional Detection**
- Vendor + amount + date proximity analysis [^514^]
- Line item description and quantity comparison
- Confidence scoring: 95-100% = auto-reject, 85-94% = review required [^514^]
- Pattern recognition for systematic vendor duplication

**Duplicate Detection Accuracy by Method** [^514^]:

| Method | Accuracy | Speed | Best For |
|--------|----------|-------|----------|
| Manual Review | 40-60% | 15-20 min/invoice | <50 invoices/month |
| ERP Exact Match | 50-70% | Instant | Simple duplicates |
| Rule-Based | 70-85% | <1 min/invoice | 50-500/month |
| AI Multi-Dimensional | 95-99% | <5 seconds | 500+/month |
| Hybrid (AI + Human) | 99%+ | <10 seconds | Critical invoices |

### 7.6 Confidence Scoring Per Field

The system assigns **confidence scores to every extracted field** [^579^][^581^][^585^]:

| Field Type | Confidence Source | Threshold for Auto-Approval | Threshold for Human Review |
|------------|------------------|---------------------------|--------------------------|
| Financial totals | LLM logprobs + mathematical validation | >= 0.95 | < 0.95 |
| Invoice number | Pattern match + checksum | >= 0.90 | < 0.90 |
| Dates | Format validation + range check | >= 0.90 | < 0.90 |
| Line items | OCR confidence + math cross-check | >= 0.85 | < 0.85 |
| Descriptions | LLM logprobs only | >= 0.70 | < 0.70 |
| Tax ID | Format validation + checksum | >= 0.95 | < 0.95 |

**Confidence Score Calibration** [^580^]:
- Start with 0.95 threshold for financial fields
- Adjust based on observed accuracy patterns
- Monitor calibration: 90% confidence should mean ~90% accuracy
- Field-specific thresholds: stricter for amounts, looser for descriptions

---

## 8. Exception Handling & Human Review

### 8.1 Exception Types & Routing

Documents are routed to human review based on exception type and severity:

| Exception Type | Trigger | Routing | SLA |
|---------------|---------|---------|-----|
| **Low Confidence** | Any field confidence below threshold | Review queue with flagged fields highlighted | 4 hours |
| **Math Validation Fail** | Subtotal + Tax != Total | Priority review — likely extraction error | 2 hours |
| **Duplicate Detected** | Similarity score > 0.85 | Duplicate investigation queue | 4 hours |
| **Unknown Vendor** | Vendor not in master file | Vendor onboarding + AP review | 24 hours |
| **Unsupported Format** | Unrecognized document structure | Specialist manual entry | 8 hours |
| **Multi-Page Ambiguity** | Document boundary unclear | Splitter review | 4 hours |
| **OCR Quality Low** | Document-level confidence < 0.70 | Request re-scan + manual entry | 8 hours |

### 8.2 Review Queue Design

Based on HITL best practices [^507^][^509^][^510^]:

**Review UI Requirements:**
1. **Side-by-side view**: Original document image next to extracted fields
2. **Field highlighting**: Color-coded confidence indicators (green = high, yellow = medium, red = low)
3. **One-click correction**: Click field → edit → save → next
4. **Keyboard shortcuts**: Navigate between fields without mouse
5. **Document zoom**: Zoom in on specific regions for verification
6. **Audit trail**: Log who reviewed, what was corrected, and when

**Review Queue Prioritization:**
```python
# Priority score = f(amount, exception_severity, vendor_reliability, age)
def calculate_priority(document):
    score = 0
    score += document.total_amount * 0.01  # Higher amount = higher priority
    score += document.exception_severity * 100  # Critical exceptions first
    score += document.hours_in_queue * 10  # Age-based escalation
    score -= document.vendor_reliability_score * 5  # Trusted vendors deprioritized
    return score
```

### 8.3 HITL Workflow

```
Automated Extraction
    |
    v
[Confidence + Validation Check]
    ├── All fields pass + math checks out ──→ Auto-approve ──→ ERP
    ├── Low confidence fields ──→ Human Review Queue
    ├── Validation failure ──→ Priority Review Queue
    └── Duplicate detected ──→ Duplicate Investigation Queue
                                    |
                                    v
                           [Human Reviewer Interface]
                                    |
                                    v
                           [Correct/Approve/Reject]
                                    |
                    ┌───────────────┼───────────────┐
                    v               v               v
                Approved      Corrected      Rejected
                    |               |               |
                    v               v               v
                   ERP       PFTFI Learning     Return to Sender
                               Loop Triggered
```

### 8.4 Review Metrics & SLA Monitoring

| Metric | Target | Measurement |
|--------|--------|-------------|
| Documents auto-approved | 85-90% | No human touch |
| Average review time per document | < 45 seconds | Timer from open to decision |
| Review accuracy | > 99% | Sample audit of reviewed documents |
| Queue depth | < 50 documents | Real-time monitoring |
| Time in queue | < 4 hours | P95 across all exception types |
| Reviewer throughput | > 80 documents/hour | Per FTE |

### 8.5 Silent Failure Prevention

Silent failures — where incorrect data passes through without detection — are the **biggest risk** in document processing [^507^][^510^]. Mitigation strategies:

1. **Confidence scoring on every field**: Uncertainty must be explicit [^581^]
2. **Mathematical validation**: Automated cross-checks catch numeric errors
3. **Statistical anomaly detection**: Flag invoices with unusual amounts, dates, or vendors
4. **Periodic sampling**: Randomly sample 5% of auto-approved documents for audit
5. **Downstream monitoring**: Track payment disputes, vendor complaints as quality signals
6. **Audit trails**: Every extraction decision logged with confidence scores [^509^]

---

## 9. Learning Loop & Continuous Improvement

### 9.1 Prompt Fine Tuning with Feedback Inheritance (PFTFI)

The system implements the **PFTFI mechanism** from the MADP architecture [^498^][^525^] — a novel approach that improves extraction accuracy without retraining underlying models:

**PFTFI Workflow:**
```
Human Reviewer Makes Correction
    |
    v
[PFTFI Agent Captures]
    ├── Original extraction (wrong value)
    ├── Corrected value (human input)
    ├── Document context (vendor, layout, field type)
    └── Error pattern analysis
    |
    v
[Structured Feedback Generation]
    ├── Error classification (misread, hallucination, format confusion)
    ├── Pattern description (what the model got wrong and why)
    └── Suggested prompt refinement
    |
    v
[Prompt Update]
    ├── Extraction Agent: Add few-shot example of corrected extraction
    ├── Parser Agent: Update layout handling rules if structural
    └── Version control: New prompt version created
    |
    v
[Feedback Inheritance]
    ├── Apply updated prompt to future documents
    └── Re-process pending documents with similar characteristics
    |
    v
[Continuous Accuracy Improvement]
```

**PFTFI Results** [^498^][^525^]:
- Human review time: ~45 seconds per flagged document (vs. 120 seconds for manual processing)
- Corrections propagate immediately to extraction prompts
- No model retraining required
- Bidirectional feedback: semantic corrections improve Extraction Agent; layout feedback improves Parser Agent

### 9.2 Active Learning Pipeline

Beyond PFTFI, the system uses **active learning** to prioritize high-value training samples [^587^]:

```
Production Documents
    |
    v
[Uncertainty Sampling]
    ├── Low confidence extractions
    ├── Validation failures
    └── Novel document formats
    |
    v
[Human Annotation]
    ├── Transcription of difficult regions
    ├── Field-level correction
    └── Layout structure validation
    |
    v
[Training Data Augmentation]
    ├── Add corrected samples to training pool
    ├── Trigger fine-tuning when pool > threshold
    └── A/B test new model vs. current
    |
    v
[Model Deployment]
    ├── Gradual rollout (10% → 50% → 100%)
    ├── Accuracy monitoring
    └── Rollback if degradation detected
```

### 9.3 Transfer Learning for New Vendors

When processing invoices from **new vendors**, the system uses transfer learning [^589^]:
- Apply patterns learned from thousands of existing vendors
- Achieve reasonable accuracy on first encounter (typically 80-85%)
- Vendor-specific corrections rapidly improve accuracy to 95%+
- No explicit configuration required for each new vendor

### 9.4 Performance Monitoring

| Metric | Baseline | Improvement Target | Measurement |
|--------|----------|-------------------|-------------|
| Field-level extraction accuracy | 94% | > 97% | Per-field comparison to ground truth |
| Document-level accuracy | 85% (pure AI) | 98.5% (AI+HITL) | Full document correctness [^525^] |
| Auto-approval rate | 70% | > 85% | Documents passing without review |
| Human review time | 120s/doc | < 45s/doc | Time from queue to decision |
| FTE requirement (100K invoices) | 23 FTE | 7 FTE | 70% reduction [^525^] |
| Time to process new vendor format | Days | Hours | First correct extraction |

### 9.5 Feedback Loop Architecture

```python
class LearningLoop:
    def on_human_correction(self, document_id, field_name, original, corrected, reviewer_id):
        # 1. Store correction in feedback database
        correction = FeedbackRecord(
            document_id=document_id,
            field_name=field_name,
            original_value=original,
            corrected_value=corrected,
            reviewer_id=reviewer_id,
            timestamp=now(),
            document_type=get_document_type(document_id),
            vendor=get_vendor(document_id)
        )
        db.feedback.insert(correction)
        
        # 2. PFTFI: Update extraction prompts
        self.pftfi_agent.generate_feedback(correction)
        self.pftfi_agent.update_extraction_prompt(correction)
        
        # 3. Check if reprocessing pending documents would help
        similar_pending = find_similar_pending_documents(correction)
        if similar_pending:
            self.pftfi_agent.apply_feedback_inheritance(similar_pending, correction)
        
        # 4. Active learning: Add to training pool if informative
        if is_informative_sample(correction):
            self.training_pool.add(correction)
            if self.training_pool.size() > RETRAIN_THRESHOLD:
                self.trigger_model_fine_tuning()
        
        # 5. Update vendor-specific accuracy metrics
        self.accuracy_tracker.record_correction(correction)
        
        # 6. Alert if accuracy drops below threshold
        vendor_accuracy = self.accuracy_tracker.get_vendor_accuracy(correction.vendor)
        if vendor_accuracy < VENDOR_ACCURACY_ALERT_THRESHOLD:
            self.alert_ops_team(f"Vendor {correction.vendor} accuracy dropped to {vendor_accuracy}")
```

---

## 10. Privacy & Compliance

### 10.1 Data Minimization

The system implements **data minimization** by design [^489^][^526^]:

| Principle | Implementation |
|-----------|---------------|
| **Collect only necessary data** | Extract only fields required for accounting; discard unrelated personal information |
| **Minimize retention** | Raw documents retained per financial regulations; extracted data anonymized after period close |
| **Local processing option** | Docling + local LLM (e.g., Mistral-Small, DeepSeek-OCR) for sensitive documents |
| **No cloud for confidential** | Air-gapped deployment option for classified/sensitive financial data |

### 10.2 GDPR Compliance

Following GDPR requirements for financial document processing [^526^]:

**Step 1: Map All Personal Data**
- Inventory of all personal data processed (vendor names, employee names, bank accounts, addresses)
- Data flow diagrams showing collection → processing → storage → deletion

**Step 2: Categorize by Purpose and Legal Basis**
| Category | Purpose | Legal Basis | Retention |
|----------|---------|-------------|-----------|
| Invoice data | Accounts payable processing | Contract fulfillment | 7 years (tax requirement) |
| Receipt data | Expense reimbursement | Contract fulfillment | 7 years |
| Bank statements | Reconciliation | Legitimate interest | 7 years |
| Employee expense claims | Payroll processing | Legal obligation | 7 years |

**Step 3: Set Retention Periods**
- Financial documents: 7 years (tax/regulatory requirement)
- Raw extraction logs: 90 days
- Confidence scores and metadata: 2 years
- Human review audit trails: 7 years

**Step 4: Document Deletion Procedures**
- Automated deletion after retention period expires
- Secure erasure (cryptographic wiping for digital records)
- Deletion extends to backups within 30 days of request
- Right to erasure ("right to be forgotten") honored within 30 days

### 10.3 Local Processing Architecture

For organizations requiring **air-gapped or local processing** [^489^][^526^][^531^]:

```
Document Input
    |
    v
[Docling - Local Processing]
    ├── Layout Analysis Model (RT-DETR) - local
    ├── TableFormer - local
    ├── OCR (EasyOCR) - local
    └── Output: Structured Markdown
    |
    v
[Local LLM - Self-hosted]
    ├── Mistral-Small-3.2 (self-hosted)
    ├── DeepSeek-OCR (self-hosted)
    └── Output: Structured JSON
    |
    v
[Local Validation + Storage]
    ├── Mathematical validation
    ├── Confidence scoring
    └── PostgreSQL/Local DB
```

**Local-First Benefits** [^489^]:
- No documents leave the organization's infrastructure
- Zero external API costs for document processing
- Complete control over data residency
- Compliance with financial services regulations
- Processing latency independent of internet connectivity

### 10.4 Security Controls

| Control | Implementation |
|---------|---------------|
| **Encryption at rest** | AES-256-GCM for all stored documents |
| **Encryption in transit** | TLS 1.3 for all API communications |
| **Access control** | RBAC with field-level permissions for reviewers |
| **Audit logging** | Immutable logs of all extraction, review, and correction actions |
| **Data segregation** | Tenant isolation for multi-organization deployments |
| **Anonymization** | PII redaction in logs and training data |
| **Vendor data protection** | Vendor bank accounts stored encrypted; access restricted to payment systems |

### 10.5 Audit Trail

Every document processing event is logged for compliance:

```json
{
  "audit_event_id": "ae_123456",
  "timestamp": "2024-01-15T09:23:30Z",
  "document_id": "doc_abc123",
  "actor": {
    "type": "system" | "human",
    "id": "system_extraction_agent" | "user_jane_doe",
    "ip_address": "10.0.1.100"
  },
  "action": "field_corrected",
  "details": {
    "field": "vendor_name",
    "original_value": "Acme Softwar Inc",
    "corrected_value": "Acme Software Inc",
    "confidence_before": 0.72,
    "confidence_after": 0.99,
    "correction_reason": "typo_in_original_extraction"
  },
  "compliance_metadata": {
    "retention_class": "financial_7_years",
    "gdpr_category": "contractual_data",
    "data_subject_consent": "N/A_business_data"
  }
}
```

### 10.6 Compliance Frameworks

| Framework | Requirements | System Support |
|-----------|-------------|----------------|
| **GDPR** | Data minimization, right to erasure, consent tracking | Full: local processing, retention policies, deletion procedures |
| **SOX** | Audit trails, data integrity, access controls | Full: immutable audit logs, RBAC, change tracking |
| **PCI DSS** | Secure handling of cardholder data | Partial: last-four-only storage, encrypted transmission |
| **HIPAA** (if applicable) | PHI protection, access logging | Full: encryption, access controls, audit trails |
| **SOC 2 Type II** | Security, availability, processing integrity | Full: all Trust Service Criteria supported |

---

## Appendix A: Technology Stack Recommendations

| Component | Primary Option | Alternative | Local Option |
|-----------|---------------|-------------|--------------|
| Document Parsing | Docling [^526^] | LlamaParse, Marker | Docling (MIT license) |
| OCR Engine | Mistral OCR 3 [^577^] | DeepSeek-OCR, Qwen3-VL | Tesseract, EasyOCR |
| Extraction LLM | GPT-4o / Claude 3.5 Sonnet | Gemini 2.5 Pro | Mistral-Small-3.2 [^525^] |
| Classification | ResNet-18 CNN [^525^] | Azure Doc Intelligence | ResNet-18 (self-hosted) |
| Validation | Custom Python rules | Azure AI Document Intelligence | Custom rules |
| Review Queue | Custom React/Next.js UI | Rossum, Hyperscience | Custom UI |
| Document Store | AWS S3 / Azure Blob | Google Cloud Storage | MinIO (self-hosted) |
| Database | PostgreSQL | MongoDB | PostgreSQL |
| Message Queue | Apache Kafka | RabbitMQ, AWS SQS | Apache Kafka |

## Appendix B: Performance Benchmarks

| Benchmark | Metric | Value | Source |
|-----------|--------|-------|--------|
| MADP Production (Jan 2026) | Full-pipeline automation | 97.0% | [^525^] |
| MADP Stratified Ablation | Document-level accuracy (AI+HITL) | 98.5% | [^525^] |
| MADP Parser Agent | Accuracy improvement contribution | +17.5 pp | [^525^] |
| MADP FTE Reduction | vs. manual processing | 70% | [^525^] |
| Vision LLM vs Text Pipeline | Scanned invoice accuracy | 92.71% vs 64.03% | [^499^] |
| Mistral OCR 3 | Overall benchmark score | 94.89% | [^574^] |
| Confidence Scoring | Silent failure reduction | >90% | [^581^] |
| Docling Token Reduction | vs. raw OCR output | 35% | [^525^] |
| AI Duplicate Detection | Detection rate | 95-99% | [^514^] |

## Appendix C: Cost Model (Annual, 100,000 Invoices)

| Scenario | FTE Required | Annual Cost | Accuracy |
|----------|-------------|-------------|----------|
| **Manual Processing** | 23 FTE | $1,380,000 (loaded) | 95% |
| **Pure AI (no HITL)** | 4 FTE | $85,000 infra + review | 85% |
| **AI + HITL (Recommended)** | 7 FTE | $175,000 infra + $210,000 labor | 98.5% |
| **Savings vs Manual** | -16 FTE | **-$995,000/year** | +3.5% |

Cloud API costs at 100K documents/year:
- Text-based invoices: ~$1,500-$3,000/year
- Scanned invoices (50% mix): ~$4,500-$7,500/year
- Docling local processing: $0 (compute only)

---

## References

[^486^] Khanchandani, K. et al. (2025). "Automated Invoice Data Extraction: Using LLM and OCR." arXiv:2511.05547. https://arxiv.org/pdf/2511.05547

[^487^] xKDR (2025). "Information Extraction From Fiscal Documents Using LLMs." arXiv:2511.10659. https://arxiv.org/html/2511.10659v2

[^489^] LumaDock. "OpenClaw PDF workflows for local summarization and extraction." https://lumadock.com/tutorials/openclaw-pdf-summarization-extraction

[^490^] AgentMail (2026). "OpenClaw Email Automation: 7 Real-World Use Cases." https://www.agentmail.to/blog/openclaw-email-automation-use-cases

[^493^] Cognica (2025). "Automated Financial Statement Extraction from PDFs Using LLMs." https://www.cognica.io/en/blog/posts/2025-11-18-llm-pdf-financial-statement-extraction

[^494^] AI Expedition Journey (2025). "Hybrid OCR-LLM: Not a Bigger Model, but a Smarter Pipeline." https://aiexpjourney.substack.com/p/hybrid-ocr-llm-not-a-bigger-model

[^496^] Thomas Wiegold (2026). "Building Reliable Invoice Extraction Prompts That Handle Edge Cases." https://thomas-wiegold.com/blog/building-reliable-invoice-extraction-prompts/

[^497^] Microsoft Tech Community (2024). "Evaluating the quality of AI document data extraction with small and large language models." https://techcommunity.microsoft.com/discussions/azurepartners/evaluating-the-quality-of-ai-document-data-extraction-with-small-and-large-langu/4157719

[^498^] Gosmar, D. & Zenezini, G. (2026). "MADP: A Multi-Agent Pipeline for Sustainable Document Processing with Human-in-the-Loop." arXiv:2605.17159. https://arxiv.org/html/2605.17159v1

[^499^] InvoiceDataExtraction.com (2026). "Vision LLM Invoice Extraction with Python: Practical Guide." https://invoicedataextraction.com/blog/vision-llm-invoice-extraction-python

[^500^] CodeAwake (2024). "Automating Invoice Processing with GPT-4o." https://codeawake.com/blog/invoice-processing

[^501^] LinkstartAI (2026). "Extract Invoice Data with LlamaParse & GPT-4o." https://www.linkstartai.com/en/toolkits/llamaparse-gpt-4o-google-sheets-telegram

[^502^] Azure Samples (2024). "azure-openai-gpt-4-vision-pdf-extraction-sample." GitHub. https://github.com/Azure-Samples/azure-openai-gpt-4-vision-pdf-extraction-sample

[^505^] Databricks (2026). "What is Human-in-the-Loop (HITL)?" https://www.databricks.com/blog/human-in-the-loop

[^506^] "Invoice Information Extraction: Methods and Performance Evaluation." arXiv:2510.15727v2. https://arxiv.org/html/2510.15727v2

[^507^] LlamaIndex. "What is Human-In-The-Loop Verification?" https://www.llamaindex.ai/glossary/human-in-the-loop-verification

[^509^] Flooowed (2026). "Human-in-the-Loop Document Automation for Lenders." https://www.floowed.com/insights/human-in-the-loop-document-automation

[^510^] Mindee (2026). "The role of human-in-the-loop (HITL) in document automation." https://www.mindee.com/blog/what-is-human-in-the-loop-automation

[^514^] Peakflo (2026). "How to Prevent Duplicate Invoices and Payments in Accounts Payable." https://peakflo.co/blog/prevent-duplicate-invoices-payments-accounts-payable

[^515^] Docsumo (2026). "Guide To Duplicate Invoice Detection." https://www.docsumo.com/blog/duplicate-invoice-detection

[^517^] InvoiceDataExtraction.com (2026). "Azure AI Document Intelligence for Invoice Extraction." https://invoicedataextraction.com/blog/azure-ai-document-intelligence-invoice-extraction

[^519^] Syncfusion. "Azure AI Document Intelligence." https://www.syncfusion.com/succinctly-free-ebooks/azure-ai-services-succinctly/azure-ai-document-intelligence

[^522^] Gennai (2026). "Fixing Duplicate Invoice Detection Problems." https://www.gennai.io/blog/duplicate-invoice-detection

[^523^] InvoiceDataExtraction.com (2026). "Receipt OCR: How It Works, Accuracy, and Key Challenges." https://invoicedataextraction.com/blog/receipt-ocr-guide

[^525^] Gosmar, D. & Zenezini, G. (2026). "MADP: A Multi-Agent Pipeline for Sustainable Document Processing with Human-in-the-Loop." arXiv:2605.17159v1. https://arxiv.org/html/2605.17159v1

[^526^] Livathinos, N. et al. (2024). "Docling: An Efficient Open-Source Toolkit for AI-driven Document Conversion." arXiv:2501.17887v1. https://arxiv.org/html/2501.17887v1

[^527^] Moonlight AI (2026). "MADP Literature Review." https://www.themoonlight.io/en/review/madp-a-multi-agent-pipeline-for-sustainable-document-processing-with-human-in-the-loop

[^529^] InfoWorld (2025). "Docling: An open-source tool kit for advanced document processing." https://www.infoworld.com/article/3997240/docling-an-open-source-tool-kit-for-advanced-document-processing.html

[^530^] Docling Documentation. https://www.docling.ai/

[^531^] IBM Research (2024). "IBM is open-sourcing a new toolkit for document conversion." https://research.ibm.com/blog/docling-generative-AI

[^532^] CommonPlace (2026). "MADP summary and claims." https://commonplace.workforcefutures.net/paper/arxiv:2605.17159

[^567^] Subhajit Bhar (2026). "Invoice Data Extraction with Python: From Script to Production Pipeline." https://subhajitbhar.com/blog/idp/invoice-data-extraction-python/

[^568^] PDFPenguin (2026). "Extract Invoice Data from PDF The Ultimate How To Guide." https://pdfpenguin.net/blog/extract-invoice-data-from-pdf

[^569^] SparkCo AI (2025). "DeepSeek OCR vs Mistral OCR: Benchmark Analysis 2025." https://sparkco.ai/blog/deepseek-ocr-vs-mistral-ocr-benchmark-analysis-2025

[^570^] Analytics Vidhya (2025). "DeepSeek OCR vs Qwen-3 VL vs Mistral OCR." https://www.analyticsvidhya.com/blog/2025/11/deepseek-ocr-vs-qwen-3-vl-vs-mistral-ocr/

[^571^] Towards Data Science (2026). "I Spent May Evaluating Different Engines for OCR." https://towardsdatascience.com/i-spent-may-evaluating-different-engines-for-ocr/

[^573^] Docspire AI (2026). "How to Perform Complex Table Extraction for Multi-Line Invoices." https://docspire.ai/blog/multi-line-invoice-processing-automation/

[^574^] Mistral AI (2024). "Mistral OCR." https://mistral.ai/news/mistral-ocr/

[^577^] Medium (2026). "Mistral OCR 3 Changed OCR Overnight." https://medium.com/codetodeploy/mistral-ocr-3-changed-ocr-overnight-its-now-ai-infrastructure-c9d9af844cd2

[^578^] Agami AI (2026). "Document Processing: Validation is Plan A." https://blog.agami.ai/document-processing-validation-is-plan-a/

[^579^] Landing AI (2026). "Introducing Confidence Scores: Surface Parsing Uncertainty Before It Becomes a Problem." https://landing.ai/blog/introducing-confidence-scores-surface-parsing-uncertainty-before-it-becomes-a-problem

[^580^] LlamaIndex. "Understanding Confidence Threshold in AI Systems." https://www.llamaindex.ai/glossary/what-is-confidence-threshold

[^581^] Subhajit Bhar (2026). "Confidence Scoring in Document Extraction." https://subhajitbhar.com/blog/idp/glossary/confidence-scoring-document-extraction/

[^585^] Microsoft Learn (2025). "Interpret and improve model accuracy and confidence scores." https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept/accuracy-confidence

[^586^] Docling Documentation. "Confidence scores." https://docling-project.github.io/docling/concepts/confidence_scores/

[^587^] LlamaIndex. "What is Active Learning for OCR?" https://www.llamaindex.ai/glossary/active-learning-for-ocr

[^589^] Gennai (2026). "Machine Learning for Invoice Data: A Practical Guide." https://www.gennai.io/blog/machine-learning-invoice-data-guide
