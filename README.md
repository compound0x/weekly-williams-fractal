# weekly-williams-fractal

S&P 500 Williams Fractal 10 scanners for both **weekly and daily charts**, modeled after `daily-bullish-engulf`.

## Weekly scanner

- Universe: current S&P 500 constituents.
- Timeframe: **weekly**.
- Williams Fractal period: **10**.
- Bullish signal: a confirmed Williams down/bullish fractal, meaning the center week's low is strictly lower than the lows of the 10 weekly candles before and 10 weekly candles after it.
- Signal validity: the fractal can be the latest completed weekly candle or up to **5 completed weekly candles old**.
- The currently forming weekly candle is never used as the signal candle.
- Scheduled GitHub Actions run: Saturday after the weekly market candle has closed.

## Daily scanner

- Universe: current S&P 500 constituents.
- Timeframe: **daily**.
- Williams Fractal period: **10**.
- Bullish signal: a confirmed Williams down/bullish fractal, meaning the center day's low is strictly lower than the lows of the 10 trading sessions before and 10 trading sessions after it.
- Signal validity: the fractal can be the latest completed trading day or up to **5 completed trading sessions old**.
- The currently forming daily candle is never used as the signal candle.
- Scheduled GitHub Actions run: Monday-Friday at 21:00 UTC, after the US market close during EDT.

## Dashboards

The weekly workflow generates `weekly-williams-fractal-report/index.html` and publishes it under the `weekly-williams-fractal` GitHub Pages subdirectory.

The daily workflow generates `daily-williams-fractal-report/index.html` and publishes it under the `daily-williams-fractal` GitHub Pages subdirectory.

Both scanners use the same core signal concept, with the timeframe and completed-candle handling adapted to the respective chart.
