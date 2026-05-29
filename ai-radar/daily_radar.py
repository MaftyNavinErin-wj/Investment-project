import argparse
import datetime as dt
import email.utils
import html
import math
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict


ROOT = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ROOT)
BLOOMBERG_SNAPSHOT_PATHS = [
    r"\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie\bloomberg_snapshot_latest.json",
    os.path.join(PROJECT_ROOT, "data", "bloomberg_snapshot_latest.json"),
    os.path.join(PROJECT_ROOT, "data", "bloomberg_snapshot.json"),
    os.path.join(os.path.expanduser("~"), "Desktop", "bloomberg_snapshot.json"),
]
BLOOMBERG_HISTORY_PATHS = [
    r"\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie\bloomberg_history_latest.json",
    os.path.join(PROJECT_ROOT, "data", "bloomberg_history_latest.json"),
    os.path.join(os.path.expanduser("~"), "Desktop", "bloomberg_history_latest.json"),
]
BLOOMBERG_NEWS_PATHS = [
    r"\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie\bloomberg_news_latest.json",
    os.path.join(PROJECT_ROOT, "data", "bloomberg_news_latest.json"),
    os.path.join(os.path.expanduser("~"), "Desktop", "bloomberg_news_latest.json"),
]
LOCAL_BLOOMBERG_CACHE = {
    "snapshot": os.path.join(PROJECT_ROOT, "data", "bloomberg_snapshot_latest.json"),
    "history": os.path.join(PROJECT_ROOT, "data", "bloomberg_history_latest.json"),
    "news": os.path.join(PROJECT_ROOT, "data", "bloomberg_news_latest.json"),
}
STOPWORDS = {
    "about", "above", "after", "again", "against", "ahead", "also", "amid", "among", "another", "around",
    "because", "before", "behind", "being", "between", "beyond", "could", "data", "does", "down", "during",
    "early", "from", "have", "into", "just", "large", "latest", "more", "most", "next", "over", "said",
    "says", "should", "stock", "stocks", "than", "that", "their", "there", "these", "this", "through",
    "under", "while", "with", "would", "year", "years", "your", "news", "market", "markets", "shares",
    "company", "companies", "inc", "corp", "group", "holdings", "technology", "technologies", "and",
    "the", "for", "are", "was", "will", "has", "had", "its", "our", "you", "can", "may", "center",
    "centers", "infrastructure", "business", "growth", "driver", "drivers", "largest", "world"
}


def utc_now():
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def strip_tags(value):
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def parse_date(value):
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo:
            parsed = parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
        return parsed
    except Exception:
        return None


def fetch_url(url, timeout=18):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 investment-radar/0.1",
            "Accept": "application/rss+xml, application/xml, text/xml, text/html;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_json(url, timeout=18):
    return json.loads(fetch_url(url, timeout=timeout).decode("utf-8", errors="replace"))


def fetch_bing_news(query, max_items):
    encoded = urllib.parse.urlencode({"q": query, "format": "rss"})
    url = f"https://www.bing.com/news/search?{encoded}"
    raw = fetch_url(url)
    root = ET.fromstring(raw)
    items = []
    for item in root.findall(".//item")[:max_items]:
        title = strip_tags(item.findtext("title"))
        link = strip_tags(item.findtext("link"))
        summary = strip_tags(item.findtext("description"))
        published = parse_date(item.findtext("pubDate"))
        items.append(
            {
                "query": query,
                "title": title,
                "link": link,
                "summary": summary,
                "published": published,
                "source": "Bing News",
            }
        )
    return items


def fetch_google_news(query, max_items):
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
    raw = fetch_url(url)
    root = ET.fromstring(raw)
    items = []
    for item in root.findall(".//item")[:max_items]:
        title = strip_tags(item.findtext("title"))
        link = strip_tags(item.findtext("link"))
        summary = strip_tags(item.findtext("description"))
        published = parse_date(item.findtext("pubDate"))
        items.append(
            {
                "query": query,
                "title": title,
                "link": link,
                "summary": summary,
                "published": published,
                "source": "Google News",
            }
        )
    return items


def read_manual_inbox(path):
    if not os.path.isdir(path):
        return []
    items = []
    for name in sorted(os.listdir(path)):
        if not name.lower().endswith((".txt", ".md")):
            continue
        full = os.path.join(path, name)
        with open(full, "r", encoding="utf-8", errors="replace") as f:
            body = f.read().strip()
        if not body:
            continue
        first_line = body.splitlines()[0][:120]
        items.append(
            {
                "query": "manual_inbox",
                "title": first_line or name,
                "link": full,
                "summary": strip_tags(body[:1200]),
                "published": utc_now(),
                "source": f"manual:{name}",
            }
        )
    return items


def normalize_text(item):
    return f"{item.get('title', '')} {item.get('summary', '')}".lower()


def score_item(item, theme):
    text = normalize_text(item)
    pos = [term for term in theme.get("positive_terms", []) if term.lower() in text]
    neg = [term for term in theme.get("negative_terms", []) if term.lower() in text]
    score = len(pos) - len(neg)
    return score, pos, neg


def crowded_hits(item, config):
    text = normalize_text(item)
    return [term for term in config.get("crowded_terms", []) if term.lower() in text]


def theme_keyword_hit(item, theme):
    text = normalize_text(item)
    return any(term.lower() in text for term in theme.get("keywords", []))


def item_key(item):
    link = item.get("link") or ""
    title = item.get("title") or ""
    return link or title.lower()


def within_lookback(item, lookback_days):
    published = item.get("published")
    if not published:
        return True
    threshold = utc_now() - dt.timedelta(days=lookback_days)
    return published >= threshold


def within_delta_window(item, since):
    if since is None:
        return True
    published = item.get("published")
    if not published:
        return True
    return published >= since


def collect_items(config):
    max_items = int(config.get("max_items_per_query", 10))
    all_items = []
    errors = []
    for theme in config["themes"]:
        for query in theme["queries"]:
            try:
                for item in fetch_bing_news(query, max_items):
                    item["theme_hint"] = theme["id"]
                    all_items.append(item)
            except Exception as exc:
                errors.append(f"{theme['name']} / {query}: {exc}")
            try:
                for item in fetch_google_news(query, max_items):
                    item["theme_hint"] = theme["id"]
                    all_items.append(item)
            except Exception as exc:
                errors.append(f"{theme['name']} / Google / {query}: {exc}")
    manual_dir = os.path.join(PROJECT_ROOT, config.get("manual_inbox_dir", "manual_inbox"))
    all_items.extend(read_manual_inbox(manual_dir))
    return all_items, errors


def collect_discovery_items(config, since=None):
    max_items = int(config.get("max_items_per_query", 10))
    all_items = []
    errors = []
    for query in config.get("discovery_queries", []):
        try:
            for item in fetch_bing_news(query, max_items):
                item["theme_hint"] = "discovery"
                all_items.append(item)
        except Exception as exc:
            errors.append(f"Discovery / {query}: {exc}")
        try:
            for item in fetch_google_news(query, max_items):
                item["theme_hint"] = "discovery"
                all_items.append(item)
        except Exception as exc:
            errors.append(f"Discovery / Google / {query}: {exc}")
    dedup = {}
    for item in all_items:
        if within_delta_window(item, since):
            dedup.setdefault(item_key(item), item)
    return list(dedup.values()), errors


def classify_items(config, raw_items, since=None):
    dedup = {}
    for item in raw_items:
        if not within_delta_window(item, since) and item.get("query") != "manual_inbox":
            continue
        dedup.setdefault(item_key(item), item)

    by_theme = defaultdict(list)
    for item in dedup.values():
        for theme in config["themes"]:
            score, pos, neg = score_item(item, theme)
            query_hit = item.get("theme_hint") == theme["id"]
            keyword_hit = theme_keyword_hit(item, theme)
            if query_hit or (keyword_hit and score != 0):
                enriched = dict(item)
                enriched["score"] = score
                enriched["positive_hits"] = pos
                enriched["negative_hits"] = neg
                enriched["crowded_hits"] = crowded_hits(item, config)
                by_theme[theme["id"]].append(enriched)

    for theme_id in by_theme:
        by_theme[theme_id].sort(key=lambda x: (x.get("score", 0), x.get("published") or dt.datetime.min), reverse=True)
    return by_theme


def theme_signal(items):
    total = sum(item.get("score", 0) for item in items)
    pos_hits = sum(len(item.get("positive_hits", [])) for item in items)
    neg_hits = sum(len(item.get("negative_hits", [])) for item in items)
    if total >= 3 or (pos_hits >= 4 and pos_hits >= neg_hits * 2):
        return "利好"
    if total <= -2 or (neg_hits >= 3 and neg_hits > pos_hits):
        return "利空"
    return "中性"


def signal_driver(items, direction):
    if direction not in ("利好", "利空"):
        return ""
    key = "positive_hits" if direction == "利好" else "negative_hits"
    counts = Counter()
    examples = []
    for item in items:
        for term in item.get(key, []):
            counts[term] += 1
        if len(examples) < 2:
            title = item.get("title")
            if title:
                examples.append(title)
    terms = ", ".join([term for term, _ in counts.most_common(3)])
    if terms:
        return terms
    return "; ".join(examples[:2])


def theme_maturity(items):
    crowded = sum(len(item.get("crowded_hits", [])) for item in items)
    evidence = len(items)
    pos_hits = sum(len(item.get("positive_hits", [])) for item in items)
    if crowded >= 3:
        return "已成共识/可能拥挤"
    if evidence >= 14 and pos_hits >= 5:
        return "正在快速扩散"
    if evidence >= 7 and pos_hits >= 3:
        return "正在扩散"
    if evidence >= 3:
        return "有早期线索"
    if evidence > 0:
        return "零星线索"
    return "无新线索"


def nearest_price(points, target_ts):
    before = [point for point in points if point[0] <= target_ts and point[1] is not None]
    if before:
        return before[-1][1]
    after = [point for point in points if point[0] > target_ts and point[1] is not None]
    if after:
        return after[0][1]
    return None


def pct_return(current, previous):
    if current is None or previous in (None, 0):
        return None
    return (current / previous - 1) * 100


def fetch_quote_history(symbol):
    encoded = urllib.parse.quote(symbol)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=1y&interval=1d&events=history"
    data = fetch_json(url)
    result = data.get("chart", {}).get("result", [])
    if not result:
        raise ValueError("no chart result")
    result = result[0]
    timestamps = result.get("timestamp", [])
    quote = result.get("indicators", {}).get("quote", [{}])[0]
    adj = result.get("indicators", {}).get("adjclose", [{}])[0]
    closes = adj.get("adjclose") or quote.get("close", [])
    points = [(ts, close) for ts, close in zip(timestamps, closes) if close is not None]
    if not points:
        raise ValueError("no close prices")
    current_ts, current = points[-1]
    now = dt.datetime.fromtimestamp(current_ts, tz=dt.timezone.utc)
    targets = {
        "1M": int((now - dt.timedelta(days=30)).timestamp()),
        "3M": int((now - dt.timedelta(days=91)).timestamp()),
        "6M": int((now - dt.timedelta(days=182)).timestamp()),
        "1Y": int((now - dt.timedelta(days=365)).timestamp()),
    }
    returns = {label: pct_return(current, nearest_price(points, ts)) for label, ts in targets.items()}
    if len(points) >= 6:
        returns["5D"] = pct_return(current, points[-6][1])
    ma20 = sum(point[1] for point in points[-20:]) / 20 if len(points) >= 20 else None
    ma60 = sum(point[1] for point in points[-60:]) / 60 if len(points) >= 60 else None
    return {
        "symbol": symbol,
        "date": now.strftime("%Y-%m-%d"),
        "price": current,
        "returns": returns,
        "ma20": ma20,
        "ma60": ma60,
        "dist_ma20": pct_return(current, ma20),
        "dist_ma60": pct_return(current, ma60),
    }


