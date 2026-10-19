import sys
import time
from datetime import datetime
from src.config import DISCORD_WEBHOOK_URL, TIMEZONE
from src.market_data import get_all_market_data, get_mag7_market_data
from src.news_fetcher import fetch_categorized_news
from src.ai_analyzer import generate_market_brief_analysis
from src.discord_sender import send_discord_report, send_mag7_report

def run(force_morning: bool = False):
    if not DISCORD_WEBHOOK_URL:
        print("[Error] DISCORD_WEBHOOK_URL is missing!")
        sys.exit(1)

    now = datetime.now(TIMEZONE)
    # เช็กว่าเป็นรอบเช้าหรือไม่ (ก่อน 10:00 น. หรือสั่งบังคับ force_morning)
    is_morning = (now.hour < 10) or force_morning

    print("[1/4] Fetching US Futures and Financial Indicators...")
    market_data = get_all_market_data()

    print("[2/4] Fetching categorized news...")
    categorized_news = fetch_categorized_news()

    print("[3/4] Generating AI Editorial Brief...")
    ai_analysis = generate_market_brief_analysis(market_data, categorized_news)

    print("[4/4] Sending Main Report to Discord...")
    for attempt in range(1, 4):
        try:
            # 1. ส่งการ์ดภาพรวมตลาดหลัก
            send_discord_report(DISCORD_WEBHOOK_URL, market_data, ai_analysis)
            print("Successfully posted US Market Brief!")
            break
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}")
            if attempt == 3:
                sys.exit(1)
            time.sleep(5 * attempt)

    # 2. ถ้าเป็นรอบเช้า หรือสั่ง force_morning จะส่งการ์ด 7 นางฟ้าแยกอีกข้อความ
    if is_morning:
        print("[Morning Session] Fetching and sending Mag 7 Stock Report...")
        try:
            mag7_data = get_mag7_market_data()
            send_mag7_report(DISCORD_WEBHOOK_URL, mag7_data)
            print("Successfully posted Mag 7 Report as a separate message!")
        except Exception as e:
            print(f"Failed to send Mag 7 report: {e}")

if __name__ == "__main__":
    run(force_morning=True)