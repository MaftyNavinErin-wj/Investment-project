import datetime as dt
import html
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORTS = ROOT / "reports"


KEY_MACRO = [
    "SPX",
    "NDX",
    "SOX",
    "VIX",
    "USGG2YR",
    "USGG5YR",
    "USGG10YR",
    "USGG30YR",
    "LUACOAS",
    "LF98OAS",
    "DXY",
    "HG1",
    "NG1",
    "CL1",
]

FOCUS_QUOTES = [
    "DELL",
    "SMCI",
    "HPE",
    "NVDA",
    "AVGO",
    "AMD",
    "MRVL",
    "ARM",
    "MU",
    "WDC",
    "ANET",
    "ALAB",
    "COHR",
    "LITE",
    "VRT",
    "ETN",
    "SU",
    "2317.TW",
    "2308.TW",
    "PWR",
    "GEV",
    "FCX",
    "CEG",
    "VST",
    "EQIX",
    "DLR",
    "300308.SZ",
    "300502.SZ",
    "300394.SZ",
    "002463.SZ",
    "688008.SS",
    "300476.SZ",
    "002179.SZ",
    "002837.SZ",
    "002335.SZ",
    "0700.HK",
    "1024.HK",
    "300750.SZ",
    "0300.HK",
]

HOLDINGS = [
    "300750.SZ",
    "300308.SZ",
    "002463.SZ",
    "688008.SS",
    "0700.HK",
    "0300.HK",
    "1024.HK",
]

MISSING_TRIGGER_TICKERS = []


