# -*- coding: utf-8 -*-
"""
scheduler_job.py - Daily 16:30 after-market report

1. Check if today is a trading day
2. Fetch watchlist institutional investor data
3. Fetch 5 active ETF holdings changes
4. Merge into a LINE Push Message and send to user
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

_LINE_LIMIT = 4900  # LINE message character limit (with 100 buffer)


# ── Push helper ───────────────────────────────────────────────────────────────

def _push(text: str) -> None:
    if not LINE_USER_ID:
        logger.warning("LINE_USER_ID not set, cannot push")
        return
    if not LINE_CHANNEL_ACCESS_TOKEN:
        logger.warning("LINE_CHANNEL_ACCESS_TOKEN not set, cannot push")
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
    """Split long messages by line, ensuring each chunk <= limit chars"""
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


# ── Daily report main logic ───────────────────────────────────────────────────

def run_daily_report() -> str:
    """
    Build and push daily after-market report.
    Returns status string for HTTP endpoint response.
    """
    date_str = today_tw()
    logger.info(f"Daily report start - {date_str}")

    # Institutional investors
    watchlist = load_watchlist()
    inst_data = fetch_institutional(date_str)

    if inst_data is None:
        # Non-trading day - push a brief notice
        _push(build_no_data_message(date_str))
        return f"non-trading-day:{date_str}"

    records = filter_watchlist(inst_data, watchlist)

    # ETF holdings changes
    etf_results = []
    for etf in TRACKED_ETFS:
        code, name, company = etf["code"], etf["name"], etf["company"]
        prev = get_etf_previous(code)
        curr = fetch_etf_holdings(code, company, date_str)
        diff = compare_holdings(prev, curr) if curr is not None else None
        etf_results.append((code, name, diff))

    # Merge and push
    report = build_daily_report(date_str, records, etf_results)
    _push(report)

    logger.info("Daily report done.")
    return f"ok:{date_str}"


# ── APScheduler (for local testing) ──────────────────────────────────────────

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
        logger.warning("apscheduler not installed - using Render Cron Job")
