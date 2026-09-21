---
title: MCP Integration
created: 2026-09-21
updated: 2026-09-21
type: concept
tags: [integration, mcp]
sources: [raw/articles/hermes-mcp-docs.md]
---

# MCP Integration

**MCP（Model Context Protocol）** 是 agent 与外部工具服务器之间的标准协议。在 [[hermes-agent]] 这类运行时里，它的定位是**适配器层**：

> Hermes 仍然是 agent，MCP 服务器提供工具。

心智模型：不是"连接一切"，而是**以最小的有效范围连接正确的东西**。

## 配置结构

Hermes 在 `~/.hermes/config.yaml` 的 `mcp_servers` 块下配置：

```yaml
mcp_servers:
  <server_name>:
    command: "..."        # stdio 模式
    args: []
    env: {}
    # OR
    url: "..."            # HTTP 模式
    headers: {}

    enabled: true
    timeout: 120
    connect_timeout: 60
    tools:
      include: []
      exclude: []
    resources: true
    prompts: true
    trust: full           # full | untrusted
```

## 工具命名

`mcp_<server>_<tool>`，例如 `mcp_github_create_issue`。

连字符和点号在注册前替换为下划线：服务器 `my-api` 的 `list-items.v2` → `mcp_my_api_list_items_v2`。
（但写 `include`/`exclude` 过滤器时要用**原始名**。）

## 过滤语义

- `include` 存在 → 白名单，只注册列出的
- `exclude` 存在且无 `include` → 黑名单
- 两者同时设置 → **`include` 优先**

## 安全要点

- **`trust: untrusted`** —— 该服务器上所有具写能力的工具调用（即没有 `readOnlyHint: true` 注解的）执行前都需用户批准。`readOnlyHint` 是服务器**自报**的提示，恶意服务器最多让自称只读的工具跳过审批，不会因此获得额外权限
- **认证** —— HTTP 服务器设 `auth: oauth` 启用 OAuth 2.1 PKCE；token 持久化到 `~/.hermes/mcp-tokens/<server>.json`
- **优先白名单** —— 对内部 API 等敏感系统，严格白名单远优于排除列表

## 何时该用 / 不该用

**该用：**
- 工具已以 MCP 形式存在，不想构建原生工具
- 需要通过干净的 RPC 层操作本地或远程系统
- 需要细粒度的按服务器暴露控制
- 想连内部 API 而不改 runtime 核心

**不该用：**
- 内置工具已能做好
- 服务器暴露大量危险工具而没准备好过滤
- 只需要很窄的集成（原生工具更简单安全）

## 为什么与本 wiki 相关

[[jev]] 已有社区 MCP server 形态（暴露 `jev_classify` / `jev_score` / `jev_check` / `jev_ask`），
而 [[hermes-agent]] 原生支持 MCP —— 因此 MCP 是二者对接的天然桥梁。方案见 [[jev-in-hermes]]。

## 相关

- [[hermes-agent]] —— 支持 MCP 的运行时
- [[jev-in-hermes]] —— 具体集成方案
- [[jev]] —— 通过 MCP 接入的决策模型
