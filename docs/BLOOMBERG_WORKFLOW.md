# Bloomberg Data Workflow

This project cannot connect to Bloomberg Desktop API from the local machine when Bloomberg Terminal runs inside VDI.
The fixed workflow is now shared-drive based:

1. Maintain the canonical files locally:
   - `data/bloomberg_request.json`
   - `scripts/bloomberg_export.py`
2. Sync both files to the Bloomberg shared-drive folder:
   - `\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie\bloomberg_request.json`
   - `\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie\bloomberg_export.py`
3. Run the exporter inside Bloomberg VDI directly from the shared-drive folder while Bloomberg Terminal is logged in.
4. The exporter writes:
   - `\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie\bloomberg_snapshot_latest.json`
   - `\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie\bloomberg_snapshot_YYYY-MM-DD.json`
   - `\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie\bloomberg_history_latest.json`
   - `\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie\bloomberg_history_YYYY-MM-DD.json`
   - `\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie\bloomberg_news_latest.json` when Bloomberg News export is enabled and supported by the VDI API session
   - `\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie\bloomberg_news_YYYY-MM-DD.json`
5. The local daily report reads Bloomberg data in this order:
   - shared-drive `bloomberg_snapshot_latest.json`
   - local `data/bloomberg_snapshot_latest.json`
   - local `data/bloomberg_snapshot.json`
   - desktop `bloomberg_snapshot.json`
   - original fallback sources

## Sync Files To Shared Drive

From the local project, use the helper script:

```powershell
.\scripts\sync-bloomberg-shared.ps1 -Mode Push
```

Manual equivalent:

```powershell
$share = "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie"
Copy-Item .\data\bloomberg_request.json -Destination (Join-Path $share "bloomberg_request.json") -Force
Copy-Item .\scripts\bloomberg_export.py -Destination (Join-Path $share "bloomberg_export.py") -Force
```

Codex can perform this sync when shared-drive access is available.

The sync also writes VDI runner scripts to the shared-drive folder:

- `run_bloomberg_reference.ps1`
- `run_bloomberg_full.ps1`
- `run_bloomberg_field_search.ps1`
- `run_bloomberg_comprehensive_update.ps1`

## Pull Latest Data Back

After the VDI export finishes, pull the generated latest files back into local `data/`:

```powershell
.\scripts\sync-bloomberg-shared.ps1 -Mode Pull
```

This copies:

- shared-drive `bloomberg_snapshot_latest.json` to `data/bloomberg_snapshot_latest.json`
- shared-drive `bloomberg_history_latest.json` to `data/bloomberg_history_latest.json`
- shared-drive `bloomberg_news_latest.json` to `data/bloomberg_news_latest.json` when present

To check timestamps and file sizes without copying:

```powershell
.\scripts\sync-bloomberg-shared.ps1 -Mode Status
```

## VDI Command

In Bloomberg VDI, run the exporter by full UNC path. This does not require changing the current directory:

```powershell
powershell -ExecutionPolicy Bypass -File "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie\run_bloomberg_comprehensive_update.ps1"
```

If PowerShell returns `running scripts is disabled on this system`, use a one-time execution-policy bypass:

```powershell
powershell -ExecutionPolicy Bypass -File "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie\run_bloomberg_full.ps1"
```

The comprehensive runner performs preflight checks, runs the full reference and history export, prints output file status, validates the latest JSON files, and writes a timestamped log in the shared-drive folder. To additionally run the best-effort Bloomberg News diagnostic probe:

```powershell
powershell -ExecutionPolicy Bypass -File "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie\run_bloomberg_comprehensive_update.ps1" -NewsProbe
```

For reference-only:

```powershell
powershell -ExecutionPolicy Bypass -File "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie\run_bloomberg_reference.ps1"
```

Manual equivalent:

```powershell
$share = "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie"
python (Join-Path $share "bloomberg_export.py") --request (Join-Path $share "bloomberg_request.json")
```

This exports both reference data and one-year daily historical data. For a quick reference-only check:

```powershell
$share = "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie"
python (Join-Path $share "bloomberg_export.py") --request (Join-Path $share "bloomberg_request.json") --reference-only
```

Bloomberg News status:

As of the 2026-05-29 VDI probe, this Bloomberg Desktop API session does not expose Bloomberg News search:

- `//blp/refdata/NewsSearchRequest` returned `Operation 'NewsSearchRequest' was not found`.
- `//blp/news` returned `openService false`.

Therefore keyword-style Bloomberg News search is not available through the tested Desktop API services. The exporter now supports a different diagnostic path: `//blp/refdata` `ReferenceDataRequest` using `NEWS_HEADLINES` for configured securities, then `NEWS_STORY` for returned story IDs if Bloomberg returns them.

`news.enabled` remains disabled in `data/bloomberg_request.json` by default so normal reference/history exports stay clean. `--news-only` still runs the diagnostic news pull even while `news.enabled=false`.

For a future Bloomberg News-only smoke test:

```powershell
$share = "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie"
python (Join-Path $share "bloomberg_export.py") --request (Join-Path $share "bloomberg_request.json") --news-only
```

News export is best-effort and non-blocking. If `NEWS_HEADLINES` / `NEWS_STORY` are unavailable for the current entitlement, the exporter writes field exceptions into `bloomberg_news_latest.json` and still leaves reference/history workflow unchanged.

