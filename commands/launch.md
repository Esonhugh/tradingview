---
description: "Launch TradingView browser with persistent Chrome profile for data access"
argument-hint: "[--headless=false] [--port=9333]"
allowed-tools: ["Bash"]
---

Launch or ensure the TradingView Chrome browser is running with persistent profile at `~/.claude/plugins/data/.chrome-profiles/tradingview`.

> **Note:** In normal operation, the plugin monitor automatically launches and manages Chrome in headless mode. This command is mainly useful for visible-mode login or manual troubleshooting.

## Prerequisites

Requires `uv` installed. Check first:
```bash
command -v uv || echo "ERROR: Install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"
```

## Usage

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run ./tradingview.py launch [--headless=false] [--port=9333]
```

Options:
- `--headless=false`: Show the browser window (useful for first-time login)
- `--port=9333`: CDP debugging port (default 9333)

## First-Time Setup

On first launch, use `--headless=false` so the user can log into TradingView manually. The session persists in the Chrome profile.

## Output

Returns JSON with: `status`, `port`, `pid`, `monitor_pid`, `profile_dir`
