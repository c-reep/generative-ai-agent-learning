"""命令行入口：只负责用户交互和会话状态。"""

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)

from config import EXERCISE_COMPLETE, load_settings
from llm import create_client, new_history, run_agent_turn


def main() -> None:
    if not EXERCISE_COMPLETE:
        raise SystemExit(
            "学习任务尚未完成：请完成 tools.py 中的必做 TODO，"
            "测试通过后将 config.py 的 EXERCISE_COMPLETE 改为 True。"
        )

    try:
        settings = load_settings()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    client = create_client(settings)
    history = new_history()

    print("GenAI Starter 已启动。")
    print("工具：calculator、save_note、get_weather")
    print("命令：exit/quit 退出，clear 清空对话。\n")

    while True:
        try:
            user_input = input("你：").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n对话已结束。")
            break

        if not user_input:
            print("请输入内容。")
            continue

        command = user_input.lower()
        if command in {"exit", "quit"}:
            print("对话已结束。")
            break
        if command == "clear":
            history = new_history()
            print("历史已清空，但 System 消息仍然保留。\n")
            continue

        # 先在候选历史中运行。本轮完全成功后才覆盖正式 history，
        # 避免 API 或工具失败污染后续上下文。
        working_history = history.copy()
        working_history.append({"role": "user", "content": user_input})

        try:
            answer = run_agent_turn(client, working_history, settings)
        except AuthenticationError:
            print("认证失败：请检查 DEEPSEEK_API_KEY。")
            continue
        except RateLimitError:
            print("请求过于频繁或账户额度受限，请稍后重试。")
            continue
        except (APIConnectionError, APITimeoutError):
            print("无法连接 DeepSeek 服务，请检查网络后重试。")
            continue
        except APIStatusError as exc:
            print(f"DeepSeek 服务返回错误，状态码：{exc.status_code}")
            continue
        except Exception as exc:
            print(f"本轮请求失败：{exc}")
            continue

        history = working_history
        print(f"\nAgent：{answer}\n")


if __name__ == "__main__":
    main()
