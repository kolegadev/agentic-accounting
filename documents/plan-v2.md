# Architecture Revision Plan v2

## Key Changes from User Clarifications

1. **MCP as Gateway**: Model Context Protocol replaces Kong/Traefik as the unified access layer
2. **Dual Client Model**: 1a) Direct Chat for humans + 1b) SKILL.md + MCP for Agentic Users (OpenClaw, Claude Code, Codex, Hermes, OpenCode, KolegaCode, Kolega Code)
3. **Katra-Agentic-Memory**: Cognitive memory infrastructure as the data/memory layer (MongoDB, Redis, MinIO, JetStream via MCP on :3112 / admin :9012)
4. **Local-First Open Source MVP**: Docker Compose, lightweight services, runs on local machine (incl. Pi5)
5. **Single Docker Architecture**: Same docker-compose.yml for local MVP and hosted SaaS
6. **SKILL.md Auto-Install**: Single SKILL.md file enables automatic installation in any MCP-compatible agent
7. **Per-Service Docker Containers**: Each functional service in its own container

## Files to Revise

### Primary (Direct Rewrite)
- `accounting_system_sec01.md` — Sections 1.2 and 1.3 (design philosophy + architecture)

### Secondary (Alignment Updates)
- `accounting_system_sec00.md` — Executive Summary (architecture description)
- `accounting_system_sec03.md` — Agentic Interface (MCP gateway, dual client, SKILL.md install)
- `accounting_system_sec08.md` — MVP Spec (Docker Compose, local-first, SKILL.md)

### Tertiary (Minor Alignment)
- `accounting_system_sec09.md` — Roadmap (phasing reflects local→SaaS)
- `accounting_system_sec01.md` — Section 1.4 (target users reflect open source)

## Deliverables
1. Revised `accounting_system_sec01.md` (primary)
2. Aligned `accounting_system_sec00.md`, `sec03.md`, `sec08.md` (secondary)
3. Re-assembled final `.md` and `.docx`
