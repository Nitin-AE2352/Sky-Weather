
from concurrent.futures import ThreadPoolExecutor

from weather_api import (
    search_city,
    _validate_coordinates,
    _get_open_meteo_weather,
    _get_met_weather,
)


# =========================================================
# HELPERS
# =========================================================

def _safe_float(value):
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _difference(first, second):
    first = _safe_float(first)
    second = _safe_float(second)

    if first is None or second is None:
        return None

    return round(abs(first - second), 2)


def _get_provider_weather(
    provider,
    latitude,
    longitude,
    timezone_name,
):
    try:
        if provider == "Open-Meteo":
            result = _get_open_meteo_weather(
                latitude,
                longitude,
                timezone_name,
            )

        elif provider == "MET Norway":
            result = _get_met_weather(
                latitude,
                longitude,
                timezone_name,
            )

        elif provider == "Open-Meteo ECMWF IFS":
            result = _get_open_meteo_weather(
                latitude,
                longitude,
                timezone_name,
                model="ecmwf_ifs025",
            )

            if isinstance(result, dict):
                result["source"] = "Open-Meteo ECMWF IFS 0.25 degree"

        else:
            raise ValueError(
                f"Unknown weather provider: {provider}"
            )

        if not isinstance(result, dict):
            raise ValueError(
                "Provider returned an invalid response."
            )

        if not isinstance(result.get("current"), dict):
            raise ValueError(
                "Provider did not return current weather."
            )

        return result

    except Exception as error:
        return {
            "source": provider,
            "error": str(error),
        }


# =========================================================
# PROVIDER COMPARISON
# =========================================================

def _compare_current_weather(
    open_meteo,
    met_norway,
):
    first = open_meteo.get("current", {})
    second = met_norway.get("current", {})

    temperature_difference = _difference(
        first.get("temperature_2m"),
        second.get("temperature_2m"),
    )

    wind_difference = _difference(
        first.get("wind_speed_10m"),
        second.get("wind_speed_10m"),
    )

    humidity_difference = _difference(
        first.get("relative_humidity_2m"),
        second.get("relative_humidity_2m"),
    )

    # These are comparison thresholds, not accuracy guarantees.
    temperature_agreement = (
        temperature_difference <= 2
        if temperature_difference is not None
        else None
    )

    wind_agreement = (
        wind_difference <= 10
        if wind_difference is not None
        else None
    )

    humidity_agreement = (
        humidity_difference <= 10
        if humidity_difference is not None
        else None
    )

    checks = [
        temperature_agreement,
        wind_agreement,
        humidity_agreement,
    ]

    available_checks = [
        value for value in checks
        if value is not None
    ]

    passed_checks = sum(
        1 for value in available_checks
        if value is True
    )

    total_checks = len(available_checks)

    if total_checks == 0:
        agreement_status = "Insufficient data"

    elif passed_checks == total_checks:
        agreement_status = "Good agreement"

    elif passed_checks > 0:
        agreement_status = "Partial agreement"

    else:
        agreement_status = "Significant disagreement"

    return {
        "temperature_difference_c": temperature_difference,
        "wind_speed_difference_kmh": wind_difference,
        "humidity_difference_percent": humidity_difference,

        "temperature_agreement": temperature_agreement,
        "wind_agreement": wind_agreement,
        "humidity_agreement": humidity_agreement,

        "agreement_status": agreement_status,
        "checks_passed": passed_checks,
        "total_checks": total_checks,
    }


# =========================================================
# MAIN COMPARISON FUNCTION
# =========================================================

def compare_weather(city_name, location=None):
    city_name = str(city_name or "").strip()

    if len(city_name) < 2:
        raise ValueError(
            "Please enter a valid city name."
        )

    if location is None:
        city = search_city(city_name)
    else:
        if not isinstance(location, dict):
            raise ValueError("Selected city information is invalid.")

        name = str(location.get("name") or city_name).strip()
        if not name:
            raise ValueError("Please enter a valid city name.")

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

    latitude = city.get("latitude")
    longitude = city.get("longitude")

    timezone_name = (
        city.get("timezone") or "auto"
    )

    if latitude is None or longitude is None:
        raise ValueError(
            "Could not find valid coordinates for this city."
        )

    # Fetch both providers simultaneously.
    with ThreadPoolExecutor(max_workers=2) as executor:

        open_meteo_future = executor.submit(
            _get_provider_weather,
            "Open-Meteo",
            latitude,
            longitude,
            timezone_name,
        )

        met_future = executor.submit(
            _get_provider_weather,
            "MET Norway",
            latitude,
            longitude,
            timezone_name,
        )

        open_meteo = open_meteo_future.result()
        met_norway = met_future.result()

    providers = {
        "open_meteo": open_meteo,
        "met_norway": met_norway,
    }

    if "error" in met_norway:
        providers["open_meteo_ecmwf_ifs"] = _get_provider_weather(
            "Open-Meteo ECMWF IFS",
            latitude,
            longitude,
            timezone_name,
        )

    available = [
        (name, data)
        for name, data in providers.items()
        if "error" not in data
    ]

    # Both providers failed.
    if not available:
        return {
            "success": False,
            "city": city,
            "comparison_available": False,
            "message": "Both weather providers failed.",
            "providers": providers,
        }

    primary_pair = {
        "open_meteo",
        "met_norway",
    }
    comparison_pair = None
    comparison_type = "provider"

    if primary_pair.issubset(providers) and all(
        "error" not in providers[name]
        for name in primary_pair
    ):
        comparison_pair = (
            providers["open_meteo"],
            providers["met_norway"],
        )
    elif "open_meteo_ecmwf_ifs" in providers:
        alternate_model = providers["open_meteo_ecmwf_ifs"]
        other_sources = [
            data
            for name, data in available
            if name != "open_meteo_ecmwf_ifs"
        ]
        if "error" not in alternate_model and other_sources:
            comparison_pair = (other_sources[0], alternate_model)
            comparison_type = "model"

    if comparison_pair is None:
        _, available_weather = available[0]

        return {
            "success": True,
            "city": city,
            "comparison_available": False,
            "message": (
                "Only one weather provider is available. "
                "Comparison cannot be completed."
            ),
            "selected_provider": available_weather.get(
                "source"
            ),
            "weather": available_weather,
            "providers": providers,
        }

    comparison = _compare_current_weather(
        comparison_pair[0],
        comparison_pair[1],
    )

    diagnostics = {}
    if comparison_type == "model":
        diagnostics["met_norway"] = met_norway
        providers = {
            "open_meteo": open_meteo,
            "open_meteo_ecmwf_ifs": providers["open_meteo_ecmwf_ifs"],
        }

    return {
        "success": True,
        "city": city,
        "comparison_available": True,
        "comparison_type": comparison_type,
        "comparison": comparison,
        "providers": providers,
        **({"diagnostics": diagnostics} if diagnostics else {}),
        "note": (
            "MET Norway was unavailable, so this compares Open-Meteo's "
            "best-match forecast with its ECMWF IFS model. These are "
            "independent model runs, not independent weather providers."
            if comparison_type == "model"
            else (
                "Provider agreement does not guarantee actual accuracy. "
                "Both providers supply model-based weather estimates, "
                "and their update times may differ."
            )
        ),
    }
