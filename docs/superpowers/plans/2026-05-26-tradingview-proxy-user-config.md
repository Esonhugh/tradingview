# TradingView Proxy User Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a TradingView plugin `userConfig.proxy` setting and apply it to both Chrome traffic and TradingView HTTP API traffic.

**Architecture:** Add one focused settings module that resolves and validates proxy configuration from CLI override, Claude Code plugin userConfig environment, and proxy environment variables. Chrome lifecycle code and HTTP client code consume that module rather than each parsing proxy independently.

**Tech Stack:** Python 3.11, httpx, websockets, Chrome DevTools Protocol, Claude Code plugin manifest `userConfig`, pytest-style tests in `scripts/tests/test_plugin.py`.

---

## File Structure

- Modify `.claude-plugin/plugin.json` to declare `userConfig.proxy`.
- Modify `.codex-plugin/plugin.json` only if it has a parallel config schema; otherwise leave Codex manifest unchanged.
- Create `scripts/tradingview_cli/settings.py` for proxy lookup, validation, masking, and environment propagation.
- Modify `scripts/tradingview_cli/main.py` to parse `--proxy`, validate it once, and pass it into launch/login/API flows through environment or function parameters.
- Modify `scripts/tradingview_cli/monitor.py` to apply `--proxy-server=<proxy>` to headless Chrome and avoid writing the raw proxy to state.
- Modify `scripts/tradingview_cli/browser.py` to apply proxy to visible Chrome and propagate CLI override to spawned monitor.
- Modify `scripts/tradingview_cli/client.py` to use the unified proxy for `tv_fetch()` and `programmatic_login()`.
- Modify `scripts/pyproject.toml` to ensure SOCKS proxies work with httpx.
- Modify `scripts/tests/test_plugin.py` with unit tests for manifest schema, settings resolution, Chrome args, and HTTP proxy use.
- Modify `README.md`, `README-zh.md`, `commands/launch.md`, and `commands/login-email.md` to document the new config and fallback behavior.

## Important Existing Conventions

- Claude Code plugin `userConfig` options are injected as environment variables named `CLAUDE_PLUGIN_OPTION_<UPPERCASE_FIELD_NAME>`.
- For `proxy`, read `CLAUDE_PLUGIN_OPTION_PROXY`. This matches the IBKR plugin pattern in `ibkr-trade-analyzer/skills/ibkr-trade-analyzer/scripts/ibkr_analyzer.py:90-99`.
- Existing TradingView HTTP code currently reads proxy env vars inline in `scripts/tradingview_cli/client.py:142`.
- Existing Chrome launch paths are `scripts/tradingview_cli/monitor.py:86-111` and `scripts/tradingview_cli/browser.py:154-168`.
- Do not commit unless the user explicitly asks for a commit.

---

### Task 1: Add Manifest User Config

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Test: `scripts/tests/test_plugin.py`

- [ ] **Step 1: Write the failing manifest test**

Add this test after `test_plugin_json_valid()` in `scripts/tests/test_plugin.py`:

```python
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
```

Add it to the `tests = [...]` list in `run_all_tests()` immediately after `test_plugin_json_valid`:

```python
        test_plugin_json_valid,
        test_plugin_json_proxy_user_config,
        test_codex_plugin_json_valid,
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run from `scripts/`:

```bash
uv run python -m pytest tests/test_plugin.py::test_plugin_json_proxy_user_config -v
```

Expected: FAIL with `KeyError: 'userConfig'` or `KeyError: 'proxy'`.

- [ ] **Step 3: Add `userConfig.proxy` to the manifest**

Change `.claude-plugin/plugin.json` to:

```json
{
  "name": "tradingview",
  "version": "0.4.0",
  "description": "TradingView data access with persistent Chrome profile. K-line history (multi-timeframe), technical indicators (MACD/RSI/KDJ/Bollinger), spot quotes, options chains, screener, news, watchlists, alerts, chart state, and screenshots.",
  "author": {
    "name": "esonhugh"
  },
  "monitors": "./monitors/monitors.json",
  "userConfig": {
    "proxy": {
      "type": "string",
      "title": "Proxy URL (optional)",
      "description": "HTTP or SOCKS5 proxy for TradingView Chrome and HTTP API requests, e.g. socks5://127.0.0.1:7980. Leave empty to auto-detect from ALL_PROXY / HTTPS_PROXY / HTTP_PROXY environment variables.",
      "default": "",
      "required": false
    }
  }
}
```

- [ ] **Step 4: Run the focused test and verify it passes**

Run from `scripts/`:

```bash
uv run python -m pytest tests/test_plugin.py::test_plugin_json_proxy_user_config -v
```

Expected: PASS.

---

### Task 2: Add Unified Proxy Settings Module

**Files:**
- Create: `scripts/tradingview_cli/settings.py`
- Modify: `scripts/tests/test_plugin.py`

- [ ] **Step 1: Write failing settings tests**

Add this import near the other imports in `scripts/tests/test_plugin.py`:

```python
import pytest
```

Add these tests after `test_cli_parse_args()`:

```python
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
```

Add them to the `tests = [...]` list after `test_cli_parse_args`:

```python
        test_cli_parse_args,
        test_settings_resolve_proxy_priority,
        test_settings_resolve_proxy_empty_values_are_unset,
        test_settings_validate_proxy_scheme,
        test_settings_proxy_env_for_child,
        test_cli_help_command,
