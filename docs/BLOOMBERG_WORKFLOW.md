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

## Pull Latest Data Back

After the VDI export finishes, pull the generated latest files back into local `data/`:

```powershell
.\scripts\sync-bloomberg-shared.ps1 -Mode Pull
```

This copies:

- shared-drive `bloomberg_snapshot_latest.json` to `data/bloomberg_snapshot_latest.json`
- shared-drive `bloomberg_history_latest.json` to `data/bloomberg_history_latest.json`

To check timestamps and file sizes without copying:

```powershell
.\scripts\sync-bloomberg-shared.ps1 -Mode Status
```

## VDI Command

In Bloomberg VDI, run the exporter by full UNC path. This does not require changing the current directory:

```powershell
$share = "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie"
python (Join-Path $share "bloomberg_export.py") --request (Join-Path $share "bloomberg_request.json")
```

This exports both reference data and one-year daily historical data. For a quick reference-only check:

```powershell
$share = "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie"
python (Join-Path $share "bloomberg_export.py") --request (Join-Path $share "bloomberg_request.json") --reference-only
```

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

## Current Data Coverage

The current request exports:

- Reference: price, market cap, forward P/E, EV/EBITDA, EV/Sales, P/B, volume, 30D average volume, free float, short-interest ratio, beta, 30D volatility, 1D/5D/1M/3M/6M/1Y price changes.
- Historical: one year of daily `PX_LAST` for all equities, indices, rates, FX and commodity proxies in the request.
- Macro/cross-asset proxies: `SPX Index`, `NDX Index`, `SOX Index`, `VIX Index`, `USGG10YR Index`, `USGG2YR Index`, `DXY Curncy`, `HG1 Comdty`, `NG1 Comdty`, `CL1 Comdty`.
