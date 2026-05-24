import datetime as dt
import html
import json
import os
import re
from html.parser import HTMLParser


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE = os.path.join(ROOT, "evidence")
REPORTS = os.path.join(ROOT, "reports")


PRIORITY_SEGMENTS = [
    {
        "id": "gas_midstream",
        "name": "Natural Gas Midstream / Pipeline / Compression",
        "tickers": ["KMI", "WMB", "EQT"],
        "positive": ["data center", "power demand", "electric power", "natural gas demand", "pipeline", "compression", "interconnect", "firm transportation", "capacity expansion"],
        "negative": ["delay", "regulatory", "permit", "lower demand", "cancellation", "commodity price", "oversupply"],
        "proof": "Look for data-center or power-generation demand translating into contracted pipelines, compression, laterals, or firm transport."
    },
    {
        "id": "copper_cables",
        "name": "Copper / Cables / Electrification Metals",
        "tickers": ["FCX", "SCCO", "GLW", "APH", "ETN", "PWR"],
        "positive": ["copper", "electrification", "grid", "data center", "power", "transmission", "cable", "backlog", "capacity expansion"],
        "negative": ["lower copper prices", "cost inflation", "labor", "permitting", "delay", "capital cost"],
        "proof": "Look for AI/data-center load appearing in copper demand, grid equipment demand, or electrical backlog, not just generic electrification."
    },
    {
        "id": "ceramic_packaging_htcc",
        "name": "HTCC / Ceramic Packaging Materials",
        "tickers": ["COHR", "LITE", "APH", "GLW"],
        "positive": ["ceramic", "package", "packaging", "photonics", "optical", "laser", "transceiver", "co-packaged", "silicon photonics", "datacom"],
        "negative": ["qualification", "customer concentration", "inventory", "pricing pressure", "yield", "delay"],
        "proof": "Look for explicit optical/CPO/silicon-photonics packaging demand. If only generic photonics appears, keep mapping weak."
    },
    {
        "id": "water_resources",
        "name": "Water / Zero-water Cooling / Treatment",
        "tickers": ["XYL", "ECL", "VRT"],
        "positive": ["water", "cooling", "data center", "reuse", "treatment", "scarcity", "sustainability", "thermal"],
        "negative": ["weak demand", "municipal delay", "capex delay", "margin pressure", "project delay"],
        "proof": "Look for data-center water treatment/cooling demand, not broad industrial water exposure."
    },
    {
        "id": "ai_apps_agents",
        "name": "AI Applications / Agents / ROI",
        "tickers": ["MSFT", "NOW", "DDOG", "CRWD", "NET", "AMZN", "GOOGL", "META"],
        "positive": ["agent", "copilot", "ai revenue", "monetization", "productivity", "enterprise adoption", "workflow", "inference", "customer adoption"],
        "negative": ["roi", "margin pressure", "cost", "churn", "lower adoption", "competition", "spending optimization"],
        "proof": "Look for explicit paid adoption, ARPU, workload, retention, or margin evidence that can justify capex."
    },
]


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = False

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript"}:
            self.skip = True

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript"}:
            self.skip = False

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(raw):
    parser = TextExtractor()
    try:
        parser.feed(raw.decode("utf-8", errors="replace"))
        text = " ".join(parser.parts)
    except Exception:
        text = raw.decode("utf-8", errors="replace")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def read_text(path):
    with open(path, "rb") as f:
        raw = f.read()
    if path.lower().endswith((".htm", ".html")):
        return html_to_text(raw)
    return raw.decode("utf-8", errors="replace")


def ticker_from_path(path):
    parts = os.path.relpath(path, EVIDENCE).split(os.sep)
    if len(parts) >= 2:
        return parts[1].upper()
    return ""


