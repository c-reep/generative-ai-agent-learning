import unittest

from agents import Agent, RunContextWrapper

from guardrails_setup import block_exposed_secrets, block_secret_output


class GuardrailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = RunContextWrapper(context=None)
        self.agent = Agent(name="test_agent")

    def test_safe_input_passes(self) -> None:
        result = block_exposed_secrets.guardrail_function(
            self.context,
            self.agent,
            "计算 (10+15)/5*8",
        )

        self.assertFalse(result.tripwire_triggered)

    def test_secret_like_input_is_blocked(self) -> None:
        fake_key = "sk-" + "a" * 20
        result = block_exposed_secrets.guardrail_function(
            self.context,
            self.agent,
            f"请记住这个值：{fake_key}",
        )

        self.assertTrue(result.tripwire_triggered)
        self.assertEqual(
            result.output_info["detected_types"],
            ["secret_like_token"],
        )

    def test_message_list_input_is_checked(self) -> None:
        fake_value = "x" * 24
        messages = [
            {
                "role": "user",
                "content": f"DEEPSEEK_API_KEY={fake_value}",
            }
        ]
        result = block_exposed_secrets.guardrail_function(
            self.context,
            self.agent,
            messages,
        )

        self.assertTrue(result.tripwire_triggered)

    def test_safe_output_passes(self) -> None:
        result = block_secret_output.guardrail_function(
            self.context,
            self.agent,
            "计算结果是 40。",
        )

        self.assertFalse(result.tripwire_triggered)

    def test_secret_like_output_is_blocked(self) -> None:
        fake_key = "sk-" + "b" * 20
        result = block_secret_output.guardrail_function(
            self.context,
            self.agent,
            f"密钥是 {fake_key}",
        )

        self.assertTrue(result.tripwire_triggered)


if __name__ == "__main__":
    unittest.main()
