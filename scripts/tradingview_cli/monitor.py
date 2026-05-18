#!/usr/bin/env python3
"""
TradingView Browser Monitor — plugin monitor daemon.

Designed to run as a Claude Code monitor or Codex hook-started background task.
Manages Chrome lifecycle with health checks, auto-restart, and port conflict resolution.

Outputs status lines to stdout for the host to consume as notifications/logs.
"""

import json
import os
import signal
import socket
import subprocess
import shutil
import sys
import time

from .paths import PROFILE_DIR, STATE_FILE

DEFAULT_CDP_PORT = int(os.environ.get("TV_CDP_PORT", "9333"))
TRADINGVIEW_URL = "https://www.tradingview.com/chart/"
HEALTH_INTERVAL = 10  # seconds between health checks
MAX_RESTART_ATTEMPTS = 3


def log(msg: str):
    """Output a notification line to stdout (Claude receives this)."""
    print(msg, flush=True)


def find_chrome_binary() -> str | None:
    """Locate Chrome/Chromium binary."""
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chrome"),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def is_port_available(port: int) -> bool:
    """Check if a TCP port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def find_available_port(start: int = DEFAULT_CDP_PORT, max_tries: int = 10) -> int:
    """Find an available port starting from `start`."""
    for offset in range(max_tries):
        port = start + offset
        if is_port_available(port):
            return port
    raise RuntimeError(f"No available port in range {start}-{start + max_tries - 1}")


def check_cdp_health(port: int) -> bool:
    """Quick synchronous CDP health check via HTTP."""
    import urllib.request
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/json/version", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def write_state(state: dict):
    """Atomically write monitor state to JSON file."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(STATE_FILE)


def launch_chrome(port: int, headless: bool = True) -> subprocess.Popen | None:
    """Launch Chrome subprocess, return Popen object."""
    chrome_bin = find_chrome_binary()
    if not chrome_bin:
        return None

    args = [
        chrome_bin,
        f"--user-data-dir={PROFILE_DIR}",
        f"--remote-debugging-port={port}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
    ]
    if headless:
        args.append("--headless=new")
    args.append(TRADINGVIEW_URL)

    proc = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def wait_for_cdp(port: int, timeout: float = 15.0) -> bool:
    """Block until CDP is reachable or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if check_cdp_health(port):
            return True
        time.sleep(0.5)
    return False


def run_monitor(port: int | None = None, headless: bool = True):
    """Main monitor loop — outputs status to stdout for Claude."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    # Resolve port
    if port is None:
        port = int(os.environ.get("TV_CDP_PORT", DEFAULT_CDP_PORT))

    # Check if CDP is already reachable (e.g. from a prior session)
    if check_cdp_health(port):
        log(f"[tradingview-monitor] Browser already running on port {port}")
        write_state({
            "status": "running",
            "monitor_pid": os.getpid(),
            "chrome_pid": None,
            "port": port,
            "headless": headless,
            "profile_dir": str(PROFILE_DIR),
            "started_at": time.time(),
            "last_health": time.time(),
            "adopted": True,
        })
        # Enter health-check loop for adopted process
        _health_loop(port, headless, chrome_proc=None)
        return

    # Find available port
    if not is_port_available(port):
        try:
            old_port = port
            port = find_available_port(port)
            log(f"[tradingview-monitor] Port {old_port} busy, using {port}")
        except RuntimeError as e:
            log(f"[tradingview-monitor] ERROR: {e}")
            write_state({"status": "error", "error": str(e), "monitor_pid": os.getpid()})
            return

    # Initial launch
    chrome_proc = launch_chrome(port, headless=headless)
    if chrome_proc is None:
        log("[tradingview-monitor] ERROR: Chrome/Chromium not found")
        write_state({"status": "error", "error": "Chrome not found", "monitor_pid": os.getpid()})
        return

    # Wait for CDP ready
    if not wait_for_cdp(port):
        log("[tradingview-monitor] ERROR: CDP failed to start within timeout")
        write_state({"status": "error", "error": "CDP timeout", "monitor_pid": os.getpid()})
        chrome_proc.terminate()
        return

    log(f"[tradingview-monitor] Chrome launched — CDP on port {port}, PID {chrome_proc.pid}")
    write_state({
        "status": "running",
        "monitor_pid": os.getpid(),
        "chrome_pid": chrome_proc.pid,
        "port": port,
        "headless": headless,
        "profile_dir": str(PROFILE_DIR),
        "started_at": time.time(),
        "last_health": time.time(),
    })

    _health_loop(port, headless, chrome_proc)


def _health_loop(port: int, headless: bool, chrome_proc: subprocess.Popen | None):
    """Health-check loop with auto-restart."""
    shutdown_requested = False
    restart_count = 0

    def handle_sigterm(signum, frame):
        nonlocal shutdown_requested
        shutdown_requested = True

    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

    while not shutdown_requested:
        time.sleep(HEALTH_INTERVAL)
        if shutdown_requested:
            break

        healthy = check_cdp_health(port)

        if healthy:
            restart_count = 0
            write_state({
                "status": "running",
                "monitor_pid": os.getpid(),
                "chrome_pid": chrome_proc.pid if chrome_proc else None,
                "port": port,
                "headless": headless,
                "profile_dir": str(PROFILE_DIR),
                "started_at": time.time(),
                "last_health": time.time(),
            })
        else:
            # Chrome died — attempt restart
            restart_count += 1
            if restart_count > MAX_RESTART_ATTEMPTS:
                log(f"[tradingview-monitor] Chrome crashed {MAX_RESTART_ATTEMPTS} times, stopping monitor")
                write_state({
                    "status": "error",
                    "error": f"Chrome crashed {MAX_RESTART_ATTEMPTS} times",
                    "monitor_pid": os.getpid(),
                    "port": port,
                })
                break

            log(f"[tradingview-monitor] Chrome unresponsive, restarting (attempt {restart_count})")

            # Kill stale process
            if chrome_proc and chrome_proc.poll() is None:
                chrome_proc.terminate()
                try:
                    chrome_proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    chrome_proc.kill()

            time.sleep(1)
            if not is_port_available(port):
                time.sleep(3)

            chrome_proc = launch_chrome(port, headless=headless)
            if chrome_proc and wait_for_cdp(port):
                log(f"[tradingview-monitor] Chrome restarted — PID {chrome_proc.pid}")
                write_state({
                    "status": "running",
                    "monitor_pid": os.getpid(),
                    "chrome_pid": chrome_proc.pid,
                    "port": port,
                    "headless": headless,
                    "profile_dir": str(PROFILE_DIR),
                    "started_at": time.time(),
                    "last_health": time.time(),
                    "restart_count": restart_count,
                })

    # Shutdown
    if chrome_proc and chrome_proc.poll() is None:
        chrome_proc.terminate()
        try:
            chrome_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            chrome_proc.kill()

    try:
        subprocess.run(
            ["pkill", "-f", f"--user-data-dir={PROFILE_DIR}"],
            capture_output=True, timeout=3,
        )
    except Exception:
        pass

    STATE_FILE.unlink(missing_ok=True)
    log("[tradingview-monitor] Stopped")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TradingView browser monitor")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    args = parser.parse_args()
    run_monitor(port=args.port, headless=args.headless)
