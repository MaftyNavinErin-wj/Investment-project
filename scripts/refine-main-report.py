from pathlib import Path


REPORT = Path("reports/ai-radar-2026-05-24.md")


READING_UPDATE = """## 读法和本轮更新

这份报告先判断 AI capex 总水位，再看瓶颈如何从 GPU/ASIC 扩散到网络、内存、电力、散热和资源约束。下面的 `Segment 全景` 是完整地图；后面的 `赛道解读` 只解释应该如何读这张地图，避免和全景表逐条重复。

覆盖边界：报告结论基于已经抓取和核验到的公开资料，包括 SEC filings、公司 IR/press release、部分 earnings/transcript 页面、新闻/RSS 和市场数据。它不是对所有公司全部公开披露的穷尽覆盖；对链主公司 NVIDIA，则优先使用最新 10-Q、8-K 和官方季度业绩披露。

本轮完成 2/4/5 后，对结论有四点更新：

- **证据层面更扎实。** 本地证据库已经覆盖 SEC filings、IR 页面和部分 transcript / earnings links；主报告只引用会改变判断的证据，不再展开原文。
- **电力链和铜的优先级上调。** FCX 已把铜需求和 data centers / AI growth 直接联系起来；ETN 的 Fibrebond 收购提供 data-center modular power enclosure 证据。
- **水主题需要收窄定义。** 不再看泛水务，而是看 liquid cooling、coolant、CDU/cold plate、chilled-water 和 thermal infrastructure。ECL 的 CoolIT 证据强于 XYL 的泛水处理暴露。
- **HTCC、天然气中游、AI Apps 仍需第二证明。** HTCC 还缺陶瓷材料收入弹性；天然气需要合同/项目证明；AI Apps 需要付费采用、ARPU、留存或利润率证明 ROI。

"""


NVDA_CHAIN_MASTER = """## NVIDIA 链主披露：对上游的新增含义

NVIDIA 是 AI capex 链主，所以上游判断不能只看各自公司的叙事，还要看 NVIDIA 披露的瓶颈迁移方向。本轮重点核对了 NVIDIA 最新 10-Q、8-K 和官方 Q1 FY27 业绩披露。

| NVIDIA 披露信号 | 对上游的含义 | 对报告结论的影响 |
|---|---|---|
| Q1 FY27 revenue $81.6B，Data Center revenue $75.2B；Q2 FY27 revenue outlook $91.0B +/-2%。 | AI factory 总水位仍在上修，核心硬件链不能简单按见顶处理。 | 维持 AI capex macro 偏强，但高拥挤主线只做上修复核。 |
| Data Center compute revenue $60.4B；Data Center networking revenue $14.8B，networking YoY 增速显著高于 compute。 | 瓶颈继续从 GPU compute 向 networking、NVLink、InfiniBand、Spectrum-X Ethernet 扩散。 | 强化 Optical Modules、CPO/硅光、连接器/线缆、PCB 的产业逻辑，但这些方向多数已是 Hot Consensus。 |
| NVIDIA 披露 Blackwell 300 ramp，并称需求来自 InfiniBand、Spectrum-X Ethernet、NVLink solutions。 | Blackwell 系统化交付拉动的是整机/网络/互连/散热/电力，而不只是 GPU 芯片。 | 继续保留电力、液冷、PCB、连接器、光学作为 AI capex 关键二阶链条。 |
| NVIDIA 宣布 NVLink Fusion，并与 Marvell 合作；同时提到 silicon photonics，以及与 Coherent、Corning、Lumentum 的多年战略合作。 | 链主明确把自定义硅、光学、硅光、玻璃/光纤/激光器纳入平台生态。 | 上调对 CPO/硅光/advanced optics 的确定性，但投资动作仍要看估值和公司级收入弹性。 |
| 新 reporting framework 分为 Data Center 与 Edge Computing；Data Center 内部拆 Hyperscale 与 ACIE。10-Q 中 hyperscaler 约占 Data Center 一半，另一半来自多元 AI factory 客户。 | 需求不只来自四大云厂商，sovereign AI、AI cloud、enterprise/industrial AI factory 正在变成第二需求层。 | AI capex 不应只跟踪 hyperscaler capex，也要跟踪 neocloud、主权 AI、工业 AI factory 对电力/网络/冷却的需求。 |
| Q2 outlook 不假设来自中国的 Data Center compute revenue；H200 China licensing 仍未贡献收入且有进口/关税不确定性。 | 中国相关收入不是当前上修的核心来源，出口管制仍是风险变量。 | 对国内映射要谨慎：不能把 NVIDIA 总需求直接等同于中国链条需求。 |
| 10-Q 提到 manufacturing、supply、capacity commitments 反映 data-center-scale production 和更长的 future ordering horizons。 | 上游订单能见度提升，但也意味着链主对供应商的规划、取消/调整、库存和采购义务更关键。 | 对上游公司要看 backlog 质量、产能锁定、客户集中度和库存风险，不能只看“绑定 NVIDIA”。 |

**Additional findings：**

- Networking 是本轮 NVIDIA 披露中最强的边际信号。它支持光模块、光器件、交换/互连、CPO/硅光、连接器和高速 PCB，但这些方向已经拥挤，真正要找的是“收入弹性尚未被充分定价”的环节。
- Power/cooling 的逻辑不是 NVIDIA 直接点名某个供应商，而是由 Blackwell 系统化、AI factory、客户建设 data center infrastructure 的风险披露间接强化。它仍是二阶重点，但需要订单和项目证据。
- NVIDIA 对 Edge Computing 的新 reporting 让端侧/physical AI 有了更正式的观察入口，但短期 revenue 和投资确定性仍弱于 Data Center。

"""


