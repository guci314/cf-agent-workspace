---
title: Jev
created: 2026-09-21
updated: 2026-09-21
type: entity
tags: [decision-model]
sources: [raw/articles/typesafe-jev-intro.md]
---

# Jev

TypeSafe AI 的第一款 **System One Model**，2026-09-15 发布（early access）。作者 Diogo Almeida 曾任 OpenAI 研究员，参与 ChatGPT 背后的指令遵循研究。

它是 [[system-one-models]] 这个新模型类别的首个公开产品。核心承诺：**不生成文本，只输出带校准概率的结构化决策**——"unstructured state in, typed probabilistic decisions out"。

## 能力边界

**擅长**：分类、路由、打分、抽取、分支。

**明确不做**：
- 不写代码、不写摘要、不聊天
- **不返回推理过程**（"no reasoning back"）—— 你拿不到"为什么这么答"

原文表述："it will not write code, summaries, or tell you why it answered the way it did."

## 三种问题类型

| 类型 | 行为 | 返回 |
|---|---|---|
| `choice` | 从预定义选项选一个（≤255） | 每项概率 + confidence |
| `score` | 按有序档位打分（≤10 级） | 加权分数 + 完整分布 + confidence |
| `noul` | 回答是/否 | 为真的概率（**无 confidence 字段**） |

⚠️ **`noul` 没有独立 confidence 字段**。若写通用代码统一读 `answer.confidence`，会在二元题上崩掉。这是官方文档明确的坑。

## 调用方式

- **HTTP API** —— `POST`，body 含 `model` / `state` / `questions`
- **Python SDK** —— `pip install typesafe-sdk`（Python 3.10+），读 `TYPESAFE_API_KEY`，默认模型 `jev-latest`
- **框架集成** —— Pydantic AI（`pydantic_ai.models.typesafe.TypeSafeModel`）、LangChain（`langchain_typesafe.TypeSafeClassifier`）、OpenRouter

## 并行语义（关键特性）

**每个问题针对同一 state 并行、独立求值。** 加第 4 个或第 14 个问题几乎不改变响应时间，只多付该问题的 token，且**不会降低其他答案的质量**。所以可以投机性提问、丢弃不需要的答案。

## 官方强要求

**每个问题必须原子化（atomic）。** 一个 prompt 里塞多个判断会掉准确率。这与"如何写好评估器"的通行建议一致。

## 典型用途

- Agent / 工具路由
- 文档与工单分类
- 升级（escalation）决策
- 评估打分（rubric 结论）
- 对 agent run 做事后判定：是否需要人工复核 / 严重程度 / 失败模式

## 接入 agent 运行时

Jev 已有 MCP server 形态，可接入支持 MCP 的 agent 运行时（如 [[hermes-agent]]）。具体方案见 [[jev-in-hermes]]。

## 相关

- [[system-one-models]] —— 所属模型类别
- [[jev-in-hermes]] —— 在 Hermes 中的集成
- [[hermes-agent]] —— 宿主运行时
