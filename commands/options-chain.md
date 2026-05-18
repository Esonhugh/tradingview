---
description: "Fetch full options chain for a ticker with strike/expiry filtering"
argument-hint: "<ticker> [--expiry=2025-06-20] [--type=call] [--strikes-around-spot=10]"
allowed-tools: ["Bash"]
---

Fetch the options chain for an underlying ticker from TradingView scanner API.

## Usage

```bash
cd "${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}}/scripts" && uv run ./tradingview.py options-chain --ticker=<SYMBOL> [options]
```

## Arguments

- `--ticker` (required): Underlying symbol, e.g. `AAPL`
- `--exchange`: Exchange, default `NASDAQ`
- `--expiry`: Filter by expiration date (YYYY-MM-DD)
- `--type`: Filter by `call` or `put`
- `--strikes-around-spot`: Number of strikes around current price (e.g. `10` returns 20 total)
- `--include-expired`: Include expired contracts (`true`/`false`)

## Output

JSON with: `underlying`, `count`, `chain[]` where each entry has:
`expiration`, `strike`, `option-type`, `bid`, `ask`, `mid`, `implied-volatility`, `delta`, `gamma`, `theta`, `vega`, `rho`, `open-interest`, `volume`

## Examples

- `/tradingview:options-chain AAPL --expiry=2025-06-20 --type=call --strikes-around-spot=5`
- `/tradingview:options-chain SPY --strikes-around-spot=10`
