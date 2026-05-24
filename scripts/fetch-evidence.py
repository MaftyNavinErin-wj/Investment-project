import argparse
import datetime as dt
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SOURCES = os.path.join(ROOT, "scripts", "evidence_sources.json")
DEFAULT_OUTPUT = os.path.join(ROOT, "evidence")
SEC_BASE = "https://www.sec.gov"
SEC_DATA = "https://data.sec.gov"
TRANSCRIPT_PATTERNS = re.compile(r"(transcript|earnings|results|quarter|webcast|presentation)", re.I)


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self._href = None
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        attrs = dict(attrs)
        self._href = attrs.get("href")
        self._text = []

    def handle_data(self, data):
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href:
            self.links.append({"href": self._href, "text": " ".join(self._text).strip()})
            self._href = None
            self._text = []


def safe_name(value):
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return value.strip("-") or "item"


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path, value):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)


def fetch(url, user_agent, timeout=20):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.headers.get_content_type()


def sec_submissions(cik, user_agent):
    cik10 = str(cik).zfill(10)
    url = f"{SEC_DATA}/submissions/CIK{cik10}.json"
    raw, _ = fetch(url, user_agent)
    return json.loads(raw.decode("utf-8", errors="replace"))


def recent_filings(submission, forms, since):
    recent = submission.get("filings", {}).get("recent", {})
    rows = []
    for idx, form in enumerate(recent.get("form", [])):
        filed = recent.get("filingDate", [""])[idx]
        if form not in forms or filed < since:
            continue
        accession = recent.get("accessionNumber", [""])[idx]
        doc = recent.get("primaryDocument", [""])[idx]
        rows.append(
            {
                "form": form,
                "filing_date": filed,
                "accession": accession,
                "primary_document": doc,
                "description": recent.get("primaryDocDescription", [""])[idx],
            }
        )
    return rows


def download_sec_company(company, output_dir, user_agent, forms, since, max_filings):
    ticker = company["ticker"]
    cik = str(company["cik"]).zfill(10)
    submission = sec_submissions(cik, user_agent)
    company_dir = os.path.join(output_dir, "sec", ticker)
    os.makedirs(company_dir, exist_ok=True)
    rows = recent_filings(submission, forms, since)[:max_filings]
    manifest = {
        "ticker": ticker,
        "name": company.get("name"),
        "cik": cik,
        "segments": company.get("segments", []),
        "downloaded_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "filings": rows,
    }
    for row in rows:
        accession_compact = row["accession"].replace("-", "")
        filename = safe_name(f"{row['filing_date']}-{row['form']}-{row['primary_document']}")
        url = f"{SEC_BASE}/Archives/edgar/data/{int(cik)}/{accession_compact}/{row['primary_document']}"
        row["url"] = url
        path = os.path.join(company_dir, filename)
        row["local_path"] = os.path.relpath(path, ROOT).replace("\\", "/")
        if os.path.exists(path):
            continue
        raw, content_type = fetch(url, user_agent)
        row["content_type"] = content_type
        with open(path, "wb") as f:
            f.write(raw)
        time.sleep(0.15)
    write_json(os.path.join(company_dir, "manifest.json"), manifest)
    return manifest


def download_ir_page(page, output_dir, user_agent):
    ticker = page["ticker"]
    company_dir = os.path.join(output_dir, "ir", ticker)
    os.makedirs(company_dir, exist_ok=True)
    raw, content_type = fetch(page["url"], user_agent)
    filename = safe_name(page["name"]) + ".html"
    path = os.path.join(company_dir, filename)
    with open(path, "wb") as f:
        f.write(raw)
    manifest = {
        "ticker": ticker,
        "name": page["name"],
        "url": page["url"],
        "content_type": content_type,
        "downloaded_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "local_path": os.path.relpath(path, ROOT).replace("\\", "/"),
    }
    write_json(os.path.join(company_dir, "manifest.json"), manifest)
    return manifest


def download_related_ir_links(page, html_bytes, output_dir, user_agent, max_links=8):
    parser = LinkParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    ticker = page["ticker"]
    out_dir = os.path.join(output_dir, "transcripts", ticker)
    os.makedirs(out_dir, exist_ok=True)
    seen = set()
    rows = []
    for link in parser.links:
        href = link.get("href") or ""
        text = link.get("text") or ""
        haystack = f"{href} {text}"
        if not TRANSCRIPT_PATTERNS.search(haystack):
            continue
        url = urllib.parse.urljoin(page["url"], href)
        if url in seen or not url.startswith("http"):
            continue
        seen.add(url)
        filename = safe_name(text or os.path.basename(urllib.parse.urlparse(url).path) or "ir-link")
        if not os.path.splitext(filename)[1]:
            filename += ".html"
        path = os.path.join(out_dir, filename[:120])
        try:
            raw, content_type = fetch(url, user_agent, timeout=12)
            with open(path, "wb") as f:
                f.write(raw)
            rows.append(
                {
                    "ticker": ticker,
                    "title": text,
                    "url": url,
                    "content_type": content_type,
                    "local_path": os.path.relpath(path, ROOT).replace("\\", "/"),
                }
            )
            time.sleep(0.15)
        except Exception as exc:
            rows.append({"ticker": ticker, "title": text, "url": url, "error": str(exc)})
        if len(rows) >= max_links:
            break
    if rows:
        write_json(os.path.join(out_dir, "manifest.json"), {"ticker": ticker, "links": rows})
    return rows


def main():
    parser = argparse.ArgumentParser(description="Download official evidence for the AI radar.")
    parser.add_argument("--sources", default=DEFAULT_SOURCES)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--months", type=int, default=12)
    parser.add_argument("--max-filings", type=int, default=8)
    parser.add_argument("--skip-ir", action="store_true")
    parser.add_argument("--skip-sec", action="store_true")
    parser.add_argument("--user-agent", default="investment-radar/0.1 contact@example.com")
    args = parser.parse_args()

    sources = read_json(args.sources)
    since = (dt.date.today() - dt.timedelta(days=31 * args.months)).isoformat()
    forms = {"10-K", "10-Q", "8-K", "20-F", "6-K"}
    summary = {"since": since, "sec": [], "ir": [], "errors": []}

    if not args.skip_sec:
        for company in sources.get("sec_companies", []):
            try:
                summary["sec"].append(download_sec_company(company, args.output, args.user_agent, forms, since, args.max_filings))
            except Exception as exc:
                summary["errors"].append(f"SEC {company.get('ticker')}: {exc}")

    if not args.skip_ir:
        for page in sources.get("ir_pages", []):
            try:
                manifest = download_ir_page(page, args.output, args.user_agent)
                summary["ir"].append(manifest)
                html_path = os.path.join(ROOT, manifest["local_path"])
                with open(html_path, "rb") as f:
                    html_bytes = f.read()
                summary.setdefault("transcripts", []).extend(download_related_ir_links(page, html_bytes, args.output, args.user_agent))
            except Exception as exc:
                summary["errors"].append(f"IR {page.get('ticker')}: {exc}")

    write_json(os.path.join(args.output, "manifest.json"), summary)
    print(os.path.join(args.output, "manifest.json"))
    if summary["errors"]:
        print("Errors:")
        for err in summary["errors"]:
            print(f"- {err}")


if __name__ == "__main__":
    main()
