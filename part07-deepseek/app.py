import os

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)


SYSTEM_PROMPT = (
    "你是一名耐心、准确的学习助手。"
    "回答时优先使用清晰的中文；不确定的信息要明确说明，不要编造。"
)


def create_client() -> OpenAI:
    """读取本地环境变量并创建 DeepSeek 客户端。"""
    load_dotenv()

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "缺少 DEEPSEEK_API_KEY。请先在 .env 文件中填写你的 DeepSeek API Key。"
        )

    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        timeout=30.0,
        max_retries=2,
    )


def new_history() -> list[dict[str, str]]:
    """创建一段新对话；清空对话时也调用这个函数。"""
    return [{"role": "system", "content": SYSTEM_PROMPT}]


def build_request_messages(
    history: list[dict[str, str]], user_input: str
) -> list[dict[str, str]]:
    """组合历史消息和本轮用户消息，但不修改正式 history。"""
    request_messages = history.copy()
    request_messages.append(
        {"role": "user", "content": user_input}
    )
    return request_messages


def generate_reply(
    client: OpenAI, request_messages: list[dict[str, str]]
) -> str:
    """把完整对话历史发送给 DeepSeek，并返回助手文本。"""
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-flash").strip()

    response = client.responses.create(
        model=model,
        input=request_messages,
        reasoning={"effort": "none"},
        max_output_tokens=800,
        store=False,
    )

    answer = response.output_text.strip()
    if not answer:
        raise RuntimeError("API 请求成功，但模型没有返回文本内容。")

    return answer


def main() -> None:
    client = create_client()
    history = new_history()

    print("DeepSeek 多轮聊天已启动。")
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
            print("历史已清空，但 system 消息仍然保留。\n")
            continue

        try:
            request_messages = build_request_messages(history, user_input)
            answer = generate_reply(client, request_messages)
        except AuthenticationError:
            print("认证失败：请检查 DEEPSEEK_API_KEY 是否正确。")
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

        print(f"\nAgent：{answer}\n")

        history = request_messages + [
            {"role": "assistant", "content": answer}
        ]
        print(f"[当前保存了 {len(history) - 1} 条对话消息]\n")


if __name__ == "__main__":
    main()
