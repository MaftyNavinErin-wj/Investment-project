import argparse
import datetime as dt
import email.utils
import html
import math
import json
import os
import re
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
        return "上修/变紧"
    if total <= -2 or (neg_hits >= 3 and neg_hits > pos_hits):
        return "下修/转弱"
    if items:
        return "有信息流，但方向待确认"
    return "暂无有效新信号"


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
    return {"symbol": symbol, "date": now.strftime("%Y-%m-%d"), "price": current, "returns": returns}


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
        rows = {}
        for item in snapshot.get("rows", []):
            key = (item.get("quote") or bloomberg_security_key(item.get("security"))).upper()
            fields = item.get("fields", {})
            rows[key] = {
                "symbol": key,
                "date": (snapshot.get("created_at") or "")[:10],
                "price": parse_float(fields.get("PX_LAST")),
                "market_cap": parse_float(fields.get("CUR_MKT_CAP")),
                "forward_pe": parse_float(fields.get("BEST_PE_RATIO")),
                "ev_to_ebitda": parse_float(fields.get("EV_TO_T12M_EBITDA")),
                "ev_to_revenue": parse_float(fields.get("EV_TO_T12M_SALES")),
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
            "1M": trailing_return(21),
            "3M": trailing_return(63),
            "6M": trailing_return(126),
            "1Y": trailing_return(252),
        },
        "volatility_30d": volatility_30d,
        "max_drawdown_1y": max_drawdown * 100,
    }


