from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import webbrowser
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _configured_roots() -> list[Path]:
    configured = os.getenv("HOST_CONTROL_ALLOWED_ROOTS", "")
    roots = [PROJECT_ROOT.resolve()]
    for raw in configured.split(os.pathsep):
        if raw.strip():
            try:
                roots.append(Path(raw.strip()).expanduser().resolve())
            except OSError:
                continue
    unique: list[Path] = []
    for root in roots:
        if root not in unique:
            unique.append(root)
    return unique


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def get_capabilities() -> dict:
    system = platform.system()
    return {
        "platform": system,
        "adapter": "windows" if system == "Windows" else "macos" if system == "Darwin" else "unix",
        "actions": {
            "get_host_diagnostics": {"permission": "green", "available": True},
            "open_url": {"permission": "red", "available": True},
            "open_path": {"permission": "red", "available": True},
        },
        "allowed_path_roots": [str(root) for root in _configured_roots()],
        "restrictions": [
            "No arbitrary shell commands",
            "No process termination or shutdown in v1",
            "open_path is limited to configured roots",
            "open_url accepts only http and https",
        ],
    }


def _open_path(path: Path) -> None:
    system = platform.system()
    if system == "Windows":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif system == "Darwin":
        subprocess.Popen(["open", str(path)], start_new_session=True)
    else:
        opener = shutil.which("xdg-open")
        if not opener:
            raise RuntimeError("No host path opener is available")
        subprocess.Popen([opener, str(path)], start_new_session=True)


def execute(action: str, target: str) -> dict:
    action = (action or "").strip()
    target = (target or "").strip()
    if action == "open_url":
        parsed = urlparse(target)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return {"status": "error", "message": "Разрешены только корректные HTTP/HTTPS URL."}
        opened = webbrowser.open(target, new=0, autoraise=True)
        return {"status": "success" if opened else "degraded", "action": action, "target": target, "message": "URL открыт на компьютере." if opened else "Команда открытия URL отправлена, но браузер не подтвердил результат."}

    if action == "open_path":
        if not target:
            return {"status": "error", "message": "Путь не указан."}
        path = Path(target).expanduser().resolve()
        if not any(_is_under(path, root) for root in _configured_roots()):
            return {"status": "error", "message": "Путь находится вне разрешённых директорий."}
        if not path.exists():
            return {"status": "error", "message": "Файл или папка не найдены."}
        _open_path(path)
        return {"status": "success", "action": action, "target": str(path), "message": "Путь открыт на компьютере."}

    return {"status": "error", "message": f"Неизвестное действие host control: {action}"}
