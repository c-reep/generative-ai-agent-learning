"""终端入口：维持多轮会话，并把每一轮交给 Runner。"""

import asyncio
import json
from uuid import uuid4

from agents import (
    Agent,
    InputGuardrailTripwireTriggered,
    OutputGuardrailTripwireTriggered,
    RunResult,
    Runner,
    SQLiteSession,
    ToolApprovalItem,
    set_tracing_disabled,
)

from agent_setup import AGENT_DISPLAY_NAMES, build_routing_agent
from config import load_settings

# 当前模型请求发送给 DeepSeek，因此关闭发送到 OpenAI 平台的默认 Tracing。
set_tracing_disabled(True)


def new_session() -> SQLiteSession:
    """新 ID 表示一段全新的上下文；旧会话不会混入新会话。"""

    return SQLiteSession(f"terminal-{uuid4().hex}")


def _format_approval_arguments(arguments: str | None) -> str:
    """尽量把工具参数格式化为易读 JSON；格式异常时仍展示原文。"""

    if not arguments:
        return "（无参数）"

    try:
        parsed = json.loads(arguments)
    except (json.JSONDecodeError, TypeError):
        return arguments
    return json.dumps(parsed, ensure_ascii=False, indent=2)


def request_approval(interruption: ToolApprovalItem) -> bool:
    """向终端用户展示待执行动作；只有明确输入批准词才返回 True。"""

    tool_name = interruption.name or "未知工具"
    print("\n【需要人工审批】")
    print(f"待执行工具：{tool_name}")
    print("工具参数：")
    print(_format_approval_arguments(interruption.arguments))

    while True:
        try:
            decision = input("是否批准执行？[y/N]：").strip().lower()
        except (EOFError, KeyboardInterrupt):
            # 无法取得明确同意时一律拒绝，避免误执行带副作用的工具。
            print("\n未取得明确批准，本次操作已拒绝。")
            return False

        if decision in {"y", "yes", "是", "批准"}:
            return True
        if decision in {"", "n", "no", "否", "拒绝"}:
            return False
        print("请输入 y 批准，或输入 n/直接回车拒绝。")


async def run_with_approvals(
    agent: Agent,
    user_input: str,
    session: SQLiteSession,
) -> RunResult:
    """运行一轮 Agent，并在每个待审批工具执行前暂停给用户确认。"""

    result = await Runner.run(
        agent,
        user_input,
        session=session,
    )

    # 一次运行可能连续遇到多个待审批动作，因此不能只使用一次 if。
    while result.interruptions:
        # RunState 是当前未完成运行的快照。审批后必须恢复它，不能把审批
        # 结果当作一条新的用户消息，否则会丢失原工具调用和调用 ID。
        state = result.to_state()

        for interruption in result.interruptions:
            if request_approval(interruption):
                state.approve(interruption)
                print("操作已批准，继续执行。")
            else:
                state.reject(
                    interruption,
                    rejection_message="用户拒绝了本次工具调用。",
                )
                print("操作已拒绝，工具不会执行。")

        # 使用原 Session 恢复同一轮运行，确保暂停前后的历史保持一致。
        result = await Runner.run(
            agent,
            state,
            session=session,
        )

    return result


async def chat() -> None:
    settings = load_settings()
    # 每一轮都从分流助手开始，再由它决定是否 Handoff 给专业 Agent。
    agent = build_routing_agent(settings)
    session = new_session()

    print(f"DeepSeek Routing Agent 已启动（模型：{settings.model}）")
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
            # SDK 自动处理模型、Handoff 和普通工具；有副作用的工具则先暂停审批。
            result = await run_with_approvals(
                agent,
                user_input,
                session,
            )
            # 取得 SDK 内部的最终 Agent 名称。
            final_agent_name = result.last_agent.name
            # SDK 内部必须使用英文工具名；这里仅把终端显示映射回中文。
            display_name = AGENT_DISPLAY_NAMES.get(
                final_agent_name,
                final_agent_name,
            )
            print(f"Agent[{display_name}]：{result.final_output}")
        except InputGuardrailTripwireTriggered as exc:
            # Guardrail 用异常把控制权交还给应用；这里决定用户看到什么。
            info = exc.guardrail_result.output.output_info
            print(f"输入已被安全检查阻止：{info['reason']}")
        except OutputGuardrailTripwireTriggered as exc:
            info = exc.guardrail_result.output.output_info
            print(f"回答已被安全检查阻止：{info['reason']}")
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
