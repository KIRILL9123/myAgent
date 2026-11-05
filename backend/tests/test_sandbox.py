import pytest

from backend.app import sandbox_service
from backend.app import sandbox_runner
from backend.app.approvals.approval_service import list_approvals, resolve_approval
from backend.app.storage import db


@pytest.fixture
def sandbox_root(tmp_path, monkeypatch):
    root = tmp_path / "sandbox"
    monkeypatch.setattr(sandbox_service, "SANDBOX_ROOT", root)
    monkeypatch.setattr(sandbox_service, "SANDBOX_RUNTIME", "local")
    return root


def test_write_read_and_list_stay_inside_workspace(sandbox_root):
    written = sandbox_service.write_file("demo", "src/main.py", "print('hello')\n")

    assert written["status"] == "success"
    assert (sandbox_root / "demo" / "src" / "main.py").read_text(encoding="utf-8") == "print('hello')\n"
    assert sandbox_service.read_file("demo", "src/main.py")["content"] == "print('hello')\n"
    assert any(item["path"] == "src/main.py" for item in sandbox_service.list_files("demo")["files"])


@pytest.mark.parametrize("path", ["../outside.py", "..\\outside.py", "C:\\outside.py", "/tmp/outside.py"])
def test_path_traversal_is_rejected(sandbox_root, path):
    with pytest.raises(sandbox_service.SandboxError):
        sandbox_service.write_file("demo", path, "print('nope')")
    assert not (sandbox_root.parent / "outside.py").exists()


def test_existing_file_requires_explicit_overwrite(sandbox_root):
    sandbox_service.write_file("demo", "main.py", "print(1)")
    result = sandbox_service.write_file("demo", "main.py", "print(2)")

    assert result["status"] == "error"
    assert sandbox_service.read_file("demo", "main.py")["content"] == "print(1)"


def test_diff_tracks_changes_and_can_reset_baseline(sandbox_root):
    initial = sandbox_service.diff_workspace("demo")
    assert initial["summary"]["changed_files"] == 0

    sandbox_service.write_file("demo", "main.py", "print(1)\n")
    added = sandbox_service.diff_workspace("demo")
    assert added["summary"] == {"added": 1, "modified": 0, "removed": 0, "changed_files": 1}
    assert added["files"][0]["status"] == "added"
    assert "+print(1)" in added["files"][0]["diff"]

    sandbox_service.capture_baseline("demo")
    sandbox_service.write_file("demo", "main.py", "print(2)\n", overwrite=True)
    modified = sandbox_service.diff_workspace("demo")
    assert modified["files"][0]["status"] == "modified"
    assert "-print(1)" in modified["files"][0]["diff"]
    assert "+print(2)" in modified["files"][0]["diff"]

    saved = sandbox_service.capture_baseline("demo")
    assert saved["file_count"] == 1
    assert sandbox_service.diff_workspace("demo")["summary"]["changed_files"] == 0
    assert not (sandbox_root / "demo" / ".sandbox_metadata").exists()


def test_workspace_snapshot_reports_lifecycle_and_checkpoint(sandbox_root):
    empty = sandbox_service.workspace_snapshot("demo")
    assert empty["lifecycle"]["state"] == "empty"

    sandbox_service.write_file("demo", "main.py", "print(1)\n")
    changed = sandbox_service.workspace_snapshot("demo")
    assert changed["lifecycle"]["state"] == "draft_changed"
    assert changed["lifecycle"]["changed_files"] == 1

    sandbox_service.capture_baseline("demo")
    checkpointed = sandbox_service.workspace_snapshot("demo")
    assert checkpointed["lifecycle"]["state"] == "checkpointed"
    assert checkpointed["lifecycle"]["changed_files"] == 0


@pytest.mark.asyncio
async def test_apply_is_approval_gated_and_creates_backup(sandbox_root, tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "apply.db"))
    db.init_db()
    project_root = tmp_path / "project"
    monkeypatch.setattr(sandbox_service, "PROJECT_ROOT", project_root)

    sandbox_service.write_file("demo", "backend/app/hello.py", "print('from sandbox')\n")
    request = sandbox_service.request_apply("demo")

    assert request["status"] == "pending_approval"
    pending = list_approvals()
    assert pending[0]["kind"] == "SANDBOX_APPLY"
    assert not (project_root / "backend/app/hello.py").exists()

    resolved = await resolve_approval(pending[0]["id"], "approve")

    assert resolved["status"] == "APPROVED"
    assert (project_root / "backend/app/hello.py").read_text(encoding="utf-8") == "print('from sandbox')\n"
    assert list_approvals() == []
    assert list((project_root / ".sandbox_backups").rglob("*"))


