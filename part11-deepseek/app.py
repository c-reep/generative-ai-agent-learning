import ast
import json
import math
import operator
import os
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)


SYSTEM_PROMPT = (
    "你是一名耐心、准确的学习助手。"
    "当计算、保存笔记或查询当前天气能帮助用户时，使用已提供的工具。"
    "不要声称工具已经执行，除非你收到了对应的工具执行结果。"
)
MAX_TOOL_ROUNDS = 5
NOTES_FILE = Path(__file__).resolve().with_name("notes.txt")

# 完成下面两个 TODO 后，再改成 True。程序会在此之前阻止真实 API 请求。
EXERCISE_COMPLETE = True


BINARY_OPERATORS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
UNARY_OPERATORS: dict[type[ast.unaryop], Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# 定义工具列表，这是针对llm的
TOOLS = [
    {
        "type": "function",
        "name": "calculator",
        "description": "计算只包含数字、括号和常见算术运算符的表达式。",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "需要计算的算术表达式，例如 (12 + 8) / 4。",
                }
            },
            "required": ["expression"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "save_note",
        "description": "把用户明确要求保存的笔记追加到项目内的 notes.txt。",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "需要保存的笔记正文。",
                }
            },
            "required": ["content"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_weather",
        "description": "查询指定城市或地区的当前天气。",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "城市或地区名称，例如杭州、北京或巴黎。",
                }
            },
            "required": ["location"],
            "additionalProperties": False,
        },
    },
]


def create_client() -> OpenAI:
    """读取本地环境变量并创建 DeepSeek 客户端。"""
    load_dotenv()

    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "缺少 DEEPSEEK_API_KEY。请先在 .env 文件中填写你的 DeepSeek API Key。"
        )

    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        timeout=30.0,
        max_retries=2,
    )


def new_history() -> list[Any]:
    """创建只包含 System 消息的新对话。"""
    return [{"role": "system", "content": SYSTEM_PROMPT}]


def _evaluate_node(node: ast.AST) -> float:
    """递归计算经过限制的抽象语法树节点。"""
    if isinstance(node, ast.Expression):
        return _evaluate_node(node.body)

    if isinstance(node, ast.Constant):
        if type(node.value) not in (int, float):
            raise ValueError("表达式中只能出现数字。")
        if abs(node.value) > 1_000_000_000_000:
            raise ValueError("数字过大。")
        return float(node.value)

    if isinstance(node, ast.UnaryOp):
        operation = UNARY_OPERATORS.get(type(node.op))
        if operation is None:
            raise ValueError("包含不支持的一元运算符。")
        return operation(_evaluate_node(node.operand))

    if isinstance(node, ast.BinOp):
        operation = BINARY_OPERATORS.get(type(node.op))
        if operation is None:
            raise ValueError("包含不支持的二元运算符。")

        left = _evaluate_node(node.left)
        right = _evaluate_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 10:
            raise ValueError("指数绝对值不能超过 10。")
        return float(operation(left, right))

    raise ValueError("表达式包含函数、变量或其他不允许的内容。")


def calculator(expression: str) -> float:
    """安全计算简单算术表达式，不使用 eval。"""
    if not isinstance(expression, str):
        raise TypeError("expression 必须是字符串。")

    expression = expression.strip()
    if not expression:
        raise ValueError("表达式不能为空。")
    if len(expression) > 100:
        raise ValueError("表达式过长。")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError("表达式语法错误。") from exc

    if sum(1 for _ in ast.walk(tree)) > 50:
        raise ValueError("表达式过于复杂。")

    result = _evaluate_node(tree)
    if not math.isfinite(result):
        raise ValueError("计算结果不是有限数字。")
    return result


def save_note(content: str) -> str:
    """把非空笔记追加到项目目录内的 notes.txt。"""
    # TODO 1（由你手写）：
    # 1. 检查 content 是字符串。
    if not isinstance(content, str):
        raise TypeError("content 必须是字符串。")
    # 2. 去除首尾空白并拒绝空内容。
    content = content.strip()
    if not content:
        raise ValueError("笔记内容不能为空。")
    # 3. 限制单条笔记最长 2000 个字符。
    if len(content)>2000:
        raise ValueError("笔记长度不能大于2000字符。")
    # 4. 使用追加模式和 UTF-8，把内容写入 NOTES_FILE。
    with NOTES_FILE.open("a", encoding="utf-8") as note_file:
        note_file.write(content + "\n")
    # 5. 返回字符串："笔记已保存到 notes.txt。"
    return "笔记已保存到 notes.txt。"


class WeatherServiceError(RuntimeError):
    """天气服务不可用或返回了无效数据。"""


