import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import (
    WeatherServiceError,
    append_note,
    calculate_expression,
    lookup_weather,
)


class CalculatorTests(unittest.TestCase):
    def test_parentheses_and_precedence(self) -> None:
        self.assertEqual(calculate_expression("(10+15)/5*6"), 30)

    def test_division_by_zero_is_reported(self) -> None:
        with self.assertRaises(ZeroDivisionError):
            calculate_expression("10 / 0")

    def test_python_code_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            calculate_expression("__import__('os').getcwd()")

    def test_empty_expression_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            calculate_expression("   ")


class SaveNoteTests(unittest.TestCase):
    def test_note_is_appended_as_utf8(self) -> None:
        # 把临时目录放在项目测试目录中，避免不同系统的全局临时目录权限差异。
        with TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / "notes.txt"
            append_note("第一条学习笔记", path)
            append_note("第二条学习笔记", path)

            content = path.read_text(encoding="utf-8")
            self.assertIn("第一条学习笔记", content)
            self.assertIn("第二条学习笔记", content)

    def test_empty_note_is_rejected(self) -> None:
        with TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / "notes.txt"
            with self.assertRaises(ValueError):
                append_note("  ", path)


class WeatherTests(unittest.TestCase):
    @patch("tools._fetch_json")
    def test_weather_combines_location_and_forecast(self, fetch_json) -> None:
        fetch_json.side_effect = [
            {
                "results": [
                    {
                        "name": "上海",
                        "country": "中国",
                        "latitude": 31.23,
                        "longitude": 121.47,
                    }
                ]
            },
            {
                "current": {
                    "temperature_2m": 22.5,
                    "apparent_temperature": 23.0,
                    "precipitation": 0.0,
                    "weather_code": 1,
                    "wind_speed_10m": 8.4,
                    "time": "2026-11-04T10:00",
                }
            },
        ]

        result = lookup_weather("上海")

        self.assertEqual(result["city"], "上海")
        self.assertEqual(result["temperature_c"], 22.5)
        self.assertEqual(result["weather"], "多云")
        self.assertEqual(fetch_json.call_count, 2)

    @patch("tools._fetch_json", return_value={"results": []})
    def test_unknown_city_is_reported(self, _fetch_json) -> None:
        with self.assertRaises(WeatherServiceError):
            lookup_weather("不存在的城市")


if __name__ == "__main__":
    unittest.main()
