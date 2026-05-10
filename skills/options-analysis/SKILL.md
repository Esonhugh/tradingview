---
name: options-analysis
description: "Use when analyzing options strategies, finding optimal strikes/expiries, calculating payoff scenarios, or building options positions. Triggers: 'analyze options', 'best expiry for', 'options strategy', 'iron condor on', 'vertical spread', 'covered call analysis'."
---

Guide Claude through TradingView options data analysis for strategy evaluation.

## Options Analysis Workflow

1. Fetch available expiries for the underlying
2. Select relevant expiration(s)
3. Pull options chain data
4. Analyze Greeks, IV, and bid-ask spreads
5. Recommend strategy parameters

## Core Commands

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts

# Step 1: Check available expirations
uv run ./tradingview.py options-expiries --ticker=<SYM> --exchange=NASDAQ

# Step 2: Fetch chain for specific expiry
uv run ./tradingview.py options-chain --ticker=<SYM> --expiry=2025-06-20 --strikes-around-spot=10

# Step 3: Get spot price for reference
uv run ./tradingview.py quote --ticker=<SYM>
```

## Strategy Templates

### Covered Call
1. Get quote for current price
2. Get expiries → pick 30-45 DTE
3. Get calls at that expiry, OTM strikes
4. Look for: delta 0.25-0.35, decent premium, low bid-ask spread

### Vertical Spread (Bull Call)
1. Get expiries → pick target DTE
2. Get call chain at that expiry
3. Buy ATM call, sell OTM call
4. Evaluate: max profit, max loss, breakeven

### Iron Condor
1. Get expiries → pick 30-45 DTE
2. Get full chain (calls + puts)
3. Sell OTM call + OTM put (delta ~0.15-0.20)
4. Buy further OTM for protection
5. Calculate: credit received, max risk, probability of profit

## Key Metrics to Present

- **IV vs Historical**: Is implied vol high or low?
- **Bid-Ask Spread**: Wider = less liquid
- **Open Interest**: Higher = more liquid
- **Delta**: Probability proxy (|delta| ≈ ITM probability)
- **Theta**: Daily time decay
- **Gamma**: Rate of delta change

## Output Format

Present results as structured tables with:
- Strike, Type, Bid, Ask, Mid, IV, Delta, Theta, OI, Volume
- Highlight ATM strike
- Mark recommended strikes based on strategy