WEATHER_DESCRIPTIONS = {
    0: "晴朗",
    1: "大致晴朗",
    2: "局部多云",
    3: "阴天",
    45: "雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "中等毛毛雨",
    55: "强毛毛雨",
    56: "轻微冻毛毛雨",
    57: "强冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "轻微冻雨",
    67: "强冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "中等阵雨",
    82: "强阵雨",
    85: "小阵雪",
    86: "强阵雪",
    95: "雷暴",
    96: "雷暴伴轻微冰雹",
    99: "雷暴伴强冰雹",
}


def _fetch_json(base_url: str, params: dict[str, object]) -> dict[str, Any]:
    """发送 GET 请求并返回 JSON 对象。"""
    url = f"{base_url}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "part11-deepseek/1.0"})

    try:
        with urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise WeatherServiceError(f"天气服务返回 HTTP {exc.code}。") from exc
    except (URLError, TimeoutError) as exc:
        raise WeatherServiceError("无法连接天气服务。") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WeatherServiceError("天气服务返回了无法解析的数据。") from exc

    if not isinstance(data, dict):
        raise WeatherServiceError("天气服务返回的数据格式不正确。")
    if data.get("error"):
        raise WeatherServiceError(str(data.get("reason", "天气服务请求失败。")))
    return data


def get_weather(location: str) -> dict[str, object]:
    """通过 Open-Meteo 查询指定地点的当前天气。"""
    if not isinstance(location, str):
        raise TypeError("location 必须是字符串。")

    location = location.strip()
    if len(location) < 2:
        raise ValueError("地点名称至少需要两个字符。")
    if len(location) > 100:
        raise ValueError("地点名称不能超过 100 个字符。")

    geocoding = _fetch_json(
        "https://geocoding-api.open-meteo.com/v1/search",
        {"name": location, "count": 1, "language": "zh", "format": "json"},
    )
    locations = geocoding.get("results")
    if not isinstance(locations, list) or not locations:
        raise ValueError(f"找不到地点：{location}")

    place = locations[0]
    if not isinstance(place, dict):
        raise WeatherServiceError("地理编码结果格式不正确。")

    latitude = place.get("latitude")
    longitude = place.get("longitude")
    if not isinstance(latitude, (int, float)) or not isinstance(
        longitude, (int, float)
    ):
        raise WeatherServiceError("地理编码结果缺少经纬度。")

    forecast = _fetch_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,apparent_temperature,"
                "relative_humidity_2m,weather_code,wind_speed_10m"
            ),
            "timezone": "auto",
            "forecast_days": 1,
        },
    )
    current = forecast.get("current")
    units = forecast.get("current_units", {})
    if not isinstance(current, dict) or not isinstance(units, dict):
        raise WeatherServiceError("天气服务没有返回当前天气。")

    weather_code = current.get("weather_code")
    weather_text = WEATHER_DESCRIPTIONS.get(weather_code, f"未知代码 {weather_code}")
    location_parts = [
        str(value)
        for value in (place.get("name"), place.get("admin1"), place.get("country"))
        if value
    ]

    return {
        "location": "，".join(dict.fromkeys(location_parts)),
        "observation_time": current.get("time"),
        "weather": weather_text,
        "temperature": current.get("temperature_2m"),
        "temperature_unit": units.get("temperature_2m", "°C"),
        "apparent_temperature": current.get("apparent_temperature"),
        "humidity": current.get("relative_humidity_2m"),
        "humidity_unit": units.get("relative_humidity_2m", "%"),
        "wind_speed": current.get("wind_speed_10m"),
        "wind_speed_unit": units.get("wind_speed_10m", "km/h"),
        "source": "Open-Meteo",
    }

#建立从llm消息摘要（左）到真实python函数的映射(右)
AVAILABLE_TOOLS: dict[str, Callable[..., object]] = {
    "calculator": calculator,
    "save_note": save_note,
    "get_weather": get_weather,
}
EXPECTED_ARGUMENTS = {
    "calculator": {"expression"},
    "save_note": {"content"},
    "get_weather": {"location"},
}


def _tool_result(ok: bool, **details: object) -> str:
    """把工具结果统一编码为 JSON 字符串。"""
    return json.dumps({"ok": ok, **details}, ensure_ascii=False)


