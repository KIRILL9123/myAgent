"""Bounded code workspace for agent-generated experiments.

This module deliberately does not expose a general shell.  It gives the agent
an isolated workspace under ``CODE_SANDBOX_ROOT`` and a small allowlist of
checks.  It is a product safety boundary, not a substitute for a container or
VM when executing hostile code.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any
from uuid import uuid4

from backend.app.sandbox_runner import (
    DockerSandboxError,
    run_check as docker_run_check,
    runtime_status as docker_runtime_status,
)


DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "sandbox"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SANDBOX_ROOT = Path(os.getenv("CODE_SANDBOX_ROOT", str(DEFAULT_ROOT))).resolve()
SANDBOX_RUNTIME = os.getenv("CODE_SANDBOX_RUNTIME", "docker").strip().lower()

MAX_FILE_BYTES = 256 * 1024
MAX_WORKSPACE_BYTES = 5 * 1024 * 1024
MAX_OUTPUT_CHARS = 20_000
DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 120
SANDBOX_META_DIR_NAME = ".sandbox_metadata"
SANDBOX_BACKUP_DIR_NAME = ".sandbox_backups"
SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
ALLOWED_EXTENSIONS = {
    ".css",
    ".html",
    ".js",
    ".mjs",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


class SandboxError(ValueError):
    """A user-correctable sandbox request error."""


def _validate_session_id(session_id: str) -> str:
    if not isinstance(session_id, str) or not SESSION_RE.fullmatch(session_id):
        raise SandboxError("Invalid session_id. Use 1-64 letters, numbers, '_' or '-'.")
    return session_id


def _workspace(session_id: str, *, create: bool = True) -> Path:
    session_id = _validate_session_id(session_id)
    root = SANDBOX_ROOT.resolve()
    if create:
        root.mkdir(parents=True, exist_ok=True)
    workspace = (root / session_id).resolve()
    if workspace.parent != root:
        raise SandboxError("Sandbox workspace escaped its root.")
    if create:
        workspace.mkdir(parents=True, exist_ok=True)
    return workspace


def _safe_path(session_id: str, relative_path: str, *, create_parent: bool = False) -> tuple[Path, Path]:
    workspace = _workspace(session_id)
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise SandboxError("A relative file path is required.")

    # Normalize both separator styles before validating.  The sandbox can
    # receive a Windows path from a client even when the server runs on Linux
    # (and vice versa), so relying only on the host OS's Path semantics would
    # treat values such as ``..\\outside.py`` or ``C:\\outside.py`` as safe
    # relative filenames on POSIX.
    portable_path = relative_path.replace("\\", "/")
    candidate_input = Path(portable_path)
    windows_input = PureWindowsPath(relative_path)
    if (
        candidate_input.is_absolute()
        or windows_input.is_absolute()
        or windows_input.drive
        or any(part == ".." for part in candidate_input.parts)
        or any(part == ".." for part in windows_input.parts)
    ):
        raise SandboxError("Only relative paths inside the sandbox workspace are allowed.")
    if candidate_input.name in {"", ".", ".."}:
        raise SandboxError("A file path is required.")

    candidate = (workspace / candidate_input).resolve()
    try:
        candidate.relative_to(workspace)
    except ValueError as exc:
        raise SandboxError("Path is outside the sandbox workspace.") from exc

    # Resolve catches existing symlinks.  Also reject symlink components that
    # could be introduced between the validation and the operation.
    current = workspace
    for part in candidate_input.parts:
        current = current / part
        if current.is_symlink():
            raise SandboxError("Symlinks are not allowed in the sandbox workspace.")

    if create_parent:
        candidate.parent.mkdir(parents=True, exist_ok=True)
    return workspace, candidate


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _workspace_size(workspace: Path) -> int:
    total = 0
    for path in workspace.rglob("*"):
        if path.is_file() and not path.is_symlink():
            total += _file_size(path)
    return total


def _validate_extension(path: Path) -> None:
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise SandboxError(f"File type is not allowed. Supported extensions: {allowed}.")


def _truncate(value: Any) -> str:
    text = "" if value is None else str(value)
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + "\n...[output truncated]"


def _metadata_path(session_id: str) -> Path:
    """Keep baselines outside the editable workspace and container mount."""
    return SANDBOX_ROOT.resolve().parent / SANDBOX_META_DIR_NAME / f"{_validate_session_id(session_id)}.json"


def _capture_workspace_files(workspace: Path) -> dict[str, str]:
    captured: dict[str, str] = {}
    for item in _tree(workspace):
        if item["type"] != "file":
            continue
        path = workspace / item["path"]
        try:
            _validate_extension(path)
            if _file_size(path) > MAX_FILE_BYTES:
                continue
            captured[item["path"]] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError, SandboxError):
            continue
    return captured


def _read_baseline(session_id: str) -> dict[str, Any] | None:
    metadata = _metadata_path(session_id)
    if not metadata.exists():
        return None
    try:
        payload = json.loads(metadata.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("files"), dict):
        return None
    return payload


def _write_baseline(session_id: str, files: dict[str, str]) -> dict[str, Any]:
    baseline = {
        "version": 1,
        "session_id": _validate_session_id(session_id),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    metadata = _metadata_path(session_id)
    metadata.parent.mkdir(parents=True, exist_ok=True)
    metadata.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    return baseline


def _ensure_baseline(session_id: str, workspace: Path) -> dict[str, Any]:
    baseline = _read_baseline(session_id)
    if baseline is not None:
        return baseline
    return _write_baseline(session_id, _capture_workspace_files(workspace))


def _workspace_state(session_id: str) -> tuple[Path, dict[str, str], dict[str, str], dict[str, Any]]:
    workspace = _workspace(session_id)
    baseline = _ensure_baseline(session_id, workspace)
    before = {str(path): str(content) for path, content in baseline["files"].items()}
    after = _capture_workspace_files(workspace)
    return workspace, before, after, baseline


def _content_hash(content: str | None) -> str | None:
    if content is None:
        return None
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _workspace_digest(files: dict[str, str]) -> str:
    payload = json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _apply_target(relative_path: str) -> Path:
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise SandboxError("A relative project path is required.")
    candidate_input = Path(relative_path)
    if candidate_input.is_absolute() or any(part in {"", ".", ".."} for part in candidate_input.parts):
        raise SandboxError("Only relative paths inside the main project are allowed.")
    protected_parts = {".git", ".sandbox_metadata", SANDBOX_BACKUP_DIR_NAME, "sandbox", "node_modules"}
    if any(part.lower() in protected_parts for part in candidate_input.parts):
        raise SandboxError("This project path is protected from sandbox apply.")
    if candidate_input.name.lower() in {".env", ".env.local", ".env.production", "credentials.json", "secrets.json"}:
        raise SandboxError("Secret and environment files cannot be changed by sandbox apply.")
    if candidate_input.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise SandboxError("Only supported text-file extensions can be applied to the main project.")

    target = PROJECT_ROOT / candidate_input
    resolved = target.resolve()
    try:
        resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise SandboxError("Project path escaped the repository root.") from exc
    current = PROJECT_ROOT
    for part in candidate_input.parts:
        current = current / part
        if current.is_symlink():
            raise SandboxError("Symlinked project paths are not allowed for sandbox apply.")
    return target


def build_apply_plan(session_id: str) -> dict[str, Any]:
    """Build a reviewable apply plan without changing the main project."""
    workspace, before, after, baseline = _workspace_state(session_id)
    diff = diff_workspace(session_id)
    changes: list[dict[str, Any]] = []
    for item in diff["files"]:
        relative = item["path"]
        _apply_target(relative)
        old = before.get(relative)
        new = after.get(relative)
        changes.append({
            "path": relative,
            "status": item["status"],
            "additions": item["additions"],
            "deletions": item["deletions"],
            "diff": item["diff"],
            "baseline_sha256": _content_hash(old),
            "current_sha256": _content_hash(new),
        })
    if not changes:
        raise SandboxError("There are no sandbox changes to apply.")
    return {
        "version": 1,
        "session_id": session_id,
        "baseline_at": baseline["captured_at"],
        "workspace_digest": _workspace_digest(after),
        "summary": diff["summary"],
        "changes": changes,
        "workspace": str(workspace),
    }


def request_apply(session_id: str) -> dict[str, Any]:
    """Create a pending Approval Center request for the current sandbox diff."""
    plan = build_apply_plan(session_id)
    from backend.app.approvals.approval_service import create_sandbox_apply_request
    return create_sandbox_apply_request(plan)


def apply_sandbox_plan(plan: dict[str, Any], *, operation_id: str | None = None) -> dict[str, Any]:
    """Apply an already-reviewed plan with conflict detection and rollback."""
    if not isinstance(plan, dict):
        raise SandboxError("Invalid sandbox apply plan.")
    session_id = _validate_session_id(str(plan.get("session_id", "")))
    current_plan = build_apply_plan(session_id)
    if current_plan["workspace_digest"] != plan.get("workspace_digest") or current_plan["baseline_at"] != plan.get("baseline_at"):
        raise SandboxError("Sandbox changed after approval. Review the new diff before applying it.")
    if current_plan["changes"] != plan.get("changes"):
        raise SandboxError("Sandbox diff no longer matches the approved plan.")

    _, before, after, _ = _workspace_state(session_id)
    targets = {item["path"]: _apply_target(item["path"]) for item in current_plan["changes"]}
    for item in current_plan["changes"]:
        target = targets[item["path"]]
        expected_old = before.get(item["path"])
        if item["status"] == "added":
            if target.exists():
                raise SandboxError(f"Apply conflict: project file already exists: {item['path']}")
        else:
            if not target.exists() or not target.is_file() or target.is_symlink():
                raise SandboxError(f"Apply conflict: project file is missing or unsafe: {item['path']}")
            try:
                actual_old = target.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise SandboxError(f"Apply conflict: project file is not readable: {item['path']}") from exc
            if actual_old != expected_old:
                raise SandboxError(f"Apply conflict: project file changed outside sandbox: {item['path']}")

    operation = re.sub(r"[^A-Za-z0-9_-]", "-", operation_id or str(uuid4()))[:64]
    backup_root = PROJECT_ROOT / SANDBOX_BACKUP_DIR_NAME / operation
    backed_up: list[tuple[Path, Path]] = []
    created: list[Path] = []
    try:
        backup_root.mkdir(parents=True, exist_ok=True)
        for item in current_plan["changes"]:
            target = targets[item["path"]]
            if target.exists() and target.is_file():
                backup = backup_root / Path(item["path"])
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, backup)
                backed_up.append((target, backup))
        for item in current_plan["changes"]:
            target = targets[item["path"]]
            if item["status"] == "removed":
                target.unlink()
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(f".{target.name}.sandbox-{uuid4().hex}")
            temporary.write_text(after[item["path"]], encoding="utf-8", newline="\n")
            os.replace(temporary, target)
            if not any(existing == target for existing, _ in backed_up):
                created.append(target)
        capture_baseline(session_id)
    except Exception as exc:
        for target in created:
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass
        for target, backup in reversed(backed_up):
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup, target)
            except OSError:
                pass
        raise SandboxError(f"Sandbox apply rolled back: {exc}") from exc

    return {
        "status": "success",
        "session_id": session_id,
        "summary": current_plan["summary"],
        "applied_files": [item["path"] for item in current_plan["changes"]],
        "backup_created": True,
        "message": "Approved sandbox changes applied to the main project.",
    }


def capture_baseline(session_id: str) -> dict[str, Any]:
    workspace = _workspace(session_id)
    baseline = _write_baseline(session_id, _capture_workspace_files(workspace))
    return {
        "status": "success",
        "session_id": session_id,
        "baseline_at": baseline["captured_at"],
        "file_count": len(baseline["files"]),
        "message": "Current sandbox state saved as the comparison point.",
    }


def diff_workspace(session_id: str) -> dict[str, Any]:
    workspace = _workspace(session_id)
    baseline = _ensure_baseline(session_id, workspace)
    before = {str(path): str(content) for path, content in baseline["files"].items()}
    after = _capture_workspace_files(workspace)
    changed: list[dict[str, Any]] = []
    total_diff_chars = 0

    for relative in sorted(set(before) | set(after)):
        old = before.get(relative)
        new = after.get(relative)
        if old == new:
            continue
        if old is None:
            state = "added"
            old = ""
        elif new is None:
            state = "removed"
            new = ""
        else:
            state = "modified"
        diff_lines = list(difflib.unified_diff(
            old.splitlines(),
            new.splitlines(),
            fromfile=f"a/{relative}",
            tofile=f"b/{relative}",
            lineterm="",
        ))
        diff_text = "\n".join(diff_lines)
        remaining = max(0, MAX_OUTPUT_CHARS - total_diff_chars)
        if len(diff_text) > remaining:
            diff_text = diff_text[:remaining] + "\n...[diff truncated]"
        total_diff_chars += len(diff_text)
        additions = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
        deletions = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
        changed.append({
            "path": relative,
            "status": state,
            "diff": diff_text,
            "additions": additions,
            "deletions": deletions,
        })

    return {
        "status": "success",
        "session_id": session_id,
        "baseline_at": baseline["captured_at"],
        "summary": {
            "added": sum(1 for item in changed if item["status"] == "added"),
            "modified": sum(1 for item in changed if item["status"] == "modified"),
            "removed": sum(1 for item in changed if item["status"] == "removed"),
            "changed_files": len(changed),
        },
        "files": changed,
    }


def _tree(workspace: Path) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    if not workspace.exists():
        return files
    for path in sorted(workspace.rglob("*")):
        if path.is_symlink():
            continue
        relative = path.relative_to(workspace).as_posix()
        files.append({
            "path": relative,
            "type": "directory" if path.is_dir() else "file",
            "size": 0 if path.is_dir() else _file_size(path),
        })
    return files


def list_files(session_id: str) -> dict[str, Any]:
    workspace = _workspace(session_id)
    _ensure_baseline(session_id, workspace)
    return {
        "status": "success",
        "session_id": session_id,
        "workspace": str(workspace),
        "files": _tree(workspace),
        "total_bytes": _workspace_size(workspace),
    }


def read_file(session_id: str, path: str) -> dict[str, Any]:
    _, safe_file = _safe_path(session_id, path)
    if not safe_file.exists() or not safe_file.is_file():
        return {"status": "error", "message": f"File not found: {path}"}
    _validate_extension(safe_file)
    if _file_size(safe_file) > MAX_FILE_BYTES:
        return {"status": "error", "message": "File exceeds the 256 KB read limit."}
    try:
        content = safe_file.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"status": "error", "message": "Only UTF-8 text files can be read."}
    return {"status": "success", "session_id": session_id, "path": path, "content": content}


def delete_file(session_id: str, path: str) -> dict[str, Any]:
    _, safe_file = _safe_path(session_id, path)
    _ensure_baseline(session_id, _workspace(session_id))
    if not safe_file.exists() or not safe_file.is_file():
        return {"status": "error", "message": f"File not found: {path}"}
    _validate_extension(safe_file)
    safe_file.unlink()
    return {
        "status": "success",
        "session_id": session_id,
        "path": path,
        "message": "File deleted from the sandbox workspace.",
    }


def write_file(session_id: str, path: str, content: str, *, overwrite: bool = False) -> dict[str, Any]:
    workspace, safe_file = _safe_path(session_id, path)
    _ensure_baseline(session_id, workspace)
    _validate_extension(safe_file)
    if not isinstance(content, str):
        raise SandboxError("File content must be text.")
    content_bytes = content.encode("utf-8")
    if len(content_bytes) > MAX_FILE_BYTES:
        raise SandboxError("File exceeds the 256 KB write limit.")
    if safe_file.exists() and not overwrite:
        return {
            "status": "error",
            "message": "File already exists. Set overwrite=true only when replacement is intended.",
        }
    if safe_file.exists() and not safe_file.is_file():
        raise SandboxError("A directory cannot be used as a file path.")
    existing_size = _file_size(safe_file) if safe_file.exists() else 0
    if _workspace_size(workspace) - existing_size + len(content_bytes) > MAX_WORKSPACE_BYTES:
        raise SandboxError("Workspace exceeds the 5 MB total size limit.")
    safe_file.parent.mkdir(parents=True, exist_ok=True)
    safe_file.write_text(content, encoding="utf-8", newline="\n")
    return {
        "status": "success",
        "session_id": session_id,
        "path": path,
        "bytes": len(content_bytes),
        "message": "File written inside the sandbox workspace.",
    }


def _clean_environment() -> dict[str, str]:
    """Return only non-sensitive variables needed by local runtimes."""
    env: dict[str, str] = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "TEMP": os.environ.get("TEMP", ""),
        "TMP": os.environ.get("TMP", ""),
    }
    if os.name == "nt" and os.environ.get("SystemRoot"):
        env["SystemRoot"] = os.environ["SystemRoot"]
    return {key: value for key, value in env.items() if value}


def _resolve_runtime(command: str) -> str | None:
    if command in {"python", "pytest", "compile_python"}:
        return sys.executable
    if command == "node":
        return shutil.which("node")
    return None


def _check_command(command: str, workspace: Path, safe_file: Path) -> list[str]:
    runtime = _resolve_runtime(command)
    if not runtime:
        raise SandboxError(f"Runtime for '{command}' is not available on this machine.")
    relative = safe_file.relative_to(workspace).as_posix()
    if command == "python":
        return [runtime, "-I", "-B", relative]
    if command == "pytest":
        return [runtime, "-I", "-B", "-m", "pytest", relative]
    if command == "compile_python":
        return [runtime, "-I", "-B", "-m", "py_compile", relative]
    if command == "node":
        return [runtime, relative]
    raise SandboxError(f"Unsupported sandbox check: {command}")


def _run_local_check(
    session_id: str,
    check: str,
    path: str,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    if check not in {"python", "pytest", "node", "compile_python"}:
        raise SandboxError("Unsupported check. Use python, pytest, node, or compile_python.")
    if not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise SandboxError(f"timeout_seconds must be between 1 and {MAX_TIMEOUT_SECONDS}.")
    workspace, safe_file = _safe_path(session_id, path)
    if not safe_file.exists() or not safe_file.is_file():
        return {"status": "error", "message": f"File not found: {path}"}
    _validate_extension(safe_file)
    if check in {"python", "pytest", "compile_python"} and safe_file.suffix.lower() != ".py":
        raise SandboxError(f"'{check}' requires a .py file.")
    if check == "node" and safe_file.suffix.lower() not in {".js", ".mjs"}:
        raise SandboxError("'node' requires a .js or .mjs file.")

    command = _check_command(check, workspace, safe_file)
    started = time.monotonic()
    try:
        completed = subprocess.run(
            command,
            cwd=workspace,
            env=_clean_environment(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            shell=False,
            **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}),
        )
        return {
            "status": "success" if completed.returncode == 0 else "failed",
            "session_id": session_id,
            "check": check,
            "path": path,
            "return_code": completed.returncode,
            "stdout": _truncate(completed.stdout),
            "stderr": _truncate(completed.stderr),
            "duration_ms": round((time.monotonic() - started) * 1000),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout",
            "session_id": session_id,
            "check": check,
            "path": path,
            "stdout": _truncate(exc.stdout),
            "stderr": _truncate(exc.stderr),
            "message": f"Sandbox check timed out after {timeout_seconds} seconds.",
            "duration_ms": round((time.monotonic() - started) * 1000),
        }


def runtime_status() -> dict[str, Any]:
    if SANDBOX_RUNTIME == "local":
        return {
            "configured_runtime": "local",
            "ready": True,
            "security": "host_process",
            "message": "Локальный runtime включён только для разработки и тестов.",
        }
    if SANDBOX_RUNTIME == "docker":
        return docker_runtime_status()
    return {
        "configured_runtime": SANDBOX_RUNTIME or "unknown",
        "ready": False,
        "message": "Неизвестный CODE_SANDBOX_RUNTIME. Используйте docker или local.",
    }


def run_check(
    session_id: str,
    check: str,
    path: str,
    *,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    if SANDBOX_RUNTIME == "local":
        return _run_local_check(session_id, check, path, timeout_seconds=timeout_seconds)
    if SANDBOX_RUNTIME != "docker":
        raise SandboxError("Неизвестный CODE_SANDBOX_RUNTIME. Используйте docker или local.")
    if check not in {"python", "pytest", "node", "compile_python"}:
        raise SandboxError("Unsupported check. Use python, pytest, node, or compile_python.")
    if not isinstance(timeout_seconds, int) or not 1 <= timeout_seconds <= MAX_TIMEOUT_SECONDS:
        raise SandboxError(f"timeout_seconds must be between 1 and {MAX_TIMEOUT_SECONDS}.")
    workspace, safe_file = _safe_path(session_id, path)
    if not safe_file.exists() or not safe_file.is_file():
        return {"status": "error", "message": f"File not found: {path}"}
    _validate_extension(safe_file)
    if check in {"python", "pytest", "compile_python"} and safe_file.suffix.lower() != ".py":
        raise SandboxError(f"'{check}' requires a .py file.")
    if check == "node" and safe_file.suffix.lower() not in {".js", ".mjs"}:
        raise SandboxError("'node' requires a .js or .mjs file.")
    relative_path = safe_file.relative_to(workspace).as_posix()
    try:
        return docker_run_check(
            workspace,
            relative_path,
            check,
            timeout_seconds=timeout_seconds,
        )
    except DockerSandboxError as exc:
        raise SandboxError(str(exc)) from exc


def workspace_snapshot(session_id: str) -> dict[str, Any]:
    """Return a machine-readable summary useful for API clients and the UI."""
    result = list_files(session_id)
    baseline = _ensure_baseline(session_id, _workspace(session_id))
    diff = diff_workspace(session_id)
    runtime = runtime_status()
    if not runtime.get("ready"):
        lifecycle_state = "runtime_unavailable"
    elif diff["summary"]["changed_files"]:
        lifecycle_state = "draft_changed"
    elif result["files"]:
        lifecycle_state = "checkpointed"
    else:
        lifecycle_state = "empty"
    result["limits"] = {
        "max_file_bytes": MAX_FILE_BYTES,
        "max_workspace_bytes": MAX_WORKSPACE_BYTES,
        "max_output_chars": MAX_OUTPUT_CHARS,
        "max_timeout_seconds": MAX_TIMEOUT_SECONDS,
    }
    result["lifecycle"] = {
        "state": lifecycle_state,
        "changed_files": diff["summary"]["changed_files"],
        "baseline_at": baseline["captured_at"],
    }
    result["runtime"] = runtime
    return result
