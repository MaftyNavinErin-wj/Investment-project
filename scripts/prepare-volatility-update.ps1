param(
    [string]$Share = "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie",
    [switch]$StatusOnly
)

$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$syncScript = Join-Path $projectRoot "scripts\sync-bloomberg-shared.ps1"

if ($StatusOnly) {
    & $syncScript -Mode Status -Share $Share
} else {
    & $syncScript -Mode Push -Share $Share
}

$vdiRunner = Join-Path $Share "run_bloomberg_volatility_update.ps1"

Write-Host ""
Write-Host "Run this inside Bloomberg VDI PowerShell:"
Write-Host "powershell -ExecutionPolicy Bypass -File `"$vdiRunner`""

Write-Host ""
Write-Host "After VDI finishes, run locally:"
Write-Host ".\scripts\sync-bloomberg-shared.ps1 -Mode Pull"
Write-Host ".\run-ai-radar.ps1"
