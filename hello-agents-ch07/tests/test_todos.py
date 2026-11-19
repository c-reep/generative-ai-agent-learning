"""核心能力验收测试：补全 TODO 后应全部通过。"""

from __future__ import annotations

import json
import unittest

from agents import FunctionCallAgent, SimpleAgent
from core import AgentConfig, LLMResponse, Message, ToolCall
from tests.fakes import FakeLLM
from tools import CalculatorTool, TextStatsTool, ToolRegistry, build_default_registry


class MessageTests(unittest.TestCase):
    def test_to_dict_hides_internal_metadata(self) -> None:
        message = Message(
            role="user",
            content="你好",
            metadata={"source": "test"},
        )

        self.assertEqual(message.to_dict(), {"role": "user", "content": "你好"})

    def test_tool_message_keeps_call_id(self) -> None:
        message = Message(
            role="tool",
            content='{"ok": true}',
            tool_call_id="call_1",
        )

        self.assertEqual(message.to_dict()["tool_call_id"], "call_1")


class AgentHistoryTests(unittest.TestCase):
    def test_history_is_bounded_and_returned_as_a_copy(self) -> None:
        agent = SimpleAgent(
            name="test",
            llm=FakeLLM(),
            config=AgentConfig(max_history_length=2),
        )
        agent.add_message(Message(role="user", content="一"))
        agent.add_message(Message(role="assistant", content="二"))
        agent.add_message(Message(role="user", content="三"))

        history = agent.get_history()
        self.assertEqual([item.content for item in history], ["二", "三"])
        history.clear()
        self.assertEqual(len(agent.get_history()), 2)

    def test_clear_history(self) -> None:
        agent = SimpleAgent(name="test", llm=FakeLLM())
        agent.add_message(Message(role="user", content="需要清空"))
        agent.clear_history()
        self.assertEqual(agent.get_history(), [])


class RegistryTests(unittest.TestCase):
    def test_one_registry_contains_multiple_tools(self) -> None:
        registry = build_default_registry()
        self.assertEqual(registry.list_names(), ["calculator", "text_stats"])

    def test_schema_uses_native_function_calling_format(self) -> None:
        registry = ToolRegistry()
        registry.register(CalculatorTool())
        schema = registry.schemas()[0]

        self.assertEqual(schema["type"], "function")
        self.assertEqual(schema["function"]["name"], "calculator")
        self.assertIn("parameters", schema["function"])

    def test_execute_returns_json_and_rejects_unknown_tool(self) -> None:
        registry = ToolRegistry()
        registry.register(CalculatorTool())

        success = json.loads(
            registry.execute(
                "calculator",
                {"left": 10, "right": 5, "operation": "multiply"},
            )
        )
        failure = json.loads(registry.execute("delete_file", {}))

        self.assertEqual(success, {"ok": True, "result": 50})
        self.assertFalse(failure["ok"])
        self.assertIn("未知工具", failure["error"])

    def test_duplicate_tool_name_is_rejected(self) -> None:
        registry = ToolRegistry()
        registry.register(TextStatsTool())
        with self.assertRaises(ValueError):
            registry.register(TextStatsTool())


class SimpleAgentTests(unittest.TestCase):
    def test_second_turn_receives_first_turn_history(self) -> None:
        llm = FakeLLM(text_responses=["你好，小明。", "你叫小明。"])
        agent = SimpleAgent(
            name="聊天助手",
            llm=llm,
            system_prompt="简洁回答。",
        )

        agent.run("我叫小明")
        second_answer = agent.run("我叫什么？")

        self.assertEqual(second_answer, "你叫小明。")
        second_call = llm.text_calls[1]
        self.assertIn({"role": "user", "content": "我叫小明"}, second_call)
        self.assertIn({"role": "assistant", "content": "你好，小明。"}, second_call)


class FunctionCallAgentTests(unittest.TestCase):
    def test_tool_result_returns_to_model_before_final_answer(self) -> None:
        llm = FakeLLM(
            tool_responses=[
                LLMResponse(
                    tool_calls=[
                        ToolCall(
                            call_id="call_1",
                            name="calculator",
                            arguments_json=(
                                '{"left": 10, "right": 5, '
                                '"operation": "multiply"}'
                            ),
                        )
                    ],
                    assistant_message={
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "calculator",
                                    "arguments": (
                                        '{"left": 10, "right": 5, '
                                        '"operation": "multiply"}'
                                    ),
                                },
                            }
                        ],
                    },
                ),
                LLMResponse(
                    content="计算结果是 50。",
                    assistant_message={
                        "role": "assistant",
                        "content": "计算结果是 50。",
                    },
                ),
            ]
        )
        agent = FunctionCallAgent(
            name="工具助手",
            llm=llm,
            tool_registry=build_default_registry(),
            system_prompt="需要计算时使用工具。",
        )

        answer = agent.run("计算10乘5")

        self.assertEqual(answer, "计算结果是 50。")
        second_messages = llm.tool_calls[1]["messages"]
        tool_messages = [m for m in second_messages if m["role"] == "tool"]
        self.assertEqual(tool_messages[0]["tool_call_id"], "call_1")
        self.assertEqual(json.loads(tool_messages[0]["content"])["result"], 50)

    def test_invalid_json_becomes_tool_error_instead_of_crash(self) -> None:
        llm = FakeLLM(
            tool_responses=[
                LLMResponse(
                    tool_calls=[ToolCall("call_bad", "calculator", "not-json")],
                    assistant_message={"role": "assistant", "tool_calls": []},
                ),
                LLMResponse(
                    content="工具参数格式错误，请重新提供。",
                    assistant_message={
                        "role": "assistant",
                        "content": "工具参数格式错误，请重新提供。",
                    },
                ),
            ]
        )
        agent = FunctionCallAgent(
            name="工具助手",
            llm=llm,
            tool_registry=build_default_registry(),
        )

        answer = agent.run("计算")

        self.assertIn("参数格式错误", answer)
        tool_message = llm.tool_calls[1]["messages"][-1]
        self.assertFalse(json.loads(tool_message["content"])["ok"])


if __name__ == "__main__":
    unittest.main()
