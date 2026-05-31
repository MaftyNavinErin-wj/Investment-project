# Daily AI Radar Update Workflow

This is the repeatable workflow for updating the AI Capex Radar with fresh Bloomberg data, public news/RSS, and optional KOL cross-checks.

## Scope

The daily workflow answers one question:

> What has actually changed in the current update window, and does it change the AI capex framework, segment temperature, crowding, or holdings read-through?

Do not treat KOLs, YouTube clips, social media, or recap articles as conviction sources. They are idea feeds and crowding/narrative checks. Framework changes should come from company evidence, market data, Bloomberg snapshots, and repeatable segment logic.

## 1. Start Clean

From the project root:

```powershell
git pull
git status --short
```

If the worktree is dirty, do not revert unrelated changes. Note the dirty files and continue only with the files needed for the update.

## 2. Bloomberg Data Refresh

Bloomberg Desktop API runs inside VDI, so local Codex should not try to control the VDI GUI. Use the shared-drive workflow.

### Local: push request/exporter to shared drive

```powershell
.\scripts\sync-bloomberg-shared.ps1 -Mode Push
```

Optional status check:

```powershell
.\scripts\sync-bloomberg-shared.ps1 -Mode Status |
  Select-Object FullName,@{Name='LastWriteTimeLocal';Expression={ if ($_.LastWriteTime) { $_.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss') } else { $null } }},Length
```

### VDI: user runs Bloomberg export

Inside Bloomberg VDI, while Bloomberg Terminal is logged in, run:

```powershell
powershell -ExecutionPolicy Bypass -File "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie\run_bloomberg_full.ps1"
```

If script execution is still blocked, bypass the runner and call Python directly:

```powershell
$share = "\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie"
python (Join-Path $share "bloomberg_export.py") --request (Join-Path $share "bloomberg_request.json")
```

Expected outputs on the shared drive:

- `bloomberg_snapshot_latest.json`
- `bloomberg_history_latest.json`
- dated archive copies for both files

Bloomberg News is best-effort and may remain stale because the current VDI API session has not reliably exposed Bloomberg News search.

### Local: pull data back

After the user says the VDI export has finished:

```powershell
.\scripts\sync-bloomberg-shared.ps1 -Mode Pull
```

Verify `created_at`, row count, and size:

```powershell
@'
import json
from pathlib import Path
for name in ["bloomberg_snapshot_latest.json", "bloomberg_history_latest.json", "bloomberg_news_latest.json"]:
    p = Path("data") / name
    if not p.exists():
        print(f"{name}: missing")
        continue
    data = json.loads(p.read_text(encoding="utf-8"))
    print(f"{name}: created_at={data.get('created_at')} rows={len(data.get('rows', []))} size={p.stat().st_size}")
'@ | python -
```

## 3. Optional KOL / YouTube Cross-Check

Use this only when KOL narrative helps interpret the update window or crowding. Do not use the user's GUI or VDI. Background metadata/transcript access is preferred.

### Search rules

Use targeted searches, for example:

```powershell
$env:PYTHONIOENCODING='utf-8'
@'
import json, subprocess, sys
queries = [
  "ytsearch20:Jim Cramer CNBC AI May 2026",
  "ytsearch20:Jim Cramer CNBC Dell Nvidia data center May 2026",
  "ytsearch20:Jim Cramer CNBC Applied Materials Databricks Amazon May 2026",
  "ytsearch20:Jim Cramer CNBC hardware software rotation May 2026",
]
seen = {}
for q in queries:
    cmd = [sys.executable, "-m", "yt_dlp", "--dump-json", "--skip-download", "--no-warnings", q]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    for line in p.stdout.splitlines():
        try:
            item = json.loads(line)
        except Exception:
            continue
        title = item.get("title") or ""
        channel = item.get("channel") or ""
        upload = item.get("upload_date") or ""
        desc = item.get("description") or ""
        hay = f"{title} {channel} {desc}".lower()
        if upload >= "20260501" and ("cramer" in hay or "mad money" in hay) and any(
            k in hay for k in ["ai", "data center", "dell", "nvidia", "applied materials", "amazon", "databricks", "software", "hardware", "corning"]
        ):
            seen[item.get("id")] = {
                "id": item.get("id"),
                "title": title,
                "channel": channel,
                "upload_date": upload,
                "duration": item.get("duration"),
                "url": item.get("webpage_url"),
            }
print(json.dumps(sorted(seen.values(), key=lambda x: x["upload_date"], reverse=True), ensure_ascii=False, indent=2))
'@ | python -
```

