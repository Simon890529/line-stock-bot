# -*- coding: utf-8 -*-
"""config.py - Global settings"""
import os
from dotenv import load_dotenv

load_dotenv()

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET       = os.environ.get("LINE_CHANNEL_SECRET", "")
LINE_USER_ID              = os.environ.get("LINE_USER_ID", "")
TIMEZONE = "Asia/Taipei"
DEFAULT_WATCHLIST = [s.strip() for s in
                     os.environ.get("DEFAULT_WATCHLIST", "2454,2327,2330").split(",")
                     if s.strip()]

TRACKED_ETFS = [
    {"code": os.environ.get("ETF1_CODE","00981A"), "name": os.environ.get("ETF1_NAME","\u4e3b\u52d5\u7d71\u4e00\u53f0\u80a1\u589e\u9577"), "company": os.environ.get("ETF1_COMPANY","president")},
    {"code": os.environ.get("ETF2_CODE","00982A"), "name": os.environ.get("ETF2_NAME","\u4e3b\u52d5\u7fa4\u76ca\u53f0\u7063\u5f37\u68d2"), "company": os.environ.get("ETF2_COMPANY","capital")},
    {"code": os.environ.get("ETF3_CODE","00991A"), "name": os.environ.get("ETF3_NAME","\u4e3b\u52d5\u5fa9\u83ef\u672a\u4f8650"),       "company": os.environ.get("ETF3_COMPANY","fuh-hwa")},
    {"code": os.environ.get("ETF4_CODE","00992A"), "name": os.environ.get("ETF4_NAME","\u4e3b\u52d5\u7fa4\u76ca\u79d1\u6280\u5275\u65b0"), "company": os.environ.get("ETF4_COMPANY","capital")},
    {"code": os.environ.get("ETF5_CODE","00993A"), "name": os.environ.get("ETF5_NAME","\u4e3b\u52d5\u5b89\u806f\u53f0\u7063"),         "company": os.environ.get("ETF5_COMPANY","allianz")},
]

_raw_gsheet = os.environ.get("ETF_GSHEET_URLS", "")
ETF_GSHEET_URLS: dict[str, str] = {}
if _raw_gsheet:
    for pair in _raw_gsheet.split(";"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            ETF_GSHEET_URLS[k.strip()] = v.strip()

DATA_DIR = os.environ.get("DATA_DIR", "./data")
