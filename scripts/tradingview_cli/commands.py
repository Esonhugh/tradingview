#!/usr/bin/env python3
"""
TradingView API Commands - All 12 command implementations.
"""

import json
import re
from datetime import date, datetime
from pathlib import Path

import httpx

from .client import tv_fetch, tv_scan


# ═══════════════════════════════════════════════════════════════════════════════
#  QUOTE
# ═══════════════════════════════════════════════════════════════════════════════

QUOTE_COLUMNS = [
    "close", "change", "change_abs", "currency", "update_mode",
    "type", "exchange", "description", "name", "logoid",
    "high", "low", "open", "prev_close_price", "volume",
]


async def cmd_quote(ticker: str, exchange: str = "NASDAQ") -> dict:
    """Get spot quote for a single symbol."""
    symbol = f"{exchange}:{ticker}"
    body = {"columns": QUOTE_COLUMNS, "symbols": {"tickers": [symbol]}}
    data = await tv_scan("global", body)
    if not data or "_error" in data:
        return data

    rows = data.get("symbols", data.get("data", []))
    if not rows:
        return {"error": "No data returned", "symbol": symbol}

    row = rows[0]
    fields = data.get("fields", QUOTE_COLUMNS)
    values = row.get("f", row.get("d", []))
    result = {"symbol": row.get("s", symbol)}
    for i, f in enumerate(fields):
        if i < len(values):
            result[f] = values[i]
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  OPTIONS CHAIN
# ═══════════════════════════════════════════════════════════════════════════════

OPTIONS_COLUMNS = [
    "expiration", "strike", "option-type", "bid", "ask",
    "iv", "delta", "gamma", "theta", "vega", "rho", "volume",
]


async def cmd_options_chain(ticker: str, exchange: str = "NASDAQ",
                            expiry: str | None = None, opt_type: str | None = None,
                            strikes_around_spot: int | None = None,
                            include_expired: bool = False) -> dict:
    """Fetch options chain for an underlying symbol."""
    underlying = f"{exchange}:{ticker}"

    body: dict = {
        "columns": OPTIONS_COLUMNS,
        "sort": {"sortBy": "expiration", "sortOrder": "asc"},
        "range": [0, 500],
        "index_filters": [{"name": "underlying_symbol", "values": [underlying]}],
    }

    # scan2 doesn't support filter2 for options well, so we filter client-side
    data = await tv_scan("options", body)
    if not data or "_error" in data:
        return data

    rows = data.get("symbols", data.get("data", []))
    fields = data.get("fields", OPTIONS_COLUMNS)

    today_int = int(date.today().strftime("%Y%m%d"))
    chain = []
    for row in rows:
        values = row.get("f", row.get("d", []))
        entry = {"symbol": row.get("s", "")}
        for i, f in enumerate(fields):
            if i < len(values):
                entry[f] = values[i]

        # Client-side filters
        exp_val = entry.get("expiration")
        if not include_expired and exp_val and isinstance(exp_val, int) and exp_val < today_int:
            continue
        if expiry:
            # expiry arg can be YYYY-MM-DD or YYYYMMDD
            exp_int = int(expiry.replace("-", ""))
            if exp_val != exp_int:
                continue
        if opt_type:
            if entry.get("option-type", "").lower() != opt_type.lower():
                continue
        chain.append(entry)

    # Filter by strikes around spot
    if strikes_around_spot and chain:
        spot_data = await cmd_quote(ticker, exchange)
        spot = spot_data.get("close")
        if spot:
            chain.sort(key=lambda x: abs((x.get("strike") or 0) - spot))
            chain = chain[:strikes_around_spot * 2]
            chain.sort(key=lambda x: (x.get("expiration", ""), x.get("strike", 0)))

    return {"underlying": underlying, "count": len(chain), "chain": chain}


