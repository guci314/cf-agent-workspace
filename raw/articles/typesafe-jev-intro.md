# Introducing System One Models & Jev

> Source: https://typesafe.ai/blog/introducing-system-one-models-and-jev
> Author: Diogo Almeida (founder, TypeSafe AI) · Published: 2026-09-15 · Archived: 2026-09-21

## 核心定位

TypeSafe AI 发布首个 **System One Model**：一类新的前沿模型，专为**软件可直接使用的快速结构化决策**而构建。

> "Think of Jev as a frontier-intelligence function call: unstructured state in, typed probabilistic decisions out."

技术栈：新模型架构 + parallel sampler（并行采样器）+ 训练方法 **RLCD（Reinforcement Learning for Calibrated Decisions）**。

Jev 放弃了字符串生成能力，换来的是：为结构化输出优化、**无法产生幻觉**。

## LLM vs System One + Jev 对比（原文表格）

| 维度 | 现有 LLM | System One + Jev |
|------|---------|------------------|
| 优化方法 | RLHF / RLVR | RLCD |
| 优化目标 | 人类偏好（人们更喜欢的文字和对话） | 可验证奖励；**校准决策**（对 System One 任务给出认识论上诚实的概率） |
| 输入 | 非结构化数据（文本），强调顺序消息 | 非结构化数据，强调**结构化程序状态** |
| 输出 | 字符串/生成文本。灵活但需解析+校验，有跑偏风险 | **类型安全的结构化值**。可能输出预定义，不会类型错误，全部附校准概率和置信度 |
| 采样 | 顺序生成，逐 token | **并行**，单次查询生成全部输出 |
| 成本 | 输入 $0.20-$10/MTok；输出约为输入的 5 倍 | 输入 **$0.042/MTok**；输出**免费** |
| 速度 | 端到端 3-329 秒 | 端到端 **70ms-500ms** |
| 置信度 | 即使被要求也常过度自信、不一致 | 每次输出都带置信度与不确定性，**已校准** |
| 适用场景 | 人类在环任务（聊天机器人、copilot、coding agent） | AI 驱动工作流/**智能 if 语句**、大数据 map-reduce、实时应用、验证一切 |

## 关于"无类型错误"

> "No type errors: This would be an easy thing to falsify with just a single counter-example, but it is mathematically impossible."

## 主要用途（原文）

- AI-Powered Workflows / smart if-statements —— 结构化输出像模糊决策规则一样嵌入普通软件：分类、路由、打分、抽取、分支
- Map-reducing over big data —— 把 PB 级数据转成特征与洞察
- Real-time applications —— 100ms 速度让 AI 可用于 UX 敏感的实时场景
- Verify everything —— 打分、评判、验证、护栏、检测越狱

## 关于定价的诚实说明

> "Cost per call: We make our pricing transparent. We can't prove it isn't subsidized; we'll need the long-term to prove the sustainability of our pricing (which we expect to go down, not up)."
