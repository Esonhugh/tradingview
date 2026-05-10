---
description: "Open visible browser for TradingView login — session persists in Chrome profile"
argument-hint: "[--port=9333]"
allowed-tools: ["Bash"]
---

Launch Chrome in **visible (non-headless) mode** and navigate to TradingView login page. The user logs in manually; the session (cookies, localStorage) persists in `~/.claude/plugins/data/.chrome-profiles/tradingview` for all future headless commands.

## When to Use

- First-time setup (no existing login session)
- When commands like `watchlists`, `alerts`, or `options-chain` return "unauthorized"
- When cookies have expired and re-authentication is needed

## Steps

1. Stop any existing headless browser instance first:

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run ./tradingview.py stop
```

2. Launch in visible mode and navigate to login:

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run ./tradingview.py login --port=9333
```

3. **Tell the user** to complete login in the browser window that appears. Wait for their confirmation.

4. After user confirms login is done, verify the session works:

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run ./tradingview.py watchlists
```

5. Stop the visible browser and restart headless:

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run ./tradingview.py stop && uv run ./tradingview.py launch
```

## Important

- Always **stop** the running headless browser before launching visible mode (they share the same profile and cannot run simultaneously)
- The login session persists across all future sessions — this only needs to be done once (or when cookies expire)
- If the user has 2FA enabled, they will need to complete that in the browser window too
