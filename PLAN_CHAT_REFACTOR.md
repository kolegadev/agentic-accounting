# Chat System Refactoring Plan

## Problem
The current chat_service.py uses a REGEX-based intent_router.py that:
- Matches keywords → maps to skill IDs
- Extracts amounts/dates with regex
- **Never actually calls any accounting tool** — just simulates
- No LLM involvement whatsoever

## Solution: LLM-Powered Tool-Calling Chat Pipeline

### Architecture

```
User Message → ChatService.process_message()
  → LLM Router (analyzes intent, picks tool, extracts params)
  → Tool Executor (calls actual accounting service/route)
  → Response Formatter (persona-appropriate response)
  → State Persistence (Katra + Redis)
```

### 1. Delete
- `api/src/services/intent_router.py` — entire file (REGEX system)

### 2. New Files

#### `api/src/services/llm_router.py`
LLM-powered intent understanding:
- Takes user message + conversation history + available tools
- Sends to LLM (configurable: OpenAI-compatible API, DeepSeek, etc.)
- LLM returns JSON: `{"tool": "skill_id", "params": {...}}` OR `{"response": "clarifying question"}`
- Includes setup wizard detection (check if COA is empty → guide through setup)

#### `api/src/services/tool_executor.py`
Maps skill IDs → actual service calls:
- `coa.list` → `coa_service.list_accounts()`
- `gl.record_expense` → `transaction_service.record_expense()`
- `invoice.create` → `invoice_service.create_invoice()`
- etc. for all 40 tools

#### `api/src/services/setup_wizard.py`
Guided company setup:
- Detects fresh system (no COA accounts)
- Walks user through: business type → COA template → VAT config → bank account
- Each step calls actual services (coa_service.load_template(), etc.)

### 3. Modified Files

#### `api/src/services/chat_service.py`
- Remove `IntentRouter` import and usage
- Add `LLMRouter` and `ToolExecutor` 
- Modify `process_message()` to:
  1. Check if setup needed → run wizard
  2. Route via LLM → execute tool → format response
  3. Persist state

### 4. LLM Prompt Design

```
System: You are an accounting assistant. You have access to these tools:
[TOOL_LIST_WITH_SCHEMAS]

Rules:
- If the user's intent matches a tool, respond with: {"tool": "<skill_id>", "params": {...}}
- If you need clarification, respond with: {"response": "<your question>"}
- If the system has no chart of accounts, guide through setup
- All amounts in INTEGER PENCE (e.g., £50.00 = 5000)
- Dates in YYYY-MM-DD format

Current conversation:
{HISTORY}

User: {MESSAGE}
```

### 5. Setup Wizard State Machine

```
INIT → ASK_BUSINESS_TYPE → ASK_COA_TEMPLATE → ASK_VAT → ASK_BANK → COMPLETE

States:
- INIT: Detect empty COA → "Welcome! Let's set up your business. Are you a sole trader, limited company, or partnership?"
- ASK_BUSINESS_TYPE: User responds → "Got it. Here are the chart of accounts templates..."
- ASK_COA_TEMPLATE: User picks → load template → "COA loaded! Are you VAT registered?"
- ASK_VAT: User responds → "VAT configured. What's your main bank account called?"
- ASK_BANK: User responds → create bank account → "All set! You're ready to start recording transactions."
- COMPLETE: Normal chat mode
```

### 6. LLM Configuration (env vars)
```
LLM_API_URL=http://localhost:11434/v1  # Ollama / OpenAI-compatible
LLM_API_KEY=optional
LLM_MODEL=deepseek-v4-pro
LLM_TEMPERATURE=0.1  # Low temperature for tool calling accuracy
```

### 7. Tool Registry → Service Mapping
| Skill ID | Service Method |
|----------|---------------|
| coa.list | coa_service.list_accounts() |
| coa.add_account | coa_service.create_account() |
| coa.edit_account | coa_service.update_account() |
| coa.set_vat_rate | coa_service.set_vat_rate() |
| gl.record_expense | transaction_service.create_expense() |
| gl.record_income | transaction_service.create_income() |
| gl.record_transfer | transaction_service.create_transfer() |
| gl.journal_entry | transaction_service.create_journal() |
| gl.list_transactions | transaction_service.list_transactions() |
| gl.transaction_detail | transaction_service.get_transaction() |
| gl.undo_transaction | transaction_service.undo_transaction() |
| contact.create | contact_service.create_contact() |
| contact.edit | contact_service.update_contact() |
| contact.list | contact_service.list_contacts() |
| contact.detail | contact_service.get_contact() |
| contact.archive | contact_service.archive_contact() |
| bank.import_csv | bank_service.import_csv() |
| bank.import_ofx | bank_service.import_ofx() |
| bank.list_accounts | bank_service.list_bank_accounts() |
| bank.add_account | bank_service.create_bank_account() |
| bank.transactions | bank_service.list_transactions() |
| bank.categorize | bank_service.categorize_transaction() |
| recon.start | reconciliation_service.start_reconciliation() |
| recon.match | reconciliation_service.match_transaction() |
| recon.create_and_match | reconciliation_service.create_and_match() |
| recon.status | reconciliation_service.get_status() |
| recon.report | reconciliation_service.get_report() |
| invoice.create | invoice_service.create_invoice() |
| invoice.send | invoice_service.send_invoice() |
| invoice.list | invoice_service.list_invoices() |
| invoice.mark_paid | invoice_service.mark_paid() |
| invoice.credit_note | invoice_service.create_credit_note() |
| invoice.overdue | invoice_service.list_overdue() |
| vat.preview_return | vat_service.preview_return() |
| vat.transaction_detail | vat_service.get_transactions() |
| vat.adjustment | vat_service.create_adjustment() |
| vat.audit_trail | vat_service.get_audit_trail() |
| report.run | report_service.run_report() |
| report.list | report_service.list_reports() |
| report.schedule | report_service.schedule_report() |
