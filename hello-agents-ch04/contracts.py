"""不同 Agent 范式共同依赖的最小接口。"""

from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    """只规定 Agent 需要什么，不绑定某一家模型 SDK。"""

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
    ) -> str:
        """根据消息生成一段非空文本。"""
