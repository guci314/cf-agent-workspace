# Jev 决策模型

整理日期：2026-09-21

**Jev** 是 TypeSafe AI 于 2026-09-15 发布的 **System One 模型**（创始人 Diogo Almeida，前 OpenAI）。

**核心特征：不生成文本，只输出带校准概率的结构化决策。**

> "frontier-intelligence function call: unstructured state in, typed probabilistic decisions out."

## 关键指标

- 响应时间 **70ms–500ms**（比前沿模型快 40–200x）
- 价格：输入 **$0.042/MTok**，**输出免费**
- 不幻觉：输出结构预先定义，不会类型错误
- 每个答案带校准置信度，置信度越高越准
- **所有问题并行评估** —— 加问题几乎不增加延迟

## 三种问题类型

- **`choice`** —— 从预定义选项选一个（上限 255），返回各项概率 + confidence
- **`score`** —— 按有序档位打分（上限 10 级），返回加权分 + 完整分布 + confidence
- **`noul`** —— 是非判断，返回为真的概率。**注意没有独立 confidence 字段**

## HTTP API

```json
POST
{
  "model": "jev-latest",
  "state": { "task": "...", "final_output": "..." },
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
        "Delivered a wrong or incomplete result",
        "Took a destructive or unsafe action"
      ]
    }
  }
}
```

返回：

```json
{
  "answers": {
    "needs_review": { "type": "noul", "noul": 0.88 },
    "severity": {
      "type": "score", "score": 1.89, "confidence": 0.44,
      "probabilities": { "0": 0.02, "1": 0.63, "2": 0.14 }
    }
  },
  "usage": { "input_tokens": 1840, "output_tokens": 27 }
}
```

## Python SDK

```bash
pip install typesafe-sdk       # Python 3.10+
export TYPESAFE_API_KEY=...
```

```python
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

client = TypeSafeClient()      # 默认模型 jev-latest

resp = client.ask(
    state={"message": "..."},
    questions={
        "is_urgent": Noul(instructions="消息是否传达紧急性？"),
        "tone": Choice(instructions="情绪", criteria={"angry": "愤怒", "neutral": "中性"}),
        "priority": Score(instructions="优先级", criteria=["低", "中", "高"]),
    },
)
print(resp.answers["is_urgent"].noul)
```

其他集成：Pydantic AI（`TypeSafeModel`）、LangChain（`TypeSafeClassifier`）、OpenRouter。

## 适用 / 不适用

**适合**：agent 与工具路由、文档与工单分类、升级决策、eval 打分、guardrail 校验。
判据是**决策重复、高频、可能答案在调用前已知**。

**不适合**：写代码、写摘要、解释理由。它**不会告诉你为什么这样判断**。

## 注意事项

- `noul` 没有 confidence 字段，通用包装代码要分支处理
- 每个问题必须**原子化**，一个 prompt 塞多个判断会掉准确率
- 善用并行：一次问 4–14 个问题，时间几乎不增

## 在 Hermes 中怎么用

**⚠️ Jev 不能当主模型。** Hermes 的 main model 必须生成文本并驱动工具调用循环，而 Jev 不具备字符串生成能力。

**✅ 正确做法：经 MCP 接入为工具。**

```yaml
mcp_servers:
  jev:
    command: "uvx"                      # 或 npx
    args: ["<jev-mcp-server-package>"]  # 包名需到仓库核对
    env:
      TYPESAFE_API_KEY: "***"
    tools:
      include: [jev_classify, jev_score, jev_check, jev_ask]
      resources: false
      prompts: false
    trust: untrusted
```

然后 `/reload-mcp`，工具以 `mcp_jev_jev_classify` 形式注册，主模型即可调用。

MCP server 暴露的工具：

- `jev_classify` — 分类
- `jev_score` — 打分
- `jev_check` — 校验 / 是非判断
- `jev_ask` — 批量提问（一次多问，最省）

内置 confidence 门控：动作 `act` / `review` / `abstain`，判定 `yes` / `no` / `uncertain`。
