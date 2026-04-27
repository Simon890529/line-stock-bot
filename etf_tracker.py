"""
etf_tracker.py - 主動型 ETF 持股爬蟲

支援的投信公司（company 設定值）：
  capital   群益投信  → 00982A 群益台灣強棒、00992A 群益科技創新
  president 統一投信  → 00981A 統一台股增長
  fuh-hwa   復華投信  → 00991A 復華未來50
  allianz   安聯投信  → 00993A 安聯台灣
  yuanta    元大投信
  fubon     富邦投信
  cathay    國泰投信
  ctbc      中信投信
  general   通用（TWSE 備援）

holdings 清單每筆格式：
  {
    "code":   str,
    "name":   str,
    "shares": int,
    "weight": float,
  }

compare_holdings 輸出多一個欄位 delta_lots（張數變化）。
"""
import csv
import io
import logging
from typing import Optional

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from config import ETF_GSHEET_URLS
from storage import get_etf_previous, update_etf_cache

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


def _safe_float(s) -> float:
    try:
        return float(str(s).replace("%", "").replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0.0


def _safe_lots(s) -> int:
    """原始股數字串 ÷ 1000 → 張（整數）"""
    try:
        raw = int(str(s).replace(",", "").strip())
        return raw // 1000
    except (ValueError, AttributeError):
        return 0


def _parse_table(soup, min_cols=3) -> list[dict]:
    table = soup.find("table")
    if not table:
        return []
    holdings = []
    for tr in table.find_all("tr")[1:]:
        tds = tr.find_all("td")
        if len(tds) < min_cols:
            continue
        code   = tds[0].get_text(strip=True)
        name   = tds[1].get_text(strip=True)
        shares = _safe_lots(tds[2].get_text(strip=True))
        weight = _safe_float(tds[3].get_text(strip=True)) if len(tds) > 3 else 0.0
        if code:
            holdings.append({"code": code, "name": name, "shares": shares, "weight": weight})
    return holdings


# ── pocket.tw API（主要來源）────────────────────────────────────────────────

_POCKET_URL = (
    "https://www.pocket.tw/api/cm/MobileService/ashx/GetDtnoData.ashx"
    "?action=getdtnodata&DtNo=59449513"
    "&ParamStr=AssignID%3D{code}%3BMTPeriod%3D0%3BDTMode%3D0%3BDTRange%3D1"
    "%3BDTOrder%3D1%3BMajorTable%3DM722%3B&FilterNo=0"
)


def _from_pockettw(etf_code: str) -> Optional[list[dict]]:
    """pocket.tw API — 回傳今日最新持股，欄位：[日期,代號,名稱,權重(%),持有數,單位]"""
    url = _POCKET_URL.format(code=etf_code)
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15, verify=False)
        resp.raise_for_status()
        data = resp.json()
        rows = data.get("Data", [])
        if not rows:
            logger.info(f"PocketTW {etf_code}: no data")
            return None
        holdings = []
        for row in rows:
            if len(row) < 5:
                continue
            code   = str(row[1]).strip()
            name   = str(row[2]).strip()
            weight = _safe_float(row[3])
            shares = _safe_lots(row[4])
            if not code:
                continue
            holdings.append({"code": code, "name": name, "shares": shares, "weight": weight})
        logger.info(f"PocketTW {etf_code}: {len(holdings)} holdings")
        return holdings or None
    except Exception as e:
        logger.warning(f"PocketTW {etf_code}: {e}")
        return None


# ── Google Sheets CSV 備援 ────────────────────────────────────────────────────

def _from_gsheet(etf_code: str) -> Optional[list[dict]]:
    url = ETF_GSHEET_URLS.get(etf_code)
    if not url:
        return None
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15, verify=False)
        resp.raise_for_status()
        text = resp.content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        holdings = []
        for row in reader:
            clean_row = {k.lstrip("\ufeff").strip(): v for k, v in row.items()}
            code       = clean_row.get("代號", clean_row.get("Code", "")).strip()
            name       = clean_row.get("名稱", clean_row.get("Name", "")).strip()
            shares_raw = clean_row.get("持有數", clean_row.get("股數", clean_row.get("Shares", "0"))).strip()
            weight     = _safe_float(clean_row.get("權重", clean_row.get("Weight", "0")))
            if not code or code in ("C_NTD", "CASH"):
                continue
            holdings.append({"code": code, "name": name, "shares": _safe_lots(shares_raw), "weight": weight})
        logger.info(f"GSheet {etf_code}: {len(holdings)} holdings")
        return holdings or None
    except Exception as e:
        logger.warning(f"GSheet {etf_code}: {e}")
        return None


