---
description: "Get real-time spot quote for a stock/crypto symbol"
argument-hint: "<ticker> [--exchange=NASDAQ]"
allowed-tools: ["Bash"]
---

Fetch a real-time spot quote from TradingView for a given ticker symbol.

## Usage

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run ./tradingview.py quote --ticker=<SYMBOL> [--exchange=NASDAQ]
```

## Arguments

- `--ticker` (required): Symbol to quote, e.g. `AAPL`, `TSLA`, `BTC`
- `--exchange`: Exchange prefix, default `NASDAQ`. Use `NYSE`, `AMEX`, `BINANCE`, etc.

## Output

JSON with: `symbol`, `close`, `change`, `change_abs`, `currency`, `high`, `low`, `open`, `prev_close_price`, `volume`, `description`

## Examples

- `/tradingview:quote AAPL` → Quote for Apple on NASDAQ
- `/tradingview:quote TSLA --exchange=NASDAQ`
- `/tradingview:quote BTC --exchange=BINANCE`
