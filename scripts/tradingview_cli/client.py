#!/usr/bin/env python3
"""
TradingView Cookie Harvester & Authenticated HTTP Client.

Harvests .tradingview.com cookies from the running Chrome profile via CDP
and provides authenticated fetch wrappers for all TradingView APIs.
"""

import json
from pathlib import Path

import httpx
import websockets

from .browser import get_ws_endpoint, get_status

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

_cookie_cache: str | None = None


async def harvest_cookies() -> str:
    """Harvest TradingView cookies from browser via CDP Storage.getCookies."""
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
        cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in tv_cookies)
        _cookie_cache = cookie_str
        return cookie_str


def reset_cookie_cache():
    """Reset cached cookies."""
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

    async with httpx.AsyncClient(timeout=30.0) as client:
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
