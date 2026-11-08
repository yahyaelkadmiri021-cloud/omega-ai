# OMEGA AI — DECISIONS

Numbered, dated, with rationale. A decision is changed only by adding a new
entry that supersedes it — never by silently editing an old one.

## D-01 — New home: `~/workspace/omega-ai/` (2026-11-07)
**Decision:** the desktop build lives in its own folder `omega-ai/`.
**Rationale:** `~/workspace/omega/` already holds the live OMEGA income-research
system. Same name, different product. A shared folder would risk overwriting
live research, plans and applications. The master prompt's rule 7 ("never
delete, overwrite or replace existing projects without explicit permission")
forces the separation.
**Supersedes:** nothing.

## D-02 — Two-layer architecture: Python core + Electron shell (2026-11-07)
**Decision:** Layer 1 = the existing Python Command Center as OMEGA CORE
(runs now, zero install). Layer 2 = Electron + React + TypeScript shell
(target for Windows packaging; scaffolded now, installed when quota allows).
**Rationale:** ~60% of the spec already exists as tested Python (supervisor,
7 agents, permissions, SQLite memory, tools). Rebuilding it in TypeScript
from zero wastes that work and violates "integrate, don't rebuild". The
bridge (`bridge/omega_bridge.py`, stdlib-only) lets both layers share one
agent registry, one memory schema and one permission model, so no work is
thrown away when the Electron shell lands.
**Supersedes:** nothing. The master prompt allows improving the architecture
when justified and documented — this is that case.

## D-03 — Dashboard v0.1 is dependency-free HTML/JS (2026-11-07)
**Decision:** the first dashboard is plain HTML/JS served by the bridge,
no React build step, no `node_modules`.
**Rationale:** disk headroom is ~54MB; React + Electron install (~250MB)
fails today. A zero-dependency dashboard runs in a browser NOW and loads
unchanged inside Electron later. React+TypeScript remains the target for
the packaged app (Phase 3/11).
**Supersedes:** nothing.

## D-04 — Desktop Commander + n8n are pluggable modules, not day-one deps (2026-11-07)
**Decision:** define the MCP interface contract + stubs now; live integration
happens on a Windows machine where they can be installed and tested.
**Rationale:** Desktop Commander is a Windows/macOS tool; n8n is not
installed here. Claiming either as "integrated" without installing and
testing it would violate "never claim a tool is installed, connected or
working without testing it".
**Supersedes:** nothing.