def fetch_quote_summary(symbol):
    encoded = urllib.parse.quote(symbol)
    modules = ",".join([
        "summaryDetail",
        "defaultKeyStatistics",
        "financialData",
        "price",
    ])
    url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{encoded}?modules={modules}"
    data = fetch_json(url)
    result = data.get("quoteSummary", {}).get("result", [])
    if not result:
        raise ValueError("no quote summary result")
    summary = result[0]

    def raw(*path):
        node = summary
        for key in path:
            node = (node or {}).get(key)
        if isinstance(node, dict) and "raw" in node:
            return node.get("raw")
        return node

    return {
        "market_cap": raw("price", "marketCap"),
        "trailing_pe": raw("summaryDetail", "trailingPE"),
        "forward_pe": raw("summaryDetail", "forwardPE") or raw("defaultKeyStatistics", "forwardPE"),
        "ev_to_ebitda": raw("defaultKeyStatistics", "enterpriseToEbitda"),
        "ev_to_revenue": raw("defaultKeyStatistics", "enterpriseToRevenue"),
        "peg_ratio": raw("defaultKeyStatistics", "pegRatio"),
        "revenue_growth": raw("financialData", "revenueGrowth"),
        "earnings_growth": raw("financialData", "earningsGrowth"),
        "ebitda_margins": raw("financialData", "ebitdaMargins"),
        "gross_margins": raw("financialData", "grossMargins"),
    }


def parse_metric_value(html_text, metric_id):
    pattern = rf'id:"{re.escape(metric_id)}",title:"[^"]+",value:"([^"]+)"'
    match = re.search(pattern, html_text)
    if not match:
        return None
    value = match.group(1).replace(",", "").replace("$", "")
    if value.endswith("%"):
        value = value[:-1]
    if value.lower() == "n/a":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fetch_stockanalysis_valuation(symbol):
    if "." in symbol:
        raise ValueError("StockAnalysis fallback only supports US tickers")
    url = f"https://stockanalysis.com/stocks/{symbol.lower()}/statistics/"
    html_text = fetch_url(url, timeout=18).decode("utf-8", errors="replace")
    return {
        "trailing_pe": parse_metric_value(html_text, "pe"),
        "forward_pe": parse_metric_value(html_text, "peForward"),
        "ev_to_ebitda": parse_metric_value(html_text, "evEbitda"),
        "ev_to_revenue": parse_metric_value(html_text, "evSales"),
        "peg_ratio": parse_metric_value(html_text, "pegRatio"),
    }


def parse_float(value):
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def bloomberg_security_key(security):
    parts = (security or "").split()
    if len(parts) >= 3 and parts[-2].upper() == "US" and parts[-1].upper() == "EQUITY":
        return parts[0].upper()
    return (security or "").upper()


def load_bloomberg_snapshot():
    for path in BLOOMBERG_SNAPSHOT_PATHS:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            snapshot = json.load(f)
        cache_bloomberg_file(path, LOCAL_BLOOMBERG_CACHE["snapshot"])
        rows = {}
        for item in snapshot.get("rows", []):
            key = (item.get("quote") or bloomberg_security_key(item.get("security"))).upper()
            fields = item.get("fields", {})
            rows[key] = {
                "symbol": key,
                "date": (snapshot.get("created_at") or "")[:10],
                "price": parse_float(fields.get("PX_LAST")),
                "market_cap": parse_float(fields.get("CUR_MKT_CAP")),
                "trailing_pe": parse_float(fields.get("PE_RATIO")),
                "forward_pe": parse_float(fields.get("BEST_PE_RATIO")),
                "pe_2027e": parse_float(fields.get("PE_27E_BEST_PE_RATIO")),
                "pe_2028e": parse_float(fields.get("PE_28E_BEST_PE_RATIO")),
                "ev_to_ebitda": parse_float(fields.get("CURRENT_EV_TO_T12M_EBITDA")) or parse_float(fields.get("EV_TO_T12M_EBITDA")),
                "ev_to_ebitda_periodic": parse_float(fields.get("EV_TO_T12M_EBITDA")),
                "forward_ev_to_ebitda": parse_float(fields.get("BEST_CUR_EV_TO_EBITDA")),
                "ev_to_revenue": parse_float(fields.get("EV_TO_T12M_SALES")),
                "price_to_book": parse_float(fields.get("PX_TO_BOOK_RATIO")),
                "enterprise_value": parse_float(fields.get("CURR_ENTP_VAL")),
                "ttm_eps": parse_float(fields.get("TRAIL_12M_EPS")),
                "returns": {
                    "1M": parse_float(fields.get("CHG_PCT_1M")),
                    "3M": parse_float(fields.get("CHG_PCT_3M")),
                    "6M": parse_float(fields.get("CHG_PCT_6M")),
                    "1Y": parse_float(fields.get("CHG_PCT_1YR")),
                },
                "market_source": snapshot.get("source", "Bloomberg Desktop API"),
                "bloomberg_security": item.get("security"),
                "bloomberg_field_errors": item.get("field_errors", []),
            }
        return rows, path
    return {}, None


def cache_bloomberg_file(source, target):
    if not source or not target:
        return
    try:
        source_abs = os.path.abspath(source)
        target_abs = os.path.abspath(target)
        if source_abs == target_abs:
            return
        os.makedirs(os.path.dirname(target_abs), exist_ok=True)
        shutil.copy2(source_abs, target_abs)
    except Exception:
        pass


MACRO_TICKERS = {
    "SPX": {"name": "S&P 500", "bucket": "Risk appetite"},
    "NDX": {"name": "Nasdaq 100", "bucket": "AI equity beta"},
    "SOX": {"name": "Philadelphia Semiconductor Index", "bucket": "AI hardware crowding"},
    "VIX": {"name": "VIX", "bucket": "Volatility"},
    "USGG10YR": {"name": "US 10Y Treasury Yield", "bucket": "Discount rate"},
    "USGG2YR": {"name": "US 2Y Treasury Yield", "bucket": "Policy-rate expectations"},
    "USGG5YR": {"name": "US 5Y Treasury Yield", "bucket": "Project finance tenor"},
    "USGG30YR": {"name": "US 30Y Treasury Yield", "bucket": "Long-duration discount rate"},
    "LUACOAS": {"name": "US Corporate IG OAS", "bucket": "IG credit spread"},
    "LF98OAS": {"name": "US High Yield OAS", "bucket": "HY credit spread"},
    "DXY": {"name": "Dollar Index", "bucket": "USD/liquidity"},
    "HG1": {"name": "Copper Future", "bucket": "Power/grid input cost"},
    "NG1": {"name": "Natural Gas Future", "bucket": "Power input cost"},
    "CL1": {"name": "WTI Crude Future", "bucket": "Energy input cost"},
}

MACRO_RISK_REFERENCES = [
    {
        "topic": "融资结构",
        "point": "AI data center buildout 正从纯 equity story 变成 debt/private credit/project finance story；资本结构复杂化会放大再融资和回报率压力。",
        "source": "S&P Global",
        "url": "https://www.spglobal.com/en/research-insights/podcasts/look-forward/credit-risks-current-ai-data-center-infrastructure",
    },
    {
        "topic": "资产重化",
        "point": "GenAI 公司和 AI infra 平台越来越像资本密集型基础设施，capex、energy、data center capacity 与收入兑现之间的时间差变长。",
        "source": "S&P Global Market Intelligence",
        "url": "https://www.spglobal.com/market-intelligence/en/news-insights/research/2026/02/generative-ai-funding-a-sober-retrospective-and-the-trends-shaping-2026",
    },
    {
        "topic": "电力约束",
        "point": "Hyperscaler 正在提前锁 power；可用电力、输电建设和选址约束会影响建设速度，而不是简单影响最终需求。",
        "source": "S&P Global",
        "url": "https://www.spglobal.com/energy/en/news-research/special-reports/energy-transition/2026-trends-in-data-center-services-infrastructure",
    },
    {
        "topic": "债务融资案例",
        "point": "大型数据中心 capex 已经伴随大额债务融资案例，说明未来需要同时跟踪订单、融资成本和项目回报。",
        "source": "Data Center Dynamics",
        "url": "https://www.datacenterdynamics.com/en/news/google-secures-nearly-32bn-in-debt-following-major-data-center-capex-commitment/",
    },
]


def load_bloomberg_macro_rows():
    rows, path = load_bloomberg_snapshot()
    macro_rows = []
    for quote, meta in MACRO_TICKERS.items():
        row = rows.get(quote)
        if not row:
            continue
        returns = row.get("returns", {})
        macro_rows.append(
            {
                "quote": quote,
                "name": meta["name"],
                "bucket": meta["bucket"],
                "price": row.get("price"),
                "date": row.get("date"),
                "returns": returns,
                "source_path": path,
            }
        )
    return macro_rows


def approx_yield_change_bps(current, pct_change):
    if current is None or pct_change is None:
        return None
    prev = current / (1 + pct_change / 100) if pct_change != -100 else None
    if prev is None:
        return None
    return (current - prev) * 100


