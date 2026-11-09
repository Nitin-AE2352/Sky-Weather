import unittest
from unittest.mock import patch

from Backend import ai_agent


class AiAgentTests(unittest.TestCase):
    @patch("Backend.ai_agent._generate_response")
    @patch("Backend.ai_agent._get_ollama_models")
    def test_uses_available_qwen_fallback(
        self,
        get_models,
        generate_response,
    ):
        get_models.return_value = ["qwen2.5:3b"]
        generate_response.return_value = "Rain is possible today."

        answer = ai_agent.ask_weather_ai(
            "Will it rain?",
            {
                "city": {"name": "Noida"},
                "weather": {"current": {"precipitation": 1}},
            },
        )

        self.assertEqual(answer, "Rain is possible today.")
        self.assertEqual(
            generate_response.call_args.args[2],
            "qwen2.5:3b",
        )

    def test_detects_hinglish(self):
        self.assertEqual(
            ai_agent._detect_response_language(
                "Aaj mausam kaisa hai?"
            ),
            "Hinglish",
        )


if __name__ == "__main__":
    unittest.main()
