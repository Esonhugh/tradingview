---
name: news-research
description: "Use when researching market news, analyzing sentiment for a symbol, finding catalysts, or reviewing sector headlines. Triggers: 'what news on', 'AAPL news', 'market headlines', 'why did X move', 'read the article about', 'news sentiment'."
---

Guide Claude through TradingView news research and sentiment analysis.

## News Research Workflow

1. Fetch relevant headlines (by symbol, category, or broad)
2. Identify key stories
3. Read full stories for detail
4. Summarize catalysts and sentiment

## Core Commands

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts

# Fetch headlines for a symbol
uv run ./tradingview.py news --symbol=NASDAQ:AAPL --limit=10

# Fetch headlines by category
uv run ./tradingview.py news --category=market --limit=20

# Read full story
uv run ./tradingview.py news --id=<story_id>
```

## Available Filters

- `--symbol`: TradingView symbol (format: `EXCHANGE:TICKER`)
- `--category`: `market`, `economy`, `stock`, `crypto`, `forex`, `commodities`
- `--area`: Geographic area
- `--section`: News section
- `--provider`: Specific news provider
- `--lang`: Language code (default `en`)

## Analysis Steps

1. **Scan Headlines**: Pull 10-20 recent headlines for context
2. **Identify Movers**: Correlate with price action from `/tradingview:quote`
3. **Deep Read**: Use `--id` to read full articles on key stories
4. **Summarize**: Provide bull/bear thesis based on news flow

## Output Format

Present findings as:
- **Key Headlines** with timestamps
- **Sentiment Assessment**: Bullish / Bearish / Neutral
- **Catalysts Identified**: Earnings, guidance, macro events
- **Suggested Actions**: Further research, related symbols to monitor
