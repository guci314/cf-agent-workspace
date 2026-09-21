# OpenAI Agents SDK

整理日期：2026-09-21

## 安装

```bash
pip install openai-agents
export OPENAI_API_KEY=sk-...
```

## 基本用法

```python
from agents import Agent, Runner

agent = Agent(name="Assistant", instructions="You are a helpful assistant")
result = Runner.run_sync(agent, "Write a haiku about recursion.")
print(result.final_output)
```

## 三种模式（均已在沙箱实测通过）

### 1. 基础 Agent

```python
agent = Agent(name="Assistant", instructions="你是一个简洁的助手")
result = await Runner.run(agent, "用一句话介绍 Agent SDK")
print(result.final_output)
```

### 2. 工具调用

```python
from agents import function_tool

@function_tool
def multiply(a: float, b: float) -> float:
    """计算两个数字的乘积。

    Args:
        a: 第一个数字
        b: 第二个数字
    """
    return a * b

agent = Agent(
    name="Calculator",
    instructions="需要算术时调用工具",
    tools=[multiply],
)
```

### 3. 多 Agent Handoff

```python
math_agent = Agent(name="MathAgent", handoff_description="处理数学问题", ...)
translate_agent = Agent(name="TranslateAgent", handoff_description="处理翻译", ...)

triage = Agent(
    name="TriageAgent",
    instructions="判断问题类型并转交，不要自己回答",
    handoffs=[math_agent, translate_agent],
)

result = await Runner.run(triage, "把'早上好'翻译成英文")
print(result.last_agent.name)   # TranslateAgent
```

## 可运行 demo

`demos/agent_sdk_demo.py` —— 三种模式打包，支持命令行选择：

```bash
python agent_sdk_demo.py basic     # 基础
python agent_sdk_demo.py tool      # 工具调用
python agent_sdk_demo.py handoff   # 多 Agent
python agent_sdk_demo.py all       # 全部
```

## 接非 OpenAI 网关的坑

1. **必须用 `OpenAIChatCompletionsModel`** —— SDK 默认走 OpenAI 的 Responses API，第三方兼容网关要用 Chat Completions 模型类

```python
from agents import OpenAIChatCompletionsModel
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=os.environ["OPENCODE_API_KEY"],
    base_url="https://opencode.ai/zen/go/v1",
    default_headers={"x-opencode-session": "..."},   # 网关要求的自定义头
)
model = OpenAIChatCompletionsModel(model="deepseek-v4.1-flash", openai_client=client)
```

2. **`max_tokens` 别设太小** —— 推理模型会消耗 reasoning tokens，设 20 会导致 `content` 为空字符串

3. **`ModelSettings` 建议显式设置** —— 控制输出长度，也能加速

4. **日志里的 `OPENAI_API_KEY is not set, skipping trace export`** —— 只是追踪导出跳过，不影响运行
