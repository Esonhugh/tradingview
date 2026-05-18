---
name: tradingview
description: "Use when the user wants TradingView market data, quotes, K-line/candlestick history, technical indicators, options chains, screeners, news, watchlists, alerts, chart state, screenshots, or TradingView login/setup help."
---

Use the bundled TradingView CLI for read-only market data and chart automation.

## Locate the Plugin

Use the first available plugin root environment variable:

```bash
PLUGIN_DIR="${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-}}}"
cd "$PLUGIN_DIR/scripts"
```

If no plugin root variable is available, ask the user for the installed plugin path.

## Setup

```bash
uv sync
uv run ./tradingview.py status
```

For first-time authentication:

```bash
uv run ./tradingview.py login-email --email=user@example.com --password=secret
```

Use interactive login for 2FA accounts:

```bash
uv run ./tradingview.py login-interactive --port=9333
```

## Core Commands

```bash
uv run ./tradingview.py quote --ticker=AAPL --exchange=NASDAQ
uv run ./tradingview.py kline --ticker=AAPL --exchange=NASDAQ --resolution=D --bars=100 --indicators=macd,rsi,kdj
uv run ./tradingview.py options-expiries --ticker=AAPL --exchange=NASDAQ
uv run ./tradingview.py options-chain --ticker=AAPL --exchange=NASDAQ --strikes-around-spot=10
uv run ./tradingview.py screener --market=america --limit=50
uv run ./tradingview.py news --symbol=NASDAQ:AAPL --limit=10
uv run ./tradingview.py watchlists
uv run ./tradingview.py alerts --type=list
uv run ./tradingview.py chart-state
uv run ./tradingview.py screenshot --output=chart.png
```

## Notes

- This plugin is read-only: do not place trades, create alerts, or modify watchlists.
- The Chrome profile is host-specific by default: Codex uses `~/.codex/plugins/data/.chrome-profiles/tradingview`; Claude uses `~/.claude/plugins/data/.chrome-profiles/tradingview`.
- `TRADINGVIEW_DATA_DIR` or `TRADINGVIEW_PROFILE_DIR` can override the default storage location.
