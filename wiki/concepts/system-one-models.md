---
title: System One Models
created: 2026-09-21
updated: 2026-09-21
type: concept
tags: [decision-model, methodology]
sources: [raw/articles/typesafe-jev-intro.md]
---

# System One Models

一类**专为快速、结构化决策**设计的模型：输入是非结构化状态，输出是可被软件直接使用的**类型化答案 + 校准概率**。由 TypeSafe AI 于 2026-09 提出并首次产品化为 [[jev]]。

名字取自 Daniel Kahneman《思考，快与慢》的 System 1 —— 快速、直觉式判断。与之相对，当前主流推理模型（o3、Claude thinking 系）都在朝 System 2（慢思考、算力换准确）狂奔。System One 模型走的是反方向。

## 与 LLM 的本质差异

- **不生成字符串** —— 放弃文本生成，换来结构化输出与并行采样。因此**不会幻觉**（输出结构预先定义，理论上不可能产生类型错误）。
- **并行而非自回归** —— 所有问题在单次查询中并行求值，而非逐 token 生成。
- **训练目标不同** —— 用 **RLCD**（Reinforcement Learning for Calibrated Decisions）而非 RLHF/RLVR。目标不是"人类偏好"，而是"认识论上诚实的概率"。
- **始终携带置信度** —— 每个输出都带校准过的 confidence。原文指出 LLM 的通病："如果模型 95% 的时候能做对任务，但不说出那 5% 的时候，就无法自动化这个任务。"

## 为什么需要它

把"判断"从昂贵的 LLM 推理中剥离出来，用更专精、更快、更便宜的模型处理，让整个 AI 系统既智能又高效。定位是 AI 系统里的**"智能 if 语句"**：

- 分类、路由、打分、抽取、分支 —— 手写规则太脆、LLM 又太贵太慢的模糊决策场景
- 大数据 map-reduce：把 PB 级数据转成特征与洞察
- 实时应用：100ms 级响应让 UX 关键路径也能用上 AI
- 验证一切：对 LLM 的 prompt / 推理轨迹 / 输出做打分、判断、护栏、越狱检测

## 性能量级（TypeSafe 公布）

- 端到端延迟 **70ms–500ms**（对照前沿 LLM 3–329 秒）
- 输入 **$0.042 / MTok**，输出**免费**
- 相比前沿模型快 20–200×，便宜 40–400×

## 三种问题原语

- **Choice** —— 从预定义选项中选一个（≤255），返回每项概率 + confidence
- **Score** —— 按有序档位打分（≤10 级），返回加权值 + 完整分布 + confidence
- **Noul** —— 是非题，返回为真的概率（**无独立 confidence 字段**）

详见 [[jev]]。

## 当前实现

[[jev]] 是第一个公开的 System One 模型。它通过 HTTP API、官方 Python/JS SDK 以及 MCP 对外提供能力，因而可以接入 [[hermes-agent]] 这类 agent 运行时。

## 相关

- [[jev]] —— 首个实现
- [[jev-in-hermes]] —— 具体集成方案
- [[hermes-agent]] —— 可承载它的运行时
