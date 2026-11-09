"""从零实现 Reflection：初稿 -> 批评 -> 修改的有限循环。"""

from __future__ import annotations

from dataclasses import dataclass, field
import json

from contracts import LLMClient


DRAFT_PROMPT = """
请完成下面的任务，先生成一个可用的初稿。
任务：{task}
""".strip()


CRITIQUE_PROMPT = """
你是严格但务实的审查者。根据任务目标检查当前答案的正确性、遗漏和可执行性。
只输出合法 JSON，不要使用 Markdown：
{{"needs_revision": true, "feedback": "需要修改的具体原因"}}
如果已经满足要求，则将 needs_revision 设为 false。

任务：{task}
当前答案：
{answer}
""".strip()


REFINE_PROMPT = """
请根据审查意见修改答案。直接输出完整的新版本，不要只描述修改过程。

任务：{task}
上一版答案：
{answer}
审查意见：
{feedback}
""".strip()


@dataclass(frozen=True)
class Critique:
    needs_revision: bool
    feedback: str


@dataclass(frozen=True)
class ReflectionResult:
    initial_draft: str
    final_answer: str
    revisions: int
    stopped_because: str
    critiques: list[Critique] = field(default_factory=list)


def parse_critique(text: str) -> Critique:
    """验证反思结果，不能只因为“看起来像 JSON”就相信它。"""

    try:
        value = json.loads(text.strip())
    except json.JSONDecodeError as exc:
        raise ValueError("审查结果不是合法 JSON。") from exc

    if not isinstance(value, dict):
        raise ValueError("审查结果必须是 JSON 对象。")
    if set(value) != {"needs_revision", "feedback"}:
        raise ValueError("审查结果字段必须恰好是 needs_revision 和 feedback。")
    if not isinstance(value["needs_revision"], bool):
        raise ValueError("needs_revision 必须是布尔值。")
    if not isinstance(value["feedback"], str):
        raise ValueError("feedback 必须是字符串。")
    feedback = value["feedback"].strip()
    if value["needs_revision"] and not feedback:
        raise ValueError("需要修改时 feedback 不能为空。")
    return Critique(value["needs_revision"], feedback)


class ReflectionAgent:
    def __init__(
        self,
        llm: LLMClient,
        *,
        max_iterations: int = 2,
        verbose: bool = True,
    ) -> None:
        if max_iterations < 1:
            raise ValueError("max_iterations 必须至少为 1。")
        self.llm = llm
        self.max_iterations = max_iterations
        self.verbose = verbose

    def run(self, task: str) -> ReflectionResult:
        initial_draft = self.llm.complete(
            [{"role": "user", "content": DRAFT_PROMPT.format(task=task)}],
            temperature=0.2,
        )
        current_answer = initial_draft
        critiques: list[Critique] = []
        revisions = 0

        if self.verbose:
            print(f"\n--- 初稿 ---\n{initial_draft}")

        for index in range(1, self.max_iterations + 1):
            critique_text = self.llm.complete(
                [
                    {
                        "role": "user",
                        "content": CRITIQUE_PROMPT.format(
                            task=task,
                            answer=current_answer,
                        ),
                    }
                ]
            )
            critique = parse_critique(critique_text)
            critiques.append(critique)

            if self.verbose:
                print(f"\n--- 第 {index} 次审查 ---")
                print(f"需要修改：{critique.needs_revision}")
                print(f"反馈：{critique.feedback or '无'}")

            if not critique.needs_revision:
                return ReflectionResult(
                    initial_draft,
                    current_answer,
                    revisions,
                    "critic_approved",
                    critiques,
                )

            current_answer = self.llm.complete(
                [
                    {
                        "role": "user",
                        "content": REFINE_PROMPT.format(
                            task=task,
                            answer=current_answer,
                            feedback=critique.feedback,
                        ),
                    }
                ],
                temperature=0.1,
            )
            revisions += 1
            if self.verbose:
                print(f"\n--- 第 {index} 次修改结果 ---\n{current_answer}")

        return ReflectionResult(
            initial_draft,
            current_answer,
            revisions,
            "max_iterations",
            critiques,
        )
