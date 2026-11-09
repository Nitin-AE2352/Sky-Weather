import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from Backend.main import app, compare_weather


class ApiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_home_endpoint(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "running")

    @patch("Backend.main.compare_weather")
    def test_compare_forwards_selected_city_coordinates(
        self,
        compare_weather,
    ):
        compare_weather.return_value = {
            "success": True,
            "city": {"name": "Springfield", "latitude": 42.1},
            "comparison_available": False,
            "providers": {},
        }

        response = self.client.get(
            "/api/weather/compare",
            params={
                "city": "Springfield",
                "latitude": 42.1,
                "longitude": -72.6,
                "timezone": "America/New_York",
                "country": "United States",
                "country_code": "US",
                "admin1": "Massachusetts",
            },
        )

        self.assertEqual(response.status_code, 200)
        location = compare_weather.call_args.kwargs["location"]
        self.assertEqual(location["latitude"], 42.1)
        self.assertEqual(location["longitude"], -72.6)
        self.assertEqual(location["timezone"], "America/New_York")
        self.assertEqual(location["country_code"], "US")

    def test_compare_rejects_partial_coordinates(self):
        response = self.client.get(
            "/api/weather/compare",
            params={
                "city": "Springfield",
                "latitude": 42.1,
            },
        )

        self.assertEqual(response.status_code, 422)

    @patch("weather_compare._get_provider_weather")
    def test_comparison_compares_both_providers_at_selected_coordinates(
        self,
        get_provider_weather,
    ):
        get_provider_weather.side_effect = [
            {
                "source": "Open-Meteo",
                "current": {
                    "temperature_2m": 20,
                    "wind_speed_10m": 10,
                    "relative_humidity_2m": 50,
                },
            },
            {
                "source": "MET Norway",
                "current": {
                    "temperature_2m": 21,
                    "wind_speed_10m": 12,
                    "relative_humidity_2m": 55,
                },
            },
        ]
        location = {
            "name": "Springfield",
            "latitude": 42.1,
            "longitude": -72.6,
            "timezone": "America/New_York",
            "country": "United States",
            "country_code": "US",
        }

        result = compare_weather("Springfield", location=location)

        self.assertTrue(result["comparison_available"])
        self.assertEqual(result["city"]["country"], "United States")
        self.assertEqual(
            result["comparison"]["temperature_difference_c"],
            1,
        )
        self.assertEqual(result["comparison"]["checks_passed"], 3)
        self.assertEqual(get_provider_weather.call_count, 2)
        for call in get_provider_weather.call_args_list:
            self.assertEqual(call.args[1:3], (42.1, -72.6))
            self.assertEqual(call.args[3], "America/New_York")

    @patch("weather_compare._get_provider_weather")
    def test_comparison_keeps_available_provider_when_other_fails(
        self,
        get_provider_weather,
    ):
        get_provider_weather.side_effect = [
            {
                "source": "Open-Meteo",
                "current": {"temperature_2m": 20},
            },
            {
                "source": "MET Norway",
                "error": "Provider unavailable.",
            },
            {
                "source": "Open-Meteo ECMWF IFS 0.25 degree",
                "error": "Model unavailable.",
            },
        ]

        result = compare_weather(
            "Noida",
            location={
                "name": "Noida",
                "latitude": 28.58,
                "longitude": 77.33,
                "timezone": "Asia/Kolkata",
            },
        )

        self.assertTrue(result["success"])
        self.assertFalse(result["comparison_available"])
        self.assertEqual(result["selected_provider"], "Open-Meteo")
        self.assertEqual(
            result["providers"]["met_norway"]["error"],
            "Provider unavailable.",
        )
        self.assertNotIn("diagnostics", result)

    @patch("weather_compare._get_provider_weather")
    def test_comparison_falls_back_to_ecmwf_when_met_norway_fails(
        self,
        get_provider_weather,
    ):
        get_provider_weather.side_effect = [
            {
                "source": "Open-Meteo",
                "current": {
                    "temperature_2m": 20,
                    "wind_speed_10m": 10,
                    "relative_humidity_2m": 50,
                },
            },
            {
                "source": "MET Norway",
                "error": "Unable to connect.",
            },
            {
                "source": "Open-Meteo ECMWF IFS 0.25 degree",
                "current": {
                    "temperature_2m": 22,
                    "wind_speed_10m": 12,
                    "relative_humidity_2m": 55,
                },
            },
        ]

        result = compare_weather(
            "Noida",
            location={
                "name": "Noida",
                "latitude": 28.58,
                "longitude": 77.33,
                "timezone": "Asia/Kolkata",
            },
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["comparison_available"])
        self.assertEqual(result["comparison_type"], "model")
        self.assertEqual(
            result["comparison"]["temperature_difference_c"],
            2,
        )
        self.assertEqual(
            result["providers"]["open_meteo_ecmwf_ifs"]["source"],
            "Open-Meteo ECMWF IFS 0.25 degree",
        )
        self.assertNotIn("met_norway", result["providers"])
        self.assertEqual(
            result["diagnostics"]["met_norway"]["error"],
            "Unable to connect.",
        )
        self.assertIn("MET Norway was unavailable", result["note"])
        self.assertEqual(
            get_provider_weather.call_args_list[-1].args,
            (
                "Open-Meteo ECMWF IFS",
                28.58,
                77.33,
                "Asia/Kolkata",
            ),
        )

    @patch("Backend.main.get_available_tools")
    def test_mcp_tools_returns_sync_client_result(self, get_tools):
        get_tools.return_value = {
            "success": True,
            "connected": True,
            "tools": [{"name": "search_weather_cities"}],
            "count": 1,
        }

        response = self.client.get("/api/mcp/tools")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    @patch("Backend.main.execute_mcp_tool")
    def test_mcp_call_returns_sync_client_result(self, execute_tool):
        execute_tool.return_value = {
            "success": True,
            "tool_name": "search_weather_cities",
            "content": {"cities": []},
            "is_error": False,
        }

        response = self.client.post(
            "/api/mcp/call",
            json={
                "tool_name": "search_weather_cities",
                "arguments": {"city_name": "Noida"},
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_error"])
        execute_tool.assert_called_once_with(
            "search_weather_cities",
            {"city_name": "Noida"},
        )

    @patch("Backend.main.execute_mcp_tool")
    def test_mcp_call_uses_selected_city_when_city_argument_is_missing(
        self,
        execute_tool,
    ):
        execute_tool.return_value = {
            "success": True,
            "tool_name": "get_city_weather",
            "content": {"city": {"name": "Noida"}},
            "is_error": False,
        }

        response = self.client.post(
            "/api/mcp/call",
            json={
                "tool_name": "get_city_weather",
                "arguments": {},
                "selected_city": "Noida",
            },
        )

        self.assertEqual(response.status_code, 200)
        execute_tool.assert_called_once_with(
            "get_city_weather",
            {"city_name": "Noida"},
        )

    @patch("Backend.main.execute_mcp_tool")
    def test_mcp_call_uses_selected_city_when_city_argument_is_blank(
        self,
        execute_tool,
    ):
        execute_tool.return_value = {
            "success": True,
            "tool_name": "search_weather_cities",
            "content": {"cities": []},
            "is_error": False,
        }

        response = self.client.post(
            "/api/mcp/call",
            json={
                "tool_name": "search_weather_cities",
                "arguments": {"city_name": "  "},
                "selected_city": "Delhi",
            },
        )

        self.assertEqual(response.status_code, 200)
        execute_tool.assert_called_once_with(
            "search_weather_cities",
            {"city_name": "Delhi"},
        )

    @patch("Backend.main.execute_mcp_tool")
    def test_mcp_call_requires_city_when_no_fallback_is_available(
        self,
        execute_tool,
    ):
        response = self.client.post(
            "/api/mcp/call",
            json={
                "tool_name": "get_city_forecast",
                "arguments": {},
            },
        )

        self.assertEqual(response.status_code, 400)
        execute_tool.assert_not_called()

    @patch("Backend.main.ask_weather_ai")
    def test_assistant_forwards_chat_history(self, ask_weather_ai):
        ask_weather_ai.return_value = "The current temperature is 28°C."

        response = self.client.post(
            "/api/assistant/chat",
            json={
                "question": "What is the temperature?",
                "weather_data": {"city": {"name": "Noida"}},
                "chat_history": [
                    {"role": "user", "content": "Hello"},
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["answer"],
            "The current temperature is 28°C.",
        )
        ask_weather_ai.assert_called_once_with(
            "What is the temperature?",
            {"city": {"name": "Noida"}},
            [{"role": "user", "content": "Hello"}],
        )


if __name__ == "__main__":
    unittest.main()
