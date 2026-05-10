#!/usr/bin/env python3
"""
TradingView CLI - Main entry point for uv run.

Usage:
    uv run tradingview.py <command> [options]

Commands:
    launch          Launch/ensure Chrome browser with persistent profile
    stop            Stop the running browser
    status          Check browser CDP connection status
    login-email     Non-interactive login with email/password
    quote           Get spot quote for a symbol
    options-chain   Fetch options chain
    options-expiries List available expiration dates
    screener        Run stock/crypto/forex screener
    search          Search for symbols
    news            Fetch news headlines or story
    watchlists      List/fetch watchlists
    alerts          Fetch price alerts
    chart-state     Read current chart state from browser
    screenshot      Take chart screenshot
"""

import asyncio
import json
import sys

import httpx


def parse_args(argv: list[str]) -> tuple[str, dict]:
    """Parse CLI args into (command, options_dict)."""
    if not argv:
        return "help", {}
    cmd = argv[0]
    args = {}
    i = 1
    while i < len(argv):
        if argv[i].startswith("--"):
            key = argv[i][2:]
            if "=" in key:
                k, v = key.split("=", 1)
                args[k] = v
            elif i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                args[key] = argv[i + 1]
                i += 1
            else:
                args[key] = "true"
        i += 1
    return cmd, args


