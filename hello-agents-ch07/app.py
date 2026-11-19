"""第七章最小框架的终端入口。完成 TODO 后再运行真实模型。"""

from __future__ import annotations

import argparse

from agents import FunctionCallAgent, SimpleAgent
from core import OpenAICompatibleLLM, load_model_settings
from tools import build_default_registry


def build_agent(mode: str):
    """只在入口层决定使用哪一种 Agent，核心组件彼此保持独立。"""

    llm = OpenAICompatibleLLM(load_model_settings())
    if mode == "simple":
        return SimpleAgent(
            name="简单聊天助手",
            llm=llm,
            system_prompt="你是一个简洁、可靠的中文助手。",
        )
    return FunctionCallAgent(
        name="Function Calling 助手",
        llm=llm,
        system_prompt=(
            "你是一个简洁、可靠的中文助手。需要计算或统计文本时必须使用工具，"
            "不要伪造工具结果。"
        ),
        tool_registry=build_default_registry(),
    )


def chat(mode: str) -> None:
    agent = build_agent(mode)
    print(f"{agent.name} 已启动。输入 /new 清空历史，exit 或 quit 退出。")

    while True:
        try:
            user_input = input("\n你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("已退出。")
            break
        if user_input.lower() == "/new":
            agent.clear_history()
            print("历史已清空。")
            continue

        try:
            print(f"Agent：{agent.run(user_input)}")
        except Exception as exc:
            print(f"本轮失败：{type(exc).__name__}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hello-Agents 第七章最小框架")
    parser.add_argument(
        "mode",
        choices=["simple", "function"],
        help="simple=普通多轮对话，function=原生 Function Calling",
    )
    args = parser.parse_args()
    chat(args.mode)


if __name__ == "__main__":
    main()
