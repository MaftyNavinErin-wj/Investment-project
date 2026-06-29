param(
    [string]$Share = "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie",
    [switch]$NewsProbe
)

$ErrorActionPreference = "Stop"

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "== $Title ==" -ForegroundColor Cyan
}

function Test-TcpPort {
    param(
        [string]$HostName = "127.0.0.1",
        [int]$Port = 8194,
        [int]$TimeoutMs = 2000
    )

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $async = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) {
            return $false
        }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function Show-FileStatus {
    param([string[]]$Names)

    foreach ($name in $Names) {
        $path = Join-Path $Share $name
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
}

function Get-ArrayCount {
    param($Value)
    if ($null -eq $Value) {
        return 0
    }
    return @($Value).Count
}

function Show-JsonSummary {
    param(
        [string]$Name,
        [ValidateSet("Snapshot", "History", "News")]
        [string]$Kind
    )

    $path = Join-Path $Share $Name
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Host "$Name missing" -ForegroundColor Red
        return
    }

    try {
        $json = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
        $rows = @($json.rows)
        if ($Kind -eq "Snapshot") {
            $bad = @($rows | Where-Object { $_.security_error -or (Get-ArrayCount $_.field_errors) -gt 0 })
            Write-Host "$Name created_at=$($json.created_at) rows=$($rows.Count) rows_with_errors=$($bad.Count)"
            if ($bad.Count -gt 0) {
                $bad | Select-Object -First 15 | ForEach-Object {
                    Write-Host "  - $($_.security) security_error=$($_.security_error) field_errors=$(Get-ArrayCount $_.field_errors)" -ForegroundColor Yellow
                }
            }
        } elseif ($Kind -eq "History") {
            $bad = @($rows | Where-Object { $_.security_error -or (Get-ArrayCount $_.field_exceptions) -gt 0 })
            $points = 0
            foreach ($row in $rows) {
                $points += Get-ArrayCount $row.field_data
            }
            Write-Host "$Name created_at=$($json.created_at) rows=$($rows.Count) points=$points rows_with_errors=$($bad.Count)"
            if ($bad.Count -gt 0) {
                $bad | Select-Object -First 15 | ForEach-Object {
                    Write-Host "  - $($_.security) security_error=$($_.security_error) field_exceptions=$(Get-ArrayCount $_.field_exceptions)" -ForegroundColor Yellow
                }
            }
        } else {
            $errors = Get-ArrayCount $json.errors
            Write-Host "$Name created_at=$($json.created_at) rows=$($rows.Count) errors=$errors"
            if ($errors -gt 0) {
                @($json.errors) | Select-Object -First 10 | ForEach-Object {
                    Write-Host "  - $_" -ForegroundColor Yellow
                }
            }
        }
    } catch {
        Write-Host "$Name JSON parse failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

if (-not (Test-Path -LiteralPath $Share)) {
    throw "Bloomberg share is not reachable: $Share"
}

$request = Join-Path $Share "bloomberg_request.json"
$exporter = Join-Path $Share "bloomberg_export.py"
$common = Join-Path $Share "run_bloomberg_common.ps1"

foreach ($path in @($request, $exporter, $common)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Required file missing: $path"
    }
}

$logPath = Join-Path $Share ("run_bloomberg_comprehensive_update_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
try {
    Start-Transcript -LiteralPath $logPath -Force | Out-Null
} catch {
    Write-Host "Could not start transcript: $($_.Exception.Message)" -ForegroundColor Yellow
}

try {
    Write-Section "Bloomberg comprehensive update"
    Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Host "Share: $Share"
    Write-Host "Request: $request"
    Write-Host "Exporter: $exporter"
    Write-Host "NewsProbe: $NewsProbe"

    Write-Section "Input files"
    Show-FileStatus @(
        "bloomberg_request.json",
        "bloomberg_export.py",
        "run_bloomberg_common.ps1"
    ) | Format-Table -AutoSize

    Write-Section "Request summary"
    $requestJson = Get-Content -LiteralPath $request -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Host "description=$($requestJson.description)"
    Write-Host "securities=$(Get-ArrayCount $requestJson.securities)"
    Write-Host "reference_fields=$(Get-ArrayCount $requestJson.reference_fields)"
    Write-Host "historical_enabled=$($requestJson.historical.enabled) lookback_days=$($requestJson.historical.lookback_days)"
    Write-Host "news_enabled=$($requestJson.news.enabled) news_mode=$($requestJson.news.mode)"

    Write-Section "Bloomberg API preflight"
    if (Test-TcpPort -HostName "127.0.0.1" -Port 8194) {
        Write-Host "127.0.0.1:8194 is reachable."
    } else {
        Write-Host "127.0.0.1:8194 is not reachable. Make sure Bloomberg Terminal is open and logged in before continuing." -ForegroundColor Yellow
    }

    . $common

    Write-Section "Run reference and history export"
    Invoke-WithBloombergPython @($exporter, "--request", $request)

    if ($NewsProbe) {
        Write-Section "Run optional Bloomberg news probe"
        Invoke-WithBloombergPython @($exporter, "--request", $request, "--news-only")
    }

    Write-Section "Output files"
    Show-FileStatus @(
        "bloomberg_snapshot_latest.json",
        "bloomberg_history_latest.json",
        "bloomberg_news_latest.json",
        "bloomberg_field_search_latest.json",
        "bloomberg_field_info_latest.json"
    ) | Format-Table -AutoSize

    Write-Section "JSON checks"
    Show-JsonSummary -Name "bloomberg_snapshot_latest.json" -Kind Snapshot
    Show-JsonSummary -Name "bloomberg_history_latest.json" -Kind History
    if ($NewsProbe -or (Test-Path -LiteralPath (Join-Path $Share "bloomberg_news_latest.json"))) {
        Show-JsonSummary -Name "bloomberg_news_latest.json" -Kind News
    }

    Write-Section "Finished"
    Write-Host "Finished: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    Write-Host "Log: $logPath"
} finally {
    try {
        Stop-Transcript | Out-Null
    } catch {
    }
}
