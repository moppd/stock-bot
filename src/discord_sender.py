import requests
from datetime import datetime
from src.config import TIMEZONE

def _format_futures_change(pct: float) -> str:
    if pct is None:
        return "N/A"
    if abs(pct) < 0.005:
        return "≈0.00% (ทรงตัว)"
    return f"+{pct:.2f}%" if pct > 0 else f"{pct:.2f}%"

def _get_futures_icon(pct: float) -> str:
    if pct is None or abs(pct) < 0.005:
        return "⚪"
    return "🟢" if pct > 0 else "🔴"

def _get_bias_color(bias: str) -> int:
    b = bias.lower()
    if "บวก" in b or "bull" in b:
        return 0x2ECC71  # เขียว
    elif "ลบ" in b or "bear" in b:
        return 0xE74C3C  # แดง
    elif "กลาง" in b or "neutral" in b:
        return 0xF1C40F  # เหลือง
    return 0x95A5A6      # เทา

def send_discord_report(webhook_url: str, market_data: dict, ai_analysis: dict):
    now_th = datetime.now(TIMEZONE).strftime("%d/%m/%Y %H:%M น.")
    bias = ai_analysis.get("market_bias", "เป็นกลาง")
    color = _get_bias_color(bias)

    fields = []

    # 1. US Futures Overview (แสดงชื่อเต็ม + ตัดวันเวลาออกทั้งหมด)
    futures_lines = []
    for f in market_data["futures"]:
        if f["status"] == "unavailable":
            futures_lines.append(f"• **{f['name']}**: `ไม่พบข้อมูล`")
        else:
            icon = _get_futures_icon(f["change_percent"])
            chg_str = _format_futures_change(f["change_percent"])
            futures_lines.append(f"{icon} **{f['name']}**: `{f['last_price']:,.2f}` ({chg_str})")

    fields.append({
        "name": "📊 ภาพรวมดัชนี Futures สหรัฐฯ",
        "value": "\n".join(futures_lines)[:1024],
        "inline": False
    })

    # 2. Market Indicators
    indicator_lines = []
    for ind in market_data["indicators"]:
        if ind["last_price"] is not None:
            unit_display = f" {ind['unit']}" if ind.get("unit") else ""
            chg_str = f"+{ind['change_percent']:.2f}%" if (ind["change_percent"] or 0) > 0 else f"{ind['change_percent']:.2f}%"
            indicator_lines.append(f"• **{ind['name']}**: `{ind['last_price']}{unit_display}` ({chg_str})")

    if ai_analysis.get("indicators_interpretation_th"):
        indicator_lines.append(f"\n💡 {ai_analysis['indicators_interpretation_th']}")

    if indicator_lines:
        fields.append({
            "name": "📈 สัญญาณจากตลาดการเงิน",
            "value": "\n".join(indicator_lines)[:1024],
            "inline": False
        })

    # 3. Drivers & Risks
    if ai_analysis.get("drivers_th"):
        fields.append({
            "name": "🟢 ปัจจัยบวกต่อตลาด",
            "value": "\n".join([f"• {d}" for d in ai_analysis["drivers_th"]])[:1024],
            "inline": False
        })
    if ai_analysis.get("risks_th"):
        fields.append({
            "name": "🔴 ปัจจัยกดดันตลาด",
            "value": "\n".join([f"• {r}" for r in ai_analysis["risks_th"]])[:1024],
            "inline": False
        })

    # 4. Events vs Highlights (ไม่มี Source, เนื้อหาครบถ้วน)
    evt_block = ai_analysis.get("events_or_highlights", {})
    evt_title = evt_block.get("title", "🔥 ประเด็นสำคัญที่ต้องจับตา")
    evt_items = evt_block.get("items", [])
    if evt_items:
        evt_lines = []
        for it in evt_items:
            topic = it.get("topic_th") or it.get("title_th", "")
            detail = it.get("detail_th", "")
            evt_lines.append(f"• **{topic}**\n  {detail}\n")
        fields.append({
            "name": evt_title,
            "value": "\n".join(evt_lines).strip()[:1024],
            "inline": False
        })

    # 5. Big Tech & AI (ไม่มี Source, เนื้อหาครบถ้วน)
    big_tech = ai_analysis.get("big_tech_news", [])
    if big_tech:
        tech_lines = []
        for t in big_tech:
            topic = t.get("topic_th") or t.get("headline_th", "")
            detail = t.get("detail_th") or f"{t.get('facts_th', '')} {t.get('impact_th', '')}"
            tech_lines.append(f"• **{topic}**\n  {detail}\n")
        fields.append({
            "name": "💻 เจาะข่าว Big Tech & AI",
            "value": "\n".join(tech_lines).strip()[:1024],
            "inline": False
        })

    # 6. Global Impact (ไม่มี Source, เนื้อหาครบถ้วน)
    global_news = ai_analysis.get("global_news", [])
    if global_news:
        global_lines = []
        for g in global_news:
            topic = g.get("topic_th") or g.get("headline_th", "")
            detail = g.get("detail_th") or g.get("transmission_mechanism_th", "")
            global_lines.append(f"• **{topic}**\n  {detail}\n")
        fields.append({
            "name": "🌍 เศรษฐกิจโลกที่กระทบตลาดหุ้น",
            "value": "\n".join(global_lines).strip()[:1024],
            "inline": False
        })

    # Description: รวม Outlook สรุปภาพรวม
    description_text = (
        f"**มุมมองตลาด:** `{bias}`\n"
        f"**{ai_analysis.get('headline_th', '')}**\n\n"
        f"{ai_analysis.get('overview_th', '')}"
    )

    embed = {
        "title": f"🇺🇸 US Market | {now_th}",
        "description": description_text[:4096],
        "color": color,
        "fields": fields,
        "footer": {
            "text": "ข้อมูลสรุปเพื่อการวิเคราะห์และติดตามสถานะตลาด มิใช่คำแนะนำการลงทุน"
        }
    }

    resp = requests.post(webhook_url, json={"embeds": [embed]}, timeout=15)
    resp.raise_for_status()

