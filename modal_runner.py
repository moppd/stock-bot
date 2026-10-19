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
    .add_local_dir(".", remote_path="/root")  # ซิงค์โค้ดในโฟลเดอร์ขึ้น Cloud
)

# ตั้งเวลา Cron (UTC): 23:05, 05:05, 11:05, 13:05 UTC = 06:05, 12:05, 18:05, 20:05 น. (เวลาไทย)
@app.function(
    image=image,
    schedule=modal.Cron("0 5,11,13,23 * * *"),
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