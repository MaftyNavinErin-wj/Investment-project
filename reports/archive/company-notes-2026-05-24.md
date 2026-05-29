# Company Notes - AI Second-Order Verification - 2026-05-24

Purpose: turn the segment-level work into company-level verification tasks. Scope is local SEC/IR/transcript evidence plus the latest market snapshot in `data/segment_history.jsonl`.

## Portfolio Implication

- **结论变化 1: 铜/电力链继续上调优先级。** FCX 的 primary-source 证据最直接，ETN 的 data-center power 证据更接近设备订单；SCCO 做铜价 beta 对照。
- **结论变化 2: 水资源主题需要改名。** 不是买 generic water scarcity，而是找液冷、冷却液、冷板/CDU、chilled-water、数据中心热管理服务。ECL 优先级高于 XYL。
- **结论变化 3: APH 是连接器/高速线缆 proof source，不是 HTCC 结论。** 现阶段不能因为 APH 有 optical/high-speed cable，就直接推出 ceramic/HTCC 材料弹性。
- **结论变化 4: VRT 作为景气验证基准，不作为低拥挤增量首选。** 它证明热管理和 critical power 方向仍强，但估值/涨幅已经把容错率压低。

## Snapshot

| Ticker | Stance | Segment | Crowding | 3M | 1Y | Fwd PE | EV/EBITDA |
|---|---|---|---|---:|---:|---:|---:|
| ETN | 优先验证 | Critical Power / Copper / Electrical Infrastructure | 中高拥挤 | +4.3% | +23.3% | 27.8x | 27.3x |
| FCX | 优先验证 | Copper / Electrification Metals | 拥挤度尚可 | -0.7% | +60.7% | 20.8x | 9.8x |
| SCCO | 次优先验证 | Copper / Electrification Metals | 中高拥挤 | -6.0% | +106.7% | 27.2x | 17.2x |
| APH | 映射验证 | Connectors / High-speed Cable / Optical Interconnect | 拥挤度尚可 | -12.5% | +55.5% | 26.6x | 21.6x |
| ECL | 优先验证 | Liquid Cooling / Coolant / Water Treatment | 拥挤度尚可 | -15.6% | -2.0% | 29.4x | 19.8x |
| XYL | 观察验证 | Water Reuse / Treatment / Industrial Water | 拥挤度尚可 | -14.4% | -10.0% | 19.7x | 14.4x |
| VRT | 高拥挤基准 | Thermal Management / Critical Power | 高拥挤 | +34.8% | +214.8% | 48.1x | 53.1x |

## Company Notes

### ETN - Eaton

- **Action:** 优先验证
- **Thesis hook:** AI 数据中心从 GPU 约束继续外溢到供电、配电、模块化电力设施，ETN 是比纯液冷更低 beta 的电力链候选。
- **AI capex mapping:** 直接映射在数据中心电力系统、模块化 power enclosure、switchgear/UPS/配电；间接映射在电网扩容与电气化。
- **Not proven yet:** 还没有量化到 AI/data-center 订单占比、backlog 斜率、价格/毛利弹性；当前仍可能被市场当作 broad electrification 而非纯 AI capex 交易。
- **Market context:** crowding 中高拥挤; 3M +4.3%; 1Y +23.3%; forward PE 27.8x; EV/EBITDA 27.3x.
- **Next checks:** 下一步看 earnings transcript 是否披露 data-center backlog、large project conversion、capacity/lead time、Fibrebond 收购后的订单协同。
- **Local evidence:**
  - `data center` from `evidence/sec/ETN/2026-05-05-10-Q-etn-20260331.htm`: fire detection, intrinsically safe explosion-proof instrumentation, and structural support systems that are produced and sold globally. The principal markets for these segments are commercial & institutional, data centers and distributed IT, industrial, utilities, residential, and machinery OEMs. These products are used wherever there is a demand for electrical power in data centers, utilities, industrial and energy
  - `Fibrebond` from `evidence/sec/ETN/2026-05-05-10-Q-etn-20260331.htm`: Fibrebond) for $ 1.43 billion, net of cash acquired. Fibrebond is a U.S. based designer and builder of pre-integrated modular power enclosures for data center, industrial, utility and communications customers. Fibrebond is reported within the Electrical Americas business segment. The acquisition of Fibrebond has been accounted for using the acquisition method of accounting which requires the assets acquired and liabi
  - `backlog` from `evidence/sec/ETN/2026-05-05-10-Q-etn-20260331.htm`: ticipated synergies of acquiring Fibrebond. Goodwill recognized as a result of the acquisition is deductible for tax purposes. The estimated fair value of the customer relationships, technology, trademarks and backlog intangible assets of $ 410 million, $ 171 million, $ 74 million and $ 60 million, respectively were determined using either the relief-from-royalty model or the multi-period excess earnings model, which

