param([string]$TaskName = "Mira Backend Watchdog")

$ErrorActionPreference = "Stop"
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Output "Removed '$TaskName'."
