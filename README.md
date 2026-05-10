# TradingView Claude Code Plugin

Read-only TradingView data access via persistent headless Chrome with automatic lifecycle management.

## Features

- **13 slash commands** covering quotes, options, screener, news, watchlists, alerts, chart state, and screenshots
- **Persistent Chrome profile** at `~/.claude/plugins/data/.chrome-profiles/tradingview` — login once, access forever
- **Plugin monitor** — Chrome auto-launches, health-checks every 10s, auto-restarts on crash, port conflict resolution
- **3 analysis skills** for guided screener, options, and news workflows

## Prerequisites

| Requirement | Install |
|-------------|---------|
| **uv** (required) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Python 3.11+ | Managed by uv automatically |
| Chrome/Chromium | System browser |

> **uv is mandatory.** The plugin will refuse to work without it. Run `/tradingview:preflight` to verify all prerequisites.

## Quick Start

```bash
# 1. Sync dependencies
cd <plugin-root>/scripts
uv sync

# 2. First-time: launch with visible browser for login
/tradingview:login

# 3. Log into TradingView in the browser window
#    Session persists in ~/.claude/plugins/data/.chrome-profiles/tradingview

# 4. Done! The plugin monitor auto-launches headless Chrome on every session
```

## Commands

| Command | Description |
|---------|-------------|
| `/tradingview:preflight` | Verify prerequisites (uv, deps, profile) |
| `/tradingview:launch` | Launch Chrome with persistent profile |
| `/tradingview:login` | Open visible browser for login |
| `/tradingview:stop` | Stop the browser and monitor |
| `/tradingview:status` | Check connection status and open tabs |
| `/tradingview:quote <ticker>` | Get real-time spot quote |
| `/tradingview:options-chain <ticker>` | Fetch options chain with Greeks |
| `/tradingview:options-expiries <ticker>` | List available expiration dates |
| `/tradingview:screener` | Run stock/crypto/forex screener |
| `/tradingview:search <query>` | Search symbols by name |
| `/tradingview:news` | Fetch news headlines or read full story |
| `/tradingview:watchlists` | List/fetch watchlists or color flags |
| `/tradingview:alerts` | Fetch price alerts (list/active/triggered) |
| `/tradingview:chart-state` | Read current chart symbol and interval |
| `/tradingview:screenshot` | Capture chart as PNG |

## Skills (contextual triggers)

| Skill | Triggers |
|-------|----------|
| `screener` | "screen stocks", "find oversold", "market scan", "top volume" |
| `options-analysis` | "analyze options", "best expiry", "iron condor", "vertical spread" |
| `news-research` | "AAPL news", "why did X move", "market headlines", "sentiment" |

## Plugin Monitor (Auto-Launch)

The plugin uses Claude Code's native `monitors` component to automatically manage Chrome:

- **Auto-start**: Monitor launches headless Chrome when the plugin loads
- **Health checks**: CDP connectivity verified every 10 seconds
- **Auto-restart**: If Chrome crashes, the monitor restarts it (up to 3 attempts)
- **Port conflict resolution**: If port 9333 is busy, auto-selects next available port
- **State file**: Monitor writes state to `.monitor.json` for CLI commands to read

The monitor outputs status lines to stdout, which Claude receives as notifications (e.g., "Chrome launched", "Chrome restarted after crash").

After first-time login setup, all data commands work seamlessly without manual browser management.

## Architecture

```
tradingview/
├── .claude-plugin/plugin.json  # Plugin manifest (v0.2.0)
├── commands/                   # 14 slash commands
├── skills/                     # 3 analysis workflow skills
├── monitors/                   # Plugin monitor (auto-manages Chrome)
│   └── monitors.json
└── scripts/                    # Python uv project
    ├── pyproject.toml
    ├── tradingview.py          # CLI: uv run ./tradingview.py <cmd>
    └── tradingview_cli/        # Python package
        ├── monitor.py          # Monitor daemon (health check, auto-restart)
        ├── browser.py          # Chrome lifecycle (reads monitor state)
        ├── client.py           # Cookie harvester + authenticated HTTP
        ├── commands.py         # Command implementations
        └── main.py             # CLI dispatcher
```

## Design Decisions

1. **Monitor-based lifecycle**: Plugin monitor daemon manages Chrome with health checks and auto-restart, replacing manual launch/hook patterns
2. **Persistent Chrome profile**: Login once at `~/.claude/plugins/data/.chrome-profiles/tradingview`, access persists across all sessions
3. **CDP health check**: Uses HTTP GET to `/json/version` instead of PID checks (Chrome headless spawns child processes)
4. **Read-only by design**: No trade execution, alert creation, or watchlist modification
5. **uv project**: Fast, reproducible dependency management

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TV_CDP_PORT` | `9333` | Chrome DevTools Protocol port |

## License

MIT
