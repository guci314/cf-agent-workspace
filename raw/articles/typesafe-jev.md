# Source: TypeSafe Jev — 原始资料存档

> **存档说明**：本文件是 Jev 相关原始资料的摘录汇总，供 wiki 页面溯源使用。
> **采集日期**：2026-09-22
> **来源清单**：
> 1. TypeSafe AI 官方博客《Introducing System One Models & Jev》(2026-09-15)，作者 Diogo Almeida（创始人，前 OpenAI）
> 2. Langfuse 博客《Using TypeSafe's Jev for evals》(2026-09-18)，作者 Annabell Schäfer
> 3. Pydantic AI 文档《TypeSafe (Jev)》
> 4. LangChain 博客《Building a Harness with Jev》(2026-09-17)
> 5. MCP Market 条目「Jev」(作者 rashedInt32)

---

## 1. 定位与设计动机（来源 1）

> "Models have been superhuman at chat for years, so where is all the automation?"

> "today, TypeSafe AI is releasing our first System One Model: a new class of frontier models built to make fast, structured decisions that software can use directly."

> "Our first public model is **Jev**, available today in early access. Jev achieves similar levels of intelligence on System One tasks compared to existing LLMs, while being two orders of magnitude faster and more efficient. While Jev gives up string generation, it's optimized for structured outputs and **can't hallucinate**."

> "Think of Jev as a frontier-intelligence function call: **unstructured state in, typed probabilistic decisions out**."

## 2. 与现有 LLM 的对照（来源 1）

| 维度 | 现有 LLM | System One + Jev |
|------|----------|------------------|
| 优化方法 | RLHF / RLVR | RLCD（Reinforcement Learning for Calibrated Decisions） |
| 优化目标 | 人类偏好（写作、聊天响应） | 校准决策（认识论上诚实的概率） |
| 输入 | 非结构化数据，强调顺序消息 | 非结构化数据，强调结构化程序状态 |
| 输出 | 字符串，需解析 + 验证，有跑偏风险 | 类型安全的结构化值，模型不会类型错误 |
| 采样 | 顺序（逐 token） | 并行（单次查询生成所有输出） |
| 成本 | 输入 $0.20–$10/MTok，输出约为输入 5 倍 | 输入 $0.042/MTok，输出免费 |
| 速度 | 端到端 3–329 秒 | 70ms–500ms |
| 置信度 | 过度自信、不一致 | 每个输出都带校准置信度 |
| 典型用例 | 人在环中（聊天、copilot、coding agent） | AI 工作流 / 智能 if 语句、大数据 map-reduce、实时应用、验证 |

> "End-to-end response time is 70ms-500ms for TypeSafe. This can range from 40x-200x faster for the same levels of frontier intelligence for System One shaped queries."

> "All answers are accompanied with calibrated probabilities and confidence scores."

## 3. 三种问题类型（来源 2、4）

- **Choice** — 从你定义的一组选项中选一个，**上限 255 个**，返回每项概率 + 一个 confidence 值
- **Score** — 按有序评分档打分，**上限 10 级**，返回概率加权值 + 完整分布 + confidence 值
- **Noul** — 回答是/否，返回为真的概率。**没有独立的 confidence 字段**，所以对所有答案统一读 `.confidence` 的代码会在二元题上崩溃

## 4. HTTP API 示例（来源 2）

请求：

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

响应：

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

> "Every question is evaluated in parallel and in isolation against the same state. So adding a fourth question, or a fourteenth, barely changes response time, costs only the tokens of the question itself, and cannot degrade the answers to the others."

## 5. 使用建议（来源 2）

- Jev 适用于决策**重复、高频、且可能答案在调用前已known**的场景：
  - Agent 与工具路由
  - 文档与工单分类
  - 升级/上报决策
  - Eval 打分（只需要 rubric 判定时）
- TypeSafe 文档**坚持每个问题必须原子化（atomic）**

## 6. Python SDK（来源 3）

```bash
pip install typesafe-sdk   # 需要 Python 3.10+
export TYPESAFE_API_KEY=...
```

```python
from typesafe_sdk import Choice, Noul, NoulCriteria, Score, TypeSafeClient

client = TypeSafeClient()  # 自动读 TYPESAFE_API_KEY，默认模型 jev-latest
```

SDK 也提供 `AsyncTypeSafeClient`。从 `apiKey` / `api_key` 参数或 `TYPESAFE_API_KEY` 环境变量读取凭证。

## 7. 框架集成（来源 3、4）

- **Pydantic AI**：`pydantic_ai.models.typesafe` 的 `TypeSafeModel`；"Each field of the `output_type` becomes one question"
- **LangChain**：`langchain_typesafe` 的 `TypeSafeClassifier`，`classifier.invoke({...})` 返回分类结果而非聊天响应
- **OpenRouter**：官方文档有 TypeSafe SDK 集成指南

## 8. MCP server（来源 5）

社区 MCP server 将 Jev 暴露为类型化判断工具：

- `jev_classify` — 分类
- `jev_score` — 打分
- `jev_check` — 校验
- `jev_ask` — 批量提问（一次多问，最高效省成本）

特点：返回完整概率分布 + confidence；强制调用方拥有选项集（防止模型自造答案）；实现 confidence 门控，动作取值 `act` / `review` / `abstain`，判定取值 `yes` / `no` / `uncertain`。
