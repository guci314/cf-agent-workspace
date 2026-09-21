# TypeSafe Jev — System One Model 原始资料

> 来源：
> - https://typesafe.ai/blog/introducing-system-one-models-and-jev （官方发布博客，2026-09-15）
> - https://langfuse.com/blog/2026-09-18-using-typesafes-jev-for-evals （Langfuse 实测文，2026-09-18）
> 抓取：2026-09-21 ｜ raw 层存档

## 官方定义

> "Think of Jev as a frontier-intelligence function call: unstructured state in, typed probabilistic decisions out."

Jev 是 TypeSafe AI 发布的第一个 **System One Model**。核心取舍：**放弃字符串生成能力，换取结构化输出与速度**。

## 官方对比表（现有 LLM vs System One + Jev）

| 维度 | 现有 LLM | System One + Jev |
|------|----------|------------------|
| 优化方法 | RLHF / RLVR | RLCD（Reinforcement Learning for Calibrated Decisions） |
| 优化目标 | 人类偏好：人们喜欢的文字与对话 | 校准决策：在 System One 任务上给出认识论诚实的概率 |
| 输入 | 非结构化数据，偏重**顺序消息** | 非结构化数据，偏重**结构化程序状态** |
| 输出 | 字符串/生成文本。要被软件使用需解析+校验，且总有跑偏风险 | 类型安全的结构化值。可能输出与结构**预先定义**，模型永不产生类型错误，每个答案附带校准概率与置信度 |
| 采样 | 顺序。逐 token 生成 | 并行。单次查询生成全部输出 |
| 成本 | 输入 $0.20–$10 / MTok；输出约为输入 5 倍 | 输入 $0.042 / MTok；**输出免费** |
| 速度 | 端到端 3–329 秒 | 端到端 **70ms–500ms**（同级别前沿智能下快 40–200 倍） |
| 置信度 | 即便被要求也给不准，倾向过度自信且不一致 | 每个输出都带置信度与不确定性，且**校准过**：更高置信=更高准确率 |
| 适用场景 | 人在环任务（chatbot、copilot、coding agent） | AI 工作流 / 智能 if 语句、大数据 map-reduce、实时应用、验证与护栏 |

## 三种问题类型（Primitives）

- **Choice** — 从你定义的一组选项中选一个，最多 **255** 个，返回每项概率 + confidence
- **Score** — 按有序评分档打分，最多 **10** 级，返回概率加权分数、完整分布、confidence
- **Noul** — 回答是/否，返回为真的概率。**没有独立的 confidence 字段**（对每个 answer 都读 `.confidence` 的代码会在二元题上崩）

## HTTP API 请求示例（Langfuse 实测）

```json
{
  "model": "jev-latest",
  "state": {
    "task": "{{task}}",
    "tool_calls": "{{tool_calls}}",
    "final_output": "{{final_output}}"
  },
  "questions": {
    "needs_review": {
      "type": "noul",
      "instructions": "Does this run need a human to look at it?"
    },
    "severity": {
      "type": "score",
      "instructions": "How badly did this run go?",
      "criteria": [
        "Completed the task cleanly",
        "Completed it, but took a wasteful or confusing path",
        "Delivered a wrong or incomplete result",
        "Took a destructive or unsafe action"
      ]
    },
    "failure_mode": {
      "type": "choice",
      "instructions": "What went wrong, if anything?",
      "criteria": {
        "tool_error": "A tool returned an error or unusable output",
        "missing_context": "The agent lacked information it needed",
        "wrong_approach": "The agent chose an unsuitable strategy",
        "user_abandoned": "The user left before the task finished",
        "none": "Nothing went wrong"
      }
    }
  }
}
```

## HTTP API 响应示例

```json
{
  "model": "jev-1.13.0",
  "answers": {
    "needs_review": { "type": "noul", "noul": 0.88 },
    "severity": {
      "type": "score",
      "score": 1.89,
      "confidence": 0.44,
      "legend": {
        "0": "Completed the task cleanly",
        "1": "Completed it, but took a wasteful or confusing path",
        "2": "Delivered a wrong or incomplete result",
        "3": "Took a destructive or unsafe action"
      },
      "probabilities": { "0": 0.02, "1": 0.21, "2": 0.63, "3": 0.14 }
    },
    "failure_mode": {
      "type": "choice",
      "choice": "missing_context",
      "probabilities": {
        "tool_error": 0.11,
        "missing_context": 0.58,
        "wrong_approach": 0.24,
        "user_abandoned": 0.05,
        "none": 0.02
      },
      "confidence": 0.51
    }
  },
  "usage": { "input_tokens": 1840, "output_tokens": 27 }
}
```

**解读要点**：`needs_review` 0.88 → 排队人工；`severity` 1.89 → 逼近"交付错误结果"；`failure_mode` 结论不明确（missing_context 0.58 居首，但 wrong_approach 0.24 紧随，confidence 仅 0.51）。

## 并行评估特性

> "Every question is evaluated in parallel and in isolation against the same state."

加第 4 个或第 14 个问题，响应时间几乎不变，只多付该问题本身的 token，且不会降低其他问题的答案质量。可以"投机性提问"再丢弃不需要的。

## 官方强调：每个问题必须原子化（atomic）

TypeSafe 文档反复强调这一点，与"如何写好评估器"的指导一致。

## 定价与速度证据（官方自述）

- 输入 $0.042 / MTok（$42 per billion tokens）
- 输出免费（"too cheap to meter"）
- 端到端 70ms–500ms
- 官方承认"无法证明定价未被补贴"，需长期验证可持续性

## SDK 与集成

- Python：`pip install typesafe-sdk`（需 Python 3.10+），读 `TYPESAFE_API_KEY`，默认模型 `jev-latest`
- 核心类：`TypeSafeClient`、`AsyncTypeSafeClient`、`Choice`、`Score`、`Noul`
- JS/TS：官方 SDK
- Pydantic AI：`typesafe_sdk` + `pydantic_ai.models.typesafe.TypeSafeModel`（输出类型的每个字段变成一个 question）
- LangChain：`langchain_typesafe` 的 `TypeSafeClassifier`
- OpenRouter：提供 TypeSafe SDK 接入
- 原始 HTTP API 亦可直接调用

## 官方适用场景清单

- Agent 与工具路由
- 文档与工单分类
- 升级/上报决策
- Eval 评分（只需 rubric 判定时）
