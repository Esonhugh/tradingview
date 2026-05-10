---
description: "Fetch TradingView news headlines or read a full story"
argument-hint: "[--symbol=AAPL] [--id=<story_id>] [--category=...] [--limit=20]"
allowed-tools: ["Bash"]
---

Fetch news headlines from TradingView or read a full story by ID.

## Usage

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run ./tradingview.py news [options]
```

## Arguments

- `--id`: Story ID to fetch full article text
- `--symbol`: Filter headlines by symbol (e.g. `NASDAQ:AAPL`)
- `--category`: News category filter
- `--area`: Geographic area filter
- `--section`: Section filter
- `--provider`: News provider filter
- `--lang`: Language, default `en`
- `--limit`: Max headlines (default 20)

## Modes

1. **Headlines** (no --id): Returns list of recent headlines
2. **Full Story** (with --id): Returns full article with AST body flattened to text
