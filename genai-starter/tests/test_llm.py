"""测试 Agent 循环，不发送真实 API 请求。"""

import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from config import Settings
import llm


class FakeResponses:
    def __init__(self, responses):
        self.responses = list(responses)
        self.call_count = 0

    def create(self, **_kwargs):
        self.call_count += 1
        return self.responses.pop(0)


class AgentLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(api_key="test-key", max_tool_rounds=2)

    @patch.object(llm, "execute_tool_call")
    def test_runs_tool_loop_then_returns_text(self, execute_tool_call) -> None:
        function_call = SimpleNamespace(
            type="function_call",
            name="calculator",
            arguments=json.dumps({"expression": "6 * 7"}),
            call_id="call_42",
        )
        first = SimpleNamespace(output=[function_call], output_text="")
        second = SimpleNamespace(output=[], output_text="结果是 42。")
        client = SimpleNamespace(responses=FakeResponses([first, second]))
        execute_tool_call.return_value = {
            "type": "function_call_output",
            "call_id": "call_42",
            "output": '{"ok": true, "result": 42.0}',
        }
        history = llm.new_history() + [{"role": "user", "content": "6*7是多少？"}]

        answer = llm.run_agent_turn(client, history, self.settings)

        self.assertEqual(answer, "结果是 42。")
        self.assertEqual(client.responses.call_count, 2)
        execute_tool_call.assert_called_once_with(function_call)
        self.assertEqual(history[-1]["type"], "function_call_output")

    def test_stops_after_maximum_tool_rounds(self) -> None:
        calls = [
            SimpleNamespace(
                output=[
                    SimpleNamespace(
                        type="function_call",
                        name="calculator",
                        arguments='{"expression":"1+1"}',
                        call_id=f"call_{index}",
                    )
                ],
                output_text="",
            )
            for index in range(2)
        ]
        client = SimpleNamespace(responses=FakeResponses(calls))

        with patch.object(
            llm,
            "execute_tool_call",
            return_value={
                "type": "function_call_output",
                "call_id": "call_test",
                "output": "{}",
            },
        ):
            with self.assertRaisesRegex(RuntimeError, "超过限制"):
                llm.run_agent_turn(client, llm.new_history(), self.settings)


if __name__ == "__main__":
    unittest.main()