@pytest.mark.asyncio
async def test_apply_rejects_project_conflict_without_overwrite(sandbox_root, tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "conflict.db"))
    db.init_db()
    project_root = tmp_path / "project"
    monkeypatch.setattr(sandbox_service, "PROJECT_ROOT", project_root)

    sandbox_service.write_file("demo", "backend/app/conflict.py", "print('sandbox')\n")
    request = sandbox_service.request_apply("demo")
    target = project_root / "backend/app/conflict.py"
    target.parent.mkdir(parents=True)
    target.write_text("print('changed elsewhere')\n", encoding="utf-8")

    with pytest.raises(ValueError, match="already exists"):
        await resolve_approval(request["approval_id"], "approve")
    assert target.read_text(encoding="utf-8") == "print('changed elsewhere')\n"


def test_python_check_runs_only_in_workspace(sandbox_root):
    sandbox_service.write_file("demo", "main.py", "print('sandbox ok')")

    result = sandbox_service.run_check("demo", "python", "main.py")

    assert result["status"] == "success"
    assert result["return_code"] == 0
    assert "sandbox ok" in result["stdout"]


def test_docker_mode_never_silently_falls_back_to_local(sandbox_root, monkeypatch):
    sandbox_service.write_file("demo", "main.py", "print('docker')")
    calls = []

    def fake_docker_runner(workspace, relative_path, check, *, timeout_seconds):
        calls.append((workspace, relative_path, check, timeout_seconds))
        return {"status": "success", "runtime": "docker"}

    monkeypatch.setattr(sandbox_service, "SANDBOX_RUNTIME", "docker")
    monkeypatch.setattr(sandbox_service, "docker_run_check", fake_docker_runner)
    monkeypatch.setattr(sandbox_service, "_run_local_check", lambda *args, **kwargs: pytest.fail("local fallback used"))

    result = sandbox_service.run_check("demo", "python", "main.py", timeout_seconds=7)

    assert result["runtime"] == "docker"
    assert calls and calls[0][1:] == ("main.py", "python", 7)


def test_docker_runner_builds_restricted_command(tmp_path, monkeypatch):
    captured = {}

    monkeypatch.setattr(sandbox_runner, "_docker_binary", lambda: "docker")
    monkeypatch.setattr(
        sandbox_runner,
        "_run_docker_probe",
        lambda args, timeout=sandbox_runner.DOCKER_TIMEOUT_SECONDS: type("Probe", (), {"returncode": 0, "stdout": "27.0", "stderr": ""})(),
    )
    monkeypatch.setattr(sandbox_runner, "_image_available", lambda image: True)

    def fake_run(args, **kwargs):
        captured["args"] = args
        return type("Completed", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()

    monkeypatch.setattr(sandbox_runner.subprocess, "run", fake_run)
    result = sandbox_runner.run_check(tmp_path, "main.py", "python", timeout_seconds=5)

    args = captured["args"]
    assert result["runtime"] == "docker"
    assert args[0] == "docker"
    assert "--network" in args and args[args.index("--network") + 1] == "none"
    assert "--read-only" in args
    assert "--cap-drop" in args and args[args.index("--cap-drop") + 1] == "ALL"
    assert "--security-opt" in args and "no-new-privileges" in args
    assert "--memory" in args and sandbox_runner.DOCKER_MEMORY in args
    assert "--cpus" in args and sandbox_runner.DOCKER_CPUS in args
    assert "--mount" in args and "/workspace" in args


def test_arbitrary_checks_and_extensions_are_rejected(sandbox_root):
    with pytest.raises(sandbox_service.SandboxError):
        sandbox_service.write_file("demo", "run.bat", "whoami")

    sandbox_service.write_file("demo", "main.py", "print(1)")
    with pytest.raises(sandbox_service.SandboxError):
        sandbox_service.run_check("demo", "powershell", "main.py")


def test_workspace_does_not_follow_symlinks(sandbox_root, tmp_path):
    outside = tmp_path / "outside.py"
    outside.write_text("print('outside')", encoding="utf-8")
    link = sandbox_root / "demo" / "link.py"
    link.parent.mkdir(parents=True)
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation is unavailable on this Windows setup")

    with pytest.raises(sandbox_service.SandboxError):
        sandbox_service.read_file("demo", "link.py")


@pytest.mark.asyncio
async def test_agent_write_tool_requires_confirmation(monkeypatch):
    from backend.app.agent import orchestrator

    monkeypatch.setattr(orchestrator, "save_pending_action", lambda *args, **kwargs: (42, "nonce"))
    monkeypatch.setattr(orchestrator, "log_action", lambda *args, **kwargs: None)
    monkeypatch.setattr(orchestrator, "record_event", lambda *args, **kwargs: None)

    result = await orchestrator.execute_tool(
        {
            "function": {
                "name": "sandbox_write_file",
                "arguments": {
                    "session_id": "demo",
                    "path": "main.py",
                    "content": "print(1)",
                },
            }
        },
        "web_session",
    )

    assert result["requires_confirmation"] is True
    assert result["pending_action_id"] == 42
