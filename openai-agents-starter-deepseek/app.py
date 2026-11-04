"""终端入口：维持多轮会话，并把每一轮交给 Runner。"""

import asyncio
from uuid import uuid4

from agents import Runner, SQLiteSession, set_tracing_disabled

from agent_setup import build_agent
from config import load_settings

# 当前模型请求发送给 DeepSeek，因此关闭发送到 OpenAI 平台的默认 Tracing。
set_tracing_disabled(True)


def new_session() -> SQLiteSession:
    """新 ID 表示一段全新的上下文；旧会话不会混入新会话。"""

    return SQLiteSession(f"terminal-{uuid4().hex}")


async def chat() -> None:
    settings = load_settings()
    agent = build_agent(settings)
    session = new_session()

    print(f"DeepSeek Agent 已启动（模型：{settings.model}）")
    print("输入 /new 开始新会话，输入 /help 查看帮助，输入 exit 或 quit 退出。")

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
            session = new_session()
            print("已开始一段没有旧历史的新会话。")
            continue
        if user_input.lower() == "/help":
            print(
                "exit:退出命令\n"
                "quit:退出命令\n"
                "/new:新开启一段对话\n"
                "/help:显示帮助"
                )
            continue
        try:
            # SDK 在一次 run 内自动处理：模型调用、工具执行、结果回传和最终回答。
            result = await Runner.run(
                agent,
                user_input,
                session=session,
            )
            print(f"Agent：{result.final_output}")
        except Exception as exc:
            # 终端应用的边界保护：单轮失败不应让整个聊天程序直接退出。
            print(f"本轮请求失败：{type(exc).__name__}: {exc}")

def main() -> None:
    try:
        asyncio.run(chat())
    except RuntimeError as exc:
        print(f"启动失败：{exc}")


if __name__ == "__main__":
    main()
