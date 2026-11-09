"""从零实现 ReAct：Thought -> Action -> Observation 循环。"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from contracts import LLMClient
from tools import ToolExecutor


REACT_PROMPT = """
你是一个会使用工具解决问题的中文助手。

可用工具：
{tools}

每轮只能输出以下两个字段：
Thought: 一句简短的决策说明，不要展开冗长推理
Action: ToolName[参数]

获得足够信息后，必须输出：
Thought: 一句简短总结
Action: Finish[给用户的最终答案]

用户问题：{question}

此前轨迹：
{history}
""".strip()


@dataclass(frozen=True)
class ReActStep:
    thought: str
    action: str
    observation: str


@dataclass(frozen=True)
class ReActResult:
    completed: bool
    final_answer: str | None
    stop_reason: str
    steps: list[ReActStep] = field(default_factory=list)


def parse_react_output(text: str) -> tuple[str, str]:
    """解析模型协议；模型文本始终是不可信输入。"""

    match = re.fullmatch(
        r"\s*Thought:\s*(.*?)\s*\nAction:\s*(.*?)\s*",
        text,
        flags=re.DOTALL,
    )
    if match is None:
        raise ValueError("模型输出不符合 Thought/Action 格式。")
    thought, action = (part.strip() for part in match.groups())
    if not thought or not action:
        raise ValueError("Thought 和 Action 都不能为空。")
    return thought, action


def parse_action(action: str) -> tuple[str, str]:
    match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\[(.*)\]", action, re.DOTALL)
    if match is None:
        raise ValueError("Action 必须是 ToolName[参数]。")
    return match.group(1), match.group(2).strip()


class ReActAgent:
    def __init__(
        self,
        llm: LLMClient,
        tools: ToolExecutor,
        *,
        max_steps: int = 5,
        verbose: bool = True,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps 必须至少为 1。")
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.verbose = verbose

    def run(self, question: str) -> ReActResult:
        history: list[str] = []
        steps: list[ReActStep] = []

        for index in range(1, self.max_steps + 1):
            prompt = REACT_PROMPT.format(
                tools=self.tools.descriptions(),
                question=question,
                history="\n".join(history) if history else "（暂无）",
            )
            raw_output = self.llm.complete([{"role": "user", "content": prompt}])

            try:
                thought, action = parse_react_output(raw_output)
                name, tool_input = parse_action(action)
            except ValueError as exc:
                # 不直接崩溃：把格式错误作为环境反馈，允许模型下一轮纠正。
                observation = f"Error: {exc} 原始输出：{raw_output}"
                step = ReActStep("输出解析失败", raw_output, observation)
                steps.append(step)
                history.extend([f"Action: {raw_output}", f"Observation: {observation}"])
                self._print_step(index, step)
                continue

            if name == "Finish":
                if not tool_input:
                    observation = "Error: Finish 中的最终答案不能为空。"
                    step = ReActStep(thought, action, observation)
                    steps.append(step)
                    history.extend([f"Action: {action}", f"Observation: {observation}"])
                    self._print_step(index, step)
                    continue
                step = ReActStep(thought, action, "任务结束")
                steps.append(step)
                self._print_step(index, step)
                return ReActResult(True, tool_input, "finished", steps)

            observation = self.tools.execute(name, tool_input)
            step = ReActStep(thought, action, observation)
            steps.append(step)
            history.extend([f"Action: {action}", f"Observation: {observation}"])
            self._print_step(index, step)

        return ReActResult(False, None, "max_steps", steps)

    def _print_step(self, index: int, step: ReActStep) -> None:
        if not self.verbose:
            return
        print(f"\n--- ReAct 第 {index} 步 ---")
        print(f"Thought: {step.thought}")
        print(f"Action: {step.action}")
        print(f"Observation: {step.observation}")