If `NEWS_HEADLINES` returns `BAD_FLD`, run a field probe by temporarily setting `news.mode` to `field_probe` in `bloomberg_request.json`, then rerun `--news-only`. The probe tests candidate news/headline/story fields against `DELL US Equity` and reports `valid_fields` / `invalid_fields`. If no valid field appears, use Bloomberg Terminal `FLDS <GO>` or ask Bloomberg support for the exact Desktop API refdata fields available under the account entitlement.

If `Set-Location` / `cd` to the UNC path returns `Access is denied`, do not rely on `cd`. First test whether the session can read the folder:

```powershell
$share = "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie"
Test-Path -LiteralPath $share
Get-ChildItem -LiteralPath $share
```

If `Get-ChildItem` works but `cd` fails, keep using the full UNC command above. If both fail, the Bloomberg VDI user/session does not have access to the share; open a normal non-admin PowerShell, access the folder in File Explorer, or map the share with the correct domain credentials. `pushd` can also be used to map a temporary drive letter:

```powershell
pushd "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie"
python .\bloomberg_export.py --request .\bloomberg_request.json
popd
```

If the shared drive is unavailable but the script and request are available locally, write outputs to a local folder:

```powershell
python .\bloomberg_export.py --request .\bloomberg_request.json --output-dir "$env:USERPROFILE\Desktop"
```

Then copy `bloomberg_snapshot_latest.json` and `bloomberg_history_latest.json` back to local `data/`.

## Updating The Request

When the report scope changes, update only `data/bloomberg_request.json`:

- Add or remove securities under `securities`.
- Add fields under `reference_fields`.
- Add historical fields or change lookback under `historical`.
- Keep `quote` equal to the report ticker so the local report can match rows.
- Keep `security` equal to Bloomberg security syntax, for example:
  - `NVDA US Equity`
  - `700 HK Equity`
  - `300750 CH Equity`
  - `000660 KS Equity`
  - `2454 TT Equity`

The exporter can stay unchanged unless the report needs a new request type such as intraday bars, estimate-history time series, or Bloomberg news.

After changing `data/bloomberg_request.json`, run:

```powershell
.\scripts\sync-bloomberg-shared.ps1 -Mode Push
```

Then rerun the VDI command above.

### Current Expanded AI Capex Coverage

The request now covers more than equity valuation. The report separates AI capex into demand, financing, resources and crowding:

- Demand and AI infrastructure platforms: hyperscalers, Oracle, CoreWeave, Dell and AI server/networking representatives.
- Data center asset proxies: Equinix and Digital Realty.
- Power/resource proxies: Constellation Energy, Vistra, NextEra, copper, natural gas and crude.
- Financing proxies: US 2Y/5Y/10Y/30Y yields plus IG/HY OAS indices where Bloomberg entitlement supports them.
- Crowding proxies: SOX, NDX, SPX and VIX.

After this kind of request expansion, run at least the reference export on the Bloomberg VDI:

```powershell
powershell -ExecutionPolicy Bypass -File "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie\run_bloomberg_reference.ps1"
```

If proxy credit indices such as `LUACOAS Index` or `LF98OAS Index` return Bloomberg errors, keep the output and verify the correct ticker in Terminal. Equity and macro rows should still export even if a few proxy indices fail.

## Bloomberg Field Discovery

Do not guess Bloomberg field names. Use the API field metadata service from VDI:

```powershell
$share = "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie"
python (Join-Path $share "bloomberg_export.py") --request (Join-Path $share "bloomberg_request.json") --field-search "news headline story" "enterprise value ebitda" "pe ratio"
```

This writes:

- `bloomberg_field_search_latest.json`
- `bloomberg_field_search_YYYY-MM-DD.json`

To inspect specific fields:

```powershell
$share = "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie"
python (Join-Path $share "bloomberg_export.py") --request (Join-Path $share "bloomberg_request.json") --field-info PE_RATIO BEST_PE_RATIO EV_TO_T12M_EBITDA NEWS_HEADLINES NEWS_STORY
```

This writes:

- `bloomberg_field_info_latest.json`
- `bloomberg_field_info_YYYY-MM-DD.json`

After running either command, pull results locally:

```powershell
.\scripts\sync-bloomberg-shared.ps1 -Mode Pull
```

## Current Data Coverage

The current request exports:

- Reference: price, market cap, TTM P/E, forward P/E, current EV/TTM EBITDA, periodic EV/TTM EBITDA, BEst EV/EBITDA, EV/Sales, P/B, volume, 30D average volume, free float, short-interest ratio, beta, 30D volatility, 1D/5D/1M/3M/6M/1Y price changes.
- Historical: one year of daily `PX_LAST` for all equities, indices, rates, FX and commodity proxies in the request.
- News: configurable event-driven Bloomberg News searches for AI server earnings, hyperscaler capex, networking/optics, power/cooling and AI ROI/application signals.
- Macro/cross-asset proxies: `SPX Index`, `NDX Index`, `SOX Index`, `VIX Index`, `USGG10YR Index`, `USGG2YR Index`, `DXY Curncy`, `HG1 Comdty`, `NG1 Comdty`, `CL1 Comdty`.
