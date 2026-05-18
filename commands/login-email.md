---
description: "Non-interactive email/password login — no browser window needed"
argument-hint: "--email=<email> --password=<password>"
allowed-tools: ["Bash"]
---

Login to TradingView using email and password without opening a visible browser. Authenticates via HTTP, then injects session cookies into the headless Chrome profile.

## When to Use

- Headless/CLI environments where a visible browser is unavailable
- Automated setup without manual interaction
- When the interactive `login-interactive` command is not practical

## Usage

```bash
cd "${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}}/scripts" && uv run ./tradingview.py login-email --email=user@example.com --password=secret
```

## How It Works

1. POSTs email + password to TradingView's `/accounts/signin/` endpoint
2. Injects the resulting session cookies into the headless Chrome profile via CDP
3. Saves cookies to disk for auto-restore across sessions
4. Verifies the session works by fetching watchlists

## Limitations

- Does **not** support accounts with 2FA enabled — use `/tradingview:login-interactive` for those
- Requires a working network connection to tradingview.com

## After Login

The session persists in the Chrome profile. Session cookies are also saved to disk under the host-specific plugin data directory (`~/.codex/plugins/data/...` for Codex, `~/.claude/plugins/data/...` for Claude) and auto-restored on future browser restarts. All other commands (`watchlists`, `quote`, `alerts`, etc.) work immediately.