async def run(cmd: str, args: dict) -> dict:
    """Dispatch command to appropriate handler."""
    from tradingview_cli.browser import (
        launch_browser, stop_browser, get_status, ensure_running, list_pages,
        inject_cookies, DEFAULT_CDP_PORT,
    )
    from tradingview_cli.client import programmatic_login, reset_cookie_cache
    from tradingview_cli.commands import (
        cmd_quote, cmd_options_chain, cmd_options_expiries,
        cmd_screener, cmd_search, cmd_news, cmd_watchlists,
        cmd_alerts, cmd_chart_state, cmd_screenshot,
    )

    port = int(args.get("port", DEFAULT_CDP_PORT))
    headless = args.get("headless", "true") != "false"

    if cmd == "launch":
        return await launch_browser(port=port, headless=headless)

    elif cmd == "login":
        # Always stop existing instance, then launch visible for login
        stop_browser()
        result = await launch_browser(port=port, headless=False)
        # Navigate to sign-in page via CDP
        try:
            import websockets
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"http://127.0.0.1:{port}/json")
                pages = resp.json()
            tv_page = next((p for p in pages if p.get("type") == "page"), None)
            if tv_page:
                ws_url = tv_page["webSocketDebuggerUrl"]
                async with websockets.connect(ws_url, max_size=5*1024*1024) as ws:
                    nav_msg = json.dumps({"id": 1, "method": "Page.navigate", "params": {"url": "https://www.tradingview.com/#signin"}})
                    await ws.send(nav_msg)
                    await ws.recv()
        except Exception:
            pass  # Non-fatal: user can navigate manually
        result["mode"] = "visible"
        result["message"] = "Browser opened at TradingView sign-in page. Please log in, then confirm here."
        return result

    elif cmd == "login-email":
        email = args.get("email")
        password = args.get("password")
        if not email or not password:
            return {"error": "Missing --email and/or --password arguments"}

        # Step 1: Programmatic login via HTTP
        login_result = await programmatic_login(email, password)
        if "error" in login_result:
            return login_result

        # Step 2: Ensure browser is running, then inject cookies
        inject_result = await inject_cookies(login_result["cookies"])
        if "error" in inject_result:
            return inject_result

        # Step 3: Clear cookie cache so next harvest picks up injected cookies
        reset_cookie_cache()

        # Step 4: Verify session works
        try:
            verify = await cmd_watchlists()
            if isinstance(verify, dict) and "_error" in verify:
                return {
                    "status": "login_ok_but_verify_failed",
                    "injected": inject_result["injected"],
                    "user": login_result.get("user", {}),
                    "verify_error": verify.get("_message", str(verify)),
                }
        except Exception:
            pass  # Non-fatal: login succeeded even if verify fails

        return {
            "status": "logged_in",
            "injected": inject_result["injected"],
            "user": login_result.get("user", {}),
        }

    elif cmd == "ensure":
        return await ensure_running(port=port, headless=headless)

    elif cmd == "stop":
        return stop_browser()

    elif cmd == "status":
        status = get_status()
        if status["running"]:
            pages = await list_pages()
            tv_pages = [p for p in pages if "tradingview.com" in p.get("url", "")]
            status["tabs"] = tv_pages
            status["endpoint"] = f"http://127.0.0.1:{status['port']}"
        return status

    elif cmd == "quote":
        ticker = args.get("ticker")
        if not ticker:
            return {"error": "Missing --ticker argument"}
        return await cmd_quote(ticker, args.get("exchange", "NASDAQ"))

    elif cmd == "options-chain":
        ticker = args.get("ticker")
        if not ticker:
            return {"error": "Missing --ticker argument"}
        strikes = int(args["strikes-around-spot"]) if "strikes-around-spot" in args else None
        return await cmd_options_chain(
            ticker, args.get("exchange", "NASDAQ"),
            expiry=args.get("expiry"), opt_type=args.get("type"),
            strikes_around_spot=strikes,
            include_expired=args.get("include-expired", "false") == "true",
        )

    elif cmd == "options-expiries":
        ticker = args.get("ticker")
        if not ticker:
            return {"error": "Missing --ticker argument"}
        return await cmd_options_expiries(
            ticker, args.get("exchange", "NASDAQ"),
            include_expired=args.get("include-expired", "false") == "true",
        )

    elif cmd == "screener":
        columns = args.get("columns", "").split(",") if args.get("columns") else None
        tickers = args.get("tickers", "").split(",") if args.get("tickers") else None
        filter_clauses = json.loads(args["filter"]) if args.get("filter") else None
        return await cmd_screener(
            market=args.get("market", "america"), columns=columns,
            filter_clauses=filter_clauses,
            sort_by=args.get("sort", "volume"), sort_order=args.get("order", "desc"),
            tickers=tickers, label_product=args.get("label-product"),
            limit=int(args.get("limit", 50)), offset=int(args.get("offset", 0)),
        )

    elif cmd == "search":
        query = args.get("query")
        if not query:
            return {"error": "Missing --query argument"}
        return await cmd_search(
            query, sym_type=args.get("type"),
            exchange=args.get("exchange"), country=args.get("country"),
            lang=args.get("lang", "en"),
            limit=int(args.get("limit", 30)), offset=int(args.get("offset", 0)),
        )

    elif cmd == "news":
        return await cmd_news(
            story_id=args.get("id"), symbol=args.get("symbol"),
            category=args.get("category"), area=args.get("area"),
            section=args.get("section"), provider=args.get("provider"),
            lang=args.get("lang", "en"), limit=int(args.get("limit", 20)),
        )

    elif cmd == "watchlists":
        return await cmd_watchlists(list_id=args.get("id"), color=args.get("color"))

    elif cmd == "alerts":
        return await cmd_alerts(args.get("type", "list"))

    elif cmd == "chart-state":
        return await cmd_chart_state(tab_id=args.get("tab"))

    elif cmd == "screenshot":
        return await cmd_screenshot(tab_id=args.get("tab"), output=args.get("output"))

    elif cmd == "help":
        return {"commands": [
            "launch", "login", "login-email", "stop", "ensure", "status", "quote",
            "options-chain", "options-expiries", "screener", "search", "news",
            "watchlists", "alerts", "chart-state", "screenshot",
        ]}

    else:
        return {"error": f"Unknown command: {cmd}", "hint": "Use 'help' to list commands"}


def main():
    """CLI entry point."""
    cmd, args = parse_args(sys.argv[1:])
    try:
        result = asyncio.run(run(cmd, args))
    except Exception as e:
        result = {"error": type(e).__name__, "message": str(e)}
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
