import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from app import _format_approval_arguments, request_approval, run_with_approvals
from tools import calculator, get_weather, save_note


class ApprovalConfigurationTests(unittest.TestCase):
    def test_only_side_effecting_tool_requires_approval(self) -> None:
        self.assertTrue(save_note.needs_approval)
        self.assertFalse(calculator.needs_approval)
        self.assertFalse(get_weather.needs_approval)

    def test_arguments_are_formatted_for_human_review(self) -> None:
        formatted = _format_approval_arguments('{"content":"学习 HITL"}')

        self.assertIn('"content": "学习 HITL"', formatted)

    @patch("builtins.input", return_value="")
    def test_empty_decision_is_rejected_by_default(self, _input: Mock) -> None:
        interruption = SimpleNamespace(
            name="save_note",
            arguments='{"content":"不应保存"}',
        )

        self.assertFalse(request_approval(interruption))


class ApprovalFlowTests(unittest.TestCase):
    def test_approval_resumes_the_same_state_and_session(self) -> None:
        agent = Mock(name="agent")
        session = Mock(name="session")
        interruption = SimpleNamespace(name="save_note", arguments="{}")
        state = Mock(name="state")
        interrupted_result = SimpleNamespace(
            interruptions=[interruption],
            to_state=Mock(return_value=state),
        )
        final_result = SimpleNamespace(interruptions=[], final_output="已保存")

        with (
            patch("app.Runner.run", new_callable=AsyncMock) as runner,
            patch("app.request_approval", return_value=True),
        ):
            runner.side_effect = [interrupted_result, final_result]
            result = asyncio.run(run_with_approvals(agent, "保存笔记", session))

        self.assertIs(result, final_result)
        state.approve.assert_called_once_with(interruption)
        state.reject.assert_not_called()
        self.assertEqual(runner.await_count, 2)
        runner.assert_any_await(agent, "保存笔记", session=session)
        runner.assert_any_await(agent, state, session=session)

    def test_rejection_resumes_without_approving_the_tool(self) -> None:
        agent = Mock(name="agent")
        session = Mock(name="session")
        interruption = SimpleNamespace(name="save_note", arguments="{}")
        state = Mock(name="state")
        interrupted_result = SimpleNamespace(
            interruptions=[interruption],
            to_state=Mock(return_value=state),
        )
        final_result = SimpleNamespace(interruptions=[], final_output="已取消")

        with (
            patch("app.Runner.run", new_callable=AsyncMock) as runner,
            patch("app.request_approval", return_value=False),
        ):
            runner.side_effect = [interrupted_result, final_result]
            result = asyncio.run(run_with_approvals(agent, "保存笔记", session))

        self.assertIs(result, final_result)
        state.approve.assert_not_called()
        state.reject.assert_called_once_with(
            interruption,
            rejection_message="用户拒绝了本次工具调用。",
        )


if __name__ == "__main__":
    unittest.main()
