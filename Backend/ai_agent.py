
import json
import os
import re

import httpx


# =========================================================
# CONFIGURATION
# =========================================================

OLLAMA_HOST = os.getenv(
    "OLLAMA_HOST",
    "http://localhost:11434",
).rstrip("/")

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "qwen2.5:1.5b",
).strip()

OLLAMA_FALLBACK_MODELS = [
    model.strip()
    for model in os.getenv(
        "OLLAMA_FALLBACK_MODELS",
        "qwen2.5:3b,qwen2.5:1.5b",
    ).split(",")
    if model.strip()
]

OLLAMA_TIMEOUT = float(
    os.getenv("OLLAMA_TIMEOUT", "120")
)

OLLAMA_KEEP_ALIVE = os.getenv(
    "OLLAMA_KEEP_ALIVE",
    "5m",
)

CHAT_URL = f"{OLLAMA_HOST}/api/chat"
TAGS_URL = f"{OLLAMA_HOST}/api/tags"


# =========================================================
# COMMON HELPERS
# =========================================================

def _clean_model_name(model_name):
    """
    Remove a tag only when comparing model names.
    Example: qwen2.5:1.5b
    """
    return str(model_name or "").strip().lower()


def _extract_model_names(data):
    models = []

    for item in data.get("models", []):
        name = item.get("name")

        if name:
            models.append(name)

    return models


def _get_ollama_models():
    try:
        response = httpx.get(
            TAGS_URL,
            timeout=10,
        )

        response.raise_for_status()

        return _extract_model_names(
            response.json()
        )

    except httpx.TimeoutException:
        raise RuntimeError(
            "Ollama connection timed out."
        )

    except httpx.ConnectError:
        raise RuntimeError(
            "Ollama is not running. "
            "Start Ollama and try again."
        )

    except httpx.HTTPStatusError as error:
        raise RuntimeError(
            f"Ollama returned HTTP "
            f"{error.response.status_code}."
        )

    except (httpx.RequestError, ValueError) as error:
        raise RuntimeError(
            f"Could not read Ollama models: {error}"
        )


def _model_is_available(model_name, available_models):
    target = _clean_model_name(model_name)

    return any(
        _clean_model_name(name) == target
        for name in available_models
    )


def _select_available_model(available_models):
    candidates = [OLLAMA_MODEL, *OLLAMA_FALLBACK_MODELS]
    for candidate in candidates:
        if _model_is_available(candidate, available_models):
            return candidate
    return None


# =========================================================
# OLLAMA CONNECTION STATUS
# =========================================================

def check_ollama_connection():
    """
    Check whether Ollama is running and whether
    the configured model is installed.
    """

    try:
        available_models = _get_ollama_models()

        selected_model = _select_available_model(
            available_models
        )
        model_available = selected_model is not None

        return {
            "connected": True,
            "model": OLLAMA_MODEL,
            "active_model": selected_model,
            "model_available": model_available,
            "available_models": available_models,
            "host": OLLAMA_HOST,
            "message": (
                "Ollama connected successfully."
                if model_available
                else (
                    "No configured Qwen model is installed. "
                    "Pull qwen2.5:1.5b or qwen2.5:3b before "
                    "using the assistant."
                )
            ),
        }

    except Exception as error:
        return {
            "connected": False,
            "model": OLLAMA_MODEL,
            "active_model": None,
            "model_available": False,
            "available_models": [],
            "host": OLLAMA_HOST,
            "error": str(error),
        }


# =========================================================
# WEATHER DATA PREPARATION
# =========================================================

def _prepare_weather_context(weather_data):
    """
    Prepare a compact weather context for the AI model.
    """

    if not isinstance(weather_data, dict):
        raise ValueError(
            "Weather data must be a dictionary."
        )

    city = weather_data.get("city", {})
    weather = weather_data.get("weather", {})

    if not isinstance(city, dict):
        city = {}

    if not isinstance(weather, dict):
        weather = {}

    current = weather.get("current", {})
    hourly = weather.get("hourly", {})
    daily = weather.get("daily", {})
    air_quality = weather.get("air_quality", {})

    context = {
        "location": {
            "city": city.get("name"),
            "country": city.get("country"),
            "state": city.get("admin1"),
            "timezone": weather.get("timezone"),
            "latitude": city.get("latitude"),
            "longitude": city.get("longitude"),
        },
        "current_weather": current,
        "hourly_forecast": hourly,
        "daily_forecast": daily,
        "air_quality": air_quality,
        "weather_source": weather.get("source"),
        "last_updated": weather.get("updated_at"),
    }

    # Keep the prompt within a reasonable size.
    serialized = json.dumps(
        context,
        ensure_ascii=False,
        default=str,
    )

    if len(serialized) > 30000:
        context["hourly_forecast"] = {
            key: value[:24]
            if isinstance(value, list)
            else value
            for key, value in hourly.items()
        }

        serialized = json.dumps(
            context,
            ensure_ascii=False,
            default=str,
        )

    return serialized


