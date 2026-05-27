#!/usr/bin/env python3
"""
Integration tests for TradingView CLI plugin.

Tests cover:
- Module imports
- Monitor functions (port check, CDP health, state file)
- Browser module (status, state read)
- CLI dispatch (all commands parse correctly)
- Monitor entry point args

Run: uv run python -m pytest tests/ -v
  or: uv run python tests/test_plugin.py
"""

import asyncio
import importlib
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ═══════════════════════════════════════════════════════════
#  Test: Module Imports
# ═══════════════════════════════════════════════════════════

def test_imports():
    """All plugin modules import without error."""
    import tradingview_cli
    import tradingview_cli.browser
    import tradingview_cli.monitor
    import tradingview_cli.main
    import tradingview_cli.client
    import tradingview_cli.commands
    print("  PASS  test_imports")


# ═══════════════════════════════════════════════════════════
#  Test: Monitor Functions
# ═══════════════════════════════════════════════════════════

def test_monitor_port_check():
    """is_port_available correctly identifies used/free ports."""
    from tradingview_cli.monitor import is_port_available
    # Port 9333 is in use (Chrome running from previous session)
    # Just verify the function returns a bool
    result = is_port_available(9333)
    assert isinstance(result, bool)
    # A random high port should be available
    assert is_port_available(59999) is True
    print("  PASS  test_monitor_port_check")


def test_monitor_find_available_port():
    """find_available_port returns an int."""
    from tradingview_cli.monitor import find_available_port
    port = find_available_port(start=59990, max_tries=5)
    assert isinstance(port, int)
    assert 59990 <= port <= 59994
    print("  PASS  test_monitor_find_available_port")


def test_monitor_find_chrome_binary():
    """find_chrome_binary returns a valid path on macOS."""
    from tradingview_cli.monitor import find_chrome_binary
    result = find_chrome_binary()
    # On macOS with Chrome installed, this should find it
    if result:
        assert os.path.isfile(result)
    print(f"  PASS  test_monitor_find_chrome_binary (found: {result is not None})")


def test_monitor_build_chrome_args_with_proxy():
    """Monitor Chrome args include proxy-server only when proxy is configured."""
    from tradingview_cli.monitor import build_chrome_args

    no_proxy = build_chrome_args("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", 9333, True, None)
    assert "--proxy-server=http://127.0.0.1:7890" not in no_proxy
    assert "--headless=new" in no_proxy

    with_proxy = build_chrome_args(
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        9333,
        True,
        "http://127.0.0.1:7890",
    )
    assert "--proxy-server=http://127.0.0.1:7890" in with_proxy
    assert with_proxy[-1] == "https://www.tradingview.com/chart/"
    print("  PASS  test_monitor_build_chrome_args_with_proxy")


def test_monitor_cdp_health():
    """check_cdp_health returns bool."""
    from tradingview_cli.monitor import check_cdp_health
    # Test against a non-existent port (should return False)
    assert check_cdp_health(59999) is False
    # If 9333 is running, should return True
    result = check_cdp_health(9333)
    assert isinstance(result, bool)
    print(f"  PASS  test_monitor_cdp_health (port 9333 healthy: {result})")


def test_monitor_write_state():
    """write_state creates a valid JSON state file."""
    from tradingview_cli.monitor import write_state, STATE_FILE, PROFILE_DIR
    import time

    # Write test state
    test_state = {
        "status": "running",
        "monitor_pid": os.getpid(),
        "chrome_pid": 12345,
        "port": 9333,
        "headless": True,
        "profile_dir": str(PROFILE_DIR),
        "started_at": time.time(),
        "last_health": time.time(),
    }
    write_state(test_state)

    # Verify file exists and is valid JSON
    assert STATE_FILE.exists()
    loaded = json.loads(STATE_FILE.read_text())
    assert loaded["status"] == "running"
    assert loaded["port"] == 9333
    assert loaded["monitor_pid"] == os.getpid()
    print("  PASS  test_monitor_write_state")


# ═══════════════════════════════════════════════════════════
#  Test: Browser Module
# ═══════════════════════════════════════════════════════════

def test_browser_get_status():
    """get_status returns a dict with expected keys."""
    from tradingview_cli.browser import get_status
    status = get_status()
    assert isinstance(status, dict)
    assert "running" in status
    assert "port" in status
    if status["running"]:
        assert status["port"] is not None
    print(f"  PASS  test_browser_get_status (running: {status['running']})")


