---
description: "Non-interactive email/password login — no browser window needed"
argument-hint: "--email=<email> --password=<password>"
allowed-tools: ["Bash"]
---

Login to TradingView using email and password without opening a visible browser. Authenticates via HTTP, then injects session cookies into the headless Chrome profile.

## When to Use

- Headless/CLI environments where a visible browser is unavailable
- Automated setup without manual interaction
- When the interactive `login` command is not practical

## Usage

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts && uv run ./tradingview.py login-email --email=user@example.com --password=secret
```

## How It Works

1. Makes an HTTP request to TradingView to get a CSRF token
2. POSTs email + password to `/accounts/signin/`
3. Injects the resulting session cookies into the headless Chrome profile via CDP
4. Verifies the session works by fetching watchlists

## Limitations

- Does **not** support accounts with 2FA enabled — use the interactive `login` command for those
- Requires a working network connection to tradingview.com

## After Login

The session persists in the Chrome profile. All other commands (`watchlists`, `quote`, `alerts`, etc.) work immediately.