# ═══════════════════════════════════════════════════════════════════════════════
#  OPTIONS EXPIRIES
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_options_expiries(ticker: str, exchange: str = "NASDAQ",
                               include_expired: bool = False) -> dict:
    """List available option expiration dates."""
    chain_data = await cmd_options_chain(ticker, exchange, include_expired=include_expired)
    if "error" in chain_data or "_error" in chain_data:
        return chain_data

    expiries = {}
    today = date.today()
    for item in chain_data.get("chain", []):
        exp = item.get("expiration")
        if exp:
            # Expiration can be integer YYYYMMDD or string YYYY-MM-DD
            if isinstance(exp, int):
                exp_str = f"{exp // 10000}-{(exp % 10000) // 100:02d}-{exp % 100:02d}"
            else:
                exp_str = str(exp)
            if exp_str not in expiries:
                try:
                    exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
                    dte = (exp_date - today).days
                except ValueError:
                    dte = None
                expiries[exp_str] = {"expiry": exp_str, "dte": dte, "contracts": 0}
            expiries[exp_str]["contracts"] += 1

    result = sorted(expiries.values(), key=lambda x: x["expiry"])
    return {"underlying": f"{exchange}:{ticker}", "count": len(result), "expiries": result}


# ═══════════════════════════════════════════════════════════════════════════════
#  SCREENER
# ═══════════════════════════════════════════════════════════════════════════════

SCREENER_DEFAULT_COLUMNS = [
    "name", "description", "close", "change", "change_abs",
    "volume", "market_cap_basic", "price_earnings_ttm",
]


async def cmd_screener(market: str = "america", columns: list | None = None,
                       filter_clauses: list | None = None, sort_by: str = "volume",
                       sort_order: str = "desc", tickers: list | None = None,
                       label_product: str | None = None,
                       limit: int = 50, offset: int = 0) -> dict:
    """Run stock/crypto/forex/bond screener."""
    cols = columns or SCREENER_DEFAULT_COLUMNS
    limit = max(1, min(500, limit))

    body: dict = {
        "columns": cols,
        "sort": {"sortBy": sort_by, "sortOrder": sort_order},
        "range": [offset, offset + limit],
    }

    if tickers:
        body["symbols"] = {"tickers": tickers}
    if filter_clauses:
        body["filter2"] = {"operator": "and", "operands": filter_clauses}
    if label_product:
        body["preset"] = label_product

    data = await tv_scan(market, body)
    if not data or "_error" in data:
        return data

    rows = data.get("symbols", data.get("data", []))
    fields = data.get("fields", cols)
    results = []
    for row in rows:
        values = row.get("f", row.get("d", []))
        entry = {"symbol": row.get("s", "")}
        for i, f in enumerate(fields):
            if i < len(values):
                entry[f] = values[i]
        results.append(entry)

    return {"market": market, "count": len(results), "total": data.get("totalCount", len(results)), "rows": results}


# ═══════════════════════════════════════════════════════════════════════════════
#  SEARCH
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_search(query: str, sym_type: str | None = None,
                     exchange: str | None = None, country: str | None = None,
                     lang: str = "en", limit: int = 30, offset: int = 0) -> dict:
    """Search for symbols via TradingView autocomplete API."""
    params = {"text": query, "hl": "1", "lang": lang, "search_type": "undefined", "start": str(offset)}
    if sym_type:
        params["type"] = sym_type
    if exchange:
        params["exchange"] = exchange
    if country:
        params["country"] = country

    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"https://symbol-search.tradingview.com/symbol_search/v3/?{qs}"

    data = await tv_fetch(url)
    if "_error" in data:
        return data

    symbols = data.get("symbols", data) if isinstance(data, dict) else data
    if isinstance(symbols, list):
        for s in symbols:
            if isinstance(s, dict):
                for k, v in s.items():
                    if isinstance(v, str):
                        s[k] = re.sub(r"</?em>", "", v)
        return {"count": len(symbols), "results": symbols[:limit]}
    return data


# ═══════════════════════════════════════════════════════════════════════════════
#  NEWS
# ═══════════════════════════════════════════════════════════════════════════════

