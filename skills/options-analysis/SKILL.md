---
name: options-analysis
description: >
  Use when analyzing options chains, expirations, implied volatility, Greeks, liquidity,
  payoff scenarios, covered calls, vertical spreads, iron condors, straddles, strangles,
  protective puts, collars, 期权链, 到期日, 隐含波动率, 希腊值, 备兑看涨, 垂直价差,
  跨式, 勒式, or options strategy research.
---

Guide TradingView options data analysis for research and strategy framing. Follow the user's language for the response.

## Workflow

1. Get the underlying quote first unless the user already provided a spot price.
2. Fetch available expiries.
3. Select expiry using the user's timeframe; default to 30-45 DTE only when the user asks for income or neutral premium strategies.
4. Fetch the options chain for the selected expiry.
5. Analyze liquidity first, then Greeks/IV, then payoff framing.
6. Present tradeoffs without telling the user to open the trade.

## Core Commands

```bash
cd "${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}}/scripts"
uv run ./tradingview.py quote --ticker=<SYM> --exchange=NASDAQ
uv run ./tradingview.py options-expiries --ticker=<SYM> --exchange=NASDAQ
uv run ./tradingview.py options-chain --ticker=<SYM> --exchange=NASDAQ --expiry=2025-06-20 --strikes-around-spot=10
```

## Strategy Templates

### Covered Call

- Look for 30-45 DTE when the user wants income.
- Focus on OTM calls, delta around 0.25-0.35 when available.
- Reject or warn on wide bid-ask spreads and low returned volume.

### Vertical Spread

- Use the user's directional thesis.
- Compare debit/credit, max profit, max loss, and breakeven.
- Prefer strikes with tighter spreads and higher returned volume when possible.

### Iron Condor

- Use only when the user asks for range-bound or neutral premium ideas.
- Start with short strikes around delta 0.15-0.20 when available.
- Warn when IV, liquidity, or event risk makes the setup fragile.

## Output Format

Return:

1. **Underlying Context** — spot price, daily move, and selected expiry.
2. **Chain Snapshot** — table with strike, type, bid, ask, mid, IV, delta, theta, and volume when available.
3. **Liquidity Check** — spread width, returned volume, and any strikes to avoid.
4. **Strategy Framing** — candidate structure, max risk/reward if derivable, breakeven, and assumptions.
5. **Risks & Follow-up** — earnings/events, liquidity, IV crush, assignment, and data staleness.

## Guardrails

- This is options research, not financial advice.
- Do not invent missing Greeks or premiums.
- If bid/ask and volume are missing, say liquidity cannot be assessed from returned data.
- Do not recommend execution; phrase conclusions as setups to review.
