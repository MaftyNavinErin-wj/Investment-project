$ErrorActionPreference = "Stop"

$share = "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie"
$request = Join-Path $share "bloomberg_request.json"
$exporter = Join-Path $share "bloomberg_export.py"

. (Join-Path $share "run_bloomberg_common.ps1")

Write-Host "Starting Bloomberg volatility update..."
Write-Host "Request: $request"
Write-Host "Exporter: $exporter"

Invoke-WithBloombergPython @($exporter, "--request", $request)

Write-Host ""
Write-Host "Latest output files:"
$files = @(
    "bloomberg_snapshot_latest.json",
    "bloomberg_history_latest.json",
    "bloomberg_news_latest.json",
    "bloomberg_field_search_latest.json",
    "bloomberg_field_info_latest.json"
)

foreach ($name in $files) {
    $path = Join-Path $share $name
    if (Test-Path -LiteralPath $path) {
        $item = Get-Item -LiteralPath $path
        [pscustomobject]@{
            Name = $item.Name
            LastWriteTime = $item.LastWriteTime
            Length = $item.Length
        }
    } else {
        [pscustomobject]@{
            Name = $name
            LastWriteTime = $null
            Length = $null
        }
    }
}

Write-Host ""
Write-Host "Quick JSON checks:"
foreach ($name in @("bloomberg_snapshot_latest.json", "bloomberg_history_latest.json")) {
    $path = Join-Path $share $name
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Host "$name missing" -ForegroundColor Red
        continue
    }

    try {
        $json = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
        $rowCount = 0
        if ($json.rows) {
            $rowCount = @($json.rows).Count
        }
        Write-Host "$name created_at=$($json.created_at) rows=$rowCount"
    } catch {
        Write-Host "$name JSON parse failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Bloomberg volatility update finished."
