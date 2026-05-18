---
description: "Run TradingView stock/crypto/forex screener with filters, sorting, and custom columns"
argument-hint: "[--market=america] [--sort=volume] [--limit=50] [--filter=JSON] [--columns=...] [--tickers=...]"
allowed-tools: ["Bash"]
---

Run the TradingView market screener with full filter/sort/column control.

## Usage

```bash
cd "${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}}/scripts" && uv run ./tradingview.py screener [options]
```

## Arguments

- `--market`: Market to scan. Supports:
  - Countries: `america`, `uk`, `japan`, `china`, `germany`, `france`, `india`, `brazil`, `australia`, etc. (~70 codes)
  - Asset classes: `crypto`, `forex`, `futures`, `bond`
- `--columns`: Comma-separated column names. Supports timeframe suffix: `RSI|60` (60m RSI). Default: `name,description,close,change,change_abs,volume,market_cap_basic,price_earnings_ttm`
- `--filter`: JSON filter clause array (TradingView filter2 format)
- `--sort`: Sort column, default `volume`
- `--order`: Sort order `asc`/`desc`, default `desc`
- `--tickers`: Explicit ticker list (comma-separated, format: `EXCHANGE:SYMBOL`)
- `--label-product`: Preset label/product filter
- `--limit`: Results per page (1-500, default 50)
- `--offset`: Pagination offset

## Filter Examples

RSI oversold stocks:
```bash
--filter='[{"operation":{"operator":"less","operands":["RSI",30]}}]'
```

Volume > 1M:
```bash
--filter='[{"operation":{"operator":"greater","operands":["volume",1000000]}}]'
```

## Output

JSON with: `market`, `count`, `total`, `rows[]` with requested columns
