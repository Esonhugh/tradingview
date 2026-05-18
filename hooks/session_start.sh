#!/usr/bin/env bash
set -euo pipefail

PLUGIN_DIR="${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-}}}"
if [ -z "$PLUGIN_DIR" ]; then
  PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "[tradingview-monitor] uv not found; install uv before using the TradingView plugin."
  exit 0
fi

cd "$PLUGIN_DIR/scripts"

status="$(uv run ./tradingview.py status 2>/dev/null || true)"
if printf '%s' "$status" | grep -q '"running": true'; then
  echo "[tradingview-monitor] browser already running"
  exit 0
fi

nohup uv run python -m tradingview_cli.monitor --headless >/tmp/tradingview-codex-monitor.log 2>&1 &
echo "[tradingview-monitor] starting background browser monitor"
