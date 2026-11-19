"""集中管理 Agent 行为配置和模型连接配置。"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class AgentConfig(BaseModel):
    """与具体模型服务无关的 Agent 运行限制。"""

    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_history_length: int = Field(default=20, ge=2, le=200)
    max_tool_turns: int = Field(default=5, ge=1, le=20)


@dataclass(frozen=True)
class ModelSettings:
    """连接 OpenAI 兼容模型服务所需的最少配置。"""

    api_key: str
    base_url: str
    model: str
    timeout_seconds: float = 60.0


def load_model_settings() -> ModelSettings:
    """从项目内的 .env 加载模型配置，不在代码中保存密钥。"""

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

    return ModelSettings(api_key, base_url, model, timeout_seconds)
