# AI Radar Workflow

## 目标

这个 workflow 的目标不是每天堆新闻，而是回答一个投资问题：

> AI capex 产业链里，哪些 segment 的共识正在变化，哪些仍然有清晰映射但拥挤度尚可，哪些只是已经很热的主线复核？

每天报告要服务三件事：

1. 追踪大共识变化：AI capex 是否继续强、是否见顶、是否从训练转向推理、是否从硬件转向 ROI。
2. 追踪小 segment 变化：缺货、涨价、订单、产能、交付周期、客户验证、产品代际切换。
3. 映射到股票：先判断 segment，再判断代表票，最后判断是否值得进入持仓研究池。

## 一键运行

```powershell
.\run-ai-radar.ps1
```

输出位置：

- `reports/ai-radar-YYYY-MM-DD.md`
- `reports/ai-radar-YYYY-MM-DD.html`
- `reports/ai-radar-YYYY-MM-DD.pdf`

日常阅读优先看 PDF 或 HTML。Markdown 只是源文件，不作为主要阅读形态。

## 核心框架

### A/B/C 三层

| 层级 | 含义 | 投资含义 |
|---|---|---|
| A 层 | 已知核心瓶颈 | 逻辑最硬，但市场通常已经定价；赚的是业绩兑现和继续超预期的钱。 |
| B 层 | 瓶颈迁移 | 从已知瓶颈向相邻环节扩散，最适合寻找非共识到共识的机会。 |
| C 层 | 架构重塑 | 更远期、更难验证，但一旦方向成立，可能改变价值分配。 |

例子：

- A 层：GPU/HBM/CoWoS/AI server/800G-1.6T 光模块。
- B 层：CPO、硅光、PCB、高速连接器、电力、燃机、天然气中游、光纤预制棒、HTCC、水资源。
- C 层：EDA/IP/SerDes/CXL/测试良率/AI 应用 ROI/治理安全/端侧 AI。

### Segment 优先，不先看股票

报告必须先列完整 segment，再找股票。顺序是：

1. Segment 的位置：离 AI capex 近还是远。
2. Segment 的逻辑强度：需求链条是否清楚。
3. Segment 的映射强度：能否明确映射到上市公司收入和利润。
4. Segment 的拥挤度：代表票近期涨幅和估值是否已经很高。
5. Segment 的最新 delta：今天相比昨天，市场认知发生了什么变化。
6. 股票筛选：只在值得研究的 segment 里找代表票和弹性票。

## 报告结构

每日报告应固定为以下结构。

### 1. AI Capex Macro

这是报告最前面的总开关。先判断美国 AI capex 的总水位，再看细分环节。

必须覆盖四个问题：

- Hyperscaler capex 是否继续上修：Microsoft、Alphabet、Meta、Amazon、Oracle 等。
- ROI 是否开始被市场质疑：AI 云收入、广告/搜索/软件变现、推理需求、企业付费。
- 资金成本是否构成压力：美国长端利率、进一步加息风险、数据中心融资成本、project finance 利差。
- 资源约束是否加剧：电力、燃机、并网、土地、水、冷却、组件价格。

判断方式：

| 情况 | 含义 | 动作 |
|---|---|---|
| Capex 继续上修，ROI 没恶化 | 总水位支持硬件链 | 继续找订单和盈利预测上修环节。 |
| Capex 继续上修，但 ROI/利率/资源约束风险升温 | 主线还能涨，但估值容错下降 | 高拥挤票只看业绩继续上修，不买纯估值扩张。 |
| Capex 停止上修或下修 | AI 硬件链进入风险复盘 | 先降杠杆/降预期，再重新看估值。 |

这部分要明确传导到 A 股：

- 中际旭创：最直接看网络瓶颈、800G/1.6T、硅光/NPO/OCS、毛利率。
- 沪电股份：看 AI server / GPU / ASIC / 1.6T switch 对高端 PCB 的结构升级。
- 澜起科技：看 MRDIMM、MRCD/MDB、PCIe Retimer、CXL 的架构升级，而不是单纯 capex 总额。

### 2. Segment 全景

这是最重要的表。必须按产业链远近和逻辑顺序排列，不要把不相干环节混在一起。

建议顺序：

1. AI Server / GPU Infrastructure
2. HBM
3. DRAM / NAND / Enterprise SSD
4. Memory Interface / Retimer / CXL
5. Optical Modules 800G/1.6T
6. CPO / Silicon Photonics / OCS
7. High-speed PCB
8. Connectors / SerDes / High-speed Interconnect
9. Critical Power: UPS / Switchgear / Power Distribution
10. Liquid Cooling / Thermal Management
11. Power Generation / Gas Turbines
12. Natural Gas Midstream / Pipeline / Compression
13. Grid EPC / Transmission / Substation
14. Copper / Cables / Electrification Metals
15. Fiber / Preform / Optical Cable
16. HTCC / Ceramic Packaging Materials
17. Water / Zero-water Cooling / Treatment
18. Testing / Burn-in / Yield
19. AI Applications / Agents / ROI
20. AI Governance / Security / Observability
21. Edge / On-device AI

