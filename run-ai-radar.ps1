$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Script = Join-Path $Root "ai-radar\daily_radar.py"

if (-not (Test-Path $Script)) {
  throw "Cannot find $Script"
}

$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) {
  $Python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $Python) {
  throw "Python is required. Install Python or add it to PATH."
}

& $Python.Source $Script