def execute_tool_call(tool_call: Any) -> dict[str, str]:
    """校验并执行模型请求的工具，返回 function_call_output。"""
    # TODO 2（由你手写）：
    # 1. 从 tool_call 读取 name、arguments 和 call_id。
    #将模型给出的工具名->python定义的函数名
    function_name = tool_call.name
    function_call_id = tool_call.call_id
    # 2. 用 json.loads() 把 arguments 解析为字典。
    try:
        function_args  = json.loads(tool_call.arguments)
        if not isinstance(function_args, dict):
            raise TypeError("工具参数必须是 JSON 对象。")
    # 3. 从 AVAILABLE_TOOLS 白名单查找真实 Python 函数。
        function_to_call = AVAILABLE_TOOLS.get(function_name)
    # 4. 用 EXPECTED_ARGUMENTS 检查参数字段是否正确。
    #若没有在AVAILABLE_TOOLS 白名单中找到
        if function_to_call is None:
            result = _tool_result(
                False,
                error=f"不允许调用工具：{function_name}",
            )
        else:
            #如果要用这个方法，我期待你传入形如{"expression"}的参数
            #expected = EXPECTED_ARGUMENTS["calculator"]
            #expected = {"expression"}
            expected = EXPECTED_ARGUMENTS[function_name]
            #function_args 是字典，使用set取字典的键
            #function_args={"expression": "12 + 8"}
            #set(function_args) = "expression",表示我确实传入了一个名为"expression"的参数
            actual = set(function_args)
            if actual != expected:
                raise ValueError("参数名称不正确")
            # 5. 执行 function(**arguments)，捕获工具运行异常。
            function_response = function_to_call(**function_args)
            result = _tool_result(
                True,
                result=function_response,
            )
    except json.JSONDecodeError:
        result = _tool_result(False, error="工具参数不是合法JSON。")
    except (TypeError, ValueError) as exc:
        result = _tool_result(False, error=f"参数错误：{exc}")
    except (ZeroDivisionError, OverflowError) as exc:
        result = _tool_result(False, error=f"计算错误：{exc}")
    except WeatherServiceError as exc:
        result = _tool_result(False, error=f"天气查询失败：{exc}")
    except OSError as exc:
        result = _tool_result(False, error=f"文件操作失败：{exc}")
    # 6. 成功和失败结果都使用 _tool_result() 转成 JSON 字符串。
    # 7. 返回下面的结构，并保证 call_id 与请求一致：
    return {
         "type": "function_call_output",
         "call_id": function_call_id,
         "output": result,
     }


def run_agent_turn(client: OpenAI, conversation: list[Any]) -> str:
    """运行模型与工具之间的闭环，直到得到最终文本回答。"""
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-flash").strip()

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.responses.create(
            model=model,
            input=conversation,
            tools=TOOLS,
            tool_choice="auto",
            reasoning={"effort": "none"},
            max_output_tokens=800,
            store=False,
        )

        conversation.extend(response.output)
        tool_calls = [
            item for item in response.output if item.type == "function_call"
        ]

        if not tool_calls:
            answer = response.output_text.strip()
            if not answer:
                raise RuntimeError("模型既没有返回文本，也没有请求工具。")
            return answer

        for tool_call in tool_calls:
            conversation.append(execute_tool_call(tool_call))

    raise RuntimeError("工具调用轮数超过限制，已停止本轮请求。")


def main() -> None:
    if not EXERCISE_COMPLETE:
        raise SystemExit(
            "学习任务尚未完成：请完成两个 TODO，测试通过后将 "
            "EXERCISE_COMPLETE 改为 True。"
        )

    client = create_client()
    history = new_history()

    print("DeepSeek Function Calling Agent 已启动。")
    print("工具：calculator、save_note、get_weather")
    print("命令：exit/quit 退出，clear 清空对话。\n")

    while True:
        try:
            user_input = input("你：").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n对话已结束。")
            break

        if not user_input:
            print("请输入内容。")
            continue

        command = user_input.lower()
        if command in {"exit", "quit"}:
            print("对话已结束。")
            break

        if command == "clear":
            history = new_history()
            print("历史已清空，但 System 消息仍然保留。\n")
            continue

        # 使用候选历史；API 失败时不污染正式 history。
        working_history = history.copy()
        working_history.append({"role": "user", "content": user_input})

        try:
            answer = run_agent_turn(client, working_history)
        except AuthenticationError:
            print("认证失败：请检查 DEEPSEEK_API_KEY 是否正确。")
            continue
        except RateLimitError:
            print("请求过于频繁或账户额度受限，请稍后重试。")
            continue
        except (APIConnectionError, APITimeoutError):
            print("无法连接 DeepSeek 服务，请检查网络后重试。")
            continue
        except APIStatusError as exc:
            print(f"DeepSeek 服务返回错误，状态码：{exc.status_code}")
            continue
        except Exception as exc:
            print(f"本轮请求失败：{exc}")
            continue

        history = working_history
        print(f"\nAgent：{answer}\n")


if __name__ == "__main__":
    main()
