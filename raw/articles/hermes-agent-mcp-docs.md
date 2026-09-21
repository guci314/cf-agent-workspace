# Hermes Agent — MCP 配置文档摘录

> **Sources**:
> - https://hermes-agent.nousresearch.com/docs/zh-Hans/reference/mcp-config-reference
> - https://hermes-agent.nousresearch.com/docs/zh-Hans/guides/use-mcp-with-hermes
> - https://hermes-agent.nousresearch.com/docs/user-guide/configuring-models
> **Captured**: 2026-09-21
> **Layer**: raw (immutable)

## Hermes Agent 是什么

Nous Research 推出的**开源、自托管 AI 助手**。核心特色：长期记忆、自我学习（从经验创建 skills）、可执行终端命令、支持消息网关（Telegram / Discord）。配置文件在 `~/.hermes/config.yaml`。

## 两类模型槽位（Configuring Models）

- **Main model** — agent 思考用。每条用户消息、每个工具调用循环、每段流式响应都走它。
- **Auxiliary models** — 卸载的小任务：上下文压缩、视觉（图像分析）、网页摘要、**审批评分（approval scoring）**、**MCP 工具路由（MCP tool routing）**、会话标题生成、技能搜索。各有独立槽位，可单独覆盖。

模型切换副作用：mid-session 切换模型会**重置 prompt cache**，下一条消息按全额 input token 计费（而非缓存折扣价 ~75–90% off）。默认当会话上下文超过 100,000 tokens 时，切换前会要求确认（`model.switch_context_confirm_tokens`）。

## MCP 根配置结构

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

## 服务器键说明

- `command` / `args` / `env` — stdio 模式：可执行文件、参数、子进程环境变量
- `url` / `headers` — HTTP 远程 MCP 端点
- `enabled` — false 时完全跳过（不连接、不发现、不注册）
- `timeout` / `connect_timeout` — 工具调用 / 初始连接超时
- `supports_parallel_tool_calls` — 允许该服务器工具并发
- `tools` — 过滤及工具策略
- `auth` — HTTP 认证方式；设为 `oauth` 启用 PKCE 的 OAuth 2.1
- `trust` — `full`（默认）或 `untrusted`。untrusted 服务器上，所有具备写能力的工具调用（即没有 `readOnlyHint: true` 注解的）执行前需用户批准。无法识别的值按 untrusted 处理（失败即关闭）

## tools 过滤语义

- `include` — 白名单：只注册列出的服务器原生工具
- `exclude` — 黑名单：注册除列出名称外的全部
- **两者同时设置时 include 优先**
- `resources`（bool）— 启用/禁用 `list_resources` + `read_resource`
- `prompts`（bool）— 启用/禁用 `list_prompts` + `get_prompt`

能力感知：即使设 `resources: true`，也只有当 MCP 会话实际暴露对应能力时才注册。

## 工具命名

服务器原生工具命名格式：`mcp_<server>_<tool>`
例：`mcp_github_create_issue`、`mcp_filesystem_read_file`

包装器：`mcp_<server>_list_resources` / `_read_resource` / `_list_prompts` / `_get_prompt`

**名称规范化**：服务器名与工具名中的连字符（`-`）和点号（`.`）在注册前替换为下划线。
例：服务器 `my-api` + 工具 `list-items.v2` → `mcp_my_api_list_items_v2`。
注意：写 `include`/`exclude` 过滤器时要使用**原始 MCP 工具名**（含连字符/点号），不是规范化后的名字。

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

## 安装与重载

- 标准安装脚本已含 MCP 支持（`uv pip install -e ".[all]"`）
- 单独安装：`cd ~/.hermes/hermes-agent && uv pip install -e ".[mcp]"`
- 基于 npm 的服务器需 Node.js 与 npx；Python MCP 服务器推荐 `uvx`
- 改配置后重载：`/reload-mcp`
- 命令行添加：`hermes mcp add <name> --command ... --args ...`；测试：`hermes mcp test <name>`

## 官方何时建议用 MCP / 不用

**用**：工具已以 MCP 形式存在且你不想写原生 Hermes 工具；想通过干净 RPC 层操作本地或远程系统；需要细粒度按服务器暴露控制；接入内部 API/数据库而不改 Hermes 核心。

**不用**：内置 Hermes 工具已能胜任；服务器暴露大量危险工具且你未准备好过滤；只需要很窄的集成（原生工具更简单安全）。

心智模型："将 MCP 视为一个适配器层。Hermes 仍然是 agent，MCP 服务器提供工具。"

## 何时该写 Tool / 何时该写 Skill（开发者指南）

- **Skill**：能力可通过指令 + shell 命令 + 现有工具实现（如 arXiv 搜索、git 工作流、PDF 处理）
- **Tool**：需要与 API 密钥端到端集成、自定义处理逻辑、二进制数据处理或流式传输（如浏览器自动化、TTS、视觉分析）

Tool 关键规则：Handler **必须返回 JSON 字符串**（`json.dumps()`），不得返回原始 dict；错误必须以 `{"error": "message"}` 形式返回，不得抛异常；`check_fn` 返回 False 时该工具被静默排除。
