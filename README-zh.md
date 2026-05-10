# TradingView Claude Code 插件

基于持久化无头 Chrome 的 TradingView 只读数据访问插件，具备自动生命周期管理能力。

## 功能特性

- **13 个 slash 命令** — 覆盖行情报价、期权链、筛选器、新闻、自选列表、提醒、图表状态、截图
- **持久化 Chrome Profile** — 位于 `~/.claude/plugins/data/.chrome-profiles/tradingview`，登录一次永久有效
- **插件 Monitor** — Chrome 自动启动、每 10 秒健康检查、崩溃自动重启、端口冲突自动规避
- **3 个分析 Skill** — 筛选器、期权分析、新闻研究的引导式工作流

## 前置要求

| 依赖 | 安装方式 |
|------|---------|
| **uv** (必须) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Python 3.11+ | uv 自动管理 |
| Chrome/Chromium | 系统浏览器 |

> **uv 是必须的。** 插件在没有 uv 的情况下会拒绝工作。使用 `/tradingview:preflight` 验证所有前置条件。

## 快速开始

```bash
# 1. 安装依赖
cd <plugin-root>/scripts
uv sync

# 2. 首次使用：执行登录命令
/tradingview:login

# 3. 在弹出的浏览器窗口中登录 TradingView
#    登录状态将持久化保存到 ~/.claude/plugins/data/.chrome-profiles/tradingview

# 4. 完成！插件 Monitor 会在每次会话自动启动无头 Chrome
```

## 命令列表

| 命令 | 说明 |
|------|------|
| `/tradingview:preflight` | 验证前置条件（uv、依赖、Profile） |
| `/tradingview:launch` | 启动 Chrome（持久化 Profile） |
| `/tradingview:login` | 打开可见浏览器进行登录 |
| `/tradingview:stop` | 停止浏览器和 Monitor |
| `/tradingview:status` | 检查连接状态和打开的标签页 |
| `/tradingview:quote <ticker>` | 获取实时行情报价 |
| `/tradingview:options-chain <ticker>` | 获取期权链（含 Greeks） |
| `/tradingview:options-expiries <ticker>` | 列出可用到期日 |
| `/tradingview:screener` | 运行股票/加密/外汇筛选器 |
| `/tradingview:search <query>` | 按名称搜索标的 |
| `/tradingview:news` | 获取新闻头条或阅读全文 |
| `/tradingview:watchlists` | 列出/获取自选列表或颜色标记 |
| `/tradingview:alerts` | 获取价格提醒（列表/活跃/已触发） |
| `/tradingview:chart-state` | 读取当前图表标的和周期 |
| `/tradingview:screenshot` | 截取图表为 PNG |

## Skills（上下文触发）

| Skill | 触发词 |
|-------|--------|
| `screener` | "筛选股票"、"找超卖"、"市场扫描"、"成交量排名" |
| `options-analysis` | "分析期权"、"最佳到期日"、"铁鹰策略"、"垂直价差" |
| `news-research` | "AAPL 新闻"、"为什么涨/跌"、"市场头条"、"情绪分析" |

## 插件 Monitor（自动启动）

插件使用 Claude Code 原生 `monitors` 组件自动管理 Chrome：

- **自动启动**：插件加载时 Monitor 自动启动无头 Chrome
- **健康检查**：每 10 秒通过 CDP HTTP 验证连接
- **崩溃自动恢复**：Chrome 崩溃后自动重启（最多 3 次）
- **端口冲突规避**：若 9333 端口被占用，自动选择下一个可用端口
- **状态文件**：Monitor 写入 `.monitor.json`，CLI 命令通过读取该文件获取运行状态

Monitor 将状态信息输出到 stdout，Claude 以通知形式接收（如 "Chrome launched"、"Chrome restarted after crash"）。

首次登录设置完成后，所有数据命令无需手动管理浏览器即可正常工作。

## 项目结构

```
tradingview/
├── .claude-plugin/plugin.json  # 插件清单 (v0.2.0)
├── commands/                   # 14 个 slash 命令
├── skills/                     # 3 个分析工作流 Skill
├── monitors/                   # 插件 Monitor（自动管理 Chrome）
│   └── monitors.json
└── scripts/                    # Python uv 项目
    ├── pyproject.toml
    ├── tradingview.py          # CLI 入口：uv run ./tradingview.py <cmd>
    └── tradingview_cli/        # Python 包
        ├── monitor.py          # Monitor 守护进程（健康检查、自动重启）
        ├── browser.py          # Chrome 生命周期管理（读取 Monitor 状态）
        ├── client.py           # Cookie 收割 + 认证 HTTP 客户端
        ├── commands.py         # 命令实现
        └── main.py             # CLI 分发器
```

## 设计理念

1. **Monitor 生命周期管理**：插件 Monitor 守护进程管理 Chrome，具备健康检查和自动重启能力，取代手动启动/Hook 模式
2. **持久化 Chrome Profile**：在 `~/.claude/plugins/data/.chrome-profiles/tradingview` 一次登录，跨会话保持
3. **CDP 健康检查**：通过 HTTP GET `/json/version` 检测存活，而非 PID 检查（Chrome headless 会产生子进程）
4. **只读设计**：不执行交易、不创建提醒、不修改自选
5. **uv 项目管理**：快速、可复现的依赖管理

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TV_CDP_PORT` | `9333` | Chrome DevTools Protocol 端口 |

## 许可证

MIT
