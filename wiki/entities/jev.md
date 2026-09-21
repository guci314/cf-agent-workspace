---
title: Jev
created: 2026-09-21
updated: 2026-09-21
type: entity
tags: [decision-model]
sources: [raw/articles/typesafe-jev.md]
---

# Jev

**Jev** 是 TypeSafe AI 于 2026-09-15 发布的**首个 System One 模型**，创始人 Diogo Almeida（前 OpenAI，参与过 ChatGPT 背后的指令遵循研究）。它不是对话模型——**不生成文本**，只输出带校准概率的类型化决策。

一句话定位：**frontier-intelligence function call — unstructured state in, typed probabilistic decisions out.** ^[raw/articles/typesafe-jev.md]

## 关键特征

- **不幻觉**：输出结构预先定义，不会产生类型错误，因此结构上不可能幻觉
- **快**：端到端 70ms–500ms
- **便宜**：输入 $0.042/MTok，**输出免费**
- **校准**：每个答案附带校准概率；置信度高则准确率高
- **并行**：所有问题在单次查询中并行评估，加问题几乎不增加延迟

## 三种问题类型

按 [[system-one-models]] 的规范，Jev 只覆盖三种判断原语：

- **Choice** — 从预定义选项中选一个（≤255），返回各项概率 + confidence
- **Score** — 按有序档位打分（≤10 级），返回加权分 + 分布 + confidence
- **Noul** — 是非判断，返回为真概率。**注意没有独立 confidence 字段**

## 调用方式

- **HTTP API**：`POST`，body 为 `{model, state, questions}`，返回 `{model, answers, usage}` ^[raw/articles/typesafe-jev.md]
- **Python SDK**：`pip install typesafe-sdk`，`from typesafe_sdk import Choice, Noul, Score, TypeSafeClient`
- **框架集成**：Pydantic AI（`TypeSafeModel`）、LangChain（`TypeSafeClassifier`）、OpenRouter
- **MCP server**：社区实现，暴露 `jev_classify` / `jev_score` / `jev_check` / `jev_ask`

## 在 Hermes 中怎么用

Jev 不能当 [[hermes-agent]] 的主模型（不生成文本、无法做工具调用循环）。正确姿势是经 MCP 接入为工具，详见 [[jev-in-hermes]]。

## 适用与不适用

**适合**：agent/工具路由、文档与工单分类、升级决策、eval 打分、guardrail 校验——即决策重复、高频、选项已知的场景。

**不适合**：写代码、写摘要、解释推理过程。它**不会告诉你为什么这样判断**。

## 相关

- [[system-one-models]] — Jev 所属的模型类别
- [[hermes-agent]] — 主要集成目标运行时
- [[jev-in-hermes]] — 具体集成方案
