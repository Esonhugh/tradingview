---
description: "Check TradingView plugin prerequisites (uv, dependencies, Chrome profile)"
allowed-tools: ["Bash"]
---

Verify all prerequisites for the TradingView plugin are met.

Run the preflight check:

```bash
# 1. Check uv is installed
if ! command -v uv &> /dev/null; then
    echo "ERROR: 'uv' is required but not installed."
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi
echo "uv: $(uv --version)"

# 2. Check dependencies are synced
cd ${CLAUDE_PLUGIN_ROOT}/scripts
if [ ! -d .venv ]; then
    echo "Dependencies not synced. Running uv sync..."
    uv sync
fi
echo "venv: OK"

# 3. Check CLI works
uv run ./tradingview.py status

# 4. Check Chrome profile
if [ -d ~/.claude/plugins/data/.chrome-profiles/tradingview ]; then
    echo "Chrome profile: EXISTS"
else
    echo "Chrome profile: NOT FOUND (will be created on first launch)"
fi
```

If any check fails, inform the user:
- **uv missing**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **deps missing**: `cd <plugin>/scripts && uv sync`
- **no profile**: Run `/tradingview:login` for first-time login