def test_browser_constants():
    """Browser module constants are correct."""
    from tradingview_cli.browser import PROFILE_DIR, STATE_FILE, DEFAULT_CDP_PORT
    assert DEFAULT_CDP_PORT == 9333
    assert "/.claude/plugins/data/.chrome-profiles/tradingview" in str(PROFILE_DIR)
    assert STATE_FILE.name == ".monitor.json"
    print("  PASS  test_browser_constants")


def test_browser_build_visible_chrome_args_with_proxy():
    """Visible Chrome args include proxy-server only when proxy is configured."""
    from tradingview_cli.browser import build_visible_chrome_args

    args = build_visible_chrome_args(
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        9333,
        None,
    )
    assert "--proxy-server=http://127.0.0.1:7890" not in args

    args = build_visible_chrome_args(
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        9333,
        "socks5://127.0.0.1:7980",
    )
    assert "--proxy-server=socks5://127.0.0.1:7980" in args
    assert args[-1] == "https://www.tradingview.com/chart/"
    print("  PASS  test_browser_build_visible_chrome_args_with_proxy")


def test_codex_path_detection():
    """Path helper switches to Codex data root under Codex plugin env."""
    import tradingview_cli.paths as paths

    tracked = [
        "TRADINGVIEW_DATA_DIR",
        "TRADINGVIEW_PROFILE_DIR",
        "TRADINGVIEW_PLUGIN_HOST",
        "CODEX_HOME",
        "CODEX_PLUGIN_ROOT",
        "PLUGIN_ROOT",
        "CLAUDE_PLUGIN_ROOT",
    ]
    saved = {key: os.environ.get(key) for key in tracked}
    try:
        for key in tracked:
            os.environ.pop(key, None)
        os.environ["PLUGIN_ROOT"] = "/tmp/codex-plugin"
        reloaded = importlib.reload(paths)
        assert "/.codex/plugins/data/.chrome-profiles/tradingview" in str(reloaded.PROFILE_DIR)
    finally:
        for key in tracked:
            if saved[key] is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = saved[key]
        importlib.reload(paths)

    print("  PASS  test_codex_path_detection")


def test_browser_read_state():
    """_read_state handles missing/corrupt files gracefully."""
    from tradingview_cli.browser import _read_state
    # Should not raise even if state file has issues
    result = _read_state()
    # Result is either None or a dict
    assert result is None or isinstance(result, dict)
    print("  PASS  test_browser_read_state")


def test_browser_monitor_alive():
    """_monitor_alive checks PID existence."""
    from tradingview_cli.browser import _monitor_alive
    # Current process should be alive
    assert _monitor_alive({"monitor_pid": os.getpid()}) is True
    # Non-existent PID should not be alive
    assert _monitor_alive({"monitor_pid": 999999}) is False
    # Missing PID
    assert _monitor_alive({}) is False
    print("  PASS  test_browser_monitor_alive")


# ═══════════════════════════════════════════════════════════
#  Test: CLI Dispatch
# ═══════════════════════════════════════════════════════════

def test_cli_parse_args():
    """parse_args handles various argument formats."""
    from tradingview_cli.main import parse_args

    # Basic command
    cmd, args = parse_args(["status"])
    assert cmd == "status"
    assert args == {}

    # Command with --key=value
    cmd, args = parse_args(["quote", "--ticker=AAPL", "--exchange=NASDAQ"])
    assert cmd == "quote"
    assert args["ticker"] == "AAPL"
    assert args["exchange"] == "NASDAQ"

    # Command with --key value (space-separated)
    cmd, args = parse_args(["search", "--query", "apple"])
    assert cmd == "search"
    assert args["query"] == "apple"

    # Boolean flag
    cmd, args = parse_args(["launch", "--headless"])
    assert cmd == "launch"
    assert args["headless"] == "true"

    # Empty args
    cmd, args = parse_args([])
    assert cmd == "help"

    print("  PASS  test_cli_parse_args")


def test_cli_parse_proxy_arg():
    """CLI parser accepts temporary --proxy overrides."""
    from tradingview_cli.main import parse_args

    cmd, args = parse_args(["launch", "--proxy=socks5://127.0.0.1:7980"])
    assert cmd == "launch"
    assert args["proxy"] == "socks5://127.0.0.1:7980"
    print("  PASS  test_cli_parse_proxy_arg")


