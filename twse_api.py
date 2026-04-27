# -*- coding: utf-8 -*-
"""
twse_api.py - TWSE institutional investor API
Raw units are shares; divides by 1000 to convert to lots.
"""
import logging
from datetime import datetime
import pytz
import requests

logger = logging.getLogger(__name__)
_TZ = pytz.timezone("Asia/Taipei")
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.twse.com.tw/",
}

def today_tw() -> str:
    return datetime.now(_TZ).strftime("%Y%m%d")

def _raw_to_lots(s) -> int:
    try:
        return int(str(s).replace(",", "").replace("+", "").strip()) // 1000
    except (ValueError, AttributeError):
        return 0

def fetch_institutional(date_str: str | None = None) -> dict | None:
    if date_str is None:
        date_str = today_tw()
    url = (
        "https://www.twse.com.tw/fund/T86"
        f"?response=json&date={date_str}&selectType=ALLBUT0999"
    )
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        logger.error(f"TWSE T86 request failed ({date_str}): {e}")
        return None
    if payload.get("stat") != "OK" or not payload.get("data"):
        logger.info(f"TWSE T86: no data for {date_str}")
        return None
    result: dict[str, dict] = {}
    for row in payload["data"]:
        if len(row) < 18:
            continue
        code = row[0].strip()
        name = row[1].strip()
        foreign_net = _raw_to_lots(row[4])
        trust_net   = _raw_to_lots(row[10])
        dealer_net  = _raw_to_lots(row[13]) + _raw_to_lots(row[16])
        three_net   = foreign_net + trust_net + dealer_net
        result[code] = {
            "name": name,
            "foreign_buy":  _raw_to_lots(row[2]),
            "foreign_sell": _raw_to_lots(row[3]),
            "foreign_net":  foreign_net,
            "trust_buy":    _raw_to_lots(row[8]),
            "trust_sell":   _raw_to_lots(row[9]),
            "trust_net":    trust_net,
            "dealer_net":   dealer_net,
            "three_net":    three_net,
        }
    if not result:
        return None
    logger.info(f"TWSE T86: {len(result)} records for {date_str}")
    return result

def is_trading_day(date_str: str | None = None) -> bool:
    data = fetch_institutional(date_str)
    return data is not None and len(data) > 0

def filter_watchlist(data: dict, watchlist: list[str]) -> list[dict]:
    result = []
    for code in watchlist:
        if code in data:
            entry = data[code].copy()
            entry["code"] = code
            result.append(entry)
        else:
            result.append({
                "code": code, "name": "\u300e\u67e5\u7121\u8cc7\u6599\u300f",
                "foreign_net": 0, "trust_net": 0,
                "dealer_net": 0, "three_net": 0,
                "foreign_buy": 0, "foreign_sell": 0,
                "trust_buy": 0, "trust_sell": 0,
            })
    return result
