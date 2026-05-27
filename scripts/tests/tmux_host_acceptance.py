#!/usr/bin/env python3
"""Host acceptance checks intended to be run inside tmux."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def run(cmd: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> str:
    display = " ".join(cmd)
    print(f"$ {display}", flush=True)
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        env=merged_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n", flush=True)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {display}")
    return proc.stdout


def run_json(cmd: list[str], *, cwd: Path = SCRIPTS, env: dict[str, str]) -> dict:
    return json.loads(run(cmd, cwd=cwd, env=env))


def assert_common_cli(host: str, port: int, env: dict[str, str]) -> None:
    help_data = run_json(["uv", "run", "./tradingview.py", "help"], env=env)
    required = {"launch", "status", "search", "screenshot", "stop"}
    assert required.issubset(set(help_data["commands"])), help_data
    print(f"{host}_HELP_OK", flush=True)

    launched = run_json(["uv", "run", "./tradingview.py", "launch"], env=env)
    assert launched["status"] in ("launched", "already_running"), launched
    assert launched["port"] == port, launched
    print(f"{host}_LAUNCH_OK", flush=True)

    status = run_json(["uv", "run", "./tradingview.py", "status"], env=env)
    assert status["running"] is True, status
    assert status["port"] == port, status
    assert status["tabs"], status
    print(f"{host}_STATUS_OK", flush=True)

    search = run_json(
        ["uv", "run", "./tradingview.py", "search", "--query=AAPL", "--limit=1"],
        env=env,
    )
    assert search.get("count", 0) >= 1, search
    print(f"{host}_SEARCH_OK", flush=True)

    shot_path = Path(env["TRADINGVIEW_DATA_DIR"]) / f"{host.lower()}-chart.png"
    screenshot = run_json(
        ["uv", "run", "./tradingview.py", "screenshot", f"--output={shot_path}"],
        env=env,
    )
    assert Path(screenshot["path"]).exists(), screenshot
    assert screenshot["size_bytes"] > 1000, screenshot
    print(f"{host}_SCREENSHOT_OK", flush=True)

    stopped = run_json(["uv", "run", "./tradingview.py", "stop"], env=env)
    assert stopped["status"] == "stopped", stopped
    print(f"{host}_STOP_OK", flush=True)


def test_claude() -> None:
    data_dir = tempfile.mkdtemp(prefix="tradingview-claude-data-")
    temp_home = tempfile.mkdtemp(prefix="tradingview-claude-home-")
    port = int(os.environ.get("TV_TEST_PORT", "9541"))
    print(f"CLAUDE_TEST_BEGIN root={ROOT} data={data_dir} port={port}", flush=True)

    run(["claude", "plugin", "validate", str(ROOT)])

    claude_env = {"HOME": temp_home}
    run(["claude", "plugin", "marketplace", "add", str(ROOT), "--scope", "user"], env=claude_env)
    available = json.loads(
        run(["claude", "plugin", "list", "--available", "--json"], env=claude_env)
    )
    assert any(
        item.get("name") == "tradingview" and item.get("version") == "0.4.1"
        for item in available.get("available", [])
    ), available
    print("CLAUDE_MARKETPLACE_AVAILABLE_OK", flush=True)

    run(
        ["claude", "plugin", "install", "tradingview@Esonhugh-TradingView", "--scope", "user"],
        env=claude_env,
    )
    installed = json.loads(run(["claude", "plugin", "list", "--json"], env=claude_env))
    assert any(
        item.get("id") == "tradingview@Esonhugh-TradingView" and item.get("enabled") is True
        for item in installed
    ), installed
    print("CLAUDE_INSTALL_OK", flush=True)

    cli_env = {
        "CLAUDE_PLUGIN_ROOT": str(ROOT),
        "TRADINGVIEW_DATA_DIR": data_dir,
        "TV_CDP_PORT": str(port),
    }
    try:
        assert_common_cli("CLAUDE", port, cli_env)
    finally:
        run(["uv", "run", "./tradingview.py", "stop"], cwd=SCRIPTS, env=cli_env)

    print("CLAUDE_TEST_DONE", flush=True)


def test_codex() -> None:
    data_dir = tempfile.mkdtemp(prefix="tradingview-codex-data-")
    codex_home = tempfile.mkdtemp(prefix="tradingview-codex-home-")
    port = int(os.environ.get("TV_TEST_PORT", "9542"))
    print(f"CODEX_TEST_BEGIN root={ROOT} data={data_dir} port={port}", flush=True)

    run(["python3", "-m", "json.tool", str(ROOT / ".codex-plugin/plugin.json")])
    run(["python3", "-m", "json.tool", str(ROOT / ".agents/plugins/marketplace.json")])
    plugin = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
    marketplace = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text())
    entry = marketplace["plugins"][0]
    assert plugin["name"] == entry["name"] == "tradingview"
    assert plugin["version"] == "0.4.1"
    assert entry["source"] == {"source": "local", "path": "./"}
    assert entry["policy"]["installation"] == "AVAILABLE"
    assert entry["policy"]["authentication"] == "ON_INSTALL"
    print("CODEX_SCHEMA_OK", flush=True)

    codex_env = {"CODEX_HOME": codex_home}
    run(["codex", "plugin", "marketplace", "add", str(ROOT)], env=codex_env)
    config = Path(codex_home, "config.toml").read_text()
    assert "[marketplaces.esonhugh-tradingview]" in config, config
    print("CODEX_MARKETPLACE_ADD_OK", flush=True)

    cli_env = {
        "PLUGIN_ROOT": str(ROOT),
        "CODEX_HOME": codex_home,
        "TRADINGVIEW_DATA_DIR": data_dir,
        "TV_CDP_PORT": str(port),
    }
    try:
        assert_common_cli("CODEX", port, cli_env)
    finally:
        run(["uv", "run", "./tradingview.py", "stop"], cwd=SCRIPTS, env=cli_env)

    hook_port = port + 100
    hook_env = cli_env | {"TV_CDP_PORT": str(hook_port)}
    run(["bash", str(ROOT / "hooks/session_start.sh")], env=hook_env)
    deadline = time.time() + 30
    last_status: dict | None = None
    while time.time() < deadline:
        last_status = run_json(["uv", "run", "./tradingview.py", "status"], env=hook_env)
        if last_status.get("running") and last_status.get("port") == hook_port:
            break
        time.sleep(1)
    assert last_status and last_status.get("running") is True, last_status
    assert last_status["port"] == hook_port, last_status
    print("CODEX_HOOK_START_OK", flush=True)
    run_json(["uv", "run", "./tradingview.py", "stop"], env=hook_env)
    print("CODEX_HOOK_STOP_OK", flush=True)

    print("CODEX_TEST_DONE", flush=True)


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"claude", "codex"}:
        print("usage: tmux_host_acceptance.py claude|codex", file=sys.stderr)
        return 2
    if sys.argv[1] == "claude":
        test_claude()
    else:
        test_codex()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
