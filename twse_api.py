"""
twse_api.py - 台灣證券交易所 (TWSE) 三大法人 API 串接
資料來源：https://www.twse.com.tw/fund/T86

TWSE T86 原始欄位（共 19 欄，index 0–18）：
 0  證券代號          1  證券名稱
 2  外陸資買進股數     3  外陸資賣出股數     4  外陸資買賣超股數
 5  外資自營商買進     6  外資自營商賣出     7  外資自營商買賣超
 8  投信買進股數       9  投信賣出股數      10  投信買賣超股數
11  自營商買賣超股數(合計)
12  自營商買進(自行)  13  自營商賣出(自行)  14  自營商買賣超(自行)
15  自營商買進(避險)  16  自營商賣出(避險)  17  自營商買賣超(避險)
18  三大法人買賣超股數

⚠️ 原始單位：股（股）。本模組一律 ÷1,000 轉換成「張」後儲存。
"""
import logging
from datetime import datetime

import urllib3
import pytz
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

_TZ = pytz.timezone("Asia/Taipei")
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
twse_api.py - 台灣證券交易所 (TWSE) 三大法人 API 串接
資料來源：https://www.twse.com.tw/fund/T86

TWSE T86 原始欄位（共 19 欄，index 0-18）：
 0  證券代號          1  證券名稱
 2  外陸資買進股數     3  外陸資賣出股數     4  外陸資買賣超股數
 5  外資自營商買進     6  外資自營商賣出     7  外資自營商買賣超
 8  投信買進股數       9  投信賣出股數      10  投信買賣超股數
11  自營商買賣超股數(合計)
12  自營商買進(自行)  13  自營商賣出(自行)  14  自營商買賣超(自行)
15  自營商買進(避險)  16  自營商賣出(避險)  17  自營商買賣超(避險)
18  三大法人買賣超股數

上櫃（TPEX）欄位對應（共 24 欄，index 0-23）：
  0  代號          1  名稱
  2  外資及陸資買進 3  賣出  4  買賣超
  5  外資自營商買進 6  賣出  7  買賣超
  8  外資合計買進   9  賣出  10 買賣超
 11  投信買進      12  賣出  13 買賣超
 14  自營(自行)買進 15 賣出  16 買賣超
 17  自營(避險)買進 18 賣出  19 買賣超
 20  自營合計買進  21  賣出  22 買賣超
 23  三大法人買賣超股數合計

⚠️ 原始單位：股。本模組一律 ÷1,000 轉換成「張」後儲存。
"""
import logging
from datetime import datetime

import urllib3
import pytz
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

_TPEX_URL = "https://www.tpex.org.tw/www/zh-tw/insti/dailyTrade"
_TPEX_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.tpex.org.tw/",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded",
}


def today_tw() -> str:
    return datetime.now(_TZ).strftime("%Y%m%d")


def _raw_to_lots(s) -> int:
    """原始字串（股）÷ 1000 → 張（整數）"""
    try:
        return int(str(s).replace(",", "").replace("+", "").strip()) // 1000
    except (ValueError, AttributeError):
        return 0


def _greg_to_roc(date_str: str) -> str:
    """YYYYMMDD → 民國年格式，例如 '20260427' → '115/4/27'"""
    year  = int(date_str[:4]) - 1911
    month = int(date_str[4:6])
    day   = int(date_str[6:8])
    return f"{year}/{month}/{day}"

def _fetch_tpex_institutional(date_str: str):
    """
    取得上櫃三大法人資料（TPEX POST API）。
    回傳：dict { 股票代號: {...} }  或 None
    """
    roc_date = _greg_to_roc(date_str)
    body = f"type=Daily&sect=AL&date={roc_date}&id="
    try:
        resp = requests.post(
            _TPEX_URL, data=body, headers=_TPEX_HEADERS, timeout=20, verify=False
        )
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        logger.error(f"TPEX dailyTrade request failed ({date_str}): {e}")
        return None

    tables = payload.get("tables", [])
    if not tables or not tables[0].get("data"):
        logger.info(f"TPEX dailyTrade: no data for {date_str}")
        return None

    result = {}
    for row in tables[0]["data"]:
        if len(row) < 24:
            continue
        code = row[0].strip()
        name = row[1].strip()
        result[code] = {
            "name":         name,
            "foreign_buy":  _raw_to_lots(row[2]),
            "foreign_sell": _raw_to_lots(row[3]),
            "foreign_net":  _raw_to_lots(row[4]),
            "trust_buy":    _raw_to_lots(row[11]),
            "trust_sell":   _raw_to_lots(row[12]),
            "trust_net":    _raw_to_lots(row[13]),
            "dealer_net":   _raw_to_lots(row[22]),
            "three_net":    _raw_to_lots(row[23]),
        }

    if not result:
        return None

    logger.info(f"TPEX dailyTrade: {len(result)} records for {date_str}")
    return result


def fetch_institutional(date_str=None):
    """
    取得三大法人資料（上市 + 上櫃合併）。
    回傳：dict { 股票代號: {..., 數字單位均為「張」} }
         或 None（非交易日 / 資料尚未更新）
    """
    if date_str is None:
        date_str = today_tw()

    url = (
        "https://www.twse.com.tw/fund/T86"
        f"?response=json&date={date_str}&selectType=ALLBUT0999"
    )
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=20, verify=False)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        logger.error(f"TWSE T86 request failed ({date_str}): {e}")
        return None

    if payload.get("stat") != "OK" or not payload.get("data"):
        logger.info(f"TWSE T86: no data for {date_str}")
        return None

    result = {}
    for row in payload["data"]:
        if len(row) < 18:
            continue
        code = row[0].strip()
        name = row[1].strip()

        foreign_net = _raw_to_lots(row[4])
        trust_net   = _raw_to_lots(row[10])

        if len(row) >= 19:
            dealer_net = _raw_to_lots(row[11])
            three_net  = _raw_to_lots(row[18])
        else:
            dealer_net = _raw_to_lots(row[13]) + _raw_to_lots(row[16])
            three_net  = _raw_to_lots(row[17])

        result[code] = {
            "name":         name,
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

    # 合併上櫃（TPEX）資料；任何例外均不影響上市結果
    try:
        tpex = _fetch_tpex_institutional(date_str)
        if tpex:
            result.update(tpex)
            logger.info(f"TPEX merged: {len(tpex)} records for {date_str}")
    except Exception as e:
        logger.error(f"TPEX merge failed, TWSE result unaffected: {e}")

    return result


def is_trading_day(date_str=None) -> bool:
    data = fetch_institutional(date_str)
    return data is not None and len(data) > 0


def filter_watchlist(data: dict, watchlist: list) -> list:
    """篩選持股清單；查無資料的股票補上佔位欄位"""
    result = []
    for code in watchlist:
        if code in data:
            entry = data[code].copy()
            entry["code"] = code
            result.append(entry)
        else:
            result.append({
                "code": code, "name": "（查無資料）",
                "foreign_net": 0, "trust_net": 0,
                "dealer_net": 0, "three_net": 0,
                "foreign_buy": 0, "foreign_sell": 0,
                "trust_buy": 0, "trust_sell": 0,
            })
    return result
