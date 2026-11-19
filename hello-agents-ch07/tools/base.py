"""所有工具都必须遵守的统一接口。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """工具只描述能力并执行 Python 逻辑，不负责选择自己何时被调用。"""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
    ) -> None:
        self.name = name
        self.description = description
        self.parameters = parameters

    @abstractmethod
    def run(self, arguments: dict[str, Any]) -> Any:
        """执行已经由注册表确认过的工具参数。"""

    def to_schema(self) -> dict[str, Any]:
        """把“工具定义”(agent框架内用的）转换成模型 API(openai sdk) 认识的标准格式。(字典)"""

        # TODO（必须由你手写）：
        # 返回一个新的 Function Calling Schema 字典。
        tool_to_schema :dict[str, Any]={
           "type":"function",
           "function":{
               "name":self.name,
               "description":self.description,
               "parameters":self.parameters
           }
        }
        return tool_to_schema
        # 项目内参考：
        # - 可用数据来自 Tool.__init__() 保存的三个字段。
        # - 目标结构见 tests/test_todos.py 的
        #   RegistryTests.test_schema_uses_native_function_calling_format。
        # - tools/builtin.py 展示了 parameters 字段内部的 JSON Schema。

        # 重新完成前先回答：
        # - 这个方法是执行工具，还是只生成给模型看的说明书？给模型看的说明书
