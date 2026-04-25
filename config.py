"""
config.py - 全域設定
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── LINE Bot ──────────────────────────────────────────────────────────────────
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET       = os.environ.get("LINE_CHANNEL_SECRET", "")
# 您個人的 LINE User ID（啟動 Bot 後傳送「我的ID」指令即可取得）
LINE_USER_ID              = os.environ.get("LINE_USER_ID", "")

# ── 時區 ──────────────────────────────────────────────────────────────────────
TIMEZONE = "Asia/Taipei"

# ── 預設追蹤持股（可透過 Line 指令調整，以逗號分隔）─────────────────────────
DEFAULT_WATCHLIST = [s.strip() for s in
                     os.environ.get("DEFAULT_WATCHLIST", "2454,2327,2330").split(",")
                     if s.strip()]

# ── 5 檔主動型 ETF 設定 ───────────────────────────────────────────────────────
# company 支援值：capital / president / fuh-hwa / allianz / yuanta / fubon / cathay / ctbc / general
TRACKED_ETFS = [
    {
        "code":    os.environ.get("ETF1_CODE",    "00981A"),
        "name":    os.environ.get("ETF1_NAME",    "主動統一台股增長"),
        "company": os.environ.get("ETF1_COMPANY", "president"),
    },
    {
        "code":    os.environ.get("ETF2_CODE",    "00982A"),
        "name":    os.environ.get("ETF2_NAME",    "主動群益台灣強棒"),
        "company": os.environ.get("ETF2_COMPANY", "capital"),
    },
    {
        "code":    os.environ.get("ETF3_CODE",    "00991A"),
        "name":    os.environ.get("ETF3_NAME",    "主動復華未來50"),
        "company": os.environ.get("ETF3_COMPANY", "fuh-hwa"),
    },
    {
        "code":    os.environ.get("ETF4_CODE",    "00992A"),
        "name":    os.environ.get("ETF4_NAME",    "主動群益科技創新"),
        "company": os.environ.get("ETF4_COMPANY", "capital"),
    },
    {
        "code":    os.environ.get("ETF5_CODE",    "00993A"),
        "name":    os.environ.get("ETF5_NAME",    "主動安聯台灣"),
        "company": os.environ.get("ETF5_COMPANY", "allianz"),
    },
]

# ── 若您已把 Excel 發佈為 Google Sheets CSV，可填入 URL 作為備援資料來源 ──────
# 格式：ETF代碼=CSV_URL，多筆以分號分隔
_raw_gsheet = os.environ.get("ETF_GSHEET_URLS", "")
ETF_GSHEET_URLS: dict[str, str] = {}
if _raw_gsheet:
    for pair in _raw_gsheet.split(";"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            ETF_GSHEET_URLS[k.strip()] = v.strip()

# ── 資料持久化目錄 ─────────────────────────────────────────────────────────────
DATA_DIR = os.environ.get("DATA_DIR", "./data")
