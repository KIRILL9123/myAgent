param(
    [int]$Port = 8000,
    [string]$ListenHost = "0.0.0.0"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$listeners = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
if ($listeners.Count -gt 0) {
    $owners = ($listeners | Select-Object -ExpandProperty OwningProcess | Sort-Object -Unique) -join ", "
    Write-Error "Port $Port already in use (PID: $owners). Stop the old backend process first; no process was terminated automatically."
    exit 1
}

$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $python = "python"
}

& $python -m uvicorn backend.app.main:app --host $ListenHost --port $Port
exit $LASTEXITCODE
