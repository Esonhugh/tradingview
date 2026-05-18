---
description: "Read current chart symbol, interval, and layout from browser"
argument-hint: "[--tab=<tab_id>]"
allowed-tools: ["Bash"]
---

Read the current chart state (symbol, interval, layout ID) from an open TradingView chart tab via CDP.

## Usage

```bash
cd "${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}}/scripts" && uv run ./tradingview.py chart-state [--tab=<tab_id>]
```

## Arguments

- `--tab`: Specific tab ID (from `/tradingview:status`). If omitted, auto-selects the first chart tab.

## Output

JSON with: `tab_id`, `title`, `symbol`, `interval`, `layoutId`, `url`

## Requirements

Browser must be running (`/tradingview:launch`) with a TradingView chart page open.
