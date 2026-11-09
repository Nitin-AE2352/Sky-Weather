
import json
import sqlite3

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_DIR = BASE_DIR / "Database"
DATABASE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

DB_PATH = DATABASE_DIR / "weather_history.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    connection = sqlite3.connect(
        str(DB_PATH),
        timeout=30,
    )

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")

    return connection


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def initialize_database():
    """
    Create the weather history table and indexes
    if they do not already exist.
    """

    with get_connection() as connection:

        connection.execute("""
            CREATE TABLE IF NOT EXISTS weather_history (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                city_name TEXT NOT NULL,

                country TEXT,

                latitude REAL,

                longitude REAL,

                temperature REAL,

                feels_like REAL,

                humidity REAL,

                wind_speed REAL,

                pressure REAL,

                precipitation REAL,

                cloud_cover REAL,

                weather_condition TEXT,

                weather_code INTEGER,

                timezone TEXT,

                source TEXT,

                weather_data TEXT,

                recorded_at TEXT NOT NULL
            )
        """)

        existing_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(weather_history)"
            ).fetchall()
        }

        optional_columns = {
            "wind_gusts": "REAL",
            "visibility": "REAL",
            "uv_index": "REAL",
            "aqi": "REAL",
            "sunrise": "TEXT",
            "sunset": "TEXT",
            "fetched_at": "TEXT",
        }

        for column_name, column_type in optional_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    f"ALTER TABLE weather_history ADD COLUMN "
                    f"{column_name} {column_type}"
                )

        connection.execute("""
            CREATE TABLE IF NOT EXISTS favorite_cities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city_name TEXT NOT NULL COLLATE NOCASE,
                country TEXT,
                latitude REAL,
                longitude REAL,
                timezone TEXT,
                created_at TEXT NOT NULL,
                last_viewed_at TEXT,
                UNIQUE(city_name, country)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                selected_city TEXT,
                result_count INTEGER NOT NULL DEFAULT 0,
                searched_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_weather_city
            ON weather_history(city_name)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_weather_recorded_at
            ON weather_history(recorded_at)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_favorite_cities_last_viewed
            ON favorite_cities(last_viewed_at)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_search_history_searched_at
            ON search_history(searched_at)
        """)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def _safe_float(value):
    """
    Convert a value to float.
    Return None if conversion is not possible.
    """

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value):
    """
    Convert a value to integer.
    Return None if conversion is not possible.
    """

    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _get_weather_parts(weather):
    """
    Extract city and current weather information
    from the weather bundle.
    """

    if not isinstance(weather, dict):
        raise ValueError(
            "Weather data must be a dictionary."
        )

    weather_section = weather.get("weather", {})

    if not isinstance(weather_section, dict):
        weather_section = {}

    current = weather_section.get("current", {})

    if not isinstance(current, dict):
        current = {}

    city = weather.get("city", {})

    if not isinstance(city, dict):
        city = {}

    return city, weather_section, current


# =========================================================
# SAVE WEATHER HISTORY
# =========================================================

