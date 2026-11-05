import unittest
from types import SimpleNamespace

from agents import OpenAIResponsesModel
from agents.handoffs import handoff
from agent_setup import AGENT_DISPLAY_NAMES, build_agent, build_routing_agent


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

    def test_routing_agent_has_two_specialists(self) -> None:
        routing_agent = build_routing_agent(self._settings())
        specialists = {agent.name: agent for agent in routing_agent.handoffs}

        self.assertEqual(routing_agent.name, "routing_agent")
        self.assertEqual(routing_agent.tools, [])
        self.assertEqual(
            set(specialists),
            {"calculation_agent", "life_agent"},
        )

    def test_routing_specialists_have_separate_tools(self) -> None:
        routing_agent = build_routing_agent(self._settings())
        specialists = {agent.name: agent for agent in routing_agent.handoffs}

        calculation_tools = {
            tool.name for tool in specialists["calculation_agent"].tools
        }
        life_tools = {tool.name for tool in specialists["life_agent"].tools}

        self.assertEqual(calculation_tools, {"calculator"})
        self.assertEqual(life_tools, {"get_weather", "save_note"})

    def test_routing_agents_share_selected_model(self) -> None:
        routing_agent = build_routing_agent(self._settings())

        self.assertEqual(routing_agent.model.model, "deepseek-flash")
        for specialist in routing_agent.handoffs:
            self.assertIs(specialist.model, routing_agent.model)

    def test_guardrails_are_attached_to_the_correct_agents(self) -> None:
        routing_agent = build_routing_agent(self._settings())

        self.assertEqual(
            [guardrail.get_name() for guardrail in routing_agent.input_guardrails],
            ["block_exposed_secrets"],
        )
        self.assertFalse(routing_agent.input_guardrails[0].run_in_parallel)

        all_agents = [routing_agent, *routing_agent.handoffs]
        for agent in all_agents:
            self.assertEqual(
                [guardrail.get_name() for guardrail in agent.output_guardrails],
                ["block_secret_output"],
            )

    def test_internal_names_have_chinese_display_names(self) -> None:
        self.assertEqual(
            AGENT_DISPLAY_NAMES,
            {
                "routing_agent": "分流助手",
                "calculation_agent": "计算助手",
                "life_agent": "生活助手",
            },
        )

    def test_handoff_tool_names_are_valid_and_unique(self) -> None:
        routing_agent = build_routing_agent(self._settings())
        handoff_tool_names = [
            handoff(agent).tool_name for agent in routing_agent.handoffs
        ]

        self.assertEqual(
            handoff_tool_names,
            [
                "transfer_to_calculation_agent",
                "transfer_to_life_agent",
            ],
        )
        self.assertEqual(len(handoff_tool_names), len(set(handoff_tool_names)))


if __name__ == "__main__":
    unittest.main()