def _ast_to_text(node) -> str:
    """Recursively flatten TradingView AST body to plain text."""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(_ast_to_text(n) for n in node)
    if isinstance(node, dict):
        children = node.get("children", node.get("content", []))
        tag = node.get("type", "")
        text = _ast_to_text(children) if isinstance(children, (list, dict, str)) else ""
        if tag in ("paragraph", "p"):
            return text + "\n\n"
        if tag in ("heading", "h1", "h2", "h3"):
            return f"\n## {text}\n\n"
        if tag == "br":
            return "\n"
        return text
    return ""


async def cmd_news(story_id: str | None = None, symbol: str | None = None,
                   category: str | None = None, area: str | None = None,
                   section: str | None = None, provider: str | None = None,
                   lang: str = "en", limit: int = 20) -> dict:
    """Fetch news headlines or a specific story."""
    if story_id:
        url = f"https://news-headlines.tradingview.com/v2/story?id={story_id}"
        data = await tv_fetch(url)
        if "_error" in data:
            return data
        story = data.get("story", data)
        if isinstance(story, dict) and "astDescription" in story:
            story["text"] = _ast_to_text(story["astDescription"])
        return story

    params = {"client": "overview", "lang": lang, "limit": str(limit)}
    if symbol:
        params["symbol"] = symbol
    if category:
        params["category"] = category
    if area:
        params["area"] = area
    if section:
        params["section"] = section
    if provider:
        params["provider"] = provider

    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"https://news-headlines.tradingview.com/v2/headlines?{qs}"
    data = await tv_fetch(url)
    if "_error" in data:
        return data

    items = data if isinstance(data, list) else data.get("items", data.get("headlines", []))
    return {"count": len(items) if isinstance(items, list) else 0, "headlines": items}


# ═══════════════════════════════════════════════════════════════════════════════
#  WATCHLISTS
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_watchlists(list_id: str | None = None, color: str | None = None) -> dict:
    """Fetch watchlists (all, by id, or by color flag)."""
    base = "https://www.tradingview.com/api/v1/symbols_list"
    if color:
        url = f"{base}/colored/?source=web"
        return {"color": color, "data": await tv_fetch(url)}
    if list_id:
        url = f"{base}/custom/{list_id}?source=web"
        return {"id": list_id, "data": await tv_fetch(url)}
    # Fetch all categories
    custom = await tv_fetch(f"{base}/custom/?source=web")
    active = await tv_fetch(f"{base}/active/?source=web")
    colored = await tv_fetch(f"{base}/colored/?source=web")
    return {"custom": custom, "active": active, "colored": colored}


# ═══════════════════════════════════════════════════════════════════════════════
#  ALERTS
# ═══════════════════════════════════════════════════════════════════════════════

ALERT_ENDPOINTS = {
    "list": "/list_alerts",
    "active": "/get_active_alerts",
    "triggered": "/get_triggered_alerts",
    "offline": "/get_offline_fires",
    "log": "/get_log",
}


async def cmd_alerts(alert_type: str = "list") -> dict:
    """Fetch price alerts by type."""
    endpoint = ALERT_ENDPOINTS.get(alert_type, "/list_alerts")
    url = f"https://pricealerts.tradingview.com{endpoint}"
    data = await tv_fetch(url)
    if "_error" in data:
        return data

    alerts = data.get("r", data.get("results", data.get("alerts", [])))
    if isinstance(alerts, list):
        normalized = []
        for a in alerts:
            if isinstance(a, dict):
                symbol = a.get("symbol", "")
                if isinstance(symbol, str) and symbol.startswith('={"'):
                    try:
                        parsed = json.loads(symbol[1:])
                        a["symbol_clean"] = parsed.get("symbol", symbol)
                    except json.JSONDecodeError:
                        a["symbol_clean"] = symbol
                normalized.append(a)
        return {"type": alert_type, "count": len(normalized), "alerts": normalized}
    return {"type": alert_type, "data": data}


