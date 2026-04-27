# -*- coding: utf-8 -*-
"""
commands.py - Parse and process LINE user commands
Returns plain text string; app.py sends it to the user.
"""
import logging
import re
from datetime import datetime

import pytz

from config import TRACKED_ETFS
from etf_tracker import compare_holdings, fetch_etf_holdings
from message_builder import (
    HELP_TEXT,
    build_etf_error,
    build_etf_report,
    build_institutional_report,
    build_no_data_message,
    build_watchlist_message,
)
from storage import (
    add_stock,
    get_etf_previous,
    load_watchlist,
    remove_stock,
)
from twse_api import fetch_institutional, filter_watchlist, today_tw

logger = logging.getLogger(__name__)
_TZ = pytz.timezone("Asia/Taipei")


# ── Utility functions ─────────────────────────────────────────────────────────

def _is_stock_code(text: str) -> bool:
    """Check if string is a Taiwan stock code (4-6 alphanumeric chars)"""
    return bool(re.fullmatch(r"[0-9A-Za-z]{4,6}", text))


def _parse_date(text: str) -> str | None:
    """Try to parse various date formats; return YYYYMMDD string"""
    text = text.strip().replace("/", "").replace("-", "").replace(".", "")
    if re.fullmatch(r"\d{8}", text):
        try:
            datetime.strptime(text, "%Y%m%d")
            return text
        except ValueError:
            return None
    return None


# ── ETF command handlers ──────────────────────────────────────────────────────

def _handle_etf_single(etf_code: str, date_str: str) -> str:
    etf_conf = next((e for e in TRACKED_ETFS if e["code"] == etf_code), None)
    if etf_conf is None:
        return f"\u26a0\ufe0f \u672a\u5728\u8a2d\u5b9a\u6e05\u55ae\u4e2d\u627e\u5230 ETF {etf_code}\u3002"

    prev = get_etf_previous(etf_code)
    curr = fetch_etf_holdings(etf_code, etf_conf["company"], date_str)

    if curr is None:
        return build_etf_error(etf_code, etf_conf["name"])

    diff = compare_holdings(prev, curr)
    return build_etf_report(etf_code, etf_conf["name"], date_str, diff)


def _handle_etf_all(date_str: str) -> str:
    parts = []
    for etf in TRACKED_ETFS:
        prev = get_etf_previous(etf["code"])
        curr = fetch_etf_holdings(etf["code"], etf["company"], date_str)
        if curr is None:
            parts.append(build_etf_error(etf["code"], etf["name"]))
        else:
            diff = compare_holdings(prev, curr)
            parts.append(build_etf_report(etf["code"], etf["name"], date_str, diff))

    return "\n\n" + "\u2500" * 20 + "\n\n".join(parts)


# ── Institutional investor command handlers ───────────────────────────────────

def _handle_institutional(date_str: str) -> str:
    watchlist = load_watchlist()
    data = fetch_institutional(date_str)
    if data is None:
        return build_no_data_message(date_str)
    records = filter_watchlist(data, watchlist)
    return build_institutional_report(date_str, records)


def _handle_single_stock(code: str, date_str: str) -> str:
    """Query institutional investor data for a single stock"""
    data = fetch_institutional(date_str)
    if data is None:
        return build_no_data_message(date_str)
    if code not in data:
        return f"\u26a0\ufe0f \u5728 {date_str} \u7684\u4e09\u5927\u6cd5\u4eba\u8cc7\u6599\u4e2d\u67e5\u7121\u80a1\u7968\u4ee3\u78bc {code}\u3002"
    records = filter_watchlist(data, [code])
    return build_institutional_report(date_str, records)


# ── Main command dispatcher ───────────────────────────────────────────────────

def process_command(text: str, user_id: str) -> str | None:
    """
    Parse user message; return reply string.
    Return None if command unrecognized (no reply sent).
    """
    text_lower = text.lower().strip()
    today = today_tw()

    # Help
    if text_lower in ("\u8aaa\u660e", "help", "\u6307\u4ee4", "?", "\uff1f"):
        return HELP_TEXT

    # My LINE User ID
    if text_lower in ("\u6211\u7684id", "\u6211\u7684 id", "my id", "id"):
        return f"\u60a8\u7684 LINE User ID\uff1a\n{user_id}\n\n\u8acb\u5c07\u6b64 ID \u8a2d\u5b9a\u5230 Render \u74b0\u5883\u8b8a\u6578 LINE_USER_ID\u3002"

    # Add stock
    if text.startswith("+") and _is_stock_code(text[1:]):
        code = text[1:].upper()
        if add_stock(code):
            wl = load_watchlist()
            return f"\u2705 \u5df2\u65b0\u589e {code} \u5230\u8ffd\u8e64\u6e05\u55ae\u3002\n\u76ee\u524d\u5171 {len(wl)} \u6a94\u3002"
        else:
            return f"\u2139\ufe0f {code} \u5df2\u5728\u8ffd\u8e64\u6e05\u55ae\u4e2d\u3002"

    # Remove stock
    if text.startswith("-") and _is_stock_code(text[1:]):
        code = text[1:].upper()
        if remove_stock(code):
            wl = load_watchlist()
            return f"\u2705 \u5df2\u5f9e\u8ffd\u8e64\u6e05\u55ae\u79fb\u9664 {code}\u3002\n\u76ee\u524d\u5171 {len(wl)} \u6a94\u3002"
        else:
            return f"\u2139\ufe0f {code} \u4e0d\u5728\u8ffd\u8e64\u6e05\u55ae\u4e2d\u3002"

    # Watchlist
    if text_lower in ("\u6301\u80a1", "\u6e05\u55ae", "watchlist", "list"):
        return build_watchlist_message(load_watchlist())

    # Today institutional data
    if text_lower in ("\u4eca\u65e5", "\u4eca\u5929", "today", "\u5831\u544a", "\u4e09\u5927\u6cd5\u4eba"):
        return _handle_institutional(today)

    # Institutional data by date
    m = re.match(r"^(\u5831\u544a|\u67e5\u8a62|\u6cd5\u4eba)\s*(\S+)$", text)
    if m:
        d = _parse_date(m.group(2))
        if d:
            return _handle_institutional(d)
        return "\u26a0\ufe0f \u65e5\u671f\u683c\u5f0f\u6709\u8aa4\uff0c\u8acb\u4f7f\u7528 YYYYMMDD\uff0c\u4f8b\u5982\uff1a\u5831\u544a 20241201"

    # Single stock query
    if _is_stock_code(text):
        code = text.upper()
        return _handle_single_stock(code, today)

    # ETF commands
    if text_lower in ("etf", "etf \u5168\u90e8", "\u6240\u6709etf"):
        return _handle_etf_all(today)

    m = re.match(r"^etf\s+(\S+)$", text_lower)
    if m:
        etf_code = m.group(1).upper()
        return _handle_etf_single(etf_code, today)

    # Unrecognized - return None (no reply)
    return None
