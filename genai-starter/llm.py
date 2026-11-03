"""封装 DeepSeek 客户端和“模型 ↔ 工具”的循环。"""

from typing import Any

from openai import OpenAI

from config import SYSTEM_PROMPT, Settings
from tools import TOOLS, execute_tool_call


def create_client(settings: Settings) -> OpenAI:
    """根据集中配置创建客户端，避免 app.py 知道连接细节。"""
    return OpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=settings.timeout_seconds,
        max_retries=settings.max_retries,
    )


def new_history() -> list[Any]:
    """创建新会话；clear 后仍保留系统行为约束。"""
    return [{"role": "system", "content": SYSTEM_PROMPT}]


def run_agent_turn(
    client: OpenAI,
    conversation: list[Any],
    settings: Settings,
) -> str:
    """运行一轮完整 Agent 循环，直到得到最终文本回答。"""
    for _ in range(settings.max_tool_rounds):
        response = client.responses.create(
            model=settings.model,
            input=conversation,
            tools=TOOLS,
            tool_choice="auto",
            reasoning={"effort": "none"},
            max_output_tokens=settings.max_output_tokens,
            store=False,
        )

        # 必须把模型返回的 function_call 也保存进历史，第二轮模型才能知道
        # function_call_output 对应的是哪一次调用。
        conversation.extend(response.output)
        tool_calls = [
            item for item in response.output if item.type == "function_call"
        ]

        if not tool_calls:
            answer = response.output_text.strip()
            if not answer:
                raise RuntimeError("模型既没有返回文本，也没有请求工具。")
            return answer

        for tool_call in tool_calls:
            conversation.append(execute_tool_call(tool_call))

    # 防止模型无限调用工具，消耗额度或让程序无法返回。
    raise RuntimeError("工具调用轮数超过限制，已停止本轮请求。")
