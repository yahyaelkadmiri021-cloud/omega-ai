"""OMEGA AI — Project Manager agent verification (Phase 5).

Dry-run with a raising LLM (no API key): proves the deterministic board
works without a key, the supervisor wiring is correct, and the full
pipeline completes honestly (errors recorded, never faked).

Run:  ~/workspace/YAHYA_AI_COMMAND_CENTER/.venv/bin/python tests/test_project_manager.py
"""
import json
import sys
from pathlib import Path

CC = Path.home() / "workspace" / "YAHYA_AI_COMMAND_CENTER"
VENV_SITE = CC / ".venv" / "lib" / "python3.12" / "site-packages"
sys.path.insert(0, str(VENV_SITE))
sys.path.insert(0, str(CC))

import yaml  # noqa: E402
from agents import project_manager  # noqa: E402
from core.state import new_state  # noqa: E402
from core.supervisor import WORKER_MODULES, Supervisor  # noqa: E402


def raising_llm(*a, **k):
    raise RuntimeError("No usable model for role 'pm' (no key)")


def main() -> None:
    # 0. configs parse
    yaml.safe_load((CC / "config" / "models.yaml").read_text(encoding="utf-8"))
    yaml.safe_load((CC / "config" / "agents.yaml").read_text(encoding="utf-8"))
    print("CONFIG OK: models.yaml + agents.yaml parse")

    # 1. wiring
    assert "project_manager" in WORKER_MODULES, "PM not in WORKER_MODULES"
    sup = Supervisor(root=str(CC))
    plan = sup.classify_task("build a website and a video")
    assert plan[-1] == "project_manager", f"PM not last: {plan}"
    print("WIRING OK:", plan)

    # 2. isolated PM dry-run on the real OMEGA AI TASKS.md
    state = new_state("omega-ai-test", "verify PM board")
    state["slug"] = "pm-test"
    state["_root"] = "/tmp/pm-test-root"
    state["agent_status"] = {"researcher": "DONE", "coder": "FAILED", "critic": "DONE"}
    state["errors"] = ["coder failed: no key"]
    state["tasks_file"] = str(Path.home() / "workspace" / "omega-ai" / "TASKS.md")
    md = project_manager.run(state, raising_llm)
    board = state["task_board"]
    assert board["tasks"], "empty board"
    assert "LLM unavailable" in (board["recommendation"] or ""), "fallback missing"
    assert board["counts"].get("completed", 0) >= 1, "no completed counted"
    assert board["next_action"], "no next action"
    files = sorted(Path("/tmp/pm-test-root/projects/active/pm-test").glob("task_board.*"))
    assert len(files) == 2, f"board files missing: {files}"
    assert "# Task Board" in md and "## Next action" in md
    print(f"BOARD OK: {len(board['tasks'])} tasks; counts={board['counts']}; "
          f"blockers={len(board['blockers'])}; next={board['next_action']}")

    # 3. full pipeline dry run (no key — agents fail fast, honestly)
    state2 = sup.run_project("omega-ai-pm-test", "test the project manager wiring")
    assert "task_board" in state2, "no task_board after full run"
    assert state2["agent_status"].get("project_manager") == "DONE", state2["agent_status"]
    report = CC / "projects" / "active" / "omega-ai-pm-test" / "REPORT.md"
    assert report.is_file(), "no REPORT.md"
    tb = CC / "projects" / "active" / "omega-ai-pm-test" / "task_board.json"
    assert tb.is_file(), "no task_board.json from full run"
    print(f"FULL RUN OK: pm DONE, REPORT.md + task_board.json written, "
          f"errors recorded: {len(state2['errors'])}")
    print("ALL PM TESTS PASSED")


if __name__ == "__main__":
    main()
