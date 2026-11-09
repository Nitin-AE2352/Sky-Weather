
import httpx

from datetime import datetime, timezone
import unicodedata
from zoneinfo import ZoneInfo


# =========================================================
# API CONFIGURATION
# =========================================================

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

MET_URL = (
    "https://api.met.no/weatherapi/"
    "locationforecast/2.0/compact"
)

TIMEOUT = 20

HEADERS = {
    "User-Agent": "SkyCastWeatherApp/2.0 weather-dashboard"
}


CURRENT_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "is_day",
    "precipitation",
    "rain",
    "showers",
    "snowfall",
    "weather_code",
    "cloud_cover",
    "pressure_msl",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "uv_index",
]

HOURLY_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation_probability",
    "precipitation",
    "rain",
    "weather_code",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "uv_index",
]

DAILY_FIELDS = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "sunrise",
    "sunset",
    "uv_index_max",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
]

CITY_SEARCH_ALIASES = {
    "ahmedabad": "Ahmedabad",
    "amdavad": "Ahmedabad",
    "bambai": "Mumbai",
    "bangalore": "Bengaluru",
    "bangaluru": "Bengaluru",
    "banaras": "Varanasi",
    "baroda": "Vadodara",
    "bombay": "Mumbai",
    "calcutta": "Kolkata",
    "cochin": "Kochi",
    "dilli": "Delhi",
    "indraprastha": "Delhi",
    "madras": "Chennai",
    "mysore": "Mysuru",
    "allahabad": "Prayagraj",
    "poona": "Pune",
    "puney": "Pune",
    "trivandrum": "Thiruvananthapuram",
    "kashi": "Varanasi",
    "landon": "London",
    "nyu york": "New York",
    "paris": "Paris",
    "parish": "Paris",
    "ujjain": "Ujjain",
    "मुंबई": "Mumbai",
    "बंबई": "Mumbai",
    "दिल्ली": "Delhi",
    "नयी दिल्ली": "New Delhi",
    "नई दिल्ली": "New Delhi",
    "बेंगलुरु": "Bengaluru",
    "बैंगलोर": "Bengaluru",
    "चेन्नई": "Chennai",
    "मद्रास": "Chennai",
    "कोलकाता": "Kolkata",
    "कलकत्ता": "Kolkata",
    "हैदराबाद": "Hyderabad",
    "पुणे": "Pune",
    "जयपुर": "Jaipur",
    "लखनऊ": "Lucknow",
    "वाराणसी": "Varanasi",
    "बनारस": "Varanasi",
    "अहमदाबाद": "Ahmedabad",
    "सूरत": "Surat",
    "पटना": "Patna",
    "भोपाल": "Bhopal",
    "इंदौर": "Indore",
    "नागपुर": "Nagpur",
    "चंडीगढ़": "Chandigarh",
    "कोच्चि": "Kochi",
    "मैसूर": "Mysuru",
    "मैसूरु": "Mysuru",
    "गुरुग्राम": "Gurugram",
    "गुड़गांव": "Gurugram",
    "प्रयागराज": "Prayagraj",
    "टोक्यो": "Tokyo",
    "लंदन": "London",
    "न्यूयॉर्क": "New York",
    "पेरिस": "Paris",
    "बीजिंग": "Beijing",
    "सिंगापुर": "Singapore",
    "दुबई": "Dubai",
    "मॉस्को": "Moscow",
}


# =========================================================
# WEATHER CODE DESCRIPTIONS
# =========================================================

WEATHER_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Heavy freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def weather_description(code):
    if code is None:
        return "Weather information unavailable"

    try:
        return WEATHER_DESCRIPTIONS.get(
            int(code),
            "Unknown weather condition",
        )
    except (TypeError, ValueError):
        return "Weather information unavailable"


# =========================================================
# COMMON HTTP REQUEST
# =========================================================

def _request(url, params, headers=None):
    request_headers = {
        **HEADERS,
        **(headers or {}),
    }

    try:
        response = httpx.get(
            url,
            params=params,
            headers=request_headers,
            timeout=TIMEOUT,
            follow_redirects=True,
        )

        response.raise_for_status()

        return response.json()

    except httpx.TimeoutException:
        raise Exception("Weather API request timed out.")

    except httpx.HTTPStatusError as error:
        raise Exception(
            f"Weather API returned HTTP "
            f"{error.response.status_code}."
        )

    except httpx.RequestError:
        raise Exception(
            "Unable to connect to the weather service."
        )

    except ValueError:
        raise Exception(
            "Weather API returned invalid JSON."
        )


