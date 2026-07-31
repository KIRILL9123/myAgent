param(
    [int]$Port = 8000,
    [string]$ListenHost = "0.0.0.0",
    [int]$RestartDelaySeconds = 5
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { $python = "python" }
$logDir = Join-Path $projectRoot "logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$stopMarker = Join-Path $logDir "backend.stop"

if (Test-Path -LiteralPath $stopMarker) { Remove-Item -LiteralPath $stopMarker -Force }

while ($true) {
    $existing = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    if ($existing.Count -gt 0) {
        $owners = ($existing | Select-Object -ExpandProperty OwningProcess | Sort-Object -Unique) -join ","
        throw "Port $Port is already used by PID(s): $owners"
    }

    & $python -m uvicorn backend.app.main:app --host $ListenHost --port $Port
    $exitCode = $LASTEXITCODE
    if (Test-Path -LiteralPath $stopMarker) { Remove-Item -LiteralPath $stopMarker -Force; exit 0 }
    Add-Content -LiteralPath (Join-Path $logDir "backend-watchdog.log") -Value "$(Get-Date -Format o) backend exited with code $exitCode; restarting"
    Start-Sleep -Seconds $RestartDelaySeconds
}
