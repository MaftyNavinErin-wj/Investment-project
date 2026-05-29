# Investment Project

This workspace starts with an AI supply-chain tracking workflow.

Run the daily AI radar:

```powershell
.\run-ai-radar.ps1
```

Download official evidence first when doing deeper work:

```powershell
python .\scripts\fetch-evidence.py --months 12
```

This writes SEC filings and official investor-relations pages under `evidence/`, with manifests that the research workflow can cite or review manually.

The script writes dated reports under `reports/`:

- `ai-radar-YYYY-MM-DD.md`
- `ai-radar-YYYY-MM-DD.html`
- `ai-radar-YYYY-MM-DD.pdf`

Workflow notes and maintenance rules live in:

- [docs/AI_RADAR_WORKFLOW.md](docs/AI_RADAR_WORKFLOW.md)
- [docs/BLOOMBERG_WORKFLOW.md](docs/BLOOMBERG_WORKFLOW.md)
