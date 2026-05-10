---
description: "Search TradingView symbols by name, type, exchange, or country"
argument-hint: "<query> [--type=stock] [--exchange=NASDAQ] [--limit=30]"
allowed-tools: ["Bash"]
---

Search for symbols via TradingView's autocomplete/search API.

## Usage

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run ./tradingview.py search --query=<TEXT> [options]
```

## Arguments

- `--query` (required): Search text
- `--type`: Asset type filter: `stock`, `fund`, `index`, `futures`, `forex`, `crypto`, `economy`, `undefined`
- `--exchange`: Exchange filter (e.g. `NASDAQ`, `NYSE`, `BINANCE`)
- `--country`: Country code (e.g. `US`, `CN`, `JP`)
- `--lang`: Language code, default `en`
- `--limit`: Max results (default 30)
- `--offset`: Pagination offset

## Output

JSON with: `count`, `results[]` each having symbol details