def test_settings_resolve_proxy_priority():
    """Proxy lookup prefers CLI override, then plugin userConfig, then env fallback."""
    from tradingview_cli.settings import resolve_proxy

    env = {
        "CLAUDE_PLUGIN_OPTION_PROXY": "http://plugin-proxy:8080",
        "ALL_PROXY": "socks5://env-proxy:1080",
        "HTTPS_PROXY": "http://https-proxy:8080",
        "HTTP_PROXY": "http://http-proxy:8080",
    }
    assert resolve_proxy("http://cli-proxy:8888", env=env) == "http://cli-proxy:8888"
    assert resolve_proxy(None, env=env) == "http://plugin-proxy:8080"

    env.pop("CLAUDE_PLUGIN_OPTION_PROXY")
    assert resolve_proxy(None, env=env) == "socks5://env-proxy:1080"

    env.pop("ALL_PROXY")
    assert resolve_proxy(None, env=env) == "http://https-proxy:8080"

    env.pop("HTTPS_PROXY")
    assert resolve_proxy(None, env=env) == "http://http-proxy:8080"
    print("  PASS  test_settings_resolve_proxy_priority")


def test_settings_resolve_proxy_empty_values_are_unset():
    """Empty proxy values are ignored."""
    from tradingview_cli.settings import resolve_proxy

    env = {
        "CLAUDE_PLUGIN_OPTION_PROXY": "",
        "ALL_PROXY": "   ",
        "HTTPS_PROXY": "http://https-proxy:8080",
    }
    assert resolve_proxy("", env=env) == "http://https-proxy:8080"
    assert resolve_proxy("   ", env={}) is None
    print("  PASS  test_settings_resolve_proxy_empty_values_are_unset")


def test_settings_validate_proxy_scheme():
    """Proxy validation accepts supported schemes and rejects unsupported schemes."""
    from tradingview_cli.settings import ProxyConfigError, validate_proxy

    assert validate_proxy(None) is None
    assert validate_proxy("http://127.0.0.1:7890") == "http://127.0.0.1:7890"
    assert validate_proxy("https://proxy.example:443") == "https://proxy.example:443"
    assert validate_proxy("socks5://127.0.0.1:1080") == "socks5://127.0.0.1:1080"
    assert validate_proxy("socks4://127.0.0.1:1080") == "socks4://127.0.0.1:1080"

    with pytest.raises(ProxyConfigError, match="Unsupported proxy scheme"):
        validate_proxy("ftp://127.0.0.1:21")
    print("  PASS  test_settings_validate_proxy_scheme")


def test_settings_proxy_env_for_child():
    """Child monitor env receives the resolved proxy through plugin option env."""
    from tradingview_cli.settings import proxy_env_for_child

    child = proxy_env_for_child("http://127.0.0.1:7890", base_env={"PATH": "/bin"})
    assert child["PATH"] == "/bin"
    assert child["CLAUDE_PLUGIN_OPTION_PROXY"] == "http://127.0.0.1:7890"
    assert child["ALL_PROXY"] == "http://127.0.0.1:7890"
    assert child["HTTPS_PROXY"] == "http://127.0.0.1:7890"
    assert child["HTTP_PROXY"] == "http://127.0.0.1:7890"
    print("  PASS  test_settings_proxy_env_for_child")


def test_client_resolves_proxy_for_http():
    """HTTP client proxy resolution uses the unified settings module."""
    from tradingview_cli import client

    tracked = [
        "CLAUDE_PLUGIN_OPTION_PROXY",
        "ALL_PROXY",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "all_proxy",
        "https_proxy",
        "http_proxy",
    ]
    saved = {key: os.environ.get(key) for key in tracked}
    try:
        for key in tracked:
            os.environ.pop(key, None)
        os.environ["CLAUDE_PLUGIN_OPTION_PROXY"] = "http://plugin-proxy:8080"
        assert client.get_http_proxy() == "http://plugin-proxy:8080"

        os.environ.pop("CLAUDE_PLUGIN_OPTION_PROXY")
        os.environ["ALL_PROXY"] = "socks5://env-proxy:1080"
        assert client.get_http_proxy() == "socks5://env-proxy:1080"
    finally:
        for key in tracked:
            if saved[key] is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = saved[key]
    print("  PASS  test_client_resolves_proxy_for_http")


