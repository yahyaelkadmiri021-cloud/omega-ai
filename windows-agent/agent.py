#!/usr/bin/env python3
"""Muse Windows Agent — OMEGA AI desktop control (Phase 2/3 preparation).

Stdlib-only HTTP layer (http.server). The real control backend is PyAutoGUI
(Windows); when PyAutoGUI is unavailable (e.g. a headless Linux VM) the agent
runs in MOCK mode: it records calls and returns generated data, and NEVER
executes shell commands or touches the real desktop.

Security (Windows Control Brief §3):
- Token auth on EVERY request: Authorization: Bearer <token>.
  The token comes ONLY from the MUSE_AGENT_TOKEN environment variable.
  No default token, no token in code, no token in logs.
- Binds 127.0.0.1 by default. MUSE_AGENT_HOST may name another local address
  (e.g. the Tailscale IP, set by the operator later). 0.0.0.0 is REFUSED.
- Permission model (same as OMEGA GREEN/YELLOW/RED):
  GREEN  — read-only: /, /status, /screenshot, /log.
  YELLOW — desktop actions: /mouse, /keyboard, /open-app (allowed, logged,
           flagged; sensitive use needs Yahya's confirmation via the OMEGA gate).
  RED    — /shell (and any install/delete/admin action): requires
           {"approved": true} in the request body, else 403. Approved RED
           requests are still logged in full detail.
- Every action is appended to actions.jsonl next to this file (never the token).

Run (Windows):
  pip install -r requirements.txt
  set MUSE_AGENT_TOKEN=<strong random value, created on that machine only>
  python agent.py
Verify:
  curl http://127.0.0.1:8472/status -H "Authorization: Bearer <token>"
"""

from __future__ import annotations

import hmac
import json
import os
import platform
import struct
import subprocess
import sys
import threading
import time
import zlib
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

VERSION = "0.1.0"
AGENT_NAME = "muse-windows-agent"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8472
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "actions.jsonl")
MAX_BODY_BYTES = 64 * 1024
MAX_LOG_RETURN = 200

# ---------------------------------------------------------------------------
# Permission model (same levels as OMEGA)
# ---------------------------------------------------------------------------
PERMISSIONS = {
    "/": "GREEN",
    "/status": "GREEN",
    "/screenshot": "GREEN",
    "/log": "GREEN",
    "/mouse": "YELLOW",
    "/keyboard": "YELLOW",
    "/open-app": "YELLOW",
    "/shell": "RED",
}

# Keys that must never appear in the log, even if a caller sends them.
SECRET_KEYS = {"token", "password", "passwd", "api_key", "apikey", "secret",
               "authorization", "auth"}

# ---------------------------------------------------------------------------
# Backend: real (PyAutoGUI) or mock
# ---------------------------------------------------------------------------
FORCE_BACKEND = os.environ.get("MUSE_AGENT_BACKEND", "").strip().lower()

try:
    if FORCE_BACKEND == "mock":
        raise ImportError("mock backend forced by MUSE_AGENT_BACKEND=mock")
    import pyautogui  # type: ignore
    BACKEND = "pyautogui"
    # Failsafe: moving the mouse to a screen corner aborts PyAutoGUI actions.
    pyautogui.FAILSAFE = True
except Exception:
    pyautogui = None  # type: ignore
    BACKEND = "mock"

MOCK_SCREEN = (1920, 1080)
_mock_calls: list = []
_mock_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _redact(params):
    """Deep-copy params, replacing secret-looking values."""
    if isinstance(params, dict):
        return {k: ("***REDACTED***" if k.lower() in SECRET_KEYS else _redact(v))
                for k, v in params.items()}
    if isinstance(params, list):
        return [_redact(v) for v in params]
    return params


_log_lock = threading.Lock()


def log_action(endpoint: str, level: str, params, ok: bool, result=None,
               error: str | None = None) -> None:
    entry = {
        "time": _now_iso(),
        "endpoint": endpoint,
        "permission": level,
        "params": _redact(params if params is not None else {}),
        "ok": ok,
        "result": result,
        "error": error,
    }
    line = json.dumps(entry, ensure_ascii=False)
    with _log_lock:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            # Logging must never break the request itself.
            pass


# ---------------------------------------------------------------------------
# Mock backend helpers (pure stdlib — no Pillow needed)
# ---------------------------------------------------------------------------
def _solid_png(width: int, height: int, rgb=(16, 32, 64)) -> bytes:
    """Minimal valid true-colour PNG of one solid colour."""
    def chunk(typ: bytes, data: bytes) -> bytes:
        out = struct.pack(">I", len(data)) + typ + data
        out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
        return out

    row = b"\x00" + bytes(rgb) * width
    raw = row * height
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


def _screen_size():
    if BACKEND == "pyautogui":
        try:
            w, h = pyautogui.size()
            return int(w), int(h)
        except Exception:
            return MOCK_SCREEN
    return MOCK_SCREEN