def load_bloomberg_history():
    for path in BLOOMBERG_HISTORY_PATHS:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            history = json.load(f)
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
        if items:
            signals.append(f"{theme_id}:{theme_signal(items)}")
    matched_topics = []
    segment_text = f"{segment.get('name', '')} {segment.get('logic', '')}".lower()
    for topic in discovery_topics:
        topic_text = f"{topic.get('name', '')} {' '.join(topic.get('keywords', []))}".lower()
        if topic.get("hits") and any(word in topic_text for word in segment_text.split()[:6]):
            matched_topics.append(topic["name"])
    if signals:
        return "; ".join(signals[:3])
    if matched_topics:
        return "discovery: " + ", ".join(matched_topics[:2])
    return "无明显新 delta"


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
    if crowding in ("拥挤度尚可", "待确认") and "上修/变紧" in delta:
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
    if len(pos_hits) >= 3 and len(risk_hits) >= 3:
        stance = "总水位仍上修，但市场开始同时交易 ROI、融资成本和资源约束。"
        risk_level = "中高"
    elif len(pos_hits) >= 3:
        stance = "总水位偏上修，AI 基建仍处在扩张阶段。"
        risk_level = "中"
    elif len(risk_hits) >= 3:
        stance = "风险词更多，需警惕 AI capex 从上修转为审慎。"
        risk_level = "高"
    else:
        stance = "公开信息不足，先维持观察。"
        risk_level = "待确认"
    top_items = items[:5]
    return {
        "stance": stance,
        "risk_level": risk_level,
        "pos_hits": pos_hits,
        "risk_hits": risk_hits,
        "top_items": top_items,
    }


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
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", Arial, sans-serif; margin: 28px; color: #1f2937; line-height: 1.55; }
    h1 { font-size: 28px; margin-bottom: 18px; }
    h2 { margin-top: 30px; padding-top: 12px; border-top: 1px solid #e5e7eb; font-size: 20px; }
    h3 { margin-top: 22px; font-size: 16px; }
    p { margin: 7px 0; }
    .bullet { margin-left: 8px; }
    .table-wrap { overflow-x: auto; margin: 12px 0 24px; border: 1px solid #e5e7eb; border-radius: 8px; }
    table { border-collapse: collapse; width: 100%; min-width: 980px; font-size: 12px; }
    th { background: #f3f4f6; text-align: left; position: sticky; top: 0; }
    th, td { border-bottom: 1px solid #e5e7eb; padding: 7px 9px; vertical-align: top; }
    tr:nth-child(even) td { background: #fafafa; }
    a { color: #2563eb; text-decoration: none; }
    .tag.hot { color: #991b1b; font-weight: 700; background: #fee2e2; }
    .tag.warm { color: #92400e; font-weight: 700; background: #fef3c7; }
    .tag.ok { color: #065f46; font-weight: 700; background: #d1fae5; }
    @media print {
      body { margin: 14mm; }
      .table-wrap { overflow: visible; border: none; }
      table { min-width: 0; font-size: 9px; page-break-inside: auto; }
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
    if output_abs and os.path.exists(output_abs):
        candidates.append(output_abs)
    if os.path.isdir(reports_dir):
        for name in os.listdir(reports_dir):
            if not re.match(r"ai-radar-\d{4}-\d{2}-\d{2}\.md$", name):
                continue
            path = os.path.abspath(os.path.join(reports_dir, name))
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
    lines.append("## AI Capex Macro")
    lines.append("")
    lines.append("先判断总水位，再看细分环节。若美国 AI capex 从继续上修变成审慎，A 股硬件链的估值会先受压；若总水位仍上修，重点就是找哪一环节继续吃到订单和盈利预测上修。")
    lines.append("")
    lines.append("| 维度 | 当前判断 | 对 A 股硬件链的含义 |")
    lines.append("|---|---|---|")
    lines.append(f"| 总水位 | {macro['stance']} | 支撑光模块、AI PCB、存储接口、电力/散热等核心链条，但不能自动推出所有二阶映射都有机会。 |")
    lines.append(f"| 风险温度 | {macro['risk_level']} | 风险不是订单立刻消失，而是高 PE/远期故事先被压估值；进一步加息或长端利率上行会放大这个压力。 |")
    lines.append("| 传导顺序 | Hyperscaler capex -> GPU/ASIC 集群 -> 网络/PCB/内存带宽 -> 电力/散热/资源约束 | 中际最直接吃网络瓶颈，沪电吃高速 PCB 复杂度，澜起吃 MRDIMM/Retimer/CXL 等架构升级。 |")
    lines.append("| 核心证伪 | Capex 指引停止上修、AI ROI 被质疑、融资型数据中心项目放缓、长端利率继续上行 | 出现组合坏信号时，高拥挤主线先做风险复盘，不再只看静态 PE。 |")
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
    if macro["top_items"]:
        lines.append("- 今日公开信息样本：")
        for item in macro["top_items"][:4]:
            lines.append(f"  - {format_date(item.get('published'))} [{md_escape(item.get('title'))}]({item.get('link')})")
    lines.append("")

    segment_rows = []
    for segment in config.get("segments", []):
        reps = segment_representatives(segment, market_rows)
        crowding = segment_crowding(reps)
        delta = segment_delta(segment, by_theme, discovery_topics)
        layer = layers.get(segment.get("layer"), {}).get("name", segment.get("layer", "")).split("：")[0]
        score = segment_score(segment, crowding)
        row = {"segment": segment, "reps": reps, "crowding": crowding, "delta": delta, "layer": layer, "score": score}
        row["temperature"] = segment_temperature(row)
        segment_rows.append(row)

    lines.append("## Segment 全景")
    lines.append("")
    lines.append("先看所有相关 segment，再找“逻辑强、映射强、拥挤度尚可”的交集。")
    lines.append("")
    lines.append("| Segment | 层级 | 温度 | 逻辑 | 映射 | 拥挤度 | 最新 delta | 代表票 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for row in segment_rows:
        segment = row["segment"]
        rep_text = ", ".join([rep.get("name", rep.get("quote", "")) for rep in segment.get("reps", [])[:4]])
        lines.append(
            f"| {segment['name']} | {row['layer']} | {row['temperature']} | {segment.get('logic_strength')} | {segment.get('mapping_strength')} | "
            f"{row['crowding']} | {row['delta']} | {rep_text} |"
        )
    lines.append("")

    lines.append("## Theme Temperature")
    lines.append("")
    lines.append("Hot 不代表不能涨，但不能叫 emergent；Warming 才适合继续找标的；Early 只是线索，需要人工验证。")
    lines.append("")
    hot = [row for row in segment_rows if row["temperature"] == "Hot Consensus"]
    warming = [row for row in segment_rows if row["temperature"] in ("Warming", "Hot/Warming")]
    early = [row for row in segment_rows if row["temperature"] == "Early Signal"]
    if hot:
        lines.append("**Hot Consensus：只做趋势/超预期复核，不当 early theme**")
        for row in hot[:10]:
            lines.append(f"- {row['segment']['name']}：{row['crowding']}，{row['segment']['logic']}")
        lines.append("")
    if warming:
        lines.append("**Warming：可继续验证，重点找未拥挤标的**")
        for row in warming[:10]:
            lines.append(f"- {row['segment']['name']}：{row['crowding']}，{row['segment']['logic']}")
        lines.append("")
    if early:
        lines.append("**Early Signals：不是交易结论，只是人工深挖线索**")
        for row in early[:10]:
            lines.append(f"- {row['segment']['name']}：{row['crowding']}，{row['segment']['logic']}")
        lines.append("")

    lines.append("## 结论")
    lines.append("")
    lines.append("理想目标：逻辑强度高、映射强度高、拥挤度不是高拥挤。若没有完美交集，就按“可研究 / 只能拥挤复核 / 先排除”分层。")
    lines.append("")
    candidates = [row for row in segment_rows if row["segment"].get("logic_strength") in ("high", "medium") and row["segment"].get("mapping_strength") in ("high", "medium") and row["crowding"] in ("拥挤度尚可", "待确认")]
    candidates.sort(key=lambda row: row["score"], reverse=True)
    if candidates:
        lines.append("**可优先研究：**")
        for row in candidates[:8]:
            segment = row["segment"]
            lines.append(f"- **{segment['name']}**：{row['layer']}，拥挤度={row['crowding']}。{segment['logic']}")
    else:
        lines.append("**可优先研究：** 暂无完全满足条件的 segment。")
    crowded = [row for row in segment_rows if row["temperature"] == "Hot Consensus"]
    if crowded:
        lines.append("")
        lines.append("**只能拥挤复核，不当 early theme：**")
        for row in crowded[:8]:
            lines.append(f"- {row['segment']['name']}")
    lines.append("")

    lines.append("## 代表票候选")
    lines.append("")
    lines.append("先从可研究 segment 里找票；高拥挤 segment 的票只做超预期复核。")
    lines.append("")
    lines.append("| Segment | 标的 | 代码 | 3M | 1Y | Fwd P/E | EV/EBITDA | 拥挤度 |")
    lines.append("|---|---|---|---:|---:|---:|---:|---|")
    for row in candidates[:8]:
        for rep in row["reps"][:4]:
            returns = rep.get("returns", {})
            lines.append(
                f"| {row['segment']['name']} | {rep.get('name')} | {rep.get('quote')} | "
                f"{fmt_pct(returns.get('3M'))} | {fmt_pct(returns.get('1Y'))} | {fmt_num(rep.get('forward_pe'))} | "
                f"{fmt_num(rep.get('ev_to_ebitda'))} | {combined_crowding(rep)} |"
            )
    if not candidates:
        lines.append("| n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")
    lines.append("")

    lines.append("## 搜索热度线索")
    lines.append("")
    lines.append("这部分只反映搜索/新闻关键词，不自动等同于 emergent。若对应 segment 已经 Hot，会被排除在 Early 之外。")
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
    lines.append("这些不是推荐买入，只是当前观察池里“涨幅/估值没有明显爆掉”的复核对象。")
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

    lines.append("## 持仓映射")
    lines.append("")
    market_by_quote = {row.get("quote"): row for row in market_rows}
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
    lines.append("这张表是为了防止把已经涨完一大段、估值又很贵的方向误判成 emergent。Yahoo 没有提供未来两年一致预期时，先用公开 forward P/E 和 EV/EBITDA 近似；缺口会标出来。")
    lines.append("")
    lines.append("| 标的 | 代码 | 主题 | 最新日 | 1M | 3M | 1Y | Fwd P/E | TTM P/E | EV/EBITDA | EV/Sales | 综合 |")
    lines.append("|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|")
    sorted_rows = sorted(
        [row for row in market_rows if row.get("returns")],
        key=lambda row: (row["returns"].get("3M") if row["returns"].get("3M") is not None else -999),
        reverse=True,
    )
    for row in sorted_rows:
        returns = row.get("returns", {})
        themes = ",".join(row.get("themes", []))
        lines.append(
            f"| {row.get('name')} | {row.get('quote')} | {themes} | {row.get('date', 'n/a')} | "
            f"{fmt_pct(returns.get('1M'))} | {fmt_pct(returns.get('3M'))} | {fmt_pct(returns.get('1Y'))} | "
            f"{fmt_num(row.get('forward_pe'))} | {fmt_num(row.get('trailing_pe'))} | {fmt_num(row.get('ev_to_ebitda'))} | {fmt_num(row.get('ev_to_revenue'))} | {combined_crowding(row)} |"
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

    with open(output, "w", encoding="utf-8") as f:
        f.write(report)
    html_output = os.path.splitext(output)[0] + ".html"
    pdf_output = os.path.splitext(output)[0] + ".pdf"
    with open(html_output, "w", encoding="utf-8") as f:
        f.write(markdown_to_html(report, config.get("report_title", "AI Capex Radar")))
    pdf_ok = False
    try:
        pdf_ok = render_pdf(html_output, pdf_output)
    except Exception as exc:
        print(f"PDF export failed: {exc}")
    print(output)
    print(html_output)
    if pdf_ok:
        print(pdf_output)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
