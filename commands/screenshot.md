---
description: "Take a PNG screenshot of a TradingView chart tab"
argument-hint: "[--output=./chart.png] [--tab=<tab_id>]"
allowed-tools: ["Bash"]
---

Capture a PNG screenshot of an open TradingView chart tab via CDP.

## Usage

```bash
cd "${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}}/scripts" && uv run ./tradingview.py screenshot [--output=<path>] [--tab=<tab_id>]
```

## Arguments

- `--output`: Save path for the PNG. Default: `~/tradingview-<timestamp>.png`
- `--tab`: Specific tab ID. If omitted, auto-selects the first chart tab.

## Output

JSON with: `path` (saved file), `size_bytes`, `tab` (title)

## Requirements

Browser must be running with a TradingView chart page open.
