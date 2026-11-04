"""集中管理项目路径和环境变量。"""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
NOTES_FILE = PROJECT_ROOT / "notes.txt"


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = os.getenv("MODEL_API_KEY", "").strip()
    base_url = os.getenv("MODEL_BASE_URL", "").strip()
    model = os.getenv("MODEL_NAME", "").strip()

    if not api_key:
        raise RuntimeError("MODEL_API_KEY 不能为空。")
    if not base_url:
        raise RuntimeError("MODEL_BASE_URL 不能为空。")
    if not model:
        raise RuntimeError("MODEL_NAME 不能为空。")

    return Settings(
        api_key=api_key,
        base_url=base_url,
        model=model,
    )