If needed, fetch available transcripts with `youtube-transcript-api`. Do not store long transcript dumps in the repo. Store only short, compliant summaries and framework mapping.

### Coverage standard

Be precise in language:

- OK: "covered the core recent CNBC/Cramer clips directly relevant to AI capex."
- Not OK: "guaranteed full YouTube coverage."

Prefer official CNBC Television / Mad Money clips. Treat FinVid and other compilations as discovery only unless they point to a primary clip.

### Output file

Create or update:

```text
data/kol_watch_YYYY-MM-DD.json
```

Keep video titles unchanged. Write the interpretation fields in Chinese:

- `view`
- `cross_check`
- `a_share_readthrough`
- `framework_takeaway.stance`
- `framework_takeaway.report_use`

The report generator automatically reads the latest `data/kol_watch_*.json` and renders the `外部 KOL 交叉验证` section.

## 4. Regenerate Reports

Run:

```powershell
.\run-ai-radar.ps1
```

Expected outputs:

- `reports/ai-radar-YYYY-MM-DD.md`
- `reports/ai-radar-YYYY-MM-DD.html`
- `reports/ai-radar-YYYY-MM-DD.pdf`
- `reports/ai-radar-YYYY-MM-DD-readthrough.md`
- `reports/ai-radar-YYYY-MM-DD-readthrough.html`
- `reports/ai-radar-YYYY-MM-DD-readthrough.pdf`

## 5. Verify

Check report files:

```powershell
Get-Item reports\ai-radar-YYYY-MM-DD.* , reports\ai-radar-YYYY-MM-DD-readthrough.* |
  Select-Object FullName,@{Name='LastWriteTimeLocal';Expression={$_.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')}},Length
```

Check KOL section when applicable:

```powershell
Select-String -Path reports\ai-radar-YYYY-MM-DD.md -Pattern "外部 KOL 交叉验证|KOL 解读|映射：" -Context 0,2
```

Check git status:

```powershell
git status --short
```

Expected changed/generated files for a full update may include:

- `data/bloomberg_snapshot_latest.json`
- `data/bloomberg_history_latest.json`
- `data/discovery_history.jsonl`
- `data/kol_watch_YYYY-MM-DD.json` when KOL work was done
- `reports/ai-radar-YYYY-MM-DD.*`
- `reports/ai-radar-YYYY-MM-DD-readthrough.*`

## 6. Interpretation Rules

When summarizing "what changed today":

- Use the report's `Delta window`, not just the calendar date.
- Separate demand evidence from macro/financing pressure.
- Separate "theme confirmed" from "stock is attractive."
- Treat KOL agreement as narrative/crowding confirmation.
- Do not turn a hot-consensus segment into an emergent opportunity.
- For A-share mapping, require company-level order, revenue, margin, or customer evidence before upgrading conviction.

## 7. Current 2026-05-31 Pattern

The 2026-05-31 update is the template example:

- Bloomberg snapshot/history refreshed via VDI shared-drive workflow.
- Dell became the key incremental AI server evidence.
- Macro/financing pressure remained an offset through higher US rates.
- Cramer/CNBC clips confirmed the physical AI infrastructure narrative, but also confirmed crowding.
- Report conclusion stayed selective: validate EPS/order revisions, do not chase the full hardware chain blindly.
