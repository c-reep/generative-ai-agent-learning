"""Agent 可以调用的工具，以及不依赖模型的纯 Python 实现。"""

from __future__ import annotations

import ast
from datetime import datetime
import json
import math
import operator
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from agents import function_tool

from config import NOTES_FILE


class WeatherServiceError(RuntimeError):
    """天气服务不可用或返回了无法使用的数据。"""


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


def calculate_expression(expression: str) -> int | float:
    """只计算白名单内的算术语法，绝不直接使用 eval。"""

    if not isinstance(expression, str):
        raise TypeError("expression 必须是字符串。")

    expression = expression.strip()
    if not expression:
        raise ValueError("算式不能为空。")
    if len(expression) > 200:
        raise ValueError("算式过长。")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError("算式语法不正确。") from exc

    result = _evaluate_node(tree.body, depth=0)
    if not math.isfinite(float(result)):
        raise OverflowError("计算结果不是有限数字。")
    if abs(result) > 1_000_000_000_000_000:
        raise OverflowError("计算结果过大。")
    return result


def _evaluate_node(node: ast.AST, depth: int) -> int | float:
    """递归解释 AST；任何未明确允许的节点都会被拒绝。"""

    if depth > 12:
        raise ValueError("算式嵌套过深。")

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("算式中只能出现数字。")
        return node.value

    if isinstance(node, ast.UnaryOp):
        operation = _UNARY_OPERATORS.get(type(node.op))
        if operation is None:
            raise ValueError("包含不支持的一元运算。")
        return operation(_evaluate_node(node.operand, depth + 1))

    if isinstance(node, ast.BinOp):
        operation = _BINARY_OPERATORS.get(type(node.op))
        if operation is None:
            raise ValueError("包含不支持的运算符。")

        left = _evaluate_node(node.left, depth + 1)
        right = _evaluate_node(node.right, depth + 1)
        if isinstance(node.op, ast.Pow) and abs(right) > 12:
            raise OverflowError("指数绝对值不能超过 12。")

        result = operation(left, right)
        if not math.isfinite(float(result)) or abs(result) > 1_000_000_000_000_000:
            raise OverflowError("中间计算结果过大。")
        return result

    raise ValueError("算式包含变量、函数调用或其他不允许的语法。")


def append_note(content: str, notes_file: Path = NOTES_FILE) -> str:
    """校验后追加一条笔记；单独传入路径便于离线测试。"""

    if not isinstance(content, str):
        raise TypeError("content 必须是字符串。")

    cleaned = content.strip()
    if not cleaned:
        raise ValueError("笔记内容不能为空。")
    if len(cleaned) > 2_000:
        raise ValueError("单条笔记不能超过 2000 个字符。")

    notes_file.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    with notes_file.open("a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] {cleaned}\n")

    return f"笔记已保存到 {notes_file.name}。"


def _fetch_json(url: str, timeout: float = 8.0) -> dict[str, Any]:
    """发送只读 HTTP 请求，并把网络/JSON 错误统一成天气服务错误。"""

    request = Request(url, headers={"User-Agent": "openai-agents-starter/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise WeatherServiceError("无法连接天气服务或解析其响应。") from exc

    if not isinstance(payload, dict):
        raise WeatherServiceError("天气服务返回的数据格式不正确。")
    return payload


def lookup_weather(city: str) -> dict[str, Any]:
    """使用 Open-Meteo 查询城市当前天气，不需要额外 API Key。"""

    if not isinstance(city, str):
        raise TypeError("city 必须是字符串。")

    city = city.strip()
    if not city:
        raise ValueError("城市名称不能为空。")
    if len(city) > 80:
        raise ValueError("城市名称过长。")

    geocoding_query = urlencode(
        {"name": city, "count": 1, "language": "zh", "format": "json"}
    )
    location_data = _fetch_json(
        f"https://geocoding-api.open-meteo.com/v1/search?{geocoding_query}"
    )
    locations = location_data.get("results")
    if not isinstance(locations, list) or not locations:
        raise WeatherServiceError(f"没有找到城市：{city}")

    location = locations[0]
    if not isinstance(location, dict):
        raise WeatherServiceError("城市查询结果格式不正确。")

    try:
        latitude = float(location["latitude"])
        longitude = float(location["longitude"])
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherServiceError("城市坐标缺失。") from exc

    forecast_query = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": (
                "temperature_2m,apparent_temperature,precipitation,"
                "weather_code,wind_speed_10m"
            ),
            "timezone": "auto",
        }
    )
    forecast_data = _fetch_json(
        f"https://api.open-meteo.com/v1/forecast?{forecast_query}"
    )
    current = forecast_data.get("current")
    if not isinstance(current, dict):
        raise WeatherServiceError("天气服务没有返回当前天气。")

    code = current.get("weather_code")
    return {
        "city": location.get("name", city),
        "country": location.get("country", ""),
        "temperature_c": current.get("temperature_2m"),
        "apparent_temperature_c": current.get("apparent_temperature"),
        "precipitation_mm": current.get("precipitation"),
        "wind_speed_kmh": current.get("wind_speed_10m"),
        "weather": _weather_description(code),
        "observed_at": current.get("time"),
        "source": "Open-Meteo",
    }


def _weather_description(code: Any) -> str:
    """把 WMO 天气代码压缩成适合终端显示的中文描述。"""

    try:
        numeric_code = int(code)
    except (TypeError, ValueError):
        return "未知"

    if numeric_code == 0:
        return "晴"
    if numeric_code in {1, 2, 3}:
        return "多云"
    if numeric_code in {45, 48}:
        return "雾"
    if numeric_code in {51, 53, 55, 56, 57}:
        return "毛毛雨"
    if numeric_code in {61, 63, 65, 66, 67, 80, 81, 82}:
        return "雨"
    if numeric_code in {71, 73, 75, 77, 85, 86}:
        return "雪"
    if numeric_code in {95, 96, 99}:
        return "雷暴"
    return "未知"


def _tool_result(ok: bool, **payload: Any) -> str:
    """工具统一返回 JSON 字符串，便于模型和日志稳定读取。"""

    return json.dumps({"ok": ok, **payload}, ensure_ascii=False)


@function_tool
def calculator(expression: str) -> str:
    """精确计算一个算术表达式。需要真实计算结果时必须使用此工具。"""

    try:
        result = calculate_expression(expression)
        return _tool_result(True, expression=expression, result=result)
    except (TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
        return _tool_result(False, error=f"计算失败：{exc}")


@function_tool
def save_note(content: str) -> str:
    """将用户明确要求保存的文本追加到本地 notes.txt。"""

    try:
        message = append_note(content)
        return _tool_result(True, result=message)
    except (TypeError, ValueError, OSError) as exc:
        return _tool_result(False, error=f"保存失败：{exc}")


@function_tool
def get_weather(city: str) -> str:
    """查询指定城市的当前天气。不要凭模型记忆猜测实时天气。"""

    try:
        return _tool_result(True, result=lookup_weather(city))
    except (TypeError, ValueError, WeatherServiceError) as exc:
        return _tool_result(False, error=f"天气查询失败：{exc}")
