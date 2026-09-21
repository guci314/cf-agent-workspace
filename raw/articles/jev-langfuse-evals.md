# Using TypeSafe's Jev for evals

> Source: https://langfuse.com/blog/2026-09-18-using-typesafes-jev-for-evals
> Author: Annabell Schäfer · Published: 2026-09-18 · Archived: 2026-09-21

## 核心描述

> "You send a state, a string or JSON, plus typed questions. You get typed answers with probabilities. It gives you no reasoning back."

Jev 比前沿模型快 20–200x、便宜 40–400x（据 TypeSafe）。

## 三种问题类型

- **Choice** —— 从你定义的一组选项中选一个（最多 255 个），返回每项概率 + confidence
- **Score** —— 按有序评分档打分（最多 10 级），返回概率加权值、完整分布 + confidence
- **Noul** —— 回答是/否，返回为真的概率。**没有独立的 confidence 字段**，所以对所有 answer 都读 `.confidence` 的代码会在二元题上崩掉

## 适用场景

- Agent 和工具路由
- 文档与工单分类
- 升级（escalation）决策
- Eval 打分（只需 rubric 判定时）

## 完整 API 请求示例（一次问三个问题）

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

## 响应示例

```json
{
  "model": "jev-1.13.0",
  "answers": {
    "needs_review": { "type": "noul", "noul": 0.88 },
    "severity": {
      "type": "score",
      "score": 1.89,
      "confidence": 0.44,
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

**解读要点：** `needs_review` = 0.88 → 排队人工审核。`severity` = 1.89，接近"交付了错误结果"。`failure_mode` 结论不明确：`missing_context` 以 0.58 领先，但 confidence 只有 0.51，因为 `wrong_approach` 紧随其后（0.24）。

## 关键特性：并行

> "Every question is evaluated in parallel and in isolation against the same state. So adding a fourth question, or a fourteenth, barely changes response time, costs only the tokens of the question itself, and cannot degrade the answers to the others."

可以投机性地多问，然后丢掉不需要的。

## 设计约束

TypeSafe 文档强调**每个问题必须原子化**（atomic），这与"如何写好 evaluator"的指导一致。
