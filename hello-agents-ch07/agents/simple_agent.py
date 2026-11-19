"""最基础的多轮对话 Agent。"""

from __future__ import annotations
from typing import Any
from core.agent import Agent
from core.message import Message


class SimpleAgent(Agent):
    """负责组装消息和保存历史；HTTP 请求仍由 llm.py 负责。"""

    def run(self, input_text: str) -> str:
        """只需要注意，messages 是准备发送给模型 API 的消息列表，
        而 OpenAI 兼容 API 接收的是字典，
        不是我们自己定义的 Message 对象。"""
        # TODO（必须由你手写）：
        # 1. input_text 去除首尾空白后不能为空。
        # 2. 创建 messages 列表。
        # 3. 如果有 system_prompt，加入 system 消息。
        # 4. 使用 Message.to_dict() 把历史加入 messages。
        # 5. 加入本轮 user 消息。
        # 6. 调用 self.llm.complete(..., temperature=self.config.temperature)。
        # 7. 只有模型调用成功后，才把本轮 user 和 assistant 保存进正式历史。
        # 8. 返回模型回答。
        cleaned_input_text = input_text.strip()
        if not cleaned_input_text:
            raise ValueError("输入不能为空")

        #注意这里保存的是官方api格式，不是agent框架的Message
        messages: list[dict[str, Any]] = []

        """调用开始前，维护的是messages"""
        if self.system_prompt:
            messages.append({
                "role":"system",
                "content":self.system_prompt
            })

        for msg in self.get_history():
            messages.append(msg.to_dict())

        messages.append(
            {
                "role":"user",
                "content":cleaned_input_text
            }
        )
        #整合完消息后，就可以调用complete方法了
        result = self.llm.complete(messages, temperature=self.config.temperature)
        """调用完成后，维护的是history"""
        self.add_message(
            Message(role="user", content=cleaned_input_text)
        )
        self.add_message(
            Message(role="assistant", content=result)
        )
        return result
