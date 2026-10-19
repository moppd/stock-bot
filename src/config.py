import os
import pytz

TIMEZONE = pytz.timezone(os.getenv("APP_TIMEZONE", "Asia/Bangkok"))
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

NEWS_LOOKBACK_HOURS = int(os.getenv("NEWS_LOOKBACK_HOURS", "24"))
NEWS_MAX_ITEMS = int(os.getenv("NEWS_MAX_ITEMS", "12"))

# Tickers
FUTURES_TICKERS = {
    "ES": {"symbol": "ES=F", "name": "S&P 500"},
    "NQ": {"symbol": "NQ=F", "name": "Nasdaq 100"},
    "YM": {"symbol": "YM=F", "name": "Dow Jones"},
    "RTY": {"symbol": "RTY=F", "name": "Russell 2000"},
}

INDICATOR_TICKERS = {
    "US10Y": {"symbol": "^TNX", "name": "US 10Y Yield", "unit": "%"},
    "DXY": {"symbol": "DX-Y.NYB", "name": "US Dollar Index", "unit": "pts"},
    "VIX": {"symbol": "^VIX", "name": "Volatility Index", "unit": "pts"},
    "Gold": {"symbol": "GC=F", "name": "Gold Futures", "unit": "$/oz"},
    "WTI": {"symbol": "CL=F", "name": "Crude Oil (WTI)", "unit": "$/bbl"},
}

# Keywords สำหรับคัดแยกหมวดหมู่ข่าวอย่างเคร่งครัด
BIG_TECH_KEYWORDS = [
    "nvidia", "nvda", "microsoft", "msft", "apple", "aapl", "amazon", "amzn",
    "google", "googl", "goog", "alphabet", "meta", "tesla", "tsla", "amd",
    "semiconductor", "semiconductors", "chipmaker", "tsmc", "intel",
    "cloud infrastructure", "ai model", "openai", "generative ai"
]

GLOBAL_KEYWORDS = [
    "china", "beijing", "pboc", "japan", "boj", "yen", "ecb", "europe",
    "eurozone", "middle east", "oil output", "opec", "tariff", "tariffs",
    "trade war", "supply chain", "taiwan strait", "geopolitic"
]

# เพิ่มต่อท้ายใน src/config.py
MAG7_TICKERS = {
    "NVDA": "NVIDIA",
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "AMZN": "Amazon",
    "GOOGL": "Alphabet",
    "META": "Meta Platforms",
    "TSLA": "Tesla",
}