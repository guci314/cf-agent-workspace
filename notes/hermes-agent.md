# Hermes Agent

整理日期：2026-09-21

Nous Research 推出的**开源、自托管 AI agent**。特色：持久记忆、自我学习（从经验创建 skills）、可执行终端命令、消息网关（Telegram / Discord）。配置位于 `~/.hermes/config.yaml`。

与 Claude Code 这类 coding agent 的差别在于**长期记忆 + 自我学习**，能积累对你的理解，而非每次从零开始。

## 两类模型槽位

- **Main model** —— agent 思考用。每条用户消息、每个工具调用循环、每段流式响应都走它
- **Auxiliary models** —— 卸载的小任务：上下文压缩、视觉、网页摘要、**审批评分**、**MCP 工具路由**、会话标题生成、技能搜索

**⚠️ main model 必须能生成文本并驱动工具调用循环。** 因此不生成文本的决策模型（如 Jev）**不能**当 main model。

**切换模型的隐藏成本**：mid-session 切换会重置 prompt cache，下一条消息按全额 input token 计费（而非缓存折扣价 ~75–90% off）。默认会话超过 100,000 tokens 时会要求确认。

## MCP 支持

Hermes 原生支持 MCP，把它当**适配器层**：

> Hermes 仍然是 agent，MCP 服务器提供工具。

配置结构（`~/.hermes/config.yaml`）：

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
      include: []         # 白名单
      exclude: []         # 黑名单；若同时设 include，则 include 优先
    resources: true
    prompts: true
    trust: full           # full | untrusted
```

### 要点

- **工具命名**：`mcp_<server>_<tool>`，例如 `mcp_github_create_issue`
  连字符和点号在注册前替换为下划线，但写 `include`/`exclude` 时要用**原始名**
- **改配置后**：`/reload-mcp`
- **`trust: untrusted`**：该服务器上所有具写能力的工具调用需用户批准。
  `readOnlyHint` 是服务器**自报**的提示，恶意服务器最多让自称只读的工具跳过审批，不会因此获得额外权限
- **OAuth**：HTTP 服务器设 `auth: oauth` 启用 OAuth 2.1 PKCE，token 存 `~/.hermes/mcp-tokens/`

### 何时该用 / 不该用 MCP

**该用**：工具已以 MCP 形式存在、需要通过 RPC 层操作系统、需要细粒度暴露控制、想连内部 API 而不改核心。

**不该用**：内置工具已够用、服务器暴露大量危险工具而没准备好过滤、只需要很窄的集成。

## 扩展机制：Skill vs Tool

- **Skill** —— 能力可用"指令 + shell 命令 + 现有工具"实现时（如 arXiv 搜索、git 工作流、PDF 处理）
- **Tool** —— 需要 API 密钥端到端集成、自定义处理逻辑、二进制数据或流式传输时
- 自定义工具优先走**插件（Plugin）**，而非修改 Hermes 核心
