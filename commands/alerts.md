---
description: "Fetch TradingView price alerts (list/active/triggered/offline/log)"
argument-hint: "[--type=list|active|triggered|offline|log]"
allowed-tools: ["Bash"]
---

Read-only access to TradingView price alerts.

## Usage

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run ./tradingview.py alerts [--type=list]
```

## Arguments

- `--type`: Alert endpoint type:
  - `list` (default) — All alerts
  - `active` — Currently active alerts
  - `triggered` — Recently triggered
  - `offline` — Offline fires
  - `log` — Alert log history

## Output

JSON with: `type`, `count`, `alerts[]` each with alert details and `symbol_clean` (parsed symbol)

## Note

Write operations (create/edit/remove/restart alerts) are intentionally NOT supported. Read-only access.
