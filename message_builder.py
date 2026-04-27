# -*- coding: utf-8 -*-
"""message_builder.py - Format LINE messages"""
from datetime import datetime
import pytz
_TZ = pytz.timezone("Asia/Taipei")
_SEP_THICK = "━━━━━━━━━━━━━━"
_SEP_THIN  = "─────────────"

def _fmt_date(date_str: str) -> str:
    try:
        return datetime.strptime(date_str, "%Y%m%d").strftime("%Y/%m/%d")
    except Exception:
        return date_str

def _fmt_lots(n: int) -> str:
    sign = "+" if n >= 0 else ""
    return f"{sign}{n:,} \u5f35"

def _fmt_etf_lots(n: int) -> str:
    sign = "+" if n >= 0 else ""
    return f"{sign}{n:,}\u5f35"

def build_daily_report(date_str, institutional_records, etf_results) -> str:
    lines = [
        "\U0001f4cb \u6bcf\u65e5\u5831\u544a",
        f"\U0001f4c5 {_fmt_date(date_str)}",
        _SEP_THICK, "",
    ]
    lines.append("\u3010\u6301\u80a1 - \u4e09\u5927\u6cd5\u4eba\u9032\u51fa\u3011")
    for r in institutional_records:
        icon = "\U0001f4c8" if r["three_net"] >= 0 else "\U0001f4c9"
        lines.append(f"{icon} {r['name']}\uff08{r['code']}\uff09")
        if r["name"] == "NO_DATA":
            lines.append("\u26a0\ufe0f \u4eca\u65e5\u7121\u8cc7\u6599")
        else:
            lines.append(f"\u5916\u8cc7\uff1a{_fmt_lots(r['foreign_net'])}")
            lines.append(f"\u6295\u4fe1\uff1a{_fmt_lots(r['trust_net'])}")
            lines.append(f"\u81ea\u71df\u5546\uff1a{_fmt_lots(r['dealer_net'])}")
            lines.append(f"\u5408\u8a08\uff1a{_fmt_lots(r['three_net'])}")
        lines.append(_SEP_THIN)
    lines.append("")
    lines.append("\u3010\u4e3b\u52d5\u578bETF - \u6301\u80a1\u8b8a\u5316\u3011")
    for (etf_code, etf_name, diff) in etf_results:
        lines.append(f"\U0001f4ca {etf_name}\uff08{etf_code}\uff09")
        if diff is None:
            lines.append("\u26a0\ufe0f \u7121\u6cd5\u53d6\u5f97\u8cc7\u6599\uff0c\u8acb\u7a0d\u5f8c\u91cd\u8a66")
            lines.append(_SEP_THIN)
            continue
        if not diff["added"] and not diff["removed"] and not diff["changed"]:
            if diff["top10"]:
                lines.append("\uff08\u9996\u6b21\u57f7\u884c\uff0c\u986f\u793a\u524d 10 \u5927\u6301\u80a1\uff09")
                for i, h in enumerate(diff["top10"], 1):
                    w = f"{h['weight']:.2f}%" if h.get("weight") else ""
                    lines.append(f"  {i:2d}. {h['name']}({h['code']}) {w}")
            else:
                lines.append("\u2705 \u6301\u80a1\u8207\u524d\u6b21\u76f8\u540c\uff0c\u7121\u8b8a\u5316")
            lines.append(_SEP_THIN)
            continue
        added = diff.get("added", [])
        if added:
            lines.append("\u52a0\u78bc\uff1a")
            for h in added:
                lots = h.get("delta_lots") or (h.get("shares", 0) // 1000)
                lines.append(f"\U0001f7e2{h['name']}({h['code']}){_fmt_etf_lots(lots)}")
        removed = diff.get("removed", [])
        if removed:
            lines.append("\u6e1b\u78bc\uff1a")
            for h in removed:
                lots = -(h.get("delta_lots") or (h.get("shares", 0) // 1000))
                lines.append(f"\U0001f534{h['name']}({h['code']}){_fmt_etf_lots(lots)}")
        lines.append(_SEP_THIN)
    return "\n".join(lines)

def build_institutional_report(date_str, records) -> str:
    lines = [
        "\U0001f4cb \u4e09\u5927\u6cd5\u4eba\u9032\u51fa",
        f"\U0001f4c5 {_fmt_date(date_str)}",
        _SEP_THICK,
    ]
    for r in records:
        icon = "\U0001f4c8" if r["three_net"] >= 0 else "\U0001f4c9"
        lines.append(f"{icon} {r['name']}\uff08{r['code']}\uff09")
        if r["name"] == "NO_DATA":
            lines.append("\u26a0\ufe0f \u4eca\u65e5\u7121\u8cc7\u6599")
        else:
            lines.append(f"\u5916\u8cc7\uff1a{_fmt_lots(r['foreign_net'])}")
            lines.append(f"\u6295\u4fe1\uff1a{_fmt_lots(r['trust_net'])}")
            lines.append(f"\u81ea\u71df\u5546\uff1a{_fmt_lots(r['dealer_net'])}")
            lines.append(f"\u5408\u8a08\uff1a{_fmt_lots(r['three_net'])}")
        lines.append(_SEP_THIN)
    lines.append("\u8cc7\u6599\u4f86\u6e90\uff1a\u53f0\u7063\u8b49\u5238\u4ea4\u6613\u6240")
    return "\n".join(lines)

def build_no_data_message(date_str: str) -> str:
    return (
        f"\u26a0\ufe0f {_fmt_date(date_str)} \u67e5\u7121\u4e09\u5927\u6cd5\u4eba\u8cc7\u6599\n"
        "\u53ef\u80fd\u662f\u975e\u4ea4\u6613\u65e5\u6216\u8cc7\u6599\u5c1a\u672a\u66f4\u65b0\u3002\n"
        "\u683c\u5f0f\uff1a\u5831\u544a YYYYMMDD"
    )

def build_etf_report(etf_code, etf_name, date_str, diff) -> str:
    lines = [
        f"\U0001f4ca {etf_name}\uff08{etf_code}\uff09",
        f"\U0001f4c5 {_fmt_date(date_str)}",
        _SEP_THICK,
    ]
    added   = diff.get("added", [])
    removed = diff.get("removed", [])
    if not added and not removed and not diff.get("changed"):
        if diff.get("top10"):
            lines.append("\uff08\u9996\u6b21\u57f7\u884c\uff0c\u986f\u793a\u524d 10 \u5927\u6301\u80a1\uff09")
            for i, h in enumerate(diff["top10"], 1):
                w = f"{h['weight']:.2f}%" if h.get("weight") else ""
                lines.append(f"  {i:2d}. {h['name']}({h['code']}) {w}")
        else:
            lines.append("\u2705 \u6301\u80a1\u7121\u8b8a\u5316")
        return "\n".join(lines)
    if added:
        lines.append("\u52a0\u78bc\uff1a")
        for h in added:
            lots = h.get("delta_lots") or (h.get("shares", 0) // 1000)
            lines.append(f"\U0001f7e2{h['name']}({h['code']}){_fmt_etf_lots(lots)}")
    if removed:
        lines.append("\u6e1b\u78bc\uff1a")
        for h in removed:
            lots = -(h.get("delta_lots") or (h.get("shares", 0) // 1000))
            lines.append(f"\U0001f534{h['name']}({h['code']}){_fmt_etf_lots(lots)}")
    return "\n".join(lines)

def build_etf_error(etf_code, etf_name) -> str:
    return f"\u26a0\ufe0f {etf_code} {etf_name}\n\u7121\u6cd5\u53d6\u5f97\u6301\u80a1\u8cc7\u6599\uff0c\u8acb\u7a0d\u5f8c\u91cd\u8a66\u3002"

def build_watchlist_message(stocks) -> str:
    if not stocks:
        return "\U0001f4cb \u8ffd\u8e64\u6e05\u55ae\u662f\u7a7a\u7684\u3002\n\u4f7f\u7528\u300c+2330\u300d\u65b0\u589e\u80a1\u7968\u3002"
    items = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(stocks))
    return f"\U0001f4cb \u76ee\u524d\u8ffd\u8e64\u6e05\u55ae\uff08{len(stocks)} \u6a94\uff09\uff1a\n{items}"

HELP_TEXT = (
    "\U0001f916 \u53f0\u80a1\u6cd5\u4eba\u8ffd\u8e64 Bot \u6307\u4ee4\u8aaa\u660e\n\n"
    "\u3010\u6301\u80a1\u6e05\u55ae\u3011\n"
    "  +2330       \u65b0\u589e\u80a1\u7968\uff084-6\u78bc\uff09\n"
    "  -2330       \u79fb\u9664\u80a1\u7968\n"
    "  \u6301\u80a1 / \u6e05\u55ae  \u67e5\u770b\u6e05\u55ae\n\n"
    "\u3010\u4e09\u5927\u6cd5\u4eba\u3011\n"
    "  \u4eca\u65e5         \u4eca\u65e5\u5831\u544a\n"
    "  \u5831\u544a 20241201 \u6307\u5b9a\u65e5\u671f\n"
    "  2330         \u67e5\u8a62\u55ae\u4e00\u80a1\u7968\n\n"
    "\u3010ETF \u6301\u80a1\u3011\n"
    "  ETF          \u6240\u6709ETF\u6301\u80a1\u8b8a\u5316\n"
    "  ETF 00981A   \u6307\u5b9aETF\n\n"
    "\u3010\u5176\u4ed6\u3011\n"
    "  \u6211\u7684ID       \u53d6\u5f97\u60a8\u7684 LINE User ID\n"
    "  \u8aaa\u660e / help  \u986f\u793a\u6b64\u8aaa\u660e"
)
