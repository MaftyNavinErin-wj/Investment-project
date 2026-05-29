param(
    [ValidateSet("Status", "Push", "Pull", "RoundTrip")]
    [string]$Mode = "Status",

    [string]$Share = "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie"
)

$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$requestLocal = Join-Path $projectRoot "data\bloomberg_request.json"
$exporterLocal = Join-Path $projectRoot "scripts\bloomberg_export.py"
$snapshotLocal = Join-Path $projectRoot "data\bloomberg_snapshot_latest.json"
$historyLocal = Join-Path $projectRoot "data\bloomberg_history_latest.json"

$requestShare = Join-Path $Share "bloomberg_request.json"
$exporterShare = Join-Path $Share "bloomberg_export.py"
$snapshotShare = Join-Path $Share "bloomberg_snapshot_latest.json"
$historyShare = Join-Path $Share "bloomberg_history_latest.json"

function Test-Share {
    if (-not (Test-Path -LiteralPath $Share)) {
        throw "Bloomberg share is not reachable: $Share"
    }
}

function Show-ItemStatus {
    param([string[]]$Paths)

    foreach ($path in $Paths) {
        if (Test-Path -LiteralPath $path) {
            Get-Item -LiteralPath $path | Select-Object FullName, LastWriteTime, Length
        } else {
            [pscustomobject]@{
                FullName = $path
                LastWriteTime = $null
                Length = $null
            }
        }
    }
}

function Push-BloombergFiles {
    Test-Share
    Copy-Item -LiteralPath $requestLocal -Destination $requestShare -Force
    Copy-Item -LiteralPath $exporterLocal -Destination $exporterShare -Force
    Show-ItemStatus @($requestShare, $exporterShare)
}

function Pull-BloombergLatest {
    Test-Share
    Copy-Item -LiteralPath $snapshotShare -Destination $snapshotLocal -Force
    Copy-Item -LiteralPath $historyShare -Destination $historyLocal -Force
    Show-ItemStatus @($snapshotLocal, $historyLocal)
}

switch ($Mode) {
    "Status" {
        Test-Share
        Show-ItemStatus @($requestShare, $exporterShare, $snapshotShare, $historyShare, $requestLocal, $exporterLocal, $snapshotLocal, $historyLocal)
    }
    "Push" {
        Push-BloombergFiles
    }
    "Pull" {
        Pull-BloombergLatest
    }
    "RoundTrip" {
        Push-BloombergFiles
        Pull-BloombergLatest
    }
}
