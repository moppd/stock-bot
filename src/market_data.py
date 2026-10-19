from datetime import datetime, timezone
import yfinance as yf
from src.config import FUTURES_TICKERS, INDICATOR_TICKERS, TIMEZONE

def _fetch_ticker_quote(symbol_id: str, ticker_symbol: str, name: str) -> dict:
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="5d", interval="1m")
        if hist.empty:
            hist = ticker.history(period="5d")
            
        if hist.empty:
            return {
                "symbol": symbol_id,
                "name": name,
                "status": "unavailable",
                "last_price": None,
                "change": None,
                "change_percent": None,
                "timestamp_str": "-"
            }

        last_row = hist.iloc[-1]
        last_price = float(last_row["Close"])
        last_time = hist.index[-1].to_pydatetime()
        
        prev_close = ticker.fast_info.get("previous_close")
        if not prev_close and len(hist) > 1:
            prev_close = hist.iloc[-2]["Close"]

        change = (last_price - prev_close) if prev_close else 0.0
        change_pct = ((change / prev_close) * 100.0) if prev_close else 0.0

        now_utc = datetime.now(timezone.utc)
        age_hours = (now_utc - last_time.astimezone(timezone.utc)).total_seconds() / 3600.0
        status = "stale/closed" if age_hours > 4 else "live/delayed"

        local_time = last_time.astimezone(TIMEZONE).strftime("%d/%m/%Y %H:%M น. (เวลาไทย)")

        return {
            "symbol": symbol_id,
            "name": name,
            "status": status,
            "last_price": round(last_price, 2),
            "change": round(change, 2),
            "change_percent": round(change_pct, 2),
            "timestamp_str": local_time
        }
    except Exception:
        return {
            "symbol": symbol_id,
            "name": name,
            "status": "error",
            "last_price": None,
            "change": None,
            "change_percent": None,
            "timestamp_str": "-"
        }

def get_all_market_data() -> dict:
    futures_data = [_fetch_ticker_quote(k, v["symbol"], v["name"]) for k, v in FUTURES_TICKERS.items()]
    indicators_data = [_fetch_ticker_quote(k, v["symbol"], v["name"]) for k, v in INDICATOR_TICKERS.items()]
    return {"futures": futures_data, "indicators": indicators_data}
