"""
OpenAI Agents SDK Demo — 接入 OpenCode 网关
环境：Python 3.13 / openai-agents 0.22.3
用法：python agent_sdk_demo.py [basic|tool|handoff|all]

注意：本文件通过 os.environ 读取 API key，不包含任何真实密钥。
"""
import os
import sys
import asyncio

from agents import (
    Agent, Runner, ModelSettings,
    OpenAIChatCompletionsModel, function_tool,
)
from openai import AsyncOpenAI

# ---------- 1. 后端：OpenCode 网关（OpenAI 兼容） ----------
client = AsyncOpenAI(
    api_key=os.environ["OPENCODE_API_KEY"],
    base_url="https://opencode.ai/zen/go/v1",
    default_headers={"x-opencode-session": "agent-sdk-demo"},  # 必需，否则 400
)
model = OpenAIChatCompletionsModel(model="deepseek-v4.1-flash", openai_client=client)
ms = ModelSettings(max_tokens=300)


# ---------- 2. 自定义工具 ----------
@function_tool
def multiply(a: float, b: float) -> float:
    """计算两个数字的乘积。

    Args:
        a: 第一个数字
        b: 第二个数字
    """
    return a * b


# ---------- 3. Demo A：基础 Agent ----------
async def demo_basic():
    agent = Agent(
        name="Assistant",
        instructions="你是一个简洁的助手，回答最多一句话。",
        model=model,
        model_settings=ms,
    )
    result = await Runner.run(agent, "用一句话介绍什么是 Agent SDK。")
    print("[A] 基础 Agent:", result.final_output)


# ---------- 4. Demo B：带工具的 Agent ----------
async def demo_tool():
    agent = Agent(
        name="Calculator",
        instructions="需要算术时调用工具，最后用一句话给出结果。",
        model=model,
        model_settings=ms,
        tools=[multiply],
    )
    result = await Runner.run(agent, "请用工具计算 23 乘以 17 等于多少？")
    print("[B] 工具调用:", result.final_output)


# ---------- 5. Demo C：多 Agent 协作（Handoff） ----------
async def demo_handoff():
    math_agent = Agent(
        name="MathAgent",
        handoff_description="处理数学计算问题",
        instructions="你是数学专家，简洁回答。",
        model=model,
        model_settings=ms,
    )
    translate_agent = Agent(
        name="TranslateAgent",
        handoff_description="处理中英翻译问题",
        instructions="你是翻译专家，简洁回答。",
        model=model,
        model_settings=ms,
    )
    triage = Agent(
        name="TriageAgent",
        instructions="你是分诊助手，判断问题类型并转交给对应专家，不要自己回答。",
        model=model,
        model_settings=ms,
        handoffs=[math_agent, translate_agent],
    )
    result = await Runner.run(triage, "帮我把\u201c早上好\u201d翻译成英文")
    print("[C] 转交给:", result.last_agent.name, "| 输出:", result.final_output)


# ---------- 6. 入口 ----------
DEMOS = {
    "basic": demo_basic,
    "tool": demo_tool,
    "handoff": demo_handoff,
}


async def main(choice: str):
    if choice == "all":
        for name, fn in DEMOS.items():
            await fn()
    elif choice in DEMOS:
        await DEMOS[choice]()
    else:
        print(f"未知选项 {choice!r}，可选: {', '.join(DEMOS)} 或 all")
        sys.exit(1)


if __name__ == "__main__":
    choice = sys.argv[1] if len(sys.argv) > 1 else "all"
    asyncio.run(main(choice))
