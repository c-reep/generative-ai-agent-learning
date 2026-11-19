"""基于原生 Function Calling 的最小 Agent 循环。"""

from __future__ import annotations

import json
from typing import Any

from core.agent import Agent
from core.message import Message
from tools.registry import ToolRegistry


class FunctionCallAgent(Agent):
    """模型提出工具调用，注册表授权并执行，模型整理最终答案。"""

    def __init__(
        self,
        *args: Any,
        tool_registry: ToolRegistry,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.tool_registry = tool_registry

    @staticmethod
    def _parse_arguments(arguments_json: str) -> dict[str, Any]:
        """把模型返回的 JSON 字符串解析为 Python 参数字典。"""

        arguments = json.loads(arguments_json)
        if not isinstance(arguments, dict):
            raise TypeError("工具参数 JSON 的顶层必须是对象")
        return arguments

    def _build_messages(self, input_text: str) -> list[dict[str, Any]]:
        """把 System Prompt、正式历史和本轮输入组合成 API 消息。"""

        messages: list[dict[str, Any]] = []

        if self.system_prompt:
            messages.append(
                {"role": "system", "content": self.system_prompt}
            )

        # 正式历史保存 Message 对象；发送给 API 前转换成字典。
        messages.extend(
            message.to_dict() for message in self.get_history()
        )
        messages.append({"role": "user", "content": input_text})
        return messages

    def run(self, input_text: str) -> str:
        """执行有最大轮数限制的模型—工具—模型循环。"""

        cleaned_input_text = input_text.strip()
        if not cleaned_input_text:
            raise ValueError("输入不能为空")

        # messages 是本轮临时工作区，会在工具循环中不断增长。
        messages = self._build_messages(cleaned_input_text)

        # schemas 只是发送给模型的工具说明书列表。
        # 真正的名称到 Tool 对象映射仍保存在 ToolRegistry 内部。
        schemas = self.tool_registry.schemas()

        for _ in range(self.config.max_tool_turns):
            response = self.llm.complete_with_tools(
                messages,
                schemas,
                temperature=self.config.temperature,
            )

            # 没有工具调用，说明模型已经生成最终自然语言答案。
            if not response.tool_calls:
                if not response.content:
                    raise RuntimeError("模型没有返回最终答案")

                # 只有本轮成功完成后，才提交正式历史。
                self.add_message(
                    Message(role="user", content=cleaned_input_text)
                )
                self.add_message(
                    Message(role="assistant", content=response.content)
                )
                return response.content

            # assistant_message 已经是包含 tool_calls 的完整 API 消息字典。
            #有工具调用时，先把模型返回加入messages
            messages.append(response.assistant_message)

            for call in response.tool_calls:
                try:
                    arguments = self._parse_arguments(call.arguments_json)
                except (json.JSONDecodeError, TypeError) as exc:
                    # 参数解析失败也要作为工具结果回传，让模型有机会纠正。
                    tool_result = argument_error_result(exc)
                else:
                    # 真正的工具执行权属于 Python 注册表。
                    tool_result = self.tool_registry.execute(
                        call.name,
                        arguments,
                    )

                # tool 消息必须使用同一次调用的 call_id 绑定请求与结果。
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.call_id,
                        "content": tool_result,
                    }
                )

        # 达到上限代表本轮失败，不能把临时 messages 写入正式历史。
        raise RuntimeError("达到最大工具调用轮数，仍未获得最终答案")


def argument_error_result(exc: Exception) -> str:
    """把不可信的模型参数错误变成模型可读取的 JSON 工具结果。"""

    return json.dumps(
        {
            "ok": False,
            "error": f"工具参数解析失败：{type(exc).__name__}: {exc}",
        },
        ensure_ascii=False,
    )