def _format_weather_number(value, suffix=""):
    if value is None or value == "":
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if not number.is_integer():
        return f"{number:.1f}{suffix}"

    return f"{int(number)}{suffix}"


def _answer_current_weather_question(question, weather_data):
    question_words = set(
        re.findall(r"[a-zA-Z]+", question.casefold())
    )
    question_text = question.casefold()
    asks_weather = (
        "weather" in question_words
        or "mausam" in question_words
        or "temperature" in question_words
        or "temp" in question_words
        or "मौसम" in question_text
    )
    asks_forecast = bool(
        question_words.intersection({
            "forecast", "tomorrow", "weekly", "week",
            "kal", "hoga", "hogi", "अगले", "कल",
        })
    )

    if not asks_weather or asks_forecast:
        return None

    city = weather_data.get("city") or {}
    weather = weather_data.get("weather") or {}
    current = weather.get("current") or {}
    daily = weather.get("daily") or {}

    if not isinstance(city, dict) or not isinstance(current, dict):
        return None

    city_name = city.get("name")
    if not city_name:
        return None

    condition = (
        current.get("description")
        or weather_description(current.get("weather_code"))
    )
    temperature = _format_weather_number(
        current.get("temperature_2m"),
        "°C",
    )
    feels_like = _format_weather_number(
        current.get("apparent_temperature"),
        "°C",
    )
    humidity = _format_weather_number(
        current.get("relative_humidity_2m"),
        "%",
    )
    wind = _format_weather_number(
        current.get("wind_speed_10m"),
        " km/h",
    )

    language = _detect_response_language(question)
    if language == "Hindi":
        answer = [f"{city_name} में अभी मौसम: {condition}।"]
    elif language == "Hinglish":
        answer = [f"{city_name} mein abhi {condition} hai."]
    else:
        answer = [f"Current weather in {city_name}: {condition}."]

    details = []
    if temperature:
        details.append(temperature)
    if feels_like:
        details.append(
            ("feels like " if language == "English" else "feels like ")
            + feels_like
        )
    if humidity:
        details.append(
            ("humidity " if language == "English" else "humidity ")
            + humidity
        )
    if wind:
        details.append(
            ("wind " if language == "English" else "wind ")
            + wind
        )

    if details:
        answer.append(" · ".join(details))

    current_time = current.get("time")
    current_date = (
        current_time[:10]
        if isinstance(current_time, str) and len(current_time) >= 10
        else None
    )
    dates = daily.get("time") or []
    date_index = dates.index(current_date) if current_date in dates else 0

    daily_highs = daily.get("temperature_2m_max") or []
    daily_lows = daily.get("temperature_2m_min") or []
    high = (
        _format_weather_number(daily_highs[date_index], "°C")
        if date_index < len(daily_highs)
        else None
    )
    low = (
        _format_weather_number(daily_lows[date_index], "°C")
        if date_index < len(daily_lows)
        else None
    )
    if high or low:
        if language == "Hindi":
            label = "आज का अधिकतम/न्यूनतम"
        elif language == "Hinglish":
            label = "Aaj ka high/low"
        else:
            label = "Today's high/low"
        answer.append(
            f"{label}: {high or 'unavailable'} / {low or 'unavailable'}."
        )

    source = weather.get("source")
    if source:
        answer.append(f"Source: {source}.")

    return " ".join(answer)


# =========================================================
# LANGUAGE DETECTION
# =========================================================

def _detect_response_language(question):
    hindi_pattern = re.compile(
        r"[\u0900-\u097F]"
    )

    if hindi_pattern.search(question):
        return "Hindi"

    hinglish_words = {
        "kya", "hai", "hain", "kaise", "batao",
        "btao", "aj", "aaj", "ky", "kal", "mausam", "baarish",
        "barish", "hoga", "hogi", "kitna", "kitni",
        "chahiye", "lekar", "jaun", "karu",
    }

    words = set(
        re.findall(
            r"[a-zA-Z]+",
            question.lower(),
        )
    )

    if words.intersection(hinglish_words):
        return "Hinglish"

    return "English"


# =========================================================
# AI SYSTEM PROMPT
# =========================================================

