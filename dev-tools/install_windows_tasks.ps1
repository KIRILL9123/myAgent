param(
    [string]$TaskName = "Mira Backend Watchdog",
    [int]$Port = 8000,
    [string]$ListenHost = "0.0.0.0"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$watchdog = Join-Path $projectRoot "dev-tools\run_backend_watchdog.ps1"
$currentUser = (whoami).Trim()
$argument = "-NoProfile -ExecutionPolicy Bypass -File `"$watchdog`" -Port $Port -ListenHost $ListenHost"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argument -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $currentUser
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Days 3650)
$principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Write-Output "Installed '$TaskName'. It starts the backend watchdog at user logon."
Write-Output "Run dev-tools\healthcheck.ps1 after login to verify the service."