def fmt_bps(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{value:+.0f}bp"


def macro_market_dashboard():
    rows = load_bloomberg_macro_rows()
    by_quote = {row["quote"]: row for row in rows}
    us10 = by_quote.get("USGG10YR", {})
    us2 = by_quote.get("USGG2YR", {})
    us5 = by_quote.get("USGG5YR", {})
    us30 = by_quote.get("USGG30YR", {})
    ig_oas = by_quote.get("LUACOAS", {})
    hy_oas = by_quote.get("LF98OAS", {})
    sox = by_quote.get("SOX", {})
    ndx = by_quote.get("NDX", {})
    vix = by_quote.get("VIX", {})
    hg = by_quote.get("HG1", {})
    ng = by_quote.get("NG1", {})

    us10_3m_bps = approx_yield_change_bps(us10.get("price"), (us10.get("returns") or {}).get("3M"))
    us2_3m_bps = approx_yield_change_bps(us2.get("price"), (us2.get("returns") or {}).get("3M"))
    us5_3m_bps = approx_yield_change_bps(us5.get("price"), (us5.get("returns") or {}).get("3M"))
    us30_3m_bps = approx_yield_change_bps(us30.get("price"), (us30.get("returns") or {}).get("3M"))
    ig_oas_1m_bps = approx_yield_change_bps(ig_oas.get("price"), (ig_oas.get("returns") or {}).get("1M"))
    hy_oas_1m_bps = approx_yield_change_bps(hy_oas.get("price"), (hy_oas.get("returns") or {}).get("1M"))
    sox_3m = (sox.get("returns") or {}).get("3M")
    ndx_3m = (ndx.get("returns") or {}).get("3M")
    vix_1m = (vix.get("returns") or {}).get("1M")
    copper_1m = (hg.get("returns") or {}).get("1M")
    gas_1m = (ng.get("returns") or {}).get("1M")

    risk_notes = []
    if us10_3m_bps is not None and us10_3m_bps > 35:
        risk_notes.append("10Y 上行超过 35bp，长久期 AI 硬件估值折现率压力上升")
    if us2_3m_bps is not None and us2_3m_bps > 35:
        risk_notes.append("2Y 上行，降息预期/短端资金成本对融资型项目不友好")
    if us5_3m_bps is not None and us5_3m_bps > 35:
        risk_notes.append("5Y 上行，项目融资和中期债务成本压力上升")
    if us30_3m_bps is not None and us30_3m_bps > 35:
        risk_notes.append("30Y 上行，长久期基础设施资产折现率压力上升")
    if ig_oas_1m_bps is not None and ig_oas_1m_bps > 10:
        risk_notes.append("IG OAS 走阔，投资级融资环境边际变差")
    if hy_oas_1m_bps is not None and hy_oas_1m_bps > 30:
        risk_notes.append("HY OAS 走阔，信用风险偏好对高杠杆 AI infra 更不友好")
    if sox_3m is not None and sox_3m > 40:
        risk_notes.append("SOX 3M 涨幅过大，半导体 beta 和拥挤度已经很高")
    if vix_1m is not None and vix_1m < -10:
        risk_notes.append("VIX 下行说明风险偏好尚可，短期不是流动性压力主导")
    if copper_1m is not None and copper_1m > 8:
        risk_notes.append("铜价上行，电网/电气化/数据中心建设成本压力抬升")
    if gas_1m is not None and gas_1m > 15:
        risk_notes.append("天然气上行，on-site power 和电力输入成本需要跟踪")

    credit_worse = any(value is not None and value > threshold for value, threshold in [(ig_oas_1m_bps, 10), (hy_oas_1m_bps, 30)])
    if us10_3m_bps and us10_3m_bps > 35 and sox_3m and sox_3m > 40:
        verdict = "中性偏利空"
        message = "基本面需求仍强，但 discount-rate + crowding 的组合变差；这会先压高估值和远期故事，而不是立刻否定订单。"
    elif credit_worse:
        verdict = "中性偏利空"
        message = "信用利差走阔会提高 AI infra 融资成本，尤其影响高杠杆或项目融资依赖更强的链条。"
    elif sox_3m and sox_3m > 40:
        verdict = "中性"
        message = "AI beta 很强，短期动量仍在，但拥挤度已经限制 risk/reward。"
    else:
        verdict = "中性"
        message = "宏观行情没有给出足够强的新增方向，维持跟踪。"

    return {
        "rows": rows,
        "verdict": verdict,
        "message": message,
        "risk_notes": risk_notes,
        "us10_3m_bps": us10_3m_bps,
        "us2_3m_bps": us2_3m_bps,
        "us5_3m_bps": us5_3m_bps,
        "us30_3m_bps": us30_3m_bps,
        "ig_oas_1m_bps": ig_oas_1m_bps,
        "hy_oas_1m_bps": hy_oas_1m_bps,
    }


def compute_history_metrics(points):
    series = []
    for point in points or []:
        value = parse_float(point.get("PX_LAST"))
        if value is not None:
            series.append((point.get("date"), value))
    if len(series) < 2:
        return {}
    current = series[-1][1]

    def trailing_return(days):
        if len(series) <= days:
            base = series[0][1]
        else:
            base = series[-days - 1][1]
        if not base:
            return None
        return (current / base - 1) * 100

    daily_returns = []
    for (_, prev), (_, value) in zip(series, series[1:]):
        if prev:
            daily_returns.append(value / prev - 1)
    trailing_30 = daily_returns[-30:]
    volatility_30d = None
    if len(trailing_30) >= 2:
        mean = sum(trailing_30) / len(trailing_30)
        variance = sum((value - mean) ** 2 for value in trailing_30) / (len(trailing_30) - 1)
        volatility_30d = math.sqrt(variance) * math.sqrt(252) * 100

    peak = series[0][1]
    max_drawdown = 0
    for _, value in series:
        peak = max(peak, value)
        if peak:
            max_drawdown = min(max_drawdown, value / peak - 1)

    return {
        "date": series[-1][0],
        "price": current,
        "returns": {
            "5D": trailing_return(5),
            "1M": trailing_return(21),
            "3M": trailing_return(63),
            "6M": trailing_return(126),
            "1Y": trailing_return(252),
        },
        "ma20": sum(value for _, value in series[-20:]) / 20 if len(series) >= 20 else None,
        "ma60": sum(value for _, value in series[-60:]) / 60 if len(series) >= 60 else None,
        "dist_ma20": pct_return(current, sum(value for _, value in series[-20:]) / 20) if len(series) >= 20 else None,
        "dist_ma60": pct_return(current, sum(value for _, value in series[-60:]) / 60) if len(series) >= 60 else None,
        "volatility_30d": volatility_30d,
        "max_drawdown_1y": max_drawdown * 100,
    }


def load_bloomberg_history():
    for path in BLOOMBERG_HISTORY_PATHS:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            history = json.load(f)
        cache_bloomberg_file(path, LOCAL_BLOOMBERG_CACHE["history"])
        rows = {}
        for item in history.get("rows", []):
            key = (item.get("quote") or bloomberg_security_key(item.get("security"))).upper()
            metrics = compute_history_metrics(item.get("field_data"))
            if metrics:
                metrics["history_source_path"] = path
                rows[key] = metrics
        return rows, path
    return {}, None


def collect_market_data(config):
    rows = []
    errors = []
    seen = set()
    universe = []
    bloomberg_rows, bloomberg_path = load_bloomberg_snapshot()
    bloomberg_history, _ = load_bloomberg_history()
    universe.extend(config.get("holdings", []))
    universe.extend(config.get("watchlist", []))
    for segment in config.get("segments", []):
        for rep in segment.get("reps", []):
            enriched = dict(rep)
            enriched["themes"] = segment.get("themes", [])
            universe.append(enriched)
    for item in universe:
        symbol = item.get("quote") or item.get("ticker")
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        row = {"name": item.get("name", symbol), "quote": symbol, "themes": item.get("themes", [])}
        bloomberg_row = bloomberg_rows.get(symbol.upper())
        if bloomberg_row:
            row.update(bloomberg_row)
            if symbol.upper() in bloomberg_history:
                history_metrics = bloomberg_history[symbol.upper()]
                row.update(history_metrics)
            row["market_source_path"] = bloomberg_path
            rows.append(row)
            continue
        if symbol.upper() in bloomberg_history:
            row.update(bloomberg_history[symbol.upper()])
            row["market_source"] = "Bloomberg Desktop API historical"
            rows.append(row)
            continue
        try:
            row.update(fetch_quote_history(symbol))
            try:
                row.update(fetch_quote_summary(symbol))
            except Exception as exc:
                try:
                    row.update(fetch_stockanalysis_valuation(symbol))
                    row["valuation_source"] = "StockAnalysis"
                except Exception as fallback_exc:
                    row["valuation_error"] = f"{exc}; fallback={fallback_exc}"
        except Exception as exc:
            row["error"] = str(exc)
            errors.append(f"{item.get('name', symbol)} / {symbol}: {exc}")
        rows.append(row)
    return rows, errors


def crowded_by_return(row):
    returns = row.get("returns") or {}
    one_m = returns.get("1M")
    three_m = returns.get("3M")
    six_m = returns.get("6M")
    one_y = returns.get("1Y")
    if any(value is not None and value >= threshold for value, threshold in [(one_m, 40), (three_m, 80), (six_m, 120), (one_y, 180)]):
        return "极拥挤"
    if any(value is not None and value >= threshold for value, threshold in [(one_m, 20), (three_m, 40), (six_m, 70), (one_y, 100)]):
        return "偏拥挤"
    if any(value is not None and value <= -20 for value in [one_m, three_m]):
        return "降温/回撤"
    if any(value is not None for value in [one_m, three_m, six_m, one_y]):
        return "不算拥挤"
    return "无行情"


def crowded_by_valuation(row):
    forward_pe = row.get("forward_pe")
    trailing_pe = row.get("trailing_pe")
    ev_ebitda = row.get("ev_to_ebitda")
    ev_revenue = row.get("ev_to_revenue")
    if all(value is None for value in [forward_pe, trailing_pe, ev_ebitda, ev_revenue]):
        return "估值缺口"
    if any(value is not None and value >= threshold for value, threshold in [(forward_pe, 60), (trailing_pe, 80), (ev_ebitda, 40), (ev_revenue, 15)]):
        return "估值很贵"
    if any(value is not None and value >= threshold for value, threshold in [(forward_pe, 35), (trailing_pe, 50), (ev_ebitda, 25), (ev_revenue, 8)]):
        return "估值偏贵"
    if any(value is not None and value <= threshold for value, threshold in [(forward_pe, 18), (trailing_pe, 22), (ev_ebitda, 12), (ev_revenue, 4)]):
        return "估值尚可"
    return "估值中性"


def combined_crowding(row):
    ret = crowded_by_return(row)
    val = crowded_by_valuation(row)
    if "极拥挤" in ret or val == "估值很贵":
        return "高拥挤"
    if "偏拥挤" in ret or val == "估值偏贵":
        return "中高拥挤"
    if ret in ("不算拥挤", "降温/回撤") and val in ("估值尚可", "估值中性", "估值缺口"):
        return "拥挤度尚可"
    return "待确认"


def trading_crowding_risk(row):
    returns = row.get("returns") or {}
    score = 0
    notes = []

    def add(condition, points, note):
        nonlocal score
        if condition:
            score += points
            notes.append(note)

    add((returns.get("5D") or 0) >= 15, 1, "5D上涨过快")
    add((returns.get("1M") or 0) >= 30, 2, "1M涨幅过大")
    add(20 <= (returns.get("1M") or 0) < 30, 1, "1M涨幅偏快")
    add((returns.get("3M") or 0) >= 80, 2, "3M极拥挤")
    add(50 <= (returns.get("3M") or 0) < 80, 1, "3M偏拥挤")
    add((returns.get("1Y") or 0) >= 300, 2, "1Y涨幅过大")
    add(150 <= (returns.get("1Y") or 0) < 300, 1, "1Y涨幅偏大")

    dist_ma20 = row.get("dist_ma20")
    dist_ma60 = row.get("dist_ma60")
    add(dist_ma20 is not None and dist_ma20 >= 20, 2, "偏离20日线过大")
    add(dist_ma20 is not None and 10 <= dist_ma20 < 20, 1, "偏离20日线偏高")
    add(dist_ma60 is not None and dist_ma60 >= 35, 1, "偏离60日线偏高")

    high_pe = any(
        value is not None and value >= threshold
        for value, threshold in [
            (row.get("pe_2027e"), 50),
            (row.get("pe_2028e"), 35),
            (row.get("forward_pe"), 45),
            (row.get("trailing_pe"), 60),
        ]
    )
    very_high_pe = any(
        value is not None and value >= threshold
        for value, threshold in [
            (row.get("pe_2027e"), 80),
            (row.get("pe_2028e"), 60),
            (row.get("forward_pe"), 70),
            (row.get("trailing_pe"), 90),
        ]
    )
    add(very_high_pe, 2, "估值很贵")
    add(high_pe and not very_high_pe, 1, "估值偏贵")
    add((row.get("volatility_30d") or 0) >= 70, 1, "波动率高")

    if score >= 7:
        level = "高"
    elif score >= 4:
        level = "中高"
    elif score >= 2:
        level = "中"
    else:
        level = "低"
    return {"score": score, "level": level, "notes": notes[:3]}


def level_score(level):
    return {"低": 0, "中": 1, "中高": 2, "高": 3}.get(level, 1)


def fundamental_support(row, by_theme):
    score = 0
    notes = []

    def add(condition, points, note):
        nonlocal score
        if condition:
            score += points
            notes.append(note)

    theme_ids = row.get("themes") or []
    for theme_id in theme_ids:
        signal = theme_signal(by_theme.get(theme_id, []))
        add(signal == "利好", 2, f"{theme_id}边际利好")
        add(signal == "中性" and by_theme.get(theme_id), 1, f"{theme_id}有信息流")

    add(row.get("pe_2028e") is not None and row.get("pe_2028e") <= 25, 1, "28E估值可解释")
    add(row.get("pe_2027e") is not None and row.get("pe_2027e") <= 35, 1, "27E估值可解释")
    add(row.get("forward_pe") is not None and row.get("forward_pe") <= 35, 1, "远期估值可解释")
    add((row.get("earnings_growth") or 0) >= 0.25, 1, "盈利增长较快")
    add((row.get("revenue_growth") or 0) >= 0.25, 1, "收入增长较快")

    if score >= 5:
        level = "强"
    elif score >= 3:
        level = "中强"
    elif score >= 1:
        level = "中"
    else:
        level = "弱/待验证"
    return {"score": score, "level": level, "notes": notes[:3]}


def combined_pullback_risk(trading, support):
    raw = level_score(trading["level"])
    support_offset = {"强": 2, "中强": 1, "中": 0, "弱/待验证": -1}.get(support["level"], 0)
    adjusted = raw - support_offset
    if adjusted >= 3:
        level = "高"
        action = "交易和预期都偏脆弱；先控制仓位。"
    elif adjusted == 2:
        level = "中高"
        action = "回调风险明显；需要EPS/订单继续上修来消化。"
    elif adjusted == 1:
        level = "中"
        action = "有拥挤压力，但基本面仍可承接，回调更像换手。"
    else:
        level = "中低"
        action = "交易拥挤可见，但基本面支撑较强，不宜只因涨幅大判断结束。"
    return {"level": level, "action": action}


def pullback_risk_dashboard(config, market_rows, by_theme):
    focus_quotes = {item.get("quote") or item.get("ticker") for item in config.get("holdings", [])}
    for item in config.get("pullback_watchlist", []):
        focus_quotes.add(item.get("quote") or item.get("ticker"))
    rows = []
    for row in market_rows:
        if row.get("quote") not in focus_quotes:
            continue
        trading = trading_crowding_risk(row)
        support = fundamental_support(row, by_theme)
        risk = combined_pullback_risk(trading, support)
        rows.append({"row": row, "risk": risk, "trading": trading, "support": support})
    rows.sort(key=lambda item: (level_score(item["risk"]["level"]), (item["row"].get("returns") or {}).get("3M") or -999), reverse=True)
    return rows


def tokenize(text):
    words = re.findall(r"[A-Za-z][A-Za-z0-9+\-/]{2,}", text.lower())
    return [word.strip("-/") for word in words if word not in STOPWORDS and len(word) > 2]


def phrase_counts(items):
    counts = Counter()
    examples = defaultdict(list)
    for item in items:
        text = normalize_text(item)
        words = tokenize(text)
        for n in (1, 2, 3):
            for idx in range(0, max(0, len(words) - n + 1)):
                phrase = " ".join(words[idx:idx + n])
                if len(phrase) < 4:
                    continue
                counts[phrase] += 1
                if len(examples[phrase]) < 3:
                    examples[phrase].append(item)
    return counts, examples


def history_path(config):
    data_dir = os.path.join(PROJECT_ROOT, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "discovery_history.jsonl")


def load_discovery_history(config):
    path = history_path(config)
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def save_discovery_snapshot(config, counts):
    path = history_path(config)
    today = dt.datetime.now().strftime("%Y-%m-%d")
    history = load_discovery_history(config)
    if any(row.get("date") == today for row in history):
        return
    top_counts = dict(counts.most_common(120))
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"date": today, "counts": top_counts}, ensure_ascii=False) + "\n")


