---
description: "List available option expiration dates for a ticker"
argument-hint: "<ticker> [--exchange=NASDAQ]"
allowed-tools: ["Bash"]
---

List all available option expiration dates with DTE and contract counts.

## Usage

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run ./tradingview.py options-expiries --ticker=<SYMBOL> [--exchange=NASDAQ] [--include-expired=false]
```

## Arguments

- `--ticker` (required): Underlying symbol
- `--exchange`: Exchange, default `NASDAQ`
- `--include-expired`: Include past expirations

## Output

JSON with: `underlying`, `count`, `expiries[]` each having `expiry` (date), `dte` (days to expiry), `contracts` (count)
