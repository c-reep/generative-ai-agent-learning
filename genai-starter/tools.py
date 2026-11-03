"""Agent 可以调用的工具，以及唯一的工具执行入口。

安全边界：模型返回的工具名和参数都属于不可信输入。
只有通过白名单、JSON 解析和参数校验后，Python 才能执行真实函数。
"""

import ast
import json
import math
import operator
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from config import NOTES_FILE


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


def _evaluate_node(node: ast.AST) -> float:
    """只计算允许的抽象语法树节点，避免直接使用 eval。"""
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
    """安全计算简单算术表达式。"""
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
    if not isinstance(content, str):
        raise TypeError("content 必须是字符串。")

    content = content.strip()
    if not content:
        raise ValueError("笔记内容不能为空。")
    if len(content) > 2000:
        raise ValueError("单条笔记不能超过 2000 个字符。")

    # 使用追加模式，避免每次保存时覆盖以前的笔记。
    with NOTES_FILE.open("a", encoding="utf-8") as note_file:
        note_file.write(content + "\n")
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
    """发送 GET 请求并把外部服务错误转换为项目自己的异常。"""
    url = f"{base_url}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "genai-starter/1.0"})

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

    # 第一次请求：把人类地点名称转换成经纬度。
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

    # 第二次请求：经纬度比地名更精确，适合天气接口查询。
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


# TOOLS 是提供给 LLM 的“说明书”，不是 Python 函数本身。
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
                    "description": "需要计算的表达式，例如 (12 + 8) / 4。",
                }
            },
            "required": ["expression"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "save_note",
        "description": "把用户明确要求保存的笔记追加到 notes.txt。",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "需要保存的笔记正文。"}
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

# 白名单把模型输出的名称映射到真实函数。
# 不使用 globals() 或 eval()，避免模型调用未授权代码。
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
    """统一工具成功和失败结果，便于模型稳定读取。"""
    return json.dumps({"ok": ok, **details}, ensure_ascii=False)


def execute_tool_call(tool_call: Any) -> dict[str, str]:
    """校验并执行模型请求的工具，返回 function_call_output。"""
    # 这是模型输出进入真实 Python 函数前最重要的安全边界。
    # 1. 读取 tool_call.name、tool_call.arguments、tool_call.call_id。
    function_name = tool_call.name
    function_call_id = tool_call.call_id

    # 2. 在 try 中使用 json.loads() 解析 arguments，并确认结果是 dict。
    try:
        function_args = json.loads(tool_call.arguments)
        if not isinstance(function_args, dict):
            raise TypeError("工具参数必须是 JSON 对象。")

        # 3. 使用白名单查找真实函数；不使用 globals() 或 eval()。
        function_to_call = AVAILABLE_TOOLS.get(function_name)
        if function_to_call is None:
            result = _tool_result(
                False,
                error=f"不允许调用工具：{function_name}",
            )
        else:
            # 4. 参数名必须与预期完全一致，拒绝缺失或多余字段。
            expected_args = EXPECTED_ARGUMENTS[function_name]
            actual_args = set(function_args)
            if expected_args != actual_args:
                missing = expected_args - actual_args
                extra = actual_args - expected_args
                raise ValueError(
                    f"缺少参数：{sorted(missing)}；多余参数：{sorted(extra)}"
                )

            # 5. ** 把参数字典拆成函数需要的关键字参数。
            function_response = function_to_call(**function_args)

            # 6. 工具结果统一编码成 JSON 字符串交还模型。
            result = _tool_result(True, result=function_response)

    # 7. 工具失败也转换成模型可读结果，避免整个聊天程序退出。
    except json.JSONDecodeError:
        result = _tool_result(False, error="工具参数不是合法 JSON。")
    except (TypeError, ValueError) as exc:
        result = _tool_result(False, error=f"参数错误：{exc}")
    except (ZeroDivisionError, OverflowError) as exc:
        result = _tool_result(False, error=f"计算错误：{exc}")
    except WeatherServiceError as exc:
        result = _tool_result(False, error=f"天气查询失败：{exc}")
    except OSError as exc:
        result = _tool_result(False, error=f"文件操作失败：{exc}")

    # 8. 返回：
    return {
        "type": "function_call_output",
        "call_id": function_call_id,
        "output": result,
    }
