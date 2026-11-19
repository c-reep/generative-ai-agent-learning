"""工具注册、发现、白名单授权和异常隔离。"""

from __future__ import annotations

import json
import re
from typing import Any

from .base import Tool


class ToolRegistry:
    """模型只能调用这里已经注册的工具，真正执行权属于 Python。"""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """注册一个工具，同时拒绝非法名称和重复名称。"""

        # TODO（必须由你手写）：
        # 1. tool 必须是 Tool 实例。
        # 2. 名称必须匹配 [A-Za-z_][A-Za-z0-9_]*。
        # 3. 拒绝重复注册。
        # 4. 保存到 self._tools。
        if not isinstance(tool,Tool):
            raise TypeError("tool 必须是 Tool 实例")
        if re.compile(r"[A-Za-z_][A-Za-z0-9_]*").fullmatch(tool.name) is None:
            raise ValueError("工具名称格式不合法")
        #查找键
        if tool.name in self._tools:
            raise ValueError("工具已经注册")
        #注意看上面，self._tools是dict[str, Tool]类型
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """按名称查找工具；找不到时返回 None。"""

        # TODO（必须由你手写）：从 self._tools 中按名称安全查找。
        return self._tools.get(name)
        # 项目内参考：函数返回类型允许 Tool 或 None。


    def list_names(self) -> list[str]:
        """返回注册顺序稳定的工具名称。"""

        return list(self._tools)

    def descriptions(self) -> str:
        """生成人类和 Prompt 都能阅读的工具列表。"""

        return "\n".join(
            f"- {tool.name}: {tool.description}" for tool in self._tools.values()
        )

    def schemas(self) -> list[dict[str, Any]]:
        """返回所有工具的原生 Function Calling Schema。"""
        "tool. to_schema()是为了生成工具说明书，在api调用时一起给模型"
        # TODO（必须由你手写）：对每个工具调用 to_schema()。
        tools_to_schemas: list[dict[str, Any]]=[]
        #取出值->即工具
        for tool in self._tools.values():
            tools_to_schemas.append(tool.to_schema())
        return tools_to_schemas
        # 项目内参考：
        # - self._tools 是字典；这里需要的是 Tool 对象，不是工具名称。
        # - 每个 Tool 都继承了 tools/base.py 中的 to_schema()。
        # - 返回类型说明最终结果必须是列表。

        # 重新完成前先回答：
        # - 直接遍历字典得到键还是值？
        # - 这里需要调用 to_schema() 的是字符串还是 Tool 对象？

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """执行白名单工具，并把成功或异常统一转换为 JSON 字符串。"""

        # TODO（必须由你手写）：
        # 1. 用 get(name) 查找工具，拒绝未知工具。
        # 2. arguments 必须是 dict。
        # 3. 调用 tool.run(arguments)。
        # 4. 成功时返回 _result(True, result=执行结果)。
        # 5. 捕获 TypeError、ValueError、ZeroDivisionError、OverflowError。
        # 6. 最后捕获其他 Exception，避免单个工具让 Agent 进程退出。
        tool = self.get(name)
        if tool is None:
            #raise ValueError("未知工具")
             return _result(
                                False,
                                error="未知工具"
                            )
        if not isinstance(arguments,dict):
            #raise TypeError("arguments 必须是 dict")
             return _result(
                                            False,
                                            error="arguments 必须是 dict"
                                        )
        try:
            tool_result = tool.run(arguments)
        except (TypeError,ValueError,ZeroDivisionError,OverflowError) as exc:
                return _result(
                    False,
                    error="工具调用错误"
                )
        except   Exception as e:
            return _result(
                False,
                error="工具内部错误"
            )
        else:
            return _result(
                True,
                result=tool_result
            )
        # 项目内参考：
        # - 查找工具应复用本类的 get()，具体执行入口是 Tool.run()。
        # - _result() 已在文件底部实现，返回值正好符合本方法的 str 标注。
        # - CalculatorTool.run() 展示了可能抛出的参数与计算异常。


def _result(ok: bool, **payload: Any) -> str:
    """工具结果统一使用 JSON，模型和测试无需猜测文本格式。"""

    return json.dumps({"ok": ok, **payload}, ensure_ascii=False)
