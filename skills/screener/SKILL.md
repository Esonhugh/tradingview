---
name: screener
description: "Use when analyzing market conditions, scanning for stocks matching criteria, building watchlists from screener results, or comparing sectors. Triggers: 'screen stocks', 'find stocks with', 'market scan', 'oversold stocks', 'top volume stocks', 'crypto screener'."
---

Guide Codex or Claude through constructing and interpreting TradingView screener queries for market analysis.

## Screener Workflow

1. Determine user's screening criteria (market, filters, columns, sort)
2. Construct the screener command with appropriate parameters
3. Execute and interpret results
4. Suggest follow-up actions (quotes, options, deeper analysis)

## Running the Screener

```bash
cd "${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}}/scripts" && uv run ./tradingview.py screener [options]
```

## Available Markets

- US: `america` | UK: `uk` | Asia: `japan`, `china`, `india`, `korea`, `hongkong`
- Europe: `germany`, `france`, `italy`, `spain`, `switzerland`
- Other: `brazil`, `australia`, `canada`, `russia`
- Asset classes: `crypto`, `forex`, `futures`, `bond`

## Common Column Names

Price: `close`, `change`, `change_abs`, `high`, `low`, `open`, `volume`
Fundamentals: `market_cap_basic`, `price_earnings_ttm`, `earnings_per_share_basic_ttm`, `dividend_yield_recent`
Technicals: `RSI`, `MACD.macd`, `MACD.signal`, `BB.upper`, `BB.lower`, `EMA20`, `SMA50`, `SMA200`, `ADX`, `ATR`
Timeframe suffix: Append `|60` for 1h, `|240` for 4h, `|1W` for weekly (e.g. `RSI|60`)

## Filter Syntax

Filters use TradingView's `filter2` operator format:
```json
[{"operation": {"operator": "less", "operands": ["RSI", 30]}}]
```

Operators: `equal`, `not_equal`, `greater`, `less`, `in_range`, `not_in_range`, `has`, `crosses_above`, `crosses_below`

## Preset Screens

- RSI oversold: `--filter='[{"operation":{"operator":"less","operands":["RSI",30]}}]'`
- High volume breakout: `--filter='[{"operation":{"operator":"greater","operands":["volume",5000000]}},{"operation":{"operator":"greater","operands":["change",3]}}]'`
- Value stocks: `--filter='[{"operation":{"operator":"less","operands":["price_earnings_ttm",15]}},{"operation":{"operator":"greater","operands":["market_cap_basic",10000000000]}}]'`

## Interpreting Results

After running, present results as a table and highlight:
- Top movers by change %
- Unusual volume (relative to average)
- Extreme technical readings (RSI <30 or >70)
- Suggest `/tradingview:quote` for individual stocks of interest
