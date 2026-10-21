import json
import os
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import Mock, patch

from src.economic_calendar import BANGKOK, fetch_events, report_pages, week_start, event_line
from calendar_runner import run_calendar, post


class CalendarTests(unittest.TestCase):
    @patch("src.economic_calendar.requests.get")
    def test_bangkok_boundaries_and_duplicates(self, get):
        row = {"eventName": "CPI", "importance": "high"}
        get.return_value.json.return_value = {"data": [
            {**row, "scheduledAt": "2026-10-18T16:59:00Z"},
            {**row, "scheduledAt": "2026-10-18T17:00:00Z"},
            {**row, "scheduledAt": "2026-10-18T17:00:00Z"},
            {**row, "scheduledAt": "2026-10-25T17:00:00Z"}]}
        events = fetch_events(date(2026, 10, 19), date(2026, 10, 26))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["local_time"].hour, 0)
        self.assertEqual(get.call_args.kwargs["params"]["from"], "2026-10-18")
        self.assertEqual(week_start(date(2026, 10, 25)), date(2026, 10, 19))

    @patch("src.economic_calendar.requests.get")
    def test_provider_error_is_not_empty_day(self, get):
        get.return_value.json.return_value = {"Error Message": "Invalid key"}
        with self.assertRaises(ValueError):
            fetch_events(date(2026, 10, 19), date(2026, 10, 26))

    @patch("src.economic_calendar.requests.get")
    def test_provider_http_error_is_not_empty_day(self, get):
        get.return_value.status_code = 402
        get.return_value.ok = False
        with self.assertRaisesRegex(RuntimeError, "XOOMAR calendar returned HTTP 402"):
            fetch_events(date(2026, 10, 19), date(2026, 10, 26))
        get.return_value.json.assert_not_called()

    @patch("src.economic_calendar.requests.get")
    def test_mapping_attribution_and_no_key(self, get):
        get.return_value.json.return_value = {"data": [{
            "eventName": "GDP", "scheduledAt": "2026-10-20T12:30:00Z",
            "importance": "med", "previous": 0, "actual": None,
            "unit": "%", "source": "bea", "periodLabel": "Q3"}],
            "meta": {"sourceAttribution": "Bureau of Economic Analysis"}}
        events = fetch_events(date(2026, 10, 19), date(2026, 10, 26))
        self.assertEqual(events[0]["impact"], "Medium")
        self.assertEqual(events[0]["local_time"].hour, 19)
        self.assertNotIn("apikey", get.call_args.kwargs["params"])
        text = report_pages(events, "Daily")[0]["description"]
        self.assertIn("ครั้งก่อน: 0", text)
        self.assertEqual(events[0]["source_attribution"], "Bureau of Economic Analysis")
        self.assertNotIn("Bureau of Economic Analysis", text)
        self.assertNotIn("xoomar.com", text)
        self.assertNotIn("footer", report_pages(events, "Daily")[0])
        self.assertIn("ไม่มีค่าคาดการณ์ตลาด", text)

    @patch("src.economic_calendar.requests.get")
    def test_rejects_unsupported_country_and_invalid_timestamps(self, get):
        with self.assertRaisesRegex(ValueError, "US events only"):
            fetch_events(date(2026, 10, 19), date(2026, 10, 26), countries=("GB",))
        get.assert_not_called()
        for stamp in (None, "2026-10-20T12:30:00"):
            get.return_value.json.return_value = {"data": [{"eventName": "CPI", "scheduledAt": stamp}]}
            with self.assertRaises(ValueError):
                fetch_events(date(2026, 10, 19), date(2026, 10, 26))

    def test_cpi_estimate_thresholds_are_explicit_and_optional(self):
        event = {"event": "CPI", "impact": "High", "local_time": datetime(2026, 10, 22, 19, 30, tzinfo=BANGKOK)}
        self.assertNotIn("คาดการณ์ตลาด: 2", event_line(event))
        event["estimate"] = {"value": "2.0", "unit": "%", "basis": "CPI รวม รายปี", "source": "ตัวอย่างทดสอบ"}
        text = event_line(event)
        self.assertIn("คาดการณ์ตลาด: 2 %", text)
        self.assertIn("สูงกว่า 2 %", text)
        self.assertIn("ต่ำกว่า 2 %", text)
        self.assertIn("เท่ากับ 2 %", text)
        self.assertNotIn("แหล่งข้อมูลไม่มีค่าคาดการณ์ตลาด", text)

    @patch("src.economic_calendar.requests.get")
    def test_estimates_match_exact_event_and_bangkok_date(self, get):
        get.return_value.json.return_value = {"data": [{"eventName": "CPI", "scheduledAt": "2026-10-21T18:00:00Z", "importance": "high"}]}
        entry = {"date": "2026-10-22", "event": "CPI", "value": 2, "unit": "%", "basis": "CPI รวม รายปี", "source": "test"}
        with patch.dict(os.environ, {"CALENDAR_ESTIMATES_JSON": json.dumps([entry])}):
            events = fetch_events(date(2026, 10, 19), date(2026, 10, 26))
            self.assertEqual(events[0]["estimate"]["value"], 2)
        entry["date"] = "2026-10-21"
        with patch.dict(os.environ, {"CALENDAR_ESTIMATES_JSON": json.dumps([entry])}):
            self.assertIsNone(fetch_events(date(2026, 10, 19), date(2026, 10, 26))[0]["estimate"])

    def test_large_calendar_paginates_without_dropping_events(self):
        events = [{"event": f"Release {i}", "impact": "High", "local_time": datetime(2026, 10, 19, tzinfo=BANGKOK)} for i in range(200)]
        pages = report_pages(events, "Weekly", True)
        self.assertGreater(len(pages), 1)
        self.assertTrue(all(len(p["description"]) <= 4096 for p in pages))
        self.assertIn("Release 199", pages[-1]["description"])

    def test_thai_readable_report_hides_missing_values_and_single_page_count(self):
        event = {"event": "Initial Jobless Claims", "impact": "High",
                 "local_time": datetime(2026, 10, 22, 19, 30, tzinfo=BANGKOK),
                 "previous": None, "actual": None, "period": "Week ending 2026-10-17"}
        page = report_pages([event], "รายงาน", weekly=True)[0]
        self.assertEqual(page["title"], "รายงาน")
        self.assertNotIn("เวลาทั้งหมดเป็นเวลาไทย", page["description"])
        self.assertIn("(Initial Jobless Claims)", page["description"])
        self.assertIn("🟢 ", page["description"])
        self.assertNotIn("อาจเป็นบวก:", page["description"])
        self.assertIn("🔴 ", page["description"])
        self.assertNotIn("อาจเป็นลบ:", page["description"])
        self.assertIn("วันพฤหัสบดีที่ 22 ตุลาคม 2026", page["description"])
        self.assertIn("จำนวนผู้ขอรับสวัสดิการว่างงานครั้งแรก", page["description"])
        self.assertIn("ความสำคัญ: สูง", page["description"])
        self.assertNotIn("N/A", page["description"])
        self.assertNotIn("High", page["description"])
        self.assertEqual(report_pages([], "รายวัน"), [])
        self.assertTrue(report_pages([], "รายสัปดาห์", weekly=True))

    def test_values_and_auction_are_readable_in_thai(self):
        event = {"event": "Housing Starts and Building Permits", "impact": "Medium",
                 "local_time": datetime(2026, 10, 20, 19, 30, tzinfo=BANGKOK),
                 "previous": "1288.0000", "actual": "1221.0000",
                 "unit": "thousands, annual rate, starts", "period": "September 2026"}
        text = event_line(event)
        self.assertIn("1,288", text)
        self.assertIn("1,221", text)
        self.assertIn("กันยายน 2026", text)
        self.assertIn("พันหลัง (อัตราต่อปี)", text)
        event.update(event="Treasury auction: 19-Year 10-Month Bond (reopening)", period="$13B offering, CUSIP 912810UX4", previous=None, actual=None)
        text = event_line(event)
        self.assertIn("19 ปี 10 เดือน", text)
        self.assertNotIn("CUSIP", text)

    def test_each_day_has_its_own_card_and_continuation_keeps_day_header(self):
        events = [{"event": "Initial Jobless Claims", "impact": "High", "local_time": datetime(2026, 10, day, 19, 30, tzinfo=BANGKOK)} for day in (20, 22)]
        pages = report_pages(events, "สัปดาห์", weekly=True)
        self.assertEqual(len(pages), 2)
        self.assertIn("วันอังคารที่ 20 ตุลาคม", pages[0]["description"])
        self.assertIn("วันพฤหัสบดีที่ 22 ตุลาคม", pages[1]["description"])
        many = report_pages([events[0]] * 20, "สัปดาห์", weekly=True)
        self.assertGreater(len(many), 1)
        for page in many:
            self.assertIn("วันอังคารที่ 20 ตุลาคม", page["description"])
            self.assertLessEqual(len(page["description"]), 4096)

    @patch("calendar_runner.requests.get")
    @patch("calendar_runner.fetch_events", return_value=[])
    @patch("calendar_runner.post", return_value={"id": "3", "channel_id": "2"})
    def test_no_daily_message_on_empty_day_even_when_repeated(self, send, fetch, get):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            "CALENDAR_STATE_PATH": str(Path(directory) / "state.json"),
            "CALENDAR_WEBHOOK_URL": "https://example.test", "DISCORD_GUILD_ID": "1",
            "DISCORD_BOT_TOKEN": ""}):
            now = datetime(2026, 10, 19, 6, tzinfo=BANGKOK)
            run_calendar(now)  # Weekly overview is still posted.
            run_calendar(now)
            run_calendar(datetime(2026, 10, 20, 6, tzinfo=BANGKOK))
            self.assertEqual(send.call_count, 1)
            self.assertEqual(len(send.call_args.args), 2)  # No daily jump-button message.

    @patch("calendar_runner.requests.post")
    def test_link_button_webhook_parameters(self, request):
        post("https://example.test", {"title": "Daily"}, "https://discord.com/channels/1/2/3")
        args = request.call_args.kwargs
        self.assertEqual(args["params"]["with_components"], "true")
        self.assertEqual(args["json"]["components"][0]["components"][0]["style"], 5)

    @patch("calendar_runner.fetch_events")
    @patch("calendar_runner.post", return_value={"id": "3", "channel_id": "2"})
    def test_weekly_only_dedup_even_when_today_has_events(self, send, fetch):
        fetch.return_value = [{"event": "Initial Jobless Claims", "impact": "High", "local_time": datetime(2026, 10, 19, 19, tzinfo=BANGKOK)}]
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            "CALENDAR_STATE_PATH": str(Path(directory) / "state.json"),
            "CALENDAR_WEBHOOK_URL": "https://example.test", "DISCORD_GUILD_ID": "1",
            "DISCORD_BOT_TOKEN": ""}):
            monday = datetime(2026, 10, 19, 6, tzinfo=BANGKOK)
            run_calendar(monday)
            self.assertEqual(send.call_count, 1)
            run_calendar(monday)
            self.assertEqual(send.call_count, 1)
            run_calendar(datetime(2026, 10, 20, 6, tzinfo=BANGKOK))
            self.assertEqual(send.call_count, 1)
            fetch.return_value[0]["local_time"] = datetime(2026, 10, 26, 19, tzinfo=BANGKOK)
            run_calendar(datetime(2026, 10, 26, 6, tzinfo=BANGKOK))
            self.assertEqual(send.call_count, 2)

    @patch("calendar_runner.fetch_events", return_value=[])
    @patch("calendar_runner.post")
    def test_dry_run_does_not_post_or_write_state(self, send, fetch):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            "CALENDAR_STATE_PATH": str(Path(directory) / "state.json"),
            "CALENDAR_WEBHOOK_URL": ""}), patch("builtins.print"):
            preview = run_calendar(datetime(2026, 10, 19, 6, tzinfo=BANGKOK), dry_run=True)
            self.assertIn("weekly", preview)
            self.assertNotIn("daily", preview)
            send.assert_not_called()
            self.assertFalse((Path(directory) / "state.json").exists())

    @patch("calendar_runner.requests.put")
    @patch("calendar_runner.fetch_events", return_value=[])
    @patch("calendar_runner.post", return_value={"id": "test", "channel_id": "2"})
    def test_explicit_test_send_bypasses_state_without_modifying_it(self, send, fetch, pin):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            "CALENDAR_STATE_PATH": str(Path(directory) / "state.json"),
            "CALENDAR_WEBHOOK_URL": "https://calendar.test", "DISCORD_BOT_TOKEN": "test"}):
            path = Path(directory) / "state.json"
            path.write_text("existing state must not be read or overwritten")
            checkpoint = Mock()
            now = datetime(2026, 10, 21, 6, tzinfo=BANGKOK)
            run_calendar(now, test_send=True, checkpoint=checkpoint)
            run_calendar(now, test_send=True, checkpoint=checkpoint)
            self.assertEqual(send.call_count, 2)
            self.assertIn("ทดสอบ", send.call_args.args[1]["title"])
            self.assertEqual(path.read_text(), "existing state must not be read or overwritten")
            pin.assert_not_called()
            checkpoint.assert_not_called()

    @patch("calendar_runner.fetch_events")
    @patch("calendar_runner.post")
    def test_test_send_and_dry_run_are_mutually_exclusive(self, send, fetch):
        with self.assertRaisesRegex(ValueError, "not both"):
            run_calendar(dry_run=True, test_send=True)
        send.assert_not_called()
        fetch.assert_not_called()

    @patch("calendar_runner.fetch_events", return_value=[])
    @patch("calendar_runner.post")
    def test_manual_send_publishes_real_overview_and_updates_jump_target(self, send, fetch):
        send.side_effect = [{"id": "old", "channel_id": "2"}, {"id": "new", "channel_id": "2"}]
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            "CALENDAR_STATE_PATH": str(Path(directory) / "state.json"),
            "CALENDAR_WEBHOOK_URL": "https://calendar.test", "DISCORD_GUILD_ID": "1",
            "DISCORD_BOT_TOKEN": ""}):
            now = datetime(2026, 10, 21, 6, tzinfo=BANGKOK)
            run_calendar(now)
            run_calendar(now, manual_send=True)
            self.assertEqual(send.call_count, 2)
            self.assertNotIn("ทดสอบ", send.call_args.args[1]["title"])
            state = json.loads((Path(directory) / "state.json").read_text())
            self.assertEqual(state["weekly_pages"][0]["id"], "new")
            run_calendar(now)
            self.assertEqual(send.call_count, 2)

    def test_missing_calendar_webhook_never_uses_market_channel(self):
        with patch.dict(os.environ, {"CALENDAR_WEBHOOK_URL": "", "DISCORD_WEBHOOK_URL": "https://market.test"}):
            with self.assertRaisesRegex(ValueError, "CALENDAR_WEBHOOK_URL"):
                run_calendar()

    @patch("calendar_runner.fetch_events")
    @patch("calendar_runner.post", return_value={"id": "3", "channel_id": "2"})
    def test_changing_destination_creates_new_weekly_link(self, send, fetch):
        fetch.return_value = []
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            "CALENDAR_STATE_PATH": str(Path(directory) / "state.json"),
            "CALENDAR_WEBHOOK_URL": "https://first.test", "DISCORD_GUILD_ID": "1",
            "DISCORD_BOT_TOKEN": ""}):
            now = datetime(2026, 10, 19, 6, tzinfo=BANGKOK)
            run_calendar(now)
            os.environ["CALENDAR_WEBHOOK_URL"] = "https://second.test"
            run_calendar(now)
            self.assertEqual(send.call_count, 2)
            self.assertEqual(send.call_args.args[0], "https://second.test")

    @patch("calendar_runner.requests.put")
    @patch("calendar_runner.fetch_events")
    @patch("calendar_runner.post", return_value={"id": "3", "channel_id": "2"})
    def test_pin_failure_retries_existing_weekly_message(self, send, fetch, put):
        fetch.return_value = []
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            "CALENDAR_STATE_PATH": str(Path(directory) / "state.json"),
            "CALENDAR_WEBHOOK_URL": "https://example.test", "DISCORD_GUILD_ID": "1",
            "DISCORD_BOT_TOKEN": "test"}):
            put.return_value.ok = False
            put.return_value.status_code = 403
            now = datetime(2026, 10, 19, 6, tzinfo=BANGKOK)
            with self.assertRaises(RuntimeError):
                run_calendar(now)
            self.assertEqual(send.call_count, 1)
            put.return_value.ok = True
            run_calendar(now)
            self.assertEqual(send.call_count, 1)
            self.assertEqual(put.call_count, 2)


if __name__ == "__main__":
    unittest.main()
