---
description: "Open visible browser for TradingView login — for 2FA accounts or manual login"
argument-hint: "[--port=9333]"
allowed-tools: ["Bash"]
---

Launch Chrome in **visible (non-headless) mode** and navigate to TradingView login page. The user logs in manually; the session (cookies, localStorage) persists in `~/.claude/plugins/data/.chrome-profiles/tradingview` for all future headless commands.

## When to Use

- Account has 2FA enabled (use `login-email` for accounts without 2FA)
- When `login-email` fails and manual login is needed
- When cookies have expired and re-authentication is needed

## Steps

1. Stop any existing headless browser instance first:

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run ./tradingview.py stop
```

2. Launch in visible mode and navigate to login:

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run ./tradingview.py login-interactive --port=9333
```

3. **Tell the user** to complete login in the browser window that appears. Wait for their confirmation.

4. After user confirms login is done, verify the session works (this also auto-saves cookies to disk for future sessions):

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
- Session cookies are auto-saved to disk when harvested, so they survive browser restarts
- If the user has 2FA enabled, they will need to complete that in the browser window too