# ── 群益投信（00982A, 00992A）────────────────────────────────────────────────

def _scrape_capital(etf_code: str) -> Optional[list[dict]]:
    url = f"https://www.capitalfund.com.tw/ETF/GetHolding?fundId={etf_code}"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15, verify=False)
        data = resp.json()
        items = data if isinstance(data, list) else data.get("data", data.get("holdings", []))
        holdings = []
        for item in items:
            code   = str(item.get("StockCode", item.get("stockCode", item.get("code", "")))).strip()
            name   = item.get("StockName", item.get("stockName", item.get("name", "")))
            shares_raw = item.get("Shares", item.get("shares", item.get("holdingShares", 0)))
            weight = float(item.get("Ratio", item.get("ratio", item.get("weight", 0))) or 0)
            if code:
                holdings.append({"code": code, "name": name, "shares": _safe_lots(shares_raw), "weight": weight})
        if holdings:
            return holdings
    except Exception:
        pass
    try:
        url2 = f"https://www.capitalfund.com.tw/ETFInfo?fundId={etf_code}"
        resp = requests.get(url2, headers=_HEADERS, timeout=15, verify=False)
        soup = BeautifulSoup(resp.text, "html.parser")
        holdings = _parse_table(soup)
        if holdings:
            return holdings
    except Exception as e:
        logger.warning(f"Capital {etf_code}: {e}")
    return None


def _scrape_president(etf_code: str) -> Optional[list[dict]]:
    url = f"https://www.puif.com.tw/api/ETF/Holdings?code={etf_code}"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15, verify=False)
        data = resp.json()
        items = data if isinstance(data, list) else data.get("data", [])
        holdings = []
        for item in items:
            code   = str(item.get("stockCode", item.get("code", ""))).strip()
            name   = item.get("stockName", item.get("name", ""))
            shares = _safe_lots(item.get("shares", item.get("holdingShares", 0)))
            weight = float(item.get("ratio", item.get("weight", 0)) or 0)
            if code:
                holdings.append({"code": code, "name": name, "shares": shares, "weight": weight})
        if holdings:
            return holdings
    except Exception:
        pass
    try:
        url2 = f"https://www.puif.com.tw/products/ETFContent/{etf_code}"
        resp = requests.get(url2, headers=_HEADERS, timeout=15, verify=False)
        soup = BeautifulSoup(resp.text, "html.parser")
        holdings = _parse_table(soup)
        if holdings:
            return holdings
    except Exception as e:
        logger.warning(f"President {etf_code}: {e}")
    return None


def _scrape_fuh_hwa(etf_code: str) -> Optional[list[dict]]:
    url = f"https://www.fuhwaetf.com.tw/api/etf/holdings?code={etf_code}"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15, verify=False)
        data = resp.json()
        items = data if isinstance(data, list) else data.get("data", [])
        holdings = []
        for item in items:
            code   = str(item.get("stockCode", item.get("code", ""))).strip()
            name   = item.get("stockName", item.get("name", ""))
            shares = _safe_lots(item.get("shares", 0))
            weight = float(item.get("ratio", item.get("weight", 0)) or 0)
            if code:
                holdings.append({"code": code, "name": name, "shares": shares, "weight": weight})
        if holdings:
            return holdings
    except Exception:
        pass
    try:
        url2 = f"https://www.fuhwaetf.com.tw/ETF/{etf_code}"
        resp = requests.get(url2, headers=_HEADERS, timeout=15, verify=False)
        soup = BeautifulSoup(resp.text, "html.parser")
        holdings = _parse_table(soup)
        if holdings:
            return holdings
    except Exception as e:
        logger.warning(f"Fuh-hwa {etf_code}: {e}")
    return None


def _scrape_allianz(etf_code: str) -> Optional[list[dict]]:
    url = f"https://www.allianzgi.com.tw/api/etf/portfolio?code={etf_code}"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15, verify=False)
        data = resp.json()
        items = data if isinstance(data, list) else data.get("data", data.get("holdings", []))
        holdings = []
        for item in items:
            code   = str(item.get("stockCode", item.get("code", ""))).strip()
            name   = item.get("stockName", item.get("name", ""))
            shares = _safe_lots(item.get("shares", 0))
            weight = float(item.get("ratio", item.get("weight", 0)) or 0)
            if code:
                holdings.append({"code": code, "name": name, "shares": shares, "weight": weight})
        if holdings:
            return holdings
    except Exception:
        pass
    try:
        url2 = f"https://www.allianzgi.com.tw/tw/etf/{etf_code.lower()}"
        resp = requests.get(url2, headers=_HEADERS, timeout=15, verify=False)
        soup = BeautifulSoup(resp.text, "html.parser")
        holdings = _parse_table(soup)
        if holdings:
            return holdings
    except Exception as e:
        logger.warning(f"Allianz {etf_code}: {e}")
    return None