def _do_screenshot() -> bytes:
    if BACKEND == "pyautogui":
        import io
        shot = pyautogui.screenshot()
        buf = io.BytesIO()
        shot.save(buf, format="PNG")
        return buf.getvalue()
    return _solid_png(320, 200, (16, 32, 64))


def _do_mouse(action: str, params: dict) -> dict:
    if BACKEND == "mock":
        with _mock_lock:
            _mock_calls.append({"action": "mouse", **params})
        return {"backend": "mock", "recorded": True, "action": action}
    x = int(params.get("x", 0))
    y = int(params.get("y", 0))
    if action == "move":
        pyautogui.moveTo(x, y)
    elif action == "click":
        pyautogui.click(x, y, button=params.get("button", "left"))
    elif action == "double_click":
        pyautogui.doubleClick(x, y, button=params.get("button", "left"))
    elif action == "scroll":
        pyautogui.scroll(int(params.get("dy", 0)), x=x, y=y)
    else:
        raise ValueError(f"unknown mouse action: {action}")
    return {"backend": "pyautogui", "action": action, "x": x, "y": y}


def _do_keyboard(action: str, params: dict) -> dict:
    if BACKEND == "mock":
        with _mock_lock:
            _mock_calls.append({"action": "keyboard", **params})
        return {"backend": "mock", "recorded": True, "action": action}
    if action == "type":
        pyautogui.typewrite(str(params.get("text", "")), interval=0.02)
    elif action == "press":
        pyautogui.press(str(params.get("key", "")))
    elif action == "hotkey":
        keys = params.get("keys", [])
        if not isinstance(keys, list) or not keys:
            raise ValueError("hotkey needs a non-empty 'keys' list")
        pyautogui.hotkey(*[str(k) for k in keys])
    else:
        raise ValueError(f"unknown keyboard action: {action}")
    return {"backend": "pyautogui", "action": action}


def _do_open_app(name: str) -> dict:
    if BACKEND == "mock":
        with _mock_lock:
            _mock_calls.append({"action": "open-app", "name": name})
        return {"backend": "mock", "recorded": True, "name": name}
    if os.name != "nt":
        raise RuntimeError("open-app is only implemented on Windows")
    if os.path.exists(name):
        os.startfile(name)  # noqa: S606 — path supplied by the operator
    else:
        # Launch by name through the shell's start command.
        subprocess.Popen(["cmd", "/c", "start", "", name],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return {"backend": "pyautogui", "name": name, "opened": True}


def _do_shell(command: str, shell: str) -> dict:
    """RED action. The MOCK backend NEVER executes anything."""
    if BACKEND == "mock":
        with _mock_lock:
            _mock_calls.append({"action": "shell", "command": command,
                                "shell": shell})
        return {"backend": "mock", "executed": False, "recorded": True,
                "command": command, "shell": shell,
                "note": "Mock backend: command recorded, NOT executed."}
    if shell == "powershell":
        argv = ["powershell", "-NoProfile", "-Command", command]
    elif shell == "cmd":
        argv = ["cmd", "/c", command]
    else:
        raise ValueError(f"unknown shell: {shell} (use powershell or cmd)")
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=120,
                          errors="replace")
    return {"backend": "pyautogui", "executed": True, "shell": shell,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-8000:], "stderr": proc.stderr[-8000:]}


# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------
TOKEN = os.environ.get("MUSE_AGENT_TOKEN", "")
HOST = os.environ.get("MUSE_AGENT_HOST", DEFAULT_HOST).strip() or DEFAULT_HOST
try:
    PORT = int(os.environ.get("MUSE_AGENT_PORT", str(DEFAULT_PORT)))
