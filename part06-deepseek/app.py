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


def create_client() -> OpenAI:
    """读取本地配置并创建 DeepSeek 客户端。"""
    load_dotenv()

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "缺少 DEEPSEEK_API_KEY。请在 .env 文件中填写你的 DeepSeek API Key。"
        )

    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        timeout=30.0,
        max_retries=2,
    )


def generate_plan(client: OpenAI, learning_request: str) -> str:
    """根据用户需求生成当天的学习计划。"""
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-flash").strip()

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "你是一名小学教学助手。"
                    "请根据用户需求安排当天的学习任务。"
                    "不确定的信息不要编造。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"我现有的需求是：{learning_request}\n"
                    "请安排当天的学习任务。每个任务包含名称、预计花费时间和通过标准。"
                ),
            },
        ],
        reasoning={"effort": "none"},
        max_output_tokens=1000,
        temperature=1.2,
        store=False,
    )

    answer = response.output_text.strip()
    if not answer:
        raise RuntimeError("API 请求成功，但模型没有返回文本内容。")

    return answer


def main() -> None:
    learning_request = input("请输入今天的学习需求：").strip()
    if not learning_request:
        raise SystemExit("学习需求不能为空。")

    try:
        client = create_client()
        answer = generate_plan(client, learning_request)
        print("\n生成结果：\n")
        print(answer)
    except AuthenticationError:
        print("认证失败：请检查 DEEPSEEK_API_KEY 是否正确。")
    except RateLimitError:
        print("请求过于频繁或账户额度受限，请稍后重试。")
    except (APIConnectionError, APITimeoutError):
        print("无法连接 DeepSeek 服务，请检查网络后重试。")
    except APIStatusError as exc:
        print(f"DeepSeek 服务返回错误，状态码：{exc.status_code}")
    except Exception as exc:
        print(f"程序执行失败：{exc}")


if __name__ == "__main__":
    main()
