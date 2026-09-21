---
title: Hermes Agent
created: 2026-09-21
updated: 2026-09-21
type: entity
tags: [agent-runtime, mcp]
sources: [raw/articles/hermes-agent-mcp-docs.md]
---

# Hermes Agent

Nous Research 推出的**开源、自托管 AI 助手**。核心特色：长期记忆、自我学习（从经验创建 skills）、可执行终端命令、消息网关（Telegram / Discord）。配置位于 `~/.hermes/config.yaml`。

定位是个"可以长期养成的私人助理"——与 Claude Code 这类 coding agent 的差别在于**长期记忆 + 自我学习**，能积累对你的理解，而不是每次从零开始。

## 两类模型槽位

- **Main model** —— agent 思考用。每条用户消息、每个工具调用循环、每段流式响应都走它。
- **Auxiliary models** —— 卸载的小任务：上下文压缩、视觉、网页摘要、**审批评分（approval scoring）**、**MCP 工具路由（MCP tool routing）**、会话标题生成、技能搜索。

⚠️ **main model 必须能生成文本并驱动工具调用循环。** 因此不生成文本的 [[jev]] **不能**当 main model。而 approval scoring / MCP tool routing 这两类辅助槽位在语义上正契合决策模型，但官方未公开说明其支持非标准 API 接口，不建议硬塞。

**切换模型的隐藏成本**：mid-session 切换会重置 prompt cache，下一条消息按全额 input token 计费（而非缓存折扣价 ~75–90% off）。默认会话超过 100,000 tokens 时会要求确认。

## MCP 支持

Hermes 原生支持 MCP，把它当作**适配器层**："Hermes 仍然是 agent，MCP 服务器提供工具。" 工具在启动或 `/reload-mcp` 时被发现并注册。

配置块 `mcp_servers`，支持 stdio（`command`/`args`/`env`）与 HTTP（`url`/`headers`）两种模式，并有细粒度的 `include`/`exclude` 白黑名单、`trust` 层级（`full`/`untrusted`）、OAuth 2.1 PKCE 支持。

工具命名：`mcp_<server>_<tool>`。

详见 [[mcp-integration]]。

## 扩展机制：Skill vs Tool

- **Skill** —— 能力可通过指令 + shell 命令 + 现有工具实现（arXiv 搜索、git 工作流、PDF 处理）→ 写 Skill
- **Tool** —— 需要与 API 密钥端到端集成、自定义处理逻辑、二进制数据或流式传输 → 写 Tool
- 自定义工具优先走**插件（Plugin）**方式，而非改核心

## 为什么和本 wiki 相关

Hermes 是 [[jev]] 的潜在宿主之一：Jev 已有 MCP server 形态，而 Hermes 原生支持 MCP，因此二者可以通过 MCP 桥接。参见 [[jev-in-hermes]]。

## 相关

- [[jev-in-hermes]] —— Jev 接入 Hermes 的方案
- [[mcp-integration]] —— MCP 协议与配置
- [[jev]] —— 可接入的决策模型
