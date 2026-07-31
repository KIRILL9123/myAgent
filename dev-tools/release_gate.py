"""Deterministic release gate for the Home Agent.

The gate intentionally keeps deterministic checks separate from any optional
LLM quality judging. It exits non-zero when a required check fails and stores a
small JSONL verdict history under the ignored ``logs/`` directory.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HISTORY_PATH = PROJECT_ROOT / "logs" / "release_gate.jsonl"
MAX_OUTPUT_CHARS = 4000
NPM_COMMAND = "npm.cmd" if sys.platform == "win32" else "npm"
PROJECT_PYTHON = (
    PROJECT_ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
)
PYTHON_COMMAND = str(PROJECT_PYTHON) if PROJECT_PYTHON.exists() else sys.executable


def _summarize_output(stdout: str, stderr: str) -> str:
    combined = "\n".join(part for part in (stdout.strip(), stderr.strip()) if part)
    if len(combined) <= MAX_OUTPUT_CHARS:
        return combined
    return "…" + combined[-(MAX_OUTPUT_CHARS - 1):]


def _run_check(name: str, command: list[str], cwd: Path, timeout_seconds: int) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
        status = "passed" if completed.returncode == 0 else "failed"
        return {
            "name": name,
            "status": status,
            "return_code": completed.returncode,
            "duration_ms": round((time.monotonic() - started) * 1000, 2),
            "command": command,
            "output": _summarize_output(completed.stdout, completed.stderr),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "name": name,
            "status": "failed",
            "return_code": None,
            "duration_ms": round((time.monotonic() - started) * 1000, 2),
            "command": command,
            "output": _summarize_output(
                str(exc.stdout or ""),
                f"Timed out after {timeout_seconds}s\n{exc.stderr or ''}",
            ),
        }
    except OSError as exc:
        return {
            "name": name,
            "status": "failed",
            "return_code": None,
            "duration_ms": round((time.monotonic() - started) * 1000, 2),
            "command": command,
            "output": f"Could not start check: {type(exc).__name__}: {exc}",
        }


def _git_revision() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False,
        )
        return result.stdout.strip() or None
    except OSError:
        return None


def run_release_gate(
    *, backend: bool = True, frontend: bool = True, timeout_seconds: int = 180
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    if backend:
        checks.append(_run_check(
            "backend_tests",
            [PYTHON_COMMAND, "-m", "pytest", "backend/tests", "-q"],
            PROJECT_ROOT,
            timeout_seconds,
        ))
    if frontend:
        checks.append(_run_check("frontend_lint", [NPM_COMMAND, "run", "lint"], PROJECT_ROOT / "frontend", timeout_seconds))
        checks.append(_run_check("frontend_build", [NPM_COMMAND, "run", "build"], PROJECT_ROOT / "frontend", timeout_seconds))

    passed = all(check["status"] == "passed" for check in checks) and bool(checks)
    report: dict[str, Any] = {
        "status": "passed" if passed else "failed",
        "deterministic": True,
        "revision": _git_revision(),
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "checks": checks,
    }
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("a", encoding="utf-8") as history:
        history.write(json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the deterministic Home Agent release gate")
    parser.add_argument("--backend-only", action="store_true", help="run backend tests only")
    parser.add_argument("--frontend-only", action="store_true", help="run frontend checks only")
    parser.add_argument("--timeout", type=int, default=180, help="timeout per check in seconds")
    args = parser.parse_args()
    if args.backend_only and args.frontend_only:
        parser.error("--backend-only and --frontend-only cannot be used together")

    report = run_release_gate(
        backend=not args.frontend_only,
        frontend=not args.backend_only,
        timeout_seconds=max(1, args.timeout),
    )
    # ASCII output keeps the CLI usable in the default Windows code page.
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
