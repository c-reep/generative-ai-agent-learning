"""对 OpenAI 兼容的 Chat Completions 接口做一层很薄的封装。"""

from __future__ import annotations

from openai import OpenAI

from config import Settings


class LLMCallError(RuntimeError):
    """模型请求失败，或服务返回了无法使用的内容。"""


class OpenAICompatibleLLM:
    """可连接 DeepSeek 等兼容 OpenAI 接口的模型服务。"""

    def __init__(self, settings: Settings):
        self.model = settings.model
        self.client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.timeout_seconds,
        )

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
    ) -> str:
        """调用模型并保证返回非空字符串。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )
        except Exception as exc:
            raise LLMCallError(f"模型请求失败：{type(exc).__name__}: {exc}") from exc

        if not response.choices:
            raise LLMCallError("模型没有返回 choices。")

        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise LLMCallError("模型返回了空内容。")
        return content.strip()