def send_mag7_report(webhook_url: str, mag7_data: list):
    if not mag7_data:
        return

    now_th = datetime.now(TIMEZONE).strftime("%d/%m/%Y %H:%M น.")
    
    # คำนวณผลตอบแทนเฉลี่ยของทั้งกลุ่ม
    avg_change = sum(s["change_percent"] for s in mag7_data) / len(mag7_data)
    avg_color = 0x2ECC71 if avg_change > 0 else 0xE74C3C if avg_change < 0 else 0xF1C40F
    avg_sign = f"+{avg_change:.2f}%" if avg_change > 0 else f"{avg_change:.2f}%"

    lines = []
    for s in mag7_data:
        icon = "🟢" if s["change_percent"] > 0 else "🔴" if s["change_percent"] < 0 else "⚪"
        chg_str = f"+{s['change_percent']:.2f}%" if s["change_percent"] > 0 else f"{s['change_percent']:.2f}%"
        lines.append(f"{icon} **{s['name']} ({s['symbol']})**: `${s['last_price']:,.2f}` ({chg_str})")

    embed = {
        "title": f"🌟 ราคาปิดหุ้น 7 นางฟ้า (Magnificent 7) | {now_th}",
        "description": f"**ภาพรวมกลุ่ม:** ปรับตัวเฉลี่ย `{avg_sign}`\n\n" + "\n".join(lines),
        "color": avg_color,
        "footer": {
            "text": "ราคาปิดตลาดทางการของเซสชันสหรัฐฯ ล่าสุด"
        }
    }

    # ยิงแยกเป็นอีก Message ทันที
    requests.post(webhook_url, json={"embeds": [embed]}, timeout=15)