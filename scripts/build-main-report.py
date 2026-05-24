import datetime as dt
import html
import json
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(ROOT, "reports")
HISTORY = os.path.join(ROOT, "data", "segment_history.jsonl")
EVIDENCE_INDEX = os.path.join(ROOT, "evidence", "index.json")


COMPANY_NAMES = {
    "601138.SS": "工业富联",
    "688008.SS": "澜起科技",
    "300308.SZ": "中际旭创",
    "300502.SZ": "新易盛",
    "300394.SZ": "天孚通信",
    "002463.SZ": "沪电股份",
    "300476.SZ": "胜宏科技",
    "002179.SZ": "中航光电",
    "002335.SZ": "科华数据",
    "002837.SZ": "英维克",
    "688182.SS": "灿勤科技",
    "688200.SS": "华峰测控",
    "0700.HK": "腾讯控股",
    "1024.HK": "快手-W",
}


SEGMENT_OVERRIDES = {
    "ai_server_gpu": {
        "view": "核心主线",
        "action": "只做业绩上修复核",
        "note": "AI 服务器需求明确，但市场认知和股价拥挤度都高，不再当 early idea。",
    },
    "hbm": {
        "view": "核心主线",
        "action": "只做供需/价格复核",
        "note": "HBM 是明确瓶颈，但主线已经拥挤，重点看价格、产能和订单兑现。",
    },
    "dram_nand_ssd": {
        "view": "核心外溢",
        "action": "只做周期复核",
        "note": "存储价格和 AI 需求外溢成立，但股价已反映较多周期修复。",
    },
    "memory_interface": {
        "view": "核心外溢",
        "action": "只做超预期复核",
        "note": "逻辑强，但代表公司涨幅较大，需要盈利上修证明估值。",
    },
    "optical_modules": {
        "view": "核心主线",
        "action": "只做订单/份额复核",
        "note": "800G/1.6T 是确定性瓶颈，但中际、新易盛等已高度拥挤。",
    },
    "cpo_silicon_photonics": {
        "view": "瓶颈迁移",
        "action": "观察技术路线兑现",
        "note": "CPO/硅光方向重要，但需要客户导入、量产节奏和利润率证据。",
    },
    "pcb": {
        "view": "核心外溢",
        "action": "只做订单复核",
        "note": "高速 PCB 受 AI 服务器和交换机复杂度驱动，但股价同样拥挤。",
    },
    "connectors_serdes": {
        "view": "映射验证",
        "action": "保留中航光电/APH 验证",
        "note": "高速连接器、线缆、SerDes 逻辑成立，但需要区分纯 AI 暴露和泛工业暴露。",
    },
    "critical_power": {
        "view": "重点二阶",
        "action": "优先验证 ETN/科华数据",
        "note": "数据中心供电、配电、UPS、switchgear 是 AI capex 外溢最清晰的方向之一。",
    },
    "liquid_cooling": {
        "view": "重点二阶",
        "action": "VRT 做景气基准，ECL 做新线索",
        "note": "液冷/热管理方向确定，但纯液冷标的已拥挤；新增关注冷却液、CDU、cold plate。",
    },
    "power_generation_turbines": {
        "view": "电力约束",
        "action": "只做项目验证",
        "note": "燃机受数据中心电力需求支撑，但 GE Vernova 等已经不便宜。",
    },
    "gas_midstream": {
        "view": "第二验证",
        "action": "等待合同/管道/压缩证据",
        "note": "逻辑成立，但还需要 data-center demand 转化成 firm transport 或项目经济性。",
    },
    "grid_epc": {
        "view": "电力约束",
        "action": "只做 backlog 复核",
        "note": "电网 EPC 和变电站需求强，但 PWR/MYRG 等已有高涨幅。",
    },
    "copper_cables": {
        "view": "上调优先级",
        "action": "优先验证 FCX/ETN，SCCO 做 beta 对照",
        "note": "FCX 已明确把铜需求与 data centers 和 AI growth 联系起来，是本轮最值得上调的二阶方向。",
    },
    "fiber_preform_cable": {
        "view": "核心外溢",
        "action": "只做订单复核",
        "note": "光纤/预制棒/光缆受数据中心和光网络扩张支撑，但代表公司拥挤。",
    },
    "ceramic_packaging_htcc": {
        "view": "不升级",
        "action": "只做映射验证",
        "note": "目前证据支持 optical/high-speed interconnect，但不能直接推出 HTCC/陶瓷材料收入弹性。",
    },
    "water_resources": {
        "view": "改名收窄",
        "action": "ECL 优先，XYL 观察",
        "note": "不要看泛水务，改看液冷、冷却液、CDU/cold plate、chilled-water 和数据中心热管理服务。",
    },
    "test_yield": {
        "view": "隐性瓶颈",
        "action": "观察良率/测试订单",
        "note": "先进封装和 AI 芯片复杂度提升会带来测试需求，但股价已有反映。",
    },
    "ai_apps_agents": {
        "view": "ROI 验证",
        "action": "只看商业化指标",
        "note": "硬件 capex 需要应用层 ROI 闭环，重点是付费采用、ARPU、留存、工作量和利润率。",
    },
    "ai_governance_security": {
        "view": "软件外溢",
        "action": "只做估值约束下复核",
        "note": "AI 安全/治理/可观测性需求存在，但 NET/CRWD/DDOG 等估值和拥挤度高。",
    },
    "edge_ai": {
        "view": "远期观察",
        "action": "暂不作为主线",
        "note": "端侧 AI 可能受推理成本驱动，但当前逻辑和映射强度不如电力/液冷/铜。",
    },
}