KOL_WATCH = """## KOL / 外部观点交叉验证

我们需要外部 idea feed 来避免完全闭门造车，但 KOL 观点只作为线索，不作为结论。使用方式是：先记录观点，再映射到我们的 segment，最后判断它是验证、冲突、还是仅代表市场热度。

当前先从 CNBC Mad Money / Jim Cramer 开始，后续可以扩展到其他 KOL、sell-side notes、播客和产业访谈。

| 来源 / 人物 | 观点或提到的票 | 映射到我们的框架 | Cross-check 结论 | 对 A 股逻辑的间接意义 |
|---|---|---|---|---|
| Jim Cramer / Mad Money recap | Semis and AI infrastructure are driving the market; software is in the background. | AI Server、networking、CPO/硅光、memory interface、power/cooling。 | 验证我们“硬件和物理 AI infrastructure 仍是主线”的判断，但也说明这些方向已经接近共识。 | 光模块、PCB、连接器、存储接口、电力/散热仍可跟，但必须看业绩上修，不能只看叙事。 |
| Jim Cramer / Astera Labs | 对 ALAB 这类 AI connectivity / retimer / cable-module 暴露保持正面态度。 | Memory Interface / Retimer / CXL；Connectors / SerDes / High-speed Interconnect；NVLink connectivity。 | 和 NVIDIA 披露的 NVLink、networking、connectivity 瓶颈迁移一致。 | 间接验证澜起、中航光电、连接器/高速线缆链条，但仍需公司收入证明。 |
| Jim Cramer / NVIDIA | 强调 NVIDIA 是 AI 革命核心，但也提醒 AI 热门股可能过热。 | NVIDIA chain-master；AI Server；Data Center Networking；AI Factory。 | 支持我们把 NVIDIA 披露作为上游第一过滤器，同时保留拥挤度约束。 | A 股映射应围绕 NVIDIA 真实瓶颈，而不是所有带 AI 标签的公司。 |
| Jim Cramer / NVIDIA-China | 近期观点偏向 NVIDIA fundamentals / valuation，而不是 China recovery bet。 | Export controls；China read-through；Data Center compute。 | 与 NVIDIA Q2 outlook 不假设 China Data Center compute revenue 相吻合。 | 不应把 NVIDIA 全球需求直接等同于中国链条需求；国内映射要额外验证客户和出口限制。 |

**使用规则：**

- KOL 观点用于发现 idea 和衡量市场共识，不用于替代 primary-source evidence。
- 如果 KOL 观点和公司披露一致，提升该 segment 的验证优先级。
- 如果 KOL 观点很热但股价也高度拥挤，只能作为趋势确认，不能当 early opportunity。
- 如果 KOL 提到的美股逻辑能映射到 A 股，只能算间接验证，必须再找 A 股公司的订单、客户、收入或产能证据。

"""


