# -*- coding: utf-8 -*-
"""etf_tracker.py - Active ETF holdings scraper"""
import csv, io, logging
from typing import Optional
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from bs4 import BeautifulSoup
from config import ETF_GSHEET_URLS
from storage import get_etf_previous, update_etf_cache
logger = logging.getLogger(__name__)
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
def _safe_float(s) -> float:
    try: return float(str(s).replace("%","").replace(",","").strip())
    except: return 0.0
def _safe_lots(s) -> int:
    try: return int(str(s).replace(",","").strip()) // 1000
    except: return 0
def _parse_table(soup, min_cols=3) -> list:
    table = soup.find("table")
    if not table: return []
    holdings = []
    for tr in table.find_all("tr")[1:]:
        tds = tr.find_all("td")
        if len(tds) < min_cols: continue
        code = tds[0].get_text(strip=True)
        name = tds[1].get_text(strip=True)
        shares = _safe_lots(tds[2].get_text(strip=True))
        weight = _safe_float(tds[3].get_text(strip=True)) if len(tds) > 3 else 0.0
        if code: holdings.append({"code": code, "name": name, "shares": shares, "weight": weight})
    return holdings
def _from_gsheet(etf_code: str) -> Optional[list]:
    url = ETF_GSHEET_URLS.get(etf_code)
    if not url: return None
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15, verify=False)
        resp.raise_for_status()
        reader = csv.DictReader(io.StringIO(resp.text))
        holdings = []
        for row in reader:
            code = row.get("\u4ee3\u865f", row.get("Code", "")).strip()
            name = row.get("\u540d\u7a31", row.get("Name", "")).strip()
            shares_raw = row.get("\u80a1\u6578", row.get("Shares", "0")).strip()
            weight = _safe_float(row.get("\u6b0a\u91cd", row.get("Weight", "0")))
            if not code: continue
            holdings.append({"code": code, "name": name, "shares": _safe_lots(shares_raw), "weight": weight})
        logger.info(f"GSheet {etf_code}: {len(holdings)} holdings")
        return holdings or None
    except Exception as e:
        logger.warning(f"GSheet {etf_code}: {e}")
        return None
def _scrape_capital(etf_code):
    try:
        resp = requests.get(f"https://www.capitalfund.com.tw/ETF/GetHolding?fundId={etf_code}", headers=_HEADERS, timeout=15, verify=False)
        data = resp.json()
        items = data if isinstance(data, list) else data.get("data", data.get("holdings", []))
        holdings = []
        for item in items:
            code = str(item.get("StockCode", item.get("stockCode", item.get("code","")))).strip()
            name = item.get("StockName", item.get("stockName", item.get("name","")))
            shares_raw = item.get("Shares", item.get("shares", item.get("holdingShares",0)))
            weight = float(item.get("Ratio", item.get("ratio", item.get("weight",0))) or 0)
            if code: holdings.append({"code":code,"name":name,"shares":_safe_lots(shares_raw),"weight":weight})
        if holdings: return holdings
    except: pass
    try:
        resp = requests.get(f"https://www.capitalfund.com.tw/ETFInfo?fundId={etf_code}", headers=_HEADERS, timeout=15, verify=False)
        holdings = _parse_table(BeautifulSoup(resp.text,"html.parser"))
        if holdings: return holdings
    except Exception as e:
        logger.warning(f"Capital {etf_code}: {e}")
    return None
def _scrape_president(etf_code):
    try:
        resp = requests.get(f"https://www.puif.com.tw/api/ETF/Holdings?code={etf_code}", headers=_HEADERS, timeout=15, verify=False)
        data = resp.json()
        items = data if isinstance(data, list) else data.get("data", [])
        holdings = []
        for item in items:
            code = str(item.get("stockCode", item.get("code",""))).strip()
            name = item.get("stockName", item.get("name",""))
            shares = _safe_lots(item.get("shares", item.get("holdingShares",0)))
            weight = float(item.get("ratio", item.get("weight",0)) or 0)
            if code: holdings.append({"code":code,"name":name,"shares":shares,"weight":weight})
        if holdings: return holdings
    except: pass
    try:
        resp = requests.get(f"https://www.puif.com.tw/products/ETFContent/{etf_code}", headers=_HEADERS, timeout=15, verify=False)
        holdings = _parse_table(BeautifulSoup(resp.text,"html.parser"))
        if holdings: return holdings
    except Exception as e:
        logger.warning(f"President {etf_code}: {e}")
    return None
