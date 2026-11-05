import json
import os
import platform
import shutil
import subprocess
import time
from datetime import datetime, timezone
from typing import Any


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_metrics(detail: str) -> dict[str, Any]:
    return {
        "status": "degraded",
        "detail": detail,
        "generated_at": _timestamp(),
        "cpu": {"percent": None, "cores": os.cpu_count() or 1},
        "memory": {"total_bytes": None, "available_bytes": None, "used_percent": None},
        "disks": [],
        "processes": [],
        "process_count": None,
    }


def _run_powershell(script: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=8,
    )
    if completed.returncode != 0:
        raise RuntimeError("PowerShell diagnostics failed")
    output = completed.stdout.strip()
    if not output:
        raise RuntimeError("PowerShell diagnostics returned no data")
    parsed = json.loads(output)
    return parsed if isinstance(parsed, dict) else {}


def _windows_diagnostics() -> dict[str, Any]:
    script = r"""
$ErrorActionPreference = 'Stop'
$cpu = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
$os = Get-CimInstance Win32_OperatingSystem
$disks = @(Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
  [PSCustomObject]@{ name=$_.DeviceID; total_bytes=[int64]$_.Size; free_bytes=[int64]$_.FreeSpace }
})
$processes = @(Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 20 | ForEach-Object {
  $cpuSeconds = $null
  try { $cpuSeconds = [math]::Round($_.CPU, 2) } catch {}
  [PSCustomObject]@{ name=$_.ProcessName; pid=$_.Id; cpu_seconds=$cpuSeconds; memory_bytes=[int64]$_.WorkingSet64 }
})
[PSCustomObject]@{
  cpu_percent=[math]::Round([double]$cpu, 1)
  cores=[int]$env:NUMBER_OF_PROCESSORS
  memory_total_bytes=[int64]$os.TotalVisibleMemorySize * 1KB
  memory_available_bytes=[int64]$os.FreePhysicalMemory * 1KB
  disks=$disks
  processes=$processes
  process_count=(Get-Process).Count
} | ConvertTo-Json -Depth 5 -Compress
"""
    raw = _run_powershell(script)
    total = raw.get("memory_total_bytes")
    available = raw.get("memory_available_bytes")
    used_percent = None
    if total:
        used_percent = round((1 - (available or 0) / total) * 100, 1)
    disks = []
    for disk in raw.get("disks") or []:
        total_bytes = disk.get("total_bytes") or 0
        free_bytes = disk.get("free_bytes") or 0
        disks.append({
            "name": disk.get("name"), "total_bytes": total_bytes,
            "free_bytes": free_bytes,
            "used_percent": round((1 - free_bytes / total_bytes) * 100, 1) if total_bytes else None,
        })
    return {
        "status": "ok", "detail": None, "generated_at": _timestamp(),
        "cpu": {"percent": raw.get("cpu_percent"), "cores": raw.get("cores") or os.cpu_count()},
        "memory": {"total_bytes": total, "available_bytes": available, "used_percent": used_percent},
        "disks": disks, "processes": raw.get("processes") or [], "process_count": raw.get("process_count"),
    }


def _unix_diagnostics() -> dict[str, Any]:
    """Portable fallback; keeps the contract ready for a future Mac host."""
    root = "/"
    disk = shutil.disk_usage(root)
    total_memory = available_memory = None
    try:
        with open("/proc/meminfo", encoding="utf-8") as handle:
            values = {}
            for line in handle:
                key, value = line.split(":", 1)
                values[key] = int(value.strip().split()[0]) * 1024
            total_memory = values.get("MemTotal")
            available_memory = values.get("MemAvailable")
    except (FileNotFoundError, OSError, ValueError):
        pass
    processes: list[dict[str, Any]] = []
    try:
        result = subprocess.run(["ps", "-eo", "comm=,pid=,rss="], capture_output=True, text=True, timeout=3)
        for line in result.stdout.splitlines()[:20]:
            parts = line.split()
            if len(parts) >= 3:
                processes.append({"name": parts[0], "pid": int(parts[1]), "cpu_seconds": None, "memory_bytes": int(parts[2]) * 1024})
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    used_percent = round((1 - available_memory / total_memory) * 100, 1) if total_memory and available_memory is not None else None
    return {
        "status": "ok", "detail": None, "generated_at": _timestamp(),
        "cpu": {"percent": round(os.getloadavg()[0] / (os.cpu_count() or 1) * 100, 1) if hasattr(os, "getloadavg") else None, "cores": os.cpu_count() or 1},
        "memory": {"total_bytes": total_memory, "available_bytes": available_memory, "used_percent": used_percent},
        "disks": [{"name": root, "total_bytes": disk.total, "free_bytes": disk.free, "used_percent": round((1 - disk.free / disk.total) * 100, 1) if disk.total else None}],
        "processes": processes, "process_count": len(processes),
    }


def get_host_diagnostics() -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = _windows_diagnostics() if platform.system() == "Windows" else _unix_diagnostics()
    except (OSError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        result = _empty_metrics(type(exc).__name__)
    result["collection_latency_ms"] = round((time.monotonic() - started) * 1000, 2)
    result["platform"] = platform.system()
    return result