# =========================================================
# CITY SEARCH
# =========================================================

def search_cities(city_name, count=10):
    city_name = str(city_name or "").strip()

    if len(city_name) < 2:
        return []

    count = max(1, min(int(count), 20))

    normalized_query = " ".join(city_name.casefold().split())
    query = CITY_SEARCH_ALIASES.get(normalized_query, city_name)

    def fetch_matches(search_term):
        data = _request(
            GEOCODING_URL,
            {
                "name": search_term,
                "count": count,
                "language": "en",
                "format": "json",
            },
        )

        return [
            {
                "id": city.get("id"),
                "name": city.get("name"),
                "country": city.get("country"),
                "country_code": city.get("country_code"),
                "admin1": city.get("admin1"),
                "admin2": city.get("admin2"),
                "latitude": city.get("latitude"),
                "longitude": city.get("longitude"),
                "timezone": city.get("timezone"),
                "population": city.get("population"),
            }
            for city in data.get("results", [])
        ]

    results = fetch_matches(query)

    if normalized_query != query.casefold() and results:
        return results

    if len(query) < 4 or not query.isascii():
        return results

    def normalize(value):
        decomposed = unicodedata.normalize("NFKD", value.casefold())
        return "".join(
            character
            for character in decomposed
            if character.isalnum()
        )

    query_key = normalize(query)

    def edit_distance(left, right):
        previous = list(range(len(right) + 1))

        for left_index, left_char in enumerate(left, start=1):
            current = [left_index]
            for right_index, right_char in enumerate(right, start=1):
                current.append(min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_char != right_char),
                ))
            previous = current

        return previous[-1]

    if any(
        1 - edit_distance(
            query_key,
            normalize(str(city.get("name") or "")),
        ) / max(
            len(query_key),
            len(normalize(str(city.get("name") or ""))),
            1,
        ) >= 0.9
        for city in results
    ):
        return results

    # Retry a shorter prefix for common misspellings (e.g. "Mumbay" -> "Mum").
    prefix_results = fetch_matches(query[: max(3, len(query) - 3)])
    ranked_results = []
    seen = set()

    for city in [*results, *prefix_results]:
        normalized_name = normalize(str(city.get("name") or ""))

        if not normalized_name:
            continue

        distance = edit_distance(
            query_key,
            normalized_name,
        )
        similarity = 1 - distance / max(len(query_key), 1)

        if similarity < 0.65:
            continue

        key = (
            city.get("id"),
            city.get("latitude"),
            city.get("longitude"),
        )
        if key in seen:
            continue

        seen.add(key)
        ranked_results.append((similarity, city))

    ranked_results.sort(
        key=lambda item: (
            item[0],
            item[1].get("population") or 0,
        ),
        reverse=True,
    )

    return [city for _, city in ranked_results[:count]]


def search_city(city_name):
    city_name = str(city_name or "").strip()

    if len(city_name) < 2:
        raise ValueError("Please enter a valid city name.")

    cities = search_cities(city_name, count=20)

    if not cities:
        raise ValueError(
            f"City '{city_name}' was not found."
        )

    exact_matches = [
        city for city in cities
        if city.get("name", "").casefold()
        == city_name.casefold()
    ]

    if exact_matches:
        cities = exact_matches

    # Prefer Indian city when multiple matching results exist.
    india_matches = [
        city for city in cities
        if city.get("country_code") == "IN"
    ]

    if len(india_matches) == 1:
        return india_matches[0]

    # If one result is available, use it.
    if len(cities) == 1:
        return cities[0]

    # Prefer the most populated matching city.
    cities.sort(
        key=lambda item: item.get("population") or 0,
        reverse=True,
    )

    return cities[0]


# =========================================================
# COORDINATE VALIDATION
# =========================================================

def _validate_coordinates(latitude, longitude):
    if latitude is None or longitude is None:
        raise ValueError(
            "Latitude and longitude are required."
        )

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        raise ValueError("Invalid coordinates.")

    if not -90 <= latitude <= 90:
        raise ValueError("Invalid latitude.")

    if not -180 <= longitude <= 180:
        raise ValueError("Invalid longitude.")


