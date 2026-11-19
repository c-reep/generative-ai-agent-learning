"""不调用真实模型、结果完全可重复的 FakeLLM。"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from core.llm import LLMResponse


class FakeLLM:
    def __init__(
        self,
        text_responses: list[str] | None = None,
        tool_responses: list[LLMResponse] | None = None,
    ) -> None:
        self.text_responses = list(text_responses or [])
        self.tool_responses = list(tool_responses or [])
        self.text_calls: list[list[dict[str, Any]]] = []
        self.tool_calls: list[dict[str, Any]] = []

    def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.0,
    ) -> str:
        self.text_calls.append(deepcopy(messages))
        if not self.text_responses:
            raise AssertionError("FakeLLM 没有剩余普通文本响应。")
        return self.text_responses.pop(0)

    def complete_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        *,
        temperature: float = 0.0,
    ) -> LLMResponse:
        self.tool_calls.append(
            {
                "messages": deepcopy(messages),
                "tools": deepcopy(tools),
                "temperature": temperature,
            }
        )
        if not self.tool_responses:
            raise AssertionError("FakeLLM 没有剩余 Function Calling 响应。")
        return self.tool_responses.pop(0)
