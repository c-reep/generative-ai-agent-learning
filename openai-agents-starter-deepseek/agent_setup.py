"""定义单 Agent 与 Routing Agent：模型判断意图，Python 工具执行动作。"""

from openai import AsyncOpenAI
from agents import Agent, OpenAIResponsesModel

from guardrails_setup import block_exposed_secrets, block_secret_output
from tools import calculator, get_weather, save_note


# Agent.name 会被 SDK 用来生成 Handoff 工具名，因此内部名称必须只使用
# 英文字母、数字和下划线。终端显示时再映射为易读的中文名称。
AGENT_DISPLAY_NAMES = {
    "routing_agent": "分流助手",
    "calculation_agent": "计算助手",
    "life_agent": "生活助手",
}


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


CALCULATION_AGENT_INSTRUCTIONS = """
你是一个严谨的计算助手。

规则：
1. 只处理数学计算相关请求。
2. 必须使用 calculator 得到计算结果，不要心算后假装调用过工具。
3. 工具返回 ok=false 时，解释失败原因，不要编造结果。
4. 回答保持简洁，并明确说明结果来自计算工具。
""".strip()


LIFE_AGENT_INSTRUCTIONS = """
你是一个处理天气查询和笔记保存的生活助手。

规则：
1. 查询当前天气时必须使用 get_weather，不要用训练数据猜测实时天气。
2. 只有用户明确要求“保存”或“记下”时才使用 save_note。
3. 工具返回 ok=false 时，解释失败原因，不要编造成功结果。
4. 不处理数学计算；数学请求应由计算助手处理。
""".strip()


ROUTING_AGENT_INSTRUCTIONS = """
你是整个应用的入口和分流助手。

路由规则：
1. 数学计算请求必须转交给“计算助手”。
2. 当前天气查询、保存笔记请求必须转交给“生活助手”。
3. 普通知识问题可以直接回答，不需要转交。
4. 不要自己完成专业助手负责的任务。
5. 一次请求只选择最匹配的处理者；遇到跨领域复合请求时，先请用户拆分问题。
""".strip()


def build_model(settings) -> OpenAIResponsesModel:
    """创建所有 Agent 共用的 DeepSeek 模型适配器。"""

    client = AsyncOpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
    )

    # Agents SDK 继续负责编排；模型请求改走 DeepSeek 兼容的 Responses API。
    return OpenAIResponsesModel(
        model=settings.model,
        openai_client=client,
    )


def build_agent(settings) -> Agent:
    """保留原来的单 Agent 版本，方便和 Routing 版本对比。"""

    model = build_model(settings)

    return Agent(
        name="学习助手",
        instructions=AGENT_INSTRUCTIONS,
        model=model,
        tools=[calculator, save_note, get_weather],
    )


def build_routing_agent(settings) -> Agent:
    """创建路由 Agent，并将不同工具隔离到两个专业 Agent。"""

    # 三个 Agent 共用同一个底层模型，但拥有不同指令、工具和职责。
    model = build_model(settings)

    calculation_agent = Agent(
        name="calculation_agent",
        handoff_description="处理需要可靠数学计算的请求。",
        instructions=CALCULATION_AGENT_INSTRUCTIONS,
        model=model,
        tools=[calculator],
        # 可能在执行计算类任务后作为最终agent退出，因此绑定output_guardrails
        output_guardrails=[block_secret_output],
    )

    life_agent = Agent(
        name="life_agent",
        handoff_description="处理当前天气查询和保存笔记请求。",
        instructions=LIFE_AGENT_INSTRUCTIONS,
        model=model,
        tools=[get_weather, save_note],
        #可能在执行生活类任务后作为最终agent退出，因此绑定output_guardrails
        output_guardrails=[block_secret_output],
    )

    return Agent(
        name="routing_agent",
        instructions=ROUTING_AGENT_INSTRUCTIONS,
        model=model,
        # Input Guardrail 只在整条链的第一个 Agent 上运行。
        input_guardrails=[block_exposed_secrets],
        # 普通知识问题由路由 Agent 直接回答，所以它也可能是最终 Agent。
        output_guardrails=[block_secret_output],
        # Handoff 表示：路由 Agent 判断意图后，由专业 Agent 接管本轮回答。
        handoffs=[calculation_agent, life_agent],
    )
