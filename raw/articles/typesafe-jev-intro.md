# TypeSafe Jev — System One Model 发布与 API 摘录

> **Sources**:
> - https://typesafe.ai/blog/introducing-system-one-models-and-jev (2026-09-15, Diogo Almeida)
> - https://langfuse.com/blog/2026-09-18-using-typesafes-jev-for-evals (2026-09-18)
> - https://pydantic.dev/docs/ai/models/typesafe/
> **Captured**: 2026-09-21
> **Layer**: raw (immutable)

## 定位

TypeSafe AI 的第一款 **System One Model**，2026-09-15 发布（early access）。
作者 Diogo Almeida 曾任 OpenAI 研究员（参与 ChatGPT 背后的指令遵循研究）。

原文定义："Jev achieves similar levels of intelligence on System One tasks compared to existing LLMs, while being two orders of magnitude faster and more efficient. While Jev gives up string generation, it's optimized for structured outputs and can't hallucinate."

一句话："a frontier-intelligence function call: unstructured state in, typed probabilistic decisions out."

## 对照表（原文）

| | 传统 LLM | System One + Jev |
|---|---|---|
| 训练优化 | RLHF / RLVR | **RLCD**（Reinforcement Learning for Calibrated Decisions）|
| 输入侧重 | 顺序消息 | 结构化程序状态 |
| 输出 | 字符串（需解析+校验） | **类型安全的结构化值**（预先定义） |
| 采样 | 顺序，逐 token | **并行**，单次查询生成全部输出 |
| 输入成本 | $0.20–$10 / MTok | **$0.042 / MTok** |
| 输出成本 | 约为输入 5 倍 | **免费**（"too cheap to meter"）|
| 端到端延迟 | 3–329 秒 | **70ms–500ms** |
| 置信度 | 过度自信、不一致 | **每次输出都带校准置信度** |
| 适用 | 人在回路任务 | 可验证问题、smart if-statements、大数据 map-reduce、实时应用 |

原文强调："There is also always some risk that the AI goes off the rails"（对 LLM）；而 Jev "never makes type errors"，且无法幻觉（结构预定义）。

## 三种问题类型（Question primitives）

- **Choice** — 从你定义的一组选项中选一个，**最多 255 个**，返回每项概率 + confidence
- **Score** — 按有序评分档打分，**最多 10 级**，返回概率加权值 + 完整分布 + confidence
- **Noul** — 回答是/否，返回为真的概率。**注意：没有独立的 confidence 字段**，代码若统一读 `.confidence` 会在二元题上出错

## HTTP API 请求示例

```json
{
  "model": "jev-latest",
  "state": { "task": "...", "tool_calls": "...", "final_output": "..." },
  "questions": {
    "needs_review": {
      "type": "noul",
      "instructions": "Does this run need a human to look at it?"
    },
    "severity": {
      "type": "score",
      "instructions": "How badly did this run go?",
      "criteria": ["Completed cleanly", "Wasteful path", "Wrong result", "Unsafe action"]
    },
    "failure_mode": {
      "type": "choice",
      "instructions": "What went wrong, if anything?",
      "criteria": {
        "tool_error": "A tool returned an error",
        "missing_context": "The agent lacked needed information",
        "wrong_approach": "Unsuitable strategy",
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
      "type": "score", "score": 1.89, "confidence": 0.44,
      "probabilities": { "0": 0.02, "1": 0.21, "2": 0.63, "3": 0.14 }
    },
    "failure_mode": {
      "type": "choice", "choice": "missing_context", "confidence": 0.51,
      "probabilities": { "tool_error": 0.11, "missing_context": 0.58, "wrong_approach": 0.24, "none": 0.02 }
    }
  },
  "usage": { "input_tokens": 1840, "output_tokens": 27 }
}
```

## 并行语义（重要）

"Every question is evaluated in parallel and in isolation against the same state." 加第 4 或第 14 个问题几乎不改变响应时间，只付该问题的 token，且不会降低其他答案质量。可以投机性提问、丢弃不需要的。

## TypeSafe 文档的强要求

- **每个问题必须原子化（atomic）**——一个 prompt 塞多个判断会掉准确率
- 三种调用面：HTTP API / 官方 Python+JS SDK / 框架集成
- Python SDK: `pip install typesafe-sdk`（Python 3.10+），读环境变量 `TYPESAFE_API_KEY`，默认模型 `jev-latest`
- 框架集成：Pydantic AI（`pydantic_ai.models.typesafe.TypeSafeModel`，输出类型的每个字段变成一个 question）、LangChain（`langchain_typesafe.TypeSafeClassifier`）、OpenRouter

## Jev 明确做不了的事

- 不写代码、不写摘要、不解释为什么这么答（"no reasoning back"）
- 弱于任何需要生成字符串的任务
