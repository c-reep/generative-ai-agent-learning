"""ReAct 使用的白名单工具，以及统一的注册和执行入口。"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import math
import operator
import re
from typing import Callable


ToolFunction = Callable[[str], str]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    function: ToolFunction


class ToolExecutor:
    """工具白名单：模型只能提出调用，真正执行权在 Python。"""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", tool.name):
            raise ValueError("工具名只能包含英文字母、数字和下划线。")
        if tool.name in self._tools:
            raise ValueError(f"工具已经注册：{tool.name}")
        self._tools[tool.name] = tool

    def descriptions(self) -> str:
        return "\n".join(
            f"- {tool.name}: {tool.description}" for tool in self._tools.values()
        )

    def execute(self, name: str, tool_input: str) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return _result(False, error=f"未知工具：{name}")

        try:
            return tool.function(tool_input)
        except (TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
            return _result(False, error=f"工具执行失败：{exc}")
        except Exception as exc:
            # 工具属于系统边界；单个工具崩溃不应让整个 Agent 进程退出。
            return _result(False, error=f"工具内部异常：{type(exc).__name__}: {exc}")


_BINARY_OPERATORS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPERATORS: dict[type[ast.unaryop], Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def calculate(expression: str) -> str:
    """只解释允许的算术 AST 节点，绝不把模型参数交给 eval。"""

    expression = expression.strip()
    if not expression:
        raise ValueError("算式不能为空。")
    if len(expression) > 200:
        raise ValueError("算式过长。")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError("算式语法错误。") from exc

    value = _evaluate(tree.body, depth=0)
    if not math.isfinite(float(value)):
        raise OverflowError("结果不是有限数字。")
    return _result(True, expression=expression, result=value)


def _evaluate(node: ast.AST, depth: int) -> int | float:
    if depth > 12:
        raise ValueError("算式嵌套过深。")

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("算式中只能出现数字。")
        return node.value

    if isinstance(node, ast.UnaryOp):
        function = _UNARY_OPERATORS.get(type(node.op))
        if function is None:
            raise ValueError("不支持该一元运算。")
        return function(_evaluate(node.operand, depth + 1))

    if isinstance(node, ast.BinOp):
        function = _BINARY_OPERATORS.get(type(node.op))
        if function is None:
            raise ValueError("不支持该运算符。")
        left = _evaluate(node.left, depth + 1)
        right = _evaluate(node.right, depth + 1)
        if isinstance(node.op, ast.Pow) and abs(right) > 12:
            raise OverflowError("指数绝对值不能超过 12。")
        value = function(left, right)
        if not math.isfinite(float(value)) or abs(value) > 1_000_000_000_000_000:
            raise OverflowError("中间结果过大。")
        return value

    raise ValueError("算式包含变量、函数调用或其他未授权语法。")


def word_count(text: str) -> str:
    """统计非空白字符数和以空白分隔的片段数。"""

    cleaned = text.strip()
    if not cleaned:
        raise ValueError("待统计文本不能为空。")
    return _result(
        True,
        non_whitespace_characters=len(re.sub(r"\s+", "", cleaned)),
        whitespace_separated_parts=len(cleaned.split()),
    )


def current_time(timezone_name: str) -> str:
    """读取动态时间；只允许明确列出的时区，避免平台时区库差异。"""

    timezone_name = timezone_name.strip()
    if not timezone_name:
        raise ValueError("时区不能为空，可选 local、UTC 或 Asia/Shanghai。")

    allowed_zones = {
        "UTC": timezone.utc,
        "Asia/Shanghai": timezone(timedelta(hours=8), name="Asia/Shanghai"),
    }
    if timezone_name.lower() == "local":
        now = datetime.now().astimezone()
    else:
        zone = allowed_zones.get(timezone_name)
        if zone is None:
            raise ValueError("只支持 local、UTC 或 Asia/Shanghai。")
        now = datetime.now(zone)

    return _result(True, timezone=timezone_name, datetime=now.isoformat(timespec="seconds"))


def build_default_tool_executor() -> ToolExecutor:
    executor = ToolExecutor()
    executor.register(
        Tool("Calculator", "精确计算算术表达式。输入示例：(10+15)/5*6", calculate)
    )
    executor.register(
        Tool("WordCount", "统计一段文本的字符和分词片段数量。", word_count)
    )
    executor.register(
        Tool(
            "CurrentTime",
            "查询当前时间。参数可选 local、UTC 或 Asia/Shanghai。",
            current_time,
        )
    )
    return executor


def _result(ok: bool, **payload: object) -> str:
    return json.dumps({"ok": ok, **payload}, ensure_ascii=False)
