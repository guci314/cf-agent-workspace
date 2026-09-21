# TypeSafe System One Models & Jev — 原始资料

> 来源 1：https://typesafe.ai/blog/introducing-system-one-models-and-jev
>         （Diogo Almeida, founder, 2026-09-15）
> 来源 2：https://langfuse.com/blog/2026-09-18-using-typesafes-jev-for-evals
>         （Annabell Schäfer, 2026-09-18）
> 存档日期：2026-09-21

## 一、发布背景（typesafe.ai 官方博客）

作者 Diogo Almeida 曾在 OpenAI 参与构建让语言模型擅长遵循指令与人对话的方法，
"but despite the hype it became obvious to me that there was something really big
missing."

> "Models have been superhuman at chat for years, so where is all the automation?"

经过两年 stealth 研发，发布首个 **System One Model**：一类为"做出软件可直接使用的
快速结构化决策"而构建的全新前沿模型。

技术栈三件套：
- 新的模型架构
- 并行采样器（parallel sampler）
- 训练方法 **RLCD**（Reinforcement Learning for Calibrated Decisions）

## 二、官方对比表：现有 LLM vs System One + Jev

| 维度 | 现有 LLM | System One + Jev |
|---|---|---|
| 优化方法 | RLHF / RLVR | **RLCD**（校准决策强化学习） |
| 优化目标 | 人类偏好：评分者喜欢的写作与对话 | 可验证奖励；**校准决策**：在 System One 任务上给出认识论诚实的概率 |
| 输入 | 非结构化数据（文本），强调顺序消息 | 非结构化数据，强调**结构化程序状态** |
| 输出 | 字符串/生成文本；需解析+校验；有跑偏风险 | **类型安全的结构化值**；输出可能性预先定义；永不产生类型错误；所有答案附带校准概率与置信度 |
| 采样 | 顺序，逐 token 生成 | **并行**，单次查询生成全部输出 |
| 成本 | 输入 $0.20–$10/MTok；输出约为输入 5 倍 | **输入 $0.042/MTok（$42/十亿 token）；输出免费** |
| 速度 | 前沿模型端到端 3–329 秒 | **70ms–500ms**；同等前沿智能水平下快 40×–200× |
| 置信度 | 过度自信且不一致 | 每次输出都传达置信度与不确定性；**校准**：置信度越高准确率越高 |
| 适用场景 | 人在回路任务（chatbot、copilot、coding agent） | AI 工作流/智能 if 语句；大数据 map-reduce；实时应用；验证一切 |

## 三、Jev 能回答什么（langfuse 文章）

> "You send a state, a string or JSON, plus typed questions. You get typed
> answers with probabilities. It gives you no reasoning back. Useless at other
> tasks."

三种问题类型：

- **Choice** — 从你定义的一组选项中选一个，**最多 255 个**，返回每项概率 + 一个 confidence 值
- **Score** — 针对有序评分档评级，返回概率加权值、完整分布、confidence。**最多 10 级**
- **Noul** — 回答是/否，返回为真的概率。**没有独立的 confidence 字段**，因此对所有
  answer 都读 `.confidence` 的代码会在二元题上崩掉

适合的场景（决策重复、高频、**可能答案在调用前已知**）：
- Agent 与工具路由
- 文档与工单分类
- 升级（escalation）决策
- Eval 评分（只需要 rubric 判定时）

## 四、请求/响应示例（langfuse，agent run 三合一评判）

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

解读要点（原文）：`needs_review` 0.88 → 排队；`severity` 1.89，略低于"交付了错误结果"；
`failure_mode` 不确定 —— `missing_context` 以 0.58 领先，但 confidence 只有 0.51，
因为 `wrong_approach` 以 0.24 紧追，二者仅凭 trace 确实难以区分。

**关键机制：每个问题都是对同一 state 并行且隔离评估的。** 加第 4 个问题或第 14 个，
响应时间几乎不变，只付该问题本身的 token，且不会降低其他问题的答案质量。

## 五、SDK 与集成

- **官方 SDK**：Python + JavaScript，另有原始 HTTP API
- **Python**：`pip install typesafe-sdk`（需 Python 3.10+），
  从环境变量 `TYPESAFE_API_KEY` 读取凭证，默认模型 `jev-latest`
- **Pydantic AI**：`pydantic_ai.models.typesafe` 的 `TypeSafeModel` —— 输出类型的
  每个字段变成一个问题
- **LangChain**：`langchain_typesafe` 的 `TypeSafeClassifier`，
  `classifier.invoke({...})` 直接返回分类结果
- **OpenRouter**：提供 TypeSafe SDK 接入文档

## 六、文档强调的原则

> "The TypeSafe docs are insistent that each question must be atomic."

每个问题必须原子化 —— 这与"如何写好 evaluator"的指导高度一致。
