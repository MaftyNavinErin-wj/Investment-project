$ErrorActionPreference = "Stop"
$share = "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie"
. (Join-Path $share "run_bloomberg_common.ps1")
Invoke-WithBloombergPython @((Join-Path $share "bloomberg_export.py"), "--request", (Join-Path $share "bloomberg_request.json"), "--field-search", "news headline story", "enterprise value ebitda", "pe ratio")
