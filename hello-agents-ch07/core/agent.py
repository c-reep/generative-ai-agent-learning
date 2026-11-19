"""所有具体 Agent 都必须遵守的抽象基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .config import AgentConfig
from .llm import LLMClient
from .message import Message


class Agent(ABC):
    """集中保存共用依赖和历史，具体运行策略由子类实现。"""

    def __init__(
        self,
        name: str,
        llm: LLMClient,
        system_prompt: str | None = None,
        config: AgentConfig | None = None,
    ) -> None:
        self.name = name
        self.llm = llm
        self.system_prompt = system_prompt
        self.config = config or AgentConfig()
        self._history: list[Message] = []

    @abstractmethod
    def run(self, input_text: str) -> str:
        """处理一次用户输入；每种 Agent 范式必须实现自己的运行逻辑。"""

    def add_message(self, message: Message) -> None:
        """保存消息，并限制历史长度，避免上下文无限增长。"""

        # TODO（必须由你手写）：
        # 1. 确认 message 是 Message 对象，否则抛出 TypeError。
        # 2. 把消息加入 self._history。
        # 3. 历史超过 max_history_length 时，只保留最后 N 条。
        if not isinstance(message,Message):
            raise TypeError("message 不是 Message 对象")
        #如上，self._history存的是list[Message]
        self._history.append(message)
        max_length = self.config.max_history_length
        if len(self._history) > max_length:
            self._history = self._history[-max_length:]

    def get_history(self) -> list[Message]:
        """返回历史副本，避免调用者直接修改内部列表。"""

        # TODO（必须由你手写）：不要直接 return self._history。
        return self._history.copy()
        # 项目内参考：
        # - 返回类型是 list[Message]。
        # - 测试会对返回列表调用 clear()，并确认内部历史没有被清空。

        # 重新完成前先回答：为什么不能直接 return self._history？避免调用者直接修改内部列表


    def clear_history(self) -> None:
        """清空当前 Agent 的多轮对话历史。"""

        # TODO（必须由你手写）。
        self._history.clear()
        # 项目内参考：self._history 是 list[Message]，使用列表自身的清空能力。

        # 重新完成前先回答：list.clear() 的返回值是什么？没有返回值，原地清空列表
        # 这里是否需要 return？不需要