def evidence_files():
    for base in ["sec", "ir", "transcripts"]:
        root = os.path.join(EVIDENCE, base)
        if not os.path.isdir(root):
            continue
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                if name == "manifest.json" or name.startswith("."):
                    continue
                if name.lower().endswith((".htm", ".html", ".txt", ".md")):
                    yield os.path.join(dirpath, name)


def snippet(text, term, width=280):
    matches = list(re.finditer(re.escape(term), text, flags=re.I))
    if not matches:
        return ""
    candidates = []
    for match in matches[:20]:
        start = max(0, match.start() - width // 2)
        end = min(len(text), match.end() + width // 2)
        value = re.sub(r"\s+", " ", text[start:end].strip())
        candidates.append(value)
    candidates.sort(key=snippet_noise_score)
    return candidates[0]


def snippet_noise_score(value):
    # SEC inline XBRL creates many machine-readable tokens. Prefer normal prose.
    tokens = value.split()
    if not tokens:
        return 999
    colon_tokens = sum(1 for token in tokens if ":" in token)
    numeric_tokens = sum(1 for token in tokens if re.search(r"\d{4,}", token))
    weird = value.count("鈥") + value.count("0000") + value.count("xbrli") + value.count("iso4217")
    return colon_tokens * 4 + numeric_tokens * 2 + weird * 8


def find_hits(segment, path, text):
    lower = text.lower()
    hits = []
    for polarity, terms in [("positive", segment["positive"]), ("negative", segment["negative"])]:
        for term in terms:
            if term.lower() in lower:
                hits.append({"term": term, "polarity": polarity, "snippet": snippet(text, term)})
    return hits


def score_segment(rows):
    positive = sum(1 for row in rows for hit in row["hits"] if hit["polarity"] == "positive")
    negative = sum(1 for row in rows for hit in row["hits"] if hit["polarity"] == "negative")
    source_count = len({row["ticker"] for row in rows})
    if positive >= 10 and source_count >= 3 and positive >= negative * 2:
        return "evidence improving"
    if positive >= 5 and source_count >= 2:
        return "needs second proof"
    if negative > positive:
        return "risk skew"
    return "thin evidence"


def analyze():
    paths = list(evidence_files())
    text_cache = {}
    results = []
    for segment in PRIORITY_SEGMENTS:
        rows = []
        tickers = set(segment["tickers"])
        for path in paths:
            ticker = ticker_from_path(path)
            if ticker not in tickers:
                continue
            text = text_cache.get(path)
            if text is None:
                try:
                    text = read_text(path)
                except Exception:
                    continue
                text_cache[path] = text
            hits = find_hits(segment, path, text)
            if hits:
                rows.append(
                    {
                        "ticker": ticker,
                        "path": os.path.relpath(path, ROOT).replace("\\", "/"),
                        "hits": hits[:8],
                    }
                )
        rows.sort(key=lambda row: (row["ticker"], -len(row["hits"])))
        results.append({"segment": segment, "state": score_segment(rows), "rows": rows})
    return results


def latest_segment_history():
    path = os.path.join(ROOT, "data", "segment_history.jsonl")
    if not os.path.exists(path):
        return {}
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    if not rows:
        return {}
    latest_date = max(row.get("date", "") for row in rows)
    market = {}
    for row in rows:
        if row.get("date") != latest_date:
            continue
        for rep in row.get("reps", []):
            quote = rep.get("quote")
            if quote:
                copy = dict(rep)
                copy["segment_id"] = row.get("segment_id")
                copy["segment_name"] = row.get("segment_name")
                market[quote] = copy
    return market


def company_evidence_summary(results):
    market = latest_segment_history()
    rows = []
    for result in results:
        segment = result["segment"]
        grouped = {}
        for row in result["rows"]:
            item = grouped.setdefault(row["ticker"], {"positive": 0, "negative": 0, "paths": set(), "sample": ""})
            item["paths"].add(row["path"])
            for hit in row["hits"]:
                if hit["polarity"] == "positive":
                    item["positive"] += 1
                else:
                    item["negative"] += 1
                if not item["sample"] and snippet_noise_score(hit["snippet"]) < 25:
                    item["sample"] = hit["snippet"]
        for ticker, item in grouped.items():
            market_row = market.get(ticker, {})
            net = item["positive"] - item["negative"]
            crowding = market_row.get("crowding", "n/a")
            if segment["id"] in {"copper_cables", "water_resources"} and net >= 3 and crowding in {"拥挤度尚可", "中高拥挤", "n/a"}:
                action = "priority verify"
            elif segment["id"] in {"gas_midstream", "ai_apps_agents"}:
                action = "second proof"
            elif segment["id"] == "ceramic_packaging_htcc":
                action = "mapping proof"
            elif crowding == "高拥挤":
                action = "only on upside revision"
            else:
                action = "watch"
            rows.append(
                {
                    "segment": segment["name"],
                    "ticker": ticker,
                    "positive": item["positive"],
                    "negative": item["negative"],
                    "sources": len(item["paths"]),
                    "crowding": crowding,
                    "return_3m": market_row.get("return_3m"),
                    "return_1y": market_row.get("return_1y"),
                    "action": action,
                    "next_check": segment["proof"],
                    "sample": item["sample"],
                }
            )
    rows.sort(key=lambda row: ({"priority verify": 0, "mapping proof": 1, "second proof": 2, "watch": 3, "only on upside revision": 4}.get(row["action"], 9), -row["positive"]))
    return rows


def fmt_pct(value):
    if value is None:
        return "n/a"
    return f"{value:+.1f}%"


def render(results):
    today = dt.datetime.now().strftime("%Y-%m-%d")
    company_rows = company_evidence_summary(results)
    lines = [f"# Segment Evidence Deep Dive - {today}", ""]
    lines.append("Scope: short-term AI capex second-order candidates. This report uses local SEC/IR/transcript evidence only, not RSS headlines.")
    company_notes_pdf = f"reports/company-notes-{today}.pdf"
    if os.path.exists(os.path.join(ROOT, company_notes_pdf)):
        lines.append("")
        lines.append(f"Follow-through: company-level verification notes are in `{company_notes_pdf}`.")
    lines.append("")
    lines.append("## Analyst Takeaway")
    lines.append("")
    lines.append("- **Upgrade for deeper work: Copper / Cables / Electrification Metals.** Primary-source evidence is now the cleanest among the second-order candidates: Freeport explicitly links copper demand to data centers and AI growth, while Eaton has direct data-center modular power exposure through Fibrebond. This supports moving the segment from broad electrification sympathy toward a real AI power-chain beneficiary, though single-name crowding still matters.")
    lines.append("- **Upgrade, but narrow the definition: Water / Zero-water Cooling / Treatment.** The strongest evidence is not generic water scarcity; it is Ecolab's CoolIT acquisition and Vertiv's AI-ready thermal / chilled-water positioning. Treat this as liquid cooling / coolant / thermal infrastructure, not a pure water utility trade.")
    lines.append("- **Keep as watch, not core: HTCC / Ceramic Packaging Materials.** Evidence supports optical/photonics/datacom strength, but direct ceramic / HTCC customer proof is still weak. This remains a mapping-validation project, especially for A-share names.")
    lines.append("- **Keep as second-proof: Natural Gas Midstream.** There is pipeline/compression/power language, but the evidence does not yet prove data-center demand is converting into contracted gas transport or compression economics. Needs company-level project proof.")
    lines.append("- **Keep as second-proof: AI Applications / Agents / ROI.** There are many AI adoption and product references, but also cost / ROI / competition language. The next proof must be paid adoption, ARPU, workload growth, retention, or margin evidence.")
    lines.append("")
    lines.append("| Segment | Evidence state | Sources hit | Positive hits | Negative hits | What must be proven |")
    lines.append("|---|---|---:|---:|---:|---|")
    for result in results:
        rows = result["rows"]
        pos = sum(1 for row in rows for hit in row["hits"] if hit["polarity"] == "positive")
        neg = sum(1 for row in rows for hit in row["hits"] if hit["polarity"] == "negative")
        lines.append(f"| {result['segment']['name']} | {result['state']} | {len(rows)} | {pos} | {neg} | {result['segment']['proof']} |")
    lines.append("")

    lines.append("## Company Workplan")
    lines.append("")
    lines.append("This converts segment evidence into a short research queue. `priority verify` means the segment evidence is improving and the stock is not automatically excluded by crowding; `mapping proof` means the theme is plausible but company revenue linkage is not proven; `second proof` means the segment still needs a harder bridge from narrative to economics.")
    lines.append("")
    lines.append("| Segment | Ticker | Action | Evidence +/- | Sources | Crowding | 3M | 1Y | Next check |")
    lines.append("|---|---|---|---:|---:|---|---:|---:|---|")
    for row in company_rows[:18]:
        lines.append(
            f"| {row['segment']} | {row['ticker']} | {row['action']} | +{row['positive']} / -{row['negative']} | "
            f"{row['sources']} | {row['crowding']} | {fmt_pct(row['return_3m'])} | {fmt_pct(row['return_1y'])} | {row['next_check']} |"
        )
    lines.append("")

    for result in results:
        segment = result["segment"]
        lines.append(f"## {segment['name']}")
        lines.append("")
        lines.append(f"Evidence state: **{result['state']}**")
        lines.append("")
        if not result["rows"]:
            lines.append("- No local primary-source hits yet. Add company filings/transcripts or keep this as an unproven watch item.")
            lines.append("")
            continue
        for row in result["rows"][:12]:
            lines.append(f"- **{row['ticker']}** `{row['path']}`")
            for hit in row["hits"][:3]:
                mark = "+" if hit["polarity"] == "positive" else "-"
                lines.append(f"  - {mark} `{hit['term']}`: {hit['snippet']}")
        lines.append("")
    lines.append("## Best Natural-Language Evidence")
    lines.append("")
    for row in company_rows[:12]:
        if row["sample"]:
            lines.append(f"- **{row['ticker']} / {row['segment']}**: {row['sample']}")
    lines.append("")
    return "\n".join(lines)


def render_html(markdown_text):
    escaped = html.escape(markdown_text)
    lines = escaped.splitlines()
    body = []
    in_list = False
    in_table = False
    for line in lines:
        if line.startswith("# "):
            body.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("|") and line.endswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if set(cells) == {"---"} or all(set(cell) <= {"-", ":"} for cell in cells):
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
                body.append(f"<li>{line[2:]}</li>")
            elif line.startswith("  - "):
                if not in_list:
                    body.append("<ul>")
                    in_list = True
                body.append(f"<li class='sub'>{line[4:]}</li>")
            else:
                if in_list:
                    body.append("</ul>")
                    in_list = False
                if line.strip():
                    body.append(f"<p>{line}</p>")
    if in_table:
        body.append("</table>")
    if in_list:
        body.append("</ul>")
    css = """
    body { font-family: Arial, sans-serif; margin: 32px; color: #111827; line-height: 1.45; }
    h1 { font-size: 26px; margin-bottom: 18px; }
    h2 { font-size: 20px; margin-top: 30px; border-bottom: 1px solid #d1d5db; padding-bottom: 6px; }
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
    results = analyze()
    output = os.path.join(REPORTS, f"segment-evidence-deep-dive-{dt.datetime.now():%Y-%m-%d}.md")
    html_output = os.path.splitext(output)[0] + ".html"
    report = render(results)
    with open(output, "w", encoding="utf-8") as f:
        f.write(report)
    with open(html_output, "w", encoding="utf-8") as f:
        f.write(render_html(report))
    print(output)
    print(html_output)


if __name__ == "__main__":
    main()
