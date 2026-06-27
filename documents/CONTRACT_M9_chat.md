# CONTRACT: Module 9 — LLM Chat Interface

## Goal
Implement WebSocket-based LLM Chat Interface with multi-turn conversation, intent routing,
context memory, skill registry of all 25+ SKILLs, natural date parsing, and 3 personas.

## Boundaries
- IN SCOPE: WebSocket endpoint /ws/chat/{session_id}, conversation state management in Redis,
  skill registry (YAML file listing all 25+ MCP tools with descriptions/schemas),
  intent routing (map NL to tool call), multi-turn dialogue,
  natural date parsing (last month, Q2, this FY), 3 personas (professional/friendly/minimal)
- OUT OF SCOPE: Actual LLM integration (GPT-4o/Claude — MVP uses rule-based router),
  Katra-Agentic-Memory integration (memory persistence optional for MVP)

## Technical Specs
### WebSocket Protocol
- Connect: ws://localhost:8000/ws/chat/{session_id}
- Messages: JSON format with type field
- Types: user_message, stream_start, stream_token, stream_end, confirmation_request, 
  confirmation_response, error, tool_call, tool_result

### Skill Registry (api/src/skills/registry.yaml)
YAML file listing all 25+ SKILLs with:
- id: gl.record_expense, coa.list, invoice.create, etc.
- category: COA, GL, Contact, Bank, Reconciliation, Invoice, VAT, Report
- description: from LLM's perspective (when to use)
- inputSchema: JSON Schema for parameters
- example: natural language example query

### Intent Router
Rule-based for MVP: keyword matching + pattern recognition to route NL to correct tool.
- Extract entities: amounts (£120), dates (last month), contacts (Acme), accounts (marketing)
- Map to skill: "paid" → gl.record_expense, "invoice" → invoice.create, "VAT" → vat.preview_return

### Conversation State (Redis)
Per-session JSON with: entity state, current context, history (last 50 messages), 
selected bank account, active reconciliation session, preferred persona

### API Endpoints
- WS /ws/chat/{session_id} — WebSocket endpoint
- GET /api/v1/skills — list all registered skills
- GET /api/v1/skills/{skill_id} — skill detail
- POST /api/v1/skills/reload — reload registry from YAML

## Success Criteria
1. WebSocket connection works with typed JSON messages
2. All 25+ skills discoverable via skills endpoint
3. Intent router maps at least 10 common NL patterns correctly
4. Multi-turn dialogue preserves context
5. Date parsing handles "last month", "Q2", "this FY" correctly
6. 3 personas produce different response tones

## Files
api/src/{routes/chat.py, services/chat_service.py, services/skill_registry.py, 
       services/intent_router.py, validators/chat.py}
api/src/skills/registry.yaml
api/tests/{unit/test_intent_router.py, unit/test_chat_service.py, integration/test_chat_ws.py}
