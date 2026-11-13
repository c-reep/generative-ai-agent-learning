"""统一运行三个经典 Agent 范式。"""

from __future__ import annotations

import argparse

from config import load_settings
from llm import LLMCallError, OpenAICompatibleLLM
from plan_and_solve import PlanAndSolveAgent
from react import ReActAgent
from reflection import ReflectionAgent
from tools import build_default_tool_executor


DEFAULT_TASKS = {
    "react": "请精确计算 (10+15)/5*6，并说明结果。",
    "plan": "我要在两天内复习 Python 异常处理并完成一个小练习，请给出并执行学习方案。",
    "reflection": "写一个 Python 函数，返回 1 到 n 之间的所有质数，并简要说明复杂度。",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hello-Agents 第四章最小实践")
    parser.add_argument(
        "mode",
        choices=("react", "plan", "reflection"),
        help="选择要运行的 Agent 范式",
    )

    parser.add_argument(
        "task",
        nargs="?",
        help="用户问题或任务；不填写时使用内置示例",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    task = (args.task or DEFAULT_TASKS[args.mode]).strip()
    if not task:
        raise SystemExit("任务不能为空。")

    try:
        llm = OpenAICompatibleLLM(load_settings())

        if args.mode == "react":
            result = ReActAgent(llm, build_default_tool_executor()).run(task)
            if result.completed:
                print(f"\n最终答案：{result.final_answer}")
            else:
                print(f"\n任务未完成，停止原因：{result.stop_reason}")

        elif args.mode == "plan":
            result = PlanAndSolveAgent(llm).run(task)
            print(f"\n最终答案：{result.final_answer}")

        else:
            result = ReflectionAgent(llm).run(task)
            print(f"\n最终答案：\n{result.final_answer}")
            print(f"\n修改次数：{result.revisions}；停止原因：{result.stopped_because}")

    except (RuntimeError, LLMCallError, ValueError) as exc:
        raise SystemExit(f"运行失败：{exc}") from exc


if __name__ == "__main__":
    main()
