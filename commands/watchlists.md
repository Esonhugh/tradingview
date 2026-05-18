---
description: "List TradingView watchlists or fetch specific watchlist/color flag"
argument-hint: "[--id=<list_id>] [--color=red|green|blue|...]"
allowed-tools: ["Bash"]
---

Read-only access to TradingView custom watchlists and color-flag lists.

## Usage

```bash
cd "${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}}/scripts" && uv run ./tradingview.py watchlists [options]
```

## Arguments

- `--id`: Fetch specific watchlist by ID
- `--color`: Fetch color-flag list (`red`, `orange`, `yellow`, `green`, `blue`, `purple`)

## Modes

1. **List all** (no args): Returns all custom watchlists
2. **By ID**: Returns symbols in a specific watchlist
3. **By Color**: Returns symbols with that color flag

## Note

Write operations (create/edit/delete) are intentionally NOT supported. Read-only access.