PRIORITY_COMPANIES = [
    ("FCX", "Freeport-McMoRan", "铜 / AI power-chain", "优先验证", "公司文件明确提到 data centers 和 AI growth 支撑铜需求。"),
    ("ETN", "Eaton", "Critical power / 配电", "优先验证", "Fibrebond 带来 data-center modular power enclosure 证据。"),
    ("ECL", "Ecolab", "液冷 / 冷却液", "优先验证", "CoolIT 收购把主题从泛水务收窄到 data-center liquid cooling。"),
    ("APH", "Amphenol", "高速连接器 / 线缆", "映射验证", "可验证 high-speed cable / fiber optic / interconnect，但不能直接推出 HTCC。"),
    ("XYL", "Xylem", "水处理 / reuse", "观察", "有水处理和 reuse 能力，但缺少直接 data-center 项目证据。"),
    ("SCCO", "Southern Copper", "铜 beta", "对照", "铜主题 beta 强，但 1Y 涨幅较大，直接 AI 证据弱于 FCX。"),
    ("VRT", "Vertiv", "热管理 / critical power", "景气基准", "方向最纯，但 1Y 涨幅和估值拥挤，更多用于验证行业温度。"),
    ("KMI", "Kinder Morgan", "天然气中游", "第二验证", "等待数据中心电力需求转成运输合同或压缩项目证据。"),
    ("MSFT", "Microsoft", "AI 应用 / ROI", "ROI 验证", "看 Copilot/AI 工作负载的付费采用、留存和利润率。"),
    ("NOW", "ServiceNow", "AI agents", "ROI 验证", "看 agent workflow 商业化，而不是只看产品叙事。"),
]


