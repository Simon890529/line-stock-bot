"""
commands.py - 解析並處理 LINE 使用者傳來的指令
回傳純文字字串，由 app.py 發送給使用者。
"""
import logging
import re
from datetime import datetime

import pytz

from config import TRACKED_ETFS
from etf_tracker import STALE, compare_holdings, fetch_etf_holdings
from message_builder import (
    HELP_TEXT,
    build_etf_error,
    build_etf_report,
    build_etf_stale,
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


def _is_stock_code(text: str) -> bool:
    return bool(re.fullmatch(r"[0-9A-Za-z]{4,6}", text))


def _parse_date(text: str) -> str | None:
    text = text.strip().replace("/", "").replace("-", "").replace(".", "")
    if re.fullmatch(r"\d{8}", text):
        try:
            datetime.strptime(text, "%Y%m%d")
            return text
        except ValueError:
            return None
    return None


def _handle_etf_single(etf_code: str, date_str: str) -> str:
    etf_conf = next((e for e in TRACKED_ETFS if e["code"] == etf_code), None)
    if etf_conf is None:
        return f"⚠️ 未在設定清單中找到 ETF {etf_code}。"

    prev = get_etf_previous(etf_code)
    curr = fetch_etf_holdings(etf_code, etf_conf["company"], date_str)

    if curr == STALE:
        return build_etf_stale(etf_code, etf_conf["name"])
    if curr is None:
        return build_etf_error(etf_code, etf_conf["name"])

    diff = compare_holdings(prev, curr)
    return build_etf_report(etf_code, etf_conf["name"], date_str, diff)


def _handle_etf_all(date_str: str) -> str:
    parts = []
    for etf in TRACKED_ETFS:
        prev = get_etf_previous(etf["code"])
        curr = fetch_etf_holdings(etf["code"], etf["company"], date_str)
        if curr == STALE:
            parts.append(build_etf_stale(etf["code"], etf["name"]))
        elif curr is None:
            parts.append(build_etf_error(etf["code"], etf["name"]))
        else:
            diff = compare_holdings(prev, curr)
            parts.append(build_etf_report(etf["code"], etf["name"], date_str, diff))
    return "\n\n" + "─" * 20 + "\n\n".join(parts)


def _handle_institutional(date_str: str) -> str:
    watchlist = load_watchlist()
    data = fetch_institutional(date_str)
    if data is None:
        return build_no_data_message(date_str)
    records = filter_watchlist(data, watchlist)
    return build_institutional_report(date_str, records)


def _handle_single_stock(code: str, date_str: str) -> str:
    data = fetch_institutional(date_str)
    if data is None:
        return build_no_data_message(date_str)
    if code not in data:
        return f"⚠️ 在 {date_str} 的三大法人資料中查無股票代碼 {code}。"
    records = filter_watchlist(data, [code])
    return build_institutional_report(date_str, records)


def process_command(text: str, user_id: str) -> str | None:
    text_lower = text.lower().strip()
    today = today_tw()

    if text_lower in ("說明", "help", "指令", "?", "？"):
        return HELP_TEXT

    if text_lower in ("我的id", "我的 id", "my id", "id"):
        return f"您的 LINE User ID：\n{user_id}\n\n請將此 ID 設定到 Render 環境變數 LINE_USER_ID。"

    if text.startswith("+") and _is_stock_code(text[1:]):
        code = text[1:].upper()
        if add_stock(code):
            wl = load_watchlist()
            return f"✅ 已新增 {code} 到追蹤清單。\n目前共 {len(wl)} 檔。"
        else:
            return f"ℹ️ {code} 已在追蹤清單中。"

    if text.startswith("-") and _is_stock_code(text[1:]):
        code = text[1:].upper()
        if remove_stock(code):
            wl = load_watchlist()
            return f"✅ 已從追蹤清單移除 {code}。\n目前共 {len(wl)} 檔。"
        else:
            return f"ℹ️ {code} 不在追蹤清單中。"

    if text_lower in ("持股", "清單", "watchlist", "list"):
        return build_watchlist_message(load_watchlist())

    if text_lower in ("今日", "今天", "today", "報告", "三大法人"):
        return _handle_institutional(today)

    m = re.match(r"^(報告|查詢|法人)\s*(\S+)$", text)
    if m:
        d = _parse_date(m.group(2))
        if d:
            return _handle_institutional(d)
        return "⚠️ 日期格式有誤，請使用 YYYYMMDD，例如：報告 20241201"

    if _is_stock_code(text):
        code = text.upper()
        return _handle_single_stock(code, today)

    if text_lower in ("etf", "etf 全部", "所有etf"):
        return _handle_etf_all(today)

    m = re.match(r"^etf\s+(\S+)$", text_lower)
    if m:
        etf_code = m.group(1).upper()
        return _handle_etf_single(etf_code, today)

    return None
