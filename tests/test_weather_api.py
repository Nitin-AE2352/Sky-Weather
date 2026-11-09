import unittest
from unittest.mock import patch

from Backend.weather_api import (
    _get_open_meteo_weather,
    get_air_quality,
)


class AirQualityTests(unittest.TestCase):
    @patch("Backend.weather_api._request")
    def test_air_quality_identifies_model_estimate_and_update_time(
        self,
        request,
    ):
        request.return_value = {
            "current": {
                "time": "2026-11-09T14:00",
                "us_aqi": 182,
                "european_aqi": 74,
            },
            "hourly": {
                "time": ["2026-11-09T14:00"],
                "us_aqi": [182],
            },
        }

        result = get_air_quality(28.58, 77.33, "Asia/Kolkata")

        self.assertEqual(result["current"]["us_aqi"], 182)
        self.assertEqual(result["updated_at"], "2026-11-09T14:00")
        self.assertEqual(result["source"], "Open-Meteo Air Quality")
        self.assertEqual(result["data_type"], "model_estimate")
        self.assertIn("not measurements", result["disclaimer"])
        request.assert_called_once()
        self.assertEqual(
            request.call_args.args[1]["timezone"],
            "Asia/Kolkata",
        )

    def test_air_quality_rejects_invalid_coordinates(self):
        with self.assertRaises(ValueError):
            get_air_quality(95, 77.33)

    @patch("Backend.weather_api._request")
    def test_open_meteo_can_request_a_specific_forecast_model(
        self,
        request,
    ):
        request.return_value = {
            "current": {
                "temperature_2m": 22,
                "weather_code": 1,
                "time": "2026-11-09T14:00",
            },
            "hourly": {},
            "daily": {},
            "timezone": "Asia/Kolkata",
        }

        result = _get_open_meteo_weather(
            28.58,
            77.33,
            "Asia/Kolkata",
            model="ecmwf_ifs025",
        )

        self.assertEqual(
            request.call_args.args[1]["models"],
            "ecmwf_ifs025",
        )
        self.assertEqual(
            result["source"],
            "Open-Meteo (ECMWF IFS025)",
        )
        self.assertEqual(result["model"], "ecmwf_ifs025")


if __name__ == "__main__":
    unittest.main()
