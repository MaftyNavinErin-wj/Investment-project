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
    "PE_RATIO",
    "BEST_PE_RATIO",
    "CURRENT_EV_TO_T12M_EBITDA",
    "EV_TO_T12M_EBITDA",
    "BEST_CUR_EV_TO_EBITDA",
    "EV_TO_T12M_SALES",
    "PX_TO_BOOK_RATIO",
    "CURR_ENTP_VAL",
    "TRAIL_12M_EPS",
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
DEFAULT_NEWS = {
    "enabled": False,
    "mode": "reference_fields",
    "service": "//blp/refdata",
    "headline_fields": ["NEWS_HEADLINES"],
    "story_fields": ["NEWS_STORY"],
    "field_probe_security": "DELL US Equity",
    "field_probe_fields": [
        "NEWS_HEADLINES",
        "NEWS_STORY",
        "NEWS",
        "HEADLINE",
        "LAST_NEWS",
        "TOP_NEWS",
        "CN",
        "CN_STORIES",
        "BLOOMBERG_NEWS",
        "ALL_NEWS",
    ],
    "lookback_hours": 36,
    "max_results": 20,
    "queries": [],
    "latest_filename": "bloomberg_news_latest.json",
    "archive_filename_template": "bloomberg_news_{date}.json",
}
DEFAULT_FIELD_LOOKUP = {
    "service": "//blp/apiflds",
    "search_filename": "bloomberg_field_search_latest.json",
    "info_filename": "bloomberg_field_info_latest.json",
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
        values = {}
        for i in range(element.numElements()):
            child = element.getElement(i)
            try:
                if child.isComplexType() or child.isArray():
                    values[str(child.name())] = element_to_python(child)
                elif child.numValues() == 1:
                    values[str(child.name())] = json_safe(child.getValue())
                elif child.numValues() > 1:
                    values[str(child.name())] = [json_safe(child.getValue(j)) for j in range(child.numValues())]
                else:
                    values[str(child.name())] = str(child)
            except Exception:
                values[str(child.name())] = str(child)
        return values
    try:
        return json_safe(element.getValue())
    except Exception:
        return str(element)


def json_safe(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return str(value)


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


def apply_overrides(request, overrides):
    if not overrides:
        return
    override_element = request.getElement("overrides")
    for override in overrides:
        field_id = override.get("fieldId") or override.get("field_id")
        value = override.get("value")
        if not field_id or value is None:
            continue
        item = override_element.appendElement()
        item.setElement("fieldId", field_id)
        item.setElement("value", str(value))


def merge_reference_rows(base_rows, extra_rows):
    by_security = {row.get("security"): row for row in base_rows}
    for extra in extra_rows:
        security = extra.get("security")
        if security not in by_security:
            base_rows.append(extra)
            by_security[security] = extra
            continue
        target = by_security[security]
        target.setdefault("fields", {}).update(extra.get("fields", {}))
        target.setdefault("field_errors", []).extend(extra.get("field_errors", []))
        if extra.get("security_error") and not target.get("security_error"):
            target["security_error"] = extra.get("security_error")


def fields_for_security(item, default_fields, role_fields):
    role = item.get("role")
    if role and role in role_fields:
        return role_fields[role]
    return default_fields


def fetch_reference_data_grouped(securities, default_fields, request_config, host, port):
    role_fields = request_config.get("reference_fields_by_role") or {}
    groups = {}
    for item in securities:
        item_fields = fields_for_security(item, default_fields, role_fields)
        key = tuple(item_fields)
        groups.setdefault(key, []).append(item)

    rows = []
    messages = []
    for fields, items in groups.items():
        group_rows, group_messages = fetch_reference_data(items, list(fields), host, port)
        rows.extend(group_rows)
        messages.extend(group_messages)
    for override_request in request_config.get("reference_override_requests", []):
        override_fields = override_request.get("fields") or []
        field_prefix = override_request.get("field_prefix") or ""
        if not override_fields:
            continue
        eligible = [
            item for item in securities
            if item.get("role") not in {"macro_index", "rates", "fx", "commodity", "credit_spread"}
        ]
        if not eligible:
            continue
        group_rows, group_messages = fetch_reference_data_with_overrides(
            eligible,
            override_fields,
            override_request.get("overrides", []),
            field_prefix,
            host,
            port,
        )
        merge_reference_rows(rows, group_rows)
        messages.extend(group_messages)
    return rows, messages


def fetch_reference_data_with_overrides(securities, fields, overrides, field_prefix, host, port):
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
    apply_overrides(request, overrides)

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
                                row["fields"][f"{field_prefix}{field}"] = str(field_data.getElement(field).getValue())
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


def try_set_request_value(request, name, value):
    try:
        if request.hasElement(name):
            request.set(name, value)
            return True
    except Exception:
        return False
    return False


def force_set_request_value(request, name, value):
    if try_set_request_value(request, name, value):
        return True
    try:
        request.set(name, value)
        return True
    except Exception:
        pass
    try:
        request.setElement(name, value)
        return True
    except Exception:
        pass
    try:
        request.getElement(name).setValue(value)
        return True
    except Exception:
        pass
    return False


def try_append_request_value(request, name, value):
    try:
        if request.hasElement(name):
            request.getElement(name).appendValue(value)
            return True
    except Exception:
        return False
    return False


def force_append_request_value(request, name, value):
    if try_append_request_value(request, name, value):
        return True
    try:
        request.append(name, value)
        return True
    except Exception:
        pass
    try:
        request.getElement(name).appendValue(value)
        return True
    except Exception:
        pass
    return False


def request_element_names(request):
    names = []
    try:
        for i in range(request.numElements()):
            names.append(str(request.getElement(i).name()))
    except Exception:
        pass
    return names


def send_request_collect_raw(session, request, response_message_type=None):
    session.sendRequest(request)
    messages = []
    raw_payloads = []
    try:
        while True:
            event = session.nextEvent(30000)
            for msg in event:
                message_type = str(msg.messageType())
                messages.append(message_type)
                if response_message_type and message_type != response_message_type:
                    continue
                raw_payloads.append(element_to_python(msg.asElement()))
            if event.eventType() == blpapi.Event.RESPONSE:
                break
    except Exception as exc:
        raw_payloads.append({"error": str(exc)})
    return raw_payloads, messages


def open_api_fields_service(host, port):
    opts = blpapi.SessionOptions()
    opts.setServerHost(host)
    opts.setServerPort(port)
    session = blpapi.Session(opts)
    if not session.start():
        raise RuntimeError("session.start failed")
    service_name = DEFAULT_FIELD_LOOKUP["service"]
    if not session.openService(service_name):
        session.stop()
        raise RuntimeError(f"openService {service_name} failed")
    return session, session.getService(service_name)


def bloomberg_field_search(search_specs, host, port, max_results=50):
    session, service = open_api_fields_service(host, port)
    rows = []
    errors = []
    try:
        for spec in search_specs:
            try:
                request = service.createRequest("FieldSearchRequest")
                schema = request_element_names(request)
                configured = {}
                for name in ["searchSpec", "query", "text"]:
                    configured[name] = force_set_request_value(request, name, spec)
                for name in ["maxResults", "maxResultsCount"]:
                    configured[name] = force_set_request_value(request, name, int(max_results))
                for name in ["returnFieldDocumentation", "returnDocumentation"]:
                    configured[name] = force_set_request_value(request, name, True)
                raw_payloads, messages = send_request_collect_raw(session, request)
                rows.append(
                    {
                        "search": spec,
                        "request_schema": schema,
                        "configured": configured,
                        "message_types": messages,
                        "raw_response": raw_payloads,
                    }
                )
            except Exception as exc:
                errors.append(f"{spec}: {exc}")
    finally:
        session.stop()
    return {
        "service": DEFAULT_FIELD_LOOKUP["service"],
        "request_type": "FieldSearchRequest",
        "rows": rows,
        "errors": errors,
    }


def bloomberg_field_info(field_ids, host, port):
    session, service = open_api_fields_service(host, port)
    errors = []
    try:
        request = service.createRequest("FieldInfoRequest")
        schema = request_element_names(request)
        configured = {}
        for field_id in field_ids:
            appended = False
            for name in ["id", "ids", "fieldIds", "fields"]:
                appended = force_append_request_value(request, name, field_id) or appended
            configured[field_id] = appended
        raw_payloads, messages = send_request_collect_raw(session, request)
        return {
            "service": DEFAULT_FIELD_LOOKUP["service"],
            "request_type": "FieldInfoRequest",
            "request_schema": schema,
            "configured": configured,
            "field_ids": field_ids,
            "message_types": messages,
            "raw_response": raw_payloads,
            "errors": errors,
        }
    except Exception as exc:
        errors.append(str(exc))
        return {
            "service": DEFAULT_FIELD_LOOKUP["service"],
            "request_type": "FieldInfoRequest",
            "field_ids": field_ids,
            "errors": errors,
        }
    finally:
        session.stop()


def normalize_news_query(item):
    if isinstance(item, str):
        return {"name": item, "query": item}
    if isinstance(item, dict):
        query = item.get("query") or item.get("text") or item.get("name")
        if query:
            return {
                "name": item.get("name") or query,
                "query": query,
                "topics": item.get("topics", []),
                "securities": item.get("securities", []),
            }
    return None


def fetch_reference_field_payload(securities, fields, host, port):
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
    for security in securities:
        request.getElement("securities").appendValue(security)
    for field in fields:
        request.getElement("fields").appendValue(field)

    session.sendRequest(request)
    rows = []
    message_types = []
    try:
        while True:
            event = session.nextEvent(30000)
            for msg in event:
                message_types.append(str(msg.messageType()))
                if str(msg.messageType()) != "ReferenceDataResponse":
                    continue
                security_data = msg.getElement("securityData")
                for item in security_data.values():
                    security = item.getElementAsString("security")
                    row = {
                        "security": security,
                        "fields": {},
                        "field_errors": [],
                        "security_error": None,
                    }
                    if item.hasElement("securityError"):
                        row["security_error"] = element_to_python(item.getElement("securityError"))
                    if item.hasElement("fieldData"):
                        row["fields"] = element_to_python(item.getElement("fieldData"))
                    if item.hasElement("fieldExceptions"):
                        for field_exception in item.getElement("fieldExceptions").values():
                            row["field_errors"].append(element_to_python(field_exception))
                    rows.append(row)
            if event.eventType() == blpapi.Event.RESPONSE:
                break
    finally:
        session.stop()
    return rows, message_types


def collect_story_ids(value):
    ids = []

    def walk(node):
        if isinstance(node, dict):
            for key, val in node.items():
                key_lower = str(key).lower()
                if key_lower in {"story_id", "storyid", "storyId".lower(), "id"} and val:
                    ids.append(str(val))
                walk(val)
        elif isinstance(node, list):
            for val in node:
                walk(val)

    walk(value)
    seen = set()
    unique = []
    for story_id in ids:
        if story_id not in seen:
            seen.add(story_id)
            unique.append(story_id)
    return unique


def fetch_news_via_reference_fields(news_config, host, port):
    headline_fields = news_config.get("headline_fields") or DEFAULT_NEWS["headline_fields"]
    story_fields = news_config.get("story_fields") or DEFAULT_NEWS["story_fields"]
    max_results = int(news_config.get("max_results", DEFAULT_NEWS["max_results"]))
    queries = [normalize_news_query(item) for item in news_config.get("queries", [])]
    queries = [item for item in queries if item]
    securities = []
    for query in queries:
        securities.extend(query.get("securities", []))
    securities = list(dict.fromkeys([security for security in securities if security]))
    if not securities:
        return {
            "enabled": True,
            "mode": "reference_fields",
            "service": "//blp/refdata",
            "headline_fields": headline_fields,
            "story_fields": story_fields,
            "rows": [],
            "message_types": [],
            "errors": ["No news securities configured. NEWS_HEADLINES requires securities such as 'DELL US Equity'."],
        }

    headline_rows, headline_messages = fetch_reference_field_payload(securities, headline_fields, host, port)
    story_ids = []
    for row in headline_rows:
        for value in row.get("fields", {}).values():
            story_ids.extend(collect_story_ids(value))
    story_ids = list(dict.fromkeys(story_ids))[:max_results]

    story_rows = []
    story_messages = []
    story_errors = []
    if story_ids:
        try:
            story_rows, story_messages = fetch_reference_field_payload(story_ids, story_fields, host, port)
        except Exception as exc:
            story_errors.append(str(exc))

    errors = []
    for row in headline_rows + story_rows:
        if row.get("security_error") or row.get("field_errors"):
            errors.append(f"{row.get('security')}: security_error={row.get('security_error')} field_errors={row.get('field_errors')}")

    return {
        "enabled": True,
        "mode": "reference_fields",
        "service": "//blp/refdata",
        "headline_fields": headline_fields,
        "story_fields": story_fields,
        "securities": securities,
        "story_ids": story_ids,
        "headline_rows": headline_rows,
        "story_rows": story_rows,
        "rows": headline_rows,
        "message_types": headline_messages + story_messages,
        "errors": errors + story_errors,
    }


def probe_news_fields(news_config, host, port):
    security = news_config.get("field_probe_security") or DEFAULT_NEWS["field_probe_security"]
    fields = news_config.get("field_probe_fields") or DEFAULT_NEWS["field_probe_fields"]
    rows, messages = fetch_reference_field_payload([security], fields, host, port)
    valid_fields = []
    invalid_fields = []
    for row in rows:
        valid_fields.extend(list((row.get("fields") or {}).keys()))
        for error in row.get("field_errors", []):
            field_id = error.get("fieldId") if isinstance(error, dict) else None
            if field_id:
                invalid_fields.append(field_id)
    return {
        "enabled": True,
        "mode": "field_probe",
        "service": "//blp/refdata",
        "security": security,
        "fields": fields,
        "valid_fields": list(dict.fromkeys(valid_fields)),
        "invalid_fields": list(dict.fromkeys(invalid_fields)),
        "rows": rows,
        "message_types": messages,
        "errors": [
            f"No valid fields found for {security}. Try FLDS <GO> in Terminal for news/headline/story field discovery."
        ] if not valid_fields else [],
    }


def extract_news_items(message_payload):
    items = []

    def walk(node):
        if isinstance(node, dict):
            keys = {str(key).lower() for key in node.keys()}
            if {"headline", "storyid"} & keys or {"headline", "storyId"} & set(node.keys()):
                items.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(message_payload)
    return items


def fetch_news_data(news_config, host, port):
    if (news_config.get("mode") or DEFAULT_NEWS["mode"]) == "field_probe":
        return probe_news_fields(news_config, host, port)
    if (news_config.get("mode") or DEFAULT_NEWS["mode"]) == "reference_fields":
        return fetch_news_via_reference_fields(news_config, host, port)

    service_candidates = news_config.get("service_candidates") or [news_config.get("service") or DEFAULT_NEWS["service"]]
    request_type_candidates = news_config.get("request_type_candidates") or [news_config.get("request_type") or DEFAULT_NEWS["request_type"]]
    lookback_hours = int(news_config.get("lookback_hours", DEFAULT_NEWS["lookback_hours"]))
    max_results = int(news_config.get("max_results", DEFAULT_NEWS["max_results"]))
    end = dt.datetime.now()
    start = end - dt.timedelta(hours=lookback_hours)
    queries = [normalize_news_query(item) for item in news_config.get("queries", [])]
    queries = [item for item in queries if item]
    if not queries:
        return {
            "enabled": True,
            "service_candidates": service_candidates,
            "request_type_candidates": request_type_candidates,
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "rows": [],
            "message_types": [],
            "errors": ["No Bloomberg news queries configured."],
        }

    opts = blpapi.SessionOptions()
    opts.setServerHost(host)
    opts.setServerPort(port)
    session = blpapi.Session(opts)
    if not session.start():
        raise RuntimeError("session.start failed")

    rows = []
    errors = []
    message_types = []
    opened_service_name = None
    opened_request_type = None
    service = None
    try:
        for candidate_service in service_candidates:
            if not candidate_service:
                continue
            try:
                if not session.openService(candidate_service):
                    errors.append(f"openService {candidate_service} returned false")
                    continue
                candidate = session.getService(candidate_service)
                for candidate_request_type in request_type_candidates:
                    try:
                        probe = candidate.createRequest(candidate_request_type)
                        opened_service_name = candidate_service
                        opened_request_type = candidate_request_type
                        service = candidate
                        errors.append(
                            f"Selected Bloomberg news endpoint service={opened_service_name} request_type={opened_request_type} "
                            f"schema={request_element_names(probe)}"
                        )
                        break
                    except Exception as exc:
                        errors.append(f"{candidate_service}/{candidate_request_type}: createRequest failed: {exc}")
                if service:
                    break
            except Exception as exc:
                errors.append(f"{candidate_service}: open/get service failed: {exc}")
        if not service:
            return {
                "enabled": True,
                "service_candidates": service_candidates,
                "request_type_candidates": request_type_candidates,
                "start_datetime": start.isoformat(),
                "end_datetime": end.isoformat(),
                "lookback_hours": lookback_hours,
                "max_results": max_results,
                "rows": [],
                "message_types": message_types,
                "errors": errors,
            }

        for query in queries:
            try:
                request = service.createRequest(opened_request_type)
                request_schema = request_element_names(request)
                configured = {
                    "query": False,
                    "max_results": False,
                    "start": False,
                    "end": False,
                    "securities": False,
                    "topics": False,
                }

                for name in ["query", "searchString", "text", "searchText"]:
                    configured["query"] = try_set_request_value(request, name, query["query"]) or configured["query"]
                for name in ["maxResults", "maxResultsCount", "numberOfResults"]:
                    configured["max_results"] = try_set_request_value(request, name, max_results) or configured["max_results"]
                for name, value in [
                    ("startDateTime", start),
                    ("startDate", start.strftime("%Y%m%d")),
                    ("fromDateTime", start),
                    ("endDateTime", end),
                    ("endDate", end.strftime("%Y%m%d")),
                    ("toDateTime", end),
                ]:
                    bucket = "start" if "start" in name.lower() or "from" in name.lower() else "end"
                    configured[bucket] = try_set_request_value(request, name, value) or configured[bucket]
                for security in query.get("securities", []):
                    configured["securities"] = try_append_request_value(request, "securities", security) or configured["securities"]
                for topic in query.get("topics", []):
                    configured["topics"] = try_append_request_value(request, "topics", topic) or configured["topics"]

                session.sendRequest(request)
                messages = []
                raw_payloads = []
                extracted_items = []
                while True:
                    event = session.nextEvent(30000)
                    for msg in event:
                        message_types.append(str(msg.messageType()))
                        messages.append(str(msg.messageType()))
                        payload = element_to_python(msg.asElement())
                        raw_payloads.append(payload)
                        extracted_items.extend(extract_news_items(payload))
                    if event.eventType() == blpapi.Event.RESPONSE:
                        break

                rows.append(
                    {
                        "name": query["name"],
                        "query": query["query"],
                        "request_schema": request_schema,
                        "configured": configured,
                        "message_types": messages,
                        "items": extracted_items[:max_results],
                        "raw_response": raw_payloads,
                    }
                )
            except Exception as exc:
                errors.append(f"{query.get('name') or query.get('query')}: {exc}")
    finally:
        session.stop()

    return {
        "enabled": True,
        "service": opened_service_name,
        "request_type": opened_request_type,
        "service_candidates": service_candidates,
        "request_type_candidates": request_type_candidates,
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "lookback_hours": lookback_hours,
        "max_results": max_results,
        "rows": rows,
        "message_types": message_types,
        "errors": errors,
    }


def write_outputs(payload, output_dir, latest_filename, archive_template):
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    latest_path = target_dir / latest_filename
    archive_path = target_dir / archive_template.format(date=today)
    text = json.dumps(json_safe(payload), indent=2, ensure_ascii=False)
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
    parser.add_argument("--skip-news", action="store_true", help="Skip Bloomberg news export even if request enables it")
    parser.add_argument("--news-only", action="store_true", help="Only export Bloomberg news output")
    parser.add_argument("--field-search", nargs="+", default=None, help="Search Bloomberg API fields via //blp/apiflds")
    parser.add_argument("--field-info", nargs="+", default=None, help="Fetch Bloomberg API field metadata via //blp/apiflds")
    parser.add_argument("--field-max-results", default=50, type=int)
    args = parser.parse_args()

    request, securities, fields = load_request(args.request)
    output_dir = args.output_dir or request.get("output_dir") or DEFAULT_SHARE_DIR
    latest_filename = request.get("latest_filename", "bloomberg_snapshot_latest.json")
    archive_template = request.get("archive_filename_template", "bloomberg_snapshot_{date}.json")

    if args.field_search:
        payload = {
            "created_at": dt.datetime.now().isoformat(),
            "source": "Bloomberg API Field Search",
            "host": args.host,
            "port": args.port,
            **bloomberg_field_search(args.field_search, args.host, args.port, args.field_max_results),
        }
        latest_path, archive_path = write_outputs(
            payload,
            output_dir,
            DEFAULT_FIELD_LOOKUP["search_filename"],
            "bloomberg_field_search_{date}.json",
        )
        print(f"Wrote {latest_path}")
        print(f"Wrote {archive_path}")
        if payload.get("errors"):
            print(f"Field search errors: {len(payload['errors'])}")
            for err in payload["errors"][:20]:
                print(f"- {err}")
        return

    if args.field_info:
        payload = {
            "created_at": dt.datetime.now().isoformat(),
            "source": "Bloomberg API Field Info",
            "host": args.host,
            "port": args.port,
            **bloomberg_field_info(args.field_info, args.host, args.port),
        }
        latest_path, archive_path = write_outputs(
            payload,
            output_dir,
            DEFAULT_FIELD_LOOKUP["info_filename"],
            "bloomberg_field_info_{date}.json",
        )
        print(f"Wrote {latest_path}")
        print(f"Wrote {archive_path}")
        if payload.get("errors"):
            print(f"Field info errors: {len(payload['errors'])}")
            for err in payload["errors"][:20]:
                print(f"- {err}")
        return

    if not args.history_only and not args.news_only:
        rows, messages = fetch_reference_data_grouped(securities, fields, request, args.host, args.port)
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
    if historical_config.get("enabled", True) and not args.reference_only and not args.news_only:
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

    news_config = request.get("news") or DEFAULT_NEWS
    if (news_config.get("enabled", False) or args.news_only) and not args.skip_news and not args.reference_only and not args.history_only:
        try:
            news = fetch_news_data(news_config, args.host, args.port)
        except Exception as exc:
            news = {
                "enabled": True,
                "service": news_config.get("service", DEFAULT_NEWS["service"]),
                "service_candidates": news_config.get("service_candidates", DEFAULT_NEWS["service_candidates"]),
                "request_type": news_config.get("request_type", DEFAULT_NEWS["request_type"]),
                "request_type_candidates": news_config.get("request_type_candidates", DEFAULT_NEWS["request_type_candidates"]),
                "rows": [],
                "message_types": [],
                "errors": [str(exc)],
            }
        news_payload = {
            "created_at": dt.datetime.now().isoformat(),
            "source": "Bloomberg Desktop API News",
            "request_path": str(Path(args.request).resolve()),
            "host": args.host,
            "port": args.port,
            **news,
        }
        news_latest = news_config.get("latest_filename", DEFAULT_NEWS["latest_filename"])
        news_archive = news_config.get("archive_filename_template", DEFAULT_NEWS["archive_filename_template"])
        latest_path, archive_path = write_outputs(news_payload, output_dir, news_latest, news_archive)
        print(f"Wrote {latest_path}")
        print(f"Wrote {archive_path}")
        if news_payload.get("errors"):
            print(f"News export errors: {len(news_payload['errors'])}")
            for err in news_payload["errors"][:20]:
                print(f"- {err}")


if __name__ == "__main__":
    main()
