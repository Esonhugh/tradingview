# TradingView Claude Code and Codex Plugin

TradingView data access via persistent headless Chrome with automatic lifecycle management. Multi-timeframe K-line history and built-in technical indicators.

## Features

- **17 slash commands** covering K-line history, technical indicators, quotes, options, screener, news, watchlists, alerts, chart state, and screenshots
- **K-line / Candlestick history** — all timeframes from 1-minute to monthly, extracted via CDP from the chart's internal data store
- **Technical indicators** — MACD, RSI, KDJ, Bollinger Bands, EMA, SMA computed locally on extracted data
- **Dual plugin manifests** — supports Claude Code (`.claude-plugin/plugin.json`) and Codex (`.codex-plugin/plugin.json`)
- **Persistent Chrome profile** in host-specific plugin data — Codex uses `~/.codex/plugins/data/.chrome-profiles/tradingview`, Claude uses `~/.claude/plugins/data/.chrome-profiles/tradingview`
- **Cross-session cookie persistence** — session cookies are saved to disk and auto-restored when the browser restarts, no re-login needed
- **Plugin monitor** — Chrome auto-launches, health-checks every 10s, auto-restarts on crash, port conflict resolution
- **Proxy support** — respects `HTTPS_PROXY`/`HTTP_PROXY` environment variables
- **4 skills** for general TradingView usage plus guided screener, options, and news workflows

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

# 2. First-time login (non-interactive, no browser window needed)
/tradingview:login-email --email=you@example.com --password=yourpassword

# 3. Session cookies are persisted to disk automatically
#    They survive browser restarts and new Claude/Codex sessions

