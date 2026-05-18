#!/usr/bin/env python3
"""
TradingView Cookie Harvester & Authenticated HTTP Client.

Harvests .tradingview.com cookies from the running Chrome profile via CDP
and provides authenticated fetch wrappers for all TradingView APIs.
"""

import json
import os
import time

import httpx
import websockets

from .browser import get_ws_endpoint, inject_cookies
from .paths import COOKIE_CACHE_FILE

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

_cookie_cache: str | None = None

def save_cookies_to_disk(cookies: list[dict], user: dict | None = None) -> None:
    """Persist login cookies to disk for reuse across sessions."""
    COOKIE_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cookies": cookies,
        "user": user or {},
        "saved_at": time.time(),
    }
    COOKIE_CACHE_FILE.write_text(json.dumps(payload))


def load_cookies_from_disk() -> dict | None:
    """Load cached cookies from disk. Returns None if missing/corrupt."""
    if not COOKIE_CACHE_FILE.exists():
        return None
    try:
        data = json.loads(COOKIE_CACHE_FILE.read_text())
        if data.get("cookies"):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return None


def clear_cookies_from_disk() -> None:
    """Remove persisted cookie cache."""
    COOKIE_CACHE_FILE.unlink(missing_ok=True)


async def harvest_cookies() -> str:
    """Harvest TradingView cookies from browser via CDP Storage.getCookies.

    If the browser has no TradingView cookies but a disk cache exists,
    automatically re-injects the cached cookies into the browser.
    """
    global _cookie_cache
    if _cookie_cache:
        return _cookie_cache

    try:
        ws_url = await get_ws_endpoint()
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Cannot connect to browser CDP: {e}")

    async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
        msg = json.dumps({"id": 1, "method": "Storage.getCookies", "params": {}})
        await ws.send(msg)
        resp = json.loads(await ws.recv())

        cookies = resp.get("result", {}).get("cookies", [])
        tv_cookies = [
            c for c in cookies
            if ".tradingview.com" in c.get("domain", "") or "tradingview.com" in c.get("domain", "")
        ]

    # If browser has no session cookie, try restoring from disk cache
    has_session = any(c.get("name") == "sessionid" for c in tv_cookies)
    if not has_session:
        cached = load_cookies_from_disk()
        if cached:
            result = await inject_cookies(cached["cookies"])
            if result.get("ok"):
                # Re-harvest after injection
                async with websockets.connect(ws_url, max_size=10 * 1024 * 1024) as ws:
                    await ws.send(json.dumps({"id": 1, "method": "Storage.getCookies", "params": {}}))
                    resp = json.loads(await ws.recv())
                    cookies = resp.get("result", {}).get("cookies", [])
                    tv_cookies = [
                        c for c in cookies
                        if ".tradingview.com" in c.get("domain", "") or "tradingview.com" in c.get("domain", "")
                    ]

    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in tv_cookies)
    _cookie_cache = cookie_str

    # Auto-persist session cookies to disk whenever we harvest a valid session
    has_session = any(c.get("name") == "sessionid" for c in tv_cookies)
    if has_session:
        disk_cookies = [
            {"name": c["name"], "value": c["value"], "domain": c.get("domain", ".tradingview.com"), "path": c.get("path", "/")}
            for c in tv_cookies
            if c.get("name") in ("sessionid", "sessionid_sign", "device_t")
        ]
        if disk_cookies:
            save_cookies_to_disk(disk_cookies)

    return cookie_str


def reset_cookie_cache():
    """Reset in-memory cached cookies (does not touch disk cache)."""
    global _cookie_cache
    _cookie_cache = None


async def tv_fetch(url: str, method: str = "GET", json_body: dict | None = None,
                   headers: dict | None = None) -> dict:
    """Make authenticated HTTP request to TradingView APIs."""
    try:
        cookies = await harvest_cookies()
    except RuntimeError as e:
        return {"_error": "browser_not_running", "_message": str(e)}
    except Exception as e:
        return {"_error": "cookie_harvest_failed", "_message": str(e)}

    default_headers = {
        "User-Agent": USER_AGENT,
        "Cookie": cookies,
        "Origin": "https://www.tradingview.com",
        "Referer": "https://www.tradingview.com/",
    }
    if headers:
        default_headers.update(headers)

    proxy = os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY") or os.environ.get("http_proxy") or os.environ.get("https_proxy")

    async with httpx.AsyncClient(timeout=30.0, proxy=proxy) as client:
        if method.upper() == "POST":
            resp = await client.post(url, json=json_body, headers=default_headers)
        else:
            resp = await client.get(url, headers=default_headers)

        if resp.status_code == 200:
            try:
                return resp.json()
            except (json.JSONDecodeError, ValueError):
                return {"_raw": resp.text}
        else:
            return {"_error": resp.status_code, "_body": resp.text[:500]}


async def programmatic_login(email: str, password: str) -> dict:
    """Login to TradingView via email/password, return cookies for injection.

    POSTs form-encoded credentials to /accounts/signin/ and collects
    the session cookies (sessionid, device_t, etc.) from the response.
    """
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={
                "User-Agent": USER_AGENT,
                "Origin": "https://www.tradingview.com",
                "Referer": "https://www.tradingview.com/",
            },
            timeout=30.0,
        ) as client:
            resp = await client.post(
                "https://www.tradingview.com/accounts/signin/",
                data={"username": email, "password": password, "remember": "on"},
            )

            if resp.status_code != 200:
                return {"error": f"Login failed: HTTP {resp.status_code}"}

            try:
                data = resp.json()
            except (json.JSONDecodeError, ValueError):
                return {"error": "Login failed: unexpected response format"}

            if data.get("error"):
                msg = data["error"]
                if "two" in str(msg).lower() or "2fa" in str(msg).lower():
                    return {"error": f"2FA required: {msg}. Use the interactive 'login' command instead."}
                return {"error": f"Login failed: {msg}"}

            # Collect all cookies from the client jar
            cookies = []
            for name, value in client.cookies.items():
                cookies.append({
                    "name": name,
                    "value": value,
                    "domain": ".tradingview.com",
                    "path": "/",
                })
            return {"ok": True, "cookies": cookies, "user": data.get("user", {})}

    except httpx.TimeoutException:
        return {"error": "Login request timed out"}
    except httpx.ConnectError:
        return {"error": "Could not connect to TradingView"}
    except Exception as e:
        return {"error": f"Login failed: {type(e).__name__}: {e}"}


async def tv_scan(market: str, body: dict) -> dict:
    """POST to scanner.tradingview.com/{market}/scan2."""
    url = f"https://scanner.tradingview.com/{market}/scan2"
    return await tv_fetch(url, method="POST", json_body=body)
