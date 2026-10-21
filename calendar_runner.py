"""Run once per morning. State must live on durable storage in cloud deployments."""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests

from src.economic_calendar import BANGKOK, fetch_events, report_pages, week_start


def post(webhook, embed, weekly_url=None):
    payload = {"embeds": [embed], "allowed_mentions": {"parse": []}}
    if weekly_url:
        payload["components"] = [{"type": 1, "components": [
            {"type": 2, "style": 5, "label": "📌 ปฏิทินสัปดาห์นี้", "url": weekly_url}]}]
    response = requests.post(webhook, params={"wait": "true", "with_components": "true"},
                             json=payload, timeout=30)
    if not response.ok:
        raise RuntimeError(f"Discord calendar post failed: HTTP {response.status_code}")
    return response.json()


def run_calendar(now=None, checkpoint=None, dry_run=False, test_send=False, manual_send=False):
    if sum((dry_run, test_send, manual_send)) > 1:
        raise ValueError("Use one mode only, not both dry_run/test_send or manual_send")
    now = now or datetime.now(BANGKOK)
    if now.tzinfo is None:
        raise ValueError("now must include a timezone")
    today = now.astimezone(BANGKOK).date()
    monday = week_start(today)
    countries = tuple(c.strip().upper() for c in os.getenv("CALENDAR_COUNTRIES", "US").split(",") if c.strip())
    if not countries:
        raise ValueError("CALENDAR_COUNTRIES must contain at least one country code")
    if dry_run:
        events = fetch_events(monday, monday + timedelta(days=7), countries=countries)
        preview = {
            "weekly": report_pages(events, f"📅 ปฏิทินเศรษฐกิจประจำสัปดาห์ {monday:%d/%m/%Y}", True),
        }
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return preview
    webhook = os.getenv("CALENDAR_WEBHOOK_URL")
    if not webhook:
        raise ValueError("CALENDAR_WEBHOOK_URL is required: use the economic-calendar channel webhook")
    if test_send:
        events = fetch_events(monday, monday + timedelta(days=7), countries=countries)
        pages = report_pages(events, f"🧪 ทดสอบรูปแบบปฏิทินประจำสัปดาห์ {monday:%d/%m/%Y}", weekly=True)
        for embed in pages:
            embed["description"] = "**ข้อความทดสอบ — ไม่ใช่การส่งตามกำหนดเวลา**\n\n" + embed["description"]
            post(webhook, embed)
        print(f"[Calendar] Sent {len(pages)} test page(s) to Discord; production state and pins unchanged.")
        return
    state_path = Path(os.getenv("CALENDAR_STATE_PATH", ".calendar-state/state.json"))
    state = json.loads(state_path.read_text()) if state_path.exists() else {}

    def save():
        state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state))
        temporary.replace(state_path)
        if checkpoint:
            checkpoint()

    import hashlib
    destination = hashlib.sha256(webhook.encode()).hexdigest()
    if state.get("week") != monday.isoformat() or state.get("destination") != destination:
        # Discard prior-week links so reminders can never jump to a stale calendar.
        state = {"week": monday.isoformat(), "destination": destination, "weekly_pages": [], "daily_pages": {}}
    events = fetch_events(monday, monday + timedelta(days=7), countries=countries)
    if manual_send:
        # Explicitly publish a fresh real overview and point subsequent reminders to it.
        # Do this only after a successful fetch so provider failures preserve state.
        state["weekly_pages"] = []
        state.pop("weekly_plan", None)
        state.pop("pinned", None)
        state["daily_pages"].pop(today.isoformat(), None)
    # Also initialize this week's overview on first deployment or after a missed Monday.
    weekly_pages = report_pages(events, f"📅 ปฏิทินเศรษฐกิจ {monday:%d/%m/%Y} – {monday + timedelta(days=6):%d/%m/%Y}", True)
    if "weekly_plan" not in state:
        state["weekly_plan"] = weekly_pages
        save()
    for embed in state["weekly_plan"][len(state["weekly_pages"]):]:
        message = post(webhook, embed)
        state["weekly_pages"].append({"id": message["id"], "channel_id": message["channel_id"]})
        save()
    print(f"[Calendar] Weekly overview ready: {len(state['weekly_pages'])} page(s); existing pages are not resent.")
    first = state["weekly_pages"][0]
    token = os.getenv("DISCORD_BOT_TOKEN")
    if token and not state.get("pinned"):
        response = requests.put(
            f"https://discord.com/api/v10/channels/{first['channel_id']}/messages/pins/{first['id']}",
            headers={"Authorization": f"Bot {token}"}, timeout=30)
        if not response.ok:
            raise RuntimeError(f"Calendar pin failed: HTTP {response.status_code}; check bot channel permissions")
        state["pinned"] = True
        save()
    print("[Calendar] Weekly-only mode; daily reminders are disabled.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Fetch and print reports without Discord posts or state writes")
    parser.add_argument("--test-send", action="store_true", help="Send a labeled weekly test without reading or changing production state or pins")
    parser.add_argument("--manual-send", action="store_true", help="Publish a fresh real weekly overview and today's events, updating production links")
    args = parser.parse_args()
    run_calendar(dry_run=args.dry_run, test_send=args.test_send, manual_send=args.manual_send)
