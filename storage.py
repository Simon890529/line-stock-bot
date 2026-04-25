"""
storage.py - JSON 檔案型資料持久化
存放路徑：DATA_DIR（預設 ./data/）
"""
import json
import os
from datetime import datetime

from config import DATA_DIR, DEFAULT_WATCHLIST

os.makedirs(DATA_DIR, exist_ok=True)

_WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlist.json")
_ETF_CACHE_FILE = os.path.join(DATA_DIR, "etf_cache.json")


# ── 持股清單 ──────────────────────────────────────────────────────────────────

def load_watchlist() -> list[str]:
    if os.path.exists(_WATCHLIST_FILE):
        try:
            with open(_WATCHLIST_FILE, encoding="utf-8") as f:
                return json.load(f).get("stocks", list(DEFAULT_WATCHLIST))
        except Exception:
            pass
    return list(DEFAULT_WATCHLIST)


def save_watchlist(stocks: list[str]) -> None:
    with open(_WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump({"stocks": stocks, "updated_at": datetime.now().isoformat()},
                  f, ensure_ascii=False, indent=2)


def add_stock(code: str) -> bool:
    """回傳 True 表示成功新增，False 表示已存在"""
    code = code.strip().upper()
    stocks = load_watchlist()
    if code in stocks:
        return False
    stocks.append(code)
    save_watchlist(stocks)
    return True


def remove_stock(code: str) -> bool:
    """回傳 True 表示成功移除，False 表示不存在"""
    code = code.strip().upper()
    stocks = load_watchlist()
    if code not in stocks:
        return False
    stocks.remove(code)
    save_watchlist(stocks)
    return True


# ── ETF 持股快取 ──────────────────────────────────────────────────────────────

def load_etf_cache() -> dict:
    if os.path.exists(_ETF_CACHE_FILE):
        try:
            with open(_ETF_CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_etf_cache(data: dict) -> None:
    with open(_ETF_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_etf_previous(etf_code: str) -> list[dict] | None:
    """取得上次快取的 ETF 持股列表"""
    cache = load_etf_cache()
    entry = cache.get(etf_code)
    if entry:
        return entry.get("holdings")
    return None


def update_etf_cache(etf_code: str, date_str: str, holdings: list[dict]) -> None:
    cache = load_etf_cache()
    cache[etf_code] = {
        "date": date_str,
        "holdings": holdings,
        "updated_at": datetime.now().isoformat(),
    }
    save_etf_cache(cache)
