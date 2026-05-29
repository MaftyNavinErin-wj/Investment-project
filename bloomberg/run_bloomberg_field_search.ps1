$ErrorActionPreference = "Stop"
$share = "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie"
python (Join-Path $share "bloomberg_export.py") --request (Join-Path $share "bloomberg_request.json") --field-search "news headline story" "enterprise value ebitda" "pe ratio"
