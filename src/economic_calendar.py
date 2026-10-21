"""Dated economic releases from XOOMAR; calendar boundaries always use Bangkok."""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation
import re
import json
import os

import requests

BANGKOK = ZoneInfo("Asia/Bangkok")


def week_start(day):
    return day - timedelta(days=day.weekday())


def fetch_events(start, end, countries=("US",)):
    """Fetch a half-open Bangkok date range; XOOMAR supplies US releases only."""
    if set(countries) != {"US"}:
        raise ValueError("XOOMAR supports US events only; set CALENDAR_COUNTRIES=US")
    if end <= start:
        raise ValueError("Calendar end must be after start")
    lower = datetime.combine(start, time.min, BANGKOK)
    upper = datetime.combine(end, time.min, BANGKOK)
    response = requests.get(
        "https://xoomar.com/api/markets/calendar",
        params={"from": lower.astimezone(timezone.utc).date().isoformat(),
                "to": upper.astimezone(timezone.utc).date().isoformat()}, timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"XOOMAR calendar returned HTTP {response.status_code}")
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("XOOMAR calendar returned an error or invalid data")
    attribution = payload.get("meta", {}).get("sourceAttribution", "")
    estimates = json.loads(os.getenv("CALENDAR_ESTIMATES_JSON", "[]"))
    if not isinstance(estimates, list):
        raise ValueError("CALENDAR_ESTIMATES_JSON must be a JSON list")
    estimate_map = {}
    for entry in estimates:
        if not isinstance(entry, dict) or not all(entry.get(k) for k in ("date", "event", "unit", "basis", "source")) or entry.get("value") is None:
            raise ValueError("Each calendar estimate needs date, event, value, unit, basis, and source")
        datetime.strptime(entry["date"], "%Y-%m-%d")
        try:
            value = Decimal(str(entry["value"]))
        except InvalidOperation as exc:
            raise ValueError("Calendar estimate must be numeric") from exc
        if not value.is_finite():
            raise ValueError("Calendar estimate must be finite")
        key = (entry["date"], entry["event"].strip().lower())
        if key in estimate_map:
            raise ValueError("Duplicate calendar estimate for date and event")
        estimate_map[key] = entry
    events, seen = [], set()
    for row in payload["data"]:
        if not isinstance(row, dict) or not row.get("eventName") or not row.get("scheduledAt"):
            raise ValueError("XOOMAR calendar event is missing a name or release time")
        stamp = datetime.fromisoformat(row["scheduledAt"].replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("XOOMAR calendar release time must include a timezone")
        local = stamp.astimezone(BANGKOK)
        if not lower <= local < upper:
            continue
        key = (local, row["eventName"], row.get("periodLabel"))
        if key in seen:
            continue
        seen.add(key)
        impact = {"high": "High", "med": "Medium", "medium": "Medium", "low": "Low"}.get(
            str(row.get("importance", "")).lower(), "Unknown")
        events.append({"event": row["eventName"], "country": "US", "impact": impact,
                       "local_time": local, "previous": row.get("previous"),
                       "actual": row.get("actual"), "unit": row.get("unit"),
                       "period": row.get("periodLabel"), "source": row.get("source"),
                       "source_attribution": attribution,
                       "estimate": estimate_map.get((local.date().isoformat(), row["eventName"].strip().lower()))})
    return sorted(events, key=lambda event: (event["local_time"], event["event"]))


# Fixed translations keep calendar rendering independent of an LLM/API key.
EVENT_NAMES = {
    "initial jobless claims": "จำนวนผู้ขอรับสวัสดิการว่างงานครั้งแรก",
    "continuing jobless claims": "จำนวนผู้ขอรับสวัสดิการว่างงานต่อเนื่อง",
    "housing starts and building permits": "การเริ่มสร้างบ้านและใบอนุญาตก่อสร้าง",
    "housing starts": "การเริ่มสร้างบ้าน",
    "building permits": "ใบอนุญาตก่อสร้าง",
    "cpi (consumer price index)": "ดัชนีราคาผู้บริโภค (CPI)",
    "consumer price index": "ดัชนีราคาผู้บริโภค (CPI)",
    "cpi": "ดัชนีราคาผู้บริโภค (CPI)",
    "ppi (producer price index)": "ดัชนีราคาผู้ผลิต (PPI)",
    "producer price index": "ดัชนีราคาผู้ผลิต (PPI)",
    "nonfarm payrolls (employment situation)": "การจ้างงานนอกภาคเกษตรและภาวะตลาดแรงงาน",
    "fomc rate decision": "ผลการประชุมธนาคารกลางสหรัฐฯ และมติอัตราดอกเบี้ย",
    "fomc minutes": "รายงานการประชุมธนาคารกลางสหรัฐฯ",
    "personal income and outlays (pce)": "รายได้ การใช้จ่ายส่วนบุคคล และเงินเฟ้อ PCE",
    "retail sales": "ยอดค้าปลีก",
    "industrial production": "ผลผลิตภาคอุตสาหกรรม",
    "durable goods orders": "คำสั่งซื้อสินค้าคงทน",
    "jolts job openings": "ตำแหน่งงานว่าง (JOLTS)",
    "unemployment rate": "อัตราการว่างงาน",
    "existing home sales": "ยอดขายบ้านมือสอง",
    "new home sales": "ยอดขายบ้านใหม่",
    "international trade": "การค้าระหว่างประเทศ",
}
WEEKDAYS = ("จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์")
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
THAI_MONTHS = ("มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม")


def event_name_th(name):
    name = str(name).replace("\n", " ")[:200]
    translated = EVENT_NAMES.get(name.lower())
    if translated:
        return translated
    if name.lower().startswith("treasury auction:"):
        term = re.search(r"(\d+)-Year(?: (\d+)-Month)?", name, re.I)
        if term:
            duration = f"{term[1]} ปี" + (f" {term[2]} เดือน" if term[2] else "")
        else:
            term = re.search(r"(\d+)-Week", name, re.I)
            duration = f"{term[1]} สัปดาห์" if term else ""
        kind = "พันธบัตรชดเชยเงินเฟ้อสหรัฐฯ (TIPS)" if "tips" in name.lower() else "ตราสารหนี้รัฐบาลสหรัฐฯ"
        return f"ประมูล{kind}" + (f" อายุ {duration}" if duration else "") + (" (เปิดประมูลเพิ่มเติม)" if "reopening" in name.lower() else "")
    if name.lower().startswith("gdp"):
        stage = "ประมาณการครั้งแรก" if "advance" in name.lower() else "ประมาณการครั้งที่สอง" if "second" in name.lower() else "ประมาณการครั้งที่สาม" if "third" in name.lower() else ""
        return "ผลิตภัณฑ์มวลรวมในประเทศ (GDP)" + (f" — {stage}" if stage else "")
    # Preserve unfamiliar provider labels rather than inventing a translation.
    return f"รายการเศรษฐกิจ: {name}"


def period_th(period):
    text = str(period or "")[:150]
    text = text.replace("Week ending ", "สัปดาห์สิ้นสุด ")
    for english, thai in zip(MONTHS, THAI_MONTHS):
        text = text.replace(english, thai)
    text = re.sub(r"Q([1-4])", r"ไตรมาส \1", text)
    return text


def number_th(value):
    try:
        number = Decimal(str(value))
        if number.is_finite():
            return format(number, ",f").rstrip("0").rstrip(".") if number % 1 else format(number.quantize(Decimal(1)), ",f")
    except (InvalidOperation, ValueError):
        pass
    return str(value)[:120]


def market_scenarios(name):
    """Conditional reading guide, not an inferred trading signal from provider values."""
    name = str(name).lower()
    if "jobless" in name or "unemployment" in name:
        return ("ผู้ขอรับสวัสดิการ/ว่างงานเพิ่มเล็กน้อยกว่าที่ตลาดคาด อาจลดแรงกดดันดอกเบี้ย หากตลาดยังไม่กังวลเศรษฐกิจถดถอย",
                "เพิ่มมากกว่าคาดจนตลาดกังวลเศรษฐกิจถดถอย หรือออกมาต่ำกว่าคาดมากจนตลาดกังวลดอกเบี้ยสูงนาน")
    if any(word in name for word in ("housing", "building permits", "home sales")):
        return ("ยอดก่อสร้าง/ยอดขายดีกว่าคาด อาจหนุนหุ้นบ้านและวัสดุก่อสร้าง หากผลตอบแทนพันธบัตรไม่เร่งขึ้น",
                "ยอดอ่อนแอกว่าคาด อาจกดดันหุ้นบ้านและวัสดุก่อสร้าง; ตัวเลขแข็งแรงมากก็อาจกดดันหุ้นได้หากตลาดเพิ่มคาดการณ์ดอกเบี้ย")
    if "treasury auction" in name:
        return ("ความต้องการประมูลแข็งแกร่งและผลตอบแทนพันธบัตรลดลง อาจช่วยหนุนมูลค่าหุ้น โดยเฉพาะหุ้นเติบโต",
                "ความต้องการประมูลอ่อนแอและผลตอบแทนพันธบัตรเพิ่มขึ้น อาจกดดันมูลค่าหุ้น; ต้องดูผลประมูลจริง")
    if any(word in name for word in ("cpi", "ppi", "pce", "price index")):
        return ("เงินเฟ้อต่ำกว่าคาด อาจลดแรงกดดันดอกเบี้ย หากไม่ได้สะท้อนอุปสงค์ที่ทรุดลง",
                "เงินเฟ้อสูงกว่าคาด อาจเพิ่มความกังวลว่าเฟดจะคงดอกเบี้ยสูงนาน")
    if "fomc" in name:
        return ("ท่าทีผ่อนคลายกว่าที่ตลาดคาด อาจหนุนหุ้น หากไม่ได้เกิดจากเศรษฐกิจทรุดลงรุนแรง",
                "ท่าทีเข้มงวดกว่าที่ตลาดคาด อาจดันผลตอบแทนพันธบัตรขึ้นและกดดันหุ้น")
    if any(word in name for word in ("gdp", "payroll", "jolts", "retail", "industrial", "durable")):
        return ("กิจกรรมเศรษฐกิจดีกว่าคาด อาจหนุนแนวโน้มกำไร หากไม่เพิ่มความกังวลเงินเฟ้อและดอกเบี้ย",
                "กิจกรรมอ่อนแอกว่าคาดมาก อาจกดดันกำไร; ตัวเลขร้อนแรงเกินคาดก็อาจกดดันหุ้นผ่านดอกเบี้ย")
    return ("ผลประกาศหนุนแนวโน้มกำไรหรือช่วยลดแรงกดดันดอกเบี้ยเมื่อเทียบกับที่ตลาดคาด",
            "ผลประกาศกดดันกำไรหรือเพิ่มแรงกดดันดอกเบี้ยเมื่อเทียบกับที่ตลาดคาด")


def event_line(event):
    impact = str(event.get("impact") or "Unknown").lower()
    marker, label = {"high": ("🔴", "สูง"), "medium": ("🟡", "ปานกลาง"), "low": ("⚪", "ต่ำ")}.get(impact, ("⚪", "ไม่ระบุ"))
    stamp = event["local_time"]
    english = str(event["event"]).replace("\n", " ")[:200]
    lines = [f"{marker} **{stamp:%H:%M} น. | {event_name_th(english)} ({english})**", f"ความสำคัญ: {label}"]
    # Auction metadata includes offering amounts and CUSIPs, not a statistical period.
    if event.get("period") and not str(event["event"]).lower().startswith("treasury auction:"):
        lines.append(f"งวดข้อมูล: {period_th(event['period'])}")
    values = [f"{label}: {number_th(event[key])}" for key, label in (("previous", "ครั้งก่อน"), ("actual", "ประกาศแล้ว"))
              if event.get(key) is not None]
    if values:
        lines.append(" • ".join(values))
        unit = {"thousands, annual rate, starts": "พันหลัง (อัตราต่อปี)", "thousands": "พัน", "percent": "%", "%": "%"}.get(str(event.get("unit")), event.get("unit"))
        if unit:
            lines.append(f"หน่วย: {str(unit)[:100]}")
    estimate = event.get("estimate")
    if estimate:
        target = f"{number_th(estimate['value'])} {estimate['unit']}"
        lines.extend([f"**คาดการณ์ตลาด: {target}** ({estimate['basis']})", f"ที่มาค่าคาดการณ์: {estimate['source']}"])
        if any(word in str(event["event"]).lower() for word in ("cpi", "ppi", "pce", "price index")):
            lines.extend([f"• สูงกว่า {target}: เงินเฟ้อสูงกว่าคาด อาจกดดันหุ้นผ่านความกังวลดอกเบี้ย",
                          f"• ต่ำกว่า {target}: เงินเฟ้อต่ำกว่าคาด อาจหนุนหุ้นหากไม่ได้สะท้อนเศรษฐกิจทรุดลง",
                          f"• เท่ากับ {target}: ใกล้เคียงคาด ต้องดูตัวเลขย่อยและข้อมูลที่ปรับย้อนหลัง"])
    positive, negative = market_scenarios(event["event"])
    lines.extend(["", "**แนวทางอ่านผลต่อตลาดหุ้น**", f"🟢 {positive}", f"🔴 {negative}",
                  "เทียบผลจริงกับค่าคาดการณ์ในงวดและหน่วยเดียวกัน ไม่ใช่สัญญาณซื้อขายอัตโนมัติ" if estimate else
                  "ยังไม่สรุปทิศทาง: แหล่งข้อมูลไม่มีค่าคาดการณ์ตลาด จึงเทียบได้เพียงครั้งก่อนกับผลจริง"])
    return "\n".join(lines)


def report_pages(events, title, weekly=False):
    if not events and not weekly:
        return []
    intro = ""
    if weekly:
        focus = [e for e in events if str(e.get("impact", "")).lower() == "high"]
        intro += "\n**ประเด็นสำคัญสัปดาห์นี้**\n"
        intro += ("\n".join(f"• {e['local_time']:%d/%m %H:%M} น. — {event_name_th(e['event'])}"
                            for e in focus[:10]) or "ไม่มีรายการความสำคัญสูงในข้อมูลที่ได้รับ")
        if len(focus) > 10:
            intro += f"\nดูอีก {len(focus) - 10} รายการด้านล่าง"
        intro += "\n\n**กำหนดการประจำสัปดาห์**\n"
    pages, text, last_day = [], intro, None
    for event in sorted(events, key=lambda e: e["local_time"]):
        stamp = event["local_time"]
        header = f"━━━━━━━━━━━━━━━━━━\n📆 **วัน{WEEKDAYS[stamp.weekday()]}ที่ {stamp.day} {THAI_MONTHS[stamp.month - 1]} {stamp.year}**\n━━━━━━━━━━━━━━━━━━\n\n"
        block = event_line(event)
        if stamp.date() != last_day:
            # A separate Discord embed for each day keeps event ownership unambiguous.
            if last_day is not None:
                pages.append(text)
                text = ""
            text += header
            last_day = stamp.date()
        if len(text) + len(block) + 2 > 3900:
            pages.append(text)
            text = header
        text += block + "\n\n"
    if not events:
        text += "ไม่มีรายการเศรษฐกิจในข้อมูลสัปดาห์นี้"
    pages.append(text)
    return [{"title": title if len(pages) == 1 else f"{title} — หน้า {i + 1}/{len(pages)}",
             "description": body.rstrip(), "color": 0x3498DB}
            for i, body in enumerate(pages)]
