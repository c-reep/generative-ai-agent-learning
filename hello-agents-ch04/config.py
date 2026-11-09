"""集中读取模型配置，避免在业务代码中散落 API Key。"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: float = 60.0


def load_settings() -> Settings:
    """从项目内的 .env 加载配置；缺失时尽早给出明确错误。"""

    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("MODEL_API_KEY", "").strip()
    base_url = os.getenv("MODEL_BASE_URL", "").strip()
    model = os.getenv("MODEL_NAME", "").strip()
    timeout_text = os.getenv("MODEL_TIMEOUT_SECONDS", "60").strip()

    if not api_key:
        raise RuntimeError("MODEL_API_KEY 不能为空，请先把 .env.example 复制为 .env。")
    if not base_url:
        raise RuntimeError("MODEL_BASE_URL 不能为空。")
    if not model:
        raise RuntimeError("MODEL_NAME 不能为空。")

    try:
        timeout_seconds = float(timeout_text)
    except ValueError as exc:
        raise RuntimeError("MODEL_TIMEOUT_SECONDS 必须是数字。") from exc

    if timeout_seconds <= 0:
        raise RuntimeError("MODEL_TIMEOUT_SECONDS 必须大于 0。")

    return Settings(api_key, base_url, model, timeout_seconds)
