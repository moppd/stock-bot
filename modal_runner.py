import modal

app = modal.App("us-futures-brief")

# สร้างสภาพแวดล้อม Python 3.12 บน Cloud และติดตั้ง Library ทั้งหมด
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "yfinance>=0.2.40",
        "feedparser>=6.0.11",
        "requests>=2.31.0",
        "openai>=1.40.0",
        "python-dateutil>=2.9.0",
        "pytz>=2024.1",
    )
    .add_local_python_source("src", "main", "calendar_runner")
)

# Market brief: Monday–Friday at 06:00 Bangkok.
@app.function(
    image=image,
    schedule=modal.Cron("0 23 * * 0-4"),  # รันเฉพาะจันทร์-ศุกร์ เวลา 06:00 น. (เวลาไทย)
    secrets=[modal.Secret.from_name("bot-secrets")],  # เรียกใช้ Secret ที่เราสร้างไว้
    timeout=300
)
def scheduled_run():
    import sys
    sys.path.append("/root")
    from main import run
    
    print("[Modal] Running US Futures Brief Job...")
    run()

# จุดเชื่อมสำหรับสั่งเทสต์รัน
@app.local_entrypoint()
def test():
    scheduled_run.remote()

# Calendar: Monday at 06:00 Bangkok.
calendar_volume = modal.Volume.from_name("economic-calendar-state", create_if_missing=True)


@app.function(
    image=image,
    schedule=modal.Cron("0 6 * * 1", timezone="Asia/Bangkok"),
    secrets=[modal.Secret.from_name("bot-secrets")],
    volumes={"/calendar-state": calendar_volume},
    max_containers=1,
    timeout=300,
)
def scheduled_calendar(dry_run: bool = False, test_send: bool = False, manual_send: bool = False):
    import os
    import sys
    sys.path.append("/root")
    if not (dry_run or test_send):
        calendar_volume.reload()
    os.environ["CALENDAR_STATE_PATH"] = "/calendar-state/state.json"
    from calendar_runner import run_calendar
    run_calendar(checkpoint=calendar_volume.commit, dry_run=dry_run, test_send=test_send, manual_send=manual_send)