### FCX - Freeport-McMoRan

- **Action:** 优先验证
- **Thesis hook:** 铜是 AI power-chain 最干净的上游瓶颈之一；FCX 的文件已经把 copper demand 与 data centers/AI growth 明确挂钩。
- **AI capex mapping:** 直接映射不是服务器，而是数据中心、电网、连接性、城市化共同推升的铜需求；适合作为 AI 电力扩张的 commodity beta。
- **Not proven yet:** 公司层面收益仍高度受铜价、矿山执行、成本与宏观需求影响；AI 只是需求因子之一，不是完整定价因子。
- **Market context:** crowding 拥挤度尚可; 3M -0.7%; 1Y +60.7%; forward PE 20.8x; EV/EBITDA 9.8x.
- **Next checks:** 下一步验证 management 对 AI/data-center 需求的量化口径、2026-2027 supply response、成本曲线和项目审批风险。
- **Local evidence:**
  - `artificial intelligence` from `evidence/sec/FCX/2026-05-08-10-Q-fcx-20260331.htm`: olders. We believe fundamentals for copper are favorable with growing demand supported by copper’s critical role in electrification initiatives, continued urbanization in developing countries, data centers and artificial intelligence (AI) growth and growing connectivity globally. We continue to progress organic copper growth projects in the U.S. and South America. Across our U.S. and South America operations, we are
  - `electrification` from `evidence/sec/FCX/2026-05-08-10-Q-fcx-20260331.htm`: our highly attractive portfolio of organic growth options to generate value for common stockholders. We believe fundamentals for copper are favorable with growing demand supported by copper’s critical role in electrification initiatives, continued urbanization in developing countries, data centers and artificial intelligence (AI) growth and growing connectivity globally. We continue to progress organic copper growth
  - `data centers` from `evidence/sec/FCX/2026-05-08-10-Q-fcx-20260331.htm`: for common stockholders. We believe fundamentals for copper are favorable with growing demand supported by copper’s critical role in electrification initiatives, continued urbanization in developing countries, data centers and artificial intelligence (AI) growth and growing connectivity globally. We continue to progress organic copper growth projects in the U.S. and South America. Across our U.S. and South America op

### SCCO - Southern Copper

- **Action:** 次优先验证
- **Thesis hook:** SCCO 给铜主题提供另一只高经营杠杆样本，但目前本地证据对 AI/data-center 的直接表述弱于 FCX。
- **AI capex mapping:** 主要是铜价和长期铜供需 beta，适合与 FCX 对照，判断市场买的是 AI power-chain 还是泛铜周期。
- **Not proven yet:** 1Y 涨幅已经很大，拥挤度中高；若没有更直接的 AI/data-center 需求证据，风险回报弱于 FCX。
- **Market context:** crowding 中高拥挤; 3M -6.0%; 1Y +106.7%; forward PE 27.2x; EV/EBITDA 17.2x.
- **Next checks:** 下一步找 recent transcript 中对 AI/data center、电网、electrification 的定量讨论，并核对 capex/production growth 节奏。
- **Local evidence:**
  - `capital` from `evidence/sec/SCCO/2026-04-30-10-Q-scco-20260331x10q.htm`: ​ 223.8 ​ Exploration ​ 10.8 ​ 11.7 ​ Total operating costs and expenses ​ 1,771.0 ​ 1,586.4 ​ ​ ​ ​ ​ ​ ​ ​ ​ Operating income ​ 2,480.4 ​ 1,535.5 ​ ​ ​ ​ ​ ​ ​ ​ ​ Interest expense ​ ( 104.5 ) ​ ( 102.3 ) ​ Capitalized interest ​ 14.7 ​ 10.4 ​ Interest income ​ 46.8 ​ 48.7 ​ Other income (expense) ​ 6.7 ​ ( 13.7 ) ​ Income before income taxes ​ 2,444.1 ​ 1,478.5 ​ Income taxes (including royalty taxes, see Note 4)
  - `demand` from `evidence/sec/SCCO/2026-04-30-10-Q-scco-20260331x10q.htm`: d commencement dates of mining or metal production operations, projected quantities of future metal production, anticipated production rates, operating efficiencies, costs and expenditures as well as projected demand or supply for the Company’s products. Actual results could differ materially depending upon factors including the risks and uncertainties relating to general U.S. and international economic and political
  - `copper` from `evidence/sec/SCCO/2026-04-29-8-K-scco-20260423x8k.htm`: xchange Act. ☐ ​ ​ ​ ​ ITEM 5.02 DEPARTURE OF DIRECTORS OR PRINCIPAL OFFICERS; ELECTION OF DIRECTORS; APPOINTMENT OF CERTAIN OFFICERS; COMPENSATORY ARRANGEMENTS OF CERTAIN OFFICERS. On April 13, 2026, Southern Copper Corporation (the “Company”) announced with deep regret the unexpected passing of Oscar Gonzalez Rocha, the Company’s President, Chief Executive Officer, and Board member. A titan of the mining industry,

