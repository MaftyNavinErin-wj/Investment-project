import datetime as dt
import html
import importlib.util
import os
import re


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(ROOT, "reports")
ANALYZER_PATH = os.path.join(ROOT, "scripts", "analyze-segment-evidence.py")


COMPANY_NOTES = [
    {
        "ticker": "ETN",
        "company": "Eaton",
        "segment": "Critical Power / Copper / Electrical Infrastructure",
        "stance": "优先验证",
        "thesis": "AI 数据中心从 GPU 约束继续外溢到供电、配电、模块化电力设施，ETN 是比纯液冷更低 beta 的电力链候选。",
        "mapping": "直接映射在数据中心电力系统、模块化 power enclosure、switchgear/UPS/配电；间接映射在电网扩容与电气化。",
        "not_proven": "还没有量化到 AI/data-center 订单占比、backlog 斜率、价格/毛利弹性；当前仍可能被市场当作 broad electrification 而非纯 AI capex 交易。",
        "questions": "下一步看 earnings transcript 是否披露 data-center backlog、large project conversion、capacity/lead time、Fibrebond 收购后的订单协同。",
        "terms": ["Fibrebond", "data center", "modular power", "power enclosure", "backlog"],
    },
    {
        "ticker": "FCX",
        "company": "Freeport-McMoRan",
        "segment": "Copper / Electrification Metals",
        "stance": "优先验证",
        "thesis": "铜是 AI power-chain 最干净的上游瓶颈之一；FCX 的文件已经把 copper demand 与 data centers/AI growth 明确挂钩。",
        "mapping": "直接映射不是服务器，而是数据中心、电网、连接性、城市化共同推升的铜需求；适合作为 AI 电力扩张的 commodity beta。",
        "not_proven": "公司层面收益仍高度受铜价、矿山执行、成本与宏观需求影响；AI 只是需求因子之一，不是完整定价因子。",
        "questions": "下一步验证 management 对 AI/data-center 需求的量化口径、2026-2027 supply response、成本曲线和项目审批风险。",
        "terms": ["data centers", "artificial intelligence", "copper", "electrification", "connectivity"],
    },
    {
        "ticker": "SCCO",
        "company": "Southern Copper",
        "segment": "Copper / Electrification Metals",
        "stance": "次优先验证",
        "thesis": "SCCO 给铜主题提供另一只高经营杠杆样本，但目前本地证据对 AI/data-center 的直接表述弱于 FCX。",
        "mapping": "主要是铜价和长期铜供需 beta，适合与 FCX 对照，判断市场买的是 AI power-chain 还是泛铜周期。",
        "not_proven": "1Y 涨幅已经很大，拥挤度中高；若没有更直接的 AI/data-center 需求证据，风险回报弱于 FCX。",
        "questions": "下一步找 recent transcript 中对 AI/data center、电网、electrification 的定量讨论，并核对 capex/production growth 节奏。",
        "terms": ["copper", "electrification", "power", "demand", "capital"],
    },
    {
        "ticker": "APH",
        "company": "Amphenol",
        "segment": "Connectors / High-speed Cable / Optical Interconnect",
        "stance": "映射验证",
        "thesis": "APH 可作为高速互联、光纤、连接器的美股验证样本，但它不是纯 AI 标的，收入暴露需要拆解。",
        "mapping": "映射到 high-speed cable、fiber optic、power/interconnect products；可作为 A 股连接器/线缆映射的 proof source。",
        "not_proven": "文件支持 high-speed/fiber/interconnect，但没有直接证明 HTCC/ceramic packaging 或 CPO 材料收入弹性。",
        "questions": "下一步看 transcript 对 IT datacom、AI cluster、high-speed cable、margin mix 的拆分；HTCC 主题暂不升级为核心。",
        "terms": ["high-speed cable", "fiber optic", "interconnect", "power", "datacom"],
    },
    {
        "ticker": "ECL",
        "company": "Ecolab",
        "segment": "Liquid Cooling / Coolant / Water Treatment",
        "stance": "优先验证",
        "thesis": "水主题需要重新定义为液冷/冷却液/热管理基础设施；ECL 的 CoolIT 收购让这个映射从泛水处理变成更直接的数据中心冷却链。",
        "mapping": "CoolIT 对应 CDUs、cold plates、data-center liquid cooling；ECL 原有水处理能力可补 coolant、water quality、运营服务。",
        "not_proven": "交易尚需看整合、收入贡献、利润率、客户重合度；不能简单把 ECL 当作传统 water utility。",
        "questions": "下一步跟踪收购完成时间、CoolIT 订单规模、AI 数据中心客户、冷却液/水处理交叉销售。",
        "terms": ["CoolIT", "data center liquid cooling", "coolant", "cold plates", "CDUs"],
    },
    {
        "ticker": "XYL",
        "company": "Xylem",
        "segment": "Water Reuse / Treatment / Industrial Water",
        "stance": "观察验证",
        "thesis": "XYL 有水处理、reuse、outsourced water 等能力，但目前本地文件中直接 AI/data-center 证据弱；更适合作为对照样本。",
        "mapping": "可能映射到数据中心用水、循环水、工业水处理和运营服务，但需要客户/项目级证据。",
        "not_proven": "过去 1 年股价表现弱，主题映射也弱；没有直接 data-center water 订单之前，不应把它放进第一优先级。",
        "questions": "下一步只验证 data-center water reuse/treatment 项目、hyperscaler 客户、服务收入增长，不要被泛水资源叙事带偏。",
        "terms": ["water", "reuse", "treatment", "outsourced water", "recycle"],
    },
    {
        "ticker": "VRT",
        "company": "Vertiv",
        "segment": "Thermal Management / Critical Power",
        "stance": "高拥挤基准",
        "thesis": "VRT 是 AI 电力/热管理链的高纯度基准，但 1Y 涨幅和估值拥挤已经很高，更适合作为验证行业景气的 benchmark。",
        "mapping": "直接映射 AI-ready data centers、liquid cooling、thermal management、critical power。",
        "not_proven": "基本面方向强，但投资结论受估值和拥挤度约束；除非上修继续超预期，否则不应替代更早期的 second-order 机会。",
        "questions": "下一步用 VRT 的订单、backlog、thermal/liquid cooling 评论验证 ECL/ETN/XYL 的上游扩散逻辑。",
        "terms": ["AI-ready Data Centers", "liquid cooling", "thermal management", "critical power", "high performance computing"],
    },
]


