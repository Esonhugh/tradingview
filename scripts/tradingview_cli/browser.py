#!/usr/bin/env python3
"""
TradingView Browser Manager — interface to plugin monitor daemon.

The monitor runs as a Claude Code plugin monitor or Codex plugin hook-launched
background process. This module reads its state and provides APIs for CLI commands.

For the `login` command (non-headless), it can also launch Chrome directly.
"""

import asyncio
import json
import os
import signal
import subprocess
import sys
import time

import httpx

from .paths import PROFILE_DIR, STATE_FILE

DEFAULT_CDP_PORT = int(os.environ.get("TV_CDP_PORT", "9333"))
TRADINGVIEW_URL = "https://www.tradingview.com/chart/"


def _read_state() -> dict | None:
    """Read monitor state file, return None if missing or corrupt."""
    if not STATE_FILE.exists():
        return None
    try:
        return json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _monitor_alive(state: dict) -> bool:
    """Check if the monitor process is still running."""
    pid = state.get("monitor_pid")
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def get_status() -> dict:
    """Check if browser is currently running via monitor state + CDP."""
    state = _read_state()

    if state and state.get("status") == "running" and _monitor_alive(state):
        port = state.get("port")
        # Verify CDP is reachable
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(f"http://127.0.0.1:{port}/json/version")
                if resp.status_code == 200:
                    return {
                        "running": True,
                        "port": port,
                        "pid": state.get("chrome_pid"),
                        "monitor_pid": state.get("monitor_pid"),
                        "headless": state.get("headless", True),
                    }
        except Exception:
            pass

    # Fallback: check default port directly (monitor may not have state yet)
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"http://127.0.0.1:{DEFAULT_CDP_PORT}/json/version")
            if resp.status_code == 200:
                return {
                    "running": True,
                    "port": DEFAULT_CDP_PORT,
                    "pid": state.get("chrome_pid") if state else None,
                    "monitor_pid": state.get("monitor_pid") if state else None,
                    "headless": True,
                }
    except Exception:
        pass

    # Not running
    if state and not _monitor_alive(state):
        STATE_FILE.unlink(missing_ok=True)

    return {"running": False, "port": None, "pid": None}


