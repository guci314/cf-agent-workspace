# Index

本 wiki 的目录。每次 ingest 后更新。查询时先读本文件定位相关页面，再深入。

> 领域：AI Agents & Automation。约定详见 [[SCHEMA]]。

## Entities（实体）

- [[jev]] — TypeSafe AI 的 System One 决策模型；不生成文本，输出带校准概率的类型化决策 *(created 2026-09-21)*
- [[hermes-agent]] — Nous Research 的开源自托管 AI agent；长期记忆 + 自我学习，原生支持 MCP *(created 2026-09-21)*

## Concepts（概念）

- [[system-one-models]] — 为"软件可直接使用的快速结构化决策"而构建的一类模型；Jev 是首个公开实现 *(created 2026-09-21)*
- [[mcp-integration]] — Model Context Protocol 的集成方式；作为 agent 与外部工具之间的适配器层 *(created 2026-09-21)*
- [[llm-wiki-pattern]] — Karpathy 提出的知识库构建模式：raw / wiki / schema 三层 + Ingest/Query/Lint 三操作 *(created 2026-09-21)*

## Queries（归档的查询结果）

- [[jev-in-hermes]] — 如何在 Hermes Agent 中调用 Jev 决策模型：为什么不能当主模型、如何经 MCP 桥接 *(created 2026-09-21)*

## Sources（原始资料，`raw/articles/`）

| 源文件 | 内容 | 采集 |
|--------|------|------|
| `karpathy-llm-wiki.md` | Karpathy《LLM Wiki》原文全文（11923 字符） | 2026-09-21 |
| `typesafe-jev-intro.md` | TypeSafe 官方发布文《Introducing System One Models & Jev》 | 2026-09-21 |
| `typesafe-jev.md` | Jev 资料汇总（官方 + Langfuse + Pydantic + MCP server） | 2026-09-22 |
| `jev-langfuse-evals.md` | Langfuse《Using TypeSafe's Jev for evals》含完整 API 示例 | 2026-09-21 |
| `hermes-mcp-docs.md` | Hermes Agent MCP 配置参考 | 2026-09-21 |
| `hermes-agent-mcp.md` | Hermes Agent 使用 MCP 指南 | 2026-09-21 |
| `hermes-agent-mcp-docs.md` | Hermes Agent 文档补充 | 2026-09-21 |

## Non-wiki 内容

- `demos/agent_sdk_demo.py` — OpenAI Agents SDK 三模式 demo（基础 / 工具调用 / Handoff），已在沙箱实测通过
