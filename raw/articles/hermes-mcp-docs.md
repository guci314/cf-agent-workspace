# Hermes Agent — MCP 配置参考

> Source: https://hermes-agent.nousresearch.com/docs/zh-Hans/reference/mcp-config-reference
>          https://hermes-agent.nousresearch.com/docs/zh-Hans/guides/use-mcp-with-hermes
> Publisher: Nous Research · Archived: 2026-09-21

## Hermes Agent 项目定位

Hermes Agent 是 Nous Research 推出的**开源、自托管 AI agent**。核心特色（据官方文档）：持久记忆、自我创建 skills、消息网关（Telegram / Discord 等）、内置学习循环。

## 根配置结构

MCP 配置位于 `~/.hermes/config.yaml` 的 `mcp_servers` 块下：

```yaml
mcp_servers:
  <server_name>:
    command: "..."        # stdio servers
    args: []
    env: {}
    # OR
    url: "..."            # HTTP servers
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

## 服务器键

| 键 | 类型 | 适用范围 | 含义 |
|----|------|---------|------|
| `command` | string | stdio | 要启动的可执行文件 |
| `args` | list | stdio | 子进程参数 |
| `env` | mapping | stdio | 传给子进程的环境变量 |
| `url` | string | HTTP | 远程 MCP 端点 |
| `headers` | mapping | HTTP | 请求头 |
| `enabled` | bool | 两者 | false 时完全跳过 |
| `timeout` | number | 两者 | 工具调用超时 |
| `connect_timeout` | number | 两者 | 初始连接超时 |
| `tools` | mapping | 两者 | 过滤及工具策略 |
| `auth` | string | HTTP | 设为 `oauth` 启用 OAuth 2.1 PKCE |
| `trust` | string | 两者 | `full`（默认）或 `untrusted`。untrusted 下所有写能力工具调用需用户批准 |

## 工具命名

服务器原生 MCP 工具命名为：`mcp_<server>_<tool>`

示例：
- `mcp_github_create_issue`
- `mcp_filesystem_read_file`

连字符（`-`）和点号（`.`）在注册前替换为下划线：
名为 `my-api` 的服务器暴露 `list-items.v2` → `mcp_my_api_list_items_v2`

注意：编写 `include`/`exclude` 过滤器时要用**原始名**（含连字符/点号），不是规范化后的名字。

## 过滤语义

- `include` 存在 → 只注册列出的工具
- `exclude` 存在且无 `include` → 注册除列出外的所有工具
- 两者同时设置 → **`include` 优先**

## 配置示例：GitHub 安全白名单

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

## 重新加载

修改 MCP 配置后：`/reload-mcp`

## 何时使用 MCP（官方指南）

**适合：**
- 工具已以 MCP 形式存在，且你不想构建原生 Hermes 工具
- 希望 Hermes 通过干净的 RPC 层操作本地或远程系统
- 需要细粒度的按服务器暴露控制
- 想把 Hermes 连到内部 API、数据库或公司系统，而不修改 Hermes 核心

**不适合：**
- 内置 Hermes 工具已能很好地完成该工作
- 服务器暴露大量危险工具而你没准备好过滤
- 只需要一个很窄的集成，原生工具更简单安全

## Hermes 模型槽位（来自 configuring-models 文档）

Hermes 使用两类模型槽位：

- **Main model** —— agent 思考用。每条用户消息、每个工具调用循环、每段流式响应都走它。
- **Auxiliary models** —— 卸载的小任务：上下文压缩、视觉（图像分析）、网页摘要、**审批评分**、**MCP 工具路由**、会话标题生成、技能搜索。每个有独立槽位，可单独覆盖。
