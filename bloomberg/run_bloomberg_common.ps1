$ErrorActionPreference = "Stop"

function Invoke-WithBloombergPython {
    param([string[]]$ExtraArgs)

    $candidates = @(
        @{ Command = "python"; Args = @() },
        @{ Command = "py"; Args = @("-3") },
        @{ Command = "py"; Args = @() }
    )

    foreach ($candidate in $candidates) {
        $cmd = Get-Command $candidate.Command -ErrorAction SilentlyContinue
        if (-not $cmd) {
            continue
        }

        $testArgs = @()
        $testArgs += $candidate.Args
        $testArgs += @("-c", "import blpapi; print('blpapi=' + blpapi.version())")
        & $cmd.Source @testArgs
        if ($LASTEXITCODE -ne 0) {
            continue
        }

        Write-Host "Using Python: $($cmd.Source) $($candidate.Args -join ' ')"
        $runArgs = @()
        $runArgs += $candidate.Args
        $runArgs += $ExtraArgs
        & $cmd.Source @runArgs
        return
    }

    Write-Host "No Python interpreter with Bloomberg blpapi was found." -ForegroundColor Red
    Write-Host "Run these in the Bloomberg VDI PowerShell to diagnose/install:" -ForegroundColor Yellow
    Write-Host "  where python"
    Write-Host "  py -0p"
    Write-Host "  python -m pip show blpapi"
    Write-Host "  python -m pip install --index-url=https://blpapi.bloomberg.com/repository/releases/python/simple/ blpapi"
    throw "Missing Python module: blpapi"
}
