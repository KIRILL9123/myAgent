param(
    [string]$RemoteNetwork = "192.168.2.0/24"
)

$ErrorActionPreference = "Stop"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$adminRole = [Security.Principal.WindowsBuiltInRole]::Administrator
if (-not $principal.IsInRole($adminRole)) {
    Write-Output "Requesting administrator permission to allow Mira on the local network only..."
    $arguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$PSCommandPath`"",
        "-RemoteNetwork", $RemoteNetwork
    )
    Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $arguments
    exit 0
}

$rules = @(
    @{ Name = "Mira Local Frontend"; Port = 5173; Description = "Mira personal dashboard on local LAN only" },
    @{ Name = "Mira Local Backend"; Port = 8000; Description = "Mira personal API on local LAN only" }
)

foreach ($rule in $rules) {
    $existing = Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue
    if (-not $existing) {
        New-NetFirewallRule `
            -DisplayName $rule.Name `
            -Direction Inbound `
            -Action Allow `
            -Protocol TCP `
            -LocalPort $rule.Port `
            -RemoteAddress $RemoteNetwork `
            -Profile Private,Public `
            -Description $rule.Description | Out-Null
    }
}

Write-Output "Mira LAN access is allowed for $RemoteNetwork on ports 5173 and 8000."
