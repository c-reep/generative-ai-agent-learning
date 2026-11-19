"""基于统一 Agent 基类实现的具体运行策略。"""

from .function_call_agent import FunctionCallAgent
from .simple_agent import SimpleAgent

__all__ = ["FunctionCallAgent", "SimpleAgent"]
