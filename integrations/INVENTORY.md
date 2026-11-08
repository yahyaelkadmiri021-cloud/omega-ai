# OMEGA AI — INTEGRATION INVENTORY (verified 2026-11-07)

Read-only by default. OMEGA AI never writes into these projects; it reads
them as data and links back to their own status files.

## OMEGA (income research) — `~/workspace/omega/`
- Spec: `OMEGA_SYSTEM.md` (5 engines A–E, verification rules).
- `applications/` — drafted applications (CV, listing cards, samples).
- `plans/` — execution plans (24h/3d/7d).
- `research/` — first research (1,747 lines).
- Integration: Business Agent reads opportunity DB; dashboard shows status.
- ⚠️ Name collision with OMEGA AI — separate folders, never merged.

## MUSE (factory) — `~/workspace/shorts/MUSE_OMNIPRO_MAX.md` + `content_factory/`
- Factory spec + Shorts/long-form pipelines + viral DB + style bible.
- Integration: Content Agent engine. Dashboard shows queue states.

## AWR (Digital Studio) — `~/workspace/digital-studio/awr/`
- `MASTER_STATUS.md` (current 2026-11-06), `products/` (10 READY_FOR_REVIEW),
  `decisions/`, `learnings/`, `opportunities/`, `customers/`, `orders/`.
- Integration: dashboard reads product backlog + status; no writes.

## muse_omega (memory seed) — `~/workspace/muse_omega/`
- `OMEGA_MASTER_PROMPT.md` (61KB, 2026-09-29), `MUSE_MEMORY/` (16 JSON + 9 MD),
  `STARTUP_REPORT.md`, `TOOLS_DATABASE`.
- Integration: memory seed for `core/memory-schema.sql`.

## ai-tools — `~/workspace/ai-tools/`
- `tools_database.json`, `MCP_CONNECTORS.md`, `STACK.md`, `WORKFLOWS.md`, `FAILOVER.md`.
- Integration: tool registry for the Tool Engine.

## YAHYA_AI_COMMAND_CENTER — `~/workspace/YAHYA_AI_COMMAND_CENTER/`
- The adopted OMEGA CORE. Supervisor + 7 agents + permissions + SQLite memory.
- venv populated (streamlit 1.64.0, litellm, langgraph, duckduckgo-search).
- No `.env` / API key yet — Yahya's tap.

## ORIGIN — NOT FOUND
- No folder under `~/workspace/`. Pending Yahya's answer (Windows machine? never created?).

## agents/ — `~/workspace/agents/`
- Prior agent workspaces (UUID dirs). Untouched.