### APH - Amphenol

- **Action:** 映射验证
- **Thesis hook:** APH 可作为高速互联、光纤、连接器的美股验证样本，但它不是纯 AI 标的，收入暴露需要拆解。
- **AI capex mapping:** 映射到 high-speed cable、fiber optic、power/interconnect products；可作为 A 股连接器/线缆映射的 proof source。
- **Not proven yet:** 文件支持 high-speed/fiber/interconnect，但没有直接证明 HTCC/ceramic packaging 或 CPO 材料收入弹性。
- **Market context:** crowding 拥挤度尚可; 3M -12.5%; 1Y +55.5%; forward PE 26.6x; EV/EBITDA 21.6x.
- **Next checks:** 下一步看 transcript 对 IT datacom、AI cluster、high-speed cable、margin mix 的拆分；HTCC 主题暂不升级为核心。
- **Local evidence:**
  - `fiber optic` from `evidence/sec/APH/2026-05-01-10-Q-aph-20260331x10q.htm`: he CommScope acquisition was funded through a combination of net proceeds from the Delayed Draw Term Loans, the November Senior Notes and cash on hand, as discussed in Note 4 herein. CommScope adds significant fiber optic interconnect capabilities for the IT datacom and communications networks markets, as well as a diverse range of industrial interconnect products for the building infrastructure connectivity market.
  - `high-speed cable` from `evidence/sec/APH/2026-05-01-10-Q-aph-20260331x10q.htm`: egment designs, manufactures and markets a broad range of connector and interconnect systems, including high speed, radio frequency, power, fiber optic and other interconnect products; coaxial, fiber optic and high-speed cable; antennas; and other products for use in the information technology and data communications, mobile devices, industrial, communications networks, automotive, commercial aerospace and defense en
  - `interconnect` from `evidence/sec/APH/2026-05-01-10-Q-aph-20260331x10q.htm`: acquisition was funded through a combination of net proceeds from the Delayed Draw Term Loans, the November Senior Notes and cash on hand, as discussed in Note 4 herein. CommScope adds significant fiber optic interconnect capabilities for the IT datacom and communications networks markets, as well as a diverse range of industrial interconnect products for the building infrastructure connectivity market. The accompany

### ECL - Ecolab

- **Action:** 优先验证
- **Thesis hook:** 水主题需要重新定义为液冷/冷却液/热管理基础设施；ECL 的 CoolIT 收购让这个映射从泛水处理变成更直接的数据中心冷却链。
- **AI capex mapping:** CoolIT 对应 CDUs、cold plates、data-center liquid cooling；ECL 原有水处理能力可补 coolant、water quality、运营服务。
- **Not proven yet:** 交易尚需看整合、收入贡献、利润率、客户重合度；不能简单把 ECL 当作传统 water utility。
- **Market context:** crowding 拥挤度尚可; 3M -15.6%; 1Y -2.0%; forward PE 29.4x; EV/EBITDA 19.8x.
- **Next checks:** 下一步跟踪收购完成时间、CoolIT 订单规模、AI 数据中心客户、冷却液/水处理交叉销售。
- **Local evidence:**
  - `CoolIT` from `evidence/sec/ECL/2026-05-07-10-Q-ecl-20260331x10q.htm`: ny entered into a term credit agreement providing for a $ 4.75 billion unsecured committed delayed draw term loan credit facility, the proceeds from which may only be used to finance the pending acquisition of CoolIT Systems and to pay fees, costs and expenses related to the acquisition and the credit facility. No amounts had been drawn under the facility as of the date of this filing. ​ ​ ​ ​ 6. GOODWILL AND OTHER I
  - `coolant` from `evidence/sec/ECL/2026-05-07-10-Q-ecl-20260331x10q.htm`: lIT Systems for $ 4.75 billion, subject to certain adjustments. CoolIT Systems is a pure-play data center liquid cooling company that designs and manufactures high-performance liquid cooling systems, including coolant distribution units (CDUs), cold plates and direct-to-chip cooling technologies. The acquisition is expected to close in the third quarter of 2026, subject to regulatory approvals and other customary clo
  - `cold plates` from `evidence/sec/ECL/2026-05-07-10-Q-ecl-20260331x10q.htm`: ject to certain adjustments. CoolIT Systems is a pure-play data center liquid cooling company that designs and manufactures high-performance liquid cooling systems, including coolant distribution units (CDUs), cold plates and direct-to-chip cooling technologies. The acquisition is expected to close in the third quarter of 2026, subject to regulatory approvals and other customary closing conditions. ​ Ovivo Electronic

