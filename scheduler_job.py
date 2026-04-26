"""
scheduler_job.py - 每日 16:30 盤後報告

1. 確認今日是否為交易日
2. 取得持股三大法人進出
3. 取得 5 檔主動型 ETF 持股變化
4. 合併成一則 LINE Push Message 推播給使用者
"""
import logging
from datetime import datetime

import pytz
from linebot.v3.messaging import (
    ApiClient, Configuration, MessagingApi,
    PushMessageRequest, TextMessage,
)

from config import LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, TRACKED_ETFS
from etf_tracker import compare_holdings, fetch_etf_holdings
from message_builder import build_daily_report, build_no_data_message
from storage import get_etf_previous, load_watchlist
from twse_api import fetch_institutional, filter_watchlist, today_tw

logger = logging.getLogger(__name__)
_TZ = pytz.timezone("Asia/Taipei")
_line_config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)

_LINE_LIMIT = 4900  # LINE 單則訊息字元上限（留 100 餘量）


# ── 推播工具 ──────────────────────────────────────────────────────────────────

def _push(text: str) -> None:
    if not LINE_USER_ID:
        logger.warning("LINE_USER_ID 未設定，無法推播")
        return
    if not LINE_CHANNEL_ACCESS_TOKEN:
        logger.warning("LINE_CHANNEL_ACCESS_TOKEN 未設定，無法推播")
        return

    chunks = _split(text)
    with ApiClient(_line_config) as api_client:
        api = MessagingApi(api_client)
        for chunk in chunks:
            api.push_message(
                PushMessageRequest(
                    to=LINE_USER_ID,
                    messages=[TextMessage(text=chunk)],
                )
            )
    logger.info(f"Push sent ({len(chunks)} part(s))")


def _split(text: str, limit: int = _LINE_LIMIT) -> list[str]:
    """長訊息按行切割，確保每段 ≤ limit 字元"""
    if len(text) <= limit:
        return [text]
    parts, current = [], ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > limit:
            if current.strip():
                parts.append(current.rstrip())
            current = line
        else:
            current += line
    if current.strip():
        parts.append(current.rstrip())
    return parts or [text[:limit]]


# ── 每日報告主邏輯 ────────────────────────────────────────────────────────────

def run_daily_report() -> str:
    """
    建立並推播當日盤後報告。
    回傳執行狀態字串（供 HTTP 端點回應）。
    """
    date_str = today_tw()
    logger.info(f"Daily report start — {date_str}")

    # ── 三大法人 ─────────────────────────────────────────────────────────────
    watchlist = load_watchlist()
    inst_data = fetch_institutional(date_str)

    if inst_data is None:
        # 非交易日 → 只推一則說明，不執行 ETF
        _push(build_no_data_message(date_str))
        return f"non-trading-day:{date_str}"

    records = filter_watchlist(inst_data, watchlist)

    # ── ETF 持股變化 ─────────────────────────────────────────────────────────
    etf_results = []
    for etf in TRACKED_ETFS:
        code, name, company = etf["code"], etf["name"], etf["company"]
        prev = get_etf_previous(code)
        curr = fetch_etf_holdings(code, company, date_str)
        diff = compare_holdings(prev, curr) if curr is not None else None
        etf_results.append((code, name, diff))

    # ── 合併成一則（或分段）推播 ──────────────────────────────────────────────
    report = build_daily_report(date_str, records, etf_results)
    _push(report)

    logger.info("Daily report done.")
    return f"ok:{date_str}"


# ── APScheduler（本機測試用）────────────────────────────────────────────────

def start_scheduler() -> None:
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler(timezone=_TZ)
        scheduler.add_job(
            run_daily_report,
            trigger="cron",
            day_of_week="mon-fri",
            hour=16, minute=30,
            id="daily_report",
        )
        scheduler.start()
        logger.info("APScheduler: daily report at 16:30 (Mon-Fri, Taipei)")
    except ImportError:
        logger.warning("apscheduler not installed — using Render Cron Job")