INTERPRETATION = """## 赛道解读

`Segment 全景` 已经列出每个赛道的层级、温度、逻辑、映射、拥挤度和代表公司。这里不再重复逐条解释，而是给读者一个决策读法。

| 分组 | 包含赛道 | 当前含义 | 投资/研究动作 |
|---|---|---|---|
| Core but crowded | AI Server、HBM、DRAM/NAND/SSD、Memory Interface、Optical Modules、CPO/硅光、高速 PCB、连接器、电力设备、液冷、燃机、电网 EPC、光纤、测试、安全/可观测、Edge AI | AI capex 总水位仍支撑这些方向，但多数已是 Hot Consensus，高涨幅和高估值使容错率下降。 | 只做订单、价格、份额、盈利预测上修复核；不要把它们当 early theme。 |
| Warming / second-order | 天然气中游、铜/线缆/电气化金属、HTCC/陶瓷封装、AI Applications/Agents/ROI | 这些方向是瓶颈迁移后的二阶候选，但证明强度不同。铜/电力链证据最直接；HTCC、天然气、AI Apps 还需要第二证明。 | 继续看公司公告和 transcript，要求出现 backlog、合同、客户、收入拆分或 ROI 指标。 |
| Early but needs definition | Water / Zero-water Cooling / Treatment | 原始水资源主题太宽。真正可投逻辑应收窄到 liquid cooling、coolant、CDU/cold plate、chilled-water 和 thermal infrastructure。 | ECL 优先验证，XYL 观察；VRT 做行业景气和拥挤度 benchmark。 |

**本轮最重要的边际变化：**

- **上调：Copper / Cables / Electrification Metals。** FCX 10-Q 已明确提到 data centers 和 AI growth 支撑铜需求；ETN 的 data-center power exposure 进一步验证了 AI 电力链外溢。SCCO 可作为铜 beta 对照，但 1Y 涨幅已较大。
- **重新定义：Water / Zero-water Cooling / Treatment。** 不应按泛水务理解，而应按液冷/冷却液/热管理基础设施理解。ECL 因 CoolIT 收购进入优先验证；XYL 需要 data-center water/reuse 项目证据才可上调。
- **不升级：HTCC / Ceramic Packaging Materials。** APH 能证明 high-speed cable / fiber optic / interconnect 的需求，但不能直接证明 HTCC 或陶瓷材料收入弹性。
- **第二证明：Natural Gas Midstream。** 管道和压缩逻辑成立，但必须看到 data-center demand 转成 firm transport、pipeline laterals、compression 或长期合同。
- **第二证明：AI Applications / Agents / ROI。** 产品叙事已经很多，下一步只看付费采用、ARPU、工作流留存、推理工作量和利润率。

## 代表公司验证顺序

这张表不是推荐买入，而是把后续研究精力排序：先看能改变 AI capex 框架判断的公司，再看映射验证和拥挤度复核。

| 优先级 | 公司 | 代码 | 所属逻辑 | 3M | 1Y | 当前任务 |
|---|---|---|---|---:|---:|---|
| 1 | Freeport-McMoRan | FCX | 铜 / AI power-chain | -0.7% | +60.7% | 验证 AI/data-center 铜需求是否持续进入管理层口径和供给规划。 |
| 1 | Eaton | ETN | Critical power / data-center power enclosure | +4.3% | +23.3% | 验证 Fibrebond、data-center backlog、配电/模块化电力订单。 |
| 1 | Ecolab | ECL | liquid cooling / coolant / CoolIT | -15.6% | -2.0% | 验证 CoolIT 订单、客户、整合、利润率和交叉销售。 |
| 2 | Amphenol | APH | high-speed interconnect / cable | -12.5% | +55.5% | 用作高速互联映射证明，但不直接外推 HTCC。 |
| 2 | Xylem | XYL | water treatment / reuse | -14.4% | -10.0% | 只有出现 data-center water/reuse 项目证据才上调。 |
| 2 | Kinder Morgan / Williams / EQT | KMI/WMB/EQT | gas midstream / compression | n/a | n/a | 等合同、管道、压缩和数据中心电力项目证据。 |
| 2 | Tencent / Kuaishou / Microsoft / ServiceNow | 0700.HK/1024.HK/MSFT/NOW | AI Apps / ROI | n/a | n/a | 看付费采用、ARPU、留存、margin，而不是产品发布数量。 |

"""


def main():
    text = REPORT.read_text(encoding="utf-8")
    if "## 读法和本轮更新" not in text:
        text = text.replace("## Segment 全景\n", READING_UPDATE + "## Segment 全景\n", 1)
    elif "覆盖边界：" not in text:
        text = text.replace(
            "本轮完成 2/4/5 后，对结论有四点更新：",
            "覆盖边界：报告结论基于已经抓取和核验到的公开资料，包括 SEC filings、公司 IR/press release、部分 earnings/transcript 页面、新闻/RSS 和市场数据。它不是对所有公司全部公开披露的穷尽覆盖；对链主公司 NVIDIA，则优先使用最新 10-Q、8-K 和官方季度业绩披露。\n\n本轮完成 2/4/5 后，对结论有四点更新：",
            1,
        )
    if "## NVIDIA 链主披露" not in text:
        text = text.replace("## Segment 全景\n", NVDA_CHAIN_MASTER + "## Segment 全景\n", 1)
    if "## KOL / 外部观点交叉验证" not in text:
        text = text.replace("## 搜索热度线索\n", KOL_WATCH + "## 搜索热度线索\n", 1)
    if "## Theme Temperature" in text:
        start = text.index("## Theme Temperature")
        end = text.index("## 搜索热度线索")
        text = text[:start] + INTERPRETATION + text[end:]
    REPORT.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