每一行至少包括：

- 层级：A/B/C
- 温度：Hot Consensus / Hot-Warming / Early Signal
- 逻辑强度：high / medium / low
- 映射强度：high / medium / low
- 拥挤度：高拥挤 / 中高拥挤 / 拥挤度尚可
- 最新 delta
- 代表票

### 3. 赛道解读

这部分不是为了重复 `Segment 全景`，而是为了把全景表翻译成读者可执行的决策层。报告里应保留完整 segment 地图，但解读部分只回答“现在怎么处理”，不要逐条复述每个 segment。

建议分成三类：

- Hot Consensus：已经很热，只做趋势和超预期复核，不能叫 emergent。
- Hot-Warming：有继续研究价值，重点找还没充分定价的细分环节和标的。
- Early Signal：只是线索，不能直接下交易结论。

这部分必须讲清楚：

- 哪些核心主线继续成立，但已经拥挤，只能做订单、价格、份额、盈利预测上修复核。
- 哪些二阶方向正在 warming，需要继续找公司级证据。
- 哪些 early signal 需要重新定义，避免主题太宽，例如把“水资源”收窄成液冷、冷却液、CDU/cold plate、chilled-water 和 thermal infrastructure。

### 4. 结论 / 本轮重点变化

结论必须直接回答：

1. 哪些 segment 逻辑强、映射强、拥挤度尚可。
2. 哪些 segment 逻辑强但已经太拥挤，只能等超预期或回调。
3. 哪些 segment 只是远端线索，不能现在强行交易。
4. 哪些方向相对上一版有边际变化：上调、下调、重新定义、仍需第二证明。

如果没有完美交集，要明确说没有，不要硬凑。

### 5. 代表票候选

只从值得研究的 segment 里找票。高拥挤主线可以保留在观察表，但不要伪装成新机会。

每个标的至少要看：

- 1M / 3M / 1Y 涨幅
- 当年、明年、后年 P/E
- EV/EBITDA
- 收入和利润与该 segment 的映射强度
- 关键催化剂
- 关键证伪点

### 6. 搜索热度线索

这部分只显示关键词热度和新闻线索，不自动等于投资机会。

原则：

- 如果对应 segment 已经 Hot Consensus，就只能作为“热度验证”，不能标成 emergent。
- 如果搜索热度起来但股价没怎么动，可以进入人工复核。
- 如果搜索热度和股价都已经起来，优先判断是否拥挤。

### 7. Emergent Segment Discovery / 新瓶颈发现待办

这是 workflow 的核心研究动作之一。KOL、社媒、研报标题、产业访谈只是 idea feed；真正的判断来自我们的 AI capex 框架。

流程固定为：

1. 从 AI factory 架构变化出发：GPU/ASIC、networking、memory wall、power、cooling、physical infrastructure、ROI。
2. 推导未来 6-18 个月可能变成新约束的瓶颈：例如电力保护、低压配电、服务器电源磁性器件、热管理耗材、DDR5 配套。
3. 删除已经被市场充分命名的方向：光模块/CPO 主链、AI PCB/CCL/电子布显性票、存储模组热股、铜连接显性票、液冷整机、AI 电源显性票、已起飞的测试设备票。
4. 对剩余候选做三重验证：公司级收入/订单证据、股价和估值拥挤度、未来催化剂和证伪点。
5. 只有通过验证的候选，才能进入低拥挤观察篮；否则只能留在待办或灰名单。

输出格式：

- `data/emergent_segment_watch_YYYY-MM-DD.json`：保存剔除规则、候选池、灰名单和下一步验证。
- 主报告只放读者友好的摘要，不展开成过长 deep dive。
- 不把候选写成推荐买入，措辞必须是“待办 / 观察 / 需要验证”。

当前示例候选类型：

| 类型 | 逻辑 | 需要验证 |
|---|---|---|
| 数据中心电力保护 / 低压配电 | AI 数据中心从买服务器走向重构电力链，保护器件和配电可能成为隐性消耗环节。 | data-center/HVDC 订单、客户、收入占比、股价拥挤度。 |
| 服务器电源上游 / 磁性器件 | rack-scale power、800V HVDC、48V 架构升级可能提高变压器、电感、磁性元件价值量。 | 服务器电源产品、客户验证、毛利变化、是否已经过热。 |
| 热管理材料 / 密封 / 导热 | 液冷整机已热，但 TIM、导热垫、密封胶、EMI、冷板材料等耗材可能更早期。 | AI 服务器收入证据、客户、收入拆分、毛利率。 |
| DDR5 配套 / SPD / EEPROM | memory wall 和服务器 DDR5 渗透会带来模组配套需求。 | DDR5 SPD 收入、服务器模组客户、估值和涨幅。 |

