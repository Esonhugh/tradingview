"""Shared filesystem paths for Claude and Codex plugin hosts."""

from __future__ import annotations

import os
from pathlib import Path

PLUGIN_NAME = "tradingview"


def _host_data_root() -> Path:
    """Return the host-specific plugin data directory.

    Defaults to the historical Claude path for backward compatibility. Codex
    sessions can select the Codex data root by setting PLUGIN_ROOT,
    CODEX_PLUGIN_ROOT, CODEX_HOME, or TRADINGVIEW_PLUGIN_HOST=codex.
    """
    override = os.environ.get("TRADINGVIEW_DATA_DIR")
    if override:
        return Path(override).expanduser()

    host = os.environ.get("TRADINGVIEW_PLUGIN_HOST", "").lower()
    is_codex = (
        host == "codex"
        or bool(os.environ.get("CODEX_HOME"))
        or bool(os.environ.get("CODEX_PLUGIN_ROOT"))
        or (
            bool(os.environ.get("PLUGIN_ROOT"))
            and not bool(os.environ.get("CLAUDE_PLUGIN_ROOT"))
        )
    )
    if is_codex:
        return Path.home() / ".codex" / "plugins" / "data"

    return Path.home() / ".claude" / "plugins" / "data"


def _profile_dir() -> Path:
    override = os.environ.get("TRADINGVIEW_PROFILE_DIR")
    if override:
        return Path(override).expanduser()
    return _host_data_root() / ".chrome-profiles" / PLUGIN_NAME


PROFILE_DIR = _profile_dir()
STATE_FILE = PROFILE_DIR / ".monitor.json"
COOKIE_CACHE_FILE = PROFILE_DIR / ".tv_session.json"
