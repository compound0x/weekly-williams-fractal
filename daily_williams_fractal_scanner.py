import io
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
import yfinance as yf


OUTPUT_DIR = Path("daily-williams-fractal-report")
OUTPUT_FILE = OUTPUT_DIR / "index.html"

FRACTAL_PERIOD = 10
MAX_FRACTAL_AGE_DAYS = 5
MIN_PRICE = 10.0
MIN_DOLLAR_VOLUME = 20_000_000
ET = ZoneInfo("America/New_York")


def normalize_columns(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def get_sp500_tickers():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    tables = pd.read_html(io.StringIO(response.text))
    return tables[0]["Symbol"].tolist()


def get_daily_data(ticker):
    ticker = ticker.replace(".", "-")
    stock = yf.Ticker(ticker)
    df = stock.history(period="3y", interval="1d", auto_adjust=False)
    if df.empty:
        return None
    df = normalize_columns(df)
    df = df.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
    return df


def latest_completed_day_index(df):
    """Return the latest daily bar that has definitely closed in New York time."""
    if df is None or df.empty:
        return None

    today_et = pd.Timestamp.now(tz=ET).normalize()
    last_idx = pd.Timestamp(df.index[-1])
    last_date = last_idx.tz_convert(ET).normalize() if last_idx.tzinfo else last_idx.tz_localize(ET).normalize()

    # NYSE regular session closes at 4:00 PM ET. If today's bar exists before
    # the close, exclude it; after the close it is considered completed.
    now_et = pd.Timestamp.now(tz=ET)
    if last_date >= today_et and now_et.hour < 16:
        return len(df) - 2 if len(df) >= 2 else None

    # If today's row is present after 4 PM ET, it is the completed session.
    # If the latest row is an older trading day, it is already completed.
    return len(df) - 1


def add_williams_fractal(df, period=FRACTAL_PERIOD):
    """Calculate confirmed Williams fractals using period bars on each side."""
    df = df.copy()
    lows = df["Low"].to_numpy(dtype=float)
    highs = df["High"].to_numpy(dtype=float)

    down = np.full(len(df), False, dtype=bool)
    up = np.full(len(df), False, dtype=bool)

    for i in range(period, len(df) - period):
        left_lows = lows[i - period:i]
        right_lows = lows[i + 1:i + period + 1]
        left_highs = highs[i - period:i]
        right_highs = highs[i + 1:i + period + 1]

        down[i] = lows[i] < left_lows.min() and lows[i] < right_lows.min()
        up[i] = highs[i] > left_highs.max() and highs[i] > right_highs.max()

    df["williams_down_fractal_10"] = down
    df["williams_up_fractal_10"] = up
    return df


def find_recent_fractal(df, completed_idx):
    """Find the newest confirmed bullish/down fractal no older than 5 sessions."""
    if completed_idx is None:
        return None

    start = max(FRACTAL_PERIOD, completed_idx - MAX_FRACTAL_AGE_DAYS)
    candidates = []
    for idx in range(start, completed_idx + 1):
        if bool(df["williams_down_fractal_10"].iloc[idx]):
            candidates.append((idx, completed_idx - idx))

    if not candidates:
        return None
    return max(candidates, key=lambda x: x[0])


def scan_stock(ticker):
    df = get_daily_data(ticker)
    if df is None or len(df) < (FRACTAL_PERIOD * 2 + MAX_FRACTAL_AGE_DAYS + 5):
        return None

    completed_idx = latest_completed_day_index(df)
    if completed_idx is None:
        return None

    completed = df.iloc[:completed_idx + 1].copy()
    if len(completed) < FRACTAL_PERIOD * 2 + 1:
        return None

    completed = add_williams_fractal(completed)
    fractal_info = find_recent_fractal(completed, len(completed) - 1)
    if fractal_info is None:
        return None

    fractal_idx, age = fractal_info
    current = completed.iloc[-1]
    fractal = completed.iloc[fractal_idx]

    close = float(current["Close"])
    volume = float(current["Volume"])
    dollar_volume = close * volume
    if close < MIN_PRICE or dollar_volume < MIN_DOLLAR_VOLUME:
        return None

    recent_high_20 = float(completed["High"].iloc[-20:].max())
    recent_low_20 = float(completed["Low"].iloc[-20:].min())
    daily_change = (close / float(completed["Close"].iloc[-2]) - 1) if len(completed) >= 2 else 0

    return {
        "ticker": ticker.replace(".", "-"),
        "signal_date": pd.Timestamp(fractal.name).date().isoformat(),
        "latest_completed_day": pd.Timestamp(current.name).date().isoformat(),
        "fractal_age": age,
        "fractal_low": float(fractal["Low"]),
        "fractal_high": float(fractal["High"]),
        "current_price": close,
        "daily_change": daily_change,
        "recent_high_20": recent_high_20,
        "recent_low_20": recent_low_20,
        "volume": volume,
        "dollar_volume": dollar_volume,
    }


def generate_html(results, scan_time_utc):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = sorted(results, key=lambda x: (x["fractal_age"], -x["daily_change"]))

    if not results:
        body = """
        <div class='empty'>
          No S&amp;P 500 stocks currently have a confirmed bullish Williams Fractal 10
          within the latest 5 completed daily candles.
        </div>
        """
    else:
        cards = []
        for rank, row in enumerate(results, 1):
            age_label = "latest completed day" if row["fractal_age"] == 0 else f"{row['fractal_age']} trading day(s) ago"
            daily_change = row["daily_change"] * 100
            cards.append(f"""
            <section class='card'>
              <div class='rank'>#{rank}</div>
              <div class='title-row'>
                <h2>{row['ticker']}</h2>
                <span class='badge'>BULLISH FRACTAL 10</span>
              </div>
              <p class='summary'>Confirmed Williams Fractal 10 on the daily chart. Fractal occurred <strong>{age_label}</strong> and is inside the maximum 5-session signal window.</p>
              <div class='grid'>
                <div><b>Fractal day</b><span>{row['signal_date']}</span></div>
                <div><b>Latest completed day</b><span>{row['latest_completed_day']}</span></div>
                <div><b>Fractal low</b><span>${row['fractal_low']:.2f}</span></div>
                <div><b>Current close</b><span>${row['current_price']:.2f}</span></div>
                <div><b>Daily change</b><span>{daily_change:+.1f}%</span></div>
                <div><b>20-day high</b><span>${row['recent_high_20']:.2f}</span></div>
                <div><b>20-day low</b><span>${row['recent_low_20']:.2f}</span></div>
                <div><b>Dollar volume</b><span>${row['dollar_volume']:,.0f}</span></div>
              </div>
            </section>
            """)
        body = "\n".join(cards)

    html = f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>Daily Williams Fractal 10 Scanner</title>
<style>
body{{font-family:Arial,sans-serif;background:#f5f7fa;color:#1f2937;max-width:1000px;margin:auto;padding:24px}}
h1{{margin-bottom:6px}} .sub{{color:#6b7280;margin-top:0}}
.banner{{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:16px;margin:18px 0}}
.card{{position:relative;background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:20px;margin:16px 0;box-shadow:0 3px 10px rgba(0,0,0,.04)}}
.rank{{position:absolute;right:18px;top:18px;color:#6b7280;font-weight:700}}
.title-row{{display:flex;align-items:center;gap:12px;padding-right:50px}} h2{{margin:0}}
.badge{{font-size:12px;font-weight:700;border:1px solid #16a34a;border-radius:999px;padding:5px 9px}}
.summary{{color:#4b5563;line-height:1.5}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-top:16px}}
.grid div{{background:#f8fafc;border-radius:10px;padding:12px}} .grid b{{display:block;font-size:12px;color:#6b7280;margin-bottom:4px}} .grid span{{font-weight:700}}
.empty{{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:25px;text-align:center;color:#6b7280}}
footer{{color:#6b7280;font-size:12px;margin-top:24px}}
</style>
</head>
<body>
<h1>Daily Williams Fractal 10 Scanner</h1>
<p class='sub'>S&amp;P 500 daily scanner • bullish/down fractal • period 10 • maximum signal age 5 completed trading sessions</p>
<div class='banner'>
  <strong>Scan logic:</strong> only completed daily candles are used. A bullish Williams Fractal 10 is a daily low that is strictly lower than the lows of the 10 trading sessions before and after it. A signal remains valid for up to 5 completed trading sessions after the fractal is confirmed.
  <br><br><strong>Last scan:</strong> {scan_time_utc} UTC
</div>
{body}
<footer>Automated daily scan. Data supplied by Yahoo Finance via yfinance. This dashboard is informational and not financial advice.</footer>
</body>
</html>"""

    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"Dashboard saved to {OUTPUT_FILE}")


def main():
    print("Loading S&P 500 universe...")
    tickers = get_sp500_tickers()
    results = []

    for i, ticker in enumerate(tickers, 1):
        try:
            result = scan_stock(ticker)
            if result:
                results.append(result)
                print(f"[{i}/{len(tickers)}] {ticker}: SIGNAL")
        except Exception as exc:
            print(f"[{i}/{len(tickers)}] {ticker}: skipped ({exc})")

    scan_time = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M:%S")
    generate_html(results, scan_time)
    print(f"Qualified setups: {len(results)}")


if __name__ == "__main__":
    main()