```

- [ ] **Step 2: Run the settings tests and verify they fail**

Run from `scripts/`:

```bash
uv run python -m pytest tests/test_plugin.py::test_settings_resolve_proxy_priority tests/test_plugin.py::test_settings_resolve_proxy_empty_values_are_unset tests/test_plugin.py::test_settings_validate_proxy_scheme tests/test_plugin.py::test_settings_proxy_env_for_child -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'tradingview_cli.settings'`.

- [ ] **Step 3: Create the settings module**

Create `scripts/tradingview_cli/settings.py`:

```python
#!/usr/bin/env python3
"""TradingView plugin settings."""

import os
from collections.abc import Mapping
from urllib.parse import urlparse

PLUGIN_PROXY_ENV = "CLAUDE_PLUGIN_OPTION_PROXY"
PROXY_ENV_VARS = (
    PLUGIN_PROXY_ENV,
    "ALL_PROXY",
    "HTTPS_PROXY",
    "HTTP_PROXY",
    "all_proxy",
    "https_proxy",
    "http_proxy",
)
ALLOWED_PROXY_SCHEMES = {"http", "https", "socks5", "socks4"}


class ProxyConfigError(ValueError):
    """Raised when proxy configuration is invalid."""


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def resolve_proxy(override: str | None = None, env: Mapping[str, str] | None = None) -> str | None:
    """Resolve proxy from override, plugin userConfig env, then proxy env vars."""
    cleaned_override = _clean(override)
    if cleaned_override:
        return cleaned_override

    source = env if env is not None else os.environ
    for name in PROXY_ENV_VARS:
        value = _clean(source.get(name))
        if value:
            return value
    return None


def validate_proxy(proxy: str | None) -> str | None:
    """Validate proxy URL scheme and return the normalized non-empty value."""
    cleaned = _clean(proxy)
    if not cleaned:
        return None

    parsed = urlparse(cleaned)
    if parsed.scheme.lower() not in ALLOWED_PROXY_SCHEMES:
        allowed = ", ".join(sorted(f"{scheme}://" for scheme in ALLOWED_PROXY_SCHEMES))
        raise ProxyConfigError(f"Unsupported proxy scheme for {cleaned!r}. Supported schemes: {allowed}")
    if not parsed.netloc:
        raise ProxyConfigError(f"Proxy URL must include host and port: {cleaned!r}")
    return cleaned


def get_proxy(override: str | None = None, env: Mapping[str, str] | None = None) -> str | None:
    """Resolve and validate proxy configuration."""
    return validate_proxy(resolve_proxy(override, env=env))


