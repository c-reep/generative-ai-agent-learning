"""从零实现 Plan-and-Solve：先生成完整计划，再逐步执行。"""

from __future__ import annotations

from dataclasses import dataclass
import json

from contracts import LLMClient


PLANNER_PROMPT = """
你是任务规划器。请把问题拆成 1 至 {max_steps} 个有顺序、可独立执行的步骤。
只输出 JSON 字符串数组，不要输出 Markdown 或解释。
示例：["确认已知条件", "完成计算", "检查并总结答案"]

问题：{question}
""".strip()


EXECUTOR_PROMPT = """
你是任务执行器。只完成当前步骤，不要重新制定计划。

原始问题：{question}
完整计划：{plan}
已经完成的步骤：
{history}
当前步骤：{current_step}

请直接给出当前步骤的结果。
""".strip()


SYNTHESIS_PROMPT = """
请根据原始问题和各步骤结果，给出简洁的最终答案。
不要声称执行过记录中没有发生的操作。

原始问题：{question}
步骤结果：
{history}
""".strip()


@dataclass(frozen=True)
class StepResult:
    step: str
    output: str


@dataclass(frozen=True)
class PlanAndSolveResult:
    plan: list[str]
    step_results: list[StepResult]
    final_answer: str


def parse_plan(text: str, *, max_steps: int = 6) -> list[str]:
    """只接受受限的 JSON 数组，拒绝任意 Python 表达式。"""

    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            cleaned = "\n".join(lines[1:-1]).strip()

    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError("计划不是合法 JSON 数组。") from exc

    if not isinstance(value, list):
        raise ValueError("计划必须是 JSON 数组。")
    if not 1 <= len(value) <= max_steps:
        raise ValueError(f"计划步骤数必须在 1 到 {max_steps} 之间。")
    if any(not isinstance(step, str) or not step.strip() for step in value):
        raise ValueError("每个计划步骤都必须是非空字符串。")
    return [step.strip() for step in value]


class Planner:
    def __init__(self, llm: LLMClient, *, max_steps: int = 6) -> None:
        self.llm = llm
        self.max_steps = max_steps

    def plan(self, question: str) -> list[str]:
        prompt = PLANNER_PROMPT.format(question=question, max_steps=self.max_steps)
        output = self.llm.complete([{"role": "user", "content": prompt}])
        return parse_plan(output, max_steps=self.max_steps)


class Executor:
    def __init__(self, llm: LLMClient, *, verbose: bool = True) -> None:
        self.llm = llm
        self.verbose = verbose

    def execute(self, question: str, plan: list[str]) -> PlanAndSolveResult:
        #创建结果列表：保存已经完成的步骤及结果
        results: list[StepResult] = []

        for index, step in enumerate(plan, start=1):
            #把以前的结果交给当前步骤
            history = _format_history(results)
            #重新组装prompt
            prompt = EXECUTOR_PROMPT.format(
                question=question,
                plan=json.dumps(plan, ensure_ascii=False),
                history=history,
                current_step=step,
            )
            #获取模型输出
            output = self.llm.complete([{"role": "user", "content": prompt}])
            #绑定“步骤＋结果”
            result = StepResult(step, output)
            #加入results
            results.append(result)
            if self.verbose:
                print(f"\n--- 执行步骤 {index}/{len(plan)} ---")
                print(f"步骤：{step}")
                print(f"结果：{output}")
        #整合所有“步骤+结果”
        history = _format_history(results)
        final_answer = self.llm.complete(
            [
                {
                    "role": "user",
                    "content": SYNTHESIS_PROMPT.format(
                        question=question,
                        history=history,
                    ),
                }
            ]
        )
        return PlanAndSolveResult(plan, results, final_answer)


class PlanAndSolveAgent:
    def __init__(
        self,
        llm: LLMClient,
        *,
        max_steps: int = 6,
        verbose: bool = True,
    ) -> None:
        self.planner = Planner(llm, max_steps=max_steps)
        self.executor = Executor(llm, verbose=verbose)
        self.verbose = verbose

    def run(self, question: str) -> PlanAndSolveResult:
        plan = self.planner.plan(question)
        if self.verbose:
            print("\n--- 生成的计划 ---")
            for index, step in enumerate(plan, start=1):
                print(f"{index}. {step}")
        return self.executor.execute(question, plan)


def _format_history(results: list[StepResult]) -> str:
    if not results:
        return "（暂无）"
    return "\n".join(
        f"{index}. {item.step}\n结果：{item.output}"
        for index, item in enumerate(results, start=1)
    )
