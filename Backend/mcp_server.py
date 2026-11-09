
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP


# =========================================================
# PROJECT PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "Backend"
DATABASE_DIR = BASE_DIR / "Database"

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(DATABASE_DIR))


# =========================================================
# PROJECT IMPORTS
# =========================================================

from weather_api import (
    search_cities,
    get_weather_bundle,
    get_current_weather,
    get_weather_forecast,
)

from weather_compare import compare_weather

from history import get_weather_history


# =========================================================
# MCP SERVER
# =========================================================

mcp = FastMCP(
    name="SkyCast Weather MCP Server",
)


# =========================================================
# TOOL 1: SEARCH CITIES
# =========================================================

@mcp.tool()
def search_weather_cities(
    city_name: str,
    count: int = 10,
) -> dict[str, Any]:
    """
    Search for cities by name.

    Args:
        city_name: City name to search.
        count: Maximum number of matching cities.

    Returns:
        Matching city information.
    """

    city_name = city_name.strip()

    if not city_name:
        return {
            "success": False,
            "error": "City name is required.",
        }

    count = max(
        1,
        min(count, 20),
    )

    try:
        cities = search_cities(
            city_name,
            count=count,
        )

        return {
            "success": True,
            "query": city_name,
            "cities": cities,
            "count": len(cities),
        }

    except Exception as error:
        return {
            "success": False,
            "error": str(error),
        }


# =========================================================
# TOOL 2: COMPLETE WEATHER
# =========================================================

@mcp.tool()
def get_city_weather(
    city_name: str,
) -> dict[str, Any]:
    """
    Get complete weather information for a city.

    Includes current weather, forecast and air quality
    when available.

    Args:
        city_name: Name of the city.
    """

    city_name = city_name.strip()

    if not city_name:
        return {
            "success": False,
            "error": "City name is required.",
        }

    try:
        result = get_weather_bundle(
            city_name
        )

        if not result:
            return {
                "success": False,
                "error": "Weather data was not returned.",
            }

        return {
            "success": True,
            "city": result.get("city"),
            "weather": result.get("weather"),
        }

    except Exception as error:
        return {
            "success": False,
            "error": str(error),
        }


# =========================================================
# TOOL 3: CURRENT WEATHER
# =========================================================

@mcp.tool()
def get_city_current_weather(
    city_name: str,
) -> dict[str, Any]:
    """
    Get current weather information for a city.

    Args:
        city_name: Name of the city.
    """

    city_name = city_name.strip()

    if not city_name:
        return {
            "success": False,
            "error": "City name is required.",
        }

    try:
        result = get_current_weather(
            city_name
        )

        if not result:
            return {
                "success": False,
                "error": "Current weather data unavailable.",
            }

        return {
            "success": True,
            "data": result,
        }

    except Exception as error:
        return {
            "success": False,
            "error": str(error),
        }


# =========================================================
# TOOL 4: WEATHER FORECAST
# =========================================================

@mcp.tool()
def get_city_forecast(
    city_name: str,
) -> dict[str, Any]:
    """
    Get the weather forecast for a city.

    Args:
        city_name: Name of the city.
    """

    city_name = city_name.strip()

    if not city_name:
        return {
            "success": False,
            "error": "City name is required.",
        }

    try:
        result = get_weather_forecast(
            city_name
        )

        if not result:
            return {
                "success": False,
                "error": "Forecast data unavailable.",
            }

        return {
            "success": True,
            "data": result,
        }

    except Exception as error:
        return {
            "success": False,
            "error": str(error),
        }


# =========================================================
# TOOL 5: WEATHER PROVIDER COMPARISON
# =========================================================

@mcp.tool()
def compare_city_weather(
    city_name: str,
) -> dict[str, Any]:
    """
    Compare weather estimates from Open-Meteo
    and MET Norway for the same city.

    Args:
        city_name: Name of the city.
    """

    city_name = city_name.strip()

    if not city_name:
        return {
            "success": False,
            "error": "City name is required.",
        }

    try:
        result = compare_weather(
            city_name
        )

        return result

    except Exception as error:
        return {
            "success": False,
            "error": str(error),
        }


# =========================================================
# TOOL 6: WEATHER SEARCH HISTORY
# =========================================================

@mcp.tool()
def get_saved_weather_history(
    city_name: str = "",
    limit: int = 20,
) -> dict[str, Any]:
    """
    Get previously saved weather search records.

    Args:
        city_name: Optional city name filter.
        limit: Maximum number of records.
    """

    limit = max(
        1,
        min(limit, 100),
    )

    try:
        records = get_weather_history(
            city_name=city_name.strip() or None,
            limit=limit,
        )

        return {
            "success": True,
            "records": records,
            "count": len(records),
        }

    except Exception as error:
        return {
            "success": False,
            "error": str(error),
        }


# =========================================================
# START MCP SERVER
# =========================================================

if __name__ == "__main__":

    # Use stdio because mcp_client.py launches this
    # file as a separate process.
    mcp.run(
        transport="stdio"
    )