def load_latest_segments():
    rows = []
    if not os.path.exists(HISTORY):
        return rows
    with open(HISTORY, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    if not rows:
        return []
    latest = max(row.get("date", "") for row in rows)
    return [row for row in rows if row.get("date") == latest]


def company_name(rep):
    quote = rep.get("quote", "")
    return COMPANY_NAMES.get(quote, rep.get("name") or quote)


def normalize_crowding(value):
    value = value or ""
    if "中" in value or "涓" in value:
        return "中高拥挤"
    if "高" in value or "楂" in value:
        return "高拥挤"
    if "尚可" in value or "皻" in value or "尚" in value:
        return "拥挤度尚可"
    if "待" in value or "寰" in value:
        return "待确认"
    return value or "待确认"


def fmt_pct(value):
    if value is None:
        return "n/a"
    return f"{value:+.1f}%"


def fmt_num(value):
    if value is None:
        return "n/a"
    return f"{value:.1f}x"


def market_by_ticker(segments):
    market = {}
    for segment in segments:
        for rep in segment.get("reps", []):
            ticker = rep.get("quote")
            if not ticker:
                continue
            market[ticker] = {
                "name": company_name(rep),
                "crowding": normalize_crowding(rep.get("crowding")),
                "return_3m": rep.get("return_3m"),
                "return_1y": rep.get("return_1y"),
                "forward_pe": rep.get("forward_pe"),
                "ev_to_ebitda": rep.get("ev_to_ebitda"),
            }
    return market


def evidence_count():
    if not os.path.exists(EVIDENCE_INDEX):
        return "本地证据库已建立，但 index 尚未生成"
    with open(EVIDENCE_INDEX, "r", encoding="utf-8", errors="replace") as f:
        index = json.load(f)
    return (
        f"{index.get('sec_filing_count', 0)} 份 SEC filings / "
        f"{index.get('sec_company_count', 0)} 家公司 / "
        f"{index.get('transcript_link_count', 0)} 个 earnings、results、webcast 或 presentation 链接"
    )


def segment_reps_text(segment, max_items=3):
    reps = []
    for rep in segment.get("reps", [])[:max_items]:
        reps.append(f"{company_name(rep)} ({rep.get('quote')})")
    return ", ".join(reps) if reps else "n/a"


def render_segment_dashboard(segments):
    lines = []
    lines.append("## Segment Dashboard")
    lines.append("")
    lines.append("这一页保留全部 segment，但每个方向只给决策需要的信息：现在处于什么温度、是否拥挤、该怎么处理。")
    lines.append("")
    lines.append("| # | Segment | 状态 | 温度 | 拥挤度 | 动作 | 代表公司 |")
    lines.append("|---:|---|---|---|---|---|---|")
    for idx, segment in enumerate(segments, 1):
        override = SEGMENT_OVERRIDES.get(segment.get("segment_id"), {})
        name = segment.get("segment_name", "").split(". ", 1)[-1]
        lines.append(
            f"| {idx} | {name} | {override.get('view', '观察')} | {segment.get('temperature', 'n/a')} | "
            f"{normalize_crowding(segment.get('crowding'))} | {override.get('action', '继续跟踪')} | {segment_reps_text(segment)} |"
        )
    lines.append("")
    return lines


def render_priority_companies(market):
    lines = []
    lines.append("## 重点公司清单")
    lines.append("")
    lines.append("这里不是买入名单，而是下一步验证顺序。优先级来自“产业逻辑 + 公司证据 + 股价/估值拥挤度”的交集。")
    lines.append("")
    lines.append("| 公司 | 代码 | 主题 | 角色 | 拥挤度 | 3M | 1Y | Fwd PE | EV/EBITDA | 为什么看 |")
    lines.append("|---|---|---|---|---|---:|---:|---:|---:|---|")
    for ticker, name, theme, role, why in PRIORITY_COMPANIES:
        row = market.get(ticker, {})
        lines.append(
            f"| {row.get('name', name)} | {ticker} | {theme} | {role} | {row.get('crowding', '待确认')} | "
            f"{fmt_pct(row.get('return_3m'))} | {fmt_pct(row.get('return_1y'))} | "
            f"{fmt_num(row.get('forward_pe'))} | {fmt_num(row.get('ev_to_ebitda'))} | {why} |"
        )
    lines.append("")
    return lines


def render_priority_segments():
    lines = []
    lines.append("## 本轮重点变化")
    lines.append("")
    lines.append("| 方向 | 结论 | 组合含义 | 下一步验证 |")
    lines.append("|---|---|---|---|")
    lines.append("| 铜 / 电力链 | 上调优先级 | FCX 和 ETN 的证据最直接，适合作为 AI power-chain 二阶扩散的主线验证。 | 看 data-center backlog、订单转化、铜供给响应。 |")
    lines.append("| 水 / 液冷 | 改名并收窄 | 不再看泛水务，改看 liquid cooling、coolant、CDU/cold plate、chilled-water 和热管理服务。 | ECL 优先，XYL 观察，VRT 做景气基准。 |")
    lines.append("| HTCC / 陶瓷材料 | 不升级 | 现有证据不能直接证明陶瓷材料收入弹性，只能作为映射验证。 | 继续找客户、产品、认证周期和收入拆分证据。 |")
    lines.append("| 天然气中游 | 第二验证 | 逻辑成立但缺少合同/项目级证据。 | 等数据中心电力需求转成 firm transport、laterals、compression economics。 |")
    lines.append("| AI 应用 / Agents | 看 ROI | 硬件 capex 需要应用层商业化闭环。 | 看付费采用、ARPU、留存、推理工作量和利润率。 |")
    lines.append("")
    return lines


def render_markdown():
    today = dt.datetime.now().strftime("%Y-%m-%d")
    segments = load_latest_segments()
    market = market_by_ticker(segments)

    lines = [f"# AI Capex Radar - {today}", ""]
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("AI capex 总水位仍在扩张，但主线硬件已经拥挤。本轮主报告的重点不是继续罗列证据，而是把已经验证过的资料转成可读的决策层：哪些方向继续复核，哪些方向上调，哪些方向暂时不能升级。")
    lines.append("")
    lines.append("- **上调：铜 / 电力链。** FCX 和 ETN 的公司级证据最直接，是本轮最值得继续验证的二阶方向。")
    lines.append("- **收窄：水资源。** 主题应改成液冷、冷却液、CDU/cold plate、chilled-water 和热管理服务；ECL 优先于 XYL。")
    lines.append("- **不升级：HTCC / 陶瓷材料。** 现在证据只够支持 optical/high-speed interconnect，不能直接推出陶瓷材料收入弹性。")
    lines.append("- **第二验证：天然气中游、AI 应用/Agents。** 都有逻辑，但需要合同、项目或 ROI 指标闭环。")
    lines.append("")

    lines.extend(render_priority_segments())
    lines.extend(render_segment_dashboard(segments))
    lines.extend(render_priority_companies(market))

    lines.append("## 风险和证伪")
    lines.append("")
    lines.append("- Hyperscaler capex 指引停止上修，或者数据中心项目推迟。")
    lines.append("- 电力、铜、液冷需求没有进入公司 backlog、订单、合同或收入指引。")
    lines.append("- AI 应用层 ROI 无法证明，导致市场开始质疑硬件 capex 回收周期。")
    lines.append("- 高拥挤标的继续靠估值扩张上涨，而不是盈利预测上修支撑。")
    lines.append("")

    lines.append("## 证据状态")
    lines.append("")
    lines.append(f"后台证据库当前包含：{evidence_count()}。主报告只保留影响判断的结论，证据原文不再逐条展示。")
    lines.append("")
    return "\n".join(lines)


def inline_markup(value):
    value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    return value


def render_html(markdown_text):
    escaped = html.escape(markdown_text)
    body = []
    in_list = False
    in_table = False
    for line in escaped.splitlines():
        if line.startswith("# "):
            body.append(f"<h1>{inline_markup(line[2:])}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{inline_markup(line[3:])}</h2>")
        elif line.startswith("|") and line.endswith("|"):
            cells = [inline_markup(cell.strip()) for cell in line.strip("|").split("|")]
            if all(set(cell) <= {"-", ":"} for cell in cells):
                continue
            if not in_table:
                body.append("<table>")
                in_table = True
                tag = "th"
            else:
                tag = "td"
            body.append("<tr>" + "".join(f"<{tag}>{cell}</{tag}>" for cell in cells) + "</tr>")
        else:
            if in_table:
                body.append("</table>")
                in_table = False
            if line.startswith("- "):
                if not in_list:
                    body.append("<ul>")
                    in_list = True
                body.append(f"<li>{inline_markup(line[2:])}</li>")
            else:
                if in_list:
                    body.append("</ul>")
                    in_list = False
                if line.strip():
                    body.append(f"<p>{inline_markup(line)}</p>")
    if in_table:
        body.append("</table>")
    if in_list:
        body.append("</ul>")
    css = """
    body { font-family: Arial, 'Microsoft YaHei', sans-serif; margin: 32px; color: #111827; line-height: 1.5; }
    h1 { font-size: 26px; margin-bottom: 18px; }
    h2 { font-size: 19px; margin-top: 28px; border-bottom: 1px solid #d1d5db; padding-bottom: 6px; }
    p { margin: 9px 0; }
    table { border-collapse: collapse; width: 100%; margin: 14px 0 20px; font-size: 11px; }
    th, td { border: 1px solid #d1d5db; padding: 6px; vertical-align: top; }
    th { background: #f3f4f6; text-align: left; }
    li { margin: 5px 0; }
    strong { font-weight: 700; }
    @media print { body { margin: 12mm; } table { font-size: 8.5px; } }
    """
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(body)}</body></html>"


def main():
    os.makedirs(REPORTS, exist_ok=True)
    today = dt.datetime.now().strftime("%Y-%m-%d")
    md_path = os.path.join(REPORTS, f"ai-radar-{today}.md")
    html_path = os.path.join(REPORTS, f"ai-radar-{today}.html")
    md = render_markdown()
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(render_html(md))
    print(md_path)
    print(html_path)


if __name__ == "__main__":
    main()
