# US Futures Morning Brief — Discord Bot

US futures and Thai market briefs, plus a weekly US economic calendar.

## Calendar schedule

The calendar runs **Monday at 06:00 Asia/Bangkok** and covers that Monday through Sunday. **Daily reminders are disabled.** The existing weekday market-brief schedule is unchanged.

[XOOMAR](https://xoomar.com/economic-calendar-api) supplies US releases without an API key. Reports use Thai names with English names in parentheses, separate cards for each date, previous/actual figures when available, and conditional explanations of stock-market effects. Unknown event names retain their provider labels. Reports omit the source block and footer. Provider coverage and release schedules can change.

XOOMAR does not supply consensus forecasts. The interpretation is a reading guide, not a computed trading signal: market reactions depend on surprises, earnings expectations and interest rates. See [Federal Reserve research](https://www.federalreserve.gov/econres/feds/the-effect-of-the-federal-reserve-on-the-stock-market-magnitudes-channels-and-shocks.htm). [XOOMAR terms](https://xoomar.com/terms) describe attribution and reuse requirements.

## Configure Modal

In the economic-calendar Discord channel, open **Edit Channel → Integrations → Webhooks** and create/copy its webhook. Keep the existing market-channel webhook.

Edit the existing `bot-secrets` at [Modal Secrets](https://modal.com/secrets), preserving existing market-report secrets:

| Setting | Purpose |
| --- | --- |
| `CALENDAR_WEBHOOK_URL` | Required: webhook for the economic-calendar channel. |
| `CALENDAR_COUNTRIES` | Optional: `US` only; other countries are rejected. |
| `DISCORD_BOT_TOKEN` | Optional: pins the first card of the weekly report. The bot needs access and pin permissions in this channel. |
| `CALENDAR_ESTIMATES_JSON` | Optional: verified consensus estimates; see below. |

No XOOMAR key or FMP subscription is needed. `FMP_API_KEY` is unused and can be removed. Removing a secret does not cancel provider billing.

## Test and deploy

From this repository:

```sh
source .venv/bin/activate
python -m pip install -r requirements.txt modal
modal setup
python -m unittest discover -s tests -v
```

Preview real calendar data without posting or modifying report state:

```sh
modal run modal_runner.py::scheduled_calendar --dry-run
```

Send a labeled test without changing production links, pins or state:

```sh
modal run modal_runner.py::scheduled_calendar --test-send
```

Send a fresh **real** weekly report now, updating the saved report and pinning when configured:

```sh
modal run modal_runner.py::scheduled_calendar --manual-send
```

This may create additional messages and pins; previous ones remain. Run once and wait for completion. The command without flags uses normal duplicate prevention and skips a weekly report already sent.

Deploy or update the existing app:

```sh
modal deploy modal_runner.py
```

In Modal Apps → `us-futures-brief`, confirm `scheduled_calendar` runs **Monday at 06:00 Asia/Bangkok**. Deployment is required to replace the previous daily schedule. Closing your laptop does not stop deployed schedules. Actual delivery time is best effort. `modal run modal_runner.py` alone invokes the market-report entrypoint; include `::scheduled_calendar` for calendar operations.

## State and operation

The Modal volume `economic-calendar-state` preserves weekly message IDs, report pages and pin status. Local runs use `.calendar-state/state.json`, overridable with `CALENDAR_STATE_PATH`. Do not delete production state to test formatting. Existing messages keep their original formatting; use `--manual-send` to publish a new real overview. Provider errors fail visibly instead of being treated as empty calendars. Multi-page reports preserve all events and repeat day headings as needed.

Avoid overlapping manual and scheduled runs or multiple deployments using the same state. A crash between Discord accepting a message and saving its ID may still produce a duplicate. The existing GitHub Actions workflow runs market briefs only.

## Optional consensus estimates

Set `CALENDAR_ESTIMATES_JSON` in `bot-secrets` to a JSON list. Each entry requires `date` (Bangkok release date, YYYY-MM-DD), `event` (exact English XOOMAR eventName), numeric `value`, `unit`, `basis` (e.g. headline CPI YoY versus core CPI MoM), and `source` (where the consensus came from).

Verify that series, reference period and units match. Do not substitute a previous reading, inflation target or illustrative number for consensus. Matching is by event name and Bangkok date; old dates are ignored. Reports show supplied values with their basis/source and, for inflation, above/below/equal scenarios. Missing consensus is never invented. Redeploy after updating secrets.

## Standalone API test

Import `postman/XOOMAR.postman_collection.json` into Postman; no environment or authentication is needed. Request 1 fetches the default calendar, and request 2 calculates the current Bangkok week's UTC date parameters. Inspect `data`, `scheduledAt`, and `importance`. Optional collection variables `from_date` and `to_date` override dates. FMP files are retained as legacy diagnostics only.
