"""框架内部统一的消息对象。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


MessageRole = Literal["system", "user", "assistant", "tool"]


class Message(BaseModel):
    """对内保存扩展信息，对外可转换为模型 API 需要的字典。"""

    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)
    tool_call_id: str | None = None

    def to_dict(self) -> dict[str, str]:
        """转换为模型 API 消息；时间和 metadata 不应该发送给模型。"""

        # TODO（必须由你手写）：
        # 1. 返回至少包含 role 和 content 的新字典。
        # 2. 只有 tool_call_id 不为 None 时才把它加入字典。
        # 3. 不要返回 timestamp 和 metadata。
        message_to_dict:dict[str, str]={
            "role":self.role,
            "content":self.content
        }
        if self.tool_call_id is not None:
            message_to_dict["tool_call_id"] = self.tool_call_id
        return message_to_dict
        # 项目内参考：
        # - 本方法的返回类型已经写在函数签名中。
        # - 可发送的字段来自上方 Message 类定义。
        # - 预期结果见 tests/test_todos.py 的 MessageTests。

        # 重新完成前先回答：
        # - dict[str, str] 是类型，还是运行时对象？类型
        # - 真正创建字典应该使用什么符号？{}
        # - 这里的 self 指向哪个 Message 实例？