def prior_average(history, phrase):
    values = [row.get("counts", {}).get(phrase, 0) for row in history[-30:]]
    if not values:
        return 0
    return sum(values) / len(values)


def topic_discovery_scores(config, discovery_items, market_summary):
    text_by_topic = {}
    rows = []
    all_text = [normalize_text(item) for item in discovery_items]
    for topic in config.get("discovery_topics", []):
        hits = []
        for item in discovery_items:
            text = normalize_text(item)
            matched = [kw for kw in topic.get("keywords", []) if kw.lower() in text]
            if matched:
                copy = dict(item)
                copy["matched_keywords"] = matched
                hits.append(copy)
        crowded = sum(len(crowded_hits(item, config)) for item in hits)
        rows.append(
            {
                "name": topic["name"],
                "why": topic.get("why", ""),
                "hits": hits,
                "keywords": sorted({kw for item in hits for kw in item.get("matched_keywords", [])}),
                "crowded_terms": crowded,
            }
        )
        text_by_topic[topic["name"]] = all_text
    return rows


def build_discovery(config, discovery_items, market_summary):
    counts, examples = phrase_counts(discovery_items)
    history = load_discovery_history(config)
    candidates = []
    for phrase, count in counts.most_common(80):
        if count < 2:
            continue
        if any(token in STOPWORDS for token in phrase.split()):
            continue
        avg = prior_average(history, phrase)
        novelty = count if avg == 0 else count / max(avg, 0.5)
        if count >= 3 or novelty >= 2.5:
            candidates.append({"phrase": phrase, "count": count, "prior_avg": avg, "novelty": novelty, "examples": examples[phrase]})
    save_discovery_snapshot(config, counts)
    topics = topic_discovery_scores(config, discovery_items, market_summary)
    return candidates[:20], topics


