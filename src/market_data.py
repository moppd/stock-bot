from datetime import datetime, timezone
import yfinance as yf
from src.config import FUTURES_TICKERS, INDICATOR_TICKERS, TIMEZONE, MAG7_TICKERS

def _fetch_ticker_quote(symbol_id: str, ticker_symbol: str, name: str, unit: str = "") -> dict:
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # 1. ดึงแท่งเทียนรายวัน (1d) เพื่อหาราคาปิดของวันก่อนหน้า (Previous Day Close)
        daily_hist = ticker.history(period="5d", interval="1d")
        if daily_hist.empty:
            return {
                "symbol": symbol_id, "name": name, "status": "unavailable",
                "last_price": None, "change": None, "change_percent": None,
                "timestamp_str": "-", "unit": unit
            }

        # ราคาปิดของเมื่อวาน คือแท่งก่อนหน้าแท่งสุดท้ายของ Daily
        if len(daily_hist) >= 2:
            prev_close = float(daily_hist.iloc[-2]["Close"])
        else:
            prev_close = float(daily_hist.iloc[0]["Close"])

        # 2. ดึงราคาล่าสุดแบบ Real-time / ล่าสุดของเซสชัน (1m)
        intraday = ticker.history(period="1d", interval="1m")
        if not intraday.empty:
            last_row = intraday.iloc[-1]
            last_price = float(last_row["Close"])
            last_time = intraday.index[-1].to_pydatetime()
        else:
            last_row = daily_hist.iloc[-1]
            last_price = float(last_row["Close"])
            last_time = daily_hist.index[-1].to_pydatetime()

        # 3. คำนวณการเปลี่ยนแปลงเทียบกับราคาปิดเมื่อวาน (Daily Change)
        change = last_price - prev_close
        change_pct = (change / prev_close) * 100.0 if prev_close else 0.0

        # ป้องกันปัญหา -0.00% โดยถ้าใกล้ศูนย์มากๆ ให้เป็น 0.00 แบบไม่มีลบ
        if abs(change_pct) < 0.005:
            change_pct = 0.0
        if abs(change) < 0.005:
            change = 0.0

        # ตรวจสอบว่าตลาดปิด/ข้อมูลเก่าเกิน 4 ชม. หรือไม่
        now_utc = datetime.now(timezone.utc)
        age_hours = (now_utc - last_time.astimezone(timezone.utc)).total_seconds() / 3600.0
        status = "stale/closed" if age_hours > 4 else "live/delayed"

        local_time_dt = last_time.astimezone(TIMEZONE)
        timestamp_str = local_time_dt.strftime("%d/%m/%Y %H:%M น.")

        return {
            "symbol": symbol_id,
            "name": name,
            "status": status,
            "last_price": round(last_price, 2),
            "change": round(change, 2),
            "change_percent": round(change_pct, 2),
            "timestamp_str": timestamp_str,
            "unit": unit
        }
    except Exception:
        return {
            "symbol": symbol_id, "name": name, "status": "error",
            "last_price": None, "change": None, "change_percent": None,
            "timestamp_str": "-", "unit": unit
        }

def get_all_market_data() -> dict:
    futures_data = []
    for k, v in FUTURES_TICKERS.items():
        futures_data.append(_fetch_ticker_quote(k, v["symbol"], v["name"]))

    # ตรวจสอบ Timestamps ว่าตรงกันทั้ง 4 สัญญาหรือไม่
    available_timestamps = [f["timestamp_str"] for f in futures_data if f["status"] != "unavailable" and f["timestamp_str"] != "-"]
    all_timestamps_match = len(available_timestamps) > 0 and len(set(available_timestamps)) == 1
    common_timestamp = available_timestamps[0] if all_timestamps_match else None

    indicators_data = []
    for k, v in INDICATOR_TICKERS.items():
        indicators_data.append(_fetch_ticker_quote(k, v["symbol"], v["name"], v.get("unit", "")))

    return {
        "futures": futures_data,
        "futures_all_match": all_timestamps_match,
        "futures_common_timestamp": common_timestamp,
        "indicators": indicators_data
    }

def get_mag7_market_data() -> list:
    mag7_results = []
    for symbol, name in MAG7_TICKERS.items():
        try:
            ticker = yf.Ticker(symbol)
            # ดึงราคาย้อนหลัง 5 วัน เพื่อนำแท่งล่าสุดมาเทียบกับแท่งก่อนหน้า
            hist = ticker.history(period="5d", interval="1d")
            if len(hist) >= 2:
                last_price = float(hist.iloc[-1]["Close"])
                prev_close = float(hist.iloc[-2]["Close"])
                change = last_price - prev_close
                change_pct = (change / prev_close) * 100.0

                mag7_results.append({
                    "symbol": symbol,
                    "name": name,
                    "last_price": round(last_price, 2),
                    "change": round(change, 2),
                    "change_percent": round(change_pct, 2)
                })
        except Exception:
            continue
    return mag7_results