def load_json(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def parse_float(value):
    try:
        if value in (None, ""):
            return None
        num = float(value)
        if math.isnan(num):
            return None
        return num
    except Exception:
        return None


def fmt_pct(value):
    if value is None:
        return "n/a"
    return f"{value:+.1f}%"


def fmt_num(value, digits=2):
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def fmt_bp(value):
    if value is None:
        return "n/a"
    return f"{value:+.0f}bp"


def row_maps(snapshot, history):
    snap_by_quote = {row.get("quote"): row for row in snapshot.get("rows", [])}
    hist_by_quote = {row.get("quote"): row for row in history.get("rows", [])}
    return snap_by_quote, hist_by_quote


def field(row, name):
    return parse_float((row.get("fields") or {}).get(name)) if row else None


def history_points(row):
    points = []
    for item in (row or {}).get("field_data", []):
        px = parse_float(item.get("PX_LAST"))
        if px is None:
            continue
        points.append((item.get("date"), px))
    return points


def trailing_return(points, days):
    if len(points) <= days:
        return None
    last = points[-1][1]
    prev = points[-1 - days][1]
    if not prev:
        return None
    return (last / prev - 1) * 100


def trailing_bp(points, days):
    if len(points) <= days:
        return None
    return (points[-1][1] - points[-1 - days][1]) * 100


def max_drawdown(points, lookback=90):
    window = points[-lookback:] if len(points) > lookback else points
    if not window:
        return None
    peak = window[0][1]
    worst = 0.0
    for _, px in window:
        peak = max(peak, px)
        if peak:
            worst = min(worst, px / peak - 1)
    return worst * 100


def enrich(row, hist_row):
    points = history_points(hist_row)
    return {
        "name": row.get("name"),
        "quote": row.get("quote"),
        "security": row.get("security"),
        "price": field(row, "PX_LAST"),
        "d1": field(row, "CHG_PCT_1D"),
        "d5": field(row, "CHG_PCT_5D"),
        "m1": field(row, "CHG_PCT_1M"),
        "m3": field(row, "CHG_PCT_3M"),
        "y1": field(row, "CHG_PCT_1YR"),
        "vol30": field(row, "VOLATILITY_30D"),
        "pe": field(row, "BEST_PE_RATIO") or field(row, "PE_RATIO"),
        "pe27": field(row, "PE_27E_BEST_PE_RATIO"),
        "pe28": field(row, "PE_28E_BEST_PE_RATIO"),
        "ret5": trailing_return(points, 5),
        "ret20": trailing_return(points, 20),
        "ret60": trailing_return(points, 60),
        "dd90": max_drawdown(points, 90),
        "points": points,
    }


def markdown_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    lines.extend("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows)
    return lines


def to_html(markdown, title):
    body = []
    in_table = False
    for line in markdown.splitlines():
        if line.startswith("# "):
            body.append(f"<h1>{html.escape(line[2:])}</h1>")
            continue
        if line.startswith("## "):
            if in_table:
                body.append("</tbody></table>")
                in_table = False
            body.append(f"<h2>{html.escape(line[3:])}</h2>")
            continue
        if line.startswith("- "):
            body.append(f"<p class='bullet'>{html.escape(line)}</p>")
            continue
        if line.startswith("|"):
            cells = [html.escape(cell.strip()) for cell in line.strip("|").split("|")]
            if set(cells) == {"---"}:
                continue
            if not in_table:
                body.append("<table><tbody>")
                in_table = True
            tag = "th" if cells and cells[0] in ("指标", "资产", "名称", "持仓", "情景") else "td"
            body.append("<tr>" + "".join(f"<{tag}>{cell}</{tag}>" for cell in cells) + "</tr>")
            continue
        if in_table:
            body.append("</tbody></table>")
            in_table = False
        if line.strip():
            body.append(f"<p>{html.escape(line)}</p>")
    if in_table:
        body.append("</tbody></table>")
    style = """
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 36px; color: #172026; line-height: 1.55; }
    h1 { font-size: 28px; margin-bottom: 8px; }
    h2 { font-size: 20px; margin-top: 28px; border-bottom: 1px solid #d9e0e6; padding-bottom: 6px; }
    table { border-collapse: collapse; width: 100%; margin: 12px 0 20px; font-size: 13px; }
    th, td { border: 1px solid #d9e0e6; padding: 7px 8px; text-align: left; vertical-align: top; }
    th { background: #f3f6f8; }
    .bullet { margin: 6px 0; }
    """
    return f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title><style>{style}</style></head><body>{''.join(body)}</body></html>"


def build_report():
    snapshot = load_json("bloomberg_snapshot_latest.json")
    history = load_json("bloomberg_history_latest.json")
    snap_by_quote, hist_by_quote = row_maps(snapshot, history)

    rows = {
        quote: enrich(snap_by_quote[quote], hist_by_quote.get(quote))
        for quote in snap_by_quote
        if quote in snap_by_quote
    }
    macro = {quote: rows[quote] for quote in KEY_MACRO if quote in rows}
    focus = [rows[quote] for quote in FOCUS_QUOTES if quote in rows]
    holdings = [rows[quote] for quote in HOLDINGS if quote in rows]
    losers = sorted(focus, key=lambda row: row["d1"] if row["d1"] is not None else 999)[:12]
    winners = sorted(focus, key=lambda row: row["d1"] if row["d1"] is not None else -999, reverse=True)[:8]

    sox = macro.get("SOX", {})
    ndx = macro.get("NDX", {})
    vix = macro.get("VIX", {})
    us10 = macro.get("USGG10YR", {})
    us2 = macro.get("USGG2YR", {})
    ig = macro.get("LUACOAS", {})
    hy = macro.get("LF98OAS", {})

    today = dt.date.today().isoformat()
    lines = [
        f"# AI Capex Radar 外围波动快报 - {today}",
        "",
        f"Bloomberg snapshot: {snapshot.get('created_at')}；history: {history.get('created_at')}；样本数 {len(snapshot.get('rows', []))}。",
        "",
        "## 一句话",
        "",
        (
            "这次波动更像“AI 硬件链高拥挤 + 折现率上行”的估值再定价，"
            "不是 AI capex 订单逻辑已经被证伪。操作上先把高 beta/高涨幅链条当成风险资产处理，"
            "等待 SOX、10Y 和信用利差给二次确认。"
        ),
        "",
        "## 关键市场读数",
        "",
    ]
    lines.extend(
        markdown_table(
            ["指标", "最新", "1D", "5D", "1M", "60D/3M", "说明"],
            [
                ["S&P 500", fmt_num(macro.get("SPX", {}).get("price")), fmt_pct(macro.get("SPX", {}).get("d1")), fmt_pct(macro.get("SPX", {}).get("d5")), fmt_pct(macro.get("SPX", {}).get("m1")), fmt_pct(macro.get("SPX", {}).get("m3")), "大盘风险偏好"],
                ["Nasdaq 100", fmt_num(ndx.get("price")), fmt_pct(ndx.get("d1")), fmt_pct(ndx.get("d5")), fmt_pct(ndx.get("m1")), fmt_pct(ndx.get("m3")), "长久期成长/AI 权重"],
                ["SOX", fmt_num(sox.get("price")), fmt_pct(sox.get("d1")), fmt_pct(sox.get("d5")), fmt_pct(sox.get("m1")), fmt_pct(sox.get("m3")), "半导体拥挤度的核心温度计"],
                ["VIX", fmt_num(vix.get("price")), fmt_pct(vix.get("d1")), fmt_pct(vix.get("d5")), fmt_pct(vix.get("m1")), fmt_pct(vix.get("m3")), "波动率冲击"],
                ["US 2Y", fmt_num(us2.get("price")), fmt_bp(trailing_bp(us2.get("points", []), 1)), fmt_bp(trailing_bp(us2.get("points", []), 5)), fmt_bp(trailing_bp(us2.get("points", []), 20)), fmt_bp(trailing_bp(us2.get("points", []), 60)), "Fed 路径预期"],
                ["US 10Y", fmt_num(us10.get("price")), fmt_bp(trailing_bp(us10.get("points", []), 1)), fmt_bp(trailing_bp(us10.get("points", []), 5)), fmt_bp(trailing_bp(us10.get("points", []), 20)), fmt_bp(trailing_bp(us10.get("points", []), 60)), "估值折现率/项目融资"],
                ["IG OAS", fmt_num(ig.get("price")), fmt_bp(trailing_bp(ig.get("points", []), 1)), fmt_bp(trailing_bp(ig.get("points", []), 5)), fmt_bp(trailing_bp(ig.get("points", []), 20)), fmt_bp(trailing_bp(ig.get("points", []), 60)), "信用风险传导"],
                ["HY OAS", fmt_num(hy.get("price")), fmt_bp(trailing_bp(hy.get("points", []), 1)), fmt_bp(trailing_bp(hy.get("points", []), 5)), fmt_bp(trailing_bp(hy.get("points", []), 20)), fmt_bp(trailing_bp(hy.get("points", []), 60)), "风险资产融资压力"],
                ["DXY", fmt_num(macro.get("DXY", {}).get("price")), fmt_pct(macro.get("DXY", {}).get("d1")), fmt_pct(macro.get("DXY", {}).get("d5")), fmt_pct(macro.get("DXY", {}).get("m1")), fmt_pct(macro.get("DXY", {}).get("m3")), "美元流动性"],
                ["Copper", fmt_num(macro.get("HG1", {}).get("price")), fmt_pct(macro.get("HG1", {}).get("d1")), fmt_pct(macro.get("HG1", {}).get("d5")), fmt_pct(macro.get("HG1", {}).get("m1")), fmt_pct(macro.get("HG1", {}).get("m3")), "AI 电力/工业需求 proxy"],
            ],
        )
    )

    lines.extend(
        [
            "",
            "## AI 链条跌幅",
            "",
        ]
    )
    lines.extend(
        markdown_table(
            ["资产", "名称", "最新", "1D", "5D", "1M", "3M", "90D回撤", "估值"],
            [
                [
                    row["quote"],
                    row["name"],
                    fmt_num(row["price"]),
                    fmt_pct(row["d1"]),
                    fmt_pct(row["d5"]),
                    fmt_pct(row["m1"]),
                    fmt_pct(row["m3"]),
                    fmt_pct(row["dd90"]),
                    f"PE {fmt_num(row['pe'])} / 27E {fmt_num(row['pe27'])}",
                ]
                for row in losers
            ],
        )
    )

    lines.extend(["", "## 反向韧性", ""])
    lines.extend(
        markdown_table(
            ["资产", "名称", "1D", "5D", "1M", "3M", "说明"],
            [
                [row["quote"], row["name"], fmt_pct(row["d1"]), fmt_pct(row["d5"]), fmt_pct(row["m1"]), fmt_pct(row["m3"]), "跌幅较小或逆势，观察是否是防御/补涨/非共识"]
                for row in winners
            ],
        )
    )

    lines.extend(["", "## 持仓读数", ""])
    lines.extend(
        markdown_table(
            ["持仓", "名称", "最新", "1D", "5D", "1M", "3M", "动作含义"],
            [
                [
                    row["quote"],
                    row["name"],
                    fmt_num(row["price"]),
                    fmt_pct(row["d1"]),
                    fmt_pct(row["d5"]),
                    fmt_pct(row["m1"]),
                    fmt_pct(row["m3"]),
                    holding_action(row),
                ]
                for row in holdings
            ],
        )
    )

    lines.extend(
        [
            "",
            "## 策略框架",
            "",
            "- 第一优先级是控 beta：如果 SOX/NDX 继续放量下跌，同时 10Y 继续上行，高涨幅硬件链先降风险，不急着左侧加满。",
            "- 第二优先级是看信用：IG/HY OAS 目前没有明显失控，如果信用不走阔，这更像估值冲击；如果信用开始同步走阔，要把 data center 融资链条风险上调。",
            "- 第三优先级是分层买回：核心订单/盈利可见度强的票等恐慌释放后分批；纯估值扩张、主题补涨和二阶弱映射先不接。",
            "- A 股映射上，光模块、PCB、内存接口仍是产业主线，但当前很多票已经是高拥挤，后续必须靠订单、毛利率和盈利预测继续上修来消化估值。",
            "- 应用/ROI 方向相对不是本轮下跌核心，但如果硬件链调整，市场可能重新追问 AI 投入回报，腾讯、快手这类应看 AI 是否转成收入和利润，而不是只看 capex。",
        ]
    )
    if MISSING_TRIGGER_TICKERS:
        lines.extend(
            [
                "",
                "## 数据缺口",
                "",
                "这次 Bloomberg request 当前没有纳入以下触发源单票："
                + "、".join(f"{quote} ({security})" for quote, security in MISSING_TRIGGER_TICKERS)
                + "。本报告已用 SOX/NDX 和已有供应链票覆盖外围冲击；若要把缺口单票纳入下一版表格，需要补 request 后再跑一次 VDI。",
            ]
        )

    return "\n".join(lines)


def holding_action(row):
    quote = row["quote"]
    d1 = row["d1"] or 0
    m1 = row["m1"] or 0
    if quote in {"300308.SZ", "002463.SZ", "688008.SS"}:
        if m1 > 20:
            return "主线仍强但拥挤高，反弹先看兑现，新增仓位等缩量企稳/业绩上修。"
        return "主线映射明确，若跌幅扩大但订单未坏，可分批观察。"
    if quote in {"0700.HK", "1024.HK"}:
        return "偏 AI ROI/应用侧，受硬件杀估值影响较间接，重点看收入和利润兑现。"
    if quote == "300750.SZ":
        return "AI 电力/储能是加分项，但不按纯 AI capex beta 处理。"
    if d1 < -5:
        return "先确认是否只是系统性去 beta，再看基本面是否变化。"
    return "按原基本面框架观察。"


def main():
    REPORTS.mkdir(exist_ok=True)
    today = dt.date.today().isoformat()
    markdown = build_report()
    md_path = REPORTS / f"ai-radar-{today}-volatility.md"
    html_path = REPORTS / f"ai-radar-{today}-volatility.html"
    md_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(to_html(markdown, f"AI Capex Radar Volatility {today}"), encoding="utf-8")
    print(md_path)
    print(html_path)


if __name__ == "__main__":
    main()
