# CONTRACT: Module 10 — MCP Gateway + SKILL.md + Docker

## Goal
Implement MCP Protocol Gateway exposing all 25+ accounting tools via MCP protocol (SSE transport),
SKILL.md auto-installer file, and finalize Docker Compose orchestration.

## Boundaries
- IN SCOPE: MCP Gateway server (FastAPI on port 3112), SSE transport with 
  tools/list, tools/call, resources/list endpoints, tool registry from YAML,
  SKILL.md file at repo root for agent auto-discovery,
  Dockerfile for gateway, docker-compose.yml finalization
- OUT OF SCOPE: OAuth 2.0 + PKCE (Phase 2), stdio transport (MVP uses SSE only),
  multi-agent session management, rate limiting

## Technical Specs
### MCP Gateway (gateway/src/server.py)
- Port 3112, SSE transport
- Endpoints:
  - GET /sse — SSE connection endpoint
  - POST /message — MCP message handler
  - GET /health — health check
  - GET / — root with service info
- MCP Lifecycle:
  - initialize → server info + capabilities
  - tools/list → return all tools from registry
  - tools/call → parse tool name, validate params, proxy to accounting-api:8000
  - resources/list → static resources (COA templates, bank templates)

### SKILL.md (repo root)
Single markdown file that any MCP agent reads to discover accounting tools.
YAML frontmatter with server config, followed by tool reference section.
Must work with OpenClaw, Claude Code, Kolega Code, and any MCP-compatible agent.

### Docker Files
- gateway/Dockerfile — Python slim, FastAPI + uvicorn
- gateway/requirements.txt — minimal deps (fastapi, uvicorn, httpx, pyyaml, pydantic)

## Files
gateway/src/{server.py, tool_registry.py}
gateway/{Dockerfile, requirements.txt}
SKILL.md (repo root)
api/docker-compose.yml (update as needed)

## Success Criteria
1. MCP /tools/list returns all 25+ tools with schemas
2. MCP /tools/call routes to correct accounting-api endpoint
3. MCP /health returns 200
4. SKILL.md validates with YAML frontmatter + tool reference
5. Gateway Dockerfile builds and runs