def _scrape_fuh_hwa(etf_code):
    try:
        resp = requests.get(f"https://www.fuhwaetf.com.tw/api/etf/holdings?code={etf_code}", headers=_HEADERS, timeout=15, verify=False)
        data = resp.json()
        items = data if isinstance(data, list) else data.get("data", [])
        holdings = []
        for item in items:
            code = str(item.get("stockCode", item.get("code",""))).strip()
            name = item.get("stockName", item.get("name",""))
            shares = _safe_lots(item.get("shares",0))
            weight = float(item.get("ratio", item.get("weight",0)) or 0)
            if code: holdings.append({"code":code,"name":name,"shares":shares,"weight":weight})
        if holdings: return holdings
    except: pass
    try:
        resp = requests.get(f"https://www.fuhwaetf.com.tw/ETF/{etf_code}", headers=_HEADERS, timeout=15, verify=False)
        holdings = _parse_table(BeautifulSoup(resp.text,"html.parser"))
        if holdings: return holdings
    except Exception as e:
        logger.warning(f"Fuh-hwa {etf_code}: {e}")
    return None
def _scrape_allianz(etf_code):
    try:
        resp = requests.get(f"https://www.allianzgi.com.tw/api/etf/portfolio?code={etf_code}", headers=_HEADERS, timeout=15, verify=False)
        data = resp.json()
        items = data if isinstance(data, list) else data.get("data", data.get("holdings",[]))
        holdings = []
        for item in items:
            code = str(item.get("stockCode", item.get("code",""))).strip()
            name = item.get("stockName", item.get("name",""))
            shares = _safe_lots(item.get("shares",0))
            weight = float(item.get("ratio", item.get("weight",0)) or 0)
            if code: holdings.append({"code":code,"name":name,"shares":shares,"weight":weight})
        if holdings: return holdings
    except: pass
    try:
        resp = requests.get(f"https://www.allianzgi.com.tw/tw/etf/{etf_code.lower()}", headers=_HEADERS, timeout=15, verify=False)
        holdings = _parse_table(BeautifulSoup(resp.text,"html.parser"))
        if holdings: return holdings
    except Exception as e:
        logger.warning(f"Allianz {etf_code}: {e}")
    return None
def _scrape_yuanta(etf_code):
    try:
        resp = requests.get(f"https://www.yuantaetfs.com/api/get_etf_stockcomponent?strDate=&fundId={etf_code}", headers=_HEADERS, timeout=15, verify=False)
        data = resp.json()
        holdings = [{"code":str(i.get("stockCode","")),"name":i.get("stockName",""),"shares":_safe_lots(i.get("shareCount",0)),"weight":float(i.get("ratio",0) or 0)} for i in data.get("data",[])]
        return holdings or None
    except Exception as e:
        logger.warning(f"Yuanta {etf_code}: {e}")
        return None
def _scrape_general(etf_code):
    try:
        resp = requests.get(f"https://www.twse.com.tw/zh/ETF/fund/{etf_code}", headers=_HEADERS, timeout=15, verify=False)
        holdings = _parse_table(BeautifulSoup(resp.text,"html.parser"))
        if holdings: return holdings
    except Exception as e:
        logger.warning(f"General {etf_code}: {e}")
    return None
_SCRAPERS = {"capital": _scrape_capital, "president": _scrape_president, "fuh-hwa": _scrape_fuh_hwa, "allianz": _scrape_allianz, "yuanta": _scrape_yuanta, "fubon": _scrape_general, "cathay": _scrape_general, "ctbc": _scrape_general, "sinopac": _scrape_general, "general": _scrape_general}
def fetch_etf_holdings(etf_code, company, date_str):
    holdings = _from_gsheet(etf_code)
    if holdings:
        update_etf_cache(etf_code, date_str, holdings)
        return holdings
    scraper = _SCRAPERS.get(company.lower(), _scrape_general)
    holdings = scraper(etf_code)
    if holdings:
        update_etf_cache(etf_code, date_str, holdings)
        return holdings
    if scraper != _scrape_general:
        holdings = _scrape_general(etf_code)
        if holdings:
            update_etf_cache(etf_code, date_str, holdings)
            return holdings
    logger.warning(f"All scrapers failed for ETF {etf_code}")
    return None
def compare_holdings(prev, curr) -> dict:
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
    added.sort(key=lambda x: abs(x.get("delta_lots",0)), reverse=True)
    removed.sort(key=lambda x: abs(x.get("delta_lots",0)), reverse=True)
    return {"added": added, "removed": removed, "changed": changed, "top10": curr[:10]}
