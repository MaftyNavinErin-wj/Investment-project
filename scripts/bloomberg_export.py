import argparse
import datetime as dt
import json
import os
from pathlib import Path

import blpapi


DEFAULT_SHARE_DIR = r"\\primavera.local\primavera.local\shared\Beijing\Shared Documentation\bloomberg\Jie"
DEFAULT_FIELDS = [
    "PX_LAST",
    "CUR_MKT_CAP",
    "BEST_PE_RATIO",
    "EV_TO_T12M_EBITDA",
    "EV_TO_T12M_SALES",
    "CHG_PCT_1M",
    "CHG_PCT_3M",
    "CHG_PCT_6M",
    "CHG_PCT_1YR",
]
DEFAULT_HISTORICAL = {
    "enabled": True,
    "fields": ["PX_LAST"],
    "lookback_days": 370,
    "periodicitySelection": "DAILY",
    "nonTradingDayFillOption": "NON_TRADING_WEEKDAYS",
    "nonTradingDayFillMethod": "PREVIOUS_VALUE",
    "latest_filename": "bloomberg_history_latest.json",
    "archive_filename_template": "bloomberg_history_{date}.json",
}


def load_request(path):
    with open(path, "r", encoding="utf-8") as f:
        request = json.load(f)
    securities = request.get("securities") or []
    fields = request.get("reference_fields") or DEFAULT_FIELDS
    if not securities:
        raise ValueError(f"No securities found in {path}")
    return request, securities, fields


def element_to_python(element):
    if element.isArray():
        return [element_to_python(element.getValueAsElement(i)) for i in range(element.numValues())]
    if element.isComplexType():
        return {
            str(element.getElement(i).name()): element_to_python(element.getElement(i))
            for i in range(element.numElements())
        }
    try:
        return element.getValue()
    except Exception:
        return str(element)


def fetch_reference_data(securities, fields, host, port):
    opts = blpapi.SessionOptions()
    opts.setServerHost(host)
    opts.setServerPort(port)
    session = blpapi.Session(opts)
    if not session.start():
        raise RuntimeError("session.start failed")
    if not session.openService("//blp/refdata"):
        session.stop()
        raise RuntimeError("openService //blp/refdata failed")

    service = session.getService("//blp/refdata")
    request = service.createRequest("ReferenceDataRequest")
    security_meta = {}
    for item in securities:
        security = item["security"]
        security_meta[security] = item
        request.getElement("securities").appendValue(security)
    for field in fields:
        request.getElement("fields").appendValue(field)

    session.sendRequest(request)
    rows = []
    messages = []
    try:
        while True:
            event = session.nextEvent(30000)
            for msg in event:
                messages.append(str(msg.messageType()))
                if str(msg.messageType()) != "ReferenceDataResponse":
                    continue
                security_data = msg.getElement("securityData")
                for item in security_data.values():
                    security = item.getElementAsString("security")
                    row = {
                        "name": security_meta.get(security, {}).get("name"),
                        "quote": security_meta.get(security, {}).get("quote"),
                        "security": security,
                        "fields": {},
                        "field_errors": [],
                        "security_error": None,
                    }
                    if item.hasElement("securityError"):
                        row["security_error"] = element_to_python(item.getElement("securityError"))
                    if item.hasElement("fieldData"):
                        field_data = item.getElement("fieldData")
                        for field in fields:
                            if field_data.hasElement(field):
                                row["fields"][field] = str(field_data.getElement(field).getValue())
                    if item.hasElement("fieldExceptions"):
                        for field_exception in item.getElement("fieldExceptions").values():
                            row["field_errors"].append(element_to_python(field_exception))
                    rows.append(row)
            if event.eventType() == blpapi.Event.RESPONSE:
                break
    finally:
        session.stop()
    return rows, messages


def set_request_element(request, name, value):
    if value is not None:
        request.set(name, value)


