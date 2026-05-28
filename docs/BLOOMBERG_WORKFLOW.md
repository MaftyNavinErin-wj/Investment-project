# Bloomberg Data Workflow

This project cannot connect to Bloomberg Desktop API from the local machine when Bloomberg Terminal runs inside VDI.
The fixed workflow is:

1. Maintain the data request locally in `data/bloomberg_request.json`.
2. Copy `data/bloomberg_request.json` and `scripts/bloomberg_export.py` to the Bloomberg VDI.
3. Run the exporter inside VDI while Bloomberg Terminal is logged in.
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

## VDI Command

From the folder containing both files:

```powershell
python .\bloomberg_export.py --request .\bloomberg_request.json
```

This exports both reference data and one-year daily historical data. For a quick reference-only check:

```powershell
python .\bloomberg_export.py --request .\bloomberg_request.json --reference-only
```

If the shared drive is unavailable, write to a local folder:

```powershell
python .\bloomberg_export.py --request .\bloomberg_request.json --output-dir "$env:USERPROFILE\Desktop"
```

Then copy `bloomberg_snapshot_latest.json` back to local `data/`.

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

## Current Data Coverage

The current request exports:

- Reference: price, market cap, forward P/E, EV/EBITDA, EV/Sales, P/B, volume, 30D average volume, free float, short-interest ratio, beta, 30D volatility, 1D/5D/1M/3M/6M/1Y price changes.
- Historical: one year of daily `PX_LAST` for all equities, indices, rates, FX and commodity proxies in the request.
- Macro/cross-asset proxies: `SPX Index`, `NDX Index`, `SOX Index`, `VIX Index`, `USGG10YR Index`, `USGG2YR Index`, `DXY Curncy`, `HG1 Comdty`, `NG1 Comdty`, `CL1 Comdty`.
