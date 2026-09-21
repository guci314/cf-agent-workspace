---
title: Jev 在 Hermes 中怎么用
created: 2026-09-21
updated: 2026-09-21
type: query
tags: [decision-model, integration, mcp, agent-runtime]
sources: [raw/articles/typesafe-jev.md, raw/articles/hermes-mcp-docs.md]
---

# Jev 在 Hermes 中怎么用

**问题**：如何在 [[hermes-agent]] 中调用 [[jev]] 决策模型？

## 先排除一个错误做法

**Jev 不能当 Hermes 的主模型（main model）。**

依据 Hermes 官方对模型槽位的定义：main model 是"agent 思考用"的模型——**每条用户消息、每个工具调用循环、每段流式响应都走它**。

而 Jev 的定义性特征是**不具备字符串生成能力**（见 [[system-one-models]]），无法驱动工具调用循环。这两者根本互斥。

**那辅助槽位呢？** Hermes 的 auxiliary models 里有两类在语义上正契合 Jev：
- **审批评分（approval scoring）**
- **MCP 工具路由（MCP tool routing）**

但官方未公开说明这些槽位支持 Jev 的非标准 API 接口（Jev 不是 `chat/completions` 形态），
因此**不建议硬塞**，除非愿意承担不被支持的风险。

## 正确做法：经 MCP 接入为工具

[[jev]] 已有社区 MCP server，[[hermes-agent]] 原生支持 MCP，[[mcp-integration]] 就是二者的桥。

### 1. 在 `~/.hermes/config.yaml` 中加服务器

```yaml
mcp_servers:
  jev:
    command: "uvx"                      # 或 npx，取决于服务器实现
    args: ["<jev-mcp-server-package>"]  # ⚠️ 包名需到对应仓库核对
    env:
      TYPESAFE_API_KEY: "***"
    tools:
      include: [jev_classify, jev_score, jev_check, jev_ask]
      resources: false
      prompts: false
    trust: untrusted                    # 外部服务器建议标为 untrusted
```

### 2. 重载

```
/reload-mcp
```

### 3. 验证

问 Hermes："现在有哪些可用的工具？"
或直接指定调用：`调用 mcp_jev_jev_classify ...`

Hermes 会按 `mcp_<server>_<tool>` 规则注册，即 `mcp_jev_jev_classify`、`mcp_jev_jev_ask` 等。

### 4. 使用

主模型（真正会写字的那个，如 DeepSeek / GPT）在需要判断时调用这些工具，例如：
- 判断某条工单是否紧急 → `jev_check`
- 给 agent 输出打分 → `jev_score`
- 路由到合适的 subagent → `jev_classify`
- 一次问多个判断 → `jev_ask`

## MCP server 暴露的工具

| 工具 | 用途 |
|------|------|
| `jev_classify` | 分类 |
| `jev_score` | 打分 |
| `jev_check` | 校验 / 是非判断 |
| `jev_ask` | 批量提问（一次多问，最省成本） |

并内置 confidence 门控：动作取值 `act` / `review` / `abstain`，判定取值 `yes` / `no` / `uncertain`。

## 为什么值得这么做

按 [[system-one-models]] 的判据，适合的决策需满足：**重复、高频、可能答案调用前已知**。
Hermes 日常运行里大量判断正属于此类（工具路由、输出校验、升级决策），而 Jev 在这些任务上比前沿模型快 20–200x、便宜 40–400x。

用主模型做二元判断是在为"生成能力"付钱，而 Jev 恰好把那部分**去掉了**。

## 注意事项

1. **MCP server 包名未确认** —— 搜到的是社区实现，官方 TypeSafe 主要提供 HTTP API + Python/JS SDK。装之前核对准确包名与启动命令
2. **`noul` 无 confidence 字段** —— 写通用包装代码时要做分支
3. **问题必须原子化** —— 一个 prompt 塞多个判断会掉准确率
4. **善用并行** —— 一次问 4–14 个问题，时间几乎不增
5. **Jev 不解释理由** —— 只给概率和置信度，别指望它说明原因

## 相关

- [[jev]] —— 决策模型本体
- [[hermes-agent]] —— 宿主运行时
- [[mcp-integration]] —— 桥接协议与配置细节
- [[system-one-models]] —— 适用判据
