"""项目级 Guardrails：在输入和最终输出边界阻止疑似 API Key 泄露。"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from agents import (
    Agent,
    GuardrailFunctionOutput,
    RunContextWrapper,
    TResponseInputItem,
    input_guardrail,
    output_guardrail,
)


# 这里只记录规则名称，不把疑似密钥本身写进 output_info，避免日志二次泄露。
_SENSITIVE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "api_key_assignment",
        re.compile(
            r"\b(?:OPENAI|DEEPSEEK)_API_KEY\s*[:=]\s*['\"]?[^\s'\"]{12,}",
            re.IGNORECASE,
        ),
    ),
    (
        "secret_like_token",
        re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b", re.IGNORECASE),
    ),
)


def _collect_text(value: Any) -> Iterable[str]:
    """从字符串或 SDK 消息结构中递归提取文本，不依赖某一种消息格式。"""

    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key in ("text", "content"):
            if key in value:
                yield from _collect_text(value[key])
    elif isinstance(value, list):
        for item in value:
            yield from _collect_text(item)


def _input_to_text(input_data: str | list[TResponseInputItem]) -> str:
    """把本轮输入统一成可检查的文本。"""

    return "\n".join(_collect_text(input_data))


def _output_to_text(output: Any) -> str:
    """兼容普通字符串和 Pydantic 结构化输出。"""

    if isinstance(output, str):
        return output

    model_dump_json = getattr(output, "model_dump_json", None)
    if callable(model_dump_json):
        return model_dump_json()

    return str(output)


def find_sensitive_markers(text: str) -> list[str]:
    """返回命中的规则名称，不返回可能包含秘密的原文。"""

    return [
        name
        for name, pattern in _SENSITIVE_PATTERNS
        if pattern.search(text)
    ]


def _guardrail_output(markers: list[str], boundary: str) -> GuardrailFunctionOutput:
    """统一构造 Guardrail 结果；tripwire=True 会让 SDK 抛出阻断异常。"""

    blocked = bool(markers)
    return GuardrailFunctionOutput(
        output_info={
            "boundary": boundary,
            "blocked": blocked,
            "detected_types": markers,
            "reason": (
                "检测到疑似 API Key，已阻止继续处理。"
                if blocked
                else "未检测到疑似 API Key。"
            ),
        },
        tripwire_triggered=blocked,
    )


# False 表示先完成输入检查，再启动入口 Agent。确定性规则不需要 async。
@input_guardrail(name="block_exposed_secrets", run_in_parallel=False)
def block_exposed_secrets(
    _context: RunContextWrapper[None],
    _agent: Agent,
    input_data: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    """阻止用户把疑似 API Key 发送给模型或工具。"""

    markers = find_sensitive_markers(_input_to_text(input_data))
    return _guardrail_output(markers, boundary="input")


@output_guardrail(name="block_secret_output")
def block_secret_output(
    _context: RunContextWrapper[None],
    _agent: Agent,
    output: Any,
) -> GuardrailFunctionOutput:
    """阻止包含疑似 API Key 的最终回答离开应用。"""

    markers = find_sensitive_markers(_output_to_text(output))
    return _guardrail_output(markers, boundary="output")