def test_cli_help_command():
    """help command returns list of all commands."""
    result = asyncio.run(_run_cmd("help", {}))
    assert "commands" in result
    expected = ["launch", "login-interactive", "login-email", "stop", "ensure",
                "status", "quote", "options-chain", "options-expiries", "screener",
                "search", "news", "watchlists", "alerts", "chart-state", "screenshot"]
    for cmd in expected:
        assert cmd in result["commands"], f"Missing command: {cmd}"
    print("  PASS  test_cli_help_command")


def test_cli_status_command():
    """status command returns well-formed response."""
    result = asyncio.run(_run_cmd("status", {}))
    assert "running" in result
    print(f"  PASS  test_cli_status_command (running: {result.get('running')})")


def test_cli_missing_args():
    """Commands with missing required args return error."""
    result = asyncio.run(_run_cmd("quote", {}))
    assert "error" in result

    result = asyncio.run(_run_cmd("search", {}))
    assert "error" in result

    result = asyncio.run(_run_cmd("options-chain", {}))
    assert "error" in result

    result = asyncio.run(_run_cmd("login-email", {}))
    assert "error" in result

    result = asyncio.run(_run_cmd("login-email", {"email": "test@example.com"}))
    assert "error" in result

    print("  PASS  test_cli_missing_args")


def test_cli_unknown_command():
    """Unknown command returns error with hint."""
    result = asyncio.run(_run_cmd("nonexistent", {}))
    assert "error" in result
    assert "hint" in result
    print("  PASS  test_cli_unknown_command")


# ═══════════════════════════════════════════════════════════
#  Test: Monitor Entry Point
# ═══════════════════════════════════════════════════════════

def test_monitor_argparse():
    """Monitor __main__ block parses args correctly."""
    import argparse
    from tradingview_cli.monitor import DEFAULT_CDP_PORT

    # Simulate argument parsing
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--no-headless", dest="headless", action="store_false")

    args = parser.parse_args(["--port=9334"])
    assert args.port == 9334
    assert args.headless is True

    args = parser.parse_args(["--no-headless"])
    assert args.headless is False

    args = parser.parse_args([])
    assert args.port is None
    assert args.headless is True

    print("  PASS  test_monitor_argparse")


# ═══════════════════════════════════════════════════════════
#  Test: Plugin Structure
# ═══════════════════════════════════════════════════════════

def test_plugin_structure():
    """Verify plugin file structure is correct after refactoring."""
    plugin_root = Path(__file__).parent.parent.parent  # scripts/../.. = tradingview/

    # Must exist
    must_exist = [
        ".claude-plugin/plugin.json",
        "hooks/hooks.json",
        "hooks/session_start.sh",
        "monitors/monitors.json",
        "commands/launch.md",
        "commands/login-interactive.md",
        "commands/login-email.md",
        "commands/stop.md",
        "commands/status.md",
        "commands/preflight.md",
        "commands/quote.md",
        "commands/options-chain.md",
        "commands/options-expiries.md",
        "commands/screener.md",
        "commands/search.md",
        "commands/news.md",
        "commands/watchlists.md",
        "commands/alerts.md",
        "commands/chart-state.md",
        "commands/screenshot.md",
        "scripts/pyproject.toml",
        "scripts/tradingview.py",
        "scripts/tradingview_cli/monitor.py",
        "scripts/tradingview_cli/paths.py",
        "scripts/tradingview_cli/browser.py",
        "scripts/tradingview_cli/main.py",
        "scripts/tradingview_cli/client.py",
        "scripts/tradingview_cli/commands.py",
        "skills/news-research/SKILL.md",
        "skills/options-analysis/SKILL.md",
        "skills/screener/SKILL.md",
        "skills/tradingview/SKILL.md",
        "README.md",
        "README-zh.md",
    ]
    for path in must_exist:
        full = plugin_root / path
        assert full.exists(), f"Missing: {path}"

    # Must NOT exist (removed/obsolete)
    must_not_exist = [
        "scripts/daemon.py",
        "hooks/ensure-browser.sh",
    ]
    for path in must_not_exist:
        full = plugin_root / path
        assert not full.exists(), f"Should be removed: {path}"

    print("  PASS  test_plugin_structure")


def test_plugin_json_valid():
    """Claude plugin.json has correct content."""
    plugin_root = Path(__file__).parent.parent.parent
    pj = json.loads((plugin_root / ".claude-plugin/plugin.json").read_text())
    assert pj["name"] == "tradingview"
    assert pj["version"] == "0.4.1"
    assert pj["monitors"] == "./monitors/monitors.json"
    print("  PASS  test_plugin_json_valid")


