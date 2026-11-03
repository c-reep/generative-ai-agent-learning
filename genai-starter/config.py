"""集中管理项目配置。

为什么单独放在这里：
- 避免 API Key、模型名和超时设置散落在业务代码里。
- 其他模块只依赖 Settings，不直接关心环境变量从哪里来。
- 测试时可以直接构造 Settings，不必真的读取 .env。
"""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parent
NOTES_FILE = PROJECT_DIR / "notes.txt"

SYSTEM_PROMPT = (
    "你是一名耐心、准确的学习助手。"
    "当计算、保存笔记或查询当前天气能帮助用户时，使用已提供的工具。"
    "不要声称工具已经执行，除非你收到了对应的工具执行结果。"
)

# 发布开关：只有安全执行入口完成并通过测试后才允许真实 API 请求。
EXERCISE_COMPLETE = True


@dataclass(frozen=True)
class Settings:
    """程序运行所需的只读配置。"""

    api_key: str
    model: str = "deepseek-flash"
    base_url: str = "https://api.deepseek.com"
    timeout_seconds: float = 30.0
    max_retries: int = 2
    max_tool_rounds: int = 5
    max_output_tokens: int = 800


def load_settings() -> Settings:
    """从项目目录的 .env 加载配置，并尽早拒绝缺失的 API Key。"""
    load_dotenv(PROJECT_DIR / ".env")

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "缺少 DEEPSEEK_API_KEY。请复制 .env.example 为 .env 并填写 Key。"
        )

    model = os.getenv("DEEPSEEK_MODEL", "deepseek-flash").strip()
    return Settings(api_key=api_key, model=model or "deepseek-flash")
