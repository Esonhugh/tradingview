---
name: tradingview
description: >
  Use when the user wants TradingView market data, quotes, K-line/candlestick history,
  technical indicators, options chains, screeners, news, watchlists, alerts, chart state,
  screenshots, symbol search, TradingView login/setup help, market snapshots, trade idea research,
  股票报价, K线, 技术指标, 期权链, 股票筛选, 市场新闻, 图表截图, 自选列表, 价格提醒,
  搜索代码, 查找 ticker, or TradingView browser troubleshooting.
---

Use the bundled TradingView CLI for read-only market data and chart automation. Follow the user's language for the response.

## Safety Boundary

- This plugin is read-only: do not place trades, create alerts, edit watchlists, or modify chart layouts.
- Treat strategy and options comments as research framing, not financial advice.
- Do not invent prices, greeks, or news details not returned by the CLI.

## Locate the Plugin

Use the first available plugin root environment variable:

```bash
PLUGIN_DIR="${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-}}}"
cd "$PLUGIN_DIR/scripts"
```

If no plugin root variable is available, ask the user for the installed plugin path.

## Setup and Troubleshooting Router

Use these first when the user reports setup, login, browser, or data-access problems:

```bash
uv sync
uv run ./tradingview.py preflight
uv run ./tradingview.py status
```

Use browser lifecycle commands when status shows Chrome is stopped, stale, or no longer needed:

```bash
uv run ./tradingview.py launch --headless
uv run ./tradingview.py stop
```

For first-time authentication:

```bash
uv run ./tradingview.py login-email --email=user@example.com --password=secret
uv run ./tradingview.py login-interactive --port=9333
```

Use interactive login for 2FA accounts.

## Intent Router

| User Intent | Examples | Minimal Workflow |
|---|---|---|
| Symbol search | find ticker, lookup symbol, 搜索代码 | `search` before quote/kline when the exchange or symbol is uncertain |
| Quote | price, spot quote, 最新报价 | `quote` |
| K-line / indicators | candles, RSI, MACD, K线, 技术指标 | `kline` with requested resolution, bars, indicators |
| Market screening | oversold stocks, market scan, 股票筛选 | use the screener skill or `screener` command |
| News research | why did X move, catalyst, headlines, 新闻 | use the news-research skill or `news` + optional `quote`/`kline` |
| Options research | options chain, expiry, covered call, vertical spread, 期权链 | use the options-analysis skill with `options-expiries`, `options-chain`, `quote` |
| Watchlists / alerts | show my watchlist, active alerts | `watchlists` or `alerts --type=list`; read-only only |
| Chart automation | current chart, screenshot | `chart-state` or `screenshot` |
| Setup / login | browser not working, login, status | `preflight`, `status`, `launch`, `stop`, login commands |

## Research Workflows

### Market Snapshot

For "what is happening with SYMBOL" questions:

1. Run `quote`.
2. Run `kline` with daily bars and requested indicators when the user asks for trend context.
3. Run `news --symbol=EXCHANGE:SYMBOL --limit=10` when the user asks why it moved.
4. Present: price, daily move, trend context, news catalysts, and follow-up checks.

### Trade Idea Research

For research requests on a single symbol:

1. Run `quote`.
2. Run `kline` for the user's timeframe.
3. Run `news` for recent catalysts.
4. If options are mentioned, switch to the options-analysis workflow.
5. Present both bull and bear evidence. Do not tell the user to buy or sell.

## Core Commands

```bash
uv run ./tradingview.py search --query=Apple
uv run ./tradingview.py quote --ticker=AAPL --exchange=NASDAQ
uv run ./tradingview.py kline --ticker=AAPL --exchange=NASDAQ --resolution=D --bars=100 --indicators=macd,rsi,kdj
uv run ./tradingview.py options-expiries --ticker=AAPL --exchange=NASDAQ
uv run ./tradingview.py options-chain --ticker=AAPL --exchange=NASDAQ --strikes-around-spot=10
uv run ./tradingview.py screener --market=america --limit=50
uv run ./tradingview.py news --symbol=NASDAQ:AAPL --limit=10
uv run ./tradingview.py launch --headless
uv run ./tradingview.py stop
uv run ./tradingview.py watchlists
uv run ./tradingview.py alerts --type=list
uv run ./tradingview.py chart-state
uv run ./tradingview.py screenshot --output=chart.png
```

## Output Style

- Use compact tables for quotes, screeners, option chains, and watchlists.
- Use bullets for interpretation.
- End research answers with 2-3 concrete follow-up checks, not trade instructions.
- When commands fail, show the exact error and the next smallest diagnostic step.

## Storage Notes

- The Chrome profile is host-specific by default: Codex uses `~/.codex/plugins/data/.chrome-profiles/tradingview`; Claude uses `~/.claude/plugins/data/.chrome-profiles/tradingview`.
- `TRADINGVIEW_DATA_DIR` or `TRADINGVIEW_PROFILE_DIR` can override the default storage location.
