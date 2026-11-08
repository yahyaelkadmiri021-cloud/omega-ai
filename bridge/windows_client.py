"""OMEGA AI bridge — Windows agent client (Phase 7).

Self-contained stdlib client for the Windows desktop-control agent
(PyAutoGUI backend, token-authenticated, on the Tailscale tailnet).
Used by omega_bridge.py for the /windows/* endpoints.

The agent is reachable ONLY via the runtime tunnel proxy (port 3130);
HTTPS_PROXY points at the general egress proxy (port 3128), which does
NOT route private tailnet IPs. The tunnel URL is derived the same way
the shell does: ${HTTPS_PROXY%:*}:3130.

Credentials: the agent token comes ONLY from the bridge process env
(MUSE_AGENT_TOKEN) at request time — never from a file, never in code,
never in a log. When the token is absent the client reports
configured=False and the endpoints answer honestly instead of failing.
"""
from __future__ import annotations

import io
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

DEFAULT_HOST = "100.80.98.81"   # desktop-t96e77e (Tailscale)
DEFAULT_PORT = "8472"           # the live agent (folder omega-ai-v0.1.3 (9), since 2026-11-07 22:40; 8473 is dead)


def windows_config():
    """Token + target, read from the process env at call time."""
    token = os.environ.get("MUSE_AGENT_TOKEN", "").strip()
    host = os.environ.get("MUSE_AGENT_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST
    port = os.environ.get("MUSE_AGENT_PORT", DEFAULT_PORT).strip() or DEFAULT_PORT
    return token, host, port, f"http://{host}:{port}"


def _tunnel_proxy_url():
    https_proxy = os.environ.get("HTTPS_PROXY", "").strip()
    if not https_proxy:
        return ""
    return https_proxy.rsplit(":", 1)[0] + ":3130"


def windows_call(method, path, body=None, timeout=60):
    """Call the Windows agent. Returns (http_code, raw_bytes).

    http_code 0 = transport failure (agent down / proxy refused).
    When no token is configured, returns (401, b'{"error":"not-configured"...}').
    """
    token, _host, _port, base = windows_config()
    if not token:
        return 401, json.dumps({
            "error": "not-configured",
            "message": "MUSE_AGENT_TOKEN is not set in the bridge process env. "
                       "Start the bridge with the token to enable /windows/*.",
        }).encode("utf-8")
    tunnel = _tunnel_proxy_url()
    proxy = urllib.request.ProxyHandler({"http": tunnel, "https": tunnel}) \
        if tunnel else urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:  # noqa: BLE001
        return 0, str(e).encode("utf-8")


def _short(raw, limit=300):
    try:
        text = raw.decode("utf-8", "replace")
    except Exception:
        text = repr(raw)
    return " ".join(text.split())[:limit]


def run_windows_task(task, shots_dir):
    """Execute a task (same step semantics as windows-agent/task_runner.py).

    Returns (results, log_lines): results is a list of step dicts
    {ts, index, action, http_code, ok, summary}; log_lines are the JSONL
    lines (the caller may append them to task_log.jsonl). Screenshots are
    saved as PNGs under shots_dir. The token is never written anywhere.
    """
    name = task.get("name", "unnamed")
    steps = task.get("steps", [])
    results, log_lines = [], []
    for i, step in enumerate(steps):
        action = step.get("action", "")
        ts = datetime.now(timezone.utc).isoformat()
        ok, code, summary = False, 0, ""
        if action == "sleep":
            secs = float(step.get("seconds", 1))
            time.sleep(secs)
            ok, code, summary = True, 200, f"slept {secs}s"
        elif action == "screenshot":
            save = step.get("save", f"step_{i:02d}.png")
            code, raw = windows_call("GET", "/screenshot", timeout=60)
            if code == 200 and raw[:8] == b"\x89PNG\r\n\x1a\n":
                os.makedirs(shots_dir, exist_ok=True)
                path = os.path.join(shots_dir, save)
                with open(path, "wb") as fh:
                    fh.write(raw)
                ok, summary = True, f"PNG {len(raw)} B -> {path}"
            else:
                summary = f"screenshot failed: {_short(raw)}"
        elif action == "open-app":
            code, raw = windows_call("POST", "/open-app",
                                     {"name": step.get("name", "")})
            ok, summary = code == 200, _short(raw)
        elif action in ("type", "press", "hotkey"):
            body = {"action": action}
            if action == "type":
                body["text"] = step.get("text", "")
            elif action == "press":
                body["key"] = step.get("key", "")
            else:
                body["keys"] = step.get("keys", [])
            code, raw = windows_call("POST", "/keyboard", body)
            ok, summary = code == 200, _short(raw)
        elif action == "mouse":
            body = {"action": step.get("sub", "move"),
                    "x": step.get("x", 0), "y": step.get("y", 0)}
            code, raw = windows_call("POST", "/mouse", body)
            ok, summary = code == 200, _short(raw)
        elif action == "shell":
            body = {"command": step.get("command", ""),
                    "approved": bool(step.get("approved", False))}
            code, raw = windows_call("POST", "/shell", body, timeout=120)
            ok, summary = code == 200, _short(raw)
        elif action == "status":
            code, raw = windows_call("GET", "/status")
            ok, summary = code == 200, _short(raw)
        else:
            summary = f"unknown action: {action}"
        entry = {"ts": ts, "task": name, "index": i, "action": action,
                 "http_code": code, "ok": ok, "summary": summary}
        results.append(entry)
        log_lines.append(json.dumps(entry, ensure_ascii=False))
        if not ok and step.get("stop_on_error", True):
            break
    return results, log_lines
