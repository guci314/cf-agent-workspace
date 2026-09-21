---
title: Hermes Agent — MCP 集成文档（配置参考 + 使用指南）
source:
  - https://hermes-agent.nousresearch.com/docs/zh-Hans/reference/mcp-config-reference
  - https://hermes-agent.nousresearch.com/docs/zh-Hans/guides/use-mcp-with-hermes
  - https://hermes-agent.nousresearch.com/docs/user-guide/configuring-models
organization: Nous Research
retrieved: 2026-09-21
type: raw-source
note: 原始资料，immutable
---

# Hermes Agent — MCP 集成

Hermes Agent 是 Nous Research 推出的开源、自托管 AI agent。特性：持久记忆、自我创建 skills、消息网关（Telegram / Discord 等）。

## 模型槽位（Configuring Models）

Hermes 使用两类模型槽位：

- **Main model** — agent 思考用的模型。每条用户消息、每个工具调用循环、每段流式响应都经过它。
- **Auxiliary models** — 卸载出去的小任务。包含：上下文压缩、视觉（图像分析）、网页摘要、**审批评分（approval scoring）**、**MCP 工具路由（MCP tool routing）**、会话标题生成、技能搜索。每个槽位可独立覆盖。

配置文件：`~/.hermes/config.yaml`，`model` 段。

## MCP 根配置结构

```yaml
mcp_servers:
  <server_name>:
    command: "..."          # stdio servers
    args: []
    env: {}
    # OR
    url: "..."              # HTTP servers
    headers: {}
    enabled: true
    timeout: 120
    connect_timeout: 60
    supports_parallel_tool_calls: false
    tools:
      include: []
      exclude: []
    resources: true
    prompts: true
```

### 服务器键要点

- `command` / `args` / `env` — stdio 服务器
- `url` / `headers` — HTTP 远程 MCP 端点
- `enabled` — false 时完全跳过该服务器（不连接、不发现、不注册工具）
- `trust` — `full`（默认）或 `untrusted`。untrusted 下所有具备写能力的工具调用在执行前需用户批准
- `auth` — 设为 `oauth` 启用带 PKCE 的 OAuth 2.1（仅 HTTP 传输）
- `supports_parallel_tool_calls` — 允许该服务器工具并发执行

### tools 过滤

- `include` 白名单：只注册列出的工具
- `exclude` 黑名单：注册除列出之外的所有工具
- 两者同时设置时 **include 优先**
- 过滤器使用**原始 MCP 工具名称**（含连字符/点号），不是规范化后的名字

## 工具命名

服务器原生 MCP 工具注册为：`mcp_<server>_<tool>`

例：`mcp_github_create_issue`

名称规范化：连字符 `-` 和点号 `.` 在注册前替换为下划线。服务器 `my-api` 的工具 `list-items.v2` → `mcp_my_api_list_items_v2`。

包装器同样前缀：`mcp_<server>_list_resources`、`mcp_<server>_read_resource`、`mcp_<server>_list_prompts`、`mcp_<server>_get_prompt`。

## 重载配置

修改 MCP 配置后：`/reload-mcp`

## 验证 MCP 已加载

- 配置后 Hermes 横幅/状态应显示 MCP 集成
- 询问 Hermes 当前有哪些可用工具
- 或向 Hermes 提问："Tell me which MCP-backed tools are available right now."

## 何时应该使用 MCP

应该用：
- 工具已以 MCP 形式存在，且不想构建原生 Hermes 工具
- 希望通过干净的 RPC 层操作本地或远程系统
- 需要细粒度的按服务器暴露控制
- 连接到内部 API、数据库或公司系统，而不修改 Hermes 核心

不该用：
- 内置 Hermes 工具已能很好地完成该工作
- 服务器暴露大量危险工具而未准备好过滤
- 只需要一个非常窄的集成（原生工具更简单、更安全）

## 配置示例

GitHub 安全白名单：

```yaml
mcp_servers:
  github:
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_PERSONAL_ACCESS_TOKEN: "***"
    tools:
      include: [list_issues, create_issue, update_issue, search_code]
    resources: false
    prompts: false
```

Stripe 黑名单：

```yaml
mcp_servers:
  stripe:
    url: "https://mcp.stripe.com"
    headers:
      Authorization: "Bearer ***"
    tools:
      exclude: [delete_customer, refund_payment]
```

## 安装 MCP 支持

标准安装脚本已包含。若单独添加：

```bash
cd ~/.hermes/hermes-agent
uv pip install -e ".[mcp]"
```

基于 npm 的服务器需要 Node.js 和 npx；许多 Python MCP 服务器推荐用 `uvx`。
