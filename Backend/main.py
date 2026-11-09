
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# --------------------------------------------------
# PROJECT PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "Backend"
DATABASE_DIR = BASE_DIR / "Database"

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(DATABASE_DIR))


# --------------------------------------------------
# PROJECT IMPORTS
# --------------------------------------------------

from weather_api import (
    search_cities,
    get_weather_bundle,
    get_current_weather,
    get_weather_forecast,
)

from ai_agent import (
    ask_weather_ai,
    check_ollama_connection,
)

from weather_compare import compare_weather

from mcp_client import (
    get_available_tools,
    execute_mcp_tool,
)

from history import (
    save_weather_history,
    get_weather_history,
    delete_weather_history,
)


# --------------------------------------------------
# APPLICATION CONFIGURATION
# --------------------------------------------------

APP_NAME = "SkyCast Weather API"
APP_VERSION = "2.0.0"

default_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

configured_origins = os.getenv("FRONTEND_ORIGINS", "")

if configured_origins.strip():
    ALLOWED_ORIGINS = [
        origin.strip()
        for origin in configured_origins.split(",")
        if origin.strip()
    ]
else:
    ALLOWED_ORIGINS = default_origins


app = FastAPI(
    title=APP_NAME,
    description=(
        "Weather application backend providing weather forecasts, "
        "AI assistance through local Ollama, MCP tools and SQLite history."
    ),
    version=APP_VERSION,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class AIChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Question about the currently loaded weather data.",
    )

    weather_data: dict[str, Any] = Field(
        ...,
        description="Weather bundle returned by the weather endpoint.",
    )

    chat_history: list[dict[str, Any]] = Field(
        default_factory=list,
        max_length=12,
        description="Recent assistant conversation for context.",
    )


class MCPToolRequest(BaseModel):
    tool_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
    )

    arguments: dict[str, Any] = Field(
        default_factory=dict,
    )

    selected_city: str | None = Field(
        default=None,
        max_length=200,
        description="Current selected city used when a city argument is omitted.",
    )


# --------------------------------------------------
# COMMON ERROR HANDLER
# --------------------------------------------------

def raise_api_error(
    message: str,
    status_code: int = 500,
) -> None:
    raise HTTPException(
        status_code=status_code,
        detail=message,
    )


# --------------------------------------------------
# ROOT
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "application": APP_NAME,
        "version": APP_VERSION,
        "status": "running",
        "documentation": "/docs",
        "health": "/api/health",
    }


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/api/health")
def health_check():
    try:
        ollama_status = check_ollama_connection()
    except Exception as error:
        ollama_status = {
            "connected": False,
            "model_available": False,
            "error": str(error),
        }

    return {
        "api": "running",
        "status": "healthy",
        "ollama": ollama_status,
    }


# --------------------------------------------------
# CITY SEARCH
# --------------------------------------------------

