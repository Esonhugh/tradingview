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