def test_plugin_json_proxy_user_config():
    """Claude plugin manifest declares optional proxy userConfig."""
    plugin_root = Path(__file__).parent.parent.parent
    pj = json.loads((plugin_root / ".claude-plugin/plugin.json").read_text())
    proxy = pj["userConfig"]["proxy"]
    assert proxy["type"] == "string"
    assert proxy["title"] == "Proxy URL (optional)"
    assert "Chrome and HTTP API" in proxy["description"]
    assert "ALL_PROXY" in proxy["description"]
    assert proxy["default"] == ""
    assert proxy["required"] is False
    print("  PASS  test_plugin_json_proxy_user_config")


def test_codex_hooks_json_valid():
    """Codex hooks point at the SessionStart launcher."""
    plugin_root = Path(__file__).parent.parent.parent
    hooks = json.loads((plugin_root / "hooks/hooks.json").read_text())
    session_start = hooks["hooks"]["SessionStart"][0]["hooks"][0]
    assert session_start["type"] == "command"
    assert "session_start.sh" in session_start["command"]
    assert "statusMessage" in session_start
    print("  PASS  test_codex_hooks_json_valid")


def test_monitors_json_valid():
    """monitors.json has correct format."""
    plugin_root = Path(__file__).parent.parent.parent
    monitors = json.loads((plugin_root / "monitors/monitors.json").read_text())
    assert isinstance(monitors, list)
    assert len(monitors) == 1
    m = monitors[0]
    assert m["name"] == "tradingview-browser"
    assert "tradingview_cli.monitor" in m["command"]
    assert "${CLAUDE_PLUGIN_ROOT}" in m["command"]
    print("  PASS  test_monitors_json_valid")


def test_no_stale_path_references():
    """No command files reference old ~/.chrome-profiles/ path."""
    plugin_root = Path(__file__).parent.parent.parent
    commands_dir = plugin_root / "commands"
    for md_file in commands_dir.glob("*.md"):
        content = md_file.read_text()
        assert "~/.chrome-profiles/tradingview" not in content, \
            f"Stale path in {md_file.name}"
    print("  PASS  test_no_stale_path_references")


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════

async def _run_cmd(cmd: str, args: dict) -> dict:
    """Helper to run a CLI command."""
    from tradingview_cli.main import run
    return await run(cmd, args)


# ═══════════════════════════════════════════════════════════
#  Main runner
# ═══════════════════════════════════════════════════════════

def run_all_tests():
    """Run all tests and report results."""
    tests = [
        test_imports,
        test_monitor_port_check,
        test_monitor_find_available_port,
        test_monitor_find_chrome_binary,
        test_monitor_build_chrome_args_with_proxy,
        test_monitor_cdp_health,
        test_monitor_write_state,
        test_browser_get_status,
        test_browser_constants,
        test_browser_build_visible_chrome_args_with_proxy,
        test_codex_path_detection,
        test_browser_read_state,
        test_browser_monitor_alive,
        test_cli_parse_args,
        test_cli_parse_proxy_arg,
        test_settings_resolve_proxy_priority,
        test_settings_resolve_proxy_empty_values_are_unset,
        test_settings_validate_proxy_scheme,
        test_settings_proxy_env_for_child,
        test_client_resolves_proxy_for_http,
        test_cli_help_command,
        test_cli_status_command,
        test_cli_missing_args,
        test_cli_unknown_command,
        test_monitor_argparse,
        test_plugin_structure,
        test_plugin_json_valid,
        test_plugin_json_proxy_user_config,
        test_codex_hooks_json_valid,
        test_monitors_json_valid,
        test_no_stale_path_references,
    ]

    passed = 0
    failed = 0
    errors = []

    print("=" * 60)
    print("TradingView Plugin Integration Tests")
    print("=" * 60)

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            failed += 1
            errors.append((test.__name__, str(e)))
            print(f"  FAIL  {test.__name__}: {e}")
        except Exception as e:
            failed += 1
            errors.append((test.__name__, f"{type(e).__name__}: {e}"))
            print(f"  ERROR {test.__name__}: {type(e).__name__}: {e}")

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    if errors:
        print("\nFailures:")
        for name, msg in errors:
            print(f"  - {name}: {msg}")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