def save_weather_history(city, weather):
    """
    Save a weather search into SQLite.

    Expected arguments:
        city: City information dictionary.
        weather: Complete weather bundle.
    """

    try:
        if not isinstance(city, dict):
            raise ValueError(
                "City information must be a dictionary."
            )

        if not isinstance(weather, dict):
            raise ValueError(
                "Weather information must be a dictionary."
            )

        weather_city, weather_section, current = (
            _get_weather_parts(weather)
        )

        city_name = (
            city.get("name")
            or weather_city.get("name")
            or weather.get("city_name")
        )

        if not city_name:
            raise ValueError(
                "City name is missing from weather data."
            )

        country = (
            city.get("country")
            or weather_city.get("country")
        )

        latitude = (
            city.get("latitude")
            or weather_city.get("latitude")
        )

        longitude = (
            city.get("longitude")
            or weather_city.get("longitude")
        )

        weather_json = json.dumps(
            weather,
            ensure_ascii=False,
            default=str,
        )

        recorded_at = datetime.now(
            timezone.utc
        ).isoformat()

        air_quality = weather_section.get(
            "air_quality",
            {},
        )
        if not isinstance(air_quality, dict):
            air_quality = {}

        air_quality_current = air_quality.get(
            "current",
            air_quality,
        )
        if not isinstance(air_quality_current, dict):
            air_quality_current = {}

        daily = weather_section.get("daily", {})
        if not isinstance(daily, dict):
            daily = {}

        sunrise = (
            daily.get("sunrise", [None])[0]
            if daily.get("sunrise")
            else None
        )
        sunset = (
            daily.get("sunset", [None])[0]
            if daily.get("sunset")
            else None
        )

        with get_connection() as connection:

            cursor = connection.execute(
                """
                INSERT INTO weather_history (

                    city_name,
                    country,
                    latitude,
                    longitude,
                    temperature,
                    feels_like,
                    humidity,
                    wind_speed,
                    pressure,
                    precipitation,
                    cloud_cover,
                    weather_condition,
                    weather_code,
                    timezone,
                    source,
                    weather_data,
                    recorded_at,
                    wind_gusts,
                    visibility,
                    uv_index,
                    aqi,
                    sunrise,
                    sunset,
                    fetched_at

                )

                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    city_name,
                    country,
                    _safe_float(latitude),
                    _safe_float(longitude),

                    _safe_float(
                        current.get("temperature_2m")
                    ),

                    _safe_float(
                        current.get("apparent_temperature")
                    ),

                    _safe_float(
                        current.get("relative_humidity_2m")
                    ),

                    _safe_float(
                        current.get("wind_speed_10m")
                    ),

                    _safe_float(
                        current.get("pressure_msl")
                    ),

                    _safe_float(
                        current.get("precipitation")
                    ),

                    _safe_float(
                        current.get("cloud_cover")
                    ),

                    current.get("description"),

                    _safe_int(
                        current.get("weather_code")
                    ),

                    weather_section.get("timezone"),

                    weather_section.get("source"),

                    weather_json,

                    recorded_at,

                    _safe_float(
                        current.get("wind_gusts_10m")
                    ),

                    _safe_float(
                        current.get("visibility")
                    ),

                    _safe_float(
                        current.get("uv_index")
                    ),

                    _safe_float(
                        air_quality_current.get("us_aqi")
                        or air_quality_current.get("european_aqi")
                    ),

                    sunrise,
                    sunset,
                    weather_section.get("fetched_at"),
                ),
            )

            record_id = cursor.lastrowid

        return {
            "success": True,
            "record_id": record_id,
            "message": "Weather history saved successfully.",
        }

    except Exception as error:

        return {
            "success": False,
            "error": str(error),
        }


# =========================================================
# GET WEATHER HISTORY
# =========================================================

def get_weather_history(
    city_name=None,
    limit=50,
):
    """
    Fetch saved weather records.

    Optional:
        city_name: Filter records by city.
        limit: Maximum number of records.
    """

    try:
        limit = max(
            1,
            min(int(limit), 500),
        )

        with get_connection() as connection:

            if city_name and str(city_name).strip():

                rows = connection.execute(
                    """
                    SELECT *
                    FROM weather_history

                    WHERE LOWER(city_name) = LOWER(?)

                    ORDER BY id DESC

                    LIMIT ?
                    """,
                    (
                        str(city_name).strip(),
                        limit,
                    ),
                ).fetchall()

            else:

                rows = connection.execute(
                    """
                    SELECT *
                    FROM weather_history

                    ORDER BY id DESC

                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    except Exception as error:
        raise RuntimeError(
            f"Unable to fetch weather history: {error}"
        ) from error


# =========================================================
# GET ONE HISTORY RECORD
# =========================================================

def get_weather_history_by_id(record_id):
    """
    Fetch one weather history record by ID.
    """

    try:
        record_id = int(record_id)

        with get_connection() as connection:

            row = connection.execute(
                """
                SELECT *
                FROM weather_history

                WHERE id = ?
                """,
                (record_id,),
            ).fetchone()

        if row is None:
            return None

        return dict(row)

    except Exception as error:
        raise RuntimeError(
            f"Unable to fetch history record: {error}"
        ) from error


# =========================================================
# DELETE ONE HISTORY RECORD
# =========================================================

def delete_weather_history(record_id):
    """
    Delete one history record using its ID.
    Returns True if a record was deleted.
    """

    try:
        record_id = int(record_id)

        with get_connection() as connection:

            cursor = connection.execute(
                """
                DELETE FROM weather_history

                WHERE id = ?
                """,
                (record_id,),
            )

            return cursor.rowcount > 0

    except Exception as error:
        raise RuntimeError(
            f"Unable to delete history record: {error}"
        ) from error


# =========================================================
# CLEAR ALL HISTORY
# =========================================================

def clear_weather_history():
    """
    Delete all saved weather records.
    """

    try:
        with get_connection() as connection:

            connection.execute(
                "DELETE FROM weather_history"
            )

        return {
            "success": True,
            "message": "All weather history deleted.",
        }

    except Exception as error:

        return {
            "success": False,
            "error": str(error),
        }


# =========================================================
# DATABASE STATISTICS
# =========================================================

def get_database_stats():
    """
    Return basic SQLite database statistics.
    """

    try:
        with get_connection() as connection:

            total_records = connection.execute(
                """
                SELECT COUNT(*) AS total

                FROM weather_history
                """
            ).fetchone()["total"]

            unique_cities = connection.execute(
                """
                SELECT COUNT(
                    DISTINCT LOWER(city_name)
                ) AS total

                FROM weather_history
                """
            ).fetchone()["total"]

            latest_record = connection.execute(
                """
                SELECT recorded_at

                FROM weather_history

                ORDER BY id DESC

                LIMIT 1
                """
            ).fetchone()

        return {
            "success": True,
            "total_records": total_records,
            "unique_cities": unique_cities,
            "latest_record": (
                latest_record["recorded_at"]
                if latest_record
                else None
            ),
            "database_path": str(DB_PATH),
        }

    except Exception as error:

        return {
            "success": False,
            "error": str(error),
        }


# =========================================================
# INITIALIZE DATABASE WHEN MODULE LOADS
# =========================================================

initialize_database()
