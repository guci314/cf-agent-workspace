# Hermes Agent — MCP 与模型配置 — 原始资料

> 来源 1：https://hermes-agent.nousresearch.com/docs/zh-Hans/reference/mcp-config-reference
> 来源 2：https://hermes-agent.nousresearch.com/docs/zh-Hans/guides/use-mcp-with-hermes
> 来源 3：https://hermes-agent.nousresearch.com/docs/user-guide/configuring-models
> 来源 4：https://hermes-agent.nousresearch.com/docs/zh-Hans/developer-guide/adding-tools
> 来源 5：https://blog.kyomind.tw/hermes-agent/
> 存档日期：2026-09-21

## 一、Hermes Agent 是什么

Nous Research 推出的**开源 AI 助理项目**。核心特色：
- **长期记忆**：记住与你互动，累积对你的理解
- **自我学习**：每次任务完成后回顾并优化
- **可执行指令**：能操作 terminal，跑命令、改文件、装包

与一般 coding agent（如 Claude Code）的区别就在"长期记忆 + 自我学习"，让它能真正
"成长"为专属助理。跑在用户自己机器上。

## 二、模型槽位（Configuring Models）

Hermes 使用**两类模型槽位**：

**Main model（主模型）** — agent 思考用的模型。每一条用户消息、每一次工具调用循环、
每一段流式响应都走这个模型。

**Auxiliary models（辅助模型）** — agent 外包出去的小任务。包括：
- 上下文压缩（context compression）
- 视觉（图像分析）
- 网页摘要
- **审批评分（approval scoring）**
- **MCP 工具路由（MCP tool routing）**
- 会话标题生成
- 技能搜索（skill search）

每个辅助任务有独立槽位，可单独覆盖。

配置文件：`~/.hermes/config.yaml` 的 `model` 段。首次运行 `hermes setup` 或
`hermes model` 时，`model: ""` 会被升级成含 `provider`, `default`, `base_url`,
`api_mode` 的映射结构。

切换模型：`/model` 斜杠命令（CLI/TUI/Telegram/Discord 均可用）。

## 三、MCP 配置参考

配置文件：`~/.hermes/config.yaml` 的 `mcp_servers` 块。

### 根配置结构

```yaml
mcp_servers:
  <server_name>:
    command: "..."        # stdio 服务器
    args: []
    env: {}

    # OR
    url: "..."            # HTTP 服务器
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

### 服务器键说明

| 键 | 类型 | 适用范围 | 含义 |
|---|---|---|---|
| `command` | string | stdio | 要启动的可执行文件 |
| `args` | list | stdio | 子进程参数 |
| `env` | mapping | stdio | 传给子进程的环境变量 |
| `url` | string | HTTP | 远程 MCP 端点 |
| `headers` | mapping | HTTP | 请求头 |
| `enabled` | bool | 两者 | false 时完全跳过 |
| `timeout` | number | 两者 | 工具调用超时 |
| `connect_timeout` | number | 两者 | 初始连接超时 |
| `supports_parallel_tool_calls` | bool | 两者 | 允许工具并发 |
| `tools` | mapping | 两者 | 过滤及工具策略 |
| `auth` | string | HTTP | 设为 `oauth` 启用 PKCE 的 OAuth 2.1 |
| `trust` | string | 两者 | `full`（默认）或 `untrusted` |

`trust: untrusted` 时，所有具备写能力的工具调用（没有 `readOnlyHint: true` 注解的）
在执行前需用户批准。无法识别的值按 `untrusted` 处理（失败即关闭）。

### tools 过滤语义

- `include` 设了 → **只注册**列出的工具（白名单）
- `exclude` 设了且无 `include` → 注册除列出名称外的所有工具（黑名单）
- **两者同时设置时 `include` 优先**

### 工具命名规则

服务器原生工具命名格式：`mcp_<server>_<tool>`

示例：
- `mcp_github_create_issue`
- `mcp_filesystem_read_file`

名称规范化：服务器名和工具名中的连字符（`-`）和点号（`.`）在注册前替换为下划线。
例如服务器 `my-api` 暴露工具 `list-items.v2` → 注册为 `mcp_my_api_list_items_v2`。

**注意**：编写 include/exclude 过滤器时要使用**原始 MCP 工具名**（含连字符/点号），
而非规范化后的名称。

### 重载配置

修改 MCP 配置后使用 `/reload-mcp`。

### 配置示例（GitHub 白名单）

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

## 四、使用 MCP 的指导原则（官方）

**何时使用 MCP：**
- 工具已以 MCP 形式存在，且不想构建原生 Hermes 工具
- 希望通过干净的 RPC 层操作本地或远程系统
- 需要细粒度的按服务器暴露控制
- 希望连接内部 API、数据库或公司系统，而无需修改 Hermes 核心

**何时不要用 MCP：**
- 内置 Hermes 工具已能很好完成
- 服务器暴露大量危险工具且未准备好过滤
- 只需要非常窄的集成（原生工具更简单、更安全）

> 心智模型："将 MCP 视为一个适配器层：Hermes 仍然是 agent，MCP 服务器提供工具，
> Hermes 在启动或重新加载时发现这些工具，模型可以像使用普通工具一样使用它们。"

> "良好的 MCP 使用不是'连接一切'，而是'以最小的有效范围连接正确的东西'。"

**安装 MCP 支持：**

```bash
cd ~/.hermes/hermes-agent
uv pip install -e ".[mcp]"
```

基于 npm 的服务器需 Node.js + npx；许多 Python MCP 服务器推荐用 `uvx`。

**添加服务器（CLI）：**

```bash
hermes mcp add chrome-devtools-win --command cmd.exe --args /c npx -y chrome-devtools-mcp@latest
hermes mcp test <server-name>
```

## 五、添加原生工具的机制（供对比）

**先问自己：这应该是一个 skill 吗？**

- **应创建 Skill**：能力可通过"指令 + shell 命令 + 现有工具"实现
  （如 arXiv 搜索、git 工作流、Docker 管理、PDF 处理）
- **应创建 Tool**：需要与 API 密钥端到端集成、自定义处理逻辑、二进制数据处理或流式传输
  （如浏览器自动化、TTS、视觉分析）

**仅限内置核心工具**：本页用于向仓库本身添加 Hermes 内置工具。个人专用/项目本地/
其他自定义工具应使用**插件**方式，不修改 Hermes 核心。

添加一个内置工具涉及 2 个文件：
1. `tools/your_tool.py` — handler、schema、check 函数、`registry.register()` 调用
2. `toolsets.py` — 将工具名加入 `_HERMES_CORE_TOOLS`

**关键规则：**
- Handler **必须返回 JSON 字符串**（`json.dumps()`），不得返回原始 dict
- 错误**必须以 `{"error": "message"}` 形式返回**，不得抛异常
- `check_fn` 在构建工具定义时调用 —— 返回 False 则该工具被静默排除
- handler 接收 `(args: dict, **kwargs)`，args 是 LLM 的工具调用参数
