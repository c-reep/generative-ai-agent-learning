"""不依赖 TODO 实现的骨架测试，应当从一开始就通过。"""

import unittest

from agents import FunctionCallAgent, SimpleAgent
from core import Agent, AgentConfig, Message
from tools import CalculatorTool, Tool


class ScaffoldTests(unittest.TestCase):
    def test_concrete_agents_inherit_common_base(self) -> None:
        self.assertTrue(issubclass(SimpleAgent, Agent))
        self.assertTrue(issubclass(FunctionCallAgent, Agent))

    def test_message_role_is_validated(self) -> None:
        message = Message(role="user", content="你好")
        self.assertEqual(message.role, "user")

    def test_calculator_is_a_tool_and_does_not_use_eval(self) -> None:
        tool = CalculatorTool()
        self.assertIsInstance(tool, Tool)
        self.assertEqual(
            tool.run({"left": 10, "right": 5, "operation": "multiply"}),
            50,
        )

    def test_agent_config_rejects_unbounded_values(self) -> None:
        config = AgentConfig(max_tool_turns=3, max_history_length=10)
        self.assertEqual(config.max_tool_turns, 3)


if __name__ == "__main__":
    unittest.main()