def _scrape_yuanta(etf_code: str) -> Optional[list[dict]]:
    url = f"https://www.yuantaetfs.com/api/get_etf_stockcomponent?strDate=&fundId={etf_code}"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15, verify=False)
        data = resp.json()
        holdings = []
        for item in data.get("data", []):
            shares = _safe_lots(item.get("shareCount", 0))
            holdings.append({
                "code":   str(item.get("stockCode", "")),
                "name":   item.get("stockName", ""),
                "shares": shares,
                "weight": float(item.get("ratio", 0) or 0),
            })
        return holdings or None
    except Exception as e:
        logger.warning(f"Yuanta {etf_code}: {e}")
        return None


def _scrape_general(etf_code: str) -> Optional[list[dict]]:
    url = f"https://www.twse.com.tw/zh/ETF/fund/{etf_code}"
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15, verify=False)
        soup = BeautifulSoup(resp.text, "html.parser")
        holdings = _parse_table(soup)
        if holdings:
            logger.info(f"General {etf_code}: {len(holdings)} holdings")
            return holdings
    except Exception as e:
        logger.warning(f"General {etf_code}: {e}")
    return None


_SCRAPERS = {
    "capital":   _scrape_capital,
    "president": _scrape_president,
    "fuh-hwa":   _scrape_fuh_hwa,
    "allianz":   _scrape_allianz,
    "yuanta":    _scrape_yuanta,
    "fubon":     _scrape_general,
    "cathay":    _scrape_general,
    "ctbc":      _scrape_general,
    "sinopac":   _scrape_general,
    "general":   _scrape_general,
}


def fetch_etf_holdings(etf_code: str, company: str, date_str: str) -> Optional[list[dict]]:
    """取得 ETF 最新持股並更新快取（優先順序：pocket.tw → GSheet → 投信爬蟲）"""
    # 1. pocket.tw API（最可靠，五檔均支援）
    holdings = _from_pockettw(etf_code)
    if holdings:
        update_etf_cache(etf_code, date_str, holdings)
        return holdings

    # 2. Google Sheets CSV 備援
    holdings = _from_gsheet(etf_code)
    if holdings:
        update_etf_cache(etf_code, date_str, holdings)
        return holdings

    # 3. 投信專屬爬蟲
    scraper = _SCRAPERS.get(company.lower(), _scrape_general)
    holdings = scraper(etf_code)
    if holdings:
        update_etf_cache(etf_code, date_str, holdings)
        return holdings

    # 4. 通用 TWSE 備援
    if scraper != _scrape_general:
        holdings = _scrape_general(etf_code)
        if holdings:
            update_etf_cache(etf_code, date_str, holdings)
            return holdings

    logger.warning(f"All scrapers failed for ETF {etf_code}")
    return None


def compare_holdings(prev: list[dict] | None, curr: list[dict]) -> dict:
    if not prev:
        return {"added": [], "removed": [], "changed": [], "top10": curr[:10]}
    prev_map = {h["code"]: h for h in prev}
    curr_map = {h["code"]: h for h in curr}
    added = []
    for c in curr_map:
        if c not in prev_map:
            h = curr_map[c].copy(); h["delta_lots"] = h["shares"]; added.append(h)
    removed = []
    for c in prev_map:
        if c not in curr_map:
            h = prev_map[c].copy(); h["delta_lots"] = -h["shares"]; removed.append(h)
    changed = []
    for c in curr_map:
        if c in prev_map:
            delta = curr_map[c]["shares"] - prev_map[c]["shares"]
            if delta != 0:
                h = curr_map[c].copy(); h["prev_shares"] = prev_map[c]["shares"]; h["delta_lots"] = delta; changed.append(h)
    for h in changed:
        if h["delta_lots"] > 0: added.append(h)
        else: removed.append(h)
    added.sort(key=lambda x: abs(x.get("delta_lots", 0)), reverse=True)
    removed.sort(key=lambda x: abs(x.get("delta_lots", 0)), reverse=True)
    return {"added": added, "removed": removed, "changed": changed, "top10": curr[:10]}
