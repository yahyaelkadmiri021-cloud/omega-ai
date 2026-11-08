# OMEGA AI — ARCHITECTURE

## Module map

```
┌─────────────────────────────────────────────────────────────────┐
│  ELECTRON SHELL (target, Windows)                               │
│  electron/main.js — window, IPC, permission gates               │
│  electron/preload.js — safe bridge (contextIsolation)           │
│  dashboard/index.html — 12 sections, AR RTL + EN                │
│  React + TypeScript replaces dashboard/ when npm install lands  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP 127.0.0.1:8471
┌──────────────────────────────┴──────────────────────────────────┐
│  BRIDGE (stdlib-only Python)                                    │
│  bridge/omega_bridge.py — /status /agents /run /memory          │
└──────────────────────────────┬──────────────────────────────────┘
                               │ imports (guarded)
┌──────────────────────────────┴──────────────────────────────────┐
│  OMEGA CORE — YAHYA_AI_COMMAND_CENTER (existing, adopted)       │
│  core/supervisor.py — classify → research → plan → critic loop  │
│                     → human gate → execute → document           │
│  core/llm_router.py — LiteLLM, provider-configurable            │
│  core/permissions.py — GREEN / YELLOW / RED                     │
│  core/memory.py + memory/long_term.py — SQLite                  │
│  agents/ — researcher, strategist, coder, creative, analyst,    │
│             critic (forced different model), executor           │
│  tools/ — web_search, browser, filesystem, github, calculator,  │
│           scheduler                                             │
└─────────────────────────────────────────────────────────────────┘
```

## The 8 spec agents → real modules
| # | Spec agent | Real module | Status |
|---|---|---|---|
| 1 | Research Agent | `agents/researcher.py` | EXISTS, verified importable |
| 2 | Software Engineer Agent | `agents/coder.py` | EXISTS |
| 3 | Business Agent | `agents/strategist.py` + `agents/analyst.py` | EXISTS (split role) |
| 4 | Marketing Agent | `agents/creative.py` | EXISTS (partial — strategy via strategist) |
| 5 | Content Agent | `agents/creative.py` + factory (`MUSE_OMNIPRO_MAX.md`) | EXISTS (partial — video pipeline is the factory) |
| 6 | Computer Operator Agent | `agents/executor.py` + `tools/filesystem.py` | EXISTS (sandboxed); Desktop Commander = Phase 7 |
| 7 | Quality Assurance Agent | `agents/critic.py` (forced different model) | EXISTS |
| 8 | Project Manager Agent | **NEW** — `agents/project_manager.py` (to build) | MISSING — Phase 5 |

## Integrations (read-only unless stated)
- **MUSE factory** (`~/workspace/shorts/MUSE_OMNIPRO_MAX.md`, `content_factory/`) —
  Content Agent engine: Shorts/long-form pipelines, viral DB, style bible.
- **AWR / Digital Studio** (`~/workspace/digital-studio/awr/`) — product
  backlog (10 items READY_FOR_REVIEW) + MASTER_STATUS; dashboard reads it.
- **OMEGA research** (`~/workspace/omega/`) — income-opportunity engine;
  Business Agent reads its DB; never written by this build.
- **muse_omega memory** (`~/workspace/muse_omega/MUSE_MEMORY/`) — memory seed.
- **ai-tools** (`~/workspace/ai-tools/tools_database.json`) — tool registry.
- **ORIGIN** — not found; integration pending Yahya's answer.

## Task states (spec §5 → supervisor)
Pending → Planning → Running → Waiting for approval (human gate) →
Testing (critic loop) → Completed (verified only) / Failed (logged, retried once).

## Data flow (one objective)
Objective → bridge /run → supervisor.classify_task → agents (research →
plan → critic loop) → human gate (YELLOW/RED pause) → executor →
REPORT.md + project.json + memory → dashboard shows verified result.

## Security boundaries
- Keys only in `.env`, never in code/git/logs/chat.
- Filesystem tool is sandboxed to the workspace.
- Deletes / admin commands / installs / publishing / sends / purchases:
  explicit approval, every time.
- No self-modifying production code without backup + tests + approval.
