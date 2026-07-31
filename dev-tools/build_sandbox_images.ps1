param(
    [string]$PythonImage = "myagent-sandbox-python:latest",
    [string]$NodeImage = "myagent-sandbox-node:latest"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

docker info | Out-Null
docker build --file (Join-Path $projectRoot "docker\Dockerfile.sandbox-python") --tag $PythonImage (Join-Path $projectRoot "docker")
docker build --file (Join-Path $projectRoot "docker\Dockerfile.sandbox-node") --tag $NodeImage (Join-Path $projectRoot "docker")
