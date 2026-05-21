---
name: news-research
description: >
  Use when researching TradingView market news, symbol headlines, catalysts, sentiment,
  sector headlines, why a stock moved, full story reading, 新闻, 催化剂, 市场头条,
  情绪分析, 个股新闻, 财经新闻, or reading a TradingView news story.
---

Guide TradingView news research from headlines to catalyst interpretation. Follow the user's language for the response.

## Workflow

1. Fetch headlines by symbol, category, area, section, provider, or language.
2. Identify stories that explain price movement, earnings, guidance, macro, regulation, M&A, product, or sector rotation.
3. Read full stories by ID only for the most relevant headlines.
4. Cross-check with quote or K-line only when the user asks about market reaction or why the symbol moved.
5. Summarize catalysts and uncertainty.

## Core Commands

```bash
cd "${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}}/scripts"
uv run ./tradingview.py news --symbol=NASDAQ:AAPL --limit=10
uv run ./tradingview.py news --category=market --limit=20
uv run ./tradingview.py news --id=<story_id>
uv run ./tradingview.py quote --ticker=AAPL --exchange=NASDAQ
```

## Available Filters

- `--symbol`: TradingView symbol, e.g. `NASDAQ:AAPL`.
- `--category`: `market`, `economy`, `stock`, `crypto`, `forex`, `commodities`.
- `--area`: geographic area.
- `--section`: news section.
- `--provider`: specific news provider.
- `--lang`: language code.

## Output Format

Return:

1. **Headline Brief** — table with time, source, headline, and story ID when available.
2. **Catalyst Map** — classify each major story as earnings, guidance, macro, rates, regulation, M&A, product, legal, sector, or other.
3. **Sentiment Read** — bullish, bearish, mixed, or neutral, with evidence.
4. **Market Reaction** — quote/K-line context only if fetched or provided.
5. **What to Watch Next** — follow-up data points, related symbols, upcoming events.

## Guardrails

- Separate confirmed article facts from interpretation.
- Do not infer sentiment from headlines alone when full story context is necessary; label it as tentative.
- If the user asks why a stock moved, include price reaction only after fetching quote or K-line data.
