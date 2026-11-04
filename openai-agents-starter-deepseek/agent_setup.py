"""定义 Agent：DeepSeek 负责判断，Python 工具负责可靠执行。"""

from openai import AsyncOpenAI
from agents import Agent, OpenAIResponsesModel

from tools import calculator, get_weather, save_note


AGENT_INSTRUCTIONS = """
你是一个简洁、可靠的中文终端助手。

规则：
1. 普通知识问题可以直接回答。
2. 遇到算术表达式时使用 calculator，不要心算后假装调用过工具。
3. 用户询问当前天气时使用 get_weather，不要用训练数据猜实时天气。
4. 只有用户明确要求“保存/记下”时才使用 save_note。
5. 工具返回 ok=false 时，诚实说明失败原因，不要编造成功结果。
6. 最终回答尽量简洁，并明确区分工具结果与模型解释。
""".strip()


def build_agent(settings) -> Agent:
    client = AsyncOpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
    )

    # Agents SDK 继续负责编排；模型请求改走 DeepSeek 兼容的 Responses API。
    model = OpenAIResponsesModel(
        model=settings.model,
        openai_client=client,
    )

    return Agent(
        name="学习助手",
        instructions=AGENT_INSTRUCTIONS,
        model=model,
        tools=[calculator, save_note, get_weather],
    )