# ═══════════════════════════════════════════════════════════════════════════════
#  CHART STATE
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_chart_state(tab_id: str | None = None) -> dict:
    """Read current chart symbol, interval, and layout from browser tab."""
    import websockets
    from .browser import get_status

    status = get_status()
    if not status["running"]:
        return {"error": "Browser not running. Use /tradingview:launch first."}

    port = status["port"]

    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"http://127.0.0.1:{port}/json")
        pages = resp.json()

    tv_pages = [p for p in pages if "tradingview.com" in p.get("url", "") and p.get("type") == "page"]
    if not tv_pages:
        return {"error": "No TradingView page open in browser"}

    target = None
    if tab_id:
        target = next((p for p in tv_pages if p["id"] == tab_id), None)
    if not target:
        chart_pages = [p for p in tv_pages if "/chart/" in p.get("url", "")]
        target = chart_pages[0] if chart_pages else tv_pages[0]

    ws_url = target["webSocketDebuggerUrl"]
    async with websockets.connect(ws_url, max_size=5 * 1024 * 1024) as ws:
        js_code = """
        (() => {
            const url = window.location.href;
            const layoutMatch = url.match(/\\/chart\\/([^\\/\\?]+)/);
            const layoutId = layoutMatch ? layoutMatch[1] : null;
            let symbol = '';
            const symbolEl = document.querySelector('[data-symbol-short]');
            if (symbolEl) symbol = symbolEl.getAttribute('data-symbol-short');
            if (!symbol) {
                const titleEl = document.querySelector('.chart-widget .pane-legend-title__description');
                if (titleEl) symbol = titleEl.textContent.trim();
            }
            if (!symbol) {
                const title = document.title;
                const m = title.match(/^([A-Z0-9.]+)/);
                if (m) symbol = m[1];
            }
            let interval = '';
            const intEl = document.querySelector('[data-value][data-active="true"]');
            if (intEl) interval = intEl.getAttribute('data-value');
            if (!interval) {
                const intBtn = document.querySelector('.apply-common-tooltip[class*="isActive"]');
                if (intBtn) interval = intBtn.textContent.trim();
            }
            return JSON.stringify({symbol, interval, layoutId, url});
        })()
        """
        msg = json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": js_code, "returnByValue": True}})
        await ws.send(msg)
        resp_msg = json.loads(await ws.recv())
        result_val = resp_msg.get("result", {}).get("result", {}).get("value", "{}")
        try:
            state = json.loads(result_val)
        except (json.JSONDecodeError, TypeError):
            state = {"raw": result_val}

        return {"tab_id": target["id"], "title": target.get("title", ""), **state}


# ═══════════════════════════════════════════════════════════════════════════════
#  SCREENSHOT
# ═══════════════════════════════════════════════════════════════════════════════

async def cmd_screenshot(tab_id: str | None = None, output: str | None = None) -> dict:
    """Take a PNG screenshot of a TradingView chart tab."""
    import base64
    import websockets
    from .browser import get_status

    status = get_status()
    if not status["running"]:
        return {"error": "Browser not running. Use /tradingview:launch first."}

    port = status["port"]

    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"http://127.0.0.1:{port}/json")
        pages = resp.json()

    tv_pages = [p for p in pages if "tradingview.com" in p.get("url", "") and p.get("type") == "page"]
    if not tv_pages:
        return {"error": "No TradingView page open in browser"}

    target = None
    if tab_id:
        target = next((p for p in tv_pages if p["id"] == tab_id), None)
    if not target:
        chart_pages = [p for p in tv_pages if "/chart/" in p.get("url", "")]
        target = chart_pages[0] if chart_pages else tv_pages[0]

    ws_url = target["webSocketDebuggerUrl"]
    async with websockets.connect(ws_url, max_size=20 * 1024 * 1024) as ws:
        msg = json.dumps({"id": 1, "method": "Page.captureScreenshot", "params": {"format": "png"}})
        await ws.send(msg)
        resp_msg = json.loads(await ws.recv())
        b64_data = resp_msg.get("result", {}).get("data", "")

    if not b64_data:
        return {"error": "Screenshot capture failed"}

    if not output:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        output = str(Path.home() / f"tradingview-{ts}.png")

    img_bytes = base64.b64decode(b64_data)
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_bytes(img_bytes)
    return {"path": output, "size_bytes": len(img_bytes), "tab": target.get("title", "")}
