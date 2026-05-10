---
description: "Check TradingView browser connection status, monitor state, and open tabs"
allowed-tools: ["Bash"]
---

Check whether the TradingView browser is running (via the plugin monitor daemon) and list open TradingView tabs.

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run ./tradingview.py status
```

Returns JSON with: `running` (bool), `port`, `pid` (Chrome), `monitor_pid`, `headless`, `tabs[]` (TradingView pages with id/title/url), `endpoint`.
