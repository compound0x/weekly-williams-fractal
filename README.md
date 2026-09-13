# weekly-williams-fractal

Weekly S&P 500 scanner modeled after `daily-bullish-engulf`, but using a **Williams Fractal 10 on the weekly chart** instead of bullish engulfing confirmation.

## Signal rules

- Universe: current S&P 500 constituents.
- Timeframe: **weekly**.
- Williams Fractal period: **10**.
- Bullish signal: a confirmed Williams down/bullish fractal, meaning the center week's low is strictly lower than the lows of the 10 weekly candles before and 10 weekly candles after it.
- Signal validity: the fractal can be the latest completed weekly candle or up to **5 completed weekly candles old**.
- The currently forming weekly candle is never used as the signal candle.
- If the workflow is run before the weekly candle has closed, it falls back to the most recent completed weekly candle and scans for a fractal up to 5 completed candles before it.
- The scheduled GitHub Actions run executes every Saturday, after the weekly market candle has closed.

## Dashboard

The workflow generates `weekly-williams-fractal-report/index.html` and publishes it under the `weekly-williams-fractal` GitHub Pages subdirectory.

Source scanner structure follows the same general pattern as the existing daily scanner, which generates an HTML report and deploys it through GitHub Actions. 
