"""
message_builder.py - 格式化 LINE 訊息
"""
from datetime import datetime
import pytz

_TZ = pytz.timezone("Asia/Taipei")

_SEP_THICK = "━━━━━━━━━━━━━━"
_SEP_THIN  = "─────────────"

# 與 etf_tracker.STALE 相同的哨兵值（避免循環 import）
_STALE = "STALE"


def _fmt_date(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%Y%m%d").strftime("%Y/%m/%d")
    except Exception:
        return date_str


def _fmt_lots(n: int) -> str:
    sign = "+" if n >= 0 else ""
    return f"{sign}{n:,} 張"


def _fmt_etf_lots(n: int) -> str:
    sign = "+" if n >= 0 else ""
    return f"{sign}{n:,}張"


def build_daily_report(
    date_str: str,
    institutional_records: list[dict],
    etf_results: list[tuple],
) -> str:
    lines = [
        "📋 每日報告",
        f"📅 {_fmt_date(date_str)}",
        _SEP_THICK,
        "",
    ]

    lines.append("【持股 - 三大法人進出】")
    for r in institutional_records:
        icon = "📈" if r["three_net"] >= 0 else "📉"
        lines.append(f"{icon} {r['name']}（{r['code']}）")
        if r["name"] == "（查無資料）":
            lines.append("⚠️ 今日無資料")
        else:
            lines.append(f"外資：{_fmt_lots(r['foreign_net'])}")
            lines.append(f"投信：{_fmt_lots(r['trust_net'])}")
            lines.append(f"自營商：{_fmt_lots(r['dealer_net'])}")
            lines.append(f"合計：{_fmt_lots(r['three_net'])}")
        lines.append(_SEP_THIN)

    lines.append("")
    lines.append("【主動型ETF - 持股變化】")

    for (etf_code, etf_name, diff) in etf_results:
        lines.append(f"📊 {etf_name}（{etf_code}）")

        if diff == _STALE:
            lines.append("⏳ 今日持股資料尚未更新")
            lines.append("（通常收盤後 1-2 小時才刷新）")
            lines.append(_SEP_THIN)
            continue

        if diff is None:
            lines.append("⚠️ 無法取得資料，請稍後重試")
            lines.append(_SEP_THIN)
            continue

        if not diff["added"] and not diff["removed"] and not diff["changed"]:
            if diff["top10"]:
                lines.append("（首次執行，顯示前 10 大持股）")
                for i, h in enumerate(diff["top10"], 1):
                    w = f"{h['weight']:.2f}%" if h.get("weight") else ""
                    lines.append(f"  {i:2d}. {h['name']}({h['code']}) {w}")
            else:
                lines.append("✅ 持股與前次相同，無變化")
            lines.append(_SEP_THIN)
            continue

        added = diff.get("added", [])
        if added:
            lines.append("加碼：")
            for h in added:
                lots = h.get("delta_lots") or (h.get("shares", 0) // 1000)
                lines.append(f"🟢{h['name']}({h['code']}){_fmt_etf_lots(lots)}")

        removed = diff.get("removed", [])
        if removed:
            lines.append("減碼：")
            for h in removed:
                lots = -(h.get("delta_lots") or (h.get("shares", 0) // 1000))
                lines.append(f"🔴{h['name']}({h['code']}){_fmt_etf_lots(lots)}")

        lines.append(_SEP_THIN)

    return "\n".join(lines)


def build_institutional_report(date_str: str, records: list[dict]) -> str:
    lines = [
        "📋 三大法人進出",
        f"📅 {_fmt_date(date_str)}",
        _SEP_THICK,
    ]
    for r in records:
        icon = "📈" if r["three_net"] >= 0 else "📉"
        lines.append(f"{icon} {r['name']}（{r['code']}）")
        if r["name"] == "（查無資料）":
            lines.append("⚠️ 今日無資料")
        else:
            lines.append(f"外資：{_fmt_lots(r['foreign_net'])}")
            lines.append(f"投信：{_fmt_lots(r['trust_net'])}")
            lines.append(f"自營商：{_fmt_lots(r['dealer_net'])}")
            lines.append(f"合計：{_fmt_lots(r['three_net'])}")
        lines.append(_SEP_THIN)
    lines.append("資料來源：台灣證券交易所")
    return "\n".join(lines)


def build_no_data_message(date_str: str) -> str:
    return (
        f"⚠️ {_fmt_date(date_str)} 查無三大法人資料\n"
        "可能是非交易日或資料尚未更新。\n"
        "格式：報告 YYYYMMDD"
    )


def build_etf_report(etf_code: str, etf_name: str, date_str: str, diff: dict) -> str:
    lines = [
        f"📊 {etf_name}（{etf_code}）",
        f"📅 {_fmt_date(date_str)}",
        _SEP_THICK,
    ]
    added   = diff.get("added", [])
    removed = diff.get("removed", [])

    if not added and not removed and not diff.get("changed"):
        if diff.get("top10"):
            lines.append("（首次執行，顯示前 10 大持股）")
            for i, h in enumerate(diff["top10"], 1):
                w = f"{h['weight']:.2f}%" if h.get("weight") else ""
                lines.append(f"  {i:2d}. {h['name']}({h['code']}) {w}")
        else:
            lines.append("✅ 持股無變化")
        return "\n".join(lines)

    if added:
        lines.append("加碼：")
        for h in added:
            lots = h.get("delta_lots") or (h.get("shares", 0) // 1000)
            lines.append(f"🟢{h['name']}({h['code']}){_fmt_etf_lots(lots)}")
    if removed:
        lines.append("減碼：")
        for h in removed:
            lots = -(h.get("delta_lots") or (h.get("shares", 0) // 1000))
            lines.append(f"🔴{h['name']}({h['code']}){_fmt_etf_lots(lots)}")

    return "\n".join(lines)


def build_etf_stale(etf_code: str, etf_name: str) -> str:
    """當今日持股資料尚未更新時顯示的訊息"""
    return (
        f"📊 {etf_name}（{etf_code}）\n"
        "⏳ 今日持股資料尚未更新\n"
        "通常在台股收盤後 1-2 小時才會刷新，請晚些再試。"
    )


def build_etf_error(etf_code: str, etf_name: str) -> str:
    return f"⚠️ {etf_code} {etf_name}\n無法取得持股資料，請稍後重試。"


def build_watchlist_message(stocks: list[str]) -> str:
    if not stocks:
        return "📋 追蹤清單是空的。\n使用「+2330」新增股票。"
    items = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(stocks))
    return f"📋 目前追蹤清單（{len(stocks)} 檔）：\n{items}"


HELP_TEXT = """🤖 台股法人追蹤 Bot 指令說明

【持股清單】
  +2330       新增股票（4-6碼）
  -2330       移除股票
  持股 / 清單  查看清單

【三大法人】
  今日         今日報告
  報告 20241201 指定日期
  2330         查詢單一股票

【ETF 持股】
  ETF          所有ETF持股變化
  ETF 00981A   指定ETF

【其他】
  我的ID       取得您的 LINE User ID
  說明 / help  顯示此說明"""
