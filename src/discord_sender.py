import requests
from datetime import datetime
from src.config import TIMEZONE

def _get_color_by_bias(bias: str) -> int:
    b = bias.lower()
    if "bull" in b:
        return 0x2ECC71
    elif "bear" in b:
        return 0xE74C3C
    return 0xF1C40F

def _format_pct(val):
    if val is None:
        return "N/A"
    return f"+{val}%" if val > 0 else f"{val}%"

def send_discord_report(webhook_url: str, market_data: dict, news_items: list, ai_summary: dict):
    now_str = datetime.now(TIMEZONE).strftime("%d/%m/%Y %H:%M ICT")
    bias = ai_summary.get("market_bias", "Neutral")

    futures_lines = []
    for f in market_data["futures"]:
        if f["status"] == "unavailable":
            futures_lines.append(f"• **{f['symbol']}** ({f['name']}): `ไม่พบข้อมูล`")
        else:
            icon = "🟢" if (f["change_percent"] or 0) >= 0 else "🔴"
            futures_lines.append(f"{icon} **{f['symbol']}**: `{f['last_price']}` ({_format_pct(f['change_percent'])}) | _{f['timestamp_str']}_")

    indicator_lines = []
    for ind in market_data["indicators"]:
        if ind["last_price"] is not None:
            indicator_lines.append(f"• **{ind['symbol']}**: `{ind['last_price']}` ({_format_pct(ind['change_percent'])})")
    
    news_lines = [f"{i}. [{item['title']}]({item['link']})" for i, item in enumerate(news_items[:4], start=1)]
    if not news_lines:
        news_lines.append("ไม่มีข่าวด่วนสำคัญในรอบ 24 ชม.")

    embed = {
        "title": f"🇺🇸 US Futures Morning Brief | {now_str}",
        "description": f"**Market Outlook:** `{bias}`\n**{ai_summary.get('headline_th', '')}**\n{ai_summary.get('overview_th', '')}",
        "color": _get_color_by_bias(bias),
        "fields": [
            {"name": "📊 US Index Futures (เช้าเอเชีย)", "value": "\n".join(futures_lines), "inline": False},
            {"name": "📈 ตลาดอ้างอิงสำคัญ", "value": "\n".join(indicator_lines) if indicator_lines else "N/A", "inline": False},
            {"name": "💡 ปัจจัยหนุน (Drivers)", "value": "\n".join([f"• {d}" for d in ai_summary.get("drivers_th", ["-"])]), "inline": True},
            {"name": "⚠️ ปัจจัยเสี่ยง (Risks)", "value": "\n".join([f"• {r}" for r in ai_summary.get("risks_th", ["-"])]), "inline": True},
            {"name": "👀 สิ่งที่ต้องจับตาคืนนี้", "value": "\n".join([f"• {w}" for w in ai_summary.get("watch_events_th", ["-"])]), "inline": False},
            {"name": "📰 ข่าวเด่นรอบ 24 ชม.", "value": "\n".join(news_lines), "inline": False},
        ],
        "footer": {"text": "Yahoo Finance / CME Delayed Quotes | ข้อมูลนี้มิใช่คำแนะนำในการลงทุน"}
    }

    resp = requests.post(webhook_url, json={"embeds": [embed]}, timeout=15)
    resp.raise_for_status()
