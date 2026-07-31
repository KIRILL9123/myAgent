"""Docker execution backend for the Code Sandbox.

The caller has already validated the workspace and relative source path. This
module only builds a fixed ``docker run`` argument list; it never invokes a
shell and never accepts an arbitrary command string.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any


DOCKER_TIMEOUT_SECONDS = 8
DOCKER_MEMORY = "256m"
DOCKER_CPUS = "1.0"
DOCKER_PIDS_LIMIT = "64"
DOCKER_OUTPUT_LIMIT = 20_000
PYTHON_IMAGE = os.getenv("CODE_SANDBOX_PYTHON_IMAGE", "myagent-sandbox-python:latest")
NODE_IMAGE = os.getenv("CODE_SANDBOX_NODE_IMAGE", "myagent-sandbox-node:latest")
IMAGE_RE = re.compile(r"^[a-z0-9][a-z0-9./:_-]{0,127}$")


class DockerSandboxError(ValueError):
    """A Docker runner is unavailable or rejected the bounded execution."""


def _creation_flags() -> dict[str, int]:
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def _docker_binary() -> str | None:
    return shutil.which("docker")


def _run_docker_probe(args: list[str], timeout: int = DOCKER_TIMEOUT_SECONDS) -> subprocess.CompletedProcess[str] | None:
    binary = _docker_binary()
    if not binary:
        return None
    try:
        return subprocess.run(
            [binary, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
            **_creation_flags(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def runtime_status() -> dict[str, Any]:
    binary = _docker_binary()
    if not binary:
        return {
            "configured_runtime": "docker",
            "docker_cli": False,
            "docker_daemon": False,
            "ready": False,
            "message": "Docker CLI не найден.",
        }
    probe = _run_docker_probe(["info", "--format", "{{.ServerVersion}}"])
    if not probe or probe.returncode != 0:
        return {
            "configured_runtime": "docker",
            "docker_cli": True,
            "docker_daemon": False,
            "ready": False,
            "message": "Docker Desktop/daemon не запущен.",
        }
    return {
        "configured_runtime": "docker",
        "docker_cli": True,
        "docker_daemon": True,
        "ready": True,
        "server_version": probe.stdout.strip(),
        "message": "Docker runner готов.",
    }


def _validate_image(image: str) -> str:
    if not IMAGE_RE.fullmatch(image):
        raise DockerSandboxError("Недопустимое имя Docker-образа в настройках песочницы.")
    return image


def _image_available(image: str) -> bool:
    probe = _run_docker_probe(["image", "inspect", image])
    return bool(probe and probe.returncode == 0)


def _cleanup_container(binary: str, container_name: str) -> None:
    try:
        subprocess.run(
            [binary, "rm", "--force", container_name],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=DOCKER_TIMEOUT_SECONDS,
            shell=False,
            **_creation_flags(),
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def _command_for_check(check: str, relative_path: str) -> tuple[str, list[str]]:
    if check in {"python", "pytest", "compile_python"}:
        image = _validate_image(PYTHON_IMAGE)
        if check == "python":
            command = ["python", "-I", "-B", relative_path]
        elif check == "pytest":
            command = ["python", "-I", "-B", "-m", "pytest", relative_path]
        else:
            command = ["python", "-I", "-B", "-m", "py_compile", relative_path]
        return image, command
    if check == "node":
        return _validate_image(NODE_IMAGE), ["node", relative_path]
    raise DockerSandboxError(f"Неподдерживаемая проверка: {check}")


def run_check(
    workspace: Path,
    relative_path: str,
    check: str,
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    status = runtime_status()
    if not status["ready"]:
        raise DockerSandboxError(status["message"])

    image, command = _command_for_check(check, relative_path)
    if not _image_available(image):
        raise DockerSandboxError(
            f"Docker-образ {image} не найден. Соберите его командой из docs/design/CODE_SANDBOX.md."
        )

    binary = _docker_binary()
    if not binary:
        raise DockerSandboxError("Docker CLI не найден.")
    container_name = f"myagent-sbx-{uuid.uuid4().hex[:16]}"
    host_workspace = str(workspace.resolve())
    docker_args = [
        binary,
        "run",
        "--rm",
        "--name",
        container_name,
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        DOCKER_PIDS_LIMIT,
        "--memory",
        DOCKER_MEMORY,
        "--cpus",
        DOCKER_CPUS,
        "--user",
        "1000:1000",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
        "--mount",
        f"type=bind,source={host_workspace},target=/workspace",
        "--workdir",
        "/workspace",
        image,
        *command,
    ]

    try:
        completed = subprocess.run(
            docker_args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            shell=False,
            **_creation_flags(),
        )
    except subprocess.TimeoutExpired as exc:
        _cleanup_container(binary, container_name)
        stdout = str(exc.stdout or "")[:DOCKER_OUTPUT_LIMIT]
        stderr = str(exc.stderr or "")[:DOCKER_OUTPUT_LIMIT]
        return {
            "status": "timeout",
            "check": check,
            "path": relative_path,
            "stdout": stdout,
            "stderr": stderr,
            "message": f"Docker-проверка остановлена по таймауту ({timeout_seconds} сек.).",
        }

    return {
        "status": "success" if completed.returncode == 0 else "failed",
        "check": check,
        "path": relative_path,
        "return_code": completed.returncode,
        "stdout": completed.stdout[:DOCKER_OUTPUT_LIMIT],
        "stderr": completed.stderr[:DOCKER_OUTPUT_LIMIT],
        "runtime": "docker",
    }
