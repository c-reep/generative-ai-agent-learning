"""Manager Pattern 入口：总控 Agent 把专业 Agent 当作工具调用。"""

import asyncio

from agents import (
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
    set_tracing_disabled,
)

from agent_setup import AGENT_DISPLAY_NAMES, build_manager_agent
from app import new_session, run_with_approvals
from config import load_settings


# 当前模型请求发送给 DeepSeek，因此关闭发送到 OpenAI 平台的默认 Tracing。
set_tracing_disabled(True)


async def chat() -> None:
    settings = load_settings()
    # 与 Handoff 版不同：每轮从 Manager 开始，也由 Manager 生成最终回答。
    agent = build_manager_agent(settings)
    session = new_session()

    print(f"DeepSeek Manager Agent 已启动（模型：{settings.model}）")
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
            # 审批逻辑不因编排模式改变：嵌套专业 Agent 中的 save_note
            # 仍会暂停整条运行，得到批准后再从同一状态继续。
            result = await run_with_approvals(
                agent,
                user_input,
                session,
            )
            final_agent_name = result.last_agent.name
            display_name = AGENT_DISPLAY_NAMES.get(
                final_agent_name,
                final_agent_name,
            )
            print(f"Agent[{display_name}]：{result.final_output}")
        except InputGuardrailTripwireTriggered as exc:
            info = exc.guardrail_result.output.output_info
            print(f"输入已被安全检查阻止：{info['reason']}")
        except OutputGuardrailTripwireTriggered as exc:
            info = exc.guardrail_result.output.output_info
            print(f"回答已被安全检查阻止：{info['reason']}")
        except Exception as exc:
            # 单轮失败不会让整个终端应用直接退出。
            print(f"本轮请求失败：{type(exc).__name__}: {exc}")


def main() -> None:
    try:
        asyncio.run(chat())
    except RuntimeError as exc:
        print(f"启动失败：{exc}")


if __name__ == "__main__":
    main()