# =========================================================
# OPEN-METEO WEATHER PROVIDER
# =========================================================

def _get_open_meteo_weather(
    latitude,
    longitude,
    timezone_name,
    model=None,
):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join(CURRENT_FIELDS),
        "hourly": ",".join(HOURLY_FIELDS),
        "daily": ",".join(DAILY_FIELDS),
        "timezone": timezone_name,
        "forecast_days": 7,
        "temperature_unit": "celsius",
        "wind_speed_unit": "kmh",
        "precipitation_unit": "mm",
    }
    if model:
        params["models"] = model

    data = _request(WEATHER_URL, params)

    current = data.get("current")

    if not current:
        raise Exception(
            "Open-Meteo current weather is unavailable."
        )

    current["description"] = weather_description(
        current.get("weather_code")
    )

    hourly = data.get("hourly") or {}
    daily = data.get("daily") or {}

    daily["description"] = [
        weather_description(code)
        for code in daily.get("weather_code", [])
    ]

    return {
        "current": current,
        "hourly": hourly,
        "daily": daily,
        "timezone": data.get("timezone"),
        "timezone_abbreviation": data.get(
            "timezone_abbreviation"
        ),
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "elevation": data.get("elevation"),
        "units": {
            "temperature": "°C",
            "wind_speed": "km/h",
            "precipitation": "mm",
            "pressure": "hPa",
        },
        "source": (
            "Open-Meteo"
            if not model
            else f"Open-Meteo ({model.replace('_', ' ').upper()})"
        ),
        **({"model": model} if model else {}),
        "updated_at": current.get("time"),
        "fetched_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }


# =========================================================
# MET NORWAY WEATHER PROVIDER
# =========================================================

def _met_symbol_description(symbol):
    if not symbol:
        return "Weather information unavailable"

    symbol = symbol.lower()

    if "thunder" in symbol:
        return "Thunderstorm"

    if "snow" in symbol:
        return "Snow"

    if "sleet" in symbol:
        return "Sleet"

    if "rain" in symbol:
        return "Rain"

    if "fog" in symbol:
        return "Fog"

    if "partlycloudy" in symbol:
        return "Partly cloudy"

    if "cloudy" in symbol:
        return "Cloudy"

    if "clearsky" in symbol:
        return "Clear sky"

    return "Weather conditions available"


def _parse_met_time(item):
    return datetime.fromisoformat(
        item["time"].replace("Z", "+00:00")
    )


def _get_met_weather(
    latitude,
    longitude,
    timezone_name,
):
    data = _request(
        MET_URL,
        {
            "lat": latitude,
            "lon": longitude,
        },
        headers=HEADERS,
    )

    series = (
        data.get("properties", {})
        .get("timeseries", [])
    )

    if not series:
        raise Exception(
            "MET Norway forecast is unavailable."
        )

    try:
        local_zone = ZoneInfo(timezone_name)
    except Exception:
        local_zone = timezone.utc

    now = datetime.now(timezone.utc)

    # Select the closest available forecast time.
    selected = min(
        series,
        key=lambda item: abs(
            (
                _parse_met_time(item) - now
            ).total_seconds()
        ),
    )

    details = (
        selected["data"]["instant"]["details"]
    )

    next_data = selected["data"].get(
        "next_1_hours",
        {},
    )

    next_details = next_data.get("details", {})
    next_summary = next_data.get("summary", {})

    symbol = next_summary.get("symbol_code")

    current_time = _parse_met_time(
        selected
    ).astimezone(local_zone)

    wind_ms = details.get("wind_speed")
    gust_ms = details.get("wind_speed_of_gust")

    current = {
        "time": current_time.isoformat(),
        "temperature_2m": details.get(
            "air_temperature"
        ),
        "relative_humidity_2m": details.get(
            "relative_humidity"
        ),
        "apparent_temperature": None,
        "is_day": int(
            6 <= current_time.hour < 18
        ),
        "precipitation": next_details.get(
            "precipitation_amount", 0
        ),
        "rain": next_details.get(
            "precipitation_amount", 0
        ),
        "showers": None,
        "snowfall": None,
        "weather_code": None,
        "cloud_cover": details.get(
            "cloud_area_fraction"
        ),
        "pressure_msl": details.get(
            "air_pressure_at_sea_level"
        ),
        "surface_pressure": None,
        "wind_speed_10m": (
            round(wind_ms * 3.6, 1)
            if wind_ms is not None else None
        ),
        "wind_direction_10m": details.get(
            "wind_from_direction"
        ),
        "wind_gusts_10m": (
            round(gust_ms * 3.6, 1)
            if gust_ms is not None else None
        ),
        "uv_index": None,
        "description": _met_symbol_description(
            symbol
        ),
    }

    hourly = {
        "time": [],
        "temperature_2m": [],
        "relative_humidity_2m": [],
        "precipitation_probability": [],
        "precipitation": [],
        "rain": [],
        "weather_code": [],
        "cloud_cover": [],
        "wind_speed_10m": [],
        "wind_direction_10m": [],
        "uv_index": [],
    }

    daily_groups = {}

    for item in series:
        item_time = _parse_met_time(
            item
        ).astimezone(local_zone)

        instant = (
            item["data"]["instant"]["details"]
        )

        hour_data = item["data"].get(
            "next_1_hours",
            {},
        )

        hour_details = hour_data.get(
            "details",
            {},
        )

        hour_summary = hour_data.get(
            "summary",
            {},
        )

        if (
            item_time >= current_time
            and len(hourly["time"]) < 48
        ):
            hourly["time"].append(
                item_time.isoformat()
            )

            hourly["temperature_2m"].append(
                instant.get("air_temperature")
            )

            hourly["relative_humidity_2m"].append(
                instant.get("relative_humidity")
            )

            hourly["precipitation_probability"].append(
                None
            )

            rainfall = hour_details.get(
                "precipitation_amount"
            )

            hourly["precipitation"].append(rainfall)
            hourly["rain"].append(rainfall)

            hourly["weather_code"].append(None)

            hourly["cloud_cover"].append(
                instant.get("cloud_area_fraction")
            )

            wind = instant.get("wind_speed")

            hourly["wind_speed_10m"].append(
                round(wind * 3.6, 1)
                if wind is not None else None
            )

            hourly["wind_direction_10m"].append(
                instant.get("wind_from_direction")
            )

            hourly["uv_index"].append(None)

        date_key = item_time.date().isoformat()

        group = daily_groups.setdefault(
            date_key,
            {
                "temperatures": [],
                "rainfall": [],
                "winds": [],
                "symbols": [],
            },
        )

        temperature = instant.get(
            "air_temperature"
        )

        if temperature is not None:
            group["temperatures"].append(
                temperature
            )

        rainfall = hour_details.get(
            "precipitation_amount"
        )

        if rainfall is not None:
            group["rainfall"].append(rainfall)

        wind = instant.get("wind_speed")

        if wind is not None:
            group["winds"].append(
                wind * 3.6
            )

        daily_symbol = hour_summary.get(
            "symbol_code"
        )

        if daily_symbol:
            group["symbols"].append(
                daily_symbol
            )

    daily = {
        "time": [],
        "weather_code": [],
        "temperature_2m_max": [],
        "temperature_2m_min": [],
        "apparent_temperature_max": [],
        "apparent_temperature_min": [],
        "sunrise": [],
        "sunset": [],
        "uv_index_max": [],
        "precipitation_sum": [],
        "precipitation_probability_max": [],
        "wind_speed_10m_max": [],
        "description": [],
    }

    for date_key, group in sorted(
        daily_groups.items()
    ):
        temperatures = group["temperatures"]
        rainfall = group["rainfall"]
        winds = group["winds"]

        daily["time"].append(date_key)
        daily["weather_code"].append(None)

        daily["temperature_2m_max"].append(
            max(temperatures)
            if temperatures else None
        )

        daily["temperature_2m_min"].append(
            min(temperatures)
            if temperatures else None
        )

        daily["apparent_temperature_max"].append(None)
        daily["apparent_temperature_min"].append(None)
        daily["sunrise"].append(None)
        daily["sunset"].append(None)
        daily["uv_index_max"].append(None)

        daily["precipitation_sum"].append(
            round(sum(rainfall), 2)
            if rainfall else None
        )

        daily["precipitation_probability_max"].append(
            None
        )

        daily["wind_speed_10m_max"].append(
            round(max(winds), 1)
            if winds else None
        )

        daily["description"].append(
            _met_symbol_description(
                group["symbols"][0]
                if group["symbols"] else None
            )
        )

    return {
        "current": current,
        "hourly": hourly,
        "daily": daily,
        "timezone": timezone_name,
        "timezone_abbreviation": None,
        "latitude": latitude,
        "longitude": longitude,
        "elevation": None,
        "units": {
            "temperature": "°C",
            "wind_speed": "km/h",
            "precipitation": "mm",
            "pressure": "hPa",
        },
        "source": "MET Norway",
        "updated_at": current["time"],
        "fetched_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }


# =========================================================
# WEATHER PROVIDER WITH FALLBACK
# =========================================================

def get_weather(
    latitude,
    longitude,
    timezone_name="auto",
):
    _validate_coordinates(
        latitude,
        longitude,
    )

    try:
        return _get_open_meteo_weather(
            latitude,
            longitude,
            timezone_name,
        )

    except Exception as primary_error:
        print(
            "Open-Meteo failed. "
            "Trying MET Norway:",
            primary_error,
        )

        try:
            return _get_met_weather(
                latitude,
                longitude,
                timezone_name,
            )

        except Exception as fallback_error:
            raise Exception(
                "Both weather providers failed. "
                f"Open-Meteo: {primary_error}. "
                f"MET Norway: {fallback_error}"
            )


# =========================================================
# AIR QUALITY
# =========================================================

def get_air_quality(
    latitude,
    longitude,
    timezone_name="auto",
):
    _validate_coordinates(
        latitude,
        longitude,
    )

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "pm10,pm2_5,carbon_monoxide,"
            "nitrogen_dioxide,sulphur_dioxide,"
            "ozone,us_aqi,european_aqi"
        ),
        "hourly": (
            "pm10,pm2_5,us_aqi,european_aqi"
        ),
        "timezone": timezone_name,
        "forecast_days": 1,
    }

    data = _request(
        AIR_QUALITY_URL,
        params,
    )

    return {
        "current": data.get("current", {}),
        "hourly": data.get("hourly", {}),
        "source": "Open-Meteo Air Quality",
        "data_type": "model_estimate",
        "disclaimer": (
            "Model-based air-quality estimates are not measurements "
            "from a local regulatory monitoring station."
        ),
        "updated_at": (
            data.get("current", {}).get("time")
        ),
    }


