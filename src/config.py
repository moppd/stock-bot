import os
import pytz

TIMEZONE = pytz.timezone(os.getenv("APP_TIMEZONE", "Asia/Bangkok"))
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

NEWS_LOOKBACK_HOURS = int(os.getenv("NEWS_LOOKBACK_HOURS", "24"))
NEWS_MAX_ITEMS = int(os.getenv("NEWS_MAX_ITEMS", "24"))

FUTURES_TICKERS = {
    "ES": {"symbol": "ES=F", "name": "E-mini S&P 500"},
    "NQ": {"symbol": "NQ=F", "name": "E-mini Nasdaq 100"},
    "YM": {"symbol": "YM=F", "name": "E-mini Dow"},
    "RTY": {"symbol": "RTY=F", "name": "E-mini Russell 2000"},
}

INDICATOR_TICKERS = {
    "US10Y": {"symbol": "^TNX", "name": "US 10Y Yield"},
    "DXY": {"symbol": "DX-Y.NYB", "name": "US Dollar Index"},
    "VIX": {"symbol": "^VIX", "name": "Volatility Index"},
    "Gold": {"symbol": "GC=F", "name": "Gold Futures"},
    "WTI": {"symbol": "CL=F", "name": "Crude Oil (WTI)"},
}
