# OMEGA AI

Autonomous AI Agent Operating System — Windows 10 desktop.
Arabic-first (RTL), English supported. **$0 — free tools only.**

> This is the desktop build. It is a DIFFERENT project from the OMEGA
> income-research system in `~/workspace/omega/` — that folder is never
> touched by this build.

## What it is
A personal AI operating system: you type an objective → OMEGA researches,
plans, delegates to specialised agents, operates the computer, builds
software, manages projects, remembers everything, and improves itself.

## Two layers (see DECISIONS.md D-02)
1. **Python core** — the existing `YAHYA_AI_COMMAND_CENTER` (supervisor +
   7 agents + permissions + SQLite memory). Runs NOW, zero install.
2. **Electron shell** — Windows desktop app + React dashboard (target).
   Scaffolded here; `npm install` is gated on disk-quota relief.

## Run it now (no install, $0)
```bash
# 1. Dashboard + API (stdlib only — no dependencies)
python3 ~/workspace/omega-ai/bridge/omega_bridge.py
# open http://127.0.0.1:8471/ in a browser

# 2. Full agent core (needs the existing venv + a free API key)
cd ~/workspace/YAHYA_AI_COMMAND_CENTER
cp .env.example .env   # if present; else create it
# add OPENROUTER_API_KEY=<free key from openrouter.ai/keys> — your tap, never in chat
.venv/bin/streamlit run app.py
```

Without an API key the core honestly reports "LLM not configured" — it never
fakes a run.

## Layout
```
MASTER_STATUS.md     audit + plan + changelog (the source of truth)
DECISIONS.md         architecture decisions, dated
TASKS.md             phase task list with states
ARCHITECTURE.md      module map + integration map
package.json         Electron + React + TS target stack (install deferred)
electron/            main.js + preload.js (Electron shell scaffold)
dashboard/           index.html — dependency-free dashboard v0.1
core/                agent-registry.json + memory-schema.sql
bridge/              omega_bridge.py — stdlib HTTP bridge to the Python core
integrations/        inventory + MCP contract
```

## Standing rules (never break)
- $0 only. No paid tools, subscriptions, credits, ads, domains, card trials.
- Money, passwords, OTP/2FA, KYC/ID, publishing, external sends, irreversible
  deletes: Yahya's explicit approval, always (GREEN/YELLOW/RED — see D-07).
- Never claim a tool is installed, connected or working without testing it.
- Never report a task completed unless its output was verified.
- Backups before modifications; git checkpoints; never delete existing work.
