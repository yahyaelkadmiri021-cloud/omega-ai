# OMEGA AI — MCP INTEGRATION CONTRACT (Phase 7)

Live integration needs a Windows machine (Desktop Commander is
Windows/macOS; n8n install + test there). This file is the contract both
sides implement — no claims of a working connection until tested.

## Desktop Commander (via MCP)
- Purpose: Computer Operator Agent's hands on Windows — approved folders,
  files, commands, apps, scripts, browser workflows, local app testing.
- Transport: MCP (Model Context Protocol) server exposed by Desktop Commander;
  OMEGA CORE talks to it as an MCP client (see `ai-tools/MCP_CONNECTORS.md`).
- Tools exposed to the Operator Agent (all permission-gated):
  - `fs.read / fs.write` — inside approved folders only (workspace).
  - `exec` — approved commands only; admin commands need RED approval.
  - `open-app` — approved applications only.
  - `browser` — supported workflows only.
- Rules: never expose keys/tokens in logs; deletes/installs/publishing/
  external sends need explicit approval every time (RED/YELLOW).
- Status 2026-11-07: NOT installed, NOT tested (this VM is Linux).
  Install on Yahya's Windows 10, then run the smoke test in TASKS.md Phase 7.

## n8n (workflow automation)
- Purpose: scheduled + event-driven workflows (e.g. daily research → draft →
  human gate → publish queue).
- Status 2026-11-07: NOT installed. Install options: n8n Cloud (paid — NOT
  allowed by $0 rule) or self-hosted on his Windows machine / a free tier
  host (to evaluate in Phase 7). No workflow is promised until one runs.
- First candidate workflow (Phase 7): income-opportunity-scan → OMEGA memory
  → dashboard card (read-only, no sends without approval).

## Existing MCP notes
- `~/workspace/ai-tools/MCP_CONNECTORS.md` — connector inventory to reuse.
- The bridge (`bridge/omega_bridge.py`) already exposes the same permission
  model (GREEN/YELLOW/RED) over HTTP; the MCP layer must enforce the same
  gates server-side, never client-side only.