# 4. Done! The plugin monitor auto-launches headless Chrome on every session
```

For accounts with 2FA enabled, use `/tradingview:login-interactive` instead (opens a visible browser window).

## Commands

| Command | Description |
|---------|-------------|
| `/tradingview:preflight` | Verify prerequisites (uv, deps, profile) |
| `/tradingview:launch` | Launch Chrome with persistent profile |
| `/tradingview:login-email` | Non-interactive email/password login |
| `/tradingview:login-interactive` | Open visible browser for manual/2FA login |
| `/tradingview:stop` | Stop the browser and monitor |
| `/tradingview:status` | Check connection status and open tabs |
| `/tradingview:quote <ticker>` | Get real-time spot quote |
| `/tradingview:kline <ticker>` | Fetch K-line history (multi-timeframe) with optional indicators |
| `/tradingview:options-chain <ticker>` | Fetch options chain with Greeks |
| `/tradingview:options-expiries <ticker>` | List available expiration dates |
| `/tradingview:screener` | Run stock/crypto/forex screener |
| `/tradingview:search <query>` | Search symbols by name |
| `/tradingview:news` | Fetch news headlines or read full story |
| `/tradingview:watchlists` | List/fetch watchlists or color flags |
| `/tradingview:alerts` | Fetch price alerts (list/active/triggered) |
| `/tradingview:chart-state` | Read current chart symbol and interval |
| `/tradingview:screenshot` | Capture chart as PNG |

Codex does not use these Claude slash-command files directly. Install the Codex plugin manifest and use the bundled `tradingview` skill, or run the same CLI from the plugin root:

```bash
cd <plugin-root>/scripts
uv run ./tradingview.py quote --ticker=AAPL --exchange=NASDAQ
```

## Skills (contextual triggers)

| Skill | Triggers |
|-------|----------|
| `tradingview` | "TradingView quote", "K-line history", "chart screenshot", "login to TradingView" |
| `screener` | "screen stocks", "find oversold", "market scan", "top volume" |
| `options-analysis` | "analyze options", "best expiry", "iron condor", "vertical spread" |
| `news-research` | "AAPL news", "why did X move", "market headlines", "sentiment" |

### Research Workflows

The TradingView skills can combine existing read-only commands into research workflows:

| Workflow | Combines | Use When |
|----------|----------|----------|
| Market Snapshot | `quote`, `kline`, `news` | You want a quick read on one symbol |
| Screener Brief | `screener`, optional `quote`/`kline` follow-up | You want a shortlist from market criteria |
| Options Research | `quote`, `options-expiries`, `options-chain` | You want expiry, chain, liquidity, and strategy framing |
| News Catalyst Review | `news`, optional `quote`/`kline` | You want to understand headlines, sentiment, and price reaction |

All workflows are read-only and provide research context rather than trade recommendations.

## Authentication

The plugin supports two login methods:

| Method | Command | When to Use |
|--------|---------|-------------|
| **Email/password** | `/tradingview:login-email` | Default. Works headlessly, no browser window |
| **Interactive** | `/tradingview:login-interactive` | Accounts with 2FA, or when email login fails |

Session cookies are automatically persisted to the host-specific Chrome profile. When a new browser session starts without cookies, they are auto-restored from disk — no re-login required across Claude/Codex sessions or browser restarts.

## Plugin Monitor (Auto-Launch)

The Claude plugin uses Claude Code's native `monitors` component to automatically manage Chrome. The Codex plugin includes a `SessionStart` hook that starts the same monitor when plugin hooks are enabled; Codex plugin hooks are disabled by default in the current release, so enable `[features].plugin_hooks = true` for auto-start or run `uv run ./tradingview.py launch` manually.

- **Auto-start**: Monitor launches headless Chrome when the plugin loads
- **Health checks**: CDP connectivity verified every 10 seconds
- **Auto-restart**: If Chrome crashes, the monitor restarts it (up to 3 attempts)
- **Port conflict resolution**: If port 9333 is busy, auto-selects next available port
- **State file**: Monitor writes state to `.monitor.json` for CLI commands to read

The monitor outputs status lines to stdout, which the host receives as notifications/logs (e.g., "Chrome launched", "Chrome restarted after crash").

After first-time login setup, all data commands work seamlessly without manual browser management.

## Architecture

```
tradingview/
├── .claude-plugin/plugin.json  # Plugin manifest (v0.3.0)
├── .codex-plugin/plugin.json   # Codex plugin manifest (v0.3.0)
├── .agents/plugins/            # Codex repo marketplace entry
├── commands/                   # 17 slash commands
├── hooks/                      # Codex SessionStart hook
├── skills/                     # General and analysis workflow skills
├── monitors/                   # Plugin monitor (auto-manages Chrome)
│   └── monitors.json
└── scripts/                    # Python uv project
    ├── pyproject.toml
    ├── tradingview.py          # CLI: uv run ./tradingview.py <cmd>
    └── tradingview_cli/        # Python package
        ├── monitor.py          # Monitor daemon (health check, auto-restart)
        ├── browser.py          # Chrome lifecycle + cookie injection via CDP
        ├── client.py           # Cookie harvester + auto-restore + authenticated HTTP
        ├── commands.py         # Command implementations (quote, kline, screener, etc.)
        ├── indicators.py       # Technical indicators (MACD, RSI, KDJ, Bollinger, EMA/SMA)
        └── main.py             # CLI dispatcher
```

## Design Decisions

1. **Monitor-based lifecycle**: Plugin monitor daemon manages Chrome with health checks and auto-restart, replacing manual launch/hook patterns
2. **Persistent Chrome profile**: Login once per host-specific plugin data directory, access persists across all sessions
3. **Disk-backed cookie cache**: Session cookies saved to `.tv_session.json` and auto-restored into Chrome on new sessions — survives browser restarts without re-login
4. **CDP health check**: Uses HTTP GET to `/json/version` instead of PID checks (Chrome headless spawns child processes)
5. **Read-only by design**: No trade execution, alert creation, or watchlist modification
6. **uv project**: Fast, reproducible dependency management

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TV_CDP_PORT` | `9333` | Chrome DevTools Protocol port |
| `HTTPS_PROXY` | (none) | HTTP proxy for TradingView API requests |
| `HTTP_PROXY` | (none) | HTTP proxy (fallback) |

## License

MIT
