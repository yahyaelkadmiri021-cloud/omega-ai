#!/usr/bin/env python3
"""OMEGA AI — Windows task runner (Phase 6).

Executes a multi-step task against the Windows agent (PyAutoGUI backend)
and logs every step. Stdlib only.

Usage:
    MUSE_AGENT_TOKEN=<token> python3 task_runner.py task.json [--log log.jsonl] [--shots shots/]

Task JSON: {"name": "...", "steps": [ ... ]} where each step is one of:
    {"action": "open-app", "name": "notepad"}
    {"action": "type", "text": "..."}
    {"action": "press", "key": "enter"}
    {"action": "hotkey", "keys": ["alt", "f4"]}
    {"action": "mouse", "sub": "move", "x": 960, "y": 540}
    {"action": "shell", "command": "...", "approved": true}
    {"action": "screenshot", "save": "step.png"}
    {"action": "sleep", "seconds": 2}
    {"action": "status"}

Env:
    MUSE_AGENT_TOKEN  (required — passed transiently, never stored in files)
    MUSE_AGENT_HOST   (default 100.80.98.81 — the Tailscale IP)
    MUSE_AGENT_PORT   (default 8473 — the live agent; 8472 is the stale one)

The log is JSONL: one line per step with ts, index, action, endpoint,
http_code, ok, and a short result summary. Screenshots are saved as PNGs
under --shots (default: <script dir>/shots/). Nothing secret is logged:
the token is never written to the log or to stdout.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

TOKEN = os.environ.get("MUSE_AGENT_TOKEN", "").strip()
HOST = os.environ.get("MUSE_AGENT_HOST", "100.80.98.81").strip() or "100.80.98.81"
PORT = os.environ.get("MUSE_AGENT_PORT", "8473").strip() or "8473"
BASE = f"http://{HOST}:{PORT}"


def _tunnel_proxy_url():
    """The tailnet is reachable ONLY via the runtime tunnel proxy (port 3130).

    HTTPS_PROXY points at the general egress proxy (port 3128), which does
    NOT route private tailnet IPs — using it gives 'Remote end closed
    connection'. Derive the tunnel proxy the same way the shell does:
    ${HTTPS_PROXY%:*}:3130 (same host + credentials, port 3130).
    """
    https_proxy = os.environ.get("HTTPS_PROXY", "").strip()
    if not https_proxy:
        return ""
    return https_proxy.rsplit(":", 1)[0] + ":3130"


_OPENER = None


def _opener():
    global _OPENER
    if _OPENER is None:
        tunnel = _tunnel_proxy_url()
        if tunnel:
            proxy = urllib.request.ProxyHandler({"http": tunnel,
                                                 "https": tunnel})
        else:
            proxy = urllib.request.ProxyHandler({})
        _OPENER = urllib.request.build_opener(proxy)
    return _OPENER


def _req(method, path, body=None, timeout=30):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with _opener().open(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # connection refused, timeout, ...
        return 0, str(e).encode("utf-8")


def _short(raw, limit=300):
    try:
        text = raw.decode("utf-8", "replace")
    except Exception:
        text = repr(raw)
    text = " ".join(text.split())
    return text[:limit]


def run_task(task, log_fh, shots_dir):
    name = task.get("name", "unnamed")
    steps = task.get("steps", [])
    print(f"task: {name} ({len(steps)} steps) -> {BASE}")
    results = []
    for i, step in enumerate(steps):
        action = step.get("action", "")
        ts = datetime.now(timezone.utc).isoformat()
        ok = False
        code = 0
        summary = ""
        if action == "sleep":
            secs = float(step.get("seconds", 1))
            time.sleep(secs)
            ok, code, summary = True, 200, f"slept {secs}s"
        elif action == "screenshot":
            save = step.get("save", f"step_{i:02d}.png")
            code, raw = _req("GET", "/screenshot", timeout=60)
            if code == 200 and raw[:8] == b"\x89PNG\r\n\x1a\n":
                path = os.path.join(shots_dir, save)
                with open(path, "wb") as fh:
                    fh.write(raw)
                ok, summary = True, f"PNG {len(raw)} B -> {path}"
            else:
                summary = f"screenshot failed: {_short(raw)}"
        elif action == "open-app":
            code, raw = _req("POST", "/open-app",
                             {"name": step.get("name", "")})
            ok = code == 200
            summary = _short(raw)
        elif action in ("type", "press", "hotkey"):
            body = {"action": action}
            if action == "type":
                body["text"] = step.get("text", "")
            elif action == "press":
                body["key"] = step.get("key", "")
            else:
                body["keys"] = step.get("keys", [])
            code, raw = _req("POST", "/keyboard", body)
            ok = code == 200
            summary = _short(raw)
        elif action == "mouse":
            body = {"action": step.get("sub", "move"),
                    "x": step.get("x", 0), "y": step.get("y", 0)}
            code, raw = _req("POST", "/mouse", body)
            ok = code == 200
            summary = _short(raw)
        elif action == "shell":
            body = {"command": step.get("command", ""),
                    "approved": bool(step.get("approved", False))}
            code, raw = _req("POST", "/shell", body, timeout=120)
            ok = code == 200
            summary = _short(raw)
        elif action == "status":
            code, raw = _req("GET", "/status")
            ok = code == 200
            summary = _short(raw)
        else:
            summary = f"unknown action: {action}"
        entry = {"ts": ts, "task": name, "index": i, "action": action,
                 "http_code": code, "ok": ok, "summary": summary}
        log_fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        log_fh.flush()
        results.append(entry)
        print(f"  [{i}] {action}: http={code} ok={ok} :: {summary[:120]}")
        if not ok and step.get("stop_on_error", True):
            print("  stopping: step failed and stop_on_error is set")
            break
    done = sum(1 for r in results if r["ok"])
    print(f"result: {done}/{len(results)} steps ok")
    return results


def main():
    if not TOKEN:
        print("ERROR: MUSE_AGENT_TOKEN is not set.", file=sys.stderr)
        return 2
    ap = argparse.ArgumentParser(description="Run a Windows-agent task.")
    ap.add_argument("task", help="task JSON file")
    ap.add_argument("--log", default=None,
                    help="JSONL log file (default: task_log.jsonl next to this script)")
    ap.add_argument("--shots", default=None,
                    help="directory for screenshots (default: shots/ next to this script)")
    args = ap.parse_args()
    here = os.path.dirname(os.path.abspath(__file__))
    log_path = args.log or os.path.join(here, "task_log.jsonl")
    shots_dir = args.shots or os.path.join(here, "shots")
    os.makedirs(shots_dir, exist_ok=True)
    with open(args.task, "r", encoding="utf-8") as fh:
        task = json.load(fh)
    with open(log_path, "a", encoding="utf-8") as log_fh:
        results = run_task(task, log_fh, shots_dir)
    failed = [r for r in results if not r["ok"]]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
