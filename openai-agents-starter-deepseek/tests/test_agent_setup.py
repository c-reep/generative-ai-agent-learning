import unittest
from types import SimpleNamespace

from agents import OpenAIResponsesModel
from agent_setup import build_agent


class AgentSetupTests(unittest.TestCase):
    @staticmethod
    def _settings() -> SimpleNamespace:
        return SimpleNamespace(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model="deepseek-flash",
        )

    def test_agent_has_expected_tools(self) -> None:
        agent = build_agent(self._settings())
        tool_names = {tool.name for tool in agent.tools}

        self.assertEqual(
            tool_names,
            {"calculator", "save_note", "get_weather"},
        )

    def test_selected_model_is_kept(self) -> None:
        agent = build_agent(self._settings())

        self.assertIsInstance(agent.model, OpenAIResponsesModel)
        self.assertEqual(agent.model.model, "deepseek-flash")


if __name__ == "__main__":
    unittest.main()