def fetch_historical_data(securities, historical_config, host, port):
    fields = historical_config.get("fields") or ["PX_LAST"]
    lookback_days = int(historical_config.get("lookback_days", 370))
    end = dt.date.today()
    start = end - dt.timedelta(days=lookback_days)

    opts = blpapi.SessionOptions()
    opts.setServerHost(host)
    opts.setServerPort(port)
    session = blpapi.Session(opts)
    if not session.start():
        raise RuntimeError("session.start failed")
    if not session.openService("//blp/refdata"):
        session.stop()
        raise RuntimeError("openService //blp/refdata failed")

    service = session.getService("//blp/refdata")
    request = service.createRequest("HistoricalDataRequest")
    security_meta = {}
    for item in securities:
        security = item["security"]
        security_meta[security] = item
        request.getElement("securities").appendValue(security)
    for field in fields:
        request.getElement("fields").appendValue(field)

    request.set("startDate", start.strftime("%Y%m%d"))
    request.set("endDate", end.strftime("%Y%m%d"))
    set_request_element(request, "periodicitySelection", historical_config.get("periodicitySelection", "DAILY"))
    set_request_element(request, "nonTradingDayFillOption", historical_config.get("nonTradingDayFillOption"))
    set_request_element(request, "nonTradingDayFillMethod", historical_config.get("nonTradingDayFillMethod"))

    session.sendRequest(request)
    rows = []
    messages = []
    try:
        while True:
            event = session.nextEvent(30000)
            for msg in event:
                messages.append(str(msg.messageType()))
                if str(msg.messageType()) != "HistoricalDataResponse":
                    continue
                security_data = msg.getElement("securityData")
                security = security_data.getElementAsString("security")
                row = {
                    "name": security_meta.get(security, {}).get("name"),
                    "quote": security_meta.get(security, {}).get("quote"),
                    "security": security,
                    "field_exceptions": [],
                    "security_error": None,
                    "field_data": [],
                }
                if security_data.hasElement("securityError"):
                    row["security_error"] = element_to_python(security_data.getElement("securityError"))
                if security_data.hasElement("fieldExceptions"):
                    for field_exception in security_data.getElement("fieldExceptions").values():
                        row["field_exceptions"].append(element_to_python(field_exception))
                if security_data.hasElement("fieldData"):
                    for point in security_data.getElement("fieldData").values():
                        item = {}
                        if point.hasElement("date"):
                            item["date"] = str(point.getElement("date").getValue())
                        for field in fields:
                            if point.hasElement(field):
                                item[field] = str(point.getElement(field).getValue())
                        row["field_data"].append(item)
                rows.append(row)
            if event.eventType() == blpapi.Event.RESPONSE:
                break
    finally:
        session.stop()
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "fields": fields,
        "rows": rows,
        "message_types": messages,
    }


def write_outputs(payload, output_dir, latest_filename, archive_template):
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    latest_path = target_dir / latest_filename
    archive_path = target_dir / archive_template.format(date=today)
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    latest_path.write_text(text, encoding="utf-8")
    archive_path.write_text(text, encoding="utf-8")
    return latest_path, archive_path


def main():
    parser = argparse.ArgumentParser(description="Export Bloomberg Desktop API reference data for AI Capex Radar.")
    parser.add_argument("--request", default="bloomberg_request.json", help="Path to bloomberg_request.json")
    parser.add_argument("--output-dir", default=None, help="Output folder; defaults to request output_dir or share drive")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8194, type=int)
    parser.add_argument("--reference-only", action="store_true", help="Only export ReferenceDataRequest output")
    parser.add_argument("--history-only", action="store_true", help="Only export HistoricalDataRequest output")
    args = parser.parse_args()

    request, securities, fields = load_request(args.request)
    output_dir = args.output_dir or request.get("output_dir") or DEFAULT_SHARE_DIR
    latest_filename = request.get("latest_filename", "bloomberg_snapshot_latest.json")
    archive_template = request.get("archive_filename_template", "bloomberg_snapshot_{date}.json")

    if not args.history_only:
        rows, messages = fetch_reference_data(securities, fields, args.host, args.port)
        payload = {
            "created_at": dt.datetime.now().isoformat(),
            "source": "Bloomberg Desktop API",
            "request_path": str(Path(args.request).resolve()),
            "host": args.host,
            "port": args.port,
            "fields": fields,
            "message_types": messages,
            "rows": rows,
        }
        latest_path, archive_path = write_outputs(payload, output_dir, latest_filename, archive_template)
        print(f"Wrote {latest_path}")
        print(f"Wrote {archive_path}")
        bad = [row for row in rows if row.get("security_error") or row.get("field_errors")]
        if bad:
            print(f"Reference rows with Bloomberg errors: {len(bad)}")
            for row in bad[:20]:
                print(f"- {row.get('security')} security_error={row.get('security_error')} field_errors={row.get('field_errors')}")

    historical_config = request.get("historical") or DEFAULT_HISTORICAL
    if historical_config.get("enabled", True) and not args.reference_only:
        history = fetch_historical_data(securities, historical_config, args.host, args.port)
        history_payload = {
            "created_at": dt.datetime.now().isoformat(),
            "source": "Bloomberg Desktop API",
            "request_path": str(Path(args.request).resolve()),
            "host": args.host,
            "port": args.port,
            **history,
        }
        hist_latest = historical_config.get("latest_filename", "bloomberg_history_latest.json")
        hist_archive = historical_config.get("archive_filename_template", "bloomberg_history_{date}.json")
        latest_path, archive_path = write_outputs(history_payload, output_dir, hist_latest, hist_archive)
        print(f"Wrote {latest_path}")
        print(f"Wrote {archive_path}")
        bad = [row for row in history["rows"] if row.get("security_error") or row.get("field_exceptions")]
        if bad:
            print(f"Historical rows with Bloomberg errors: {len(bad)}")
            for row in bad[:20]:
                print(f"- {row.get('security')} security_error={row.get('security_error')} field_exceptions={row.get('field_exceptions')}")


if __name__ == "__main__":
    main()
