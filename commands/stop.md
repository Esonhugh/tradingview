---
description: "Stop the TradingView browser monitor and Chrome instance"
allowed-tools: ["Bash"]
---

Stop the TradingView monitor daemon and its managed Chrome browser instance.

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run ./tradingview.py stop
```

Returns JSON with termination status. This stops both the monitor daemon process and the Chrome browser it manages.

> **Note:** If the plugin monitor is configured in `monitors/monitors.json`, Claude Code will auto-restart it on next session. Use this command to temporarily release resources or before switching to visible-mode login.