## D-05 — Model layer: provider-configurable, keys in `.env` only (2026-11-07)
**Decision:** no hardcoded keys, no keys in git, no keys in chat. $0 default
is OpenRouter `:free` models via LiteLLM (the Command Center's existing
design). Without a key the system honestly reports "LLM not configured".
**Rationale:** standing rules (credentials are Yahya's alone) + the master
prompt's section 10. The executor already records unbacked operations as
BLOCKED instead of faking success — keep that honesty everywhere.
**Supersedes:** nothing.

## D-06 — Scope default: personal single-user build (2026-11-07)
**Decision:** build for Yahya alone on his machine unless he picks the
sellable-platform option (open question from the 2026-11-07 hub thread).
**Rationale:** a sellable multi-user platform needs accounts, payments,
hosting and legal work that cannot be decided for him. The personal build
is fully useful on its own and becomes the foundation if he later chooses
to sell it.
**Supersedes:** nothing.

## D-07 — Permissions mirror the Command Center (2026-11-07)
**Decision:** GREEN (auto: search, read, calculate, summarise) / YELLOW
(needs his confirmation: publish, email, upload, write outside workspace) /
RED (explicit approval always: pay, buy, delete, passwords/keys).
**Rationale:** already implemented and tested in `core/permissions.py`;
identical to the standing rules (money, credentials, irreversible deletes
are his alone). One permission model across both layers.
**Supersedes:** nothing.

## D-08 — Memory: SQLite, seeded from `muse_omega/MUSE_MEMORY/` (2026-11-07)
**Decision:** one SQLite schema (`core/memory-schema.sql`) for projects,
decisions, task history, tools, errors and research; seeded from the real
2026-09-29 memory files, never invented rows.
**Rationale:** the master prompt's section 7 + the existing memory design
(`memory/long_term.py`). Empty tables stay empty and marked as such.
**Supersedes:** nothing.

## D-09 — Project Manager: deterministic board, LLM only for advice (2026-11-07)
**Decision:** the PM agent builds its task board WITHOUT any LLM call
(from live state + TASKS.md); the LLM is used only for a one-line "next
action" recommendation, wrapped so a missing key falls back to a plain
deterministic line instead of failing the board.
**Rationale:** the board is coordination data, not generation — it must work
even with no key, and a missing key must never block the pipeline. The PM
runs last in every project so its board reflects the full run.
**Supersedes:** nothing.

## D-10 — Latent `_build_report` crash: fixed defensively (2026-11-07)
**Decision:** `state["code"]` starts as `[]` in `new_state()` and becomes a
dict only when coder succeeds; `_build_report` assumed dict and crashed
every run where coder failed or was absent. Fixed to handle both shapes
(+ `code_files` for board files). Backup kept
(`core/supervisor.py.bak_20261107_0915`).
**Rationale:** found by the PM full-pipeline dry run (no key). A crash in
the report step would have hidden every honest failure behind a traceback.
**Supersedes:** nothing.

## D-11 — Free hosting: hybrid Render + Cloudflare Pages (+ GitHub Releases) (2026-11-07)
**Decision:** the hosted form of OMEGA AI is a hybrid, all $0, no card:
Render Free runs the light stdlib bridge; Cloudflare Pages hosts the static
dashboard (called with `?api=<render-url>`); a future Windows `.exe` ships
via GitHub Releases. The full agent core stays on Yahya's machine.
**Rationale:** research (`hosting-research-2026-11-07.md`, official pricing
pages, Oct–Nov 2026) found NO free host that keeps a Python backend awake
24/7 without sleep or a card. Render Free is the only always-on Python
backend without a card (512MB/0.1 CPU/750h/mo) but sleeps after 15 idle
minutes (~1 min wake; free UptimeRobot ping mitigates). Static hosts can't
run the bridge at all (10s serverless cap, no SQLite). Railway is a $5/30-day
trial then $1/mo — not permanent. Fly.io has no free tier for new accounts.
Deploy-prep built the same day: bridge honours HOST/PORT env + CORS on GET,
dashboard takes API base from `?api=`, `render.yaml` + `DEPLOY.md` written,
smoke test passed (200s + CORS + honest 503 on /run).
**Supersedes:** nothing. D-06 scope (personal build) unchanged — hosting is
for remote viewing, not a multi-user platform.

## D-12 — Form: web app hosted free, opened from the browser (2026-11-07)
**Decision:** OMEGA AI ships as a **web app hosted free** (Render bridge +
Cloudflare Pages dashboard), opened from the browser. The Windows `.exe`
stays a later option, not the form now.
**Rationale:** Yahya tapped «تطبيق ويب مستضاف مجاناً (تفتحو من المتصفح)»
09:48 +01, choosing the web form over the Windows `.exe`. Consequence: the
Render account step is now definitely required (it hosts the bridge); the
`.exe`/GitHub Releases path is deferred, not cancelled.
**Supersedes:** nothing (settles the form question left open in D-11).

## D-13 — Blanket project approval: what it covers and what it does NOT (2026-11-07)
**Decision:** Yahya's «موافق عل كل ما يخص المشرع» (~20:10 +01) is accepted as
approval to build, test, document and prepare everything concerning the OMEGA AI
+ Windows-control project (including the §10 universal tool-integration
authority: discover, select, connect and configure free tools).
**It does NOT cover:** money/purchases/subscriptions, credentials/API keys
(creation stays his; values never in chat), public publishing/live deployment,
sending as him, or irreversible deletions — each still needs his explicit
per-action tap, exactly as the OMEGA master prompt §3.10 and the Windows brief
§3.5/§10 require.
**Rationale:** a blanket yes must not be read as permission for the never-auto
items. The approval unblocks the build work; the taps that are his hands
(Tailscale approval, PowerShell output, OpenRouter key, GitHub/Render accounts,
running the Windows agent on his PC) stay his.
**Supersedes:** nothing.
