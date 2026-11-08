#!/usr/bin/env python3
"""OMEGA AI — bridge between the dashboard/Electron shell and OMEGA CORE.

Stdlib only: no pip install needed. Serves the dashboard and a small JSON API
on 127.0.0.1:8471.

Endpoints:
  GET  /          dashboard (dashboard/index.html)
  GET  /status    core health: supervisor importable, memory count, agents, projects, disk
  GET  /agents    the 8-agent registry (core/agent-registry.json)
  GET  /memory    SQLite memory DB count + latest entry
  GET  /memory/search?q=...[&limit=N]  LIKE search over memory_entries
  GET  /memory?id=N                     one memory entry by id (404 when absent)
  POST /run       dry-run pipeline (Phase 4): real supervisor classification
                  (classify_task — deterministic keyword rules, no LLM, no
                  writes) + per-step status. Without an API key every
                  execution step is honestly reported "blocked: no API key"
                  and nothing is executed. With OPENROUTER_API_KEY present,
                  runs the supervisor for real (run_project) and returns its
                  state summary. Never fakes a run.
  GET  /windows/status     Windows agent health (Phase 7; needs the agent
                  token in the bridge process env, else "not-configured").
  GET  /windows/screenshot Windows desktop PNG (Phase 7; same token rule).
  POST /windows/task       run a multi-step Windows task (Phase 6/7):
                  {"name": "...", "steps": [...]} — same step semantics as
                  windows-agent/task_runner.py. Steps are logged; screenshots
                  land in windows-agent/shots/.

Run:  python3 ~/workspace/omega-ai/bridge/omega_bridge.py
Then: open http://127.0.0.1:8471/ in a browser.
Hosting: Render sets PORT itself and needs 0.0.0.0 — run with HOST=0.0.0.0.
The dashboard may live on another origin (Cloudflare Pages) — the bridge
answers CORS for GET endpoints and the dashboard takes its API base from
`?api=https://<render-url>`. No keys here: never put .env on a host.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import windows_client

ROOT = Path(__file__).resolve().parent.parent
CC = Path.home() / "workspace" / "YAHYA_AI_COMMAND_CENTER"
DASHBOARD = ROOT / "dashboard" / "index.html"
REGISTRY = ROOT / "core" / "agent-registry.json"
SCHEMA = ROOT / "core" / "memory-schema.sql"
DB_PATH = ROOT / "data" / "omega.db"
# Local default: 127.0.0.1:8471. Hosting (Render) sets PORT itself and
# requires 0.0.0.0 — honour HOST/PORT env vars; defaults keep local intact.
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8471"))

# The Command Center's venv holds its deps (litellm, langgraph, bs4...).
# Add its site-packages so the supervisor import works even when the bridge
# runs under the system python3. Stdlib-only bridge; third-party only via venv.
VENV_SITE = CC / ".venv" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
if VENV_SITE.is_dir():
    sys.path.insert(0, str(VENV_SITE))

sys.path.insert(0, str(CC))
try:
    from core import supervisor as _sup  # noqa: F401  (import test only)
    SUPERVISOR_IMPORTABLE = True
    SUPERVISOR_ERROR = None
except Exception as e:  # noqa: BLE001
    SUPERVISOR_IMPORTABLE = False
    SUPERVISOR_ERROR = f"{type(e).__name__}: {e}"


def load_registry() -> dict:
    try:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return {"agents": [], "error": str(e)}


def ensure_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    conn.commit()
    return conn


def memory_count() -> tuple[int, str | None]:
    try:
        conn = ensure_db()
        n = conn.execute("SELECT COUNT(*) FROM memory_entries").fetchone()[0]
        row = conn.execute(
            "SELECT created_at FROM memory_entries ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return n, (row[0] if row else None)
    except Exception:  # noqa: BLE001
        return 0, None


def memory_search(query: str, limit: int = 20) -> list[dict]:
    """LIKE search over memory_entries titles + bodies (newest first)."""
    conn = ensure_db()
    rows = conn.execute(
        "SELECT id, kind, title, body, source, created_at FROM memory_entries "
        "WHERE title LIKE ? OR body LIKE ? ORDER BY id DESC LIMIT ?",
        (f"%{query}%", f"%{query}%", limit),
    ).fetchall()
    conn.close()
    keys = ("id", "kind", "title", "body", "source", "created_at")
    return [dict(zip(keys, r)) for r in rows]


def memory_get(entry_id: int) -> dict | None:
    conn = ensure_db()
    row = conn.execute(
        "SELECT id, kind, title, body, source, created_at FROM memory_entries WHERE id = ?",
        (entry_id,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return dict(zip(("id", "kind", "title", "body", "source", "created_at"), row))


def record_run(task: str, chosen_agent: str) -> int | None:
    """Persist a bridge /run request in OUR memory DB (never in the CC).

    The run is recorded as a task under the OMEGA AI project, status
    'waiting' (waiting for the API key when none is present). Returns the
    task id, or None if the write fails (the run still answers honestly).
    """
    try:
        conn = ensure_db()
        row = conn.execute(
            "SELECT id FROM projects WHERE name = ?", ("OMEGA AI",)).fetchone()
        if row is None:
            cur = conn.execute(
                "INSERT INTO projects (name, objective, status) VALUES (?, ?, ?)",
                ("OMEGA AI",
                 "Autonomous AI agent operating system — Arabic-first, 8 agents, permission gates, persistent memory",
                 "running"))
            project_id = cur.lastrowid
        else:
            project_id = row[0]
        cur = conn.execute(
            "INSERT INTO tasks (project_id, agent_id, title, status) VALUES (?, ?, ?, ?)",
            (project_id, chosen_agent, task[:200], "waiting"))
        task_id = cur.lastrowid
        conn.execute(
            "INSERT INTO activity_log (actor, action, detail) VALUES (?, ?, ?)",
            ("bridge", "run-request",
             f"task_id={task_id} agent={chosen_agent} task={task[:200]}"))
        conn.commit()
        conn.close()
        return task_id
    except Exception:  # noqa: BLE001 — recording must never break the answer
        return None


def cc_projects() -> list[dict]:
    """Projects already present in the Command Center (read-only)."""
    out: list[dict] = []
    pdir = CC / "projects" / "active"
    if pdir.is_dir():
        for d in sorted(pdir.iterdir()):
            if d.is_dir():
                out.append({"name": d.name, "path": str(d)})
    return out


def disk_free_gb() -> float | None:
    try:
        st = os.statvfs(str(Path.home()))
        return round(st.f_bavail * st.f_frsize / 1e9, 1)
    except Exception:  # noqa: BLE001
        return None


def llm_key_present() -> bool:
    if os.environ.get("OPENROUTER_API_KEY"):
        return True
    env = CC / ".env"
    if env.is_file():
        return "OPENROUTER_API_KEY=" in env.read_text(errors="ignore")
    return False


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep stdout clean
        pass

    def _cors(self) -> None:
        # Dashboard may be hosted on another origin (Cloudflare Pages).
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):  # noqa: N802
        parts = urlsplit(self.path)
        path, qs = parts.path, parse_qs(parts.query)
        if path in ("/", "/index.html"):
            data = DASHBOARD.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/status":
            n, _ = memory_count()
            self._json(200, {
                "version": "0.1.0",
                "core": {
                    "path": str(CC),
                    "supervisor_importable": SUPERVISOR_IMPORTABLE,
                    "supervisor_error": SUPERVISOR_ERROR,
                    "memory_records": n,
                    "projects": cc_projects(),
                    "disk_free_gb": disk_free_gb(),
                    "llm_key_present": llm_key_present(),
                },
                "agents": load_registry().get("agents", []),
            })
            return
        if path == "/agents":
            self._json(200, load_registry())
            return
        if path == "/memory/search":
            q = (qs.get("q", [""])[0] or "").strip()
            if not q:
                self._json(400, {"error": "missing-q",
                                 "message": "GET /memory/search?q=... required."})
                return
            try:
                limit = int(qs.get("limit", ["20"])[0])
            except ValueError:
                limit = 20
            limit = max(1, min(limit, 100))
            results = memory_search(q, limit)
            self._json(200, {"q": q, "limit": limit,
                             "count": len(results), "results": results})
            return
        if path == "/memory":
            if "id" in qs:
                try:
                    entry_id = int(qs["id"][0])
                except ValueError:
                    self._json(400, {"error": "invalid-id",
                                     "message": "id must be an integer."})
                    return
                entry = memory_get(entry_id)
                if entry is None:
                    self._json(404, {"error": "not-found",
                                     "message": f"No memory entry with id {entry_id}."})
                    return
                self._json(200, entry)
                return
            n, latest = memory_count()
            self._json(200, {"db_path": str(DB_PATH), "count": n, "latest": latest})
            return
        if path == "/windows/status":
            code, raw = windows_client.windows_call("GET", "/status")
            if code == 200:
                try:
                    self._json(200, json.loads(raw.decode("utf-8")))
                except Exception:  # noqa: BLE001
                    self._json(502, {"error": "agent-bad-response",
                                     "detail": raw[:300].decode("utf-8", "replace")})
            elif code == 401:
                try:
                    self._json(401, json.loads(raw.decode("utf-8")))
                except Exception:  # noqa: BLE001
                    self._json(401, {"error": "not-configured"})
            else:
                self._json(502, {"error": "agent-unreachable",
                                 "http_code": code,
                                 "detail": raw[:300].decode("utf-8", "replace")})
            return
        if path == "/windows/screenshot":
            code, raw = windows_client.windows_call("GET", "/screenshot", timeout=60)
            if code == 200 and raw[:8] == b"\x89PNG\r\n\x1a\n":
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self._cors()
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
            elif code == 401:
                try:
                    self._json(401, json.loads(raw.decode("utf-8")))
                except Exception:  # noqa: BLE001
                    self._json(401, {"error": "not-configured"})
            else:
                self._json(502, {"error": "agent-unreachable",
                                 "http_code": code,
                                 "detail": raw[:300].decode("utf-8", "replace")})
            return
        self._json(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        parts = urlsplit(self.path)
        path = parts.path
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:  # noqa: BLE001
            self._json(400, {"error": "invalid-json",
                             "message": "POST needs a JSON body."})
            return
        if path == "/windows/task":
            if not isinstance(payload, dict) or not isinstance(payload.get("steps"), list):
                self._json(400, {"error": "invalid-task",
                                 "message": "POST /windows/task needs {\"name\": \"...\", \"steps\": [...]}."})
                return
            shots_dir = ROOT / "windows-agent" / "shots"
            results, log_lines = windows_client.run_windows_task(payload, str(shots_dir))
            try:  # append to the shared task log; never break the answer
                log_path = ROOT / "windows-agent" / "task_log.jsonl"
                with open(log_path, "a", encoding="utf-8") as fh:
                    fh.write("\n".join(log_lines) + "\n")
            except Exception:  # noqa: BLE001
                pass
            done = sum(1 for r in results if r["ok"])
            self._json(200, {"name": payload.get("name", "unnamed"),
                             "steps_ok": done, "steps_total": len(results),
                             "results": results})
            return
        if path != "/run":
            self._json(404, {"error": "not found"})
            return
        task = (payload.get("task") or "").strip() if isinstance(payload, dict) else ""
        if not task:
            self._json(400, {"error": "missing-task",
                             "message": "POST /run needs {\"task\": \"...\"}."})
            return
        if not SUPERVISOR_IMPORTABLE:
            self._json(500, {"error": "supervisor-not-importable",
                             "detail": SUPERVISOR_ERROR,
                             "message": "The supervisor could not be imported; /run cannot plan."})
            return
        # Real supervisor, dry-run: classify_task is deterministic keyword
        # rules — no LLM, no key, no writes into the Command Center.
        sup_mod = globals().get("_sup")
        try:
            sup = sup_mod.Supervisor(root=CC)
            plan = sup.classify_task(task)
        except Exception as e:  # noqa: BLE001
            self._json(500, {"error": "classify-failed",
                             "detail": f"{type(e).__name__}: {e}"})
            return
        workers = [a for a in plan if a in ("coder", "creative", "analyst")]
        chosen = workers[0] if workers else "researcher"
        task_id = record_run(task, chosen)
        if llm_key_present():
            # Key present: execute for real through the supervisor pipeline.
            # NOTE (2026-11-07): this branch is NOT testable yet — no key
            # exists anywhere, so it has never run. It is the intended
            # Phase 4 execution path once Yahya adds the free key.
            try:
                state = sup.run_project(task[:60], task)
                self._json(200, {
                    "task": task,
                    "task_id": task_id,
                    "executed": True,
                    "llm_key_present": True,
                    "plan": plan,
                    "chosen_agent": chosen,
                    "agent_status": state.get("agent_status", {}),
                    "errors": state.get("errors", []),
                    "decisions": state.get("decisions", []),
                    "requires_human_approval": state.get("requires_human_approval", False),
                    "pending_approvals": state.get("pending_approvals", []),
                    "report_chars": len(state.get("report", "")),
                })
            except Exception as e:  # noqa: BLE001
                self._json(500, {"error": "run-failed",
                                 "detail": f"{type(e).__name__}: {e}",
                                 "plan": plan, "chosen_agent": chosen})
            return
        # No key: honest dry-run. Nothing was executed; every execution step
        # is reported blocked. run_project is deliberately NOT called here:
        # it would burn failing LLM calls and write partial project artifacts
        # into the Command Center. Add a free OpenRouter key to
        # YAHYA_AI_COMMAND_CENTER/.env to unlock execution.
        steps = [{"agent": "classify", "status": "done",
                  "detail": "plan built by the real supervisor (keyword rules, no LLM)"}]
        for agent in plan:
            steps.append({"agent": agent, "status": "blocked",
                          "reason": "no API key — OPENROUTER_API_KEY missing from .env"})
        self._json(200, {
            "task": task,
            "task_id": task_id,
            "executed": False,
            "llm_key_present": False,
            "plan": plan,
            "chosen_agent": chosen,
            "steps": steps,
            "message": "Dry-run only: plan built by the real supervisor. Execution is blocked — "
                       "no API key. Add a free OpenRouter key to YAHYA_AI_COMMAND_CENTER/.env "
                       "to run agents. Nothing was executed and nothing was faked.",
        })


if __name__ == "__main__":
    ensure_db()
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"OMEGA AI bridge on http://{HOST}:{PORT}/  (Ctrl+C to stop)")
    print(f"core: {CC}  supervisor importable: {SUPERVISOR_IMPORTABLE}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