def proxy_env_for_child(proxy: str | None, base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return child process env with proxy exported for monitor and subprocesses."""
    child_env = dict(base_env if base_env is not None else os.environ)
    validated = validate_proxy(proxy)
    if validated:
        child_env[PLUGIN_PROXY_ENV] = validated
        child_env["ALL_PROXY"] = validated
        child_env["HTTPS_PROXY"] = validated
        child_env["HTTP_PROXY"] = validated
    return child_env
```

- [ ] **Step 4: Run the settings tests and verify they pass**

Run from `scripts/`:

```bash
uv run python -m pytest tests/test_plugin.py::test_settings_resolve_proxy_priority tests/test_plugin.py::test_settings_resolve_proxy_empty_values_are_unset tests/test_plugin.py::test_settings_validate_proxy_scheme tests/test_plugin.py::test_settings_proxy_env_for_child -v
```

Expected: PASS.

---

### Task 3: Apply Proxy to Headless Monitor Chrome

**Files:**
- Modify: `scripts/tradingview_cli/monitor.py`
- Modify: `scripts/tests/test_plugin.py`

- [ ] **Step 1: Write failing monitor tests**

Add this test after `test_monitor_find_chrome_binary()`:

```python
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
```

Add it to the `tests = [...]` list after `test_monitor_find_chrome_binary`:

```python
        test_monitor_find_chrome_binary,
        test_monitor_build_chrome_args_with_proxy,
        test_monitor_cdp_health,
```

- [ ] **Step 2: Run the monitor test and verify it fails**

Run from `scripts/`:

```bash
uv run python -m pytest tests/test_plugin.py::test_monitor_build_chrome_args_with_proxy -v
```

Expected: FAIL with `ImportError` or `AttributeError` because `build_chrome_args` does not exist.

- [ ] **Step 3: Refactor monitor Chrome args and apply proxy**

In `scripts/tradingview_cli/monitor.py`, add this import near existing imports:

```python
from .settings import ProxyConfigError, get_proxy
```

Add this helper above `launch_chrome()`:

```python
def build_chrome_args(chrome_bin: str, port: int, headless: bool = True,
                      proxy: str | None = None) -> list[str]:
    """Build Chrome launch arguments."""
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
    if proxy:
        args.append(f"--proxy-server={proxy}")
    if headless:
        args.append("--headless=new")
    args.append(TRADINGVIEW_URL)
    return args
```

Replace `launch_chrome()` with:

```python
def launch_chrome(port: int, headless: bool = True,
                  proxy: str | None = None) -> subprocess.Popen | None:
    """Launch Chrome subprocess, return Popen object."""
    chrome_bin = find_chrome_binary()
    if not chrome_bin:
        return None

    args = build_chrome_args(chrome_bin, port, headless=headless, proxy=proxy)
    proc = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc
```

In `run_monitor()`, resolve proxy after `PROFILE_DIR.mkdir(...)`:

```python
    try:
        proxy = get_proxy()
    except ProxyConfigError as e:
        log(f"[tradingview-monitor] ERROR: {e}")
        write_state({"status": "error", "error": str(e), "monitor_pid": os.getpid()})
        return
```

In the adopted-process `write_state(...)` block, add:

```python
            "proxy_configured": bool(proxy),
```

Change both calls to `launch_chrome(...)`:

```python
    chrome_proc = launch_chrome(port, headless=headless, proxy=proxy)
```

and:

```python
            chrome_proc = launch_chrome(port, headless=headless, proxy=proxy)
```

In every monitor `write_state(...)` block for running/restarted Chrome, add:

```python
        "proxy_configured": bool(proxy),
```

or inside `_health_loop`, pass proxy into the function and use it:

```python
def _health_loop(port: int, headless: bool, chrome_proc: subprocess.Popen | None,
                 proxy: str | None = None):
```

Update calls:

```python
        _health_loop(port, headless, chrome_proc=None, proxy=proxy)
```

```python
    _health_loop(port, headless, chrome_proc, proxy=proxy)
```

Inside `_health_loop`, update restart launch:

```python
            chrome_proc = launch_chrome(port, headless=headless, proxy=proxy)
```

and add `"proxy_configured": bool(proxy),` to running/restarted state writes.

- [ ] **Step 4: Run the monitor test and verify it passes**

Run from `scripts/`:

```bash
uv run python -m pytest tests/test_plugin.py::test_monitor_build_chrome_args_with_proxy -v
```

Expected: PASS.

---

### Task 4: Apply Proxy to Browser Launch and CLI Override

**Files:**
- Modify: `scripts/tradingview_cli/browser.py`
- Modify: `scripts/tradingview_cli/main.py`
- Modify: `scripts/tests/test_plugin.py`

- [ ] **Step 1: Write failing browser and CLI tests**

Add this test after `test_browser_constants()`:

```python
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
```

Add this test after `test_cli_parse_args()`:

```python
def test_cli_parse_proxy_arg():
    """CLI parser accepts temporary --proxy overrides."""
    from tradingview_cli.main import parse_args

    cmd, args = parse_args(["launch", "--proxy=socks5://127.0.0.1:7980"])
    assert cmd == "launch"
    assert args["proxy"] == "socks5://127.0.0.1:7980"
    print("  PASS  test_cli_parse_proxy_arg")
```

Add them to `tests = [...]`:

```python
        test_browser_constants,
        test_browser_build_visible_chrome_args_with_proxy,
        test_codex_path_detection,
```

and:

```python
        test_cli_parse_args,
        test_cli_parse_proxy_arg,
        test_settings_resolve_proxy_priority,
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run from `scripts/`:

```bash
uv run python -m pytest tests/test_plugin.py::test_browser_build_visible_chrome_args_with_proxy tests/test_plugin.py::test_cli_parse_proxy_arg -v
```

Expected: browser test FAILS because `build_visible_chrome_args` does not exist; CLI parser test may already PASS because parser handles generic `--key=value`.

- [ ] **Step 3: Update browser launch path**

In `scripts/tradingview_cli/browser.py`, add imports:

```python
from .settings import ProxyConfigError, get_proxy, proxy_env_for_child
```

Add this helper above `launch_browser()`:

```python
def build_visible_chrome_args(chrome_bin: str, port: int,
                              proxy: str | None = None) -> list[str]:
    """Build visible Chrome launch arguments."""
    args = [
        chrome_bin,
        f"--user-data-dir={PROFILE_DIR}",
        f"--remote-debugging-port={port}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if proxy:
        args.append(f"--proxy-server={proxy}")
    args.append(TRADINGVIEW_URL)
    return args
```

Change the `launch_browser` signature:

```python
async def launch_browser(port: int = DEFAULT_CDP_PORT, headless: bool = True,
                         proxy: str | None = None) -> dict:
```

Resolve proxy after `PROFILE_DIR.mkdir(...)`:

```python
    try:
        resolved_proxy = get_proxy(proxy)
    except ProxyConfigError as e:
        return {"error": str(e)}
```

In the already-running response, include only boolean state:

```python
        return {"status": "already_running", "port": status["port"], "pid": status["pid"],
                "monitor_pid": status.get("monitor_pid"),
                "proxy_configured": status.get("proxy_configured", False)}
```

In the headless monitor subprocess block, pass env:

```python
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=proxy_env_for_child(resolved_proxy),
        )
```

In the successful headless launch response, include:

```python
                    "proxy_configured": bool(state.get("proxy_configured", resolved_proxy)),
```

Replace visible mode `args = [...]` with:

```python
        args = build_visible_chrome_args(chrome_bin, port, resolved_proxy)
```

Add `"proxy_configured": bool(resolved_proxy),` to visible mode state and response.

Update `ensure_running` signature and call:

```python
async def ensure_running(port: int = DEFAULT_CDP_PORT, headless: bool = True,
                         proxy: str | None = None) -> dict:
```

```python
    return await launch_browser(port=port, headless=headless, proxy=proxy)
```

- [ ] **Step 4: Update CLI dispatcher for override propagation**

In `scripts/tradingview_cli/main.py`, add:

```python
    proxy = args.get("proxy")
```

near the existing `port` and `headless` lines.

Update launch paths:

```python
        return await launch_browser(port=port, headless=headless, proxy=proxy)
```

```python
        result = await launch_browser(port=port, headless=False, proxy=proxy)
```

```python
        return await ensure_running(port=port, headless=headless, proxy=proxy)
```

When `login-email` injects cookies into a non-running browser, `inject_cookies()` will use `ensure_running()` without explicit CLI proxy. That is acceptable because plugin userConfig/env is the primary path; direct CLI users who need login-email plus CLI-only proxy should set `CLAUDE_PLUGIN_OPTION_PROXY`, `ALL_PROXY`, or `HTTPS_PROXY` in the shell.

- [ ] **Step 5: Run focused tests and verify they pass**

Run from `scripts/`:

```bash
uv run python -m pytest tests/test_plugin.py::test_browser_build_visible_chrome_args_with_proxy tests/test_plugin.py::test_cli_parse_proxy_arg -v
```

Expected: PASS.

---

### Task 5: Apply Proxy to HTTP API Clients

**Files:**
- Modify: `scripts/tradingview_cli/client.py`
- Modify: `scripts/pyproject.toml`
- Modify: `scripts/tests/test_plugin.py`

- [ ] **Step 1: Write failing HTTP proxy tests**

Add this test after `test_settings_proxy_env_for_child()`:

```python
def test_client_resolves_proxy_for_http(monkeypatch):
    """HTTP client proxy resolution uses the unified settings module."""
    from tradingview_cli import client

    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_PROXY", "http://plugin-proxy:8080")
    assert client.get_http_proxy() == "http://plugin-proxy:8080"

    monkeypatch.delenv("CLAUDE_PLUGIN_OPTION_PROXY")
    monkeypatch.setenv("ALL_PROXY", "socks5://env-proxy:1080")
    assert client.get_http_proxy() == "socks5://env-proxy:1080"
    print("  PASS  test_client_resolves_proxy_for_http")
```

Add it to `tests = [...]` after `test_settings_proxy_env_for_child`:

```python
        test_settings_proxy_env_for_child,
        test_client_resolves_proxy_for_http,
        test_cli_help_command,
```

- [ ] **Step 2: Run the HTTP proxy test and verify it fails**

Run from `scripts/`:

```bash
uv run python -m pytest tests/test_plugin.py::test_client_resolves_proxy_for_http -v
```

Expected: FAIL because `client.get_http_proxy` does not exist.

- [ ] **Step 3: Add SOCKS support dependency**

Change `scripts/pyproject.toml` dependencies to include `socksio`:

```toml
dependencies = [
    "pydoll-python>=0.9.0",
    "httpx>=0.27.0",
    "socksio>=1.0.0",
    "websockets>=13.0",
]
```

- [ ] **Step 4: Update HTTP client code**

In `scripts/tradingview_cli/client.py`, add imports:

```python
from .settings import ProxyConfigError, get_proxy
```

Remove the direct `import os` if it becomes unused.

Add this function above `tv_fetch()`:

```python
def get_http_proxy() -> str | None:
    """Return validated proxy for TradingView HTTP requests."""
    return get_proxy()
```

Replace the inline proxy lookup in `tv_fetch()`:

```python
    proxy = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY") or os.environ.get("http_proxy") or os.environ.get("https_proxy")

    async with httpx.AsyncClient(timeout=30.0, proxy=proxy) as client:
```

with:

```python
    try:
        proxy = get_http_proxy()
    except ProxyConfigError as e:
        return {"_error": "invalid_proxy", "_message": str(e)}

    async with httpx.AsyncClient(timeout=30.0, proxy=proxy) as client:
```

In `programmatic_login()`, resolve proxy before creating the `AsyncClient`:

```python
        try:
            proxy = get_http_proxy()
        except ProxyConfigError as e:
            return {"error": str(e)}

        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={
                "User-Agent": USER_AGENT,
                "Origin": "https://www.tradingview.com",
                "Referer": "https://www.tradingview.com/",
            },
            timeout=30.0,
            proxy=proxy,
        ) as client:
```

- [ ] **Step 5: Run the HTTP proxy test and verify it passes**

Run from `scripts/`:

```bash
uv run python -m pytest tests/test_plugin.py::test_client_resolves_proxy_for_http -v
```

Expected: PASS.

- [ ] **Step 6: Sync dependencies if the lockfile is present**

Run from `scripts/`:

```bash
uv sync
```

Expected: dependencies sync successfully and `uv.lock` updates if present.

---

### Task 6: Document Proxy Configuration

**Files:**
- Modify: `README.md`
- Modify: `README-zh.md`
- Modify: `commands/launch.md`
- Modify: `commands/login-email.md`

- [ ] **Step 1: Update README environment/config table**

In `README.md`, replace the `## Environment Variables` section with:

```markdown
## Configuration

The Claude Code plugin declares a `proxy` user configuration field in `.claude-plugin/plugin.json`.

| Setting | Default | Description |
|---------|---------|-------------|
| `proxy` | empty | Optional HTTP/SOCKS proxy for both Chrome traffic and TradingView HTTP API requests. Examples: `http://127.0.0.1:7890`, `socks5://127.0.0.1:7980` |

If `proxy` is empty, the CLI falls back to environment variables in this order: `ALL_PROXY`, `HTTPS_PROXY`, `HTTP_PROXY`, then lowercase variants. `TV_CDP_PORT` still controls the Chrome DevTools Protocol port and defaults to `9333`.
```

Keep the rest of the README unchanged.

- [ ] **Step 2: Update README feature bullet**

In `README.md`, replace:

```markdown
- **Proxy support** — respects `HTTPS_PROXY`/`HTTP_PROXY` environment variables
```

with:

```markdown
- **Proxy support** — plugin `userConfig.proxy` applies to both Chrome and HTTP API traffic, with `ALL_PROXY`/`HTTPS_PROXY`/`HTTP_PROXY` fallback
```

- [ ] **Step 3: Update Chinese README consistently**

In `README-zh.md`, find the proxy feature/config references and update them to say:

```markdown
- **代理支持** — 插件 `userConfig.proxy` 同时作用于 Chrome 与 HTTP API 流量，并保留 `ALL_PROXY` / `HTTPS_PROXY` / `HTTP_PROXY` 环境变量回退
```

Add or update its configuration section with the same accepted schemes: `http://`, `https://`, `socks5://`, `socks4://`.

- [ ] **Step 4: Update launch command docs**

In `commands/launch.md`, change frontmatter argument hint from:

```markdown
argument-hint: "[--headless=false] [--port=9333]"
```

to:

```markdown
argument-hint: "[--headless=false] [--port=9333] [--proxy=socks5://127.0.0.1:7980]"
```

Change usage from:

```markdown
cd "${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}}/scripts" && uv run ./tradingview.py launch [--headless=false] [--port=9333]
```

to:

```markdown
cd "${PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}}/scripts" && uv run ./tradingview.py launch [--headless=false] [--port=9333] [--proxy=socks5://127.0.0.1:7980]
```

Add this option bullet:

```markdown
- `--proxy=socks5://127.0.0.1:7980`: Temporary proxy override. Normal plugin use should configure the manifest `userConfig.proxy` field. If neither is set, the CLI falls back to `ALL_PROXY`, `HTTPS_PROXY`, and `HTTP_PROXY`.
```

- [ ] **Step 5: Update login-email command docs**

In `commands/login-email.md`, add this paragraph under Usage:

```markdown
Proxy behavior: email login uses the same proxy as other TradingView HTTP API calls. Configure the plugin `userConfig.proxy` field for normal use, or use `ALL_PROXY` / `HTTPS_PROXY` / `HTTP_PROXY` as fallback.
```

- [ ] **Step 6: Verify docs mention the new config**

Run from repository root:

```bash
grep -R "userConfig.proxy\|CLAUDE_PLUGIN_OPTION_PROXY\|ALL_PROXY" -n README.md README-zh.md commands/launch.md commands/login-email.md
```

Expected: output includes README, README-zh, launch docs, and login-email docs.

---

### Task 7: Full Verification

**Files:**
- Test: `scripts/tests/test_plugin.py`
- Test: `scripts/pyproject.toml`

- [ ] **Step 1: Run all tests**

Run from `scripts/`:

```bash
uv run python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 2: Run the standalone test runner**

Run from `scripts/`:

```bash
uv run python tests/test_plugin.py
```

Expected: final summary reports `0 failed`.

- [ ] **Step 3: Verify CLI status still works without proxy**

Run from `scripts/`:

```bash
uv run ./tradingview.py status
```

Expected: JSON response includes `running` and no proxy URL value.

- [ ] **Step 4: Verify invalid proxy fails clearly**

Run from `scripts/`:

```bash
uv run ./tradingview.py launch --proxy=ftp://127.0.0.1:21
```

Expected: JSON response includes an `error` containing `Unsupported proxy scheme`.

- [ ] **Step 5: Inspect git diff**

Run from repository root:

```bash
git diff -- .claude-plugin/plugin.json scripts/tradingview_cli/settings.py scripts/tradingview_cli/monitor.py scripts/tradingview_cli/browser.py scripts/tradingview_cli/client.py scripts/tradingview_cli/main.py scripts/pyproject.toml scripts/tests/test_plugin.py README.md README-zh.md commands/launch.md commands/login-email.md
```

Expected: diff only contains proxy userConfig, settings, Chrome/HTTP proxy integration, tests, and docs.

- [ ] **Step 6: Do not commit unless requested**

If the user explicitly asks for a commit later, follow the repository commit workflow and include the plan/spec files only if the user wants planning docs committed.

---

## Self-Review Notes

- Spec coverage: manifest `userConfig.proxy`, unified settings module, Chrome headless/visible integration, HTTP API integration, CLI override, invalid scheme handling, state secrecy, tests, and docs are each covered by a task.
- Placeholder scan: no TBD/TODO/later placeholders remain.
- Type consistency: proxy functions are consistently named `resolve_proxy`, `validate_proxy`, `get_proxy`, `proxy_env_for_child`, and `get_http_proxy`; proxy state is consistently `proxy_configured`.
