---
description: "Fetch OHLCV candlestick (K-line) history with optional technical indicators"
argument-hint: "<ticker> [--exchange=NASDAQ] [--resolution=D] [--bars=100] [--indicators=macd,rsi,kdj]"
allowed-tools: ["Bash"]
---

Fetch historical candlestick (K-line) data from TradingView at various timeframes, with optional technical indicator computation.

## Usage

```bash
cd "${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}}/scripts" && uv run ./tradingview.py kline --ticker=<SYMBOL> [--exchange=NASDAQ] [--resolution=D] [--bars=100] [--indicators=macd,rsi,kdj]
```

## Arguments

- `--ticker` (required): Symbol to fetch, e.g. `AAPL`, `TSLA`, `BTC`
- `--exchange`: Exchange prefix, default `NASDAQ`. Use `NYSE`, `AMEX`, `BINANCE`, `SSE`, `SZSE`, etc.
- `--resolution`: Timeframe/interval. Default `D` (daily). Accepted values:
  - Minutes: `1`, `3`, `5`, `15`, `30`, `45` (or `1m`, `5m`, `15m`, `30m`)
  - Hours: `60`, `120`, `180`, `240` (or `1h`, `2h`, `3h`, `4h`)
  - Daily/Weekly/Monthly: `D`, `W`, `M` (or `1d`, `1w`, `1M`)
- `--bars`: Number of candles to return (max 5000). Default 100.
- `--indicators`: Comma-separated list of technical indicators to compute. Options:
  - `macd` — MACD line, signal line, histogram (12/26/9)
  - `rsi` — Relative Strength Index (14-period)
  - `kdj` — KDJ Stochastic Oscillator (9,3,3)
  - `boll` — Bollinger Bands (20-period, 2 std dev)
  - `ema20`, `ema50`, `ema200` — Exponential Moving Average (N-period)
  - `sma20`, `sma50`, `sma200` — Simple Moving Average (N-period)

## Output

JSON with: `symbol`, `resolution`, `count`, `candles[]`, `indicators{}`

Each candle: `{time, date, open, high, low, close, volume}`

Indicators section shows latest computed values for each requested indicator.

## Examples

- `/tradingview:kline AAPL` — 100 daily candles for Apple
- `/tradingview:kline AAPL --resolution=1h --bars=50` — 50 hourly candles
- `/tradingview:kline BTC --exchange=BINANCE --resolution=15m --bars=200` — 200x 15-min candles
- `/tradingview:kline AAPL --indicators=macd,rsi,kdj` — Daily candles + indicator summary
- `/tradingview:kline 600519 --exchange=SSE --resolution=D --bars=60 --indicators=macd,rsi,kdj,boll`

## Proxy

Set `HTTPS_PROXY=http://127.0.0.1:7890` env var if needed for network access.

## Requirements

Browser must be running and logged in (`/tradingview:launch` + `/tradingview:login-email`).
