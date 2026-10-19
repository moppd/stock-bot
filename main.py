import sys
import time
from src.config import DISCORD_WEBHOOK_URL
from src.market_data import get_all_market_data
from src.news_fetcher import fetch_top_us_news
from src.ai_analyzer import generate_market_outlook
from src.discord_sender import send_discord_report

def run():
    if not DISCORD_WEBHOOK_URL:
        print("[Error] DISCORD_WEBHOOK_URL is missing!")
        sys.exit(1)

    print("[1/4] Fetching US Futures and Market Indicators...")
    market_data = get_all_market_data()

    print("[2/4] Fetching latest financial news...")
    news_items = fetch_top_us_news()

    print("[3/4] Generating AI analysis in Thai...")
    ai_summary = generate_market_outlook(market_data, news_items)

    print("[4/4] Sending Embed report to Discord...")
    for attempt in range(1, 4):
        try:
            send_discord_report(DISCORD_WEBHOOK_URL, market_data, news_items, ai_summary)
            print("Successfully sent morning brief to Discord!")
            break
        except Exception as e:
            print(f"Send attempt {attempt} failed: {e}")
            if attempt == 3:
                sys.exit(1)
            time.sleep(5 * attempt)

if __name__ == "__main__":
    run()