def load_analyzer():
    spec = importlib.util.spec_from_file_location("segment_evidence", ANALYZER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def clean_snippet(value):
    value = re.sub(r"\s+", " ", value or "").strip()
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return value[:420].strip()


def best_evidence(analyzer, ticker, terms):
    candidates = []
    for path in analyzer.evidence_files():
        if analyzer.ticker_from_path(path) != ticker:
            continue
        try:
            text = analyzer.read_text(path)
        except Exception:
            continue
        lower = text.lower()
        for term in terms:
            if term.lower() in lower:
                value = analyzer.snippet(text, term, width=420)
                if value:
                    rel = os.path.relpath(path, ROOT).replace("\\", "/")
                    candidates.append((analyzer.snippet_noise_score(value), term, rel, clean_snippet(value)))
    candidates.sort(key=lambda item: (item[0], len(item[3])))
    return candidates[:3]


def market_rows(analyzer):
    rows = {}
    for ticker, row in analyzer.latest_segment_history().items():
        rows[ticker] = row
    return rows


def fmt_pct(value):
    if value is None:
        return "n/a"
    return f"{value:+.1f}%"


def fmt_mult(value):
    if value is None:
        return "n/a"
    return f"{value:.1f}x"


def render_md(analyzer):
    today = dt.datetime.now().strftime("%Y-%m-%d")
    market = market_rows(analyzer)
    lines = [f"# Company Notes - AI Second-Order Verification - {today}", ""]
    lines.append("Purpose: turn the segment-level work into company-level verification tasks. Scope is local SEC/IR/transcript evidence plus the latest market snapshot in `data/segment_history.jsonl`.")
    lines.append("")
    lines.append("## Portfolio Implication")
    lines.append("")
    lines.append("- **结论变化 1: 铜/电力链继续上调优先级。** FCX 的 primary-source 证据最直接，ETN 的 data-center power 证据更接近设备订单；SCCO 做铜价 beta 对照。")
    lines.append("- **结论变化 2: 水资源主题需要改名。** 不是买 generic water scarcity，而是找液冷、冷却液、冷板/CDU、chilled-water、数据中心热管理服务。ECL 优先级高于 XYL。")
    lines.append("- **结论变化 3: APH 是连接器/高速线缆 proof source，不是 HTCC 结论。** 现阶段不能因为 APH 有 optical/high-speed cable，就直接推出 ceramic/HTCC 材料弹性。")
    lines.append("- **结论变化 4: VRT 作为景气验证基准，不作为低拥挤增量首选。** 它证明热管理和 critical power 方向仍强，但估值/涨幅已经把容错率压低。")
    lines.append("")
    lines.append("## Snapshot")
    lines.append("")
    lines.append("| Ticker | Stance | Segment | Crowding | 3M | 1Y | Fwd PE | EV/EBITDA |")
    lines.append("|---|---|---|---|---:|---:|---:|---:|")
    for note in COMPANY_NOTES:
        m = market.get(note["ticker"], {})
        lines.append(
            f"| {note['ticker']} | {note['stance']} | {note['segment']} | {m.get('crowding', 'n/a')} | "
            f"{fmt_pct(m.get('return_3m'))} | {fmt_pct(m.get('return_1y'))} | {fmt_mult(m.get('forward_pe'))} | {fmt_mult(m.get('ev_to_ebitda'))} |"
        )
    lines.append("")

    lines.append("## Company Notes")
    lines.append("")
    for note in COMPANY_NOTES:
        m = market.get(note["ticker"], {})
        lines.append(f"### {note['ticker']} - {note['company']}")
        lines.append("")
        lines.append(f"- **Action:** {note['stance']}")
        lines.append(f"- **Thesis hook:** {note['thesis']}")
        lines.append(f"- **AI capex mapping:** {note['mapping']}")
        lines.append(f"- **Not proven yet:** {note['not_proven']}")
        lines.append(
            f"- **Market context:** crowding {m.get('crowding', 'n/a')}; 3M {fmt_pct(m.get('return_3m'))}; "
            f"1Y {fmt_pct(m.get('return_1y'))}; forward PE {fmt_mult(m.get('forward_pe'))}; EV/EBITDA {fmt_mult(m.get('ev_to_ebitda'))}."
        )
        lines.append(f"- **Next checks:** {note['questions']}")
        evidence = best_evidence(analyzer, note["ticker"], note["terms"])
        if evidence:
            lines.append("- **Local evidence:**")
            for _, term, path, snippet in evidence:
                lines.append(f"  - `{term}` from `{path}`: {snippet}")
        else:
            lines.append("- **Local evidence:** no clean local snippet found; needs transcript/manual source pull.")
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
        elif line.startswith("### "):
            body.append(f"<h3>{inline_markup(line[4:])}</h3>")
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
            elif line.startswith("  - "):
                if not in_list:
                    body.append("<ul>")
                    in_list = True
                body.append(f"<li class='sub'>{inline_markup(line[4:])}</li>")
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
    h2 { font-size: 20px; margin-top: 28px; border-bottom: 1px solid #d1d5db; padding-bottom: 6px; }
    h3 { font-size: 16px; margin-top: 22px; color: #0f172a; }
    table { border-collapse: collapse; width: 100%; margin: 14px 0 22px; font-size: 12px; }
    th, td { border: 1px solid #d1d5db; padding: 7px; vertical-align: top; }
    th { background: #f3f4f6; text-align: left; }
    li { margin: 5px 0; }
    li.sub { margin-left: 18px; color: #374151; }
    code { background: #f3f4f6; padding: 1px 4px; border-radius: 3px; }
    strong { font-weight: 700; }
    @media print { body { margin: 14mm; } table { font-size: 9px; } }
    """
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{''.join(body)}</body></html>"


def main():
    os.makedirs(REPORTS, exist_ok=True)
    analyzer = load_analyzer()
    md = render_md(analyzer)
    out = os.path.join(REPORTS, f"company-notes-{dt.datetime.now():%Y-%m-%d}.md")
    html_out = os.path.splitext(out)[0] + ".html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(md)
    with open(html_out, "w", encoding="utf-8") as f:
        f.write(render_html(md))
    print(out)
    print(html_out)


if __name__ == "__main__":
    main()
