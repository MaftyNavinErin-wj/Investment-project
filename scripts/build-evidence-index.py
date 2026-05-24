import json
import os


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE = os.path.join(ROOT, "evidence")


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def scan_manifests(kind):
    base = os.path.join(EVIDENCE, kind)
    rows = []
    if not os.path.isdir(base):
        return rows
    for name in sorted(os.listdir(base)):
        path = os.path.join(base, name, "manifest.json")
        data = read_json(path)
        if data:
            rows.append(data)
    return rows


def main():
    sec = scan_manifests("sec")
    ir = scan_manifests("ir")
    transcripts = scan_manifests("transcripts")
    index = {
        "sec_company_count": len(sec),
        "sec_filing_count": sum(len(item.get("filings", [])) for item in sec),
        "ir_page_count": len(ir),
        "transcript_company_count": len(transcripts),
        "transcript_link_count": sum(len(item.get("links", [])) for item in transcripts),
        "sec": sec,
        "ir": ir,
        "transcripts": transcripts,
    }
    output = os.path.join(EVIDENCE, "index.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(output)


if __name__ == "__main__":
    main()
