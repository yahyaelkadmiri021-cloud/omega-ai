# Muse Windows Agent — OMEGA AI desktop control

Small Python agent that runs on Yahya's Windows 10 PC and lets OMEGA AI see the
screen, move the mouse, type, open apps and run shell commands — through a
token-authenticated local HTTP API. Port **8472** (the OMEGA bridge uses 8471).

- Real backend: **PyAutoGUI** (free, open source) — screenshots, mouse, keyboard.
- Mock backend: if PyAutoGUI is missing, the agent still starts and records
  calls, but executes nothing (used for testing on machines without a display).
- Cost: **$0**. Python + PyAutoGUI + Tailscale free tier only.

## Run on Windows

Prerequisite: **Python 3.10+** installed (check with `python --version` in
PowerShell; if missing, install it from python.org first — Yahya's tap).

### Quick start (recommended): double-click `start-agent.bat`

The launcher does everything automatically: it checks Python (downloads and
installs it silently if missing), installs the requirements, binds the agent
to this PC's Tailscale IP, and reuses or creates the token (saved in
`token.txt` next to the launcher). When it starts it prints the token —
send that ONE line to Muse so it can connect. The token only works inside
your private Tailscale network; to revoke it, delete `token.txt` and run the
launcher again.

### Manual setup (same result, step by step)

```powershell
cd <folder where you extracted omega-ai>\windows-agent
pip install -r requirements.txt
```

### 1. Create the token (on YOUR machine only — never in chat)

Generate a strong random token in the same PowerShell window, then keep that
window open for step 2:

```powershell
$token = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 40 | ForEach-Object { [char]$_ })
$env:MUSE_AGENT_TOKEN = $token
```

The token is the only key to the agent, and it has to reach Muse somehow:
with the launcher it is saved in `token.txt` on your PC and printed once at
startup — send that ONE line to Muse so it can connect. It is a random
one-purpose token that only works inside your private Tailscale network.
Muse uses it only to call the agent and never writes it to a file or to
memory. To revoke it, delete `token.txt` and run the launcher again
(manual flow: close the PowerShell window and set a new token).

### 2. Start the agent

```powershell
python agent.py
```

You should see:

```
muse-windows-agent v0.1.0 — backend=pyautogui — listening on http://127.0.0.1:8472 (localhost only ...)
```

Stop it any time with **Ctrl+C**.

### 3. Verify it answers (same PowerShell window, so the token is set)

```powershell
curl.exe http://127.0.0.1:8472/status -H "Authorization: Bearer $env:MUSE_AGENT_TOKEN"
```

Expected: HTTP 200 with `"backend": "pyautogui"` and the screen size.
A screenshot test:

```powershell
curl.exe http://127.0.0.1:8472/screenshot -H "Authorization: Bearer $env:MUSE_AGENT_TOKEN" -o shot.png
```

## API (all JSON unless noted; every request needs the Bearer token)

| Method | Path | Permission | Body / notes |
|---|---|---|---|
| GET | `/status` | GREEN | version, platform, screen size, backend |
| GET | `/screenshot` | GREEN | returns PNG bytes |
| GET | `/log?limit=50` | GREEN | recent action-log entries |
| POST | `/mouse` | YELLOW | `{"action": "move"\|"click"\|"double_click"\|"scroll", "x": N, "y": N, "button": "left", "dy": N}` |
| POST | `/keyboard` | YELLOW | `{"action": "type", "text": "..."}` / `{"action": "press", "key": "enter"}` / `{"action": "hotkey", "keys": ["ctrl", "s"]}` |
| POST | `/open-app` | YELLOW | `{"name": "notepad"}` (program name or file path) |
| POST | `/shell` | **RED** | `{"command": "...", "shell": "powershell"\|"cmd", "approved": true}` — without `"approved": true` it returns **403** and the attempt is logged |

Errors: `401` missing/wrong token, `403` RED gate without approval,
`400` bad request, `404` unknown endpoint, `500` internal error.

## Security notes (read before running)

- **Binds localhost only** (`127.0.0.1`). Nothing is reachable from the network.
  Later, the operator may set `MUSE_AGENT_HOST` to the PC's Tailscale IP so
  Muse can reach it over the private Tailscale channel Yahya approves.
  Binding to `0.0.0.0` is refused by the agent on purpose.
- **Token auth on every request.** No token is baked into the code and the
  token is never written to the log. If `MUSE_AGENT_TOKEN` is not set, the
  agent refuses to start.
- **RED gate.** Shell / install / delete / admin actions need
  `"approved": true` in the request, and are always logged in full detail.
  YELLOW actions (mouse/keyboard/open-app) are allowed but logged and flagged;
  sensitive use still needs Yahya's confirmation through the OMEGA gate.
- **Log file:** `actions.jsonl` next to `agent.py` — one JSON line per action
  (time, endpoint, permission, parameters with secrets redacted, result).
  The token never appears in it.
- **Failsafe:** PyAutoGUI's failsafe stays ON — shoving the mouse into a screen
  corner aborts the current PyAutoGUI action.
- **Nothing leaves the machine** except through the Tailscale channel Yahya
  approves. The agent makes no outgoing connections of its own.

## OMEGA integration (Phase 7 of the Windows Control brief)

The OMEGA bridge will call this agent over the Tailscale channel:
dashboard → agents → bridge → `http://<tailscale-ip>:8472/...` → results + logs
back to the dashboard. Task records stay in the OMEGA SQLite memory; the
agent's own `actions.jsonl` is the on-machine audit trail.

## Troubleshooting

- `ERROR: MUSE_AGENT_TOKEN is not set` — set the token in the same PowerShell
  window first (step 1 above).
- `401` — the token in the request does not match the one the agent started with.
- `backend: mock` in `/status` — PyAutoGUI is not installed or has no display;
  run `pip install -r requirements.txt` and restart.
- Port 8472 busy — another copy is already running; stop it first (Ctrl+C).