def fmt_pct(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{value:+.1f}%"


def fmt_num(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{value:.1f}"


def theme_market_summary(config, market_rows):
    summary = {}
    for theme in config.get("themes", []):
        rows = [row for row in market_rows if theme["id"] in row.get("themes", []) and row.get("returns")]
        if not rows:
            summary[theme["id"]] = {"state": "无代表行情", "rows": []}
            continue
        crowded = [row for row in rows if combined_crowding(row) in ("中高拥挤", "高拥挤")]
        extreme = [row for row in rows if combined_crowding(row) == "高拥挤"]
        if len(extreme) >= max(1, len(rows) // 3):
            state = "代表票高拥挤"
        elif len(crowded) >= max(1, len(rows) // 2):
            state = "代表票中高拥挤"
        else:
            state = "代表票未明显拥挤"
        summary[theme["id"]] = {"state": state, "rows": rows}
    return summary


def strength_score(value):
    return {"high": 3, "medium": 2, "low": 1}.get(value, 0)


def crowding_score(value):
    return {"拥挤度尚可": 3, "待确认": 2, "中高拥挤": 1, "高拥挤": 0}.get(value, 1)


def segment_representatives(segment, market_rows):
    quotes = {rep.get("quote") for rep in segment.get("reps", [])}
    return [row for row in market_rows if row.get("quote") in quotes]


def segment_crowding(rep_rows):
    if not rep_rows:
        return "无行情"
    states = [combined_crowding(row) for row in rep_rows if row.get("returns")]
    if not states:
        return "无行情"
    high = sum(1 for state in states if state == "高拥挤")
    mid = sum(1 for state in states if state == "中高拥挤")
    ok = sum(1 for state in states if state == "拥挤度尚可")
    if high >= max(1, len(states) // 3):
        return "高拥挤"
    if high + mid >= max(1, len(states) // 2):
        return "中高拥挤"
    if ok >= max(1, len(states) // 2):
        return "拥挤度尚可"
    return "待确认"


def segment_delta(segment, by_theme, discovery_topics):
    signals = []
    for theme_id in segment.get("themes", []):
        items = by_theme.get(theme_id, [])
        direction = theme_signal(items)
        if direction in ("利好", "利空"):
            driver = signal_driver(items, direction)
            signals.append(f"{direction}: {driver}" if driver else direction)
    matched_topics = []
    segment_text = f"{segment.get('name', '')} {segment.get('logic', '')}".lower()
    for topic in discovery_topics:
        topic_text = f"{topic.get('name', '')} {' '.join(topic.get('keywords', []))}".lower()
        if topic.get("hits") and any(word in topic_text for word in segment_text.split()[:6]):
            matched_topics.append(topic["name"])
    if signals:
        return "; ".join(signals[:3])
    return "中性"


def segment_discovery_note(segment, discovery_topics):
    matched_topics = []
    segment_tokens = set(tokenize(f"{segment.get('name', '')} {segment.get('logic', '')}"))
    generic = {"ai", "data", "center", "demand", "drive", "drives", "server", "servers", "infrastructure"}
    segment_tokens = {token for token in segment_tokens if token not in generic}
    for topic in discovery_topics:
        topic_tokens = set(tokenize(f"{topic.get('name', '')} {' '.join(topic.get('keywords', []))}"))
        topic_tokens = {token for token in topic_tokens if token not in generic}
        if topic.get("hits") and len(segment_tokens & topic_tokens) >= 1:
            matched_topics.append(topic["name"])
    if not matched_topics:
        return "无"
    return ", ".join(matched_topics[:2])


def segment_score(segment, crowding):
    return (
        strength_score(segment.get("logic_strength")) * 3
        + strength_score(segment.get("mapping_strength")) * 3
        + crowding_score(crowding) * 3
    )


def segment_temperature(row):
    crowding = row["crowding"]
    delta = row["delta"]
    if crowding == "高拥挤":
        return "Hot Consensus"
    if crowding == "中高拥挤":
        return "Hot/Warming"
    if crowding in ("拥挤度尚可", "待确认") and ("利好" in delta or "利空" in delta):
        if row["segment"].get("mapping_strength") == "low":
            return "Early Signal"
        return "Warming"
    if crowding in ("拥挤度尚可", "待确认"):
        return "Early Signal"
    return "Unclassified"


def infer_investment_layer(theme_id, signal, maturity, market_state):
    if market_state in ("代表票高拥挤", "代表票中高拥挤") or maturity == "已成共识/可能拥挤":
        return "A_known_bottleneck"
    if theme_id in ("networking_optics", "power_cooling", "memory", "emerging_second_order"):
        return "B_bottleneck_migration"
    if theme_id in ("ai_app_roi",):
        return "C_architecture_reshaping"
    if signal == "上修/变紧" and market_state == "代表票未明显拥挤":
        return "B_bottleneck_migration"
    return "A_known_bottleneck"


def layer_by_id(config):
    return {item["id"]: item for item in config.get("investment_layers", [])}


def actionability(signal):
    if signal == "上修/变紧":
        return "强化相关持仓逻辑；若股价未同步反映，提升关注；若已大涨，等待盈利预测或订单二次验证。"
    if signal == "下修/转弱":
        return "触发复盘；检查订单、价格、毛利和 capex 指引是否进入连续走弱。"
    if signal == "有信息流，但方向待确认":
        return "保留观察；需要找公司电话会、价格、交期或订单作为第二证据。"
    return "不做动作；等待更高质量信息。"


def plain_take(signal, maturity, market_state=None):
    if market_state in ("代表票高拥挤", "代表票中高拥挤"):
        return "产业逻辑可能仍强，但代表股票已经涨过一段，重点是找未定价的细分环节，而不是追主线标签。"
    if maturity == "已成共识/可能拥挤":
        return "这条线市场大概率已经知道了，重点不是追不追，而是看盈利上修还能不能继续盖过估值拥挤。"
    if signal == "上修/变紧" and maturity in ("正在扩散", "正在快速扩散"):
        return "这条线正在从产业信号扩散到市场共识，适合做深挖和找更低拥挤度的二阶标的。"
    if "早期" in maturity or maturity == "零星线索":
        return "这还不是结论，但值得放进前置观察池，下一步要找价格、交期、订单或公司电话会验证。"
    if signal == "下修/转弱":
        return "这条线要小心，可能出现预期降温，先找是不是连续坏消息。"
    return "信息还不够硬，暂时别从标题推交易结论。"


def format_date(value):
    if not value:
        return "n/a"
    return value.strftime("%Y-%m-%d")


def format_timestamp(value):
    if not value:
        return "n/a"
    return value.strftime("%Y-%m-%d %H:%M UTC")


def ai_capex_macro_view(by_theme):
    items = by_theme.get("ai_capex", [])
    texts = " ".join(normalize_text(item) for item in items)
    pos_terms = [
        "raise",
        "raised",
        "boost",
        "increase",
        "higher",
        "capacity constrained",
        "backlog",
        "data center",
        "ai infrastructure",
    ]
    risk_terms = [
        "roi",
        "return",
        "concern",
        "high interest",
        "interest rate",
        "financing",
        "debt",
        "free cash flow",
        "margin",
        "power",
        "water",
        "grid",
        "delay",
    ]
    pos_hits = sorted({term for term in pos_terms if term in texts})
    risk_hits = sorted({term for term in risk_terms if term in texts})
    dell_hits = [
        item for item in items
        if "dell" in normalize_text(item) and any(term in normalize_text(item) for term in ["server", "backlog", "guidance", "revenue"])
    ]
    if len(pos_hits) >= 3 and len(risk_hits) >= 3:
        stance = "中性偏利好"
        consensus_delta = "边际强化，不是全市场 capex consensus 的大幅改写"
        read_through = "Dell 对 AI server 订单和 backlog 是硬证据，但更像供应链需求韧性的追加确认；若是全市场 consensus 大幅上修，供应链应出现更广谱的大涨和盈利预测同步上修。"
        risk_level = "中高"
    elif len(pos_hits) >= 3:
        stance = "利好"
        consensus_delta = "需求侧边际强化"
        read_through = "新增信息主要支持 AI 基建继续扩张，但仍需要观察是否扩散到更多 hyperscaler 和供应链盈利预测。"
        risk_level = "中"
    elif len(risk_hits) >= 3:
        stance = "利空"
        consensus_delta = "风险侧边际升温"
        read_through = "新增信息更偏 ROI、融资成本或资源约束，需要警惕高估值硬件链先压估值。"
        risk_level = "高"
    else:
        stance = "中性"
        consensus_delta = "未见足够强的新共识变化"
        read_through = "本窗口新增证据不足以改变 AI capex 总判断。"
        risk_level = "待确认"
    evidence = []
    evidence_titles = set()
    for item in dell_hits + items:
        title_key = canonical_title(item.get("title"))
        if item_key(item) in {item_key(existing) for existing in evidence} or title_key in evidence_titles:
            continue
        if title_key:
            evidence_titles.add(title_key)
        evidence.append(item)
        if len(evidence) >= 5:
            break
    return {
        "stance": stance,
        "consensus_delta": consensus_delta,
        "read_through": read_through,
        "risk_level": risk_level,
        "pos_hits": pos_hits,
        "risk_hits": risk_hits,
        "top_items": evidence,
        "dell_hits": dell_hits,
    }


def evidence_direction(item):
    if item.get("negative_hits") and not item.get("positive_hits"):
        return "利空"
    if item.get("positive_hits") and not item.get("negative_hits"):
        return "利好"
    if item.get("positive_hits") and item.get("negative_hits"):
        return "多空都有"
    if item.get("crowded_hits"):
        return "拥挤风险"
    return "中性"


def canonical_title(value):
    title = re.sub(r"\s+", " ", (value or "").lower()).strip()
    title = re.sub(r"\s+-\s+[^-]{2,40}$", "", title)
    return title


def canonical_event_key(item):
    text = normalize_text(item)
    if "dell" in text and any(term in text for term in ["ai server", "backlog", "record earnings", "raised outlook", "guidance"]):
        return "dell_ai_server_results"
    if "bubble" in text and "ai capex" in text:
        return "ai_capex_bubble_risk"
    if "kuaishou" in text and any(term in text for term in ["monetization", "revenue", "kling"]):
        return "kuaishou_ai_monetization"
    if "memory" in text and any(term in text for term in ["shortage", "scarcity", "hbm"]):
        return "ai_memory_shortage"
    return canonical_title(item.get("title"))


def evidence_table_rows(by_theme, limit=8):
    rows = []
    seen = set()
    seen_titles = set()
    priority = ["ai_capex", "networking_optics", "memory", "power_cooling", "ai_app_roi", "emerging_second_order"]
    for theme_id in priority:
        for item in by_theme.get(theme_id, []):
            key = item_key(item)
            title_key = canonical_event_key(item)
            if key in seen or title_key in seen_titles:
                continue
            seen.add(key)
            if title_key:
                seen_titles.add(title_key)
            tags = []
            if item.get("positive_hits"):
                tags.extend(item["positive_hits"][:2])
            if item.get("negative_hits"):
                tags.extend(item["negative_hits"][:2])
            if item.get("crowded_hits"):
                tags.append("拥挤:" + ",".join(item["crowded_hits"][:2]))
            rows.append({
                "theme": theme_id,
                "item": item,
                "direction": evidence_direction(item),
                "tags": tags,
            })
            if len(rows) >= limit:
                return rows
    return rows


def quote_market(quote):
    quote = (quote or "").upper()
    if quote.endswith((".SS", ".SZ")):
        return "A股"
    if quote.endswith(".HK"):
        return "港股"
    if quote.endswith((".KS", ".TW", ".JP")):
        return "亚太"
    if quote:
        return "美股/海外"
    return "无代码"


def segment_action(row):
    temp = row.get("temperature")
    delta = row.get("delta", "")
    crowding = row.get("crowding")
    if temp == "Hot Consensus":
        if "利好" in delta:
            return "超预期复核"
        if "利空" in delta:
            return "风险复盘"
        return "等待兑现"
    if temp in ("Warming", "Hot/Warming"):
        if crowding in ("拥挤度尚可", "待确认"):
            return "深挖标的"
        return "找低拥挤替代"
    if temp == "Early Signal":
        return "只做验证"
    return "观察"


def segment_readthrough(row):
    temp = row.get("temperature")
    delta = row.get("delta", "")
    crowding = row.get("crowding")
    if "利好" in delta and temp == "Hot Consensus":
        return "新增信息支持需求，但市场已熟；要看盈利预测/订单是否继续上修。"
    if "利空" in delta:
        return "先查是否连续恶化，再评估是否影响订单、价格或毛利。"
    if temp == "Hot Consensus":
        return "逻辑清楚但拥挤，不能当 emergent；只适合做兑现差。"
    if temp in ("Warming", "Hot/Warming"):
        if crowding in ("拥挤度尚可", "待确认"):
            return "有继续研究价值，重点找客户/订单/价格二次证据。"
        return "主题在升温，但代表票也不便宜，优先找更细分或更低拥挤映射。"
    if temp == "Early Signal":
        return "目前只是线索，必须找到可交易映射和公司级证据。"
    return "信息不足。"


def iter_theme_items(by_theme):
    seen = set()
    for items in by_theme.values():
        for item in items:
            key = item_key(item)
            if key in seen:
                continue
            seen.add(key)
            yield item


def holding_exit_radar_alerts(config, by_theme):
    rules = config.get("holding_exit_radar", [])
    if not rules:
        return []
    items = list(iter_theme_items(by_theme))
    alerts = []
    for rule in rules:
        terms = [term.lower() for term in rule.get("terms", []) if term]
        if not terms:
            continue
        hits = []
        for item in items:
            text = normalize_text(item)
            matched = [term for term in terms if term in text]
            if matched:
                hits.append({"item": item, "matched": matched})
        if hits:
            alerts.append({"rule": rule, "hits": hits[:3]})
    severity_order = {"red": 0, "orange": 1, "yellow": 2}
    alerts.sort(key=lambda alert: severity_order.get(alert["rule"].get("severity", "yellow"), 9))
    return alerts


def render_holding_exit_radar(alerts):
    if not alerts:
        return []
    lines = []
    lines.append("## 持仓跑路雷达")
    lines.append("")
    lines.append("只列已经命中负面触发器的持仓；没有触发器时本节不显示。")
    lines.append("")
    lines.append("| 等级 | 持仓 | 触发器 | 证据样本 | 动作 |")
    lines.append("|---|---|---|---|---|")
    for alert in alerts:
        rule = alert["rule"]
        evidence = []
        for hit in alert["hits"]:
            item = hit["item"]
            evidence.append(f"{format_date(item.get('published'))} [{md_escape(item.get('title'))}]({item.get('link')})")
        lines.append(
            f"| {rule.get('severity', 'yellow').upper()} | {md_escape(rule.get('name', rule.get('ticker', 'n/a')))} "
            f"({md_escape(rule.get('ticker', 'n/a'))}) | {md_escape(rule.get('trigger', 'n/a'))} | "
            f"{'<br>'.join(evidence)} | {md_escape(rule.get('action', 'review position'))} |"
        )
    lines.append("")
    return lines


def md_escape(value):
    return (value or "").replace("|", "\\|").strip()


def markdown_to_html(markdown_text, title):
    def inline(value):
        value = html.escape(value)
        value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)
        value = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', value)
        return value

    lines = markdown_text.splitlines()
    body = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line.startswith("# "):
            body.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("### "):
            body.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("|") and idx + 1 < len(lines) and lines[idx + 1].startswith("|---"):
            table_lines = [line]
            idx += 2
            while idx < len(lines) and lines[idx].startswith("|"):
                table_lines.append(lines[idx])
                idx += 1
            idx -= 1
            headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
            body.append('<div class="table-wrap"><table><thead><tr>')
            for header in headers:
                body.append(f"<th>{inline(header)}</th>")
            body.append("</tr></thead><tbody>")
            for table_line in table_lines[1:]:
                cells = [cell.strip() for cell in table_line.strip("|").split("|")]
                body.append("<tr>")
                for cell in cells:
                    cls = ""
                    if cell in ("高拥挤", "代表票高拥挤"):
                        cls = ' class="tag hot"'
                    elif cell in ("中高拥挤", "代表票中高拥挤"):
                        cls = ' class="tag warm"'
                    elif cell in ("拥挤度尚可", "代表票未明显拥挤"):
                        cls = ' class="tag ok"'
                    body.append(f"<td{cls}>{inline(cell)}</td>")
                body.append("</tr>")
            body.append("</tbody></table></div>")
        elif line.startswith("- "):
            body.append(f"<p class='bullet'>• {inline(line[2:])}</p>")
        elif line.strip():
            body.append(f"<p>{inline(line)}</p>")
        idx += 1

    css = """
    :root { --ink:#18212f; --muted:#667085; --line:#d9e0ea; --panel:#f7f9fc; --head:#eef3f8; --accent:#184e77; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", Arial, sans-serif; margin: 0; color: var(--ink); line-height: 1.55; background: #eef2f6; }
    body > * { max-width: 1380px; margin-left: auto; margin-right: auto; }
    h1 { max-width: none; margin: 0 0 18px; padding: 26px 42px 22px; background: #123047; color: #fff; font-size: 28px; letter-spacing: 0; }
    h2 { margin-top: 26px; padding: 14px 18px; border: 1px solid var(--line); border-left: 5px solid var(--accent); background: #fff; font-size: 19px; border-radius: 6px; }
    h3 { margin-top: 22px; font-size: 15px; color: #243b53; }
    p { margin-top: 7px; margin-bottom: 7px; padding-left: 18px; padding-right: 18px; }
    p:nth-of-type(1), p:nth-of-type(2) { color: var(--muted); font-size: 12px; }
    .bullet { margin: 8px auto; padding: 9px 14px; background: #fff; border: 1px solid var(--line); border-radius: 6px; }
    .table-wrap { overflow-x: auto; margin: 12px auto 24px; border: 1px solid var(--line); border-radius: 8px; background: #fff; box-shadow: 0 1px 2px rgba(16,24,40,.04); }
    table { border-collapse: collapse; width: 100%; min-width: 1080px; font-size: 12px; }
    th { background: var(--head); text-align: left; position: sticky; top: 0; color: #243b53; font-weight: 700; }
    th, td { border-bottom: 1px solid #e8edf3; padding: 7px 9px; vertical-align: top; }
    tr:nth-child(even) td { background: #fbfcfe; }
    tr:hover td { background: #f4f8fb; }
    a { color: #1d4f8f; text-decoration: none; }
    strong { color: #14213d; }
    .tag.hot { color: #8a1c1c; font-weight: 700; background: #fde8e8; }
    .tag.warm { color: #855a00; font-weight: 700; background: #fff3cf; }
    .tag.ok { color: #075c47; font-weight: 700; background: #dff7ed; }
    @media print {
      body { margin: 0; background: #fff; }
      h1 { padding: 14mm 12mm 8mm; }
      h2 { margin-top: 14px; }
      .table-wrap { overflow: visible; border: none; }
      table { min-width: 0; font-size: 8.4px; page-break-inside: auto; }
      tr { page-break-inside: avoid; page-break-after: auto; }
      h2 { page-break-after: avoid; }
    }
    """
    return f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title><style>{css}</style></head><body>{''.join(body)}</body></html>"


def find_browser():
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


def render_pdf(html_path, pdf_path):
    browser = find_browser()
    if not browser:
        return False
    file_url = "file:///" + os.path.abspath(html_path).replace("\\", "/")
    subprocess.run(
        [
            browser,
            "--headless",
            "--disable-gpu",
            f"--print-to-pdf={os.path.abspath(pdf_path)}",
            file_url,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return True


def previous_report_issue_time(reports_dir, output_path):
    candidates = []
    output_abs = os.path.abspath(output_path) if output_path else None
    search_dirs = [reports_dir, os.path.join(reports_dir, "archive")]
    for search_dir in search_dirs:
        if not os.path.isdir(search_dir):
            continue
        for name in os.listdir(search_dir):
            if not re.match(r"ai-radar-\d{4}-\d{2}-\d{2}\.md$", name):
                continue
            path = os.path.abspath(os.path.join(search_dir, name))
            if output_abs and path == output_abs:
                continue
            candidates.append(path)
    if not candidates:
        return None
    latest_path = max(candidates, key=lambda path: os.path.getmtime(path))
    return dt.datetime.fromtimestamp(os.path.getmtime(latest_path), tz=dt.timezone.utc).replace(tzinfo=None)


def build_report(config, by_theme, market_rows, discovery_candidates, discovery_topics, market_errors, errors, report_issued_at, delta_since):
    now = report_issued_at
    theme_map = {theme["id"]: theme for theme in config["themes"]}
    market_summary = theme_market_summary(config, market_rows)
    layers = layer_by_id(config)
    lines = []
    lines.append(f"# {config.get('report_title', 'AI Capex Radar')} - {now:%Y-%m-%d}")
    lines.append("")
    lines.append(f"Report issued: {format_timestamp(report_issued_at)}")
    lines.append(f"Delta window: {format_timestamp(delta_since)} -> {format_timestamp(report_issued_at)}")
    lines.append("")
    theme_rows = []
    for theme in config["themes"]:
        items = by_theme.get(theme["id"], [])
        signal = theme_signal(items)
        maturity = theme_maturity(items)
        market_state = market_summary.get(theme["id"], {}).get("state", "n/a")
        layer_id = infer_investment_layer(theme["id"], signal, maturity, market_state)
        layer_name = layers.get(layer_id, {}).get("name", layer_id).split("：")[0]
        theme_rows.append({"theme": theme, "items": items, "signal": signal, "maturity": maturity, "market_state": market_state, "layer": layer_name})

    macro = ai_capex_macro_view(by_theme)
    macro_market = macro_market_dashboard()
    segment_rows = []
    for segment in config.get("segments", []):
        reps = segment_representatives(segment, market_rows)
        crowding = segment_crowding(reps)
        delta = segment_delta(segment, by_theme, discovery_topics)
        layer = layers.get(segment.get("layer"), {}).get("name", segment.get("layer", "")).split("：")[0]
        score = segment_score(segment, crowding)
        row = {
            "segment": segment,
            "reps": reps,
            "crowding": crowding,
            "delta": delta,
            "discovery": segment_discovery_note(segment, discovery_topics),
            "layer": layer,
            "score": score,
        }
        row["temperature"] = segment_temperature(row)
        segment_rows.append(row)

    candidates = [row for row in segment_rows if row["segment"].get("logic_strength") in ("high", "medium") and row["segment"].get("mapping_strength") in ("high", "medium") and row["crowding"] in ("拥挤度尚可", "待确认")]
    candidates.sort(key=lambda row: row["score"], reverse=True)
    crowded = [row for row in segment_rows if row["temperature"] == "Hot Consensus"]
    hot_holding_quotes = {holding.get("quote") or holding.get("ticker") for holding in config.get("holdings", [])}
    market_by_quote = {row.get("quote"): row for row in market_rows}
    segment_by_quote = {}
    for segment in config.get("segments", []):
        for rep in segment.get("reps", []):
            quote = rep.get("quote")
            if quote:
                segment_by_quote.setdefault(quote, segment.get("name"))
    hot_holdings = [
        market_by_quote.get(quote)
        for quote in hot_holding_quotes
        if market_by_quote.get(quote) and combined_crowding(market_by_quote.get(quote)) == "高拥挤"
    ]
    pullback_rows = pullback_risk_dashboard(config, market_rows, by_theme)
    high_pullback = [item for item in pullback_rows if item["risk"]["level"] in ("高", "中高")]
    dell_items = [
        item for item in by_theme.get("ai_capex", [])
        if "dell" in normalize_text(item) and any(term in normalize_text(item) for term in ["server", "backlog", "orders", "guidance", "revenue"])
    ]
    front_evidence = evidence_table_rows(by_theme, limit=8)
    lines.append("## 今日先看")
    lines.append("")
    lines.append(f"- **总判断**：需求侧={macro['stance']}，宏观/资金侧={macro_market['verdict']}。本轮更像“{macro['consensus_delta']}”，不是无条件的全链条需求大幅上修。")
    if dell_items:
        top = dell_items[0]
        lines.append(f"- **关键事件**：Dell AI server 业绩/订单/积压进入本轮 delta，验证 AI server 需求韧性；但这是单公司/服务器链条的边际确认，不等于 hyperscaler capex consensus 被全市场大幅改写。来源：[Dell result]({top.get('link')})。")
    else:
        lines.append("- **关键事件**：本轮没有被自动抓到足够强的 AI server 单公司业绩事件；这类事件以后必须进入优先事件监控。")
    lines.append(f"- **读法**：{macro['read_through']}")
    lines.append(f"- **Macro risk**：{macro_market['message']}")
    if candidates:
        lines.append(f"- **可研究方向**：{', '.join(row['segment']['name'] for row in candidates[:3])}。")
    else:
        lines.append("- **可研究方向**：今天仍没有“逻辑强 + 映射强 + 低拥挤”的完美交集，更多是已拥挤主线的超预期复核。")
    if hot_holdings:
        lines.append("- **持仓风险**：" + "；".join(f"{row.get('name')} 3M {fmt_pct(row.get('returns', {}).get('3M'))}" for row in hot_holdings[:4]) + "，这些需要看业绩继续兑现，不能只看主题热度。")
    if high_pullback:
        lines.append("- **回调风险**：" + "；".join(f"{item['row'].get('name')}={item['risk']['level']}（交易拥挤={item['trading']['level']}，支撑={item['support']['level']}）" for item in high_pullback[:4]) + "。结论不是“涨多了就该卖”，而是看预期上修能否继续抵消交易拥挤。")
    lines.append("")

    lines.append("## 本轮新增证据")
    lines.append("")
    lines.append("先看 update window 里真正新增的事实，再读后面的历史基准和拥挤度。方向只代表这条新闻/事实对 AI capex 链条的边际含义。")
    lines.append("")
    lines.append("| 方向 | 主题 | 日期 | 证据 | 关键词 |")
    lines.append("|---|---|---|---|---|")
    if front_evidence:
        for row in front_evidence:
            item = row["item"]
            lines.append(
                f"| {row['direction']} | {row['theme']} | {format_date(item.get('published'))} | "
                f"[{md_escape(item.get('title'))}]({item.get('link')}) | {md_escape(', '.join(row['tags']) or 'n/a')} |"
            )
    else:
        lines.append("| 中性 | n/a | n/a | 本轮没有足够强的新证据 | n/a |")
    lines.append("")

    lines.append("## AI Capex Macro")
    lines.append("")
    lines.append("Macro 部分分三层：需求证据、市场隐含资金成本、资源/建设约束。过去的 capex 指引只作为基准，不当作今天的新利好；真正要看 update window 是否改变 consensus，以及利率/融资/资源约束是否开始压估值和项目 IRR。")
    lines.append("")
    lines.append("| 维度 | 方向 | 当前判断 | 投资含义 |")
    lines.append("|---|---|---|---|")
    lines.append(f"| Update window | {macro['stance']} | {macro['consensus_delta']} | {macro['read_through']} |")
    lines.append(f"| 资金成本/折现率 | {macro_market['verdict']} | US 10Y 约 {fmt_num(next((row.get('price') for row in macro_market['rows'] if row['quote']=='USGG10YR'), None))}%，3M 约 {fmt_bps(macro_market['us10_3m_bps'])}；US 2Y 约 {fmt_num(next((row.get('price') for row in macro_market['rows'] if row['quote']=='USGG2YR'), None))}%，3M 约 {fmt_bps(macro_market['us2_3m_bps'])} | 利率上行会先压长久期/高 PE/远期盈利故事，也提高 private credit、项目债、greenfield data center 的 hurdle rate。 |")
    lines.append(f"| 风险温度 | 中性偏利空 | ROI、融资成本、长端利率、电力/水/土地约束仍在发酵，风险温度={macro['risk_level']} | 风险不是订单立刻消失，而是高 PE/远期故事先压估值；如果利率或融资成本继续上行，边际项目和高估值二阶映射更脆弱。 |")
    lines.append("| 传导顺序 | 中性 | Hyperscaler capex -> GPU/ASIC 集群 -> 网络/PCB/内存带宽 -> 电力/散热/资源约束 | 越靠近订单和瓶颈，兑现要求越高；越远的二阶映射，需要更强证据，不能只靠主题外溢。 |")
    lines.append("| 核心证伪 | 利空触发 | Capex 指引停止上修、AI ROI 被明确质疑、融资型数据中心项目放缓、长端利率继续上行 | 出现组合坏信号时，高拥挤主线先做风险复盘，不再只看静态 PE。 |")
    lines.append("")
    facts = config.get("ai_capex_macro_facts", [])
    if facts:
        lines.append("**公开基准事实：**")
        lines.append("")
        lines.append("| 指标 | 当前公开信息 | 投资含义 | 来源 |")
        lines.append("|---|---|---|---|")
        for fact in facts:
            source = fact.get("source", "")
            source_text = f"[link]({source})" if source else "n/a"
            lines.append(
                f"| {md_escape(fact.get('metric'))} | {md_escape(fact.get('status'))} | "
                f"{md_escape(fact.get('implication'))} | {source_text} |"
            )
        lines.append("")
    if macro["pos_hits"] or macro["risk_hits"]:
        lines.append(f"- 正向关键词：{', '.join(macro['pos_hits'][:8]) if macro['pos_hits'] else 'n/a'}")
        lines.append(f"- 风险关键词：{', '.join(macro['risk_hits'][:8]) if macro['risk_hits'] else 'n/a'}")
    if macro_market["risk_notes"]:
        lines.append("- Bloomberg 市场信号：")
        for note in macro_market["risk_notes"][:6]:
            lines.append(f"  - {note}")
    if macro_market["rows"]:
        lines.append("")
        lines.append("**Macro / financing dashboard（Bloomberg）**")
        lines.append("")
        lines.append("| 指标 | 桶 | 最新 | 1M | 3M | 6M | 1Y | 读法 |")
        lines.append("|---|---|---:|---:|---:|---:|---:|---|")
        for row in macro_market["rows"]:
            returns = row.get("returns", {})
            read = ""
            if row["quote"] in ("USGG10YR", "USGG2YR"):
                read = "融资/折现率压力" if (returns.get("3M") or 0) > 8 else "利率压力有限"
            elif row["quote"] == "SOX":
                read = "AI 硬件 beta 拥挤" if (returns.get("3M") or 0) > 40 else "硬件 beta 正常"
            elif row["quote"] == "VIX":
                read = "风险偏好尚可" if (returns.get("1M") or 0) < 0 else "波动压力上升"
            elif row["quote"] in ("LUACOAS", "LF98OAS"):
                read = "信用利差压力上升" if (returns.get("1M") or 0) > 5 else "信用融资环境尚可"
            elif row["quote"] in ("HG1", "NG1", "CL1"):
                read = "资源/建设成本上行" if (returns.get("1M") or 0) > 8 else "成本压力未明显恶化"
            else:
                read = "风险偏好/流动性参考"
            lines.append(
                f"| {row['name']} | {row['bucket']} | {fmt_num(row.get('price'))} | "
                f"{fmt_pct(returns.get('1M'))} | {fmt_pct(returns.get('3M'))} | {fmt_pct(returns.get('6M'))} | {fmt_pct(returns.get('1Y'))} | {read} |"
            )
    lines.append("")
    lines.append("**结构性 macro risk 参考**")
    lines.append("")
    lines.append("| 主题 | 结论 | 来源 |")
    lines.append("|---|---|---|")
    for ref in MACRO_RISK_REFERENCES:
        lines.append(f"| {ref['topic']} | {md_escape(ref['point'])} | [{ref['source']}]({ref['url']}) |")
    lines.append("")
    if macro["top_items"]:
        lines.append("- 今日公开信息样本：")
        for item in macro["top_items"][:4]:
            lines.append(f"  - {format_date(item.get('published'))} [{md_escape(item.get('title'))}]({item.get('link')})")
    lines.append("")

    lines.append("## Segment Matrix")
    lines.append("")
    lines.append("这张表把 temperature 直接并入 segment 判断：Hot Consensus=市场已经充分讨论，只做超预期复核；Warming=证据在升温，找低拥挤映射；Early Signal=只有线索，不能直接交易。")
    lines.append("")
    lines.append("| Segment | 层级 | 温度 | 本轮方向 | 拥挤度 | 动作 | 怎么读 | 代表票 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for row in segment_rows:
        segment = row["segment"]
        rep_text = ", ".join([rep.get("name", rep.get("quote", "")) for rep in segment.get("reps", [])[:4]])
        lines.append(
            f"| {segment['name']} | {row['layer']} | {row['temperature']} | {row['delta']} | "
            f"{row['crowding']} | {segment_action(row)} | {segment_readthrough(row)} | {rep_text} |"
        )
    lines.append("")
    hot = [row for row in segment_rows if row["temperature"] == "Hot Consensus"]

    lines.append("## 结论")
    lines.append("")
    lines.append("理想目标：逻辑强度高、映射强度高、拥挤度不是高拥挤。若没有完美交集，就按“可研究 / 只能拥挤复核 / 先排除”分层。")
    lines.append("")
    if candidates:
        lines.append("**可优先研究：**")
        for row in candidates[:8]:
            segment = row["segment"]
            lines.append(f"- **{segment['name']}**：{row['layer']}，拥挤度={row['crowding']}。{segment['logic']}")
    else:
        lines.append("**可优先研究：** 暂无完全满足条件的 segment。")
    if crowded:
        lines.append("")
        lines.append("**只能拥挤复核，不当 early theme：**")
        for row in crowded[:8]:
            lines.append(f"- {row['segment']['name']}")
    lines.append("")

    lines.append("## 代表票候选")
    lines.append("")
    lines.append("只列“逻辑/映射较强，且拥挤度没有明显爆掉”的候选。没有候选时，不硬凑票。")
    lines.append("")
    if candidates:
        lines.append("| Segment | 标的 | 代码 | 3M | 1Y | 27E P/E | 28E P/E | EV/EBITDA | 拥挤度 |")
        lines.append("|---|---|---|---:|---:|---:|---:|---:|---|")
        for row in candidates[:8]:
            for rep in row["reps"][:4]:
                returns = rep.get("returns", {})
                lines.append(
                    f"| {row['segment']['name']} | {rep.get('name')} | {rep.get('quote')} | "
                    f"{fmt_pct(returns.get('3M'))} | {fmt_pct(returns.get('1Y'))} | {fmt_num(rep.get('pe_2027e'))} | {fmt_num(rep.get('pe_2028e'))} | "
                    f"{fmt_num(rep.get('ev_to_ebitda'))} | {combined_crowding(rep)} |"
                )
    else:
        lines.append("本轮没有满足条件的新候选。结论是：主线仍强，但代表票大多已经拥挤；今天更适合做持仓兑现复核和二阶线索验证。")
    lines.append("")

    lines.append("## 搜索/新闻线索")
    lines.append("")
    lines.append("这是 update window 的关键词雷达，不是投资结论。它只回答“哪里开始出现更多讨论”，真正能否变成交易机会，要回到上面的温度、映射和拥挤度。")
    visible_topics = [topic for topic in discovery_topics if topic["hits"]]
    if visible_topics:
        for topic in sorted(visible_topics, key=lambda row: (len(row["hits"]), -row["crowded_terms"]), reverse=True)[:5]:
            crowded_note = "有拥挤词，需谨慎" if topic["crowded_terms"] else "未见明显拥挤词"
            lines.append(f"- **{topic['name']}**：命中 {len(topic['hits'])} 条，{crowded_note}。{topic['why']}")
            if topic["keywords"]:
                lines.append(f"  - 关键词：{', '.join(topic['keywords'][:6])}")
    else:
        lines.append("- 暂无足够强的前置线索。")
    lines.append("")

    lines.append("## 低拥挤观察篮")
    lines.append("")
    lines.append("这是从 holdings/watchlist 中筛出的低拥挤复核对象，不是基于新闻热度自动推荐；作用是避免只盯已经涨完的 Hot Consensus。")
    lines.append("")
    lines.append("| 标的 | 代码 | 主题 | 3M | 1Y | 综合拥挤度 |")
    lines.append("|---|---|---|---:|---:|---|")
    watch_by_quote = {item.get("quote"): item for item in config.get("watchlist", [])}
    quiet_rows = [
        row for row in market_rows
        if row.get("quote") in watch_by_quote and combined_crowding(row) == "拥挤度尚可"
    ]
    quiet_rows.sort(key=lambda row: (row.get("returns", {}).get("3M") if row.get("returns", {}).get("3M") is not None else -999))
    for row in quiet_rows[:8]:
        returns = row.get("returns", {})
        lines.append(f"| {row.get('name')} | {row.get('quote')} | {','.join(row.get('themes', []))} | {fmt_pct(returns.get('3M'))} | {fmt_pct(returns.get('1Y'))} | {combined_crowding(row)} |")
    if not quiet_rows:
        lines.append("| n/a | n/a | n/a | n/a | n/a | 当前观察池没有低拥挤度标的 |")
    lines.append("")

    lines.extend(render_holding_exit_radar(holding_exit_radar_alerts(config, by_theme)))

    lines.append("## 回调风险结论")
    lines.append("")
    lines.append("只展示结论，不展开计算过程。这个表把短期交易拥挤和基本面/预期支撑分开看，避免把强趋势简单判成高风险。")
    lines.append("")
    lines.append("| 标的 | 代码 | 交易拥挤 | 支撑强度 | 综合风险 | 结论 |")
    lines.append("|---|---|---|---|---|---|")
    for item in pullback_rows:
        row = item["row"]
        risk = item["risk"]
        lines.append(f"| {row.get('name')} | {row.get('quote')} | {item['trading']['level']} | {item['support']['level']} | {risk['level']} | {risk['action']} |")
    if not pullback_rows:
        lines.append("| n/a | n/a | n/a | n/a | n/a | 没有可用数据 |")
    lines.append("")

    lines.append("## 持仓映射")
    lines.append("")
    for holding in config.get("holdings", []):
        own_row = market_by_quote.get(holding.get("quote") or holding.get("ticker"), {})
        own_returns = own_row.get("returns", {})
        own_crowding = combined_crowding(own_row) if own_row else "无行情"
        linked = []
        for theme_id in holding["themes"]:
            row = next((row for row in theme_rows if row["theme"]["id"] == theme_id), None)
            if row:
                linked.append(f"{row['theme']['name']}={row['layer']}/{row['signal']}/{row['market_state']}")
        linked_text = "; ".join(linked) if linked else "无明确 AI 直接映射"
        lines.append(
            f"- **{holding['name']} ({holding['ticker']})**：自身={own_crowding} "
            f"(3M {fmt_pct(own_returns.get('3M'))}, 1Y {fmt_pct(own_returns.get('1Y'))})；相关主题：{linked_text}"
        )
    lines.append("")

    lines.append("## 股价拥挤度")
    lines.append("")
    lines.append("覆盖范围来自 holdings、watchlist 和每个 segment 的代表票；不是全市场覆盖。用途是按 segment 和市场检查代表票是否已经拥挤，避免把已充分定价的主线误判成新机会。")
    lines.append("")
    lines.append("| Segment | 市场 | 标的 | 代码 | 最新日 | 1M | 3M | 1Y | 27E P/E | 28E P/E | Fwd P/E | TTM P/E | EV/EBITDA | EV/Sales | 综合 |")
    lines.append("|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    sorted_rows = sorted(
        [row for row in market_rows if row.get("returns")],
        key=lambda row: (
            segment_by_quote.get(row.get("quote"), "zz"),
            quote_market(row.get("quote")),
            -(row["returns"].get("3M") if row["returns"].get("3M") is not None else -999),
        ),
    )
    for row in sorted_rows:
        returns = row.get("returns", {})
        lines.append(
            f"| {segment_by_quote.get(row.get('quote'), 'Portfolio/Watchlist')} | {quote_market(row.get('quote'))} | {row.get('name')} | {row.get('quote')} | {row.get('date', 'n/a')} | "
            f"{fmt_pct(returns.get('1M'))} | {fmt_pct(returns.get('3M'))} | {fmt_pct(returns.get('1Y'))} | "
            f"{fmt_num(row.get('pe_2027e'))} | {fmt_num(row.get('pe_2028e'))} | {fmt_num(row.get('forward_pe'))} | {fmt_num(row.get('trailing_pe'))} | {fmt_num(row.get('ev_to_ebitda'))} | {fmt_num(row.get('ev_to_revenue'))} | {combined_crowding(row)} |"
        )
    lines.append("")

    lines.append("## Evidence")
    lines.append("")
    for theme in config["themes"]:
        items = by_theme.get(theme["id"], [])[:8]
        lines.append(f"### {theme['name']}")
        lines.append("")
        if not items:
            lines.append("- No recent matched items.")
            lines.append("")
            continue
        for item in items:
            hits = []
            if item.get("positive_hits"):
                hits.append("positive=" + ", ".join(item["positive_hits"][:4]))
            if item.get("negative_hits"):
                hits.append("negative=" + ", ".join(item["negative_hits"][:4]))
            if item.get("crowded_hits"):
                hits.append("crowded=" + ", ".join(item["crowded_hits"][:4]))
            hit_text = f" ({'; '.join(hits)})" if hits else ""
            summary = textwrap.shorten(md_escape(item.get("summary", "")), width=240, placeholder="...")
            lines.append(f"- {format_date(item.get('published'))} [{md_escape(item.get('title'))}]({item.get('link')}){hit_text}")
            if summary:
                lines.append(f"  - {summary}")
        lines.append("")

    if errors:
        lines.append("## Fetch Errors")
        lines.append("")
        for err in errors[:20]:
            lines.append(f"- {err}")
        lines.append("")

    if market_errors:
        lines.append("## Market Data Errors")
        lines.append("")
        for err in market_errors[:20]:
            lines.append(f"- {err}")
        lines.append("")

    lines.append("## Manual Inbox")
    lines.append("")
    lines.append("Put `.txt` or `.md` notes, transcript excerpts, research notes, or OCR output into `manual_inbox/`; they will be included in the next run.")
    lines.append("")
    return "\n".join(lines)


def build_readthrough(config, by_theme, market_rows, discovery_topics, report_issued_at, delta_since):
    macro = ai_capex_macro_view(by_theme)
    macro_market = macro_market_dashboard()
    market_by_quote = {row.get("quote"): row for row in market_rows}
    lines = []
    lines.append(f"# AI Capex Radar Readthrough - {report_issued_at:%Y-%m-%d}")
    lines.append("")
    lines.append(f"Report issued: {format_timestamp(report_issued_at)}")
    lines.append(f"Delta window: {format_timestamp(delta_since)} -> {format_timestamp(report_issued_at)}")
    lines.append("")

    lines.append("## 一句话")
    lines.append("")
    lines.append(
        "今天不是“AI capex 全面重新上修”的日子，而是 Dell 把 AI server 需求韧性又确认了一次。"
        "这对服务器、光模块、PCB、内存接口是利好，但这些方向很多已经很拥挤；同时利率和项目融资成本在变贵，"
        "所以市场会更挑剔：只奖励真正继续超预期的公司。"
    )
    lines.append("")

    lines.append("## 今天真正更新了什么")
    lines.append("")
    dell_items = [
        item for item in by_theme.get("ai_capex", [])
        if "dell" in normalize_text(item) and any(term in normalize_text(item) for term in ["server", "backlog", "guidance", "revenue", "record"])
    ]
    if dell_items:
        item = dell_items[0]
        lines.append(f"- **Dell 事件**：Dell AI server 相关业绩、订单/积压和指引进入本轮窗口。来源：[{md_escape(item.get('title'))}]({item.get('link')})。")
    else:
        lines.append("- **Dell 事件**：本轮没有抓到足够强的 Dell/AI server 新证据。")
    lines.append(f"- **需求侧判断**：{macro['stance']}。这更像“{macro['consensus_delta']}”，不是全市场共识被大幅改写。")
    lines.append(f"- **资金侧判断**：{macro_market['verdict']}。{macro_market['message']}")
    lines.append("- **信用利差**：IG/HY OAS 当前没有明显恶化，说明短期不是信用市场关门；压力主要来自国债利率和估值拥挤。")
    lines.append("")

    lines.append("## 为什么利率重要")
    lines.append("")
    lines.append(
        "AI data center 是很重资产的生意：买 GPU、建机房、签电力、租/建数据中心，都要先花很多钱。"
        "当 5Y/10Y/30Y 利率上行时，项目融资成本和估值折现率都会上去。"
        "这不代表订单马上消失，但会让市场更不愿意给远期故事高估值。"
    )
    lines.append("")
    lines.append("| 指标 | 当前读法 | 对 AI capex 的含义 |")
    lines.append("|---|---|---|")
    lines.append(f"| US 10Y | 3M 约 {fmt_bps(macro_market.get('us10_3m_bps'))} | 长久期成长股和高 PE 硬件链估值承压。 |")
    lines.append(f"| US 5Y | 3M 约 {fmt_bps(macro_market.get('us5_3m_bps'))} | 更贴近项目融资/中期债务成本，影响 data center IRR。 |")
    lines.append(f"| US 30Y | 3M 约 {fmt_bps(macro_market.get('us30_3m_bps'))} | 影响 REIT、utility、长期基础设施资产估值。 |")
    lines.append(f"| IG/HY OAS | 1M 约 {fmt_bps(macro_market.get('ig_oas_1m_bps'))} / {fmt_bps(macro_market.get('hy_oas_1m_bps'))} | 如果走阔，说明信用融资变差；当前更像信用环境尚可。 |")
    lines.append("")

    lines.append("## 应该怎么看供应链")
    lines.append("")
    lines.append("- **AI server / optical / PCB**：Dell 是正面验证，但这些已经是 Hot Consensus。正确动作是复核订单和盈利预测是否继续上修，不是因为新闻标题就全链条追高。")
    lines.append("- **HBM / memory / retimer**：产业逻辑仍强，但本窗口没有同等级的新确认；更适合等财报、价格、交期和订单数据。")
    lines.append("- **Power / cooling / grid**：逻辑不是“今天 Dell 利好所以全涨”，而是数据中心建设继续推高 power availability 的稀缺性。现在新增的 CEG/VST/NEE 可以作为电力侧观察 proxy。")
    lines.append("- **Data center REIT**：EQIX/DLR 可以看需求是否真的转成租金/开发收益，但估值已经不便宜，且对长端利率敏感。")
    lines.append("- **AI applications / ROI**：这是 capex 能否长期持续的最终答案。腾讯、快手、Microsoft、ServiceNow 这类要看 AI 是否带来收入，而不是只看投入。")
    lines.append("")

    lines.append("## 持仓含义")
    lines.append("")
    for holding in config.get("holdings", []):
        quote = holding.get("quote") or holding.get("ticker")
        row = market_by_quote.get(quote, {})
        returns = row.get("returns", {})
        crowding = combined_crowding(row) if row else "无行情"
        if quote in ("300308.SZ", "002463.SZ", "688008.SS"):
            implication = "主线逻辑被 Dell 支撑，但自身已高拥挤，后面必须靠订单/利润继续兑现。"
        elif quote in ("0700.HK", "1024.HK"):
            implication = "更偏 ROI/应用侧，关键是 AI 是否真正带来收入和利润，而不是 capex 本身。"
        elif quote == "300750.SZ":
            implication = "AI 电力/储能是加分项，不应把它机械当作纯 AI capex 标的。"
        else:
            implication = "目前没有明确 AI 直接映射，按原本基本面框架看。"
        lines.append(
            f"- **{holding['name']} ({quote})**：拥挤度={crowding}，3M {fmt_pct(returns.get('3M'))}，1Y {fmt_pct(returns.get('1Y'))}。{implication}"
        )
    lines.append("")

    lines.append("## 下一步要盯什么")
    lines.append("")
    lines.append("- Hyperscaler 是否跟随 Dell 出现更强 capex / backlog / data center capacity 上修。")
    lines.append("- SOX、光模块、PCB、内存接口代表票是否继续涨但盈利预测没有同步上修。")
    lines.append("- US 5Y/10Y/30Y 是否继续上行；如果继续上行，高估值和 REIT/utility 会更敏感。")
    lines.append("- IG/HY OAS 是否开始走阔；如果走阔，说明融资压力从利率扩散到信用风险。")
    lines.append("- Power availability、grid interconnection、gas/nuclear/utility 合同是否出现新的公司级订单。")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=os.path.join(ROOT, "config.json"))
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    reports_dir = os.path.join(PROJECT_ROOT, config.get("reports_dir", "reports"))
    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(os.path.join(PROJECT_ROOT, config.get("manual_inbox_dir", "manual_inbox")), exist_ok=True)

    output = args.output
    if not output:
        output = os.path.join(reports_dir, f"ai-radar-{utc_now():%Y-%m-%d}.md")

    report_issued_at = utc_now()
    delta_since = previous_report_issue_time(reports_dir, output)
    if delta_since is None:
        delta_since = report_issued_at - dt.timedelta(days=int(config.get("lookback_days", 1)))

    raw_items, errors = collect_items(config)
    discovery_items, discovery_errors = collect_discovery_items(config, since=delta_since)
    errors.extend(discovery_errors)
    by_theme = classify_items(config, raw_items, since=delta_since)
    market_rows, market_errors = collect_market_data(config)
    market_summary = theme_market_summary(config, market_rows)
    discovery_candidates, discovery_topics = build_discovery(config, discovery_items, market_summary)
    report = build_report(
        config,
        by_theme,
        market_rows,
        discovery_candidates,
        discovery_topics,
        market_errors,
        errors,
        report_issued_at,
        delta_since,
    )
    readthrough = build_readthrough(
        config,
        by_theme,
        market_rows,
        discovery_topics,
        report_issued_at,
        delta_since,
    )

    with open(output, "w", encoding="utf-8") as f:
        f.write(report)
    readthrough_output = os.path.splitext(output)[0] + "-readthrough.md"
    with open(readthrough_output, "w", encoding="utf-8") as f:
        f.write(readthrough)
    html_output = os.path.splitext(output)[0] + ".html"
    pdf_output = os.path.splitext(output)[0] + ".pdf"
    readthrough_html_output = os.path.splitext(output)[0] + "-readthrough.html"
    readthrough_pdf_output = os.path.splitext(output)[0] + "-readthrough.pdf"
    with open(html_output, "w", encoding="utf-8") as f:
        f.write(markdown_to_html(report, config.get("report_title", "AI Capex Radar")))
    with open(readthrough_html_output, "w", encoding="utf-8") as f:
        f.write(markdown_to_html(readthrough, f"{config.get('report_title', 'AI Capex Radar')} Readthrough"))
    pdf_ok = False
    try:
        pdf_ok = render_pdf(html_output, pdf_output)
    except Exception as exc:
        print(f"PDF export failed: {exc}")
    readthrough_pdf_ok = False
    try:
        readthrough_pdf_ok = render_pdf(readthrough_html_output, readthrough_pdf_output)
    except Exception as exc:
        print(f"Readthrough PDF export failed: {exc}")
    print(output)
    print(readthrough_output)
    print(html_output)
    print(readthrough_html_output)
    if pdf_ok:
        print(pdf_output)
    if readthrough_pdf_ok:
        print(readthrough_pdf_output)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
