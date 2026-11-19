"""模型通信层：只负责调用 API，不管理 Agent 历史和工具循环。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from openai import OpenAI

from .config import ModelSettings


class LLMCallError(RuntimeError):
    """模型请求失败，或服务返回了无法使用的内容。"""


@dataclass(frozen=True)
class ToolCall:
    """把不同模型 SDK 的工具调用统一成框架内部格式。"""

    call_id: str
    name: str
    arguments_json: str


@dataclass(frozen=True)
class LLMResponse:
    """同时保存自然语言内容、结构化工具调用和原始 assistant 消息。"""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    assistant_message: dict[str, Any] = field(default_factory=dict)


class LLMClient(Protocol):
    """Agent 依赖的最小模型接口，测试时可替换为 FakeLLM。"""

    def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.0,
    ) -> str: ...

    def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        temperature: float = 0.0,
    ) -> LLMResponse: ...


class OpenAICompatibleLLM:
    """可连接 DeepSeek 等兼容 Chat Completions 的模型服务。"""

    def __init__(self, settings: ModelSettings):
        self.model = settings.model
        self.client = OpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
            timeout=settings.timeout_seconds,
        )

    def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.0,
    ) -> str:
        """完成一次普通文本生成。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                extra_body={"thinking": {"type": "disabled"}},
            )
        except Exception as exc:
            raise LLMCallError(f"模型请求失败：{type(exc).__name__}: {exc}") from exc

        if not response.choices:
            raise LLMCallError("模型没有返回 choices。")

        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise LLMCallError("模型返回了空内容。")
        return content.strip()

    def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """调用原生 Function Calling，并统一模型 SDK 的返回结构。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=temperature,
                extra_body={"thinking": {"type": "disabled"}},
            )
        except Exception as exc:
            raise LLMCallError(f"模型请求失败：{type(exc).__name__}: {exc}") from exc

        if not response.choices:
            raise LLMCallError("模型没有返回 choices。")

        message = response.choices[0].message
        normalized_calls = [
            ToolCall(
                call_id=call.id,
                name=call.function.name,
                arguments_json=call.function.arguments,
            )
            for call in (message.tool_calls or [])
        ]

        return LLMResponse(
            content=(message.content or "").strip(),
            tool_calls=normalized_calls,
            assistant_message=message.model_dump(exclude_none=True),
        )
