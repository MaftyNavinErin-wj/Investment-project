# Position Memory

This file records the user's entry thesis and monitoring rules. Every portfolio review must start from this thesis, then compare fresh events against it. Do not infer a new thesis from generic AI news or recent price action.

## Portfolio Review Rule

For every holding, analyze in this order:

1. Entry thesis: what the position was originally bought to express.
2. Latest 1-day window: new events, price action, and market signals from the most recent trading day.
3. Since-last-update window: only information after the prior report delta window; old events and second-hand recaps are background, not new delta.
4. Thesis status: strengthened, unchanged, weakened, or violated.
5. Position implication: add, hold, trim, reduce to watch, or exit; include the trigger that would change the view.
6. Portfolio role: growth beta, event-driven option, dividend/defensive hedge, quality compounder, liquidity ballast, or risk offset.

## Current Holdings And Original Logic

### Ningde Times / CATL (300750.SZ)

- Role: quality China manufacturing leader, storage/power infrastructure exposure, and partial AI data-center power/storage second-order beneficiary.
- Entry thesis: storage, power infrastructure, and China manufacturing leader re-rating. AI data-center electricity and storage demand are a bonus, not the sole thesis.
- Key positive checks: global share, unit economics per Wh, storage margin, overseas growth, data-center/storage linkage, balance-sheet discipline.
- Negative trigger: single-Wh profit, global share, or storage margin deteriorates repeatedly.
- Review discipline: do not treat it as a pure AI capex beta stock. Compare its risk/reward against crowded AI hardware names.

### Zhongji Innolight (300308.SZ)

- Role: high-beta AI optical module core holding.
- Entry thesis: AI cluster bandwidth upgrades drive 800G/1.6T optical module demand.
- Key variables: North America capex, network architecture, customer orders, gross margin, supply tightness, 800G/1.6T price and mix.
- Negative trigger: 800G/1.6T demand, pricing, or key customer orders are disproven.
- Review discipline: judge risk on current market value, not original cost or realized profit cushion.

### WUS Printed Circuit / Hudian (002463.SZ)

- Role: AI server / switch / accelerator PCB exposure.
- Entry thesis: AI servers, GPU/ASIC boards, and high-speed switches drive high-layer and high-frequency PCB demand.
- Key variables: AI server/ASIC/GPU orders, product mix, gross margin, capacity utilization, high-end PCB competitive supply.
- Negative trigger: AI server PCB orders, pricing, or utilization clearly weakens.

### Montage Technology (688008.SS)

- Role: memory-interface architecture upgrade exposure.
- Entry thesis: DDR5 server penetration, RCD/MRCD/MDB, PCIe Retimer, and CXL upgrades drive memory-interface chip demand.
- Key variables: new-product revenue mix, gross margin, server memory cycle, CXL/retimer adoption, customer certification.
- Negative trigger: DDR5/RCD/MRCD/Retimer/CXL revenue or margin logic is disproven.
- Review discipline: do not add simply because the account P/L is small or negative; judge against stock-level run-up and valuation.

### Tencent (0700.HK)

- Role: China internet quality platform and AI ROI/application monetization exposure.
- Entry thesis: games, ads, cloud, and AI application commercialization support valuation repair.
- Key variables: game/ad growth, buybacks, margin, cloud AI monetization, capex discipline, ROI proof.
- Negative trigger: game/ad growth stalls, or AI investment hurts margin without commercialization.

### Midea Group H (0300.HK / Bloomberg: 300 HK Equity)

- Role: dividend, cash-flow, and portfolio risk-hedge holding.
- Entry thesis: defensive cash-flow/dividend base. It is not an AI stock by default.
- Key variables: recurring profit, free cash flow, dividend policy, overseas demand, margins, FX/export resilience.
- Negative trigger: recurring profit, cash flow, overseas business, or margin deteriorates repeatedly.
- Review discipline: do not mechanically map Midea to AI power/cooling. Only upgrade AI linkage if there is explicit data-center thermal management, building-energy, industrial technology, or order evidence.

### Kuaishou-W (1024.HK)

- Role: event-driven AI video / Kling option.
- Entry thesis: Kling and AI video commercialization option; the position depends on financing/valuation, revenue validation, and inference-cost control.
- Key variables: Kling financing/spin-off progress, valuation, strategic investors, ARR/revenue, paid adoption, inference cost, competition from Sora/Runway/Doubao-style products.
- Negative trigger: Kling spin-off/financing fails, IPO is delayed for fundamental reasons, revenue misses, ARR slows, or inference costs make commercialization unattractive.
- Review discipline: generic AI app news is not enough. Kuaishou must be reviewed through Kling event progress and monetization evidence.

## Standing Process Requirement

Every holding review must be thorough and position-specific. Avoid generic labels such as "AI application side" or "AI capex beneficiary" unless they match the recorded thesis. If new user comments refine the thesis, update this file and `ai-radar/config.json` in the same turn.
