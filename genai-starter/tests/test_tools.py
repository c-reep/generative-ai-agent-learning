"""工具层测试：不调用 DeepSeek，也不访问真实天气服务。"""

import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import tools


class CalculatorTests(unittest.TestCase):
    def test_calculates_supported_expression(self) -> None:
        self.assertEqual(tools.calculator("(12 + 8) / 4"), 5.0)

    def test_rejects_empty_expression(self) -> None:
        with self.assertRaises(ValueError):
            tools.calculator("   ")

    def test_rejects_python_code(self) -> None:
        with self.assertRaises(ValueError):
            tools.calculator("__import__('os').getcwd()")

    def test_reports_division_by_zero(self) -> None:
        with self.assertRaises(ZeroDivisionError):
            tools.calculator("1 / 0")


class SaveNoteTests(unittest.TestCase):
    def test_appends_trimmed_note(self) -> None:
        # 临时目录放在项目测试目录中，测试结束后自动删除。
        tests_dir = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(dir=tests_dir) as temp_dir:
            notes_file = Path(temp_dir) / "notes.txt"
            with patch.object(tools, "NOTES_FILE", notes_file):
                result = tools.save_note("  第一条笔记  ")
                tools.save_note("第二条笔记")

            self.assertEqual(result, "笔记已保存到 notes.txt。")
            self.assertEqual(
                notes_file.read_text(encoding="utf-8"),
                "第一条笔记\n第二条笔记\n",
            )

    def test_rejects_empty_note(self) -> None:
        with self.assertRaises(ValueError):
            tools.save_note("   ")


class WeatherTests(unittest.TestCase):
    @patch.object(tools, "_fetch_json")
    def test_returns_structured_weather(self, fetch_json) -> None:
        # 使用模拟响应，保证测试不受网络和天气变化影响。
        fetch_json.side_effect = [
            {
                "results": [
                    {
                        "name": "杭州",
                        "admin1": "浙江",
                        "country": "中国",
                        "latitude": 30.25,
                        "longitude": 120.17,
                    }
                ]
            },
            {
                "current": {
                    "time": "2026-11-03T12:00",
                    "temperature_2m": 20.0,
                    "apparent_temperature": 19.0,
                    "relative_humidity_2m": 60,
                    "weather_code": 1,
                    "wind_speed_10m": 8.0,
                },
                "current_units": {
                    "temperature_2m": "°C",
                    "relative_humidity_2m": "%",
                    "wind_speed_10m": "km/h",
                },
            },
        ]

        result = tools.get_weather("杭州")

        self.assertEqual(result["location"], "杭州，浙江，中国")
        self.assertEqual(result["weather"], "大致晴朗")
        self.assertEqual(result["temperature"], 20.0)
        self.assertEqual(fetch_json.call_count, 2)

    @patch.object(tools, "_fetch_json", return_value={"results": []})
    def test_rejects_unknown_location(self, _fetch_json) -> None:
        with self.assertRaises(ValueError):
            tools.get_weather("不存在的地点")


class ExecuteToolCallTests(unittest.TestCase):
    """验证工具执行安全边界的正常与失败路径。"""

    @staticmethod
    def make_call(name: str, arguments: str, call_id: str = "call_test"):
        return SimpleNamespace(name=name, arguments=arguments, call_id=call_id)

    def test_executes_calculator_and_returns_function_output(self) -> None:
        call = self.make_call(
            "calculator",
            json.dumps({"expression": "6 * 7"}),
        )

        output = tools.execute_tool_call(call)
        body = json.loads(output["output"])

        self.assertEqual(output["type"], "function_call_output")
        self.assertEqual(output["call_id"], "call_test")
        self.assertEqual(body, {"ok": True, "result": 42.0})

    def test_rejects_unknown_tool_without_crashing(self) -> None:
        output = tools.execute_tool_call(self.make_call("delete_file", "{}"))
        body = json.loads(output["output"])

        self.assertFalse(body["ok"])
        self.assertIn("不允许", body["error"])

    def test_reports_malformed_json(self) -> None:
        output = tools.execute_tool_call(self.make_call("calculator", "{bad json"))
        body = json.loads(output["output"])

        self.assertFalse(body["ok"])
        self.assertIn("JSON", body["error"])

    def test_rejects_wrong_argument_name(self) -> None:
        call = self.make_call(
            "calculator",
            json.dumps({"wrong": "6 * 7"}),
        )

        output = tools.execute_tool_call(call)
        body = json.loads(output["output"])

        self.assertFalse(body["ok"])
        self.assertIn("参数", body["error"])


if __name__ == "__main__":
    unittest.main()