except ValueError:
    PORT = DEFAULT_PORT


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # -- plumbing ---------------------------------------------------------
    def log_message(self, fmt, *args):  # keep stdout clean; use actions.jsonl
        pass

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_png(self, data: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _auth_ok(self) -> bool:
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return False
        presented = auth[len("Bearer "):].strip()
        return bool(presented) and hmac.compare_digest(presented, TOKEN)

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        if length > MAX_BODY_BYTES:
            raise ValueError("request body too large")
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    # -- routing ----------------------------------------------------------
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path not in PERMISSIONS:
            return self._send_json(404, {"error": "not-found",
                                         "message": f"No endpoint: {path}"})
        if not self._auth_ok():
            return self._send_json(401, {"error": "unauthorized",
                "message": "Missing or invalid Authorization: Bearer token."})
        level = PERMISSIONS[path]
        try:
            if path == "/":
                payload = {"agent": AGENT_NAME, "version": VERSION,
                           "backend": BACKEND,
                           "endpoints": sorted(PERMISSIONS.keys())}
                log_action(path, level, {}, True, {"endpoints": len(payload["endpoints"])})
                return self._send_json(200, payload)
            if path == "/status":
                w, h = _screen_size()
                payload = {"agent": AGENT_NAME, "version": VERSION,
                           "platform": platform.system() + " " + platform.release(),
                           "screen": {"width": w, "height": h},
                           "backend": BACKEND,
                           "token_configured": True,
                           "host": HOST, "port": PORT,
                           "permissions": PERMISSIONS}
                log_action(path, level, {}, True, {"backend": BACKEND})
                return self._send_json(200, payload)
            if path == "/screenshot":
                data = _do_screenshot()
                log_action(path, level, {}, True, {"bytes": len(data)})
                return self._send_png(data)
            if path == "/log":
                qs = parse_qs(parsed.query)
                try:
                    limit = max(1, min(MAX_LOG_RETURN,
                                       int(qs.get("limit", ["50"])[0])))
                except ValueError:
                    limit = 50
                entries = []
                try:
                    with open(LOG_FILE, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                    for line in lines[-limit:]:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
                except FileNotFoundError:
                    entries = []
                log_action(path, level, {"limit": limit}, True,
                           {"returned": len(entries)})
                return self._send_json(200, {"entries": entries,
                                             "count": len(entries)})
        except Exception as exc:  # noqa: BLE001 — report, never crash
            log_action(path, level, {}, False, error=str(exc))
            return self._send_json(500, {"error": "internal", "message": str(exc)})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path not in PERMISSIONS or path in ("/", "/status", "/screenshot", "/log"):
            return self._send_json(404, {"error": "not-found",
                                         "message": f"No POST endpoint: {path}"})
        if not self._auth_ok():
            return self._send_json(401, {"error": "unauthorized",
                "message": "Missing or invalid Authorization: Bearer token."})
        level = PERMISSIONS[path]
        try:
            body = self._read_json()
        except (ValueError, json.JSONDecodeError) as exc:
            return self._send_json(400, {"error": "bad-request",
                                         "message": str(exc)})
        if not isinstance(body, dict):
            return self._send_json(400, {"error": "bad-request",
                                         "message": "JSON object expected."})

        # RED gate: /shell needs an explicit approval flag in the request.
        if level == "RED" and body.get("approved") is not True:
            log_action(path, level, body, False,
                       error="red-gate: approved:true required")
            return self._send_json(403, {"error": "red-gate",
                "message": "This is a RED action (shell/install/delete/admin). "
                           "It needs an explicit approval: send "
                           '{"approved": true} in the request body. '
                           "The attempt was logged."})

        try:
            if path == "/mouse":
                action = body.get("action", "")
                if action not in ("move", "click", "double_click", "scroll"):
                    raise ValueError("mouse action must be move, click, "
                                     "double_click or scroll")
                result = _do_mouse(action, body)
            elif path == "/keyboard":
                action = body.get("action", "")
                if action not in ("type", "press", "hotkey"):
                    raise ValueError("keyboard action must be type, press or hotkey")
                result = _do_keyboard(action, body)
            elif path == "/open-app":
                name = str(body.get("name", "")).strip()
                if not name:
                    raise ValueError("open-app needs a non-empty 'name'")
                result = _do_open_app(name)
            elif path == "/shell":
                command = str(body.get("command", "")).strip()
                shell = str(body.get("shell", "powershell")).strip().lower()
                if not command:
                    raise ValueError("shell needs a non-empty 'command'")
                result = _do_shell(command, shell)
            else:  # pragma: no cover — routing guard above
                return self._send_json(404, {"error": "not-found",
                                             "message": f"No POST endpoint: {path}"})
        except (ValueError, RuntimeError) as exc:
            log_action(path, level, body, False, error=str(exc))
            return self._send_json(400, {"error": "bad-request",
                                         "message": str(exc)})
        except Exception as exc:  # noqa: BLE001 — report, never crash
            log_action(path, level, body, False, error=str(exc))
            return self._send_json(500, {"error": "internal", "message": str(exc)})

        log_action(path, level, body, True, result)
        payload = {"ok": True, "permission": level, **result}
        if level == "YELLOW":
            payload["note"] = ("YELLOW action: logged. Sensitive use needs "
                               "Yahya's confirmation via the OMEGA gate.")
        return self._send_json(200, payload)


def main() -> int:
    if not TOKEN:
        print("ERROR: MUSE_AGENT_TOKEN is not set.", file=sys.stderr)
        print("Set it to a strong random value (created on this machine only), "
              "then run again. Never paste a token in chat.", file=sys.stderr)
        return 2
    if HOST == "0.0.0.0":
        print("ERROR: binding to 0.0.0.0 is refused. Use 127.0.0.1 (default) "
              "or a specific Tailscale IP set by the operator.", file=sys.stderr)
        return 2
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"{AGENT_NAME} v{VERSION} — backend={BACKEND} — "
          f"listening on http://{HOST}:{PORT} (localhost only unless "
          f"MUSE_AGENT_HOST names a Tailscale IP)")
    print(f"Log: {LOG_FILE}")
    print("Stop with Ctrl+C.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
