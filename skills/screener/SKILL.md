---
name: screener
description: >
  Use when analyzing market conditions, scanning for stocks or crypto matching criteria,
  drafting shortlist candidates from screener results, comparing sectors, finding oversold/overbought names,
  top volume stocks, breakout candidates, value screens, 股票筛选, 市场扫描, 超卖股票,
  放量突破, or crypto/forex/futures screeners.
---

Guide TradingView screener workflows from user criteria to an interpretable shortlist. Follow the user's language for the response.

## Workflow

1. Identify market: country/asset class, defaulting to `america` for US stocks when unspecified.
2. Identify filter intent: technical, fundamental, liquidity, momentum, value, or custom JSON.
3. Choose columns that explain the screen; avoid returning columns that will not be interpreted.
4. Run the screener command.
5. Interpret results as a shortlist and suggest targeted follow-up checks.

## Running the Screener

```bash
cd "${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}}/scripts" && uv run ./tradingview.py screener [options]
```

## Available Markets

- US: `america` | UK: `uk` | Asia: `japan`, `china`, `india`, `korea`, `hongkong`
- Europe: `germany`, `france`, `italy`, `spain`, `switzerland`
- Other: `brazil`, `australia`, `canada`, `russia`
- Asset classes: `crypto`, `forex`, `futures`, `bond`

## Common Column Sets

- Momentum: `name,description,close,change,change_abs,volume,RSI,MACD.macd,EMA20,SMA50`
- Liquidity: `name,description,close,volume,market_cap_basic,change,change_abs`
- Value: `name,description,close,market_cap_basic,price_earnings_ttm,dividend_yield_recent,earnings_per_share_basic_ttm`
- Trend: `name,description,close,EMA20,SMA50,SMA200,ADX,ATR,RSI`

Timeframe suffix: append `|60` for 1h, `|240` for 4h, `|1W` for weekly.

## Preset Screens

- RSI oversold: `--filter='[{"operation":{"operator":"less","operands":["RSI",30]}}]'`
- High volume breakout: `--filter='[{"operation":{"operator":"greater","operands":["volume",5000000]}},{"operation":{"operator":"greater","operands":["change",3]}}]'`
- Value stocks: `--filter='[{"operation":{"operator":"less","operands":["price_earnings_ttm",15]}},{"operation":{"operator":"greater","operands":["market_cap_basic",10000000000]}}]'`

## Output Format

Return:

1. **Screen Setup** — market, filters, sort, columns, limit.
2. **Top Results** — compact table, default top 10 even if more rows are returned.
3. **What Stands Out** — momentum, volume, valuation, or technical extremes.
4. **Risks in the Screen** — liquidity, stale fundamentals, crowded themes, or false positives.
5. **Follow-up Checks** — suggest quote, kline, news, or options-chain checks for 2-3 symbols.

## Guardrails

- Explain filter logic before interpreting results.
- Do not call screened names buys or sells.
- If the screen returns too many rows, summarize top 10 and mention the total count.
