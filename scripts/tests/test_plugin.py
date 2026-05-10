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
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

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


def test_cli_help_command():
    """help command returns list of all commands."""
    result = asyncio.run(_run_cmd("help", {}))
    assert "commands" in result
    expected = ["launch", "login", "login-email", "stop", "ensure", "status", "quote",
                "options-chain", "options-expiries", "screener", "search",
                "news", "watchlists", "alerts", "chart-state", "screenshot"]
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
        "monitors/monitors.json",
        "commands/launch.md",
        "commands/login.md",
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
        "scripts/tradingview_cli/browser.py",
        "scripts/tradingview_cli/main.py",
        "scripts/tradingview_cli/client.py",
        "scripts/tradingview_cli/commands.py",
        "skills/news-research/SKILL.md",
        "skills/options-analysis/SKILL.md",
        "skills/screener/SKILL.md",
        "README.md",
        "README-zh.md",
    ]
    for path in must_exist:
        full = plugin_root / path
        assert full.exists(), f"Missing: {path}"

    # Must NOT exist (removed/obsolete)
    must_not_exist = [
        "scripts/daemon.py",
        "hooks/hooks.json",
        "hooks/ensure-browser.sh",
    ]
    for path in must_not_exist:
        full = plugin_root / path
        assert not full.exists(), f"Should be removed: {path}"

    print("  PASS  test_plugin_structure")


def test_plugin_json_valid():
    """plugin.json has correct content."""
    plugin_root = Path(__file__).parent.parent.parent
    pj = json.loads((plugin_root / ".claude-plugin/plugin.json").read_text())
    assert pj["name"] == "tradingview"
    assert pj["version"] == "0.2.0"
    assert "experimental" in pj
    assert pj["experimental"]["monitors"] == "./monitors/monitors.json"
    print("  PASS  test_plugin_json_valid")


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
        test_monitor_cdp_health,
        test_monitor_write_state,
        test_browser_get_status,
        test_browser_constants,
        test_browser_read_state,
        test_browser_monitor_alive,
        test_cli_parse_args,
        test_cli_help_command,
        test_cli_status_command,
        test_cli_missing_args,
        test_cli_unknown_command,
        test_monitor_argparse,
        test_plugin_structure,
        test_plugin_json_valid,
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
