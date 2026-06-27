# Plan: Headless LLM-Native Accounting System — Requirements & Roadmap

## Objective
Produce a comprehensive requirements document covering:
- a) MVP scope definition
- b) Phased implementation roadmap from MVP → Full Xero-class accounting system

## Architecture Context
- **Backend**: Formance open-source immutable double-entry ledger (https://www.formance.com/modules/ledger)
- **Primary UIs**: OpenClaw-type agentic workflow manager + LLM chat window
- **Paradigm**: "Headless" accounting — no traditional UI, LLMs interpret requirements and execute accounting
- **Tooling**: SKILLs / tool-calls for each report type (repeatable, rule-compliant)
- **Compliance**: GAAP + IFRS, multi-currency, multi-tax, domicile-aware addressing

## Stage 1 — Deep Research (Parallel)
Load: `deep-research-swarm`
- **Agent 1 — Formance Research**: Formance Ledger API, data model, transaction model, accounts, transactions, metadata, multi-currency support, scalability, deployment model
- **Agent 2 — Accounting Standards Research**: GAAP vs IFRS requirements for SME accounting, chart of accounts structures, double-entry rules, financial statements (P&L, Balance Sheet, Cash Flow), audit trails, multi-currency handling (IAS 21), tax systems (VAT/GST/sales tax), domicile addressing formats
- **Agent 3 — Xero Benchmark Research**: Xero feature catalog (SME tier), API structure, reports available, bank reconciliation, invoicing, payroll, multi-currency, tax support, add-on ecosystem
- **Agent 4 — Agentic Patterns Research**: OpenClaw architecture, agentic workflow managers, LLM tool-calling patterns for accounting operations, skill-based agent design, safety/guardrails for financial operations

Output: 4 validated research briefs

## Stage 2 — Requirements Engineering (Parallel)
- **Agent 5 — MVP Requirements**: Synthesize research into MVP feature set, core flows (onboarding, chart of accounts, transactions, basic reports), Formance integration points, agent skills needed, compliance scope for MVP
- **Agent 6 — Phased Roadmap**: Full feature taxonomy, phase grouping (MVP → v2 → v3 → v4), dependencies, complexity scoring, GAAP/IFRS coverage per phase, multi-currency rollout, tax system expansion

## Stage 3 — Report Writing
Load: `report-writing`
- Design outline based on Stage 1+2 outputs
- Write full requirements document
- Output: `/mnt/agents/output/accounting-system-requirements.md`

## Stage 4 — Document Production
Load: `docx`
- Convert final markdown to professional .docx
- Output: `/mnt/agents/output/accounting-system-requirements.docx`

## Deliverables
1. `accounting-system-requirements.md` — Full markdown requirements document
2. `accounting-system-requirements.docx` — Professional Word document