@app.get("/api/cities/search")
def city_search(
    city: str = Query(
        ...,
        min_length=2,
        max_length=100,
    )
):
    try:
        cities = search_cities(city.strip())

        if not cities:
            raise_api_error(
                "No matching city found.",
                404,
            )

        return {
            "count": len(cities),
            "cities": cities,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise_api_error(
            f"City search failed: {error}",
            502,
        )


# --------------------------------------------------
# COMPLETE WEATHER BUNDLE
# --------------------------------------------------

@app.get("/api/weather")
def weather(
    city: str = Query(
        ...,
        min_length=2,
        max_length=100,
    ),
    latitude: float | None = Query(
        None,
        ge=-90,
        le=90,
    ),
    longitude: float | None = Query(
        None,
        ge=-180,
        le=180,
    ),
    timezone: str | None = Query(
        None,
        max_length=100,
    ),
    country: str | None = Query(
        None,
        max_length=100,
    ),
    country_code: str | None = Query(
        None,
        max_length=2,
    ),
    admin1: str | None = Query(
        None,
        max_length=100,
    ),
    admin2: str | None = Query(
        None,
        max_length=100,
    ),
    city_id: int | None = Query(
        None,
        alias="id",
    ),
    population: int | None = Query(
        None,
        ge=0,
    ),
):
    try:
        if (latitude is None) != (longitude is None):
            raise_api_error(
                "Both latitude and longitude are required for a selected location.",
                422,
            )

        location = None
        if latitude is not None and longitude is not None:
            location = {
                "name": city.strip(),
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone,
                "country": country,
                "country_code": country_code,
                "admin1": admin1,
                "admin2": admin2,
                "id": city_id,
                "population": population,
            }

        result = get_weather_bundle(
            city.strip(),
            location=location,
        )

        if not isinstance(result, dict):
            raise_api_error(
                "Weather provider returned an invalid response.",
                502,
            )

        if not result.get("weather"):
            raise_api_error(
                "Weather information is unavailable.",
                502,
            )

        history_result = save_weather_history(
            result["city"],
            result,
        )

        history_saved = (
            isinstance(history_result, dict)
            and history_result.get("success", False)
        )

        result["history_saved"] = history_saved

        if not history_saved:
            result["history_error"] = (
                history_result.get("error", "History save failed.")
                if isinstance(history_result, dict)
                else "History save failed."
            )

        return result

    except HTTPException:
        raise

    except ValueError as error:
        raise_api_error(str(error), 404)

    except Exception as error:
        raise_api_error(
            f"Weather request failed: {error}",
            502,
        )


# --------------------------------------------------
# CURRENT WEATHER
# --------------------------------------------------

@app.get("/api/weather/current")
def current_weather(
    city: str = Query(
        ...,
        min_length=2,
        max_length=100,
    )
):
    try:
        return get_current_weather(city.strip())

    except ValueError as error:
        raise_api_error(str(error), 404)

    except Exception as error:
        raise_api_error(
            f"Current weather request failed: {error}",
            502,
        )


# --------------------------------------------------
# WEATHER FORECAST
# --------------------------------------------------

@app.get("/api/weather/forecast")
def weather_forecast(
    city: str = Query(
        ...,
        min_length=2,
        max_length=100,
    )
):
    try:
        return get_weather_forecast(city.strip())

    except ValueError as error:
        raise_api_error(str(error), 404)

    except Exception as error:
        raise_api_error(
            f"Forecast request failed: {error}",
            502,
        )


# --------------------------------------------------
# WEATHER PROVIDER COMPARISON
# --------------------------------------------------

@app.get("/api/weather/compare")
def compare_weather_endpoint(
    city: str = Query(
        ...,
        min_length=2,
        max_length=100,
    ),
    latitude: float | None = Query(None, ge=-90, le=90),
    longitude: float | None = Query(None, ge=-180, le=180),
    timezone: str | None = Query(None, max_length=100),
    country: str | None = Query(None, max_length=100),
    country_code: str | None = Query(None, max_length=2),
    admin1: str | None = Query(None, max_length=100),
    admin2: str | None = Query(None, max_length=100),
    city_id: int | None = Query(None, alias="id"),
    population: int | None = Query(None, ge=0),
):
    try:
        if (latitude is None) != (longitude is None):
            raise_api_error(
                "Both latitude and longitude are required for a selected location.",
                422,
            )

        location = None
        if latitude is not None and longitude is not None:
            location = {
                "name": city.strip(),
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone,
                "country": country,
                "country_code": country_code,
                "admin1": admin1,
                "admin2": admin2,
                "id": city_id,
                "population": population,
            }

        result = compare_weather(city.strip(), location=location)

        if not isinstance(result, dict):
            raise_api_error(
                "Comparison service returned an invalid response.",
                502,
            )

        return result

    except HTTPException:
        raise

    except ValueError as error:
        raise_api_error(str(error), 404)

    except Exception as error:
        raise_api_error(
            f"Weather comparison failed: {error}",
            502,
        )


# --------------------------------------------------
# AI WEATHER ASSISTANT
# --------------------------------------------------

@app.post("/api/assistant/chat")
def assistant_chat(request: AIChatRequest):
    question = request.question.strip()

    if not question:
        raise_api_error(
            "Question cannot be empty.",
            400,
        )

    if not request.weather_data:
        raise_api_error(
            "Weather data is required.",
            400,
        )

    try:
        answer = ask_weather_ai(
            question,
            request.weather_data,
            request.chat_history,
        )

        if not answer:
            answer = "AI could not generate an answer."

        return {
            "success": True,
            "answer": answer,
            "model": os.getenv(
                "OLLAMA_MODEL",
                "qwen2.5:1.5b",
            ),
        }

    except Exception as error:
        raise_api_error(
            f"AI assistant failed: {error}",
            502,
        )


# --------------------------------------------------
# AI MODEL STATUS
# --------------------------------------------------

@app.get("/api/assistant/status")
def assistant_status():
    try:
        return check_ollama_connection()

    except Exception as error:
        return {
            "connected": False,
            "model_available": False,
            "error": str(error),
        }


# --------------------------------------------------
# WEATHER HISTORY
# --------------------------------------------------

@app.get("/api/weather/history")
def weather_history(
    city: str | None = Query(
        default=None,
        max_length=100,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
    ),
):
    try:
        records = get_weather_history(
            city_name=city.strip() if city else None,
            limit=limit,
        )

        if not isinstance(records, list):
            records = []

        return {
            "count": len(records),
            "records": records,
        }

    except Exception as error:
        raise_api_error(
            f"Could not load weather history: {error}",
            500,
        )


# --------------------------------------------------
# DELETE ONE HISTORY RECORD
# --------------------------------------------------

@app.delete("/api/weather/history/{record_id}")
def remove_weather_history(
    record_id: int,
):
    if record_id < 1:
        raise_api_error(
            "Invalid history record ID.",
            400,
        )

    try:
        deleted = delete_weather_history(record_id)

        if not deleted:
            raise_api_error(
                "History record not found.",
                404,
            )

        return {
            "success": True,
            "message": "Weather history deleted successfully.",
            "record_id": record_id,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise_api_error(
            f"Could not delete history: {error}",
            500,
        )


# --------------------------------------------------
# MCP TOOL DISCOVERY
# --------------------------------------------------

@app.get("/api/mcp/tools")
def list_mcp_tools():
    try:
        tools = get_available_tools()

        if not isinstance(tools, dict):
            raise RuntimeError(
                "MCP tool discovery returned an invalid response."
            )

        return tools

    except Exception as error:
        raise_api_error(
            f"MCP server error: {error}",
            502,
        )


# --------------------------------------------------
# MCP TOOL EXECUTION
# --------------------------------------------------

@app.post("/api/mcp/call")
def call_mcp_tool(
    request: MCPToolRequest,
):
    tool_name = request.tool_name.strip()

    if not tool_name:
        raise_api_error(
            "MCP tool name cannot be empty.",
            400,
        )

    arguments = dict(request.arguments)
    city_tools = {
        "search_weather_cities",
        "get_city_weather",
        "get_city_current_weather",
        "get_city_forecast",
        "compare_city_weather",
    }
    if (
        tool_name in city_tools
        and not str(arguments.get("city_name") or "").strip()
    ):
        selected_city = (request.selected_city or "").strip()
        if not selected_city:
            raise_api_error(
                "A city name is required, or provide the currently selected city.",
                400,
            )
        arguments["city_name"] = selected_city

    try:
        result = execute_mcp_tool(
            tool_name,
            arguments,
        )

        if not isinstance(result, dict):
            return {
                "success": True,
                "result": result,
            }

        if result.get("is_error"):
            raise_api_error(
                str(result.get("content", "MCP tool execution failed.")),
                400,
            )

        return {
            "success": True,
            **result,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise_api_error(
            f"MCP tool execution failed: {error}",
            502,
        )


# --------------------------------------------------
# APPLICATION ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=True,
        app_dir=str(BACKEND_DIR),
    )