### XYL - Xylem

- **Action:** 观察验证
- **Thesis hook:** XYL 有水处理、reuse、outsourced water 等能力，但目前本地文件中直接 AI/data-center 证据弱；更适合作为对照样本。
- **AI capex mapping:** 可能映射到数据中心用水、循环水、工业水处理和运营服务，但需要客户/项目级证据。
- **Not proven yet:** 过去 1 年股价表现弱，主题映射也弱；没有直接 data-center water 订单之前，不应把它放进第一优先级。
- **Market context:** crowding 拥挤度尚可; 3M -14.4%; 1Y -10.0%; forward PE 19.7x; EV/EBITDA 14.4x.
- **Next checks:** 下一步只验证 data-center water reuse/treatment 项目、hyperscaler 客户、服务收入增长，不要被泛水资源叙事带偏。
- **Local evidence:**
  - `outsourced water` from `evidence/sec/XYL/2026-04-28-10-Q-xyl-20260331.htm`: cloud-based analytics, and remote monitoring and data management. The Water Solutions and Services segment provides tailored services and solutions, in collaboration with customers, including on‑demand water, outsourced water, recycle / reuse, pipeline services, specialty dewatering and emergency response service alternatives to improve operational reliability, performance and environmental compliance. Key offerings
  - `reuse` from `evidence/sec/XYL/2026-04-28-10-Q-xyl-20260331.htm`: remote monitoring and data management. The Water Solutions and Services segment provides tailored services and solutions, in collaboration with customers, including on‑demand water, outsourced water, recycle / reuse, pipeline services, specialty dewatering and emergency response service alternatives to improve operational reliability, performance and environmental compliance. Key offerings within this segment also in
  - `treatment` from `evidence/sec/XYL/2026-04-28-10-Q-xyl-20260331.htm`: ry ("EnviroMix"). EnviroMix is headquartered in South Carolina, U.S., and provides mixing and process control products and services to municipal and industrial customers. This acquisition expands the Company's treatment offerings and provides synergy opportunities. The operating results of EnviroMix have been included in the Company's results of operations since the acquisition date within the Water Infrastructure se

### VRT - Vertiv

- **Action:** 高拥挤基准
- **Thesis hook:** VRT 是 AI 电力/热管理链的高纯度基准，但 1Y 涨幅和估值拥挤已经很高，更适合作为验证行业景气的 benchmark。
- **AI capex mapping:** 直接映射 AI-ready data centers、liquid cooling、thermal management、critical power。
- **Not proven yet:** 基本面方向强，但投资结论受估值和拥挤度约束；除非上修继续超预期，否则不应替代更早期的 second-order 机会。
- **Market context:** crowding 高拥挤; 3M +34.8%; 1Y +214.8%; forward PE 48.1x; EV/EBITDA 53.1x.
- **Next checks:** 下一步用 VRT 的订单、backlog、thermal/liquid cooling 评论验证 ECL/ETN/XYL 的上游扩散逻辑。
- **Local evidence:**
  - `thermal management` from `evidence/sec/VRT/2026-04-22-10-Q-vrt-20260331.htm`: igital infrastructure technologies and life cycle services primarily for data centers, communication networks, and commercial and industrial environments. Vertiv’s offerings include AC and DC power management, thermal management, low/medium voltage switchgear, busbar, air cooled and liquid cooled thermal management products, integrated modular solutions, racks, single phase UPS, rack power distribution, rack thermal
  - `AI-ready Data Centers` from `evidence/ir/VRT/Vertiv-Investor-Relations.html`: ducts Download the Vertiv™ XR App Download the Vertiv™ Virtual Showroom App How to Buy Product Registration Virtually Test Cooling Systems in our Labs’ Digital Twins Solutions AI and High Performance Computing AI-ready Data Centers High Density Cooling Vertiv™ 360AI Applications Small/Medium Business Enterprise Education Federal Healthcare Manufacturing Retail Offerings Chilled Water Solutions Dynamic Power Vertiv In
  - `liquid cooling` from `evidence/ir/VRT/Vertiv-Investor-Relations.html`: cal Power Uninterruptible Power Supplies (UPS) DC Power Systems Power Distribution Static Transfer Switches Switchgear and Switchboard Busway and Busduct Battery Energy Storage System (BESS) Thermal Management Liquid Cooling Solutions Heat Rejection Outdoor Packaged Systems Room Cooling In-Row Cooling Rack Cooling Free Cooling Chillers Evaporative Free Cooling Thermal Control and Monitoring Racks & Enclosures Integra
