# TradingView Proxy Parameter Design

## Goal

Add a plugin user configuration field for a proxy and apply it consistently to both TradingView Chrome traffic and TradingView HTTP API requests.

## Configuration Entry

Add a non-required `proxy` field to `.claude-plugin/plugin.json` under `userConfig`:

```json
"userConfig": {
  "proxy": {
    "type": "string",
    "title": "Proxy URL (optional)",
    "description": "HTTP or SOCKS5 proxy for TradingView Chrome and HTTP API requests, e.g. socks5://127.0.0.1:7980. Leave empty to auto-detect from ALL_PROXY / HTTPS_PROXY / HTTP_PROXY environment variables.",
    "default": "",
    "required": false
  }
}
```

The plugin should not use `.claude/tradingview.local.md` for this feature.

## Proxy Resolution

Create a small `tradingview_cli.settings` module that owns proxy lookup and validation. The proxy priority is:

1. An explicit CLI override, if supplied by a caller.
2. Claude Code injected plugin user config for `proxy`.
3. Environment variables: `ALL_PROXY`, `HTTPS_PROXY`, `HTTP_PROXY`, then lowercase variants.
4. No proxy.

Empty strings are treated as unset.

Allowed proxy schemes are `http://`, `https://`, `socks5://`, and `socks4://`. Unsupported schemes should produce a clear error at the boundary using the setting.

## Chrome Integration

Apply the resolved proxy to both Chrome launch paths:

- `tradingview_cli.monitor.launch_chrome()` appends `--proxy-server=<proxy>` when a proxy is configured.
- `tradingview_cli.browser.launch_browser()` appends the same flag for visible login/manual Chrome launches.
- `launch_browser()` may pass the resolved proxy to the monitor process through the child environment so monitor-launched Chrome sees the same value.

Monitor/browser state should include only `proxy_configured: true/false`, not the full proxy URL.

## HTTP API Integration

Use the same resolved proxy for all TradingView HTTP clients:

- `tv_fetch()` uses the resolved proxy for scanner, quote, search, news, watchlist, alert, and related HTTP calls.
- `programmatic_login()` uses the resolved proxy for email/password login.

The current environment-variable behavior remains as fallback, but proxy lookup is centralized in the settings module.

## CLI Behavior

The primary user path is plugin `userConfig.proxy`. A temporary `--proxy=...` CLI override may be supported for direct CLI use and tests, but it is not the main configuration mechanism.

## Error Handling

- Missing or empty proxy means no proxy unless an environment variable fallback is present.
- Invalid schemes return clear errors from launch/login/API boundaries.
- No proxy connectivity preflight is added, so browser startup and API calls do not block on a separate probe.
- Authentication proxy URLs are passed through unchanged if the user provides them.

## Out of Scope

- Per-command proxy selection.
- A `.claude/tradingview.local.md` configuration file.
- Removing environment-variable proxy support.
- Masking or rewriting authentication proxy URLs beyond avoiding storage in state output.

## Testing

Add or update tests to cover:

- Manifest contains `userConfig.proxy` with the expected schema.
- Proxy resolution priority and empty-value behavior.
- Invalid proxy scheme handling.
- Monitor/headless Chrome launch args include `--proxy-server=<proxy>` when configured.
- Visible Chrome launch args include `--proxy-server=<proxy>` when configured.
- HTTP client construction uses the resolved proxy.

## Documentation

Update README and command documentation to describe the new plugin user config field, accepted proxy URL schemes, fallback environment variables, and that the proxy applies to both Chrome and HTTP API traffic.