def _build_system_prompt(language):
    return f"""
You are SkyCast AI, a helpful weather assistant.

RESPONSE LANGUAGE:
- Respond in {language}.
- If the user uses Hindi, respond in natural Hindi.
- If the user uses Hinglish, respond in natural Hinglish.
- If the user uses English, respond in English.
- Keep the language simple and easy to understand.

WEATHER ACCURACY RULES:
1. Use only the weather data supplied in the conversation.
2. Never invent temperature, rainfall, humidity, AQI,
   wind speed, forecast, sunrise or sunset values.
3. If a required value is missing, clearly say that
   the information is unavailable.
4. Do not confuse current weather with forecast weather.
5. Mention units such as °C, km/h, mm and AQI correctly.
6. Do not claim that forecast values are guaranteed.
7. If weather data is old, mention its update time when relevant.
8. Do not claim to have accessed live weather independently.
9. Do not treat missing values as zero.
10. Give practical suggestions based on available data.

ANSWER STYLE:
- Answer the actual question directly.
- Keep ordinary answers to 1-3 short sentences.
- For a simple current-weather question, state condition and current
  temperature first; add only useful supplied values.
- For a simple question, do not list every field in the weather bundle.
- Avoid unnecessary introductions.
- Use short paragraphs and bullet points when useful.
- Explain weather terms in simple words.
- Do not repeat the entire weather report unless requested.
- For comparisons, clearly mention the differences.
- For umbrella or clothing advice, explain the reason.
- For health-related weather advice, provide general information
  and avoid medical diagnosis.

You are an assistant, not a weather data provider.
The supplied weather data is your source of truth.

ANSWER QUALITY CHECK:
- First identify the user's intent: current conditions, forecast,
  comparison, advice, air quality, or a general weather question.
- Select only the relevant values from the supplied data.
- Cross-check the selected value against its unit and time period.
- Before responding, remove unsupported claims and calculations.
- If the question is not answerable from weather data, say so clearly
  and offer the closest weather-related answer.
"""


# =========================================================
# OLLAMA CHAT REQUEST
# =========================================================

def _generate_response(question, weather_context, model_name=None, chat_history=None):
    language = _detect_response_language(question)

    system_prompt = _build_system_prompt(language)

    history_text = ""
    if chat_history:
        history_text = "\nRECENT CONVERSATION:\n" + "\n".join(
            f"{item.get('role', 'user')}: {item.get('content', '')}"
            for item in chat_history[-6:]
            if isinstance(item, dict) and item.get("content")
        )

    user_prompt = f"""
WEATHER DATA:

{weather_context}

USER QUESTION:

{question}
{history_text}

Answer the user's question using the supplied weather data.
"""

    payload = {
        "model": model_name or OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": {
            "temperature": 0.2,
            "top_p": 0.8,
            "num_ctx": 8192,
            "repeat_penalty": 1.1,
        },
    }

    try:
        response = httpx.post(
            CHAT_URL,
            json=payload,
            timeout=OLLAMA_TIMEOUT,
        )

        response.raise_for_status()

        result = response.json()

        answer = (
            result.get("message", {})
            .get("content", "")
            .strip()
        )

        if not answer:
            raise RuntimeError(
                "Ollama returned an empty response."
            )

        return answer

    except httpx.TimeoutException:
        raise RuntimeError(
            f"AI response timed out after "
            f"{OLLAMA_TIMEOUT} seconds. "
            "Try a smaller model or a shorter question."
        )

    except httpx.ConnectError:
        raise RuntimeError(
            "Cannot connect to Ollama. "
            "Make sure Ollama is running."
        )

    except httpx.HTTPStatusError as error:
        try:
            error_message = error.response.json().get(
                "error",
                error.response.text,
            )
        except ValueError:
            error_message = error.response.text

        raise RuntimeError(
            f"Ollama error: {error_message}"
        )

    except httpx.RequestError as error:
        raise RuntimeError(
            f"AI request failed: {error}"
        )

    except ValueError:
        raise RuntimeError(
            "Ollama returned an invalid response."
        )


# =========================================================
# MAIN WEATHER AI FUNCTION
# =========================================================

def ask_weather_ai(question, weather_data, chat_history=None):
    """
    Generate an AI answer using local Ollama
    and the supplied weather information.

    Returns:
        str: AI-generated answer.
    """

    question = str(question or "").strip()

    if not question:
        raise ValueError(
            "Please enter a question."
        )

    if len(question) > 10000:
        raise ValueError(
            "Question is too long. Maximum length is 10000 characters."
        )

    weather_context = _prepare_weather_context(
        weather_data
    )

    direct_answer = _answer_current_weather_question(
        question,
        weather_data,
    )
    if direct_answer:
        return direct_answer

    # Check whether Ollama is available.
    available_models = _get_ollama_models()
    selected_model = _select_available_model(available_models)

    if not selected_model:
        raise RuntimeError(
            f"No configured Qwen model is installed. "
            f"Available models: "
            f"{', '.join(available_models) or 'None'}. "
            "Run: ollama pull qwen2.5:1.5b"
        )

    try:
        return _generate_response(
            question,
            weather_context,
            selected_model,
            chat_history,
        )
    except RuntimeError as first_error:
        fallback_model = next(
            (
                model
                for model in [*OLLAMA_FALLBACK_MODELS, OLLAMA_MODEL]
                if model != selected_model
                and _model_is_available(model, available_models)
            ),
            None,
        )
        if not fallback_model:
            raise first_error

        return _generate_response(
            question,
            weather_context,
            fallback_model,
            chat_history,
        )
