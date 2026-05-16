#!/usr/bin/env python3
"""
Technical Analysis Indicators — computed from OHLCV candlestick data.

Supports: MACD, RSI, KDJ (Stochastic), EMA, SMA, Bollinger Bands.
"""

from __future__ import annotations


def ema(data: list[float], period: int) -> list[float | None]:
    """Exponential Moving Average."""
    result: list[float | None] = [None] * len(data)
    if len(data) < period:
        return result
    k = 2.0 / (period + 1)
    result[period - 1] = sum(data[:period]) / period
    for i in range(period, len(data)):
        result[i] = data[i] * k + result[i - 1] * (1 - k)
    return result


def sma(data: list[float], period: int) -> list[float | None]:
    """Simple Moving Average."""
    result: list[float | None] = [None] * len(data)
    if len(data) < period:
        return result
    window_sum = sum(data[:period])
    result[period - 1] = window_sum / period
    for i in range(period, len(data)):
        window_sum += data[i] - data[i - period]
        result[i] = window_sum / period
    return result


def macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    """MACD (Moving Average Convergence Divergence).

    Returns: macd_line, signal_line, histogram arrays.
    """
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)

    macd_line: list[float | None] = [None] * len(closes)
    for i in range(len(closes)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line[i] = ema_fast[i] - ema_slow[i]

    # Signal line = EMA of MACD line
    macd_values = [v for v in macd_line if v is not None]
    signal_line_raw = ema(macd_values, signal) if len(macd_values) >= signal else []

    signal_line: list[float | None] = [None] * len(closes)
    histogram: list[float | None] = [None] * len(closes)

    macd_start = next((i for i, v in enumerate(macd_line) if v is not None), len(closes))
    for j, val in enumerate(signal_line_raw):
        idx = macd_start + j
        if idx < len(closes) and val is not None:
            signal_line[idx] = val
            if macd_line[idx] is not None:
                histogram[idx] = macd_line[idx] - val

    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def rsi(closes: list[float], period: int = 14) -> list[float | None]:
    """Relative Strength Index."""
    result: list[float | None] = [None] * len(closes)
    if len(closes) < period + 1:
        return result

    gains = []
    losses = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        result[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i + 1] = 100.0 - (100.0 / (1.0 + rs))

    return result


def kdj(highs: list[float], lows: list[float], closes: list[float],
        k_period: int = 9, d_period: int = 3, j_smooth: int = 3) -> dict:
    """KDJ (Stochastic Oscillator with J line).

    K = smoothed %K, D = smoothed %D, J = 3*K - 2*D.
    """
    n = len(closes)
    rsv: list[float | None] = [None] * n

    for i in range(k_period - 1, n):
        window_high = max(highs[i - k_period + 1:i + 1])
        window_low = min(lows[i - k_period + 1:i + 1])
        if window_high == window_low:
            rsv[i] = 50.0
        else:
            rsv[i] = (closes[i] - window_low) / (window_high - window_low) * 100.0

    k_line: list[float | None] = [None] * n
    d_line: list[float | None] = [None] * n
    j_line: list[float | None] = [None] * n

    # Initialize K at first valid RSV
    start = k_period - 1
    if start < n and rsv[start] is not None:
        k_line[start] = rsv[start]
        d_line[start] = k_line[start]
        j_line[start] = 3 * k_line[start] - 2 * d_line[start]

    for i in range(start + 1, n):
        if rsv[i] is not None and k_line[i - 1] is not None:
            k_line[i] = (2.0 / d_period) * rsv[i] + (1 - 2.0 / d_period) * k_line[i - 1]
            d_line[i] = (2.0 / d_period) * k_line[i] + (1 - 2.0 / d_period) * d_line[i - 1]
            j_line[i] = 3 * k_line[i] - 2 * d_line[i]

    return {"K": k_line, "D": d_line, "J": j_line}


def bollinger_bands(closes: list[float], period: int = 20, std_dev: float = 2.0) -> dict:
    """Bollinger Bands (middle=SMA, upper/lower = +/- N std devs)."""
    middle = sma(closes, period)
    upper: list[float | None] = [None] * len(closes)
    lower: list[float | None] = [None] * len(closes)

    for i in range(period - 1, len(closes)):
        if middle[i] is not None:
            window = closes[i - period + 1:i + 1]
            std = (sum((x - middle[i]) ** 2 for x in window) / period) ** 0.5
            upper[i] = middle[i] + std_dev * std
            lower[i] = middle[i] - std_dev * std

    return {"upper": upper, "middle": middle, "lower": lower}


def compute_indicators(candles: list[dict], indicators: list[str] | None = None) -> dict:
    """Compute requested indicators from candle data.

    Args:
        candles: List of {open, high, low, close, volume} dicts.
        indicators: List of indicator names. Default: ["macd", "rsi", "kdj"]

    Returns dict mapping indicator name to its output.
    """
    if not candles:
        return {}

    closes = [c["close"] for c in candles if c.get("close") is not None]
    highs = [c["high"] for c in candles if c.get("high") is not None]
    lows = [c["low"] for c in candles if c.get("low") is not None]

    if not indicators:
        indicators = ["macd", "rsi", "kdj"]

    result = {}
    for ind in indicators:
        ind_lower = ind.lower()
        if ind_lower == "macd":
            result["macd"] = macd(closes)
        elif ind_lower == "rsi":
            result["rsi"] = rsi(closes)
        elif ind_lower in ("kdj", "stochastic"):
            result["kdj"] = kdj(highs, lows, closes)
        elif ind_lower in ("boll", "bollinger"):
            result["bollinger"] = bollinger_bands(closes)
        elif ind_lower.startswith("ema"):
            period = int(ind_lower[3:]) if len(ind_lower) > 3 else 20
            result[f"ema{period}"] = ema(closes, period)
        elif ind_lower.startswith("sma"):
            period = int(ind_lower[3:]) if len(ind_lower) > 3 else 20
            result[f"sma{period}"] = sma(closes, period)

    return result


def summarize_indicators(candles: list[dict], indicators: list[str] | None = None) -> dict:
    """Compute indicators and return only the latest values (for quick analysis)."""
    raw = compute_indicators(candles, indicators)
    summary = {}

    for name, data in raw.items():
        if isinstance(data, dict):
            latest = {}
            for key, arr in data.items():
                vals = [v for v in arr if v is not None]
                latest[key] = round(vals[-1], 4) if vals else None
            summary[name] = latest
        elif isinstance(data, list):
            vals = [v for v in data if v is not None]
            summary[name] = round(vals[-1], 4) if vals else None

    return summary