### 8. 低拥挤观察篮

这里只放“涨幅/估值没有明显爆掉”的复核对象，不等于推荐买入。

### 9. 持仓映射

持仓映射要用大白话，不要只输出机器标签。

每个持仓建议固定写：

- 公司自身逻辑
- 和 AI 产业链的映射强弱
- 当前拥挤度
- 最新需要跟踪的 delta
- 对持仓动作的含义：继续拿、等待验证、降低预期、只看催化剂等

避免类似这种表达：

```text
美的集团：Power / Cooling=A层/上修/变紧/代表票高拥挤
```

应该写成：

```text
美的集团不是 AI 电力/液冷的直接映射票。它更像是白电和工业资产的稳健持仓，不能因为数据中心电力热度高就强行挂到 Power/Cooling 主线。
```

## 信息源原则

报告需要持续扩展信息源，目标是尽量接近 market consensus，而不是只看几条新闻。

优先信息源：

- 上游公司财报、业绩会 transcript、投资者日。
- 云厂商 capex 指引：Microsoft、Google、Meta、Amazon、Oracle、CoreWeave 等。
- 半导体和硬件链：NVIDIA、AMD、Broadcom、TSMC、ASML、Micron、SK Hynix、Samsung。
- 光通信链：中际旭创、新易盛、天孚通信、Coherent、Lumentum、Corning 等。
- 电力和基础设施：GE Vernova、Siemens Energy、Vertiv、Eaton、Quanta Services、EMCOR、燃气中游公司。
- 行业数据：TrendForce、Omdia、Dell'Oro、SemiAnalysis、LightCounting、各券商产业链跟踪。
- 市场侧：涨幅、估值、成交热度、融资余额、研报标题、社媒/KOL 讨论。

## 判断规则

### 不把热门主题误判成 emergent

如果一个 segment 已经满足任一条件，就不能叫 emergent：

- 代表票 3M 涨幅很高。
- 代表票 1Y 涨幅很高。
- 估值已经明显透支。
- 大量研报和社媒都在讨论。
- 主流投资人已经把它当作 AI 主线。

这种情况下只能问：

- 是否还有业绩上修？
- 是否还有订单/价格/供给超预期？
- 是否出现回调后的赔率？

### 先看拥挤度，再谈机会

一个好 segment 不等于好买点。

交易上更关心四象限：

| 逻辑/映射 | 拥挤度 | 处理 |
|---|---|---|
| 强 | 低/中 | 优先研究 |
| 强 | 高 | 等超预期或回调 |
| 弱 | 低 | 只做线索 |
| 弱 | 高 | 回避 |

### A 股投机要单独看

A 股中短期可以交易“可讲的映射”，但要分清：

- 硬逻辑：已经进入供应链，收入利润可验证。
- 软映射：材料/设备/封装属性可以讲，但客户和收入未实锤。
- 纯蹭：只有概念，没有可验证收入。

例如 HTCC/CPO 映射：

- 可讲：高可靠陶瓷封装可能用于光通信/硅光/CPO 上游。
- 未实锤：如果公司没有明确客户、收入拆分和毛利验证，就不能当核心供应链。
- 交易含义：可以放入 A 股题材观察，但需要严格盯公告、互动易、半年报拆分、毛利率。

## 每日人工阅读方式

每天生成报告后，按这个顺序看：

1. 先看 Segment 全景，确认主线和二阶方向有没有边际变化。
2. 再看赛道解读和结论，确认有没有“逻辑强 + 映射强 + 拥挤度尚可”的交集。
3. 看高拥挤主线有没有继续超预期，尤其是已有持仓相关方向。
4. 看 Emergent Segment Discovery，确认新瓶颈候选是否仍只是待办，还是已经有公司级证据。
5. 看低拥挤观察篮，挑出需要手工深挖的股票。
6. 最后看持仓映射，判断是否需要调整仓位、等待验证或补充研究。

## 后续改进清单

1. 补齐 A/H 股一致预期估值：当年、明年、后年 P/E 和 EV/EBITDA。
2. 增加 transcript 抓取和摘要，尤其是云厂商 capex、光通信、存储、电力。
3. 增加 segment 历史温度变化，记录从 Early 到 Hot 的迁移。
4. 增加股票级催化剂和证伪点。
5. 把持仓映射改成大白话段落，减少机器标签。
6. 增加人工 inbox 模板，方便把 X/Twitter、研报、电话会纪要贴进来。
7. 把 `data/emergent_segment_watch_*.json` 接入每日生成流程，让“剔除已拥挤 -> 候选验证 -> 进入/移出低拥挤篮”可追踪。
