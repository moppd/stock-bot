"""Render a sourced morning brief using Discord embed-safe field sizes."""
from datetime import datetime, timezone
import requests
from difflib import SequenceMatcher
from src.config import TIMEZONE


def _bias_color(bias):
    return {"Bullish": 0x2ECC71, "Bearish": 0xE74C3C}.get(bias, 0xF1C40F)


def _percentage(value):
    if value is None:
        return "N/A"
    return f"{value:+.2f}%"


def _truncate(text, limit=1024):
    text = str(text or "-")
    return text if len(text) <= limit else text[:limit - 2] + "…"


def _lines(items, empty="ไม่มีข้อมูลที่ยืนยันได้"):
    if not items:
        return empty
    return "\n".join(f"• {item}" for item in items)


def _format_thai_datetime(timestamp):
    """Convert an ISO-8601 timestamp (including UTC/Z) to Bangkok local time."""
    if not timestamp:
        return "ไม่ระบุเวลา"
    try:
        dt = datetime.fromisoformat(str(timestamp).strip().replace("Z", "+00:00"))
        if dt.tzinfo is None:
            # All published_at values from our news_fetcher are UTC.
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(TIMEZONE).strftime("%d/%m/%Y %H:%M น. (เวลาไทย)")
    except (ValueError, TypeError, OverflowError):
        return "ไม่ระบุเวลา"


def _distinct_summary(title, summary):
    """Hide near-identical title/summary text even if AI returns duplicates."""
    summary = str(summary or "").strip()
    title = str(title or "").strip()
    norm = lambda x: "".join(c.lower() for c in x if c.isalnum())
    a, b = norm(title), norm(summary)
    if a and b and (a in b or b in a or SequenceMatcher(None, a, b).ratio() >= 0.78):
        return ""
    return summary


def _news_value(items, empty):
    if not items:
        return empty
    rows = []
    for item in items:
        title = str(item.get("title_th", "ข่าวที่ติดตาม"))[:120]
        # Use the original supplied feed URL, not AI-generated URLs.
        link = item.get("link", "")
        summary = _distinct_summary(title, item.get("summary_th", ""))[:210]
        impact = str(item.get("impact_th", ""))[:180]
        stamp = item.get("published_at", "")
        parts = [f"**{title}**"]
        if summary:
            parts.append(summary)
        if impact:
            parts.append(f"**ผลต่อตลาด:** {impact}")
        if link:
            parts.append(f"[ต้นฉบับ]({link}) · {_format_thai_datetime(stamp)}")
        else:
            parts.append(_format_thai_datetime(stamp))
        rows.append("\n".join(parts))
    return _truncate("\n\n".join(rows))


def send_discord_report(webhook_url: str, market_data: dict, news_items: list, ai_summary: dict):
    now_str = datetime.now(TIMEZONE).strftime("%d/%m/%Y %H:%M น. (เวลาไทย)")
    bias = ai_summary.get("market_bias", "ข้อมูลไม่เพียงพอ")
    futures = []
    for f in market_data.get("futures", []):
        if f.get("last_price") is None or f.get("status") in {"unavailable", "error"}:
            futures.append(f"⚪ **{f.get('symbol', '?')}**: ไม่พบข้อมูล")
            continue
        pct = f.get("change_percent")
        dot = "🟢" if pct is not None and pct > 0 else "🔴" if pct is not None and pct < 0 else "⚪"
        warning = " ⚠️ ราคาล่าสุดเก่า/ตลาดปิด" if f.get("status") == "stale/closed" else ""
        futures.append(f"{dot} **{f['symbol']}**: `{f['last_price']}` ({_percentage(pct)}) | {f.get('timestamp_str', '-')}{warning}")
    indicators = [
        f"• **{ind.get('symbol', '?')}**: `{ind['last_price']}` ({_percentage(ind.get('change_percent'))})"
        for ind in market_data.get("indicators", []) if ind.get("last_price") is not None
    ]
    events = ai_summary.get("watch_events_th") or []
    highlights = ai_summary.get("market_highlights_th") or []
    section_name = "👀 สิ่งที่ต้องจับตาคืนนี้" if events else "🔥 ประเด็นเด่นที่ต้องจับตา"
    section_items = events if events else highlights
    fields = [
        {"name": "📊 US Index Futures (เช้าเอเชีย)", "value": _truncate("\n".join(futures)), "inline": False},
        {"name": "📈 ตลาดอ้างอิงสำคัญ", "value": _truncate("\n".join(indicators)), "inline": False},
        {"name": "💡 ปัจจัยหนุน (Drivers)", "value": _truncate(_lines(ai_summary.get("drivers_th", []))), "inline": True},
        {"name": "⚠️ ปัจจัยเสี่ยง (Risks)", "value": _truncate(_lines(ai_summary.get("risks_th", []))), "inline": True},
        {"name": section_name, "value": _truncate(_lines(section_items)), "inline": False},
        {"name": "💻 ข่าว Big Tech & AI", "value": _news_value(ai_summary.get("big_tech_news", []), "ไม่พบข่าว Big Tech ที่ผ่านการคัดเลือกในช่วงเวลานี้"), "inline": False},
        {"name": "🌍 ข่าวตลาดโลกที่กระทบหุ้นสหรัฐฯ", "value": _news_value(ai_summary.get("global_market_news", []), "ไม่พบข่าวต่างประเทศที่ผ่านการคัดเลือกในช่วงเวลานี้"), "inline": False},
    ]
    embed = {
        "title": f"🇺🇸 US Futures Morning Brief | {now_str}",
        "description": _truncate(f"**Market Outlook:** `{bias}`\n**{ai_summary.get('headline_th', '')}**\n{ai_summary.get('overview_th', '')}", 4096),
        "color": _bias_color(bias),
        "fields": fields,
        "footer": {"text": "Yahoo Finance (unofficial) / RSS news · ตรวจสอบเวลาและลิงก์ต้นฉบับ · ไม่ใช่คำแนะนำการลงทุน"},
    }
    response = requests.post(webhook_url, json={"embeds": [embed]}, timeout=15)
    response.raise_for_status()