async def launch_browser(port: int = DEFAULT_CDP_PORT, headless: bool = True) -> dict:
    """Start the monitor daemon which manages Chrome.

    For headless mode: starts the monitor process.
    For visible mode (login): launches Chrome directly without monitor.
    """
    import shutil

    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    # Check if already running
    status = get_status()
    if status["running"]:
        return {"status": "already_running", "port": status["port"], "pid": status["pid"],
                "monitor_pid": status.get("monitor_pid")}

    if headless:
        # Start via monitor daemon
        cmd = [sys.executable, "-m", "tradingview_cli.monitor", f"--port={port}"]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # Wait for monitor to become ready
        for _ in range(30):
            await asyncio.sleep(0.5)
            state = _read_state()
            if state and state.get("status") == "running":
                return {
                    "status": "launched",
                    "port": state["port"],
                    "pid": state.get("chrome_pid"),
                    "monitor_pid": state.get("monitor_pid"),
                    "profile_dir": str(PROFILE_DIR),
                }
            if state and state.get("status") == "error":
                return {"error": state.get("error", "Monitor failed to start")}

        return {"error": "Monitor did not become ready within timeout"}

    else:
        # Visible mode (for login) — launch Chrome directly, no monitor
        chrome_bin = None
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            shutil.which("google-chrome"),
            shutil.which("chromium"),
            shutil.which("chrome"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                chrome_bin = c
                break

        if not chrome_bin:
            return {"error": "Chrome/Chromium not found"}

        args = [
            chrome_bin,
            f"--user-data-dir={PROFILE_DIR}",
            f"--remote-debugging-port={port}",
            "--no-first-run",
            "--no-default-browser-check",
            TRADINGVIEW_URL,
        ]

        proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # Wait for CDP
        for _ in range(20):
            await asyncio.sleep(0.5)
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    resp = await client.get(f"http://127.0.0.1:{port}/json/version")
                    if resp.status_code == 200:
                        break
            except Exception:
                continue

        # Write state so stop_browser() can find the Chrome PID
        state = {
            "status": "running",
            "chrome_pid": proc.pid,
            "monitor_pid": None,
            "port": port,
            "headless": False,
            "profile_dir": str(PROFILE_DIR),
            "started_at": time.time(),
        }
        STATE_FILE.write_text(json.dumps(state))

        return {
            "status": "launched",
            "port": port,
            "pid": proc.pid,
            "profile_dir": str(PROFILE_DIR),
            "headless": False,
        }


def stop_browser() -> dict:
    """Stop the monitor daemon (which stops Chrome), or stop a visible Chrome."""
    state = _read_state()
    chrome_pid = state.get("chrome_pid") if state else None
    monitor_pid = None

    if state and _monitor_alive(state):
        monitor_pid = state["monitor_pid"]
        try:
            os.kill(monitor_pid, signal.SIGTERM)
            for _ in range(20):
                time.sleep(0.25)
                try:
                    os.kill(monitor_pid, 0)
                except OSError:
                    break
            else:
                try:
                    os.kill(monitor_pid, signal.SIGKILL)
                except OSError:
                    pass
        except OSError:
            pass

    # Ensure Chrome process is dead (handles orphaned Chrome after monitor exit)
    if chrome_pid:
        try:
            os.kill(chrome_pid, signal.SIGTERM)
            for _ in range(12):
                time.sleep(0.25)
                try:
                    os.kill(chrome_pid, 0)
                except OSError:
                    break
            else:
                try:
                    os.kill(chrome_pid, signal.SIGKILL)
                except OSError:
                    pass
        except OSError:
            pass

    # Fallback: pkill any Chrome using our profile (catches PID-unknown cases)
    try:
        subprocess.run(
            ["pkill", "-f", f"--user-data-dir={PROFILE_DIR}"],
            capture_output=True, timeout=3,
        )
    except Exception:
        pass

    # Wait briefly for port to be freed
    time.sleep(0.3)

    STATE_FILE.unlink(missing_ok=True)
    return {"status": "stopped", "monitor_pid": monitor_pid, "pid": chrome_pid}


async def ensure_running(port: int = DEFAULT_CDP_PORT, headless: bool = True) -> dict:
    """Ensure browser is running via monitor, launch if not."""
    status = get_status()
    if status["running"]:
        return {"status": "already_running", "port": status["port"], "pid": status["pid"],
                "monitor_pid": status.get("monitor_pid")}
    return await launch_browser(port=port, headless=headless)


async def inject_cookies(cookies: list[dict]) -> dict:
    """Inject cookies into running Chrome via CDP Network.setCookies.

    Connects to a page-level CDP target (not the browser endpoint) because
    Network.setCookies is only available on page targets.
    """
    import websockets

    status = get_status()
    if not status["running"]:
        result = await ensure_running()
        if "error" in result:
            return result
        status = get_status()

    port = status["port"]

    # Get a page-level WebSocket target (Network domain is page-level only)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"http://127.0.0.1:{port}/json")
            targets = resp.json()
        page = next((t for t in targets if t.get("type") == "page"), None)
        if not page:
            return {"error": "No page target found in browser"}
        ws_url = page["webSocketDebuggerUrl"]
    except Exception as e:
        return {"error": f"Cannot get CDP page target: {e}"}

    try:
        async with websockets.connect(ws_url, max_size=5 * 1024 * 1024) as ws:
            # Enable Network domain first
            await ws.send(json.dumps({"id": 1, "method": "Network.enable", "params": {}}))
            await ws.recv()

            # Inject cookies
            msg = json.dumps({
                "id": 2,
                "method": "Network.setCookies",
                "params": {"cookies": cookies},
            })
            await ws.send(msg)
            resp_data = json.loads(await ws.recv())

            if "error" in resp_data:
                return {"error": f"CDP setCookies failed: {resp_data['error']}"}

            # Navigate to TradingView to activate the session
            await ws.send(json.dumps({
                "id": 3,
                "method": "Page.navigate",
                "params": {"url": "https://www.tradingview.com/"},
            }))
            await ws.recv()

        return {"ok": True, "injected": len(cookies)}

    except Exception as e:
        return {"error": f"Cookie injection failed: {e}"}


async def list_pages() -> list:
    """List open browser pages via CDP."""
    status = get_status()
    if not status["running"]:
        return []
    port = status["port"]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"http://127.0.0.1:{port}/json")
            pages = resp.json()
            return [
                {
                    "id": p["id"],
                    "title": p.get("title", ""),
                    "url": p.get("url", ""),
                    "type": p.get("type", "page"),
                }
                for p in pages
                if p.get("type") == "page"
            ]
    except Exception:
        return []


async def get_ws_endpoint() -> str:
    """Get browser-level WebSocket endpoint."""
    status = get_status()
    if not status["running"]:
        raise RuntimeError("Browser not running. Use /tradingview:launch first.")
    port = status["port"]
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"http://127.0.0.1:{port}/json/version")
        data = resp.json()
        return data["webSocketDebuggerUrl"]
