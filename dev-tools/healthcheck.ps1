param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [switch]$CheckModel
)

$ErrorActionPreference = "Stop"
$health = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get -TimeoutSec 10
if ($health.status -ne "ok") { throw "Backend health is not ok" }
Write-Output "Backend: OK"

if ($CheckModel) {
    $modelUrl = if ($env:LLM_BASE_URL) { "$($env:LLM_BASE_URL.TrimEnd('/'))/models" } else { "http://127.0.0.1:8080/v1/models" }
    $model = Invoke-RestMethod -Uri $modelUrl -Method Get -TimeoutSec 10
    if (-not $model) { throw "Model server returned no data" }
    Write-Output "Model server: OK"
}
