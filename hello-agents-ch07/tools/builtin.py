"""用于练习注册表和 Function Calling 的无网络工具。"""

from __future__ import annotations

import operator
import re
from typing import Any, Callable

from .base import Tool
from .registry import ToolRegistry


class CalculatorTool(Tool):
    """通过白名单运算符计算两个数字，不使用 eval。"""

    _OPERATIONS: dict[str, Callable[[float, float], float]] = {
        "add": operator.add,
        "subtract": operator.sub,
        "multiply": operator.mul,
        "divide": operator.truediv,
    }

    def __init__(self) -> None:
        super().__init__(
            name="calculator",
            description="对两个数字进行加、减、乘或除运算。",
            parameters={
                "type": "object",
                "properties": {
                    "left": {"type": "number", "description": "左操作数"},
                    "right": {"type": "number", "description": "右操作数"},
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract", "multiply", "divide"],
                    },
                },
                "required": ["left", "right", "operation"],
                "additionalProperties": False,
            },
        )

    def run(self, arguments: dict[str, Any]) -> int | float:
        expected = {"left", "right", "operation"}
        actual = set(arguments)
        if actual != expected:
            raise ValueError(
                f"参数必须恰好是 {sorted(expected)}，实际为 {sorted(actual)}。"
            )

        left = arguments["left"]
        right = arguments["right"]
        operation_name = arguments["operation"]
        if isinstance(left, bool) or not isinstance(left, (int, float)):
            raise TypeError("left 必须是数字。")
        if isinstance(right, bool) or not isinstance(right, (int, float)):
            raise TypeError("right 必须是数字。")

        operation = self._OPERATIONS.get(operation_name)
        if operation is None:
            raise ValueError(f"不支持的运算：{operation_name}")
        return operation(left, right)


class TextStatsTool(Tool):
    """统计文本长度，展示同一注册表可以保存多个工具。"""

    def __init__(self) -> None:
        super().__init__(
            name="text_stats",
            description="统计一段文本的非空白字符数和空白分隔片段数。",
            parameters={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "待统计文本"}
                },
                "required": ["text"],
                "additionalProperties": False,
            },
        )

    def run(self, arguments: dict[str, Any]) -> dict[str, int]:
        if set(arguments) != {"text"}:
            raise ValueError("参数必须恰好是 text。")
        text = arguments["text"]
        if not isinstance(text, str):
            raise TypeError("text 必须是字符串。")
        if not text.strip():
            raise ValueError("待统计文本不能为空。")
        return {
            "non_whitespace_characters": len(re.sub(r"\s+", "", text)),
            "whitespace_separated_parts": len(text.split()),
        }


def build_default_registry() -> ToolRegistry:
    """集中组装工具；不是每个工具都创建一个注册表。"""

    registry = ToolRegistry()

    # TODO（必须由你手写）：
    # 使用同一个 registry.register(...) 注册 CalculatorTool 和 TextStatsTool。
    #查看register方法的定义可知，传一个tool对象
    registry.register(CalculatorTool())
    registry.register(TextStatsTool())
    # 项目内参考：
    # - 两个工具类都定义在本文件中。
    # - ToolRegistry.register() 接收的是 Tool 对象，不是工具类本身。
    # - 预期顺序见 RegistryTests.test_one_registry_contains_multiple_tools。

    # 重新完成前先回答：CalculatorTool 与 CalculatorTool() 哪个是类，哪个是实例？
    return registry
