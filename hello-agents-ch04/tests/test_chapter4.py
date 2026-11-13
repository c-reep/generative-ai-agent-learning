from __future__ import annotations

import json
import unittest

from plan_and_solve import PlanAndSolveAgent, parse_plan
from react import ReActAgent, parse_action, parse_react_output
from reflection import ReflectionAgent, parse_critique
from tools import Tool, ToolExecutor, build_default_tool_executor, calculate, current_time


class FakeLLM:
    """按顺序返回预设文本，使测试完全不调用真实 API。"""

    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls: list[list[dict[str, str]]] = []

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
    ) -> str:
        self.calls.append(messages)
        if not self.responses:
            raise AssertionError("FakeLLM 没有剩余响应。")
        return self.responses.pop(0)


class ToolTests(unittest.TestCase):
    def test_calculator_handles_precedence(self) -> None:
        result = json.loads(calculate("(10+15)/5*6"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"], 30)

    def test_calculator_rejects_python_code(self) -> None:
        with self.assertRaises(ValueError):
            calculate("__import__('os').getcwd()")

    def test_executor_rejects_unknown_tool(self) -> None:
        result = json.loads(build_default_tool_executor().execute("DeleteFile", "a.txt"))
        self.assertFalse(result["ok"])
        self.assertIn("未知工具", result["error"])

    def test_duplicate_tool_name_is_rejected(self) -> None:
        executor = ToolExecutor()
        tool = Tool("Echo", "返回原文", lambda text: text)
        executor.register(tool)
        with self.assertRaises(ValueError):
            executor.register(tool)

    def test_current_time_returns_requested_timezone(self) -> None:
        result = json.loads(current_time("Asia/Shanghai"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["timezone"], "Asia/Shanghai")


class ReActTests(unittest.TestCase):
    def test_parsers(self) -> None:
        #先将输入拆分成thought & action
        thought, action = parse_react_output(
            "Thought: 需要精确计算\nAction: Calculator[(10+15)/5*6]"
        )
        #再将action拆分成tool_name&tool_input
        self.assertEqual(thought, "需要精确计算")
        self.assertEqual(parse_action(action), ("Calculator", "(10+15)/5*6"))

    def test_react_completes_tool_loop(self) -> None:
        llm = FakeLLM(
            [
                #测试工具调用
                "Thought: 使用计算工具\nAction: Calculator[(10+15)/5*6]",
                #测试finished
                "Thought: 已获得可靠结果\nAction: Finish[计算结果是 30。]",
            ]
        )
        result = ReActAgent(
            llm,
            build_default_tool_executor(),
            max_steps=3,
            verbose=False,
        ).run("计算 (10+15)/5*6")

        self.assertTrue(result.completed)
        self.assertEqual(result.final_answer, "计算结果是 30。")
        self.assertIn('"result": 30', llm.calls[1][0]["content"])

    def test_max_steps_stops_loop(self) -> None:
        llm = FakeLLM(["Thought: 继续计算\nAction: Calculator[1+1]"])
        result = ReActAgent(
            llm,
            build_default_tool_executor(),
            max_steps=1,
            verbose=False,
        ).run("计算")
        self.assertFalse(result.completed)
        self.assertEqual(result.stop_reason, "max_steps")


class PlanAndSolveTests(unittest.TestCase):
    def test_plan_parser_accepts_json_array(self) -> None:
        self.assertEqual(parse_plan('["步骤一", "步骤二"]'), ["步骤一", "步骤二"])

    def test_plan_parser_rejects_non_list(self) -> None:
        with self.assertRaises(ValueError):
            parse_plan('{"step": "错误格式"}')

    def test_full_plan_and_solve_flow(self) -> None:
        llm = FakeLLM(
            [
                '["提取数字", "完成计算"]',
                "已知周一为 15。",
                "三天分别为 15、30、25，总计 70。",
                "三天总共卖出 70 个苹果。",
            ]
        )
        result = PlanAndSolveAgent(llm, verbose=False).run("计算三天苹果销量")
        self.assertEqual(len(result.plan), 2)
        self.assertEqual(len(result.step_results), 2)
        self.assertEqual(result.final_answer, "三天总共卖出 70 个苹果。")


class ReflectionTests(unittest.TestCase):
    def test_critique_parser_validates_fields(self) -> None:
        critique = parse_critique(
            '{"needs_revision": true, "feedback": "缺少边界检查"}'
        )
        self.assertTrue(critique.needs_revision)
        self.assertEqual(critique.feedback, "缺少边界检查")

    def test_reflection_can_stop_without_revision(self) -> None:
        llm = FakeLLM(
            [
                "初稿已经满足要求。",
                '{"needs_revision": false, "feedback": ""}',
            ]
        )
        result = ReflectionAgent(llm, verbose=False).run("写一句话")
        self.assertEqual(result.revisions, 0)
        self.assertEqual(result.stopped_because, "critic_approved")

    def test_reflection_refines_and_has_iteration_limit(self) -> None:
        llm = FakeLLM(
            [
                "缺少边界处理的初稿",
                '{"needs_revision": true, "feedback": "增加边界处理"}',
                "已经增加边界处理的新版本",
            ]
        )
        result = ReflectionAgent(
            llm,
            max_iterations=1,
            verbose=False,
        ).run("编写函数")
        self.assertEqual(result.revisions, 1)
        self.assertEqual(result.final_answer, "已经增加边界处理的新版本")
        self.assertEqual(result.stopped_because, "max_iterations")


if __name__ == "__main__":
    unittest.main()
