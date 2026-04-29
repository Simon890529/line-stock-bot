"""
twse_api.py - å°ç£è­å¸äº¤ææ (TWSE) ä¸å¤§æ³äºº API ä¸²æ¥
è³æä¾æºï¼https://www.twse.com.tw/fund/T86

TWSE T86 åå§æ¬ä½ï¼å± 19 æ¬ï¼index 0â18ï¼ï¼
 0  è­å¸ä»£è          1  è­å¸åç¨±
 2  å¤é¸è³è²·é²è¡æ¸     3  å¤é¸è³è³£åºè¡æ¸     4  å¤é¸è³è²·è³£è¶è¡æ¸
 5  å¤è³èªçåè²·é²     6  å¤è³èªçåè³£åº     7  å¤è³èªçåè²·è³£è¶
 8  æä¿¡è²·é²è¡æ¸       9  æä¿¡è³£åºè¡æ¸      10  æä¿¡è²·è³£è¶è¡æ¸
11  èªçåè²·è³£è¶è¡æ¸(åè¨)
12  èªçåè²·é²(èªè¡)  13  èªçåè³£åº(èªè¡)  14  èªçåè²·è³£è¶(èªè¡)
15  èªçåè²·é²(é¿éª)  16  èªçåè³£åº(é¿éª)  17  èªçåè²·è³£è¶(é¿éª)
18  ä¸å¤§æ³äººè²·è³£è¶è¡æ¸

â ï¸ åå§å®ä½ï¼è¡ï¼è¡ï¼ãæ¬æ¨¡çµä¸å¾ Ã·1,000 è½ææãå¼µãå¾å²å­ã
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


def today_tw() -> str:
    return datetime.now(_TZ).strftime("%Y%m%d")


def _raw_to_lots(s) -> int:
    """åå§å­ä¸²ï¼è¡ï¼Ã· 1000 â å¼µï¼æ´æ¸ï¼"""
    try:
        return int(str(s).replace(",", "").replace("+", "").strip()) // 1000
    except (ValueError, AttributeError):
        return 0


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


def _greg_to_roc(date_str: str) -> str:
    """YYYYMMDD â æ°åå¹´æ ¼å¼ï¼ä¾å¦ '20260427' â '115/4/27'"""
    year  = int(date_str[:4]) - 1911
    month = int(date_str[4:6])
    day   = int(date_str[6:8])
    return f"{year}/{month}/{day}"


def _fetch_tpex_institutional(date_str: str) -> dict | None:
    """
    åå¾ä¸æ«ä¸å¤§æ³äººè³æï¼TPEX POST APIï¼ã
    åå³ï¼dict { è¡ç¥¨$»£è: {...} }  æ Noneï¼éäº¤ææ¥ / ç¡è³æ / é¯èª¤ï¼

    TPEX æ¬ä½å°æï¼å± 24 æ¬ï¼index 0â23ï¼ï¼
      0  ä»£è          1  åç¨±
      2  å¤è³åé¸è³è²·é² 3  è³£åº  4  è²·è³£è¶
      5  å¤è³èªçåè²·é² 6  è³£åº  7  è²·è³£è¶
      8  å¤è³åè¨è²·é²   9  è³£åº  10 è²·è³£è¶
     11  æä¿¡è²·é²      12  è³£åº  13 è²·è³£è¶
     14  èªç(èªè¡)è²·é² 15 è³£åº  16 è²·è³£è¶
     17  èªç(é¿éª)è²·é² 18 è³£åº  19 è²·è³£è¶
     20  èªçåè¨è²·é²  21  è³£åº  22 è²·è³£è¶
     23  ä¸å¤§æ³äººè²·è³£è¶è¡æ¸åè¨
    å®ä½ï¼è¡ï¼Ã·1000 â å¼µ
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

    result: dict[str, dict] = {}
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


def fetch_institutional(date_str: str | None = None) -> dict | None:
    """
    åå¾ä¸å¤§æ³äººè³æã
    åå³ï¼dict { è¡ç¥¨ä»£è: {..., æ¸å­å®ä½åçºãå¼µã} }
         æ Noneï¼éäº¤ææ¥ / è³æå°æªæ´æ°ï¼
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

    result: dict[str, dict] = {}
    for row in payload["data"]:
        if len(row) < 18:
            continue
        code = row[0].strip()
        name = row[1].strip()

        foreign_net = _raw_to_lots(row[4])
        trust_net   = _raw_to_lots(row[10])

        if len(row) >= 19:
            # æ°æ ¼å¼ï¼19 æ¬ï¼ï¼col[11] = èªçåè²·è³£è¶(åè¨)ï¼col[18] = ä¸å¤§æ³äººè²·è³£è¶
            dealer_net = _raw_to_lots(row[11])
            three_net  = _raw_to_lots(row[18])
        else:
            # èæ ¼å¼ï¼18 æ¬ï¼ï¼col[13] = èªè¡è¶ï¼col[16] = é¿éªè¶ï¼col[17] = ä¸å¤§æ³äººè¶
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

    # åä½µä¸æ«ï¼TPEXï¼è³æï¼ä»»ä½ä¾å¤åä¸å½±é¿ä¸å¸çµæ
    try:
        tpex = _fetch_tpex_institutional(date_str)
        if tpex:
            result.update(tpex)
            logger.info(f"TPEX merged: {len(tpex)} records for {date_str}")
    except Exception as e:
        logger.error(f"TPEX merge failed, TWSE result unaffected: {e}")

    return result


def is_trading_day(date_str: str | None = None) -> bool:
    data = fetch_institutional(date_str)
    return data is not None and len(data) > 0


def filter_watchlist(data: dict, watchlist: list[str]) -> list[dict]:
    """ç¯©é¸æè¡æ¸å®ï»~VþhÈK®KÙÎK.K®*X®ijîZØ¾i8ÞKÙÎK.i8ÞKÙÎYÞzjÈ®KØÒ"" ¢&W7VÇBÒµÐ¢f÷"6öFRâvF6Æ7C ¢b6öFRâFF ¢VçG'ÒFF¶6öFUÒæ6÷¢VçG'²&6öFR%ÒÒ6öFP¢&W7VÇBæVæBVçG'¢VÇ6S ¢&W7VÇBæVæB°¢&6öFR#¢6öFRÂ&æÖR#¢.ûÈiú^xJ8~iiûÈ"À¢&f÷&VvåöæWB#¢Â'G'W7EöæWB#¢À¢&FVÆW%öæWB#¢Â'F&VUöæWB#¢À¢&f÷&Vvåö'W#¢Â&f÷&Vvå÷6VÆÂ#¢À¢'G'W7Eö'W#¢Â'G'W7E÷6VÆÂ#¢À¢Ò¢&WGW&â&W7VÇ@