# =========================================================
# COMPLETE WEATHER BUNDLE
# =========================================================

def get_weather_bundle(city_name, location=None):
    if location is None:
        city = search_city(city_name)
    else:
        if not isinstance(location, dict):
            raise ValueError("Selected city information is invalid.")

        name = str(
            location.get("name") or city_name or ""
        ).strip()

        if not name:
            raise ValueError("A city name is required.")

        latitude = location.get("latitude")
        longitude = location.get("longitude")
        _validate_coordinates(latitude, longitude)

        city = {
            "id": location.get("id"),
            "name": name,
            "country": location.get("country"),
            "country_code": location.get("country_code"),
            "admin1": location.get("admin1"),
            "admin2": location.get("admin2"),
            "latitude": float(latitude),
            "longitude": float(longitude),
            "timezone": location.get("timezone") or "auto",
            "population": location.get("population"),
        }

    latitude = city["latitude"]
    longitude = city["longitude"]

    timezone_name = (
        city.get("timezone") or "auto"
    )

    weather = get_weather(
        latitude,
        longitude,
        timezone_name,
    )

    try:
        air_quality = get_air_quality(
            latitude,
            longitude,
            timezone_name,
        )

    except Exception as error:
        air_quality = {
            "error": str(error),
            "current": {},
            "hourly": {},
            "source": "Open-Meteo Air Quality",
        }

    weather["air_quality"] = air_quality

    return {
        "city": city,
        "weather": weather,
    }


# =========================================================
# CURRENT WEATHER
# =========================================================

def get_current_weather(city_name):
    bundle = get_weather_bundle(city_name)

    weather = bundle["weather"]

    return {
        "city": bundle["city"],
        "current": weather["current"],
        "air_quality": weather["air_quality"],
        "source": weather["source"],
        "updated_at": weather["updated_at"],
    }


# =========================================================
# WEATHER FORECAST
# =========================================================

def get_weather_forecast(city_name):
    bundle = get_weather_bundle(city_name)

    weather = bundle["weather"]

    return {
        "city": bundle["city"],
        "hourly": weather["hourly"],
        "daily": weather["daily"],
        "timezone": weather["timezone"],
        "source": weather["source"],
        "updated_at": weather["updated_at"],
    }
