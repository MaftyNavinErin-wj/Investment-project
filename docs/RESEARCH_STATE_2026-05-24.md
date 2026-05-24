# AI Capex Research State - 2026-05-24

## Current Primary Output

The main audience-facing report is:

- `reports/ai-radar-2026-05-24.md`
- `reports/ai-radar-2026-05-24.html`
- `reports/ai-radar-2026-05-24-kol.pdf`

Note: `reports/ai-radar-2026-05-24.pdf` was locked by an external process during export, so newer PDFs use suffixed filenames. The latest PDF is `ai-radar-2026-05-24-kol.pdf`.

## Scope Boundary

The report is based on public materials that have been collected and checked locally:

- SEC filings
- Company IR / press release pages
- Selected earnings / transcript / webcast / presentation pages where available
- News / RSS momentum checks
- Market price and valuation snapshots

It is not a complete archive of every public disclosure by every company. NVIDIA is treated as the chain-master company, so the latest NVIDIA 10-Q, 8-K, and official quarterly results receive higher weight in the framework.

## Evidence Store

Local evidence is stored under:

- `evidence/sec/`
- `evidence/ir/`
- `evidence/transcripts/`
- `evidence/index.json`

Current evidence index:

- 112 SEC filings
- 28 companies
- 10 IR pages
- 43 earnings / results / webcast / presentation links across 10 companies

The evidence store is for verification and follow-up research. It should not be copied verbatim into the main report.

## Main Report Structure

The main report should preserve this order:

1. AI capex macro and headline capex evidence
2. Reading guide and coverage boundary
3. NVIDIA chain-master disclosure findings
4. Full segment map
5. Segment interpretation without repeating the full map
6. Representative company verification order
7. KOL / external idea-feed cross-check
8. Search heat / early signal notes
9. Low-crowding watch basket
10. Holdings mapping
11. Stock crowding table
12. Evidence appendix

The earlier `Theme Temperature` section was removed because it repeated the segment map. Its useful content was consolidated into `赛道解读`.

## Current Investment Conclusions

- AI capex macro remains positive: hyperscaler and NVIDIA disclosures still support an expanding AI infrastructure cycle.
- NVIDIA is the chain-master signal. Its disclosure strengthens networking, NVLink, InfiniBand, Spectrum-X Ethernet, silicon photonics, advanced optics, and system-level power / cooling logic.
- Core hardware remains highly crowded. Optical modules, memory, CPO / silicon photonics, PCB, power and liquid cooling mostly require earnings revision proof rather than narrative proof.
- Copper / electrical infrastructure moved up in priority. FCX explicitly links copper demand to data centers and AI growth; ETN adds direct data-center modular power exposure through Fibrebond.
- Water should be reframed as liquid cooling / coolant / CDU / cold plate / chilled-water / thermal infrastructure. ECL is higher priority than XYL because of CoolIT.
- HTCC / ceramic packaging is not upgraded. APH helps validate high-speed cable / fiber optic / interconnect, but it does not prove HTCC revenue elasticity.
- Natural gas midstream remains second-proof. It needs firm transport, pipeline lateral, compression, or project-level evidence tied to data-center power demand.
- AI applications / agents remain second-proof. The next validation points are paid adoption, ARPU, retention, inference workload, and margin.
- China / export controls remain a risk. NVIDIA's latest outlook does not assume China Data Center compute revenue.

## Supporting Reports

These are useful research artifacts but are not the main audience-facing report:

- `reports/company-notes-2026-05-24.md`
- `reports/company-notes-2026-05-24.pdf`
- `reports/segment-evidence-deep-dive-2026-05-24.md`
- `reports/segment-evidence-deep-dive-2026-05-24.pdf`
- `reports/nvda-disclosure-findings-2026-05-24.txt`

Use these for follow-up verification, not as the primary client-facing narrative.

## Scripts Added

- `scripts/fetch-evidence.py`: download SEC filings and official IR / transcript-like materials.
- `scripts/build-evidence-index.py`: summarize local evidence inventory.
- `scripts/analyze-segment-evidence.py`: produce segment-level evidence review.
- `scripts/build-company-notes.py`: generate company-level verification notes.
- `scripts/refine-main-report.py`: apply current main-report structure and NVIDIA chain-master additions.
- `scripts/evidence_sources.json`: current tracked universe for official evidence collection.

## Known Issues

- The original `ai-radar-2026-05-24.pdf` file was locked during export. The latest PDF is `ai-radar-2026-05-24-nvda.pdf`.
- Some PowerShell commands display UTF-8 Chinese text as mojibake. Use `rg` or open files in a UTF-8-aware editor to verify content.
- The evidence puller downloads what is available from configured sources; transcript coverage is partial and depends on company IR site structure.

## Next Work

- Integrate the refined report structure directly into `ai-radar/daily_radar.py`, so the report generator produces the cleaner structure automatically.
- Replace the locked main PDF once it is no longer open.
- Add a small evidence coverage table by company and source type, without expanding raw snippets in the main report.
- For NVIDIA-driven updates, add a recurring chain-master review section rather than treating it as a one-off insertion.
- For KOL-driven updates, maintain `data/kol_watch_*.json` and map each external view to the segment framework before changing conclusions.
