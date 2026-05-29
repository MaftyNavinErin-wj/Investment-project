param(
    [ValidateSet("Status", "Push", "Pull", "RoundTrip")]
    [string]$Mode = "Status",

    [string]$Share = "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie"
)

$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$requestLocal = Join-Path $projectRoot "data\bloomberg_request.json"
$exporterLocal = Join-Path $projectRoot "scripts\bloomberg_export.py"
$runnerReferenceLocal = Join-Path $projectRoot "bloomberg\run_bloomberg_reference.ps1"
$runnerFullLocal = Join-Path $projectRoot "bloomberg\run_bloomberg_full.ps1"
$runnerFieldSearchLocal = Join-Path $projectRoot "bloomberg\run_bloomberg_field_search.ps1"
$snapshotLocal = Join-Path $projectRoot "data\bloomberg_snapshot_latest.json"
$historyLocal = Join-Path $projectRoot "data\bloomberg_history_latest.json"
$newsLocal = Join-Path $projectRoot "data\bloomberg_news_latest.json"
$fieldSearchLocal = Join-Path $projectRoot "data\bloomberg_field_search_latest.json"
$fieldInfoLocal = Join-Path $projectRoot "data\bloomberg_field_info_latest.json"

$requestShare = Join-Path $Share "bloomberg_request.json"
$exporterShare = Join-Path $Share "bloomberg_export.py"
$runnerReferenceShare = Join-Path $Share "run_bloomberg_reference.ps1"
$runnerFullShare = Join-Path $Share "run_bloomberg_full.ps1"
$runnerFieldSearchShare = Join-Path $Share "run_bloomberg_field_search.ps1"
$snapshotShare = Join-Path $Share "bloomberg_snapshot_latest.json"
$historyShare = Join-Path $Share "bloomberg_history_latest.json"
$newsShare = Join-Path $Share "bloomberg_news_latest.json"
$fieldSearchShare = Join-Path $Share "bloomberg_field_search_latest.json"
$fieldInfoShare = Join-Path $Share "bloomberg_field_info_latest.json"

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
    Copy-Item -LiteralPath $runnerReferenceLocal -Destination $runnerReferenceShare -Force
    Copy-Item -LiteralPath $runnerFullLocal -Destination $runnerFullShare -Force
    Copy-Item -LiteralPath $runnerFieldSearchLocal -Destination $runnerFieldSearchShare -Force
    Show-ItemStatus @($requestShare, $exporterShare, $runnerReferenceShare, $runnerFullShare, $runnerFieldSearchShare)
}

function Pull-BloombergLatest {
    Test-Share
    Copy-Item -LiteralPath $snapshotShare -Destination $snapshotLocal -Force
    Copy-Item -LiteralPath $historyShare -Destination $historyLocal -Force
    if (Test-Path -LiteralPath $newsShare) {
        Copy-Item -LiteralPath $newsShare -Destination $newsLocal -Force
    }
    if (Test-Path -LiteralPath $fieldSearchShare) {
        Copy-Item -LiteralPath $fieldSearchShare -Destination $fieldSearchLocal -Force
    }
    if (Test-Path -LiteralPath $fieldInfoShare) {
        Copy-Item -LiteralPath $fieldInfoShare -Destination $fieldInfoLocal -Force
    }
    Show-ItemStatus @($snapshotLocal, $historyLocal, $newsLocal, $fieldSearchLocal, $fieldInfoLocal)
}

switch ($Mode) {
    "Status" {
        Test-Share
        Show-ItemStatus @($requestShare, $exporterShare, $snapshotShare, $historyShare, $newsShare, $fieldSearchShare, $fieldInfoShare, $requestLocal, $exporterLocal, $snapshotLocal, $historyLocal, $newsLocal, $fieldSearchLocal, $fieldInfoLocal)
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